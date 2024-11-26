import aiohttp
import asyncio
import random
from logging import Logger
from websockets import ConnectionClosedOK
from os import getenv

from dotenv import load_dotenv

from client.services.client_websocket import MyWebSocket
from load_testing.sample_words import sample_words

load_dotenv()

URL = "http://127.0.0.1:8000"
URL = getenv("URL")
WS_URL = "ws://127.0.0.1:8000"
WS_URL = getenv("WS_URL")
LOGIN_ENDPOINT = "/auth/token"

MAX_MESSAGE_LENGTH = 10


class WebsocketConnectionError(Exception):
    def __init__(self, logger, message):
        # TODO Flesh this out
        logger.warning(message)


class User:
    """Virtual user class. Uses provided credentials to login to server, then perform the specified number of actions before disconnecting. Actions are randomly chosen between sending a randomly generated message, joining a new channel, and leaving a current channel, weighted towards sending a message. This is to simulate real user activity as accurately as possible."""
    def __init__(
        self, logger: Logger,  account: dict, actions: int = 0, delay_before_actions: int = 0, delay_between_actions: int = 2, test_channels: list = [],  
    ):
        self.logger: Logger = logger
        self.actions: int = actions
        self.delay_before_actions: int = delay_before_actions
        self.delay_between_actions: int = delay_between_actions
        self.connection_active: bool = False
        self.test_channels: list = test_channels
        self.channels: list = []
        self.account = account
        self.username = self.account.get("username")
        self.logger.debug(self.account)
        self.listener_task = None
        
    async def authorize_account(self):
        """Use provided credentials to get a bearer token"""
        if "access_token" in self.account:
            self.bearer_token = self.account.get("access_token")
        else:
            self.username = self.account.get("username")
            self.password = self.account.get("password")
            self.bearer_token = await self.get_auth_token()
        self.logger.debug(f"{self.username}: Bearer token acquired: {self.bearer_token}")

    async def connect_websocket(self, max_retries=5, retry_delay=1):
        """Open websocket connection with retry mechanism"""
        for attempt in range(max_retries):
            try:
                await self.client_websocket.connect()
                self.connection_active = True
                if not self.listener_task:
                    self.listener_task = asyncio.create_task(self.listen_for_messages())
                return
            except Exception as e:
                self.logger.info(f"Connection attempt {attempt + 1} failed: {e.args=}, {e.__class__=}")
                # traceback.print_tb(e.__traceback__)
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
        raise WebsocketConnectionError(self.logger,
            f"Failed to connect after {max_retries} attempts"
        )

    async def get_auth_token(self) -> dict | None:
        """Submits username and password to get a bearer token from the server, repeats if unsuccessful"""
        try:
            payload = {
                "username": self.username,
                "password": self.password,
            }
            async with aiohttp.request('POST', f"{URL}{LOGIN_ENDPOINT}", data=payload) as response:
                response.raise_for_status()
                self.logger.debug(f"{self.username}: Auth token received!")
                return await response.json()
        except Exception as e:
            self.logger.info(f"{self.username}: Auth token request failed, retrying: {e}")
            await asyncio.sleep(2)
            return await self.get_auth_token()

    async def join_channel(self, channel_name):
        """Join the specified channel"""
        formatted_message = {
            "event": "add_channel",
            "channel": channel_name,
        }
        await self.send_message(formatted_message)

    async def send_message(self, message):
        """Send the provided message over the websocket"""
        if self.performing_actions:
            try:
                await self.client_websocket.send_message(message)
            except ConnectionClosedOK:
                self.performing_actions = False
            except ConnectionError:
                await self.connect_websocket()
                await self.send_message(message)
            except Exception as e:
                self.logger.info(f"User.send_message() {type(e).__name__}: {e}")


    async def leave_channel(self, channel_name):
        """Leave the specified channel"""

        formatted_message = {"event": "leave_channel", "channel": channel_name}
        await self.send_message(formatted_message)
        self.channels.remove(channel_name)

    async def start_activity(self):
        self.performing_actions = True
        await asyncio.sleep(self.delay_before_actions)
        for _ in range(self.actions):
            try:
                await self.choose_action()
                await asyncio.sleep(self.delay_between_actions)
            except Exception as e:
                self.logger.info(f"Error during activity: {type(e).__name__}: {e}")
        self.performing_actions = False

    async def choose_action(self):
        """Pick which action to perform"""
        # If user has no channel subscriptions, subscribe to a random selection
        if not self.channels:
            channels_to_add = random.sample(self.test_channels, random.randint(2, 6))
            self.logger.debug(f"No channel subscriptions, adding: {channels_to_add=}")
            for channel in channels_to_add:
                await self.join_channel(channel)
        # Generate a random number to decide the next action
        random_value = random.randint(0, 99)
        # 94% chance to send a message
        if random_value >= 6:
            await self.send_random_message()
        # 3% chance to join a new channel
        elif 5 >= random_value >= 3 and len(self.channels) < min(len(self.test_channels), 11):
            channel_name = random.choice(
                [
                    channel
                    for channel in self.test_channels
                    if channel not in self.channels
                ]
            )
            await self.join_channel(channel_name)
        # 3% chance to leave a channel
        elif len(self.channels) >= 4:
            channel_name = random.choice(self.channels)
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
            await self.send_message(message)

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


    async def listen_for_messages(self):
        while self.connection_active:
            try:
                message: dict = await self.client_websocket.receive_message()
                if message is not None:
                    event_type = message.get("event")
                    if event_type == "channel_subscriptions":
                        new_channels = message.get("data")
                        if isinstance(new_channels, list):
                            self.channels.extend(new_channels)
            except asyncio.CancelledError:
                break  
            except ConnectionClosedOK:
                await self.logout()
            except Exception as e:
                await self.logout()
                break


    async def run(self):
        """Initiate behavior - connect to websocket and start programmed actions"""
        await self.authorize_account()
        self.client_websocket: MyWebSocket = MyWebSocket(
            self.logger, 
            {"access_token": self.bearer_token.get("access_token")}, 
            self.username)
        try:
            await self.connect_websocket()
            await self.start_activity()
        except Exception as e:
            self.logger.info(f"Error during user run: {e}")
        finally:
            await self.logout()

    def __repr__(self):
        return f"User({self.actions=}, {self.username=}"