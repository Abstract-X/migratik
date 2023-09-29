from pathlib import Path
from typing import Union, Optional
from datetime import datetime
import enum
from enum import IntEnum

from migratik.types import MigrationFile, Migration
from migratik.backends.backend import AbstractBackend
from migratik.errors import (
    MigrationError,
    MigrationPathError,
    MigrationFileError,
    MigrationParsingError
)


_UPGRADE_COMMENT = "-- Upgrade:"
_DOWNGRADE_COMMENT = "-- Downgrade:"
_MIGRATION_TEMPLATE = (
    "-- Version {version}."
    "\n-- Created at {creation_datetime} UTC."
    f"\n\n\n{_UPGRADE_COMMENT}"
    f"\n\n\n\n{_DOWNGRADE_COMMENT}"
    "\n\n"
)
_DIGITS = frozenset("0123456789")


class ParsingState(IntEnum):
    INITIAL = enum.auto()
    UPGRADE_COLLECTING = enum.auto()
    DOWNGRADE_COLLECTING = enum.auto()


class Migrator:

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)

    def create_migration_file(self) -> Path:
        if not self._check_path():
            self.path.mkdir()

        files = self._get_migration_files()
        version = max([i.version for i in files]) + 1 if files else 1
        path = self.path / _get_migration_file_name(version)
        path.write_text(
            _MIGRATION_TEMPLATE.format(
                version=version,
                creation_datetime=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ),
            encoding="UTF-8"
        )

        return path

    def get_migration_files(self) -> list[MigrationFile]:
        if not self._check_path():
            raise MigrationPathError(
                f"Migration directory {str(self.path)!r} does not exist!"
            )

        return self._get_migration_files()

    def get_migration(self, version: int) -> Migration:
        if version < 1:
            raise ValueError("Version cannot be less than 1!")

        if not self._check_path():
            raise MigrationPathError(
                f"Migration directory {str(self.path)!r} does not exist!"
            )

        migration_path = self.path / _get_migration_file_name(version)

        if not migration_path.exists():
            raise MigrationPathError(
                f"Migration file {str(migration_path)!r} does not exist!"
            )

        upgrade_lines = []
        downgrade_lines = []
        state = ParsingState.INITIAL

        with migration_path.open(encoding="UTF-8") as file:
            for line in file:
                striped_line = line.strip()

                if state is ParsingState.INITIAL:
                    if striped_line == _UPGRADE_COMMENT:
                        state = ParsingState.UPGRADE_COLLECTING
                    elif striped_line == _DOWNGRADE_COMMENT:
                        raise MigrationParsingError(
                            f"Upgrade block missed ({migration_path})!"
                        )
                elif state is ParsingState.UPGRADE_COLLECTING:
                    if striped_line == _DOWNGRADE_COMMENT:
                        state = ParsingState.DOWNGRADE_COLLECTING
                    elif striped_line == _UPGRADE_COMMENT:
                        raise MigrationParsingError(
                            f"Extra upgrade block was found ({migration_path})!"
                        )
                    else:
                        upgrade_lines.append(
                            line.rstrip()
                        )
                elif state is ParsingState.DOWNGRADE_COLLECTING:
                    if striped_line == _UPGRADE_COMMENT:
                        raise MigrationParsingError(
                            f"Extra upgrade block was found ({migration_path})!"
                        )
                    elif striped_line == _DOWNGRADE_COMMENT:
                        raise MigrationParsingError(
                            f"Extra downgrade block was found ({migration_path})!"
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

    def upgrade(self, backend: AbstractBackend, version: Optional[int] = None) -> None:
        if (version is not None) and (version < 1):
            raise ValueError("Version cannot be less than 1!")

        files = self.get_migration_files()

        if not files:
            raise MigrationError("No migration files!")

        with backend.connect() as connection:
            with connection.get_cursor() as cursor:
                if backend.check_migration_table(cursor):
                    last_migration = backend.get_last_migration(cursor)

                    if last_migration is not None:
                        current_version = last_migration["version"]

                        if version is not None:
                            if current_version == version:
                                return
                            elif current_version > version:
                                raise MigrationError(
                                    f"Current version ({current_version}) is greater "
                                    f"than upgrade version ({version})!"
                                )

                        files = files[current_version:version]
                else:
                    backend.create_migration_table(cursor)

                migrations = [self.get_migration(i.version) for i in files]
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
        if version < 1:
            raise ValueError("Version cannot be less than 1!")

        files = self.get_migration_files()

        if not files:
            raise MigrationError("No migration files!")

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
                elif current_version < version:
                    raise MigrationError(
                        f"Current version ({current_version}) is smaller "
                        f"than downgrade version ({version})!"
                    )

                files = files[current_version - 1:version - 1:-1]
                migrations = [self.get_migration(i.version) for i in files]
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

    def _get_migration_files(self) -> list[MigrationFile]:
        files = [
            MigrationFile(
                version=_get_migration_file_version(i.name),
                path=i
            )
            for i in self.path.iterdir()
            if i.is_file() and _check_migration_file_name(i.name)
        ]

        if files:
            files.sort(key=lambda file: file.version)
            version = files[0].version

            for i in files[1:]:
                next_version = version + 1

                if i.version != next_version:
                    raise MigrationFileError(
                        f"List of migration files is incomplete. "
                        f"Missing migration with version {next_version}!"
                    )

                version = i.version

        return files


def _check_migration_file_name(file_name: str) -> bool:
    try:
        name, extension = file_name.rsplit(".", 1)
    except ValueError:
        return False

    return (
        (extension == "sql")
        and (name[0] == "v")
        and bool(name[1:])
        and all(i in _DIGITS for i in name[1:])
    )


def _get_migration_file_name(version: int) -> str:
    return f"v{version}.sql"


def _get_migration_file_version(file_name: str) -> int:
    return int(file_name[1:].split(".", 1)[0])
