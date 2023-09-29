from typing import Optional

from migratik.backends.connection import AbstractConnection, AbstractConnectionContext
from migratik.backends.psycopg2.cursor import Psycopg2CursorContext


class Psycopg2Connection(AbstractConnection):

    def __init__(self, connection):
        self._connection = connection

    def start_transaction(self) -> None:
        pass

    def get_cursor(self) -> Psycopg2CursorContext:
        return Psycopg2CursorContext(self._connection)

    def commit_transaction(self) -> None:
        self._connection.commit()

    def rollback_transaction(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


class Psycopg2ConnectionContext(AbstractConnectionContext):

    def __init__(
        self,
        database: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None
    ):
        super().__init__()
        self.database = database
        self.user = user
        self.password = password
        self.host = host
        self.port = port

    def get_connection(self) -> Psycopg2Connection:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        return Psycopg2Connection(
            psycopg2.connect(
                database=self.database,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                cursor_factory=RealDictCursor
            )
        )
