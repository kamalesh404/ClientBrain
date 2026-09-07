"""Embeddings: OpenAI API when key exists, else offline hash vectors.

Keeps Phase 2 light (no torch/sentence-transformers) while giving
better-than-keyword ranking via cosine similarity.
"""
import hashlib
import math

import httpx

from app.config import settings

DIM = 128


def _hash_vec(text: str, dim: int = DIM) -> list[float]:
    vec = [0.0] * dim
    for tok in text.lower().split():
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16) % dim
        vec[h] += 1.0
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def _cos(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


async def embed(texts: list[str]) -> list[list[float]]:
    if settings.openai_api_key and not settings.openai_api_key.startswith("sk-change"):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{settings.openai_base_url}/embeddings",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={"model": settings.embed_model, "input": texts[:32]},
                )
                r.raise_for_status()
                return [d["embedding"][:DIM] + [0.0] * max(0, DIM - len(d["embedding"]))
                        for d in r.json()["data"]]
        except Exception:
            pass
    return [_hash_vec(t) for t in texts]


def rank(query: str, docs: list[dict], top_k: int = 4) -> list[dict]:
    """Keyword overlap first, hash-vector cosine as tiebreak."""
    import re
    qvec = _hash_vec(query)
    scored = []
    qtok = set(re.findall(r"[a-z0-9]+", query.lower()))
    for d in docs:
        dtok = set(re.findall(r"[a-z0-9]+", d["text"].lower()))
        overlap = len(qtok & dtok)
        cos = _cos(qvec, d.get("embedding") or _hash_vec(d["text"][:500]))
        scored.append((overlap * 2 + cos, d))
    scored.sort(key=lambda x: x[0], reverse=True)
    # keep at least keyword hits; if none, return top cosine hits only when query shares nothing?
    # Honest behavior: return only overlap>0 unless store is tiny (demo mode)
    hits = [d for s, d in scored if s > 0.05][:top_k]
    kw = [d for d in hits if len(qtok & set(re.findall(r"[a-z0-9]+", d["text"].lower()))) > 0]
    return kw if kw else ([] if len(docs) > 10 else hits)
