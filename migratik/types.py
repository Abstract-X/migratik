from dataclasses import dataclass


@dataclass
class Migration:
    version: int
    upgrade_queries: str
    downgrade_queries: str
