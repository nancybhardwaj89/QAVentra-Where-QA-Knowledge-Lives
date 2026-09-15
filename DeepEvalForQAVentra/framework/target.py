"""The system under test.

This is the ONLY file that knows how to talk to the application being
evaluated. To reuse this framework on a different project, write a new
Target subclass here and point TARGET_CLASS at it — nothing in the test
files, metrics, or reporting needs to change.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

import requests

from framework import config


@dataclass
class TargetResponse:
    """Normalized response shape every Target must return."""
    answer: str
    retrieval_context: List[str] = field(default_factory=list)


class Target(ABC):
    """Base class for any system this framework can evaluate."""

    @abstractmethod
    def query(self, question: str, **kwargs) -> TargetResponse:
        """Send a question to the system, return its answer + retrieved context."""
        raise NotImplementedError

    def name(self) -> str:
        return self.__class__.__name__


class QAVentraTarget(Target):
    """Adapter for QAVentra's /ask endpoint."""

    def __init__(self, api_url: str = None):
        self.api_url = api_url or config.TARGET_API_URL

    def query(self, question: str, source_filter: str = "all") -> TargetResponse:
        response = requests.post(
            f"{self.api_url}/ask",
            json={"question": question, "filter": source_filter},
            timeout=config.TARGET_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        context = [
            s["text"] for s in data.get("sources", []) if s.get("text")
        ]

        if not context:
            print(
                "  [warn] No retrieval context returned. Retrieval metrics "
                "(Contextual Precision/Recall) cannot score without it — "
                "confirm the API includes chunk text in its sources response."
            )

        return TargetResponse(answer=data["answer"], retrieval_context=context)


# Swap this to evaluate a different system.
TARGET_CLASS = QAVentraTarget

_cached_target = None


def get_target() -> Target:
    global _cached_target
    if _cached_target is None:
        _cached_target = TARGET_CLASS()
    return _cached_target