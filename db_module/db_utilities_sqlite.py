from os import getenv
from dotenv import load_dotenv
from fastapi import status, HTTPException
from passlib.context import CryptContext
import sqlite3
import json


load_dotenv()

CRYPTCONTEXT_SCHEME = getenv("CRYPTCONTEXT_SCHEME")
DB_NAME = getenv("DB_NAME")

pwd_context = CryptContext(schemes=[CRYPTCONTEXT_SCHEME], deprecated="auto")


class DatabaseConnectionError(Exception):
    """Custom error that is raised when connecting to the database fails"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class DatabaseManager:
    def __init__(self):
        self.DB_NAME = DB_NAME
        self.conn: sqlite3.Connection | None = None
        self.cur: sqlite3.Cursor | None = None
        self.connect()
        self.get_cursor()

    def connect(self):
        try:
            self.conn = sqlite3.connect(self.DB_NAME)
        except Exception as e:
            raise DatabaseConnectionError(e)

    def get_cursor(self):
        self.cur = self.conn.cursor()

    def insert_query(self, query: str, values: dict):
        """Function to run an INSERT SQL query"""
        try:
            self.cur.execute(query, values)
            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            print(f"Error in insert_query({query=}, {values=}): \n{e}")

    def select_query(self, query: str, values: dict | None = None) -> list:
        """Function to run a SELECT query"""
        try:
            if values:
                self.cur.execute(query, values)
            else:
                self.cur.execute(query)
            return self.cur.fetchall()
        except Exception as e:
            print(f"Error in select_query({query=}, {values=}): \n{e}")
            return []

    def retrieve_existing_usernames(self) -> set:
        """Retrieve all account usernames"""

        query = "SELECT username FROM users"

        usernames_raw = self.select_query(query=query)
        usernames: set = set(usernames_raw)
        return usernames

    def create_account(self, username: str, password: str) -> dict | None:
        """Create a new account"""

        try:
            usernames = self.retrieve_existing_usernames()
        except:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to retrieve existing usernames",
            )

        username = username.strip()

        if username in usernames:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
            )

        try:
            # Hash password
            password_hashed = pwd_context.hash(password)

            # Create account in database
            self.insert_query(
                query="INSERT INTO users (username, password_hashed) VALUES (:username, :password_hashed)",
                values=(username, password_hashed),
            )
            return {"status": "account created"}

        except Exception as e:
            print(f"Error in create_account({username=}, {password_hashed=}): \n{e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve_existing_accounts(self) -> dict:
        """Retrieve all accounts"""

        users = self.select_query(
            "SELECT username, password_hashed, disabled FROM users"
        )
        print(users)

        accounts = {
            user[0]: {
                "username": user[0],
                "password_hashed": user[1],
                "disabled": bool(user[2]),
            }
            for user in users
        }

        print(accounts)

        return accounts

    # def retrieve_channels(self, username: str) -> set:
    #     """Retrieve all channels that a user is subscribed to"""
    #     query = "SELECT channels FROM users WHERE username = :username"
    #     values = {"username": username}
    #     channels_str = self.select_query(query, values)

    #     channels = set(json.loads(channels_str))

    #     return channels

    def retrieve_channels(self, username: str) -> set:
        """Retrieve all channels that a user is subscribed to"""
        query = "SELECT channels FROM users WHERE username = :username"
        values = {"username": username}
        channels_raw = self.select_query(query, values)
        print(f"{channels_raw=}")
        channels_str = channels_raw[0][0] if channels_raw else "[]"
        channels = set(json.loads(channels_str))

        return channels

    def update_channels(self, username: str, channel: str):
        """Update a user's subscribed channels, add if absent, remove if present"""
        current_channels = self.retrieve_channels(username)

        if channel in current_channels:
            current_channels.remove(channel)
        else:
            current_channels.add(channel)

        channels_str = json.dumps(list(current_channels))
        self.update_query(
            "UPDATE users SET channels = :channels WHERE username = :username",
            {"channels": channels_str, "username": username},
        )

    def update_query(self, query: str, values: dict):
        """Function to run an UPDATE query"""
        try:
            self.cur.execute(query, values)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"Error in update_query({query=}, {values=}): \n{e}")

    def batch_insert_messages(self, messages: list[dict]):
        """Insert a batch of messages in one operation"""
        try:
            query = "INSERT INTO messages (username, channel, content) VALUES (:username, :channel, :content)"

            self.cur.executemany(query, messages)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"Error in batch_insert_messages({messages=}): \n{e}")

    def list_tables(self):
        query = "SELECT name FROM sqlite_master WHERE type=:name;"
        values = {"name": "table"}
        tables = self.select_query(query, values)
        return tables


# db = DatabaseManager()
# print(db.list_tables())
