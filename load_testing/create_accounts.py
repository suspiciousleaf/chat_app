import requests
import asyncio
import json
import random
import time
from os import getenv

from dotenv import load_dotenv
from sample_words import sample_words

load_dotenv()

URL = getenv("URL")
WS_URL = getenv("WS_URL")
LOGIN_ENDPOINT = "/auth/token"
CREATE_ACCOUNT_ENDPOINT = "/create_account"

# accounts = {username:{"password": password}}


def create_accounts_local(num: int):
    """Create num * 100 accounts and save to a local json file"""
    accounts: dict = {}
    for word in sample_words:
        for i in range(num):
            account = {
                "username": f"{word}{i}",
                "password": f"{word}{i}",
            }

            accounts[account["username"]] = {"password": account["password"]}

    with open("load_testing/accounts.json", "w") as f:
        f.write(json.dumps(accounts))


def create_account_on_server(username: str, password: str):
    """Create an account on the server with the provided credentials"""
    account_info = {
        "username": username,
        "password": password,
    }

    response = requests.post(f"{URL}{CREATE_ACCOUNT_ENDPOINT}", json=account_info)
    response.raise_for_status()


def create_accounts_on_server_from_local_file():
    """Load the local accounts file and create those accounts on the server"""
    with open("load_testing/accounts.json", "r") as f:
        accounts = json.load(f)
    i = 0
    for username, password in accounts.items():
        try:
            create_account_on_server(username, password["password"])
        except Exception as e:
            print(f"{username=}, {password['password']=}, {e}")
        i += 1
        if not i % 50:
            print(f"Account {i} created")
