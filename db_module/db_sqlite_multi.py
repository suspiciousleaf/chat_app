from os import getenv
from dotenv import load_dotenv
from fastapi import status, HTTPException
from passlib.context import CryptContext
import sqlite3
import json
from threading import local
from contextlib import contextmanager

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
        self._local = local()

    @contextmanager
    def get_connection(self):
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.DB_NAME)
        try:
            yield self._local.conn
        finally:
            pass  # We'll keep the connection open for reuse

    @contextmanager
    def get_cursor(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()

    def init_database(self):
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY UNIQUE NOT NULL,
            password_hashed TEXT NOT NULL,
            --salt TEXT NOT NULL,
            disabled BOOLEAN DEFAULT 0,
            channels TEXT,
            creation_date DATETIME DEFAULT CURRENT_TIMESTAMP
        );"""

        create_messages_table = """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            channel TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users(username)
        );"""

        with self.get_cursor() as cur:
            cur.execute(create_users_table)
            cur.execute(create_messages_table)
            cur.connection.commit()

    def insert_query(self, query: str, values: dict):
        """Function to run an INSERT SQL query"""
        with self.get_cursor() as cur:
            try:
                cur.execute(query, values)
                cur.connection.commit()
            except Exception as e:
                cur.connection.rollback()
                print(f"Error in insert_query({query=}, {values=}): \n{e}")

    def select_query(self, query: str, values: dict | None = None) -> list:
        """Function to run a SELECT query"""
        with self.get_cursor() as cur:
            try:
                if values:
                    cur.execute(query, values)
                else:
                    cur.execute(query)
                return cur.fetchall()
            except Exception as e:
                print(f"Error in select_query({query=}, {values=}): \n{e}")
                return []

    def retrieve_existing_usernames(self) -> set:
        """Retrieve all account usernames"""
        query = "SELECT username FROM users"
        usernames_raw = self.select_query(query=query)
        usernames: set = set(username[0] for username in usernames_raw)
        return usernames

    def create_account(self, username: str, password: str) -> dict | None:
        """Create a new account"""
        username = username.strip()

        with self.get_cursor() as cur:
            try:
                # Check if username already exists
                cur.execute(
                    "SELECT username FROM users WHERE username = ?", (username,)
                )
                if cur.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Username already exists",
                    )

                # Hash password
                password_hashed = pwd_context.hash(password)

                # Create account in database
                cur.execute(
                    "INSERT INTO users (username, password_hashed) VALUES (?, ?)",
                    (username, password_hashed),
                )
                cur.connection.commit()
                return {"status": "account created"}

            except sqlite3.Error as e:
                cur.connection.rollback()
                print(f"Error in create_account({username=}, {password=}): \n{e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve_existing_accounts(self) -> dict:
        """Retrieve all accounts"""
        users = self.select_query(
            "SELECT username, password_hashed, disabled FROM users"
        )
        accounts = {
            user[0]: {
                "username": user[0],
                "password_hashed": user[1],
                "disabled": bool(user[2]),
            }
            for user in users
        }
        return accounts

    def retrieve_channels(self, username: str) -> set:
        """Retrieve all channels that a user is subscribed to"""
        query = "SELECT channels FROM users WHERE username = :username"
        values = {"username": username}
        channels_raw = self.select_query(query, values)
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
        with self.get_cursor() as cur:
            try:
                cur.execute(query, values)
                cur.connection.commit()
            except Exception as e:
                cur.connection.rollback()
                print(f"Error in update_query({query=}, {values=}): \n{e}")

    def batch_insert_messages(self, messages: list[dict]):
        """Insert a batch of messages in one operation"""
        with self.get_cursor() as cur:
            try:
                query = "INSERT INTO messages (username, channel, content) VALUES (:username, :channel, :content)"
                cur.executemany(query, messages)
                cur.connection.commit()
            except Exception as e:
                cur.connection.rollback()
                print(f"Error in batch_insert_messages({messages=}): \n{e}")

    def list_tables(self):
        query = "SELECT name FROM sqlite_master WHERE type=:name;"
        values = {"name": "table"}
        tables = self.select_query(query, values)
        return tables

    def close_all(self):
        self._local.conn.close()


# Usage
db = DatabaseManager()
# db.init_database()
print(db.retrieve_channels("username_1"))
