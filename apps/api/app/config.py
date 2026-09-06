"""Central config — OpenAI-compatible, works with Ollama locally."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = "sk-change-me"
    openai_base_url: str = "https://api.openai.com/v1"
    embed_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    database_url: str = "postgresql://clientbrain:clientbrain@localhost:5432/clientbrain"
    workspace_default: str = "demo"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
