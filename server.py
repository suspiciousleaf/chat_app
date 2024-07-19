from fastapi import FastAPI, WebSocket, HTTPException, status
from pydantic import BaseModel
import redis
import json
from os import getenv

from dotenv import load_dotenv

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


# Pydantic model for message verification, eventually move to another file
class MessageSend(BaseModel):
    username: str
    password: str
    channel: str
    content: str


# Endpoint to send messages
@app.post("/send_message", status_code=status.HTTP_201_CREATED)
async def send_message(message: MessageSend):

    try:
        # Publish message to Redis channel
        r.publish(message.channel, json.dumps(message.content))
    except Exception as e:
        print(f"Unable to publish message: {e}")

    accounts = retrieve_existing_accounts()

    id = None

    for account in accounts:
        if (message.username, message.password) == account[1:]:
            id = account[0]

    if id is None:
        raise HTTPException(401, "Unauthorized account")

    try:
        # Store message in database
        run_single_query(
            query="INSERT INTO messages (user_id, channel, content) VALUES (%s, %s, %s)",
            values=(id, message.channel, message.content),
        )
    except Exception as e:
        print(f"Unable to upload message to database: {e}")
        return {"status": "message failed"}

    return {"status": "message sent"}


# Pydantic model for account verification, eventually move to another file
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
@app.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str):
    print("Websocket connection requested")
    await websocket.accept()
    pubsub = r.pubsub()
    pubsub.subscribe(channel)
    r.publish(channel, f"Welcome user to '{channel}' channel")

    try:
        for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"].decode("utf-8"))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        pubsub.unsubscribe(channel)
        await websocket.close()
