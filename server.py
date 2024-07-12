from fastapi import FastAPI, WebSocket, HTTPException
import redis
import json
from datetime import datetime
from dotenv import load_dotenv
from os import getenv
from db_module.db_utilities import run_single_query, retrieve_existing_usernames

if getenv("DB_PASSWORD") is None:
    load_dotenv()

DB_USER = getenv("DB_USER")
DB_PASSWORD = getenv("DB_PASSWORD")
DB_DB_NAME = getenv("DB_DB_NAME")


app = FastAPI()
r = redis.Redis(host="localhost", port=6379, db=0)
# conn = psycopg2.connect(f"dbname={DB_DB_NAME} user={DB_USER} password={DB_PASSWORD}")


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


# Endpoint to create account
@app.post("/create_account/")
async def create_account(username: str, password: str):
    account_info = {
        "username": username,
        "password": password,
    }

    usernames = retrieve_existing_usernames()
    if username in usernames:
        raise HTTPException(409, "Username already exists")

    # Create account in database
    run_single_query(
        query="INSERT INTO accounts (username, password) VALUES (%s, %s)",
        values=(username, password),
    )
    return {"status": "account created"}


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
