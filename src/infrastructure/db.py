
import logging
import os

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, connection_string: str = None):
        self.conn_string = connection_string or os.getenv("DATABASE_URL", "")
        self.conn = None
        if not self.conn_string:
            logger.info("No DATABASE_URL configured — running without database")

    @property
    def available(self) -> bool:
        return bool(self.conn_string)

    def connect(self):
        if not self.conn_string:
            raise RuntimeError("No DATABASE_URL configured")
        is_stale = self.conn is None or self.conn.closed
        if not is_stale:
            return
        import psycopg2
        from psycopg2.extras import RealDictCursor
        connect_args = {"cursor_factory": RealDictCursor}
        sslmode = os.getenv("DATABASE_SSLMODE", "prefer")
        connect_args["sslmode"] = sslmode
        try:
            self.conn = psycopg2.connect(self.conn_string, **connect_args)
        except psycopg2.InterfaceError:
            logger.warning("Stale database connection detected, reconnecting")
            self.conn = psycopg2.connect(self.conn_string, **connect_args)
        self.conn.autocommit = False

    def execute(self, query, params=None):
        self.connect()
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                if cur.description:
                    result = cur.fetchall()
                else:
                    result = None
            self.conn.commit()
            return result
        except Exception:
            self.conn.rollback()
            raise

    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
