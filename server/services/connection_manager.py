import time
import asyncio
import json
from pathlib import Path
from os import getenv

from redis.exceptions import ConnectionError, TimeoutError
from fastapi import WebSocket
from dotenv import load_dotenv

from server.services.redis_manager import RedisManager
from server.services.db_module.db_manager import DatabaseManager


env_path = Path(".") / ".env"
if env_path.exists():
    load_dotenv(env_path)

REDIS_QUEUE = getenv("REDIS_QUEUE")
MAX_RECONNECT_ATTEMPTS = int(getenv("MAX_RECONNECT_ATTEMPTS"))
RECONNECT_DELAY = getenv("RECONNECT_DELAY")
CACHED_MESSAGE_UPLOAD_TIMER = int(getenv("CACHED_MESSAGE_UPLOAD_TIMER"))


class ConnectionManager:
    def __init__(self, db: DatabaseManager):
        self.redis_man = RedisManager()
        self.db = db
        self.listener_task = None
        # Dict of active connections, {"username":{"ws": websocket, "channels": {"welcome", "hello", etc}}
        self.active_connections: dict[str, dict[WebSocket, set]] = {}
        # Dict of channels with pointers to the websockets of active subscribers {"channel":{"username": websocket"}}
        self.channel_subscribers: dict[str, dict] = {}
        self.message_cache: list[dict] = []
        self.time_last_message_backup: int = round(time.time())

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        channels = self.db.retrieve_channels(username)
        print(f"{username} is a member of {channels} channels")
        self.active_connections[username] = {"ws": websocket, "channels": channels}
        for channel in channels:
            if channel not in self.channel_subscribers:
                self.channel_subscribers[channel] = {}
            self.channel_subscribers[channel][username] = websocket

        info_message = {"event": "channel_subscriptions", "data": list(channels)}

        await websocket.send_text(json.dumps(info_message))

        message_history: list = self.db.retrieve_message_history(channels)

        # If any messages are in the cache, add the to the message history to send to newly logged in accounts
        if self.message_cache:
            message_history.extend(self.message_cache)

        history_message = {"event": "message history", "data": message_history}

        await websocket.send_text(json.dumps(history_message))

        # Starts the redis listener once at least one user is connected.
        if not self.listener_task or self.listener_task.done():
            self.listener_task = asyncio.create_task(self.start_listener())
            print("First connection opened, starting listener")

    async def disconnect(self, username: str):
        # TODO Could use this to send a 'user disconnected' message to the channel

        # Loop through all channels that a username is subscribed to, and remove that username from each channel's dict of subscribed users. If that channel no longer has any subscribed users connected, remove it from the dict of active channels. Finally remove user from the dict of active connections
        for channel in self.active_connections[username].get("channels", []):
            self.channel_subscribers[channel].pop(username)
            if not self.channel_subscribers[channel]:
                self.channel_subscribers.pop(channel)
        self.active_connections.pop(username, None)

        # Disable listener if there are no active connections
        if not self.active_connections and self.listener_task:
            self.listener_task.cancel()
            self.listener_task = None
            if self.message_cache:
                await self.upload_cached_messages()
            print("No active connections, stopping listener. Message cache uploaded")

    async def broadcast(self, message: dict):
        """Send message to all active connections that are subscribed to that channel"""
        channel = message.get("channel")
        # Convert message to string so it can be sent over websocket
        message_str = json.dumps(message)
        # Loop through all active connections subscribed to that channel and send the message
        for websocket in self.channel_subscribers.get(channel).values():
            await websocket.send_text(message_str)

    async def listen_for_messages(self):
        # If no messages in queue, wait 0.1 seconds and then check again. As long as there are messages in the queue, send them out as fast as possible.
        while True:
            try:
                await self.cached_messages_watcher()
                while await self.redis_man.get_len(queue=REDIS_QUEUE) > 0:
                    try:
                        message: str = await self.redis_man.dequeue_message()
                        if message:
                            data = json.loads(message)
                            await self.broadcast(data)
                    except json.JSONDecodeError:
                        print(f"Failed to parse message data: {message}")
                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"Error in message listener: {e}")
                await asyncio.sleep(1)

    async def start_listener(self):
        attempts = 0
        # Reset message upload timer if no messages in cache. This is to prevent the first message being uploaded in each new session, as the timer will be measuring from the previous session.
        if not self.message_cache:
            self.time_last_message_backup = round(time.time())
        while attempts < MAX_RECONNECT_ATTEMPTS:
            try:
                await self.listen_for_messages()
            except (ConnectionError, TimeoutError) as e:
                print(f"Redis connection error: {str(e)}. Attempting to reconnect...")
                attempts += 1
                await asyncio.sleep(RECONNECT_DELAY)
            except Exception as e:
                print(f"Unexpected error in listener: {str(e)}")
                break
        print("Max reconnection attempts reached. Listener stopped.")

    async def cached_messages_watcher(self):
        """Method to take cached messages and batch upload them to the database if conditions are met"""
        num_messages: int = len(self.message_cache)
        current_time: int = round(time.time())
        time_since_last_message_upload: int = (
            current_time - self.time_last_message_backup
        )
        # If the number of stored messages is >= 5, or if there are any messages and the last upload was more than CACHED_MESSAGE_UPLOAD_TIMER seconds ago, do the batch upload immediately
        if num_messages >= 5 or (
            time_since_last_message_upload > CACHED_MESSAGE_UPLOAD_TIMER
            and num_messages
        ):
            await self.upload_cached_messages()

    async def upload_cached_messages(self):
        """Batch inserts all cached messages into database and resets upload timer"""
        print("Uploading cached messages")
        if self.db.batch_insert_messages(self.message_cache):
            self.message_cache.clear()
            self.time_last_message_backup = round(time.time())
        else:
            # TODO log error on failure to avoid losing cached messages
            pass
