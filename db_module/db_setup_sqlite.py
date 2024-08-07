import sqlite3
from dotenv import load_dotenv
from os import getenv

load_dotenv()
DB_NAME = getenv("DB_NAME")

conn = sqlite3.connect(DB_NAME)

cur = conn.cursor()


def create_tables(cur, create_tables_commands):
    for command in create_tables_commands:
        cur.execute(command)


create_users_table = """
CREATE TABLE users (
    username TEXT PRIMARY KEY UNIQUE NOT NULL,
    password_hashed TEXT NOT NULL,
    --salt TEXT NOT NULL,
    disabled BOOLEAN DEFAULT 0,
    channels TEXT,
    creation_date DATETIME DEFAULT CURRENT_TIMESTAMP
);"""

create_messages_table = """
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    channel TEXT,
    content TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (username) REFERENCES users(username)
);"""

create_tables_commands = [create_users_table, create_messages_table]
create_tables(cur, create_tables_commands)
