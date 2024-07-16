from fastapi import FastAPI, WebSocket, HTTPException, status

# from fastapi.responses import JSONResponse
from pydantic import BaseModel
import redis
import json
from datetime import datetime
from dotenv import load_dotenv
from os import getenv
from db_module.db_utilities import (
    run_single_query,
    retrieve_existing_usernames,
    retrieve_existing_accounts,
)

if getenv("DB_PASSWORD") is None:
    load_dotenv()

DB_USER = getenv("DB_USER")
DB_PASSWORD = getenv("DB_PASSWORD")
DB_DB_NAME = getenv("DB_DB_NAME")


app = FastAPI()
r = redis.Redis(host="localhost", port=6379, db=0)
# conn = psycopg2.connect(f"dbname={DB_DB_NAME} user={DB_USER} password={DB_PASSWORD}")


# Endpoint to ping server
@app.get("/")
def ping():
    return "Chat app server running"


# Endpoint to send messages
@app.post("/send_message/")
async def send_message(account_id: int, chat_room: str, content: str):
    message = {
        "account_id": account_id,
        "chat_room": chat_room,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
    }
    # Publish message to Redis channel
    r.publish(chat_room, json.dumps(message))

    # Store message in PostgreSQL
    run_single_query(
        query="INSERT INTO messages (user_id, chat_room, content) VALUES (%s, %s, %s)",
        values=(account_id, chat_room, content),
    )
    return {"status": "message sent"}


# Pydantic model for verification, eventually move to another file
class AccountCreate(BaseModel):
    username: str
    password: str


# Endpoint to create an account
@app.post("/create_account", status_code=status.HTTP_201_CREATED)
async def create_account(account: AccountCreate):
    try:
        usernames = [user[0] for user in retrieve_existing_usernames()]

        account.username = account.username.strip()

    except:
        raise HTTPException(500, "Database connection error")

    if account.username in usernames:
        raise HTTPException(409, "Username already exists")

    try:
        # Create account in database
        run_single_query(
            query="INSERT INTO users (username, password) VALUES (%s, %s)",
            values=(account.username, account.password),
        )
        return {"status": "account created"}

    except Exception as e:
        raise HTTPException(500, str(e))


# Endpoint to view all accounts
@app.get("/accounts")
def view_accounts():
    try:
        users = retrieve_existing_accounts()
        return users
    except Exception as e:
        raise HTTPException(500, f"Server Error: {e}")


# WebSocket endpoint
@app.websocket("/ws/{chat_room}")
async def websocket_endpoint(websocket: WebSocket, chat_room: str):
    await websocket.accept()
    pubsub = r.pubsub()
    pubsub.subscribe(chat_room)

    try:
        for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"].decode("utf-8"))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        pubsub.unsubscribe(chat_room)
        await websocket.close()
