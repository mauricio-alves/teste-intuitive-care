import os
from typing import Optional
from psycopg2 import pool
from psycopg2.pool import PoolError
from psycopg2.extras import RealDictCursor
from fastapi import HTTPException

# Pool de conexões global
db_pool: Optional[pool.SimpleConnectionPool] = None

# Obtém o pool de conexões
def get_db_pool() -> pool.SimpleConnectionPool:
    global db_pool
    if db_pool is None:
        db_pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=20,
            host=os.environ["DB_HOST"],
            port=int(os.environ["DB_PORT"]),
            database=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"]
        )
    return db_pool

def get_db_connection():
    try:
        return get_db_pool().getconn()
    except PoolError:
        raise HTTPException(status_code=503, detail="Servidor sobrecarregado (limite de conexões atingido). Tente novamente em instantes.")

def release_db_connection(conn):
    get_db_pool().putconn(conn)

def execute_query(query: str, params: Optional[tuple] = None, fetch_one: bool = False):
    # Executa query e retorna resultados
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
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
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            cursor.execute(count_query, count_params if count_params is not None else (params or ()))
            count = cursor.fetchone()['count']
            return results, count
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        release_db_connection(conn)

def close_db_pool():
    # Encerra todas as conexões do pool explicitamente
    global db_pool
    if db_pool is not None:
        db_pool.closeall()
        db_pool = None
