"""ClientBrain API — Phase 2: auth + billing + pgvector-ready."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import settings
from app.routes import admin, billing, chat, ingest, system

db.init_db(settings.database_url)

app = FastAPI(title="ClientBrain API", version="0.2.0")

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
app.include_router(billing.router, prefix="/v1", tags=["billing"])
app.include_router(admin.router, prefix="/v1", tags=["admin"])


@app.get("/")
def root():
    return {"name": "ClientBrain API", "version": "0.2.0",
            "docs": "/docs", "health": "/v1/health", "backend": db.backend()}
