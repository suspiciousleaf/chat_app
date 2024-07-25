from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
import json
import redis
import time

from routers.auth import router as auth_router
from db_module.db_utilities import retrieve_channels


app = FastAPI()

app.include_router(auth_router)

r = redis.Redis(host="localhost", port=6379, db=0)


# Endpoint to ping server
@app.get("/")
def ping():
    return "WS chat app server running"


# Possible format for messages on pubsub:
# {
#   "channel": "username_1",
#   "sender": "user123",
#   "content": "Hello, world!",
#   "timestamp": "2023-07-25T12:34:56Z"
# }


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str:WebSocket] = {}
        # TODO Add function to check length of self.message_store. If more than X messages, or more than Y time, upload messages to database in a batch, reset timer, and clear list.
        self.message_store = []
        self.time_since_message_backup = time.time()

    async def connect(self, websocket: WebSocket, username: str):
        # TODO Use GUI login to provide bearer token to client, use this to authorize the websocket connection and add logic here. Store tokens in Redis.
        print(f"Websocket connection requested for user: {username}")
        await websocket.accept()
        channels = retrieve_channels(username=username)
        self.active_connections[username] = {"ws": websocket, "channels": channels}

    async def disconnect(self, username: str):
        # TODO Could use this to send a 'user disconnected' message to the channel
        connection = self.active_connections.get(username)
        if connection:
            await connection["ws"].close()
            self.active_connections.pop(username, None)

    # async def send_message(self, message: str, username: str):
    #     websocket = self.active_connections.get(username)
    #     if websocket:
    #         await websocket.send_text(message)

    # async def broadcast_message(self, message: str):
    #     for username in self.active_connections:
    #         websocket = self.active_connections.get(username)
    #         if websocket:
    #             websocket.send_text(message)


ws_manager = ConnectionManager()


@app.websocket("/ws/{username}")
# TODO Move client_id and bearer token to header
async def websocket_endpoint(websocket: WebSocket, username: str):
    await ws_manager.connect(websocket, username)
    while True:
        try:
            data = await websocket.receive_text()
            r.publish("chat_messages", data)

            # Convert string to dict to upload into database in batches
            message = json.loads(data)
            ws_manager.message_store.append(message)

        except:
            break

    print("Disconnecting...")
    # await ws_manager.disconnect(username)

    # pubsub = r.pubsub()
    # pubsub.subscribe(channel)
    # r.publish(channel, f"Welcome user to '{channel}' channel")


#! Check FastAPI websockets docs https://fastapi.tiangolo.com/advanced/websockets/
