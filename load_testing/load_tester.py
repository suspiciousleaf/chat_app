import json
import asyncio
import threading
import random
import csv
import logging
from os import getenv
from dotenv import load_dotenv

from load_testing.virtual_user import User

test_channels = [f"test_{i}" for i in range(10)]


# with open("load_testing/accounts.json", "r") as f:
#     accounts: dict = json.load(f)

with open("load_testing/accounts_tokens.csv", "r") as f:
    accounts = [row["token"] for row in csv.DictReader(f)]



class LoadTester:
    def __init__(self, logger: logging.Logger, num_accounts, num_actions, connection_delay=None):
        self.logger = logger
        self.num_accounts = num_accounts
        self.test_account_pool: list = accounts
        self.active_accounts = []
        self.num_actions = num_actions
        self.connection_delay: float | None = connection_delay
        self.logger.info(f"Starting: {str(self)}")

    def __repr__(self):
        return f"LoadTester({self.num_accounts=}, {self.num_actions=}, {self.connection_delay=})"

    async def create_and_run_user(self, token):
        user = User(token, actions=self.num_actions, test_channels=test_channels)
        self.active_accounts.append(user)
        try:
            await user.run()
        except Exception as e:
            print(f"Error running user: {e}")
        finally:
            self.active_accounts.remove(user)

    async def run_load_test(self):
        accounts_to_use = random.sample(sorted(self.test_account_pool), self.num_accounts)
        tasks = []
        for account in accounts_to_use:
            task = asyncio.create_task(self.create_and_run_user(account))
            tasks.append(task)
            if self.connection_delay:
                await asyncio.sleep(self.connection_delay)
        await asyncio.gather(*tasks)

    def start(self):
        asyncio.run(self.run_load_test())
        self.logger.info(f"LoadTester complete")
