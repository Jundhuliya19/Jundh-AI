import sqlite3


DATABASE_NAME = "jundh_ai.db"


def get_db_connection():

    connection = sqlite3.connect(
        DATABASE_NAME
    )

    connection.row_factory = sqlite3.Row

    return connection


def create_database():

    connection = get_db_connection()


    # USERS TABLE

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            username TEXT UNIQUE NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)
    # CHATS TABLE

    connection.execute("""
        CREATE TABLE IF NOT EXISTS chats (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            title TEXT NOT NULL DEFAULT 'New Chat',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users (id)
                ON DELETE CASCADE

        )
    """)

    # MESSAGES TABLE

    connection.execute("""
        CREATE TABLE IF NOT EXISTS messages (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            role TEXT NOT NULL,

            message TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users (id)
                ON DELETE CASCADE

        )
    """)


        # ADD chat_id COLUMN TO EXISTING MESSAGES TABLE

    columns = connection.execute(
        "PRAGMA table_info(messages)"
    ).fetchall()

    column_names = [
        column[1]
        for column in columns
    ]

    if "chat_id" not in column_names:

        connection.execute(
            """
            ALTER TABLE messages
            ADD COLUMN chat_id INTEGER
            """
        )

            # MOVE OLD MESSAGES INTO A CHAT

    users_with_old_messages = connection.execute(
        """
        SELECT DISTINCT user_id
        FROM messages
        WHERE chat_id IS NULL
        """
    ).fetchall()

    for user_row in users_with_old_messages:

        user_id = user_row[0]

        cursor = connection.execute(
            """
            INSERT INTO chats (user_id, title)
            VALUES (?, ?)
            """,
            (
                user_id,
                "Previous Conversation"
            )
        )

        old_chat_id = cursor.lastrowid

        connection.execute(
            """
            UPDATE messages
            SET chat_id = ?
            WHERE user_id = ?
            AND chat_id IS NULL
            """,
            (
                old_chat_id,
                user_id
            )
        )
        
    connection.commit()

    connection.close()


if __name__ == "__main__":

    create_database()

    print(
        "Jundh AI database created successfully."
    )