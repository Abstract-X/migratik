from dataclasses import dataclass
from typing import Any, Union, Optional
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
    backend: Optional[BackendSection] = None


def get_config(path: Union[str, Path]) -> Config:
    path = Path(path)

    with path.open(encoding="UTF-8") as file:
        data = yaml.load(file, Loader)

    backend_section = data.get("backend")

    if backend_section is not None:
        backend_section = BackendSection(
            class_=backend_section["class"],
            kwargs=backend_section.get("kwargs", {})
        )

    return Config(
        migrations=MigrationSection(
            path=Path(data["migrations"]["path"])
        ),
        backend=backend_section
    )
