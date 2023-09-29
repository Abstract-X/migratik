from abc import ABC, abstractmethod
from typing import Optional, Any


class AbstractCursor(ABC):

    @abstractmethod
    def execute_query(self, query: str, parameters: Optional[dict[str, Any]] = None) -> None:
        pass

    @abstractmethod
    def fetch_row(self) -> Optional[dict[str, Any]]:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


class AbstractCursorContext(ABC):

    def __init__(self):
        self._cursor: Optional[AbstractCursor] = None

    def __enter__(self) -> AbstractCursor:
        self._cursor = self.get_cursor()

        return self._cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cursor.close()

    @abstractmethod
    def get_cursor(self) -> AbstractCursor:
        pass
