from abc import ABC, abstractmethod


class BaseBackend(ABC):

    @abstractmethod
    def allow(self, key: str) -> int:
        pass
