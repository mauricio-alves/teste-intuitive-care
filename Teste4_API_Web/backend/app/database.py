import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import Optional

def get_db_connection():
    #  Cria conexão com banco de dados PostgreSQL
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "ans_dados"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        cursor_factory=RealDictCursor  
    )

def execute_query(query: str, params: Optional[tuple] = None, fetch_one: bool = False):
    # Executa query e retorna resultados
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            
            if fetch_one:
                return cursor.fetchone()
            return cursor.fetchall()
    finally:
        conn.close()

def execute_query_with_count(query: str, count_query: str, params: Optional[tuple] = None):
    # Executa query e retorna (resultados, count total)
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            
            cursor.execute(count_query, params or ())
            count = cursor.fetchone()['count']
            
            return results, count
    finally:
        conn.close()
