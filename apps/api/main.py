"""ClientBrain API — multi-tenant RAG core (Phase 1, no heavy deps)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import chat, ingest, system

app = FastAPI(title="ClientBrain API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router, prefix="/v1", tags=["system"])
app.include_router(ingest.router, prefix="/v1", tags=["ingest"])
app.include_router(chat.router, prefix="/v1", tags=["chat"])


@app.get("/")
def root():
    return {"name": "ClientBrain API", "docs": "/docs", "health": "/v1/health"}
