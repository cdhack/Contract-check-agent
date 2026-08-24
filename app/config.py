from __future__ import annotations

import json
from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
SETTINGS_FILE = ROOT / "data" / "settings.json"

class LLMSettings(BaseModel):
    provider: str = "deepseek"
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    api_key: str = ""
    temperature: float = Field(default=0.1, ge=0, le=2)
    max_tool_rounds: int = Field(default=4, ge=1, le=4)

class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    llm_provider: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_temperature: float | None = None
    llm_max_tool_rounds: int | None = None

def get_settings() -> LLMSettings:
    values = json.loads(SETTINGS_FILE.read_text("utf-8")) if SETTINGS_FILE.exists() else {}
    env = EnvSettings()
    mapping = {"provider": env.llm_provider, "base_url": env.llm_base_url, "model": env.llm_model,
               "api_key": env.llm_api_key, "temperature": env.llm_temperature, "max_tool_rounds": env.llm_max_tool_rounds}
    values.update({k: v for k, v in mapping.items() if v is not None})
    return LLMSettings(**values)

def save_settings(settings: LLMSettings) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(settings.model_dump_json(indent=2), "utf-8")
