import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "bot.db"


# --------------------
# CONNECTION / SETUP
# --------------------

def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:
        cur = conn.cursor()

        # USERS TABLE
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            afk INTEGER DEFAULT 0,
            shiny_enabled INTEGER DEFAULT 1,
            collection_enabled INTEGER DEFAULT 1
        )
        """)

        # SHINY HUNTS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS shiny_hunts (
            user_id INTEGER,
            pokemon TEXT,
            UNIQUE(user_id, pokemon)
        )
        """)

        # COLLECTIONS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS collections (
            user_id INTEGER,
            pokemon TEXT,
            UNIQUE(user_id, pokemon)
        )
        """)

        conn.commit()


# --------------------
# USER / FLAGS
# --------------------

def ensure_user(user_id: int):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO users
            (user_id, afk, shiny_enabled, collection_enabled)
            VALUES (?, 0, 1, 1)
            """,
            (user_id,)
        )
        conn.commit()


def set_afk(user_id: int, afk: bool):
    ensure_user(user_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET afk = ? WHERE user_id = ?",
            (1 if afk else 0, user_id)
        )
        conn.commit()


def is_afk(user_id: int) -> bool:
    ensure_user(user_id)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT afk FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cur.fetchone()
        return bool(row[0]) if row else False


def set_shiny_enabled(user_id: int, enabled: bool):
    ensure_user(user_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET shiny_enabled = ? WHERE user_id = ?",
            (1 if enabled else 0, user_id)
        )
        conn.commit()


def is_shiny_enabled(user_id: int) -> bool:
    ensure_user(user_id)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT shiny_enabled FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cur.fetchone()
        return bool(row[0]) if row else True


def set_collection_enabled(user_id: int, enabled: bool):
    ensure_user(user_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET collection_enabled = ? WHERE user_id = ?",
            (1 if enabled else 0, user_id)
        )
        conn.commit()


def is_collection_enabled(user_id: int) -> bool:
    ensure_user(user_id)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT collection_enabled FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cur.fetchone()
        return bool(row[0]) if row else True


# --------------------
# SHINY HUNTS
# --------------------

def add_shiny(user_id: int, pokemon: str):
    ensure_user(user_id)
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO shiny_hunts (user_id, pokemon) VALUES (?, ?)",
            (user_id, pokemon.lower())
        )
        conn.commit()


def remove_shiny(user_id: int, pokemon: str):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM shiny_hunts WHERE user_id = ? AND pokemon = ?",
            (user_id, pokemon.lower())
        )
        conn.commit()


def get_shinies(user_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT pokemon FROM shiny_hunts WHERE user_id = ?",
            (user_id,)
        )
        return [row[0] for row in cur.fetchall()]


def get_all_shiny_hunters(pokemon: str):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id FROM shiny_hunts WHERE pokemon = ?",
            (pokemon.lower(),)
        )
        return [row[0] for row in cur.fetchall()]


# --------------------
# COLLECTIONS
# --------------------

def add_collection(user_id: int, pokemon: str):
    ensure_user(user_id)
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO collections (user_id, pokemon) VALUES (?, ?)",
            (user_id, pokemon.lower())
        )
        conn.commit()


def remove_collection(user_id: int, pokemon: str):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM collections WHERE user_id = ? AND pokemon = ?",
            (user_id, pokemon.lower())
        )
        conn.commit()


def get_collections(user_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT pokemon FROM collections WHERE user_id = ?",
            (user_id,)
        )
        return [row[0] for row in cur.fetchall()]


def get_all_collectors(pokemon: str):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id FROM collections WHERE pokemon = ?",
            (pokemon.lower(),)
        )
        return [row[0] for row in cur.fetchall()]
