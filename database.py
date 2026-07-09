import os
import psycopg
from psycopg.rows import dict_row


def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is missing")
    return psycopg.connect(database_url, row_factory=dict_row)


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
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL DEFAULT 'New Chat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            chat_id INTEGER REFERENCES chats(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS document_contexts (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
            document_name TEXT,
            document_text TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, chat_id)
        )
    """)

    connection.commit()
    connection.close()


def save_document_context(user_id, chat_id, document_name, document_text):
    connection = get_db_connection()
    connection.execute("""
        INSERT INTO document_contexts
            (user_id, chat_id, document_name, document_text, updated_at)
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id, chat_id)
        DO UPDATE SET
            document_name = EXCLUDED.document_name,
            document_text = EXCLUDED.document_text,
            updated_at = CURRENT_TIMESTAMP
    """, (user_id, chat_id, document_name, document_text))
    connection.commit()
    connection.close()


def get_document_context(user_id, chat_id):
    connection = get_db_connection()
    row = connection.execute("""
        SELECT document_name, document_text
        FROM document_contexts
        WHERE user_id = %s AND chat_id = %s
    """, (user_id, chat_id)).fetchone()
    connection.close()
    return row


if __name__ == "__main__":
    create_database()
    print("NAHOR PostgreSQL database initialized successfully.")
