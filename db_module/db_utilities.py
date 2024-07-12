from os import getenv
from dotenv import load_dotenv
import psycopg2

# Check of environment variables are loaded, and if not load them from .env. Also check if running locally or not, which changes some of the information.

if getenv("DB_USER") is None:

    load_dotenv()

DB_HOST = getenv("DB_HOST")
DB_PORT = getenv("DB_PORT")
DB_ROOT_USER = getenv("DB_ROOT_USER")
DB_ROOT_PASSWORD = getenv("DB_ROOT_PASSWORD")
DB_NAME = getenv("DB_NAME")
DB_USER = getenv("DB_USER")
DB_PASSWORD = getenv("DB_PASSWORD")


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
                with db.cursor() as cursor:
                    # kwargs for db and cursor to avoid conflicts with 'self'
                    results = original_func(db=db, cursor=cursor, *args, **kwargs)

        except psycopg2.Error as e:
            raise DatabaseConnectionError(f"Database connection error: {e}")

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

    except Exception as error:
        print(f"Error: {error}")
        db.rollback()


@connect_to_database
def retrieve_existing_usernames(db, cursor):
    """Retrieve all account ids"""
    try:
        cursor.execute("SELECT username FROM accounts")
        usernames = cursor.fetchall()

        return usernames

    except Exception as error:
        print(f"Error: {error}")
