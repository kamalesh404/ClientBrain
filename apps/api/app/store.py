"""In-memory multi-tenant store for Phase 1.
Swap with Postgres+pgvector in Phase 2 without changing route signatures.
Each workspace: list of {text, source}.
"""
from collections import defaultdict

_store: dict[str, list[dict]] = defaultdict(list)
_usage: dict[str, dict] = defaultdict(lambda: {"messages": 0, "docs": 0})


def add_docs(workspace: str, docs: list[dict]) -> int:
    _store[workspace].extend(docs)
    _usage[workspace]["docs"] += len(docs)
    return len(docs)


def get_docs(workspace: str) -> list[dict]:
    return _store[workspace]


def log_message(workspace: str):
    _usage[workspace]["messages"] += 1


def get_usage(workspace: str) -> dict:
    return {"workspace": workspace, **_usage[workspace]}
