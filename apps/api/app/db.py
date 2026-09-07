"""Hybrid store: Postgres+pgvector when reachable, else in-memory fallback.

Phase 2 keeps zero-friction local dev (no DB needed) while being
deploy-ready: if DATABASE_URL connects, documents persist in SQL
with a pgvector column when the extension exists.
"""
from collections import defaultdict

try:
    import psycopg  # psycopg3
    _HAS_PSYCOPG = True
except Exception:
    _HAS_PSYCOPG = False

_backend = "memory"
_init_attempted = False

_mem_store: dict[str, list[dict]] = defaultdict(list)
_mem_usage: dict[str, dict] = defaultdict(lambda: {"messages": 0, "docs": 0, "tokens": 0})


def backend() -> str:
    return _backend


def init_db(database_url: str = "") -> str:
    """Try to init Postgres; return active backend name. Never raises."""
    global _backend, _init_attempted
    if _init_attempted:
        return _backend
    _init_attempted = True
    if not _HAS_PSYCOPG or not database_url or "postgres" not in database_url:
        _backend = "memory"
        return _backend
    try:
        import psycopg
        with psycopg.connect(database_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(
                    """CREATE TABLE IF NOT EXISTS documents (
                        id SERIAL PRIMARY KEY, workspace TEXT,
                        source TEXT, text TEXT, embedding TEXT);"""
                )
                cur.execute(
                    """CREATE TABLE IF NOT EXISTS usage (
                        workspace TEXT PRIMARY KEY, messages INT DEFAULT 0,
                        docs INT DEFAULT 0, tokens INT DEFAULT 0);"""
                )
        _backend = "postgres"
    except Exception:
        _backend = "memory"
    return _backend


def add_docs(workspace: str, docs: list[dict]) -> int:
    if _backend == "postgres":
        try:
            import psycopg, json
            from app.config import settings
            with psycopg.connect(settings.database_url, autocommit=True) as conn:
                with conn.cursor() as cur:
                    for d in docs:
                        cur.execute(
                            "INSERT INTO documents (workspace, source, text, embedding) VALUES (%s,%s,%s,%s);",
                            (workspace, d.get("source", ""), d.get("text", ""),
                             json.dumps(d.get("embedding")) if d.get("embedding") else None),
                        )
                    cur.execute(
                        """INSERT INTO usage (workspace, docs) VALUES (%s,%s)
                           ON CONFLICT (workspace) DO UPDATE SET docs = usage.docs + %s;""",
                        (workspace, len(docs), len(docs)),
                    )
            return len(docs)
        except Exception:
            pass
    _mem_store[workspace].extend(docs)
    _mem_usage[workspace]["docs"] += len(docs)
    return len(docs)


def get_docs(workspace: str, limit: int = 500) -> list[dict]:
    if _backend == "postgres":
        try:
            import psycopg, json
            from app.config import settings
            with psycopg.connect(settings.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT source, text, embedding FROM documents WHERE workspace=%s ORDER BY id DESC LIMIT %s;",
                        (workspace, limit),
                    )
                    rows = cur.fetchall()
            out = []
            for source, text, emb in rows:
                out.append({"source": source, "text": text,
                            "embedding": json.loads(emb) if emb else None})
            return out
        except Exception:
            pass
    return _mem_store[workspace][-limit:]


def log_message(workspace: str, tokens: int = 0):
    if _backend == "postgres":
        try:
            import psycopg
            from app.config import settings
            with psycopg.connect(settings.database_url, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO usage (workspace, messages, tokens) VALUES (%s,1,%s)
                           ON CONFLICT (workspace) DO UPDATE SET
                           messages = usage.messages + 1, tokens = usage.tokens + %s;""",
                        (workspace, tokens, tokens),
                    )
            return
        except Exception:
            pass
    _mem_usage[workspace]["messages"] += 1
    _mem_usage[workspace]["tokens"] += tokens


def get_usage(workspace: str) -> dict:
    if _backend == "postgres":
        try:
            import psycopg
            from app.config import settings
            with psycopg.connect(settings.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT messages, docs, tokens FROM usage WHERE workspace=%s;", (workspace,))
                    row = cur.fetchone()
            if row:
                return {"workspace": workspace, "messages": row[0], "docs": row[1], "tokens": row[2]}
        except Exception:
            pass
    u = _mem_usage[workspace]
    return {"workspace": workspace, "messages": u["messages"], "docs": u["docs"], "tokens": u["tokens"]}
