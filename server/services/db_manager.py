from os import getenv, path
import sqlite3
import json
from threading import local
from contextlib import contextmanager
import datetime

from dotenv import load_dotenv
from fastapi import status, HTTPException
from passlib.context import CryptContext

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
        """
        Initializes a `DatabaseManager` instance.

        Attributes:
            DB_NAME (str): Name of the database file, retrieved from environment variables.
            DB_FILEPATH (str): Absolute path to the database file.
            _local (threading.local): Thread-local storage for SQLite connections.

        Automatically initializes the database schema if it does not exist.
        """

        self.DB_NAME = DB_NAME
        # This is used to ensure a constant filepath for the database file inside the services directory, otherwise it changes based on the cwd
        self.DB_FILEPATH = self.create_db_filepath()
        self._local = local()
        self.init_database()

    @contextmanager
    def get_connection(self):
        """
        Context manager for retrieving a thread-local SQLite connection.

        Yields:
            sqlite3.Connection: A connection to the SQLite database.
            
        Notes:
            The connection is kept open for reuse and not closed automatically.
        """

        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.DB_FILEPATH)
        try:
            yield self._local.conn
        finally:
            pass  # We'll keep the connection open for reuse

    @contextmanager
    def get_cursor(self):
        """
        Context manager for retrieving a database cursor.

        Yields:
            sqlite3.Cursor: A cursor for executing SQL queries.
            
        Notes:
            The cursor is closed automatically after use.
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()

    def init_database(self) -> None:
        """Initializes the database schema by creating the required tables and indexes.

        Creates:
            - `users` table: Stores user data.
            - `messages` table: Stores chat messages.
            - `idx_messages_channel` index: Speeds up queries on the `messages` table by channel."""
        
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY UNIQUE NOT NULL,
            password_hashed TEXT NOT NULL,
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
            sent_at TEXT,
            FOREIGN KEY (username) REFERENCES users(username)
        );"""

        create_index_messages = "CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel);"

        with self.get_cursor() as cur:
            cur.execute(create_users_table)
            cur.execute(create_messages_table)
            cur.execute(create_index_messages)
            cur.connection.commit()

    def insert_query(self, query: str, values: dict) -> None:
        """
        Executes an INSERT SQL query.

        Args:
            query (str): The SQL query string.
            values (dict): Dictionary of parameters to bind to the query.

        Raises:
            Exception: Prints the error and rolls back the transaction on failure.
        """

        with self.get_cursor() as cur:
            try:
                cur.execute(query, values)
                cur.connection.commit()
            except Exception as e:
                cur.connection.rollback()
                print(f"Error in insert_query({query=}, {values=}): \n{e}")

    def select_query(self, query: str, values: dict | None = None) -> list:
        """
        Executes a SELECT SQL query.

        Args:
            query (str): The SQL query string.
            values (dict | None): Dictionary of parameters to bind to the query. Defaults to None.

        Returns:
            list: Query results as a list of tuples. Returns an empty list if an error occurs.
        """
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

    def batch_insert_messages(self, messages: list[dict]) -> None:
        """
        Inserts a batch of messages into the `messages` table as a single transaction.

        Args:
            messages (list[dict]): List of message dictionaries. Each dictionary must contain:
                - username (str)
                - channel (str)
                - content (str)
                - sent_at (str, ISO 8601 format)

        Raises:
            Exception: Prints the error and rolls back the transaction on failure.
        """

        with self.get_cursor() as cur:
            try:
                batch_insert_query = "INSERT INTO messages (username, channel, content, sent_at) VALUES (:username, :channel, :content, :sent_at)"
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
        """
        Fetches all usernames from the `users` table.

        Returns:
            set: A set of all usernames.
        """
        query = "SELECT username FROM users"
        usernames_raw = self.select_query(query=query)
        usernames: set = set(username[0] for username in usernames_raw)
        return usernames

    def create_account(self, username: str, password: str) -> dict | None:
        """
        Creates a new user account.

        Args:
            username (str): The desired username.
            password (str): The plaintext password.

        Returns:
            dict: Success message on account creation.
            None: If an error occurs during account creation.

        Raises:
            HTTPException: If the username already exists.
        """

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
        """
        Fetches all accounts from the `users` table.

        Returns:
            dict: A dictionary of accounts where keys are usernames, and values are account details.
        """

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
        """
        Fetches the channels a user is subscribed to.

        Args:
            username (str): The username of the user.

        Returns:
            set: A set of channel names.
        """

        query = "SELECT channels FROM users WHERE username = :username"
        values = {"username": username}
        channels_raw = self.select_query(query, values)
        channels_str: str = channels_raw[0][0] if channels_raw[0][0] else "[]"
        channels = set(json.loads(channels_str))
        return channels

    def retrieve_message_history(self, channels: set) -> list[dict]:
        """
        Fetches the message history for the specified channels.

        Args:
            channels (set): A set of channel names.

        Returns:
            list[dict]: List of message dictionaries, each containing:
                - username (str)
                - channel (str)
                - content (str)
                - sent_at (str)
        """
        placeholders = ",".join(["?" for _ in channels])
        query = f"SELECT username, channel, content, sent_at FROM messages WHERE channel in ({placeholders})"
        message_history_raw = self.select_query(query, list(channels))

        return [
            {
                "username": message[0],
                "channel": message[1],
                "content": message[2],
                "sent_at": message[3],
            }
            for message in message_history_raw
        ]

    def add_channel(self, username: str, channel: str) -> None:
        """
        Adds a channel to the list of channels a user is subscribed to.

        Args:
            username (str): The username of the user.
            channel (str): The channel to be added.
        """
        current_channels: set = self.retrieve_channels(username)

        if channel not in current_channels:
            current_channels.add(channel)

        channels_str = json.dumps(list(current_channels))
        self.update_query(
            "UPDATE users SET channels = :channels WHERE username = :username",
            {"channels": channels_str, "username": username},
        )

    def remove_channel(self, username: str, channel: str) -> None:
        """
        Removes a channel from the list of channels a user is subscribed to.

        Args:
            username (str): The username of the user.
            channel (str): The channel to be removed.
        """
        current_channels: set = self.retrieve_channels(username)

        if channel in current_channels:
            current_channels.remove(channel)

        channels_str = json.dumps(list(current_channels))
        self.update_query(
            "UPDATE users SET channels = :channels WHERE username = :username",
            {"channels": channels_str, "username": username},
        )

    def update_query(self, query: str, values: dict) -> None:
        """
        Executes an UPDATE SQL query.

        Args:
            query (str): The SQL query string.
            values (dict): Dictionary of parameters to bind to the query.

        Raises:
            Exception: Prints the error and rolls back the transaction on failure.
        """
        with self.get_cursor() as cur:
            try:
                cur.execute(query, values)
                cur.connection.commit()
            except Exception as e:
                cur.connection.rollback()
                print(f"Error in update_query({query=}, {values=}): \n{e}")

    def list_tables(self) -> list:
        """
        Fetches the names of all tables in the database.

        Returns:
            list: List of table names as tuples.
        """
        query = "SELECT name FROM sqlite_master WHERE type=:name;"
        values = {"name": "table"}
        tables: list = self.select_query(query, values)
        return tables

    def create_db_filepath(self) -> path:
        """
        Generates the absolute file path for the database.

        Returns:
            str: The absolute file path of the database file.
        """
        base_dir = path.dirname(path.abspath(__file__))
        return path.join(base_dir, "db_data", DB_NAME)

    def read_db_filepath(self) -> str:
        """
        Retrieves the file path of the current database connection.

        Returns:
            str: The database file path.
        """
        with self.get_connection() as conn:
            database_path = conn.execute("PRAGMA database_list").fetchone()[2]
            return f"Database file path: {database_path}"

    async def verify_connection_and_tables(self) -> dict:
        """
        Verifies the database connection and checks if the required tables exist.

        Returns:
            dict: A dictionary with:
                - "status" (bool): True if all checks pass, False otherwise.
                - "details" (str | None): Error details if checks fail.
        """
        required_tables = {"users", "messages"}
        try:
            with self.get_cursor() as cur:
                cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('users', 'messages');"
                )
                tables = cur.fetchall()

                existing_tables = {table[0] for table in tables}

                missing_tables = required_tables - existing_tables

                if not missing_tables:
                    return {"status": True, "details": None}
                else:
                    return {"status": False, "details": "table format error"}

        except sqlite3.Error:
            return {"status": False, "details": "database connection failed"}

        except Exception:
            return {"status": False, "details": "unexpected error"}

    def close_all(self):
        """
        Closes the thread-local database connection.
        """
        self._local.conn.close()

    @staticmethod
    def adapt_datetime_iso(val: datetime.datetime) -> str:
        """
        Converts a datetime object to a UTC ISO 8601 string.

        Args:
            val (datetime.datetime): The datetime object to convert.

        Returns:
            str: The ISO 8601 formatted string.
        """
        return val.astimezone(datetime.timezone.utc).isoformat()

    @staticmethod
    def convert_datetime(val: str) -> datetime.datetime:
        """
        Converts an ISO 8601 string to a datetime object.

        Args:
            val (str): The ISO 8601 string to convert.

        Returns:
            datetime.datetime: The resulting datetime object.
        """
        return datetime.datetime.fromisoformat(val)  # .decode()


# Create instance to be imported
db = DatabaseManager()

