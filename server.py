from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    status,
    Depends,
)
from pydantic import BaseModel, Field
from redis.exceptions import ConnectionError, TimeoutError
from contextlib import asynccontextmanager
import json
import redis
import time
import asyncio
from pathlib import Path
from os import getenv
from dotenv import load_dotenv
from pprint import pprint

from routers.auth import router as auth_router
from routers.auth import User, get_current_active_user, get_current_user

from db_module.db_manager import DatabaseManager

db = DatabaseManager()

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
# TODO Add server diagnostics, eg confirm database and redis connections are live, and report back here
@app.get("/", status_code=status.HTTP_200_OK)
def ping():
    return {"status": "ready"}


@app.get("/tables")
def tables():
    db.init_database()
    return db.list_tables()


@app.get("/filepath")
def get_filepath():
    db.init_database()
    return db.read_db_filepath()


class RedisManager:
    def __init__(self):
        self.redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)

    async def enqueue_message(self, message: dict):
        message_as_string = json.dumps(message)
        await asyncio.to_thread(self.redis.rpush, REDIS_QUEUE, message_as_string)
        # await self.redis.rpush(REDIS_QUEUE, message)

    async def dequeue_message(self) -> str:
        return await asyncio.to_thread(self.redis.blpop, REDIS_QUEUE, timeout=0)
        # return await self.redis.blpop(REDIS_QUEUE, message)

    async def get_len(self, queue: str) -> int:
        return await asyncio.to_thread(self.redis.llen, queue)


class ConnectionManager:
    def __init__(self):
        # TODO Add function to check length of self.message_store. If more than X messages, or more than Y time, upload messages to database in a batch, reset timer, and clear list.
        self.active_connections: dict[str, dict[WebSocket, set]] = {}
        self.redis_man = RedisManager()
        # self.user_channels: dict[str:list[str]] = {}
        self.listener_task = None
        self.message_store: list = []
        self.time_since_message_backup: float = time.time()

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        # TODO Use GUI login to provide bearer token to client, use this to authorize the websocket connection and add logic here. Store tokens in Redis.
        # print(f"Websocket connection requested for user: {username}")
        #! channels: set = retrieve_channels(username=username)
        channels = db.retrieve_channels(username)
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
            try:
                while await self.redis_man.get_len(queue=REDIS_QUEUE) > 0:
                    try:
                        _, message = await self.redis_man.dequeue_message()
                        if message:
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


class AccountCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=255)


# Endpoint to create an account
@app.post("/create_account", status_code=status.HTTP_201_CREATED)
async def create_account_endpoint(account: AccountCreate):
    # return create_account(account.username, account.password)
    return db.create_account(account.username, account.password)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        auth_header = websocket.headers.get("Authorization")
        print(f"Received auth header: {auth_header}")
        if not auth_header or not auth_header.startswith("Bearer "):
            print("Invalid or missing Authorization header")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        token = auth_header.split("Bearer ")[1]

        try:
            current_user = await get_current_user(token)
            active_user = await get_current_active_user(current_user)
            print(f"Authenticated user: {active_user.username}")
        except HTTPException as e:
            print(f"Authentication failed: {str(e)}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # User is authenticated and active, proceed with the WebSocket connection
        await connection_man.connect(websocket, active_user.username)

        while True:
            message: str = await websocket.receive_text()
            message_dict: dict = json.loads(message)
            message_dict["username"] = active_user.username
            connection_man.message_store.append(message_dict)
            # TODO Add graceful error handling for batch inserts / fails
            # TODO Add timeout or length, whichever comes first
            if not len(connection_man.message_store) % 5:
                if db.batch_insert_messages(connection_man.message_store):
                    connection_man.message_store.clear()
                else:
                    pass
            await connection_man.redis_man.enqueue_message(message_dict)
    except WebSocketDisconnect:
        await connection_man.disconnect(active_user.username)
    except asyncio.CancelledError:
        await connection_man.disconnect(active_user.username)


@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_event_loop()
    print(f"Current event loop: {type(loop).__name__}")


@app.on_event("shutdown")
async def shutdown_event():
    if connection_man.listener_task:
        connection_man.listener_task.cancel()
        try:
            await connection_man.listener_task
        except asyncio.CancelledError:
            pass
    # Close all active WebSocket connections
    for username, connection in connection_man.active_connections.items():
        await connection["ws"].close()
    connection_man.active_connections.clear()
    db.close_all()


# TODO Retrieve channel subscriptions on user login
# TODO Add ability for people to update their channel subscriptions via endpoint
# TODO Add database functions to update channel subscriptions
