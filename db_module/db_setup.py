from psycopg2 import sql
from db_utilities import connect_to_database
from dotenv import load_dotenv
from os import getenv

if getenv("DB_USER") is None:

    load_dotenv()

DB_ROOT_USER = getenv("DB_ROOT_USER")
DB_ROOT_PASSWORD = getenv("DB_ROOT_PASSWORD")
DB_NAME = getenv("DB_NAME")
DB_USER = getenv("DB_USER")
DB_PASSWORD = getenv("DB_PASSWORD")


# Setup database commands
create_user = sql.SQL("CREATE USER {user} WITH PASSWORD {password}").format(
    user=sql.Identifier(DB_USER), password=sql.Literal(DB_PASSWORD)
)

create_database = sql.SQL("CREATE DATABASE {dbname} OWNER {owner}").format(
    dbname=sql.Identifier(DB_NAME), owner=sql.Identifier(DB_USER)
)

grant_privileges = sql.SQL(
    "GRANT ALL PRIVILEGES ON DATABASE {dbname} TO {user}"
).format(dbname=sql.Identifier(DB_NAME), user=sql.Identifier(DB_USER))


@connect_to_database
def build_database(db, cursor, commands):
    try:
        for command in commands:
            cursor.execute(command)

        db.commit()

        print("Database created successfully.")

    except Exception as error:
        print(f"Error: {error}")
        db.rollback()


build_database_commands = [create_user, create_database, grant_privileges]

# build_database(commands=build_database_commands)

# Create table statements
create_users_table = """
CREATE TABLE users (
    username VARCHAR(50) PRIMARY KEY UNIQUE NOT NULL,
    password_hashed VARCHAR(255) NOT NULL,
    disabled BOOLEAN DEFAULT FALSE,
    creation_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""

create_messages_table = """
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) REFERENCES users(username),
    channel VARCHAR(50),
    content TEXT,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""


@connect_to_database
def create_tables(db, cursor, commands):
    try:
        for command in commands:
            cursor.execute(command)

        db.commit()

        cursor.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        results = cursor.fetchall()
        if cursor:
            print("The following tables have been created")

        for result in results:
            print(result)

    except Exception as error:
        print(f"Error: {error}")
        db.rollback()


create_tables_commands = [create_users_table, create_messages_table]

create_tables(commands=create_tables_commands)
