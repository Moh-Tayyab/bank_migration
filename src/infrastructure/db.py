
import psycopg2
from psycopg2.extras import RealDictCursor
import os

class DatabaseManager:
    def __init__(self, connection_string: str = None):
        self.conn_string = connection_string or os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/bank_migration')
        self.conn = None

    def connect(self):
        if not self.conn or self.conn.closed:
            try:
                self.conn = psycopg2.connect(self.conn_string, cursor_factory=RealDictCursor)
                self.conn.autocommit = True
            except Exception as e:
                print(f"DB Connection Error: {e}")
                raise e

    def execute(self, query, params=None):
        self.connect()
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchall()
            return None

    def close(self):
        if self.conn:
            self.conn.close()
