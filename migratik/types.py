from dataclasses import dataclass
from pathlib import Path


@dataclass
class MigrationFile:
    version: int
    path: Path


@dataclass
class Migration:
    version: int
    upgrade_queries: str
    downgrade_queries: str
