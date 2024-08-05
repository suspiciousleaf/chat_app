import asyncio
import websockets
import time

WS_URL = "ws://127.0.0.1:8000"
WEBSOCKET_ENDPOINT = "/ws"


class MyWebSocket:
    def __init__(self, auth_token: dict):
        self.websocket_url: str = f"{WS_URL}{WEBSOCKET_ENDPOINT}"
        self.websocket: websockets = None
        self.new_message: str | None = None
        self.auth_token: dict = auth_token

    async def connect(self):
        try:
            extra_headers = {
                "Authorization": f"Bearer {self.auth_token.get('access_token', '')}"
            }
            self.websocket = await websockets.connect(
                self.websocket_url,
                ping_interval=20,
                ping_timeout=10,
                extra_headers=extra_headers,
            )
            print(f"Connected to WebSocket at {self.websocket_url}")
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"Invalid status code: {e.status_code}")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

        if not self.websocket:
            print("Connection failed. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
            await self.connect()

    # async def receive_messages(self):
    #     try:
    #         while True:
    #             self.new_message = await self.websocket.recv()
    #     except websockets.exceptions.ConnectionClosedError as e:
    #         print(f"WebSocket connection closed with error for {self.username}: {e}")
    #     except websockets.exceptions.ConnectionClosedOK as e:
    #         print(f"WebSocket connection closed normally for {self.username}: {e}")
    #     except asyncio.TimeoutError:
    #         print(f"Timeout error for {self.username}, trying to reconnect...")
