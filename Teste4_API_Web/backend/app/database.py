import os
from typing import Optional
from venv import logger
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
        required_vars = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
        missing_vars = [var for var in required_vars if var not in os.environ]
        
        if missing_vars:
            raise RuntimeError(f"Configuração de banco incompleta. Variáveis ausentes: {', '.join(missing_vars)}")

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

# Obtém uma conexão do pool
def get_db_connection():
    try:
        return get_db_pool().getconn()
    except PoolError:
        raise HTTPException(status_code=503, detail="Servidor sobrecarregado (limite de conexões atingido). Tente novamente em instantes.")

# Devolve a conexão ao pool de forma segura.
def release_db_connection(conn):
    try:
        if conn:
            get_db_pool().putconn(conn)
    except Exception:
        logger.warning("⚠️ Falha ao devolver conexão ao pool. A conexão pode já ter sido encerrada.")
        pass

# Executa query e retorna resultados
def execute_query(query: str, params: Optional[tuple] = None, fetch_one: bool = False):
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

# Executa query e retorna (resultados, count total)
def execute_query_with_count(query: str, count_query: str, params: Optional[tuple] = None, count_params: Optional[tuple] = None):
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

# Encerra todas as conexões do pool explicitamente
def close_db_pool():
    global db_pool
    if db_pool is not None:
        db_pool.closeall()
        db_pool = None
