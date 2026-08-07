"""Multi-provider LLM client — free-first (Ollama Cloud, local Ollama, xAI, OpenAI-compatible)."""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar

import httpx
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from config.settings import Settings, get_settings
from content_factory.utils.logging import get_logger

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


def ollama_local_reachable(
    settings: Settings | None = None, timeout: float = 1.5
) -> bool:
    settings = settings or get_settings()
    base = settings.ollama_base_url.rstrip("/")
    if base.endswith("/v1"):
        root = base[: -len("/v1")]
    else:
        root = base
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(f"{root}/api/tags")
            return resp.status_code == 200
    except Exception:  # noqa: BLE001
        return False


# Back-compat alias
def ollama_reachable(settings: Settings | None = None, timeout: float = 1.5) -> bool:
    return ollama_local_reachable(settings, timeout=timeout)


def ollama_cloud_configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(settings.get_ollama_cloud_api_key())


def ollama_cloud_reachable(
    settings: Settings | None = None, timeout: float = 5.0
) -> bool:
    """Lightweight auth check against ollama.com free cloud API."""
    settings = settings or get_settings()
    key = settings.get_ollama_cloud_api_key()
    if not key:
        return False
    base = settings.ollama_cloud_base_url.rstrip("/")
    # Prefer OpenAI-compatible models list; fall back to native /api/tags
    urls = []
    if base.endswith("/v1"):
        urls.append(f"{base}/models")
        urls.append(f"{base[: -len('/v1')]}/api/tags")
    else:
        urls.append(f"{base}/v1/models")
        urls.append(f"{base}/api/tags")
    headers = {"Authorization": f"Bearer {key}"}
    try:
        with httpx.Client(timeout=timeout) as client:
            for url in urls:
                try:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        return True
                    if resp.status_code in {401, 403}:
                        log.warning("Ollama Cloud auth failed (%s) for %s", resp.status_code, url)
                        return False
                except Exception:  # noqa: BLE001
                    continue
    except Exception as exc:  # noqa: BLE001
        log.debug("Ollama Cloud reachability check failed: %s", exc)
    return False


def resolve_active_provider(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    p = (settings.llm_provider or "auto").strip().lower()

    if p == "none":
        return "none"

    if p == "ollama_cloud":
        if ollama_cloud_configured(settings):
            return "ollama_cloud"
        # Soft fallback to local Ollama when cloud key missing
        if ollama_local_reachable(settings):
            log.warning("ollama_cloud selected but no API key — falling back to local Ollama")
            return "ollama"
        return "none"

    if p == "ollama":
        return "ollama" if ollama_local_reachable(settings) else "none"

    if p == "xai":
        return "xai" if settings.xai_api_key.strip() else "none"

    if p == "openai_compatible":
        return "openai_compatible" if settings.openai_api_key.strip() else "none"

    # auto — free-first
    if ollama_cloud_configured(settings):
        return "ollama_cloud"
    if ollama_local_reachable(settings):
        return "ollama"
    if settings.openai_api_key.strip():
        return "openai_compatible"
    if settings.xai_api_key.strip():
        return "xai"
    return "none"


def llm_available(settings: Settings | None = None) -> bool:
    return resolve_active_provider(settings) != "none"


def get_client(settings: Settings | None = None) -> tuple[OpenAI, str, str]:
    """Return (client, model, provider_name)."""
    settings = settings or get_settings()
    provider = resolve_active_provider(settings)
    if provider == "none":
        raise LLMError(
            "No LLM available. For free tier: set OLLAMA_API_KEY from "
            "https://ollama.com/settings/keys and use --profile free. "
            "Or install local Ollama / set another provider key."
        )

    if provider == "xai":
        base, key, model = settings.xai_base_url, settings.xai_api_key, settings.xai_model
    elif provider == "ollama_cloud":
        base = settings.ollama_cloud_base_url
        key = settings.get_ollama_cloud_api_key()
        model = settings.ollama_cloud_model
    elif provider == "ollama":
        base, key, model = (
            settings.ollama_base_url,
            settings.ollama_api_key or "ollama",
            settings.ollama_model,
        )
    else:
        base, key, model = (
            settings.openai_base_url,
            settings.openai_api_key,
            settings.openai_model,
        )

    client = OpenAI(api_key=key or "unused", base_url=base)
    return client, model, provider


def chat_text(
    system: str,
    user: str,
    *,
    settings: Settings | None = None,
    temperature: float = 0.4,
    max_tokens: int = 8192,
) -> str:
    settings = settings or get_settings()
    client, model, provider = get_client(settings)
    log.info("LLM call provider=%s model=%s temp=%.2f", provider, model, temperature)
    # Cap tokens for free/local backends to conserve quota
    if provider in {"ollama", "ollama_cloud"} and max_tokens > 4096:
        max_tokens = 4096
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    content = resp.choices[0].message.content or ""
    return content.strip()


def _extract_json(text: str) -> Any:
    """Parse JSON from raw model output, tolerating fenced blocks."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        for opener, closer in (("{", "}"), ("[", "]")):
            start = cleaned.find(opener)
            end = cleaned.rfind(closer)
            if start != -1 and end > start:
                try:
                    return json.loads(cleaned[start : end + 1])
                except json.JSONDecodeError:
                    continue
        raise


def _repair_truncated_json(text: str) -> Any | None:
    """Best-effort salvage when free-tier models cut off mid-JSON."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    # Extract narration if present even when rest of JSON is broken
    narr = re.search(
        r'"narration"\s*:\s*"((?:[^"\\]|\\.)*)(?:"|\Z)',
        cleaned,
        flags=re.DOTALL,
    )
    if narr:
        raw = narr.group(1)
        # Unescape common sequences
        try:
            narration = json.loads(f'"{raw}"')
        except json.JSONDecodeError:
            narration = raw.replace('\\"', '"').replace("\\n", "\n")
        if narration.strip():
            return {
                "narration": narration.strip(),
                "visual_cues": [],
                "on_screen_text": [],
                "source_callouts": [],
            }
    # Try closing open braces/brackets
    candidate = cleaned
    if candidate.count("{") > candidate.count("}"):
        candidate += "}" * (candidate.count("{") - candidate.count("}"))
    if candidate.count("[") > candidate.count("]"):
        candidate += "]" * (candidate.count("[") - candidate.count("]"))
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def chat_json(
    system: str,
    user: str,
    *,
    settings: Settings | None = None,
    temperature: float = 0.3,
    max_tokens: int = 8192,
) -> Any:
    text = chat_text(
        system
        + "\n\nRespond with valid JSON only. No markdown outside JSON. "
        "Keep strings compact enough to finish the JSON object fully.",
        user,
        settings=settings,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    try:
        return _extract_json(text)
    except json.JSONDecodeError as exc:
        repaired = _repair_truncated_json(text)
        if repaired is not None:
            log.warning("Salvaged truncated LLM JSON after parse error")
            return repaired
        log.error("Failed to parse LLM JSON: %s", text[:500])
        raise LLMError(f"Model did not return valid JSON: {exc}") from exc


def chat_model(
    system: str,
    user: str,
    model_type: type[T],
    *,
    settings: Settings | None = None,
    temperature: float = 0.3,
    max_tokens: int = 8192,
) -> T:
    data = chat_json(
        system,
        user
        + f"\n\nJSON schema guidance (fields):\n{json.dumps(model_type.model_json_schema(), indent=2)[:4000]}",
        settings=settings,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    try:
        if isinstance(data, list):
            raise ValidationError.from_exception_data(
                model_type.__name__,
                [
                    {
                        "type": "dict_type",
                        "loc": (),
                        "input": data,
                        "ctx": {},
                    }
                ],
            )
        return model_type.model_validate(data)
    except ValidationError as exc:
        raise LLMError(
            f"JSON failed schema validation for {model_type.__name__}: {exc}"
        ) from exc
