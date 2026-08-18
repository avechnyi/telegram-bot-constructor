import sqlite3
import threading


DB_PATH = "constructor.db"

db_lock = threading.Lock()


def get_connection():
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_database():

    with db_lock:

        conn = get_connection()

        try:

            conn.execute("""
                CREATE TABLE IF NOT EXISTS bots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    username TEXT,
                    token TEXT NOT NULL UNIQUE,
                    enabled INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id INTEGER NOT NULL,
                    telegram_id INTEGER NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                    UNIQUE(bot_id, telegram_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id INTEGER NOT NULL,
                    telegram_id INTEGER NOT NULL,
                    event TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

        finally:

            conn.close()


def add_bot(
    name,
    username,
    token
):

    with db_lock:

        conn = get_connection()

        try:

            cursor = conn.execute("""
                INSERT INTO bots (
                    name,
                    username,
                    token
                )
                VALUES (?, ?, ?)
            """, (
                name,
                username,
                token
            ))

            conn.commit()

            return cursor.lastrowid

        finally:

            conn.close()


def get_bots():

    conn = get_connection()

    try:

        return conn.execute("""
            SELECT *
            FROM bots
            ORDER BY id DESC
        """).fetchall()

    finally:

        conn.close()


def get_bot(bot_id):

    conn = get_connection()

    try:

        return conn.execute("""
            SELECT *
            FROM bots
            WHERE id = ?
        """, (
            bot_id,
        )).fetchone()

    finally:

        conn.close()


def add_user(
    bot_id,
    telegram_id,
    username,
    first_name
):

    with db_lock:

        conn = get_connection()

        try:

            conn.execute("""
                INSERT OR IGNORE INTO users (
                    bot_id,
                    telegram_id,
                    username,
                    first_name
                )
                VALUES (?, ?, ?, ?)
            """, (
                bot_id,
                telegram_id,
                username,
                first_name
            ))

            conn.commit()

        finally:

            conn.close()


def add_event(
    bot_id,
    telegram_id,
    event
):

    with db_lock:

        conn = get_connection()

        try:

            conn.execute("""
                INSERT INTO events (
                    bot_id,
                    telegram_id,
                    event
                )
                VALUES (?, ?, ?)
            """, (
                bot_id,
                telegram_id,
                event
            ))

            conn.commit()

        finally:

            conn.close()


def bot_statistics(bot_id):

    conn = get_connection()

    try:

        users = conn.execute("""
            SELECT COUNT(*) AS count
            FROM users
            WHERE bot_id = ?
        """, (
            bot_id,
        )).fetchone()["count"]

        starts = conn.execute("""
            SELECT COUNT(*) AS count
            FROM events
            WHERE bot_id = ?
            AND event = 'start'
        """, (
            bot_id,
        )).fetchone()["count"]

        details = conn.execute("""
            SELECT COUNT(*) AS count
            FROM events
            WHERE bot_id = ?
            AND event = 'details'
        """, (
            bot_id,
        )).fetchone()["count"]

        curator = conn.execute("""
            SELECT COUNT(*) AS count
            FROM events
            WHERE bot_id = ?
            AND event = 'curator'
        """, (
            bot_id,
        )).fetchone()["count"]

        return {
            "users": users,
            "starts": starts,
            "details": details,
            "curator": curator
        }

    finally:

        conn.close()
