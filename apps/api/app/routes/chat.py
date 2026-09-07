import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app import db
from app.auth import PLANS, resolve_workspace
from app.config import settings
from app.embeddings import rank
from app.rag import chunk_text

router = APIRouter()


class ChatIn(BaseModel):
    workspace: str = "demo"
    message: str
    top_k: int = 4


async def _llm_answer(message: str, context: list[dict]) -> tuple[str, int]:
    if not context:
        return "I don't have that in your docs yet. Ingest your website or PDF first.", 0
    if not settings.openai_api_key or settings.openai_api_key.startswith("sk-change"):
        cites = "\n".join(f"- {c['text'][:300]} [source: {c['source']}]" for c in context)
        return f"Based on your docs:\n{cites}", len(message) // 4
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
                json={"model": settings.chat_model,
                      "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.2},
            )
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
            return text, len(prompt + text) // 4
    except Exception as e:
        fallback = "\n".join(f"- {c['text'][:300]} [source: {c['source']}]" for c in context)
        return f"(live LLM failed: {e})\nTop matches:\n{fallback or 'none'}", len(message) // 4


@router.post("/chat")
async def chat(body: ChatIn, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    ws, plan = resolve_workspace(body.workspace, x_api_key)
    quota = PLANS[plan]["messages"]
    usage = db.get_usage(ws)
    if usage["messages"] >= quota:
        raise HTTPException(status_code=402,
                            detail=f"message quota exceeded for plan '{plan}' ({quota}). Upgrade at /v1/billing/plans")
    docs = db.get_docs(ws)
    hits = rank(body.message, docs, body.top_k)
    answer, tokens = await _llm_answer(body.message, hits)
    db.log_message(ws, tokens)
    return {"workspace": ws, "plan": plan, "answer": answer,
            "sources": [{"source": h["source"], "snippet": h["text"][:300]} for h in hits],
            "usage": db.get_usage(ws)}
