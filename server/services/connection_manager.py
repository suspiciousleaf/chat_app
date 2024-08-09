import time
import asyncio
import json
from pathlib import Path
from os import getenv

from redis.exceptions import ConnectionError, TimeoutError
from fastapi import WebSocket
from dotenv import load_dotenv

from server.services.redis_manager import RedisManager


env_path = Path(".") / ".env"
if env_path.exists():
    load_dotenv(env_path)

REDIS_QUEUE = getenv("REDIS_QUEUE")
MAX_RECONNECT_ATTEMPTS = getenv("MAX_RECONNECT_ATTEMPTS")
RECONNECT_DELAY = getenv("RECONNECT_DELAY")


class ConnectionManager:
    def __init__(self, db):
        # TODO Add function to check length of self.message_store. If more than X messages, or more than Y time, upload messages to database in a batch, reset timer, and clear list.
        self.active_connections: dict[str, dict[WebSocket, set]] = {}
        self.redis_man = RedisManager()
        # self.user_channels: dict[str:list[str]] = {}
        self.listener_task = None
        self.message_store: list = []
        self.time_since_message_backup: float = time.time()
        self.db = db

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        # TODO Use GUI login to provide bearer token to client, use this to authorize the websocket connection and add logic here. Store tokens in Redis.
        # print(f"Websocket connection requested for user: {username}")
        #! channels: set = retrieve_channels(username=username)
        channels = self.db.retrieve_channels(username)
        channels.add("welcome")
        print(f"User is a member of {channels} channels")
        # Add all users to the "welcome" channel
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
        # print(f"Disconnected user: {username}")

        # Disable listener if there are no active connections
        if not self.active_connections and self.listener_task:
            self.listener_task.cancel()
            self.listener_task = None
            print("No active connections, stopping listener.")

    # async def disconnect(self, username: str):
    #     connection = self.active_connections.pop(username, None)
    #     if connection:
    #         await connection["ws"].close()
    #     if not self.active_connections and self.listener_task:
    #         self.listener_task.cancel()
    #         try:
    #             await self.listener_task
    #         except asyncio.CancelledError:
    #             pass
    #         self.listener_task = None
    #         print("No active connections, stopping listener.")

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
            print(f"listen_for_messages() while True loop")
            try:
                while await self.redis_man.get_len(queue=REDIS_QUEUE) > 0:
                    print(self.redis_man.get_len(queue=REDIS_QUEUE))
                    try:
                        _, message = await self.redis_man.dequeue_message()
                        if message:
                            print(message)
                            data = json.loads(message)
                            #! print(f"message as received by message_listener: {data}")
                            await self.broadcast(data)
                    except json.JSONDecodeError:
                        print(f"Failed to parse message data: {message}")
                await asyncio.sleep(0.25)

            except Exception as e:
                print(f"Error in message listener: {str(e)}")
                await asyncio.sleep(1)

    async def start_listener(self):
        # print("start_listener() called")
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
