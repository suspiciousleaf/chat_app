import requests
import asyncio
import json
import random
import traceback

from os import getenv

from dotenv import load_dotenv

from client.services.client_websocket import MyWebSocket
from load_testing.sample_words import sample_words

load_dotenv()

URL = getenv("URL")
# URL = "http://127.0.0.1:8000"
WS_URL = getenv("WS_URL")
# WS_URL = "ws://127.0.0.1:8000"
LOGIN_ENDPOINT = "/auth/token"

MAX_MESSAGE_LENGTH = 10


class WebsocketConnectionError(Exception):
    def __init__(self, message):
        # TODO Flesh this out
        print(message)


class User:
    def __init__(
        self, bearer_token: str, actions: int, test_channels: list, username: str = None, password: str = None, 
    ):
        self.actions: int = actions
        self.connection_active: bool = False
        self.test_channels: list = test_channels
        self.channels: list = []
        self.bearer_token = {"access_token": bearer_token.replace("Bearer ", "")}
        # self.bearer_token: dict = self.get_auth_token()
        self.client_websocket: MyWebSocket = MyWebSocket(
            self.bearer_token)#, self.username)
        self.listener_task = None

    async def connect_websocket(self, max_retries=5, retry_delay=1):
        """Open websocket connection with retry mechanism"""
        for attempt in range(max_retries):
            try:
                await self.client_websocket.connect()
                self.connection_active = True
                self.listener_task = asyncio.create_task(self.listen_for_messages())
                return
            except Exception as e:
                print(f"Connection attempt {attempt + 1} failed: {e.args=}, {e.__class__=}")
                traceback.print_tb(e.__traceback__)
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
        raise WebsocketConnectionError(
            f"Failed to connect after {max_retries} attempts"
        )

    def get_auth_token(self) -> dict | None:
        """Submits username and password to get a bearer token from the server"""
        try:
            payload = {
                "username": self.username,
                "password": self.password,
            }
            response = requests.post(f"{URL}{LOGIN_ENDPOINT}", data=payload)
            response.raise_for_status()
            # print(f"{self.username}: Auth token received!")
            return response.json()

        except Exception as e:
            print(f"{self.username}: Auth token request failed: {e}")

    async def join_channel(self, channel_name):
        """Join the specified channel"""
        formatted_message = {
            "event": "add_channel",
            "channel": channel_name,
        }
        await self.client_websocket.send_message(formatted_message)


    async def leave_channel(self, channel_name):
        """Leave the specified channel"""

        formatted_message = {"event": "leave_channel", "channel": channel_name}
        await self.client_websocket.send_message(formatted_message)
        self.channels.remove(channel_name)

    async def start_activity(self):
        # print("Beginning actions")
        try:
            for i in range(self.actions):
                await self.choose_action(i)
                await asyncio.sleep(2)
        except Exception as e:
            print(f"Error during activity: {e}")
        # finally:
        #     print("Actions completed")

    async def choose_action(self, i):
        """Pick which action to perform"""
        # If user has no channel subscriptions, subscribe to a random selection
        if not self.channels:
            channels_to_add = random.sample(self.test_channels, random.randint(2, 6))
            for channel in channels_to_add:
                await self.join_channel(channel)
        # Generate a random number to decide the next action
        random_value = random.randint(0, 99)
        # 94% chance to send a message
        if random_value >= 6:
            # print(f"Action {i+1}. RandInt({random_value}). Sending random message")
            await self.send_random_message()
        # 3% chance to join a new channel
        elif 5 >= random_value >= 3 and len(self.channels) <= 11:
            channel_name = random.choice(
                [
                    channel
                    for channel in self.test_channels
                    if channel not in self.channels
                ]
            )
            # print(f"Action {i+1}. RandInt({random_value}). Joining channel: {channel_name}")
            await self.join_channel(channel_name)
        # 3% chance to leave a channel
        elif len(self.channels) >= 4:
            channel_name = random.choice(self.channels)
            # print(f"Action {i+1}. RandInt({random_value}). Leaving channel: {channel_name}")
            await self.leave_channel(channel_name)

    async def send_random_message(self):
        """Generate a random message and send it on a random channel"""
        if self.channels:
            message = {
                "event": "message",
                "channel": random.choice(self.channels),
                "content": " ".join(
                    random.sample(sample_words, random.randint(1, MAX_MESSAGE_LENGTH))
                ),
            }
            await self.client_websocket.send_message(message)

    async def logout(self):
        """Close the websocket connection and perform cleanup"""
        if self.connection_active:
            self.connection_active = False
            if self.listener_task:
                self.listener_task.cancel()
                try:
                    await self.listener_task
                except asyncio.CancelledError:
                    pass  # This is expected
            await self.client_websocket.close()
        # print("Logged out and disconnected")


    async def listen_for_messages(self):
        while self.connection_active:
            try:
                message_str = await self.client_websocket.websocket.recv()
                message: dict = json.loads(message_str)
                if message is not None:
                    event_type = message.get("event")
                    if event_type == "channel_subscriptions":
                        new_channels = message.get("data")
                        if isinstance(new_channels, list):
                            self.channels.extend(new_channels)
            except asyncio.CancelledError:
                break  
            except Exception as e:
                if self.connection_active:
                    print(f"Error receiving message: {e}")
                    traceback.print_tb(e.__traceback__)
                else:
                    break 

    async def run(self):
        try:
            await self.connect_websocket()
            await self.start_activity()
        except Exception as e:
            print(f"Error during user run: {e}")
        finally:
            await self.logout()
