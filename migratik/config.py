from dataclasses import dataclass
from typing import Any, Union
from pathlib import Path

import yaml
from yaml import Loader


@dataclass
class MigrationSection:
    path: Path


@dataclass
class BackendSection:
    class_: str
    kwargs: dict[str, Any]


@dataclass
class Config:
    migrations: MigrationSection
    backend: BackendSection


def get_config(path: Union[str, Path]) -> Config:
    path = Path(path)

    with path.open(encoding="UTF-8") as file:
        data = yaml.load(file, Loader)

    return Config(
        migrations=MigrationSection(
            path=Path(data["migrations"]["path"])
        ),
        backend=BackendSection(
            class_=data["backend"]["class"],
            kwargs=data["backend"].get("kwargs", {})
        )
    )
