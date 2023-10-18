from pathlib import Path
from typing import Union, Optional
from datetime import datetime
import enum
from enum import IntEnum

from migratik.types import Migration
from migratik.backends.backend import AbstractBackend
from migratik.version_list import VersionList
from migratik.errors import (
    MigrationError,
    MigrationPathError,
    MigrationParsingError
)


_UPGRADE_COMMENT = "-- Upgrade:"
_DOWNGRADE_COMMENT = "-- Downgrade:"
_DIGITS = frozenset("0123456789")


class ParsingState(IntEnum):
    INITIAL = enum.auto()
    UPGRADE_COLLECTING = enum.auto()
    DOWNGRADE_COLLECTING = enum.auto()


class Migrator:

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)

    def create_migration(self) -> Path:
        if not self._check_path():
            self.path.mkdir()

        current_datetime = datetime.utcnow()
        version = int(
            current_datetime.strftime("%Y%m%d%H%M%S%f")
        )
        formatted_current_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
        content = (
            f"-- Version {version}."
            f"\n-- Created at {formatted_current_datetime} UTC."
            f"\n\n\n{_UPGRADE_COMMENT}\n"
        )

        if any(i.is_file() and _check_name(i.name) for i in self.path.iterdir()):
            content += f"\n\n\n{_DOWNGRADE_COMMENT}\n"

        content += "\n"
        path = self._get_migration_path(version)
        path.write_text(content, encoding="UTF-8")

        return path

    def get_versions(self) -> list[int]:
        if not self._check_path():
            raise MigrationPathError(
                f"Migration directory {str(self.path)!r} does not exist!"
            )

        return sorted(
            int(i.stem)
            for i in self.path.iterdir()
            if i.is_file() and _check_name(i.name)
        )

    def get_migration(self, version: int) -> Migration:
        if version < 0:
            raise ValueError("Version cannot be negative!")

        if not self._check_path():
            raise MigrationPathError(
                f"Migration directory {str(self.path)!r} does not exist!"
            )

        path = self._get_migration_path(version)

        if not path.exists():
            raise MigrationPathError(
                f"Migration file {str(path)!r} does not exist!"
            )

        return self._get_migration(version)

    def upgrade(self, backend: AbstractBackend, version: Optional[int] = None) -> None:
        if (version is not None) and (version < 0):
            raise ValueError("Version cannot be negative!")

        versions = self.get_versions()

        if not versions:
            raise MigrationError("No migration files!")

        versions = VersionList(versions)

        with backend.connect() as connection:
            with connection.get_cursor() as cursor:
                if backend.check_migration_table(cursor):
                    last_migration = backend.get_last_migration(cursor)

                    if last_migration is not None:
                        current_version = last_migration["version"]

                        if version is not None:
                            if current_version == version:
                                return

                        versions = versions.get_for_upgrade(current_version, version)
                else:
                    backend.create_migration_table(cursor)

                migrations = [self._get_migration(i) for i in versions]
                processed_migrations = []

                for migration in migrations:
                    try:
                        cursor.execute_query(migration.upgrade_queries)
                    except Exception:  # noqa
                        connection.rollback_transaction()
                        connection.start_transaction()

                        for processed_migration in reversed(processed_migrations):
                            cursor.execute_query(processed_migration.downgrade_queries)
                            backend.delete_migration(cursor, version=processed_migration.version)
                            connection.commit_transaction()
                            connection.start_transaction()

                        raise
                    else:
                        backend.add_migration(cursor, version=migration.version)
                        connection.commit_transaction()
                        processed_migrations.append(migration)
                        connection.start_transaction()

    def downgrade(self, backend: AbstractBackend, version: int) -> None:
        if version < 0:
            raise ValueError("Version cannot be negative!")

        versions = self.get_versions()

        if not versions:
            raise MigrationError("No migration files!")

        versions = VersionList(versions)

        with backend.connect() as connection:
            with connection.get_cursor() as cursor:
                if not backend.check_migration_table(cursor):
                    raise MigrationError("Migration table has not been initialized!")

                last_migration = backend.get_last_migration(cursor)

                if last_migration is None:
                    raise MigrationError("There is not single migration in migration table!")

                current_version = last_migration["version"]

                if current_version == version:
                    return

                versions = versions.get_for_downgrade(current_version, version)
                migrations = [self._get_migration(i) for i in versions]
                processed_migrations = []

                for migration in migrations:
                    try:
                        cursor.execute_query(migration.downgrade_queries)
                    except Exception:  # noqa
                        connection.rollback_transaction()
                        connection.start_transaction()

                        for processed_migration in reversed(processed_migrations):
                            cursor.execute_query(processed_migration.upgrade_queries)
                            backend.add_migration(cursor, version=processed_migration.version)
                            connection.commit_transaction()
                            connection.start_transaction()

                        raise
                    else:
                        backend.delete_migration(cursor, version=migration.version)
                        connection.commit_transaction()
                        processed_migrations.append(migration)
                        connection.start_transaction()

    def _check_path(self) -> bool:
        if self.path.exists():
            if not self.path.is_dir():
                raise MigrationPathError(f"Path {str(self.path)!r} is not directory!")

            return True

        return False

    def _get_migration(self, version: int) -> Migration:
        path = self._get_migration_path(version)
        upgrade_lines = []
        downgrade_lines = []
        state = ParsingState.INITIAL

        with path.open(encoding="UTF-8") as file:
            for line in file:
                striped_line = line.strip()

                if state is ParsingState.INITIAL:
                    if striped_line == _UPGRADE_COMMENT:
                        state = ParsingState.UPGRADE_COLLECTING
                    elif striped_line == _DOWNGRADE_COMMENT:
                        raise MigrationParsingError(
                            f"Upgrade block missed ({path})!"
                        )
                elif state is ParsingState.UPGRADE_COLLECTING:
                    if striped_line == _DOWNGRADE_COMMENT:
                        state = ParsingState.DOWNGRADE_COLLECTING
                    elif striped_line == _UPGRADE_COMMENT:
                        raise MigrationParsingError(
                            f"Extra upgrade block was found ({path})!"
                        )
                    else:
                        upgrade_lines.append(
                            line.rstrip()
                        )
                elif state is ParsingState.DOWNGRADE_COLLECTING:
                    if striped_line == _UPGRADE_COMMENT:
                        raise MigrationParsingError(
                            f"Extra upgrade block was found ({path})!"
                        )
                    elif striped_line == _DOWNGRADE_COMMENT:
                        raise MigrationParsingError(
                            f"Extra downgrade block was found ({path})!"
                        )
                    else:
                        downgrade_lines.append(
                            line.rstrip()
                        )

        return Migration(
            version=version,
            upgrade_queries="\n".join(upgrade_lines).rstrip(),
            downgrade_queries="\n".join(downgrade_lines).rstrip()
        )

    def _get_migration_path(self, version: int) -> Path:
        return self.path / f"{version}.sql"


def _check_name(file_name: str) -> bool:
    try:
        name, extension = file_name.rsplit(".", 1)
    except ValueError:
        return False

    return (
        (extension == "sql")
        and bool(name)
        and all(i in _DIGITS for i in name)
    )
