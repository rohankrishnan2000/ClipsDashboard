from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    openai_api_key: str | None = None
    openai_transcription_model: str = "whisper-1"
    openai_clip_model: str = "gpt-4.1-mini"
    data_dir: Path = BACKEND_DIR / "data"
    frontend_origin: str = "http://localhost:5173"
    llm_chunk_seconds: int = 600
    audio_segment_seconds: int = 600

    model_config = SettingsConfigDict(
        env_file=(PROJECT_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
