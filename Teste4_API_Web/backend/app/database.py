from psycopg2.extras import RealDictCursor
import os
from typing import Optional
from psycopg2 import pool

# Pool de conexões global
db_pool: Optional[pool.SimpleConnectionPool] = None

# Obtém o pool de conexões
def get_db_pool() -> pool.SimpleConnectionPool:
    global db_pool
    if db_pool is None:
        db_pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=20,
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "ans_dados"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
            cursor_factory=RealDictCursor
        )
    return db_pool

def get_db_connection():
    return get_db_pool().getconn()

def release_db_connection(conn):
    get_db_pool().putconn(conn)

def execute_query(query: str, params: Optional[tuple] = None, fetch_one: bool = False):
    # Executa query e retorna resultados
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchone() if fetch_one else cursor.fetchall()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_db_connection(conn)

def execute_query_with_count(query: str, count_query: str, params: Optional[tuple] = None, count_params: Optional[tuple] = None):
    # Executa query e retorna (resultados, count total)
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            cursor.execute(count_query, count_params if count_params is not None else (params or ()))
            count = cursor.fetchone()['count']
            return results, count
    finally:
        release_db_connection(conn)
