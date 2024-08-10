from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    status,
    Depends,
)
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
import json
import time
import asyncio
from pathlib import Path
from os import getenv
from dotenv import load_dotenv
from pprint import pprint

from server.routers.auth import router as auth_router
from server.routers.auth import User, get_current_active_user, get_current_user

from server.services.db_module.db_manager import DatabaseManager
from server.services.connection_manager import ConnectionManager

db = DatabaseManager()

app = FastAPI()

app.include_router(auth_router)


env_path = Path(".") / ".env"
if env_path.exists():
    load_dotenv(env_path)


# Endpoint to ping server
# TODO Add server diagnostics, eg confirm database and redis connections are live, and report back here
@app.get("/", status_code=status.HTTP_200_OK)
async def ping():
    db_status = await connection_man.db.verify_connection_and_tables()
    redis_status = await connection_man.redis_man.verify_connection()
    if db_status.get("status") and redis_status.get("status"):
        return {"status": "ready"}

    error_details = []
    if not db_status["status"]:
        error_details.append(db_status["details"])
    if not redis_status["status"]:
        error_details.append(redis_status["details"])
    return {"status": ", ".join(error_details)}


@app.get("/tables")
def tables():
    db.init_database()
    return db.list_tables()


@app.get("/filepath")
def get_filepath():
    db.init_database()
    return db.read_db_filepath()


connection_man = ConnectionManager(db)


class AccountCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=255)


# Endpoint to create an account
@app.post("/create_account", status_code=status.HTTP_201_CREATED)
async def create_account_endpoint(account: AccountCreate):
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