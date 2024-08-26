import json

from load_testing.virtual_user import User

ACTIONS = 200

test_channels = [f"test_{i}" for i in range(200)]

with open("load_testing/accounts.json", "r") as f:
    accounts = json.load(f)


class LoadTester:
    def __init__(self, num_accounts):
        self.num_accounts = num_accounts
        self.test_account_pool = accounts
        self.active_accounts = []
        self.create_users()

    def create_users(self):
        for username, password in accounts.items():
            if len(self.active_accounts) < self.num_accounts:
                user = User(username, password["password"], ACTIONS, test_channels)
                self.active_accounts.append(user)
                # break
            else:
                print(f"Breaking loop")
                break
