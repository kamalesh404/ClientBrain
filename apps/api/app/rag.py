"""Naive but honest retrieval: keyword overlap scoring with citations.
Phase 2 swaps this for vector search — API stays identical.
"""
import re

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> set[str]:
    return set(_WORD.findall(s.lower()))


def chunk_text(text: str, source: str, size: int = 800, overlap: int = 100) -> list[dict]:
    chunks = []
    i = 0
    while i < len(text):
        piece = text[i : i + size]
        if piece.strip():
            chunks.append({"text": piece.strip(), "source": source})
        i += size - overlap
    return chunks


def retrieve(query: str, docs: list[dict], top_k: int = 4) -> list[dict]:
    q = _tokens(query)
    scored = []
    for d in docs:
        overlap = len(q & _tokens(d["text"]))
        if overlap:
            scored.append((overlap, d))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:top_k]]
