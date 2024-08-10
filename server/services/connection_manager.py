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


class ConnectionManager:
    def __init__(self, db: DatabaseManager):
        # TODO Add function to check length of self.message_store. If more than X messages, or more than Y time, upload messages to database in a batch, reset timer, and clear list.
        self.redis_man = RedisManager()
        self.db = db
        self.listener_task = None
        self.active_connections: dict[str, dict[WebSocket, set]] = {}
        # self.channel_participants:dict = {}
        self.message_store: list = []
        self.time_since_message_backup: float = time.time()

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        channels = self.db.retrieve_channels(username)
        print(f"User is a member of {channels} channels")
        self.active_connections[username] = {"ws": websocket, "channels": channels}
        # self.active_connections[username] = websocket
        # self.user_channels[username] = await self.get_user_channels(username)

        # Starts the redis listener once at least one user is connected.
        if not self.listener_task or self.listener_task.done():
            self.listener_task = asyncio.create_task(self.start_listener())
            print("First connection opened, starting listener")

    async def disconnect(self, username: str):
        # self.active_connections.pop(username, None)
        # self.user_channels.pop(username, None)
        # TODO Could use this to send a 'user disconnected' message to the channel
        # connection = self.active_connections.get(username)
        # if connection["ws"]:
        #     await connection["ws"].close()
        self.active_connections.pop(username, None)

        # Disable listener if there are no active connections
        if not self.active_connections and self.listener_task:
            self.listener_task.cancel()
            self.listener_task = None
            print("No active connections, stopping listener.")

    async def broadcast(self, message: dict):
        channel = message.get("channel")
        # print(f"Channel as seen by broadcast: {channel}")
        for username, user_connection in self.active_connections.items():
            if channel in user_connection["channels"]:
                # print(f"Sending {message} to {username}")
                await user_connection["ws"].send_text(json.dumps(message))

    async def listen_for_messages(self):
        # If no messages in queue, wait 0.25 seconds and then check again. As long as there are messages in the queue, send them out as fast as possible.
        while True:
            try:
                while await self.redis_man.get_len(queue=REDIS_QUEUE) > 0:
                    try:
                        _, message = await self.redis_man.dequeue_message()
                        if message:
                            data = json.loads(message)
                            await self.broadcast(data)
                    except json.JSONDecodeError:
                        print(f"Failed to parse message data: {message}")
                await asyncio.sleep(0.25)

            except Exception as e:
                print(f"Error in message listener: {str(e)}")
                await asyncio.sleep(1)

    async def start_listener(self):
        attempts = 0
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
