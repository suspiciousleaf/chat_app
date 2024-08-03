import asyncio
import websockets
import time

WS_URL = "ws://127.0.0.1:8000"
WEBSOCKET_ENDPOINT = "/ws/"


class MyWebSocket:
    def __init__(self, username):  # , manager):
        self.username: str = username
        self.websocket_url: str = f"{WS_URL}{WEBSOCKET_ENDPOINT}{self.username}"
        self.websocket: websockets = None
        self.new_message: str | None = None
        # self.manager = manager

    async def connect(self):
        # while True:
        try:
            self.websocket = await websockets.connect(
                self.websocket_url, ping_interval=20, ping_timeout=10
            )
            print(f"Connected to WebSocket at {self.websocket_url}")
            # await self.receive_messages()
        except websockets.exceptions.InvalidURI as e:
            print(f"Invalid WebSocket URI: {e}")
            # break
        except websockets.exceptions.InvalidHandshake as e:
            print(f"Invalid WebSocket handshake: {e}")
            # break
        except Exception as e:
            print(f"An error occurred: {e}")
        if not self.websocket:
            print("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
            # await self.connect()

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
