import json
import asyncio
import threading
import random
import csv

from load_testing.virtual_user import User

test_channels = [f"test_{i}" for i in range(10)]

# with open("C:/Users/David/Documents/Programming/Python/Code_list/Projects/chat_app/chat_app/load_testing/accounts.json", "r") as f:
#     accounts: dict = json.load(f)

with open("C:/Users/David/Documents/Programming/Python/Code_list/Projects/chat_app/chat_app/load_testing/accounts_tokens.csv", "r") as f:
    accounts = [row["token"] for row in csv.DictReader(f)]



class LoadTester:
    def __init__(self, num_accounts, num_actions, connection_delay=1):
        self.num_accounts = num_accounts
        self.test_account_pool: list = accounts
        self.active_accounts = []
        self.num_actions = num_actions
        self.loop = asyncio.get_event_loop()
        self.connection_delay = connection_delay

    async def create_and_run_user(self, token): #username, password):
        """Create, connect, and run a single user"""
        # user = User(self.loop, username, password, self.num_actions, test_channels)
        user = User(self.loop, token, actions=self.num_actions, test_channels=test_channels)
        self.active_accounts.append(user)

        try:
            await user.connect_websocket()
            print(f"Connected successfully")
            await asyncio.gather(
                # user.listen_for_messages(),
                asyncio.to_thread(user.start_activity),
            )
        except Exception as e:
            print(f"Failed to connect or run - {e}")
        finally:
            self.active_accounts.remove(user)

    async def run_load_test(self):
        """Create and run multiple users with a delay between connections"""
        accounts_to_use = random.sample(
            sorted(self.test_account_pool), self.num_accounts
        )
        tasks = []
        for account in accounts_to_use:
            task = asyncio.create_task(
                self.create_and_run_user(account)#, self.test_account_pool[account])
            )
            tasks.append(task)
            await asyncio.sleep(self.connection_delay)

        await asyncio.gather(*tasks)

    def start(self):
        """Run the load test"""
        self.loop.run_until_complete(self.run_load_test())
