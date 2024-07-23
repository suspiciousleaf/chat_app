from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status

from routers.auth import router as auth_router


app = FastAPI()

app.include_router(auth_router)


# Endpoint to ping server
@app.get("/")
def ping():
    return "Chat app server running"


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str:WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        # TODO Use GUI login to provide bearer token to client, use this to authorize the websocket connection and add logic here. Store tokens in Redis.
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        # TODO Could use this to send a 'user disconnected' message to the channel
        self.active_connections.pop(client_id, None)

    async def send_message(self, message: str, client_id: str):
        websocket = self.active_connections.get(client_id)
        if websocket:
            await websocket.send_text(message)


manager = ConnectionManager()


@app.websocket("/ws/{client_id}")
# TODO Move client_id and bearer token to header
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages

    except WebSocketDisconnect:
        manager.disconnect(client_id)


#! Check FastAPI websockets docs https://fastapi.tiangolo.com/advanced/websockets/
