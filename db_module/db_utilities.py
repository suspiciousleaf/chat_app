from os import getenv
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import status, HTTPException
from passlib.context import CryptContext


load_dotenv()

CRYPTCONTEXT_SCHEME = getenv("CRYPTCONTEXT_SCHEME")
DB_HOST = getenv("DB_HOST")
DB_PORT = getenv("DB_PORT")
DB_ROOT_USER = getenv("DB_ROOT_USER")
DB_ROOT_PASSWORD = getenv("DB_ROOT_PASSWORD")
DB_NAME = getenv("DB_NAME")
DB_USER = getenv("DB_USER")
DB_PASSWORD = getenv("DB_PASSWORD")

pwd_context = CryptContext(schemes=[CRYPTCONTEXT_SCHEME], deprecated="auto")


class DatabaseConnectionError(Exception):
    """Custom error that is raised when connecting to the database fails"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# Decorator function
def connect_to_database(original_func):
    """Decorator function to connect to the database and run the function.

    Args:
        original_func (function): Function to run on the database
    """

    def make_connection(*args, **kwargs):
        results = None
        try:
            with psycopg2.connect(
                dbname=DB_NAME,
                user=DB_ROOT_USER,
                password=DB_ROOT_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
            ) as db:
                # Returns rows as RealDictRow, inherits from NamedTuple
                with db.cursor(cursor_factory=RealDictCursor) as cursor:
                    # kwargs for db and cursor to avoid conflicts with 'self'
                    results = original_func(db=db, cursor=cursor, *args, **kwargs)

        except psycopg2.Error as e:
            # Log actual error, return simple message
            raise DatabaseConnectionError(f"Database error")

        except Exception as e:
            raise DatabaseConnectionError(f"An unexpected error occurred: {e}")

        return results

    return make_connection


@connect_to_database
def run_single_query(db, cursor, query, values):
    """Function to run a single SQL query"""
    try:
        cursor.execute(query, values)
        db.commit()

    except Exception as e:
        db.rollback()
        raise e


def create_account(username: str, password: str) -> dict | None:
    """Create a new account"""

    try:
        usernames = retrieve_existing_usernames()
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
        run_single_query(
            query="INSERT INTO users (username, password_hashed) VALUES (%s, %s)",
            values=(username, password_hashed),
        )
        return {"status": "account created"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@connect_to_database
def retrieve_existing_usernames(db, cursor) -> set:
    """Retrieve all account usernames"""

    cursor.execute("SELECT username FROM users")
    usernames_raw = cursor.fetchall()

    usernames: set = {user["username"] for user in usernames_raw}

    return usernames


@connect_to_database
def retrieve_existing_accounts(db, cursor):
    """Retrieve all accounts"""

    cursor.execute("SELECT username, password_hashed, disabled FROM users")
    users = cursor.fetchall()

    accounts = {user["username"]: dict(user) for user in users}

    return accounts


@connect_to_database
def retrieve_channels(db, cursor, username: str) -> set | None:

    # Change cursor to not return a dict, as only one channel is being retrieved
    cursor = db.cursor()
    query = "SELECT channels FROM users WHERE username = %s"

    cursor.execute(query, (username,))

    channels = cursor.fetchone()[0]

    return set(channels)


async def send_message(username, channel, content):
    return run_single_query(
        query="INSERT INTO messages (username, channel, content) VALUES (%s, %s, %s)",
        values=(username, channel, content),
    )
