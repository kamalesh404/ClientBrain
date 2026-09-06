import os
import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.rag import retrieve
from app.store import get_docs, log_message

router = APIRouter()


class ChatIn(BaseModel):
    workspace: str = "demo"
    message: str
    top_k: int = 4


async def _llm_answer(message: str, context: list[dict]) -> str:
    """Call OpenAI-compatible chat API; fallback to extractive answer offline."""
    if not settings.openai_api_key or settings.openai_api_key.startswith("sk-change"):
        if not context:
            return "I don't have that in your docs yet. Ingest your website or PDF first."
        cites = "\n".join(f"- {c['text'][:300]} [source: {c['source']}]" for c in context)
        return f"Based on your docs:\n{cites}"
    ctx = "\n\n".join(f"[{c['source']}] {c['text'][:1200]}" for c in context)
    prompt = (
        "You are ClientBrain, a business support bot. Answer ONLY from CONTEXT. "
        "Add [source: X] citations. If missing, say you don't have it.\n\n"
        f"CONTEXT:\n{ctx}\n\nQUESTION: {message}"
    )
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(
                f"{settings.openai_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.chat_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                },
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        fallback = "\n".join(f"- {c['text'][:300]} [source: {c['source']}]" for c in context)
        return f"(live LLM failed: {e})\nTop matches:\n{fallback or 'none'}"


@router.post("/chat")
async def chat(body: ChatIn):
    docs = get_docs(body.workspace)
    hits = retrieve(body.message, docs, body.top_k)
    answer = await _llm_answer(body.message, hits)
    log_message(body.workspace)
    return {
        "workspace": body.workspace,
        "answer": answer,
        "sources": [{"source": h["source"], "snippet": h["text"][:300]} for h in hits],
    }
