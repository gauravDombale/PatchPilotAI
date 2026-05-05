from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    path: str
    code: str
    score: float


def to_state_docs(chunks: list[RetrievedChunk]) -> list[dict[str, float | str]]:
    return [{"path": c.path, "code": c.code, "score": c.score} for c in chunks]
