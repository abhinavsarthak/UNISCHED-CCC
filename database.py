
import mysql.connector
from mysql.connector import pooling
from contextlib import contextmanager
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("MYSQL_HOST", "localhost"),
    "port":     int(os.getenv("MYSQL_PORT", 3306)),
    "user":     os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "university_scheduler"),
    "charset":  "utf8mb4",
    "collation":"utf8mb4_unicode_ci",
    "autocommit": False,
}

_pool: pooling.MySQLConnectionPool | None = None


def init_pool(pool_size: int = 5) -> None:
    global _pool
    _pool = pooling.MySQLConnectionPool(
        pool_name="ucs_pool",
        pool_size=pool_size,
        **DB_CONFIG,
    )


@contextmanager
def get_db():
    
    if _pool is None:
        init_pool()
    conn = _pool.get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetchall(sql: str, params=None) -> list[dict]:
    with get_db() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        return cur.fetchall()


def fetchone(sql: str, params=None) -> dict | None:
    with get_db() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        return cur.fetchone()


def execute(sql: str, params=None) -> int:
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        return cur.lastrowid


def executemany(sql: str, params_list: list) -> None:
    with get_db() as conn:
        cur = conn.cursor()
        cur.executemany(sql, params_list)
