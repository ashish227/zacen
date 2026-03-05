"""
utils/database.py

Single persistent connection, WAL mode, thread lock for async safety.
Tables: users, shiny_hunts (single per user), collections, role_pings, channel_settings
"""

import sqlite3
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "bot.db"

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()


def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA synchronous=NORMAL")
    return _conn


def init_db():
    with _lock:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            afk INTEGER DEFAULT 0,
            shiny_enabled INTEGER DEFAULT 1,
            collection_enabled INTEGER DEFAULT 1,
            role_ping_enabled INTEGER DEFAULT 1
        )""")

        # Single shiny hunt per user — UNIQUE on user_id only
        cur.execute("""
        CREATE TABLE IF NOT EXISTS shiny_hunts (
            user_id INTEGER PRIMARY KEY,
            pokemon TEXT NOT NULL
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS collections (
            user_id INTEGER,
            pokemon TEXT,
            UNIQUE(user_id, pokemon)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS role_pings (
            guild_id INTEGER,
            role_id INTEGER,
            pokemon TEXT,
            UNIQUE(guild_id, role_id, pokemon)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS channel_settings (
            channel_id INTEGER PRIMARY KEY,
            pings_enabled INTEGER DEFAULT 1
        )""")

        # Indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_shiny_pokemon ON shiny_hunts(pokemon)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_collection_pokemon ON collections(pokemon)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_role_pings_pokemon ON role_pings(pokemon)")

        conn.commit()
        print("[DB] Initialized")


# --------------------
# USER / FLAGS
# --------------------

def ensure_user(user_id: int):
    with _lock:
        get_connection().execute(
            "INSERT OR IGNORE INTO users (user_id, afk, shiny_enabled, collection_enabled, role_ping_enabled) VALUES (?, 0, 1, 1, 1)",
            (user_id,)
        )
        get_connection().commit()


def set_afk(user_id: int, val: bool):
    ensure_user(user_id)
    with _lock:
        get_connection().execute("UPDATE users SET afk=? WHERE user_id=?", (int(val), user_id))
        get_connection().commit()

def is_afk(user_id: int) -> bool:
    ensure_user(user_id)
    with _lock:
        cur = get_connection().cursor()
        cur.execute("SELECT afk FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return bool(row[0]) if row else False

def set_shiny_enabled(user_id: int, val: bool):
    ensure_user(user_id)
    with _lock:
        get_connection().execute("UPDATE users SET shiny_enabled=? WHERE user_id=?", (int(val), user_id))
        get_connection().commit()

def is_shiny_enabled(user_id: int) -> bool:
    ensure_user(user_id)
    with _lock:
        cur = get_connection().cursor()
        cur.execute("SELECT shiny_enabled FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return bool(row[0]) if row else True

def set_collection_enabled(user_id: int, val: bool):
    ensure_user(user_id)
    with _lock:
        get_connection().execute("UPDATE users SET collection_enabled=? WHERE user_id=?", (int(val), user_id))
        get_connection().commit()

def is_collection_enabled(user_id: int) -> bool:
    ensure_user(user_id)
    with _lock:
        cur = get_connection().cursor()
        cur.execute("SELECT collection_enabled FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return bool(row[0]) if row else True

def set_role_ping_enabled(user_id: int, val: bool):
    ensure_user(user_id)
    with _lock:
        get_connection().execute("UPDATE users SET role_ping_enabled=? WHERE user_id=?", (int(val), user_id))
        get_connection().commit()

def is_role_ping_enabled(user_id: int) -> bool:
    ensure_user(user_id)
    with _lock:
        cur = get_connection().cursor()
        cur.execute("SELECT role_ping_enabled FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return bool(row[0]) if row else True

# --------------------
# SHINY HUNT (single)
# --------------------

def get_shiny(user_id: int) -> str | None:
    with _lock:
        cur = get_connection().cursor()
        cur.execute("SELECT pokemon FROM shiny_hunts WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return row[0] if row else None

def set_shiny(user_id: int, pokemon: str):
    """Upsert — replaces existing hunt."""
    ensure_user(user_id)
    with _lock:
        get_connection().execute(
            "INSERT OR REPLACE INTO shiny_hunts (user_id, pokemon) VALUES (?, ?)",
            (user_id, pokemon.lower())
        )
        get_connection().commit()

def clear_shiny(user_id: int):
    with _lock:
        get_connection().execute("DELETE FROM shiny_hunts WHERE user_id=?", (user_id,))
        get_connection().commit()

def get_all_shiny_hunters(pokemon: str) -> list[int]:
    with _lock:
        cur = get_connection().cursor()
        cur.execute("SELECT user_id FROM shiny_hunts WHERE pokemon=?", (pokemon.lower(),))
        return [r[0] for r in cur.fetchall()]

# --------------------
# COLLECTIONS
# --------------------

def add_collection(user_id: int, pokemon: str):
    ensure_user(user_id)
    with _lock:
        get_connection().execute(
            "INSERT OR IGNORE INTO collections (user_id, pokemon) VALUES (?, ?)",
            (user_id, pokemon.lower())
        )
        get_connection().commit()

def remove_collection(user_id: int, pokemon: str):
    with _lock:
        get_connection().execute(
            "DELETE FROM collections WHERE user_id=? AND pokemon=?",
            (user_id, pokemon.lower())
        )
        get_connection().commit()

def clear_collections(user_id: int):
    with _lock:
        get_connection().execute("DELETE FROM collections WHERE user_id=?", (user_id,))
        get_connection().commit()

def get_collections(user_id: int) -> list[str]:
    with _lock:
        cur = get_connection().cursor()
        cur.execute("SELECT pokemon FROM collections WHERE user_id=?", (user_id,))
        return [r[0] for r in cur.fetchall()]

def get_all_collectors(pokemon: str) -> list[int]:
    with _lock:
        cur = get_connection().cursor()
        cur.execute("SELECT user_id FROM collections WHERE pokemon=?", (pokemon.lower(),))
        return [r[0] for r in cur.fetchall()]

# --------------------
# ROLE PINGS
# --------------------

def add_role_ping(guild_id: int, role_id: int, pokemon: str):
    with _lock:
        get_connection().execute(
            "INSERT OR IGNORE INTO role_pings (guild_id, role_id, pokemon) VALUES (?, ?, ?)",
            (guild_id, role_id, pokemon.lower())
        )
        get_connection().commit()

def remove_role_ping(guild_id: int, role_id: int, pokemon: str):
    with _lock:
        get_connection().execute(
            "DELETE FROM role_pings WHERE guild_id=? AND role_id=? AND pokemon=?",
            (guild_id, role_id, pokemon.lower())
        )
        get_connection().commit()

def clear_role_pings(guild_id: int, role_id: int):
    with _lock:
        get_connection().execute(
            "DELETE FROM role_pings WHERE guild_id=? AND role_id=?",
            (guild_id, role_id)
        )
        get_connection().commit()

def get_role_pings(guild_id: int, pokemon: str) -> list[int]:
    with _lock:
        cur = get_connection().cursor()
        cur.execute(
            "SELECT role_id FROM role_pings WHERE guild_id=? AND pokemon=?",
            (guild_id, pokemon.lower())
        )
        return [r[0] for r in cur.fetchall()]

def get_role_ping_list(guild_id: int, role_id: int) -> list[str]:
    with _lock:
        cur = get_connection().cursor()
        cur.execute(
            "SELECT pokemon FROM role_pings WHERE guild_id=? AND role_id=?",
            (guild_id, role_id)
        )
        return [r[0] for r in cur.fetchall()]

def get_all_role_pings(guild_id: int) -> list[tuple[int, str]]:
    """Returns list of (role_id, pokemon) for entire guild."""
    with _lock:
        cur = get_connection().cursor()
        cur.execute(
            "SELECT role_id, pokemon FROM role_pings WHERE guild_id=? ORDER BY role_id",
            (guild_id,)
        )
        return cur.fetchall()

# --------------------
# CHANNEL SETTINGS
# --------------------

def set_pings_enabled(channel_id: int, val: bool):
    with _lock:
        get_connection().execute(
            "INSERT OR REPLACE INTO channel_settings (channel_id, pings_enabled) VALUES (?, ?)",
            (channel_id, int(val))
        )
        get_connection().commit()

def is_pings_enabled(channel_id: int) -> bool:
    with _lock:
        cur = get_connection().cursor()
        cur.execute("SELECT pings_enabled FROM channel_settings WHERE channel_id=?", (channel_id,))
        row = cur.fetchone()
        return bool(row[0]) if row else True