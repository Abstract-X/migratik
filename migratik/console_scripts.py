from argparse import ArgumentParser, Namespace
import importlib
from pathlib import Path
from typing import Any

from migratik.config import get_config, Config
from migratik.migrator import Migrator
from migratik.backends.backend import AbstractBackend
from migratik.errors import MigratikError


_CONFIG_TEMPLATE = (
    "migrations:"
    '\n    path: "..."'
    "\n\nbackend:"
    '\n    class: "..."'
    "\n    kwargs:"
    "\n        ..."
    "\n"
)


def process_command() -> None:
    parser = ArgumentParser(prog="migratik")
    subparsers = parser.add_subparsers()

    init_parser = subparsers.add_parser("init")
    init_parser.set_defaults(func=process_init)

    status_parser = subparsers.add_parser("status")
    status_parser.set_defaults(func=process_status)

    create_parser = subparsers.add_parser("create")
    create_parser.set_defaults(func=process_create)

    upgrade_parser = subparsers.add_parser("upgrade")
    upgrade_parser.add_argument("-v", "--version", type=int)
    upgrade_parser.set_defaults(func=process_upgrade)

    downgrade_parser = subparsers.add_parser("downgrade")
    downgrade_parser.add_argument("-v", "--version", type=int, required=True)
    downgrade_parser.set_defaults(func=process_downgrade)

    namespace = parser.parse_args()

    try:
        namespace.func(namespace)
    except AttributeError:
        print("You didn't specify a command.")


def process_init(namespace: Namespace) -> None:
    config_path = Path.cwd() / "migratik.yml"

    if config_path.exists():
        print("Migratik has already been initialized.")

        return

    config_path.write_text(_CONFIG_TEMPLATE, encoding="UTF-8")


def process_status(namespace: Namespace) -> None:
    try:
        config = _get_config()
        migrator = Migrator(config.migrations.path)
        migration_files = migrator.get_migration_files()

        if migration_files:
            latest_version = migration_files[-1].version
        else:
            latest_version = "—"

        backend = _get_backend(config.backend.class_, config.backend.kwargs)
        current_version = backend.get_version() or "—"
    except MigratikError as error:
        print(error)
    else:
        print(
            f"Current version: {current_version}"
            f"\nLatest version: {latest_version}"
        )


def process_create(namespace: Namespace) -> None:
    try:
        config = _get_config()
        migrator = Migrator(config.migrations.path)
        migrator.create_migration_file()
    except MigratikError as error:
        print(error)


def process_upgrade(namespace: Namespace) -> None:
    try:
        config = _get_config()
        migrator = Migrator(config.migrations.path)
        backend = _get_backend(config.backend.class_, config.backend.kwargs)
        migrator.upgrade(backend, namespace.version)
    except MigratikError as error:
        print(error)


def process_downgrade(namespace: Namespace) -> None:
    try:
        config = _get_config()
        migrator = Migrator(config.migrations.path)
        backend = _get_backend(config.backend.class_, config.backend.kwargs)
        migrator.downgrade(backend, namespace.version)
    except MigratikError as error:
        print(error)


def _get_config() -> Config:
    try:
        return get_config(
            Path.cwd() / "migratik.yml"
        )
    except FileNotFoundError:
        raise MigratikError(
            "Configuration file was not found. "
            "Initialize using «migratik init» command."
        ) from None


def _get_backend(class_: str, kwargs: dict[str, Any]) -> AbstractBackend:
    if "." in class_:
        module, class_ = class_.rsplit(".", 1)
    else:
        module = "migratik"

    module = importlib.import_module(module)
    class_ = getattr(module, class_)

    return class_(**kwargs)
