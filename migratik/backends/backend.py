from abc import ABC, abstractmethod
from typing import Optional, Any

from migratik.backends.connection import AbstractConnectionContext
from migratik.backends.cursor import AbstractCursor
from migratik.errors import MigrationTableError


class AbstractBackend(ABC):

    def __init__(self, migration_table: Optional[str] = None):
        self.migration_table = migration_table or "migratik"
        self.check_package()

    @abstractmethod
    def check_package(self) -> None:
        pass

    @abstractmethod
    def connect(self) -> AbstractConnectionContext:
        pass

    @abstractmethod
    def check_migration_table(self, cursor: AbstractCursor) -> bool:
        pass

    @abstractmethod
    def create_migration_table(self, cursor: AbstractCursor) -> None:
        pass

    @abstractmethod
    def add_migration(self, cursor: AbstractCursor, *, version: int) -> None:
        pass

    @abstractmethod
    def delete_migration(self, cursor: AbstractCursor, *, version: int) -> None:
        pass

    @abstractmethod
    def get_last_migration(self, cursor: AbstractCursor) -> Optional[dict[str, Any]]:
        pass

    def initialize_migration_table(self, version: int) -> None:
        with self.connect() as connection:
            with connection.get_cursor() as cursor:
                if self.check_migration_table(cursor):
                    raise MigrationTableError(
                        f"Migration table {self.migration_table!r} already exists!"
                    )

                self.create_migration_table(cursor)
                self.add_migration(cursor, version=version)

    def get_version(self) -> Optional[int]:
        with self.connect() as connection:
            with connection.get_cursor() as cursor:
                if self.check_migration_table(cursor):
                    last_migration = self.get_last_migration(cursor)

                    if last_migration is not None:
                        return last_migration["version"]
