"""Connector protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod

from paper_bot.models.paper import Paper


class Connector(ABC):
    source_name: str

    @abstractmethod
    def fetch(self) -> list[Paper]:
        raise NotImplementedError
