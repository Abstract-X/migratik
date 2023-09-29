from typing import Any, Optional

from migratik.backends.cursor import AbstractCursor, AbstractCursorContext


class Psycopg2Cursor(AbstractCursor):

    def __init__(self, cursor):
        self._cursor = cursor

    def execute_query(self, query: str, parameters: Optional[dict[str, Any]] = None) -> None:
        self._cursor.execute(query, parameters)

    def fetch_row(self) -> Optional[dict[str, Any]]:
        row = self._cursor.fetchone()

        if row is not None:
            return dict(row)

    def close(self) -> None:
        self._cursor.close()


class Psycopg2CursorContext(AbstractCursorContext):

    def __init__(self, connection):
        super().__init__()
        self.connection = connection

    def get_cursor(self) -> Psycopg2Cursor:
        return Psycopg2Cursor(
            self.connection.cursor()
        )
