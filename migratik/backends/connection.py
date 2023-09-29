from abc import ABC, abstractmethod
from typing import Optional

from migratik.backends.cursor import AbstractCursorContext


class AbstractConnection(ABC):

    @abstractmethod
    def start_transaction(self) -> None:
        pass

    @abstractmethod
    def get_cursor(self) -> AbstractCursorContext:
        pass

    @abstractmethod
    def commit_transaction(self) -> None:
        pass

    @abstractmethod
    def rollback_transaction(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


class AbstractConnectionContext(ABC):

    def __init__(self):
        self._connection: Optional[AbstractConnection] = None

    def __enter__(self) -> AbstractConnection:
        self._connection = self.get_connection()
        self._connection.start_transaction()

        return self._connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._connection.rollback_transaction()
        else:
            self._connection.commit_transaction()

        self._connection.close()

    @abstractmethod
    def get_connection(self) -> AbstractConnection:
        pass
