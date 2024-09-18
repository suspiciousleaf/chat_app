import requests
import asyncio
import json
import random
import time
from os import getenv
import csv
import aiohttp

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

async def get_auth_token(session: aiohttp.ClientSession, username, password) -> dict | None:
    """Submits username and password to get a bearer token from the server"""
    payload = {
        "username": username,
        "password": password,
    }
    async with session.post(f"{URL}{LOGIN_ENDPOINT}", data=payload) as response:
        response.raise_for_status()
        return await response.json()

async def process_account(session, username: str, password: str, tokens: list):
    """Processes a single account to get the token and handles exceptions."""
    try:
        token = await get_auth_token(session, username, password)
        tokens.append(token.get('access_token'))
    except Exception as e:
        try:
            await asyncio.sleep(1)
            token = await get_auth_token(session, username, password)
            tokens.append(token.get('access_token'))
        except:
            print(f"{username=}, {password=}, {e}")

async def create_bearer_token_csv():
    """Load the local accounts file and create those accounts on the server concurrently."""
    with open("load_testing/accounts.json", "r") as f:
        accounts = json.load(f)
    
    tokens = []
    
    t_whole = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        tasks = []
        for _, (username, password) in enumerate(accounts.items()):
            task = process_account(session, username, password, tokens)
            tasks.append(task)
    
        await asyncio.gather(*tasks)

    total_time = time.perf_counter() - t_whole

    print(f"{len(accounts)} tokens acquired in {total_time:.1f}s, av {(total_time / len(tokens))*1000:.1f}ms per token")
    
    with open("load_testing/accounts_tokens.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(("token",))
        for row in tokens:
            writer.writerow((row,))



def convert_accounts_json_to_csv():
    with open("load_testing/accounts.json", "r") as f:
        accounts = json.load(f)

    with open("load_testing/accounts.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(("username", "password"))
        writer.writerows(accounts.items())


# create_accounts_on_server_from_local_file()
# create_bearer_token_csv()
# asyncio.run(create_bearer_token_csv())

# Synchronous approx 200 ms per token, 198 s total, server CPU load ~70%
# Asynchronous approx 170 ms per token, 168s total, server CPU load ~92%