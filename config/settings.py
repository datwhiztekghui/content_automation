"""Application settings loaded from environment variables + optional profiles."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = parent of config/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHANNEL_STYLE_PATH = Path(__file__).resolve().parent / "channel_style.yaml"
PROFILES_DIR = Path(__file__).resolve().parent / "profiles"


class Settings(BaseSettings):
    """Runtime configuration for the content factory."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM provider selection
    # auto | ollama_cloud | ollama | xai | openai_compatible | none
    llm_provider: str = Field(default="auto", alias="LLM_PROVIDER")
    xai_api_key: str = Field(default="", alias="XAI_API_KEY")
    xai_base_url: str = Field(default="https://api.x.ai/v1", alias="XAI_BASE_URL")
    xai_model: str = Field(default="grok-4.5", alias="XAI_MODEL")

    # Ollama Cloud free tier (https://ollama.com/settings/keys)
    # Official env name is OLLAMA_API_KEY; we also accept OLLAMA_CLOUD_API_KEY
    ollama_cloud_api_key: str = Field(default="", alias="OLLAMA_CLOUD_API_KEY")
    ollama_api_key_env: str = Field(default="", alias="OLLAMA_API_KEY")
    ollama_cloud_base_url: str = Field(
        default="https://ollama.com/v1", alias="OLLAMA_CLOUD_BASE_URL"
    )
    ollama_cloud_model: str = Field(
        default="gpt-oss:20b", alias="OLLAMA_CLOUD_MODEL"
    )

    # Ollama local (free, OpenAI-compatible)
    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434/v1", alias="OLLAMA_BASE_URL"
    )
    ollama_model: str = Field(default="qwen2.5:7b", alias="OLLAMA_MODEL")
    ollama_api_key: str = Field(default="ollama", alias="OLLAMA_LOCAL_API_KEY")

    # Generic OpenAI-compatible (optional free tiers: Groq, etc.)
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1", alias="OPENAI_BASE_URL"
    )
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    # Search: auto | duckduckgo | tavily | serper | brave | none
    search_provider: str = Field(default="auto", alias="SEARCH_PROVIDER")
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    serper_api_key: str = Field(default="", alias="SERPER_API_KEY")
    brave_api_key: str = Field(default="", alias="BRAVE_API_KEY")
    x_bearer_token: str = Field(default="", alias="X_BEARER_TOKEN")

    # TTS: auto | edge | piper | elevenlabs | none
    tts_provider: str = Field(default="auto", alias="TTS_PROVIDER")
    edge_tts_voice: str = Field(default="en-GB-RyanNeural", alias="EDGE_TTS_VOICE")
    # Slightly slower than default improves word separation for tech scripts
    edge_tts_rate: str = Field(default="-8%", alias="EDGE_TTS_RATE")
    edge_tts_pitch: str = Field(default="+0Hz", alias="EDGE_TTS_PITCH")
    # Deprecated: edge-tts always uses plain text (library builds SSML internally)
    edge_tts_use_ssml: bool = Field(default=False, alias="EDGE_TTS_USE_SSML")
    piper_model_path: str = Field(default="", alias="PIPER_MODEL_PATH")

    # Voice (paid optional)
    elevenlabs_api_key: str = Field(default="", alias="ELEVENLABS_API_KEY")
    elevenlabs_voice_id: str = Field(default="", alias="ELEVENLABS_VOICE_ID")
    elevenlabs_model_id: str = Field(
        default="eleven_multilingual_v2", alias="ELEVENLABS_MODEL_ID"
    )

    # YouTube
    youtube_client_secrets: str = Field(default="", alias="YOUTUBE_CLIENT_SECRETS")
    youtube_credentials_path: str = Field(
        default="data/cache/youtube_credentials.json",
        alias="YOUTUBE_CREDENTIALS_PATH",
    )
    youtube_channel_id: str = Field(default="", alias="YOUTUBE_CHANNEL_ID")

    # Free control API (mobile remote)
    control_api_token: str = Field(default="dev-local-token", alias="CONTROL_API_TOKEN")
    control_api_host: str = Field(default="0.0.0.0", alias="CONTROL_API_HOST")
    control_api_port: int = Field(default=8787, alias="CONTROL_API_PORT")

    # Channel / runtime
    channel_name: str = Field(default="Clarion Frame", alias="CHANNEL_NAME")
    default_mode: str = Field(default="core", alias="DEFAULT_MODE")
    default_profile: str = Field(default="", alias="DEFAULT_PROFILE")
    auto_approve: bool = Field(default=False, alias="AUTO_APPROVE")
    headless: bool = Field(default=False, alias="HEADLESS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    data_dir: str = Field(default="data", alias="DATA_DIR")
    chunked_script: bool = Field(default=True, alias="CHUNKED_SCRIPT")

    # Runtime overrides applied by profile / CLI (not always from env)
    active_profile: str = Field(default="")

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def data_path(self) -> Path:
        path = Path(self.data_dir)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

    @property
    def runs_dir(self) -> Path:
        return self.data_path / "runs"

    @property
    def learnings_dir(self) -> Path:
        return self.data_path / "learnings"

    @property
    def cache_dir(self) -> Path:
        return self.data_path / "cache"

    @property
    def has_llm(self) -> bool:
        """True when any LLM backend is likely available."""
        provider = self.resolve_llm_provider()
        return provider not in {"none", ""}

    @property
    def has_search(self) -> bool:
        return self.resolve_search_provider() not in {"none", ""}

    def get_ollama_cloud_api_key(self) -> str:
        """Cloud key from OLLAMA_CLOUD_API_KEY or official OLLAMA_API_KEY."""
        return (self.ollama_cloud_api_key or self.ollama_api_key_env or "").strip()

    def resolve_llm_provider(self) -> str:
        p = (self.llm_provider or "auto").strip().lower()
        if p != "auto":
            return p
        # Free-first: Ollama Cloud → local Ollama → paid keys
        if self.get_ollama_cloud_api_key():
            return "ollama_cloud"
        if self.openai_api_key.strip():
            return "openai_compatible"
        if self.xai_api_key.strip():
            return "xai"
        return "ollama"

    def resolve_search_provider(self) -> str:
        p = (self.search_provider or "auto").strip().lower()
        if p != "auto":
            return p
        if self.tavily_api_key.strip():
            return "tavily"
        if self.serper_api_key.strip():
            return "serper"
        if self.brave_api_key.strip():
            return "brave"
        return "duckduckgo"

    def resolve_tts_provider(self) -> str:
        p = (self.tts_provider or "auto").strip().lower()
        if p != "auto":
            return p
        if self.elevenlabs_api_key.strip():
            return "elevenlabs"
        return "edge"

    def llm_connection(self) -> tuple[str, str, str]:
        """Return (base_url, api_key, model) for the resolved provider."""
        provider = self.resolve_llm_provider()
        if provider == "xai":
            return self.xai_base_url, self.xai_api_key, self.xai_model
        if provider == "ollama_cloud":
            return (
                self.ollama_cloud_base_url,
                self.get_ollama_cloud_api_key(),
                self.ollama_cloud_model,
            )
        if provider == "ollama":
            return (
                self.ollama_base_url,
                self.ollama_api_key or "ollama",
                self.ollama_model,
            )
        if provider == "openai_compatible":
            return self.openai_base_url, self.openai_api_key, self.openai_model
        raise ValueError(f"No LLM connection for provider={provider}")

    def load_channel_style(self) -> dict[str, Any]:
        if not CHANNEL_STYLE_PATH.exists():
            return {"channel_name": self.channel_name}
        with CHANNEL_STYLE_PATH.open(encoding="utf-8") as f:
            style = yaml.safe_load(f) or {}
        style.setdefault("channel_name", self.channel_name)
        return style

    def apply_profile(self, name: str) -> Settings:
        """Return a copy of settings with profile YAML overrides applied."""
        if not name:
            return self
        path = PROFILES_DIR / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Profile not found: {path}")
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        updates: dict[str, Any] = {"active_profile": name}
        if "llm_provider" in data:
            updates["llm_provider"] = data["llm_provider"]
        if "search_provider" in data:
            updates["search_provider"] = data["search_provider"]
        if "tts_provider" in data:
            # free.yaml uses "edge"
            updates["tts_provider"] = data["tts_provider"]
        if "chunked_script" in data:
            updates["chunked_script"] = bool(data["chunked_script"])
        if "auto_approve" in data:
            updates["auto_approve"] = bool(data["auto_approve"])

        ollama = data.get("ollama") or {}
        if ollama.get("base_url"):
            updates["ollama_base_url"] = ollama["base_url"]
        if ollama.get("model"):
            updates["ollama_model"] = ollama["model"]

        cloud = data.get("ollama_cloud") or {}
        if cloud.get("base_url"):
            updates["ollama_cloud_base_url"] = cloud["base_url"]
        if cloud.get("model"):
            updates["ollama_cloud_model"] = cloud["model"]

        edge = data.get("edge_tts") or {}
        if edge.get("voice"):
            updates["edge_tts_voice"] = edge["voice"]
        if edge.get("rate"):
            updates["edge_tts_rate"] = edge["rate"]
        if edge.get("pitch"):
            updates["edge_tts_pitch"] = edge["pitch"]

        return self.model_copy(update=updates)


_ACTIVE_SETTINGS: Settings | None = None


@lru_cache
def _cached_base_settings() -> Settings:
    return Settings()


def get_settings() -> Settings:
    """Return active (profile-aware) settings, or base env settings."""
    if _ACTIVE_SETTINGS is not None:
        return _ACTIVE_SETTINGS
    return _cached_base_settings()


def set_active_settings(settings: Settings | None) -> None:
    """Override process-wide settings (used by --profile and tests)."""
    global _ACTIVE_SETTINGS
    _ACTIVE_SETTINGS = settings


def reload_settings() -> Settings:
    global _ACTIVE_SETTINGS
    _ACTIVE_SETTINGS = None
    _cached_base_settings.cache_clear()
    return get_settings()


def load_profile(name: str) -> dict[str, Any]:
    path = PROFILES_DIR / f"{name}.yaml"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
