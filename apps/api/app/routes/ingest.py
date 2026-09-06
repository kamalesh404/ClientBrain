import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter
from pydantic import BaseModel

from app.rag import chunk_text
from app.store import add_docs

router = APIRouter()


class TextIn(BaseModel):
    workspace: str = "demo"
    text: str
    source: str = "pasted-text"


class UrlIn(BaseModel):
    workspace: str = "demo"
    url: str


@router.post("/ingest/text")
def ingest_text(body: TextIn):
    chunks = chunk_text(body.text, body.source)
    n = add_docs(body.workspace, chunks)
    return {"workspace": body.workspace, "chunks": n, "source": body.source}


@router.post("/ingest/url")
def ingest_url(body: UrlIn):
    try:
        r = httpx.get(body.url, timeout=20, follow_redirects=True)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)[:20000]
    except Exception as e:
        return {"error": f"fetch failed: {e}"}
    chunks = chunk_text(text, body.url)
    n = add_docs(body.workspace, chunks)
    return {"workspace": body.workspace, "chunks": n, "source": body.url}
