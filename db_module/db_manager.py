from os import getenv, path
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
        # This is used to ensure a constant filepath for the database file inside the db_module directory, otherwise it changes based on the cwd
        self.DB_FILEPATH = self.create_db_filepath()
        self._local = local()
        self.init_database()

    @contextmanager
    def get_connection(self):
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.DB_FILEPATH)
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

    def batch_insert_messages(self, messages: list[dict]):
        """Insert a batch of messages into the database as a single transaction.
        'messages' format:
        [{"username": username: str,
          "channel": channel: str,
          "content": content: str},
          {...}]
        """
        with self.get_cursor() as cur:
            try:
                batch_insert_query = "INSERT INTO messages (username, channel, content) VALUES (:username, :channel, :content)"
                cur.executemany(batch_insert_query, messages)
                cur.connection.commit()
                return True
            except Exception as e:
                cur.connection.rollback()
                print(
                    f"Error in batch_insert_messages({batch_insert_query=}, {messages=}): \n{e}"
                )
                return None

    def retrieve_existing_usernames(self) -> set:
        """Retrieve all account usernames"""
        query = "SELECT username FROM users"
        usernames_raw = self.select_query(query=query)
        usernames: set = set(username[0] for username in usernames_raw)
        return usernames

    def create_account(self, username: str, password: str) -> dict | None:
        """Create a new account"""

        username = username.strip()

        cur_usernames_query = "SELECT username FROM users WHERE username = :username"
        cur_usernames_values = {"username": username}

        cur_usernames = self.select_query(cur_usernames_query, cur_usernames_values)

        if cur_usernames:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists",
            )

        password_hashed = pwd_context.hash(password)
        try:
            # Create account in database
            create_account_query = "INSERT INTO users (username, password_hashed, channels) VALUES (:username, :password_hashed, :channels)"
            create_account_values = {
                "username": username,
                "password_hashed": password_hashed,
                "channels": json.dumps(["welcome"]),
            }

            self.insert_query(create_account_query, create_account_values)

            return {"status": "account created"}
        except Exception as e:
            print(f"Error in create_account({username=}, {password=}): \n{e}")
            return HTTPException(
                status_code=500, detail={"status": "Internal server error"}
            )

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
        print(f"{channels_raw=}")
        print(f"{channels_raw[0][0]=}")
        channels_str = channels_raw[0][0] if channels_raw[0][0] else '["welcome"]'
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

    # def batch_insert_messages(self, messages: list[dict]):
    #     """Insert a batch of messages in one operation"""
    #     with self.get_cursor() as cur:
    #         try:
    #             query = "INSERT INTO messages (username, channel, content) VALUES (:username, :channel, :content)"
    #             cur.executemany(query, messages)
    #             cur.connection.commit()
    #         except Exception as e:
    #             cur.connection.rollback()
    #             print(f"Error in batch_insert_messages({messages=}): \n{e}")

    def list_tables(self):
        query = "SELECT name FROM sqlite_master WHERE type=:name;"
        values = {"name": "table"}
        tables = self.select_query(query, values)
        return tables

    def create_db_filepath(self):
        base_dir = path.dirname(path.abspath(__file__))
        return path.join(base_dir, DB_NAME)

    def read_db_filepath(self):
        with self.get_connection() as conn:
            database_path = conn.execute("PRAGMA database_list").fetchone()[2]
            return f"Database file path: {database_path}"

    def close_all(self):
        self._local.conn.close()


# # Usage
# db = DatabaseManager()
# db.init_database()
# print(f"{db.list_tables()=}")
# print(db.read_db_filepath())
# print(db.retrieve_channels("username_1"))
