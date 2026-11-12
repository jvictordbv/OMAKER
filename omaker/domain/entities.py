"""A biomedical entity mention found in the text."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Entity:
    text: str
    start: int
    end: int
    type: str
    score: float
