"""Central config — OpenAI-compatible, works with Ollama locally."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = "sk-change-me"
    openai_base_url: str = "https://api.openai.com/v1"
    embed_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    database_url: str = "postgresql://clientbrain:clientbrain@localhost:5432/clientbrain"
    workspace_default: str = "demo"
    # Phase 2 — auth & billing
    master_api_key: str = "cb_admin_change-me"
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    billing_enabled: bool = False  # set True when keys present

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
