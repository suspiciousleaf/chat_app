from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    status,
)
from redis.exceptions import ConnectionError, TimeoutError
from contextlib import asynccontextmanager
import json
import redis
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from routers.auth import router as auth_router
from db_module.db_utilities import retrieve_channels


app = FastAPI()

app.include_router(auth_router)


env_path = Path(".") / ".env"
if env_path.exists():
    load_dotenv(env_path)

REDIS_URL = "redis://localhost:6379/0"
REDIS_QUEUE = "chat_queue"
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 5  # seconds


# Endpoint to ping server
@app.get("/")
def ping():
    return "WS chat app server running"


class RedisManager:
    def __init__(self):
        self.redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)

    async def enqueue_message(self, message: str):
        await asyncio.to_thread(self.redis.rpush, REDIS_QUEUE, message)
        # await self.redis.rpush(REDIS_QUEUE, message)

    async def dequeue_message(self) -> str:
        return await asyncio.to_thread(self.redis.blpop, REDIS_QUEUE, timeout=0)
        # return await self.redis.blpop(REDIS_QUEUE, message)


class ConnectionManager:
    def __init__(self):
        # TODO Add function to check length of self.message_store. If more than X messages, or more than Y time, upload messages to database in a batch, reset timer, and clear list.
        self.active_connections: dict[str:dict] = {}
        self.redis_man = RedisManager()
        # self.user_channels: dict[str:list[str]] = {}
        self.listener_task = None
        self.message_store = []
        self.time_since_message_backup = time.time()

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        # TODO Use GUI login to provide bearer token to client, use this to authorize the websocket connection and add logic here. Store tokens in Redis.
        print(f"Websocket connection requested for user: {username}")
        channels = retrieve_channels(username=username)
        self.active_connections[username] = {"ws": websocket, "channels": channels}
        # self.active_connections[username] = websocket
        # self.user_channels[username] = await self.get_user_channels(username)

        # Starts the redis listener once at least one user is connected.
        if not self.listener_task or self.listener_task.done():
            self.listener_task = asyncio.create_task(self.start_listener())

    async def disconnect(self, username: str):
        # self.active_connections.pop(username, None)
        # self.user_channels.pop(username, None)
        # TODO Could use this to send a 'user disconnected' message to the channel
        connection = self.active_connections.get(username)
        if connection:
            await connection["ws"].close()
            self.active_connections.pop(username, None)
            print(f"Disconnecting user: {username}")
        # TODO If no active connections, disable listener
        # if len(self.active_connections) == 0:

    async def broadcast(self, message: dict):
        channel = message.get("channel")
        for username, user_connection in self.active_connections.items():
            if channel in user_connection["channels"]:
                await self.active_connections[username]["ws"].send_text(message)

    async def listen_for_messages(self):
        # If no messages in queue, wait 0.2 seconds and then check again
        while True:
            try:
                if self.redis_man.llen(REDIS_QUEUE) > 0:
                    try:
                        _, message = await self.redis_man.dequeue_message()
                        if message:
                            data = json.loads(message)
                            await self.broadcast(data)
                    except json.JSONDecodeError:
                        print(f"Failed to parse message data: {message}")
                await asyncio.sleep(0.2)
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


connection_man = ConnectionManager()


@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    # TODO Move client_id and bearer token to header
    await connection_man.connect(websocket, username)
    try:
        while True:
            data = await websocket.receive_text()
            connection_man.message_store.append(data)
            await connection_man.redis_man.enqueue_message(data)
    except WebSocketDisconnect:
        await connection_man.disconnect(username)


#! First draft, try connecting and test behaviour
