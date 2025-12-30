from abc import ABC, abstractmethod
from django.http import HttpRequest

class KeyBuilder:

    @abstractmethod
    def build(self, request: HttpRequest) -> str:
        pass
