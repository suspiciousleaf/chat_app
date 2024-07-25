from fastapi import FastAPI, WebSocket, HTTPException, status, Depends
from pydantic import BaseModel, Field
import redis
import json
from os import getenv

from dotenv import load_dotenv

from routers.auth import router as auth_router, User, get_current_active_user

from db_module.db_utilities import (
    send_message,
    retrieve_existing_accounts,
    create_account,
)

load_dotenv()

DB_USER = getenv("DB_USER")
DB_PASSWORD = getenv("DB_PASSWORD")
DB_DB_NAME = getenv("DB_DB_NAME")


app = FastAPI()
app.include_router(auth_router)
r = redis.Redis(host="localhost", port=6379, db=0)


# Endpoint to ping server
@app.get("/")
def ping():
    return "Chat app server running"


# Pydantic model for message verification, eventually move to another file
class MessageSend(BaseModel):
    channel: str
    content: str


# Endpoint to send messages
@app.post("/send_message", status_code=status.HTTP_201_CREATED)
async def send_message(
    message: MessageSend, current_user: User = Depends(get_current_active_user)
):

    try:
        message_dict = {
            "channel": message.channel,
            "username": current_user.username,
            "content": message.content,
        }

        # Publish message to Redis channel
        r.publish(message.channel, json.dumps(message_dict))
    except Exception as e:
        print(f"Unable to publish message on redis: {e}")

    try:
        # Store message in database
        # run_single_query(
        #     query="INSERT INTO messages (username, channel, content) VALUES (%s, %s, %s)",
        #     values=(current_user.username, message.channel, message.content),
        # )
        send_message(current_user.username, message.channel, message.content)
    except Exception as e:
        print(f"Unable to upload message to database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "Failed to send message"},
        )

    return {"status": "message sent"}


# Pydantic model for account verification, eventually move to another file
class AccountCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=255)


# Endpoint to create an account
@app.post("/create_account", status_code=status.HTTP_201_CREATED)
async def create_account_endpoint(account: AccountCreate):
    return create_account(account.username, account.password)


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
async def websocket_endpoint(
    websocket: WebSocket, channel: str
):  # , current_user: User = Depends(get_current_active_user)):
    print("Websocket connection requested")
    await websocket.accept()
    pubsub = r.pubsub()
    pubsub.subscribe(channel)
    r.publish(channel, f"Welcome user to '{channel}' channel")

    while True:

        try:
            # Deal with incoming messages
            incoming_message = await websocket.receive_text()
            print(f"{incoming_message = }")
            r.publish(channel, incoming_message)

            # Deal with outgoing messages
            for message in pubsub.listen():
                if message["type"] == "message":
                    await websocket.send_text(message["data"].decode("utf-8"))
        except Exception as e:
            print(f"Error: {e}")
    # finally:
    pubsub.unsubscribe(channel)
    await websocket.close()


#! Make a new file and go through server and client code on https://websockets.readthedocs.io/en/stable/ build up from there, try to maintain a stable connection
