import requests
import asyncio
import json
import random
import time
from os import getenv
import csv

from dotenv import load_dotenv
from sample_words import sample_words

load_dotenv()

URL = getenv("URL")
# URL = "http://127.0.0.1:8000"
WS_URL = getenv("WS_URL")
# WS_URL = "ws://127.0.0.1:8000"
LOGIN_ENDPOINT = "/auth/token"
CREATE_ACCOUNT_ENDPOINT = "/create_account"

# accounts = {username:password}


def create_accounts_local(num: int):
    """Create num * 100 accounts and save to a local json file"""
    accounts: dict = {}
    for word in sample_words:
        for i in range(num):
            account_string = f"{word}{i}"
            if len(account_string) < 6:
                account_string = f"{word.title()}{account_string.title()}"
            accounts[account_string] = account_string

    with open("load_testing/accounts.json", "w") as f:
        f.write(json.dumps(accounts))


def create_account_on_server(s: requests.Session, username: str, password: str):
    """Create an account on the server with the provided credentials"""
    account_info = {
        "username": username,
        "password": password,
    }

    response = s.post(f"{URL}{CREATE_ACCOUNT_ENDPOINT}", json=account_info)
    response.raise_for_status()


def create_accounts_on_server_from_local_file():
    """Load the local accounts file and create those accounts on the server"""
    with open("load_testing/accounts.json", "r") as f:
        accounts = json.load(f)
    s = requests.Session()
    i = 0
    for username, password in accounts.items():
        try:
            create_account_on_server(s, username, password)
        except Exception as e:
            print(f"{username=}, {password=}, {e}")
        i += 1
        if not i % 50:
            print(f"Account {i} processed")
    print(f"{len(accounts)} accounts created")


def convert_accounts_json_to_csv():
    with open("load_testing/accounts.json", "r") as f:
        accounts = json.load(f)

    with open("load_testing/accounts.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(("username", "password"))
        writer.writerows(accounts.items())


# create_accounts_on_server_from_local_file()
