import requests
import asyncio
import json
import random
import time

from os import getenv

from dotenv import load_dotenv

from client.services.client_websocket import MyWebSocket

load_dotenv()

URL = getenv("URL")
WS_URL = getenv("WS_URL")
LOGIN_ENDPOINT = "/auth/token"

MAX_MESSAGE_LENGTH = 30
MESSAGES_TO_SEND = 10

sample_words = [
    "apple",
    "book",
    "car",
    "dream",
    "eagle",
    "forest",
    "garden",
    "hill",
    "ice",
    "jungle",
    "key",
    "lamp",
    "mountain",
    "night",
    "ocean",
    "pearl",
    "quartz",
    "river",
    "stone",
    "tree",
    "umbrella",
    "valley",
    "wind",
    "xylophone",
    "yarn",
    "zebra",
    "anchor",
    "breeze",
    "candle",
    "dance",
    "echo",
    "feather",
    "globe",
    "horizon",
    "island",
    "jewel",
    "kettle",
    "lighthouse",
    "moon",
    "nest",
    "owl",
    "puzzle",
    "quilt",
    "rain",
    "shadow",
    "tiger",
    "unicorn",
    "vase",
    "whale",
    "x-ray",
    "yellow",
    "zigzag",
    "arrow",
    "bottle",
    "cloud",
    "dust",
    "energy",
    "fire",
    "grape",
    "hammer",
    "ink",
    "jacket",
    "kite",
    "lemon",
    "mirror",
    "nut",
    "orange",
    "pencil",
    "quill",
    "rose",
    "star",
    "tunnel",
    "universe",
    "violet",
    "wolf",
    "xenon",
    "yacht",
    "zephyr",
    "bamboo",
    "circle",
    "dragon",
    "echoes",
    "flame",
    "grass",
    "honey",
    "isle",
    "jade",
    "knot",
    "leaf",
    "mist",
    "nebula",
    "octopus",
    "pine",
    "queen",
    "rope",
    "snow",
    "thorn",
    "utopia",
    "volcano",
    "whisper",
    "xenon",
]


class WebsocketConnectionError(Exception):
    def __init__(self):
        # TODO Flesh this out
        print("No websocket connection")


class User:
    def __init__(self, username: str, password: str, messages_to_send: int):
        self.username: str = username
        self.password: str = password
        self.messages_to_send: int = messages_to_send
        self.connection_active: bool = False
        self.channels: list = []
        self.bearer_token: dict = self.get_auth_token()
        self.client_websocket: MyWebSocket = self.open_websocket()
        self.start_activity()

    def open_websocket(self) -> MyWebSocket:
        """Open websocket connection"""
        if self.bearer_token:
            websocket: MyWebSocket = MyWebSocket(self.bearer_token)
            self.connection_active = True
            print("Websocket connected!")
            return websocket
        else:
            raise WebsocketConnectionError

    def get_auth_token(self) -> dict | None:
        """Submits username and password to get a bearer token from the server"""
        try:
            payload = {
                "username": self.username,
                "password": self.password,
            }
            response = requests.post(f"{URL}{LOGIN_ENDPOINT}", data=payload)
            response.raise_for_status()
            print("Auth token received!")
            return response.json()

        except Exception as e:
            print(f"Auth token request failed: {e}")

    def join_group(self):
        pass

    def leave_group(self):
        pass

    def start_activity(self):
        for _ in range(self.messages_to_send):
            self.send_message()
            time.sleep(1)

    # async def send_message(self):
    def send_message(self):
        """Generate a random message and send it on a random channel"""
        message = {
            "event": "message",
            "channel": random.choice(self.channels),
            "content": " ".join(
                random.sample(sample_words, random.randint(1, MAX_MESSAGE_LENGTH))
            ),
        }
        print(message)
        # await self.client_websocket.send_message(message)

    def logout(self):
        self.client_websocket.close()
        self.connection_active = False

    async def listen_for_messages(self):
        """Listen for incoming messages. Channel list will be updated, any other message will be ignored"""
        while self.connection_active:
            try:
                message_str = await asyncio.wait_for(
                    self.client_websocket.websocket.recv(), timeout=1.0
                )
                message: dict = self.decode_received_message(message_str)
                if message is not None:
                    event_type = message.get("event")
                    if event_type == "channel_subscriptions":
                        new_channels = message.get("data")
                        if isinstance(new_channels, list):
                            self.channels.extend(new_channels)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error receiving message: {e}")
                if not self.connection_active:
                    break
                await asyncio.sleep(5)

    def decode_received_message(self, message: str) -> dict:
        try:
            return json.loads(message)
        except json.JSONDecodeError:
            print(f"Could not decode message: {message}")
        except Exception as e:
            print(f"Unknown error occurred when decoding message: {e}")


User("username_1", "password_1", MESSAGES_TO_SEND)
