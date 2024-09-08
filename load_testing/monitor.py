import time
import asyncio
import json
import traceback

from load_testing.virtual_user import User

class Monitor(User):
    def __init__(self, bearer_token: str, actions: int, test_channels: list, username: str = None, password: str = None,):
        super().__init__(bearer_token, actions, test_channels, username, password)
        self.perf_data: dict = {channel:{} for channel in self.test_channels}
        
        # Info to test/get from server:
        # message ping time
        # Server CPU load
        # Server memory usage
        # Server active accounts
        # Subscribers to that channel - ensure ping reply is sent to monitor after all other users in channel
        
    async def start_activity(self):
        # Join all channels, send message every X seconds, time how long until it returns. Maybe also join and leave channels and see how long it takes. Use a while True loop rather than X actions to ensure it is live throughout the entire test.
        pass
        self.perf_test_id = 0
        await self.match_test_channel_subscriptions()
        while self.connection_active:
            for channel in self.channels:
                self.send_perf_ping(channel)
                asyncio.sleep(1)

    async def send_perf_ping(self, channel):
        """Send a message to the server with a request for server stats, and to measure response times"""
        message = {
                "event": "perf_test",
                "channel": channel,
                "content": self.perf_test_id
            }
        self.perf_data[self.perf_test_id] = {"response_delay": time.perf_counter()}
        await self.client_websocket.send_message(message)
        self.perf_test_id += 1

    async def handle_perf_response(self, message: dict):
        """Handle the perf test response message and log the data"""
        perf_test_id = message.get("content")
        time_sent_at = self.perf_data[perf_test_id].get("response_delay")
        self.perf_data[perf_test_id] = {
            "response_delay": time.perf_counter() - time_sent_at,
            "server_cpu_load" : message.get("server_cpu_load"),
            "server_memory_usage" : message.get("server_memory_usage"),
            "total_active_connections" : message.get("total_active_connections"),
            "channel_active_connections" : message.get("channel_active_connections"),
            }


    async def listen_for_messages(self):
        """Listen for perf test response messages"""
        while self.connection_active:
            try:
                message_str = await self.client_websocket.websocket.recv()
                message: dict = json.loads(message_str)
                if message is not None:
                    event_type = message.get("event")
                    if event_type == "perf_test":
                        self.handle_perf_response(message)
            except asyncio.CancelledError:
                break  
            except Exception as e:
                if self.connection_active:
                    print(f"Error receiving message: {e}")
                    traceback.print_tb(e.__traceback__)
                else:
                    break 

    async def match_test_channel_subscriptions(self):
        """Ensure monitor is connected to all test channels, and no other channels"""
        for channel in set(self.test_channels).union(self.channels):
            if channel not in self.channels:
                await self.join_channel(channel)
            elif channel not in self.test_channels:
                await self.leave_channel(channel)


    def __repr__(self):
        return f"Monitor({self.bearer_token=}, {self.actions=}, {self.test_channels=}, {self.username=}, {self.password=})"