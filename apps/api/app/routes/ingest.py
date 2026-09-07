import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app import db
from app.auth import PLANS, resolve_workspace
from app.embeddings import _hash_vec
from app.rag import chunk_text

router = APIRouter()


class TextIn(BaseModel):
    workspace: str = "demo"
    text: str
    source: str = "pasted-text"


class UrlIn(BaseModel):
    workspace: str = "demo"
    url: str


def _guard(ws: str, plan: str, new_chunks: int):
    quota = PLANS[plan]["docs"]
    if db.get_usage(ws)["docs"] + new_chunks > quota:
        raise HTTPException(status_code=402,
                            detail=f"doc quota exceeded for plan '{plan}' ({quota}). Upgrade at /v1/billing/plans")


def _embed(chunks: list[dict]):
    for c in chunks:
        c["embedding"] = _hash_vec(c["text"][:1000])
    return chunks


@router.post("/ingest/text")
def ingest_text(body: TextIn, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    ws, plan = resolve_workspace(body.workspace, x_api_key)
    chunks = _embed(chunk_text(body.text, body.source))
    _guard(ws, plan, len(chunks))
    n = db.add_docs(ws, chunks)
    return {"workspace": ws, "plan": plan, "chunks": n, "source": body.source}


@router.post("/ingest/url")
def ingest_url(body: UrlIn, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    ws, plan = resolve_workspace(body.workspace, x_api_key)
    try:
        r = httpx.get(body.url, timeout=20, follow_redirects=True)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)[:20000]
    except Exception as e:
        return {"error": f"fetch failed: {e}"}
    chunks = _embed(chunk_text(text, body.url))
    _guard(ws, plan, len(chunks))
    n = db.add_docs(ws, chunks)
    return {"workspace": ws, "plan": plan, "chunks": n, "source": body.url}
