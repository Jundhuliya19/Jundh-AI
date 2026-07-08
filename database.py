import os
import psycopg
from psycopg.rows import dict_row


def get_db_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL environment variable is missing")

    connection = psycopg.connect(
        database_url,
        row_factory=dict_row
    )

    return connection


def create_database():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'New Chat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            chat_id INTEGER,

            role TEXT NOT NULL,
            message TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (chat_id)
                REFERENCES chats(id)
                ON DELETE CASCADE
        )
    """)

    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_database()
    print("Jundh AI PostgreSQL database created successfully.")