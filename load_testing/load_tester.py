import json
import asyncio
import threading
import random

from load_testing.virtual_user import User

test_channels = [f"test_{i}" for i in range(10)]

with open("load_testing/accounts.json", "r") as f:
    accounts: dict = json.load(f)


class LoadTester:
    def __init__(self, num_accounts, num_actions):
        self.num_accounts = num_accounts
        self.test_account_pool: dict = accounts
        self.active_accounts = []
        self.num_actions = num_actions
        self.loop = asyncio.new_event_loop()
        self.start()

    def run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.create_users())

    async def create_user(self, username, password):
        """Create and start a single user"""
        user = User(self.loop, username, password, self.num_actions, test_channels)
        self.active_accounts.append(user)

        await asyncio.gather(
            user.listen_for_messages(),
            asyncio.to_thread(user.start_activity),
        )

    async def create_users(self):
        """Create and start multiple users concurrently"""
        tasks = []
        accounts_to_use = random.sample(
            sorted(self.test_account_pool), self.num_accounts
        )
        for account in accounts_to_use:
            tasks.append(self.create_user(account, self.test_account_pool[account]))
        await asyncio.gather(*tasks)

    def start(self):
        """Run the load test"""
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.create_users())
