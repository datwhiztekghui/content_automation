from config.settings import Settings, set_active_settings
from content_factory.tools.llm import resolve_active_provider
from content_factory.tools.web_search import _wikipedia


def test_settings_free_profile_overrides():
    base = Settings()
    free = base.apply_profile("free")
    assert free.llm_provider == "ollama_cloud"
    assert free.search_provider == "duckduckgo"
    assert free.tts_provider == "edge"
    assert free.chunked_script is True
    assert free.active_profile == "free"
    assert "ollama.com" in free.ollama_cloud_base_url


def test_ollama_cloud_key_aliases():
    s = Settings().model_copy(
        update={"ollama_cloud_api_key": "", "ollama_api_key_env": "sk-test-cloud"}
    )
    assert s.get_ollama_cloud_api_key() == "sk-test-cloud"
    s2 = Settings().model_copy(
        update={"ollama_cloud_api_key": "cloud-key", "ollama_api_key_env": "other"}
    )
    assert s2.get_ollama_cloud_api_key() == "cloud-key"


def test_resolve_llm_none_without_backends():
    s = base = Settings()
    s = base.model_copy(
        update={
            "llm_provider": "none",
            "xai_api_key": "",
            "openai_api_key": "",
        }
    )
    set_active_settings(s)
    try:
        assert resolve_active_provider(s) == "none"
    finally:
        set_active_settings(None)


def test_wikipedia_helper_returns_list():
    # Network-dependent; tolerate empty if offline
    results = _wikipedia("robotics", max_results=2)
    assert isinstance(results, list)
