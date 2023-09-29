from typing import Optional, Any

from migratik.backends.backend import AbstractBackend
from migratik.backends.psycopg2.connection import Psycopg2ConnectionContext
from migratik.backends.psycopg2.cursor import Psycopg2Cursor


class Psycopg2Backend(AbstractBackend):

    def __init__(
        self,
        database: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        migration_table: Optional[str] = None
    ):
        super().__init__(migration_table=migration_table)
        self.database = database
        self.user = user
        self.password = password
        self.host = host
        self.port = port

    def check_package(self) -> None:
        try:
            import psycopg2
        except ImportError:
            raise ImportError(
                "To use Psycopg2Backend you need to install «psycopg2»:"
                "\nhttps://www.psycopg.org/docs/install.html"
            ) from None

    def connect(self) -> Psycopg2ConnectionContext:
        return Psycopg2ConnectionContext(
            database=self.database,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port
        )

    def check_migration_table(self, cursor: Psycopg2Cursor) -> bool:
        cursor.execute_query(
            f"""
            SELECT
                EXISTS (
                    SELECT
                        1
                    FROM
                        "information_schema"."tables"
                    WHERE
                        "table_name" = '{self.migration_table}'
                )
                AS "result";
            """
        )

        return cursor.fetch_row()["result"]

    def create_migration_table(self, cursor: Psycopg2Cursor) -> None:
        cursor.execute_query(
            f"""
            CREATE TABLE "{self.migration_table}" (
                "id"                        SERIAL
                                            PRIMARY KEY,
                "version"                   INTEGER
                                            UNIQUE
                                            NOT NULL,
                "creation_timestamp"        TIMESTAMP WITH TIME ZONE
                                            NOT NULL
                                            DEFAULT (NOW())
            );
            """
        )

    def add_migration(self, cursor: Psycopg2Cursor, *, version: int) -> None:
        cursor.execute_query(
            f"""
            INSERT INTO
                "{self.migration_table}" ("version")
            VALUES
                (%(version)s);
            """,
            {
                "version": version
            }
        )

    def delete_migration(self, cursor: Psycopg2Cursor, *, version: int) -> None:
        cursor.execute_query(
            f"""
            DELETE FROM
                "{self.migration_table}"
            WHERE
                "version" = %(version)s;
            """,
            {
                "version": version
            }
        )

    def get_last_migration(self, cursor: Psycopg2Cursor) -> Optional[dict[str, Any]]:
        cursor.execute_query(
            f"""
            SELECT
                "id", "version", "creation_timestamp"
            FROM
                "{self.migration_table}"
            ORDER BY
                "id" DESC
            LIMIT
                1;
            """
        )

        return cursor.fetch_row()
