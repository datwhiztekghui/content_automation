from content_factory.agents.scriptwriter.agent import (
    MIN_TOTAL_WORDS,
    SECTION_PLAN,
    _expand_brief_section,
    _heuristic_script,
    _looks_incomplete,
    _word_count,
)
from content_factory.models.schemas import Citation, ResearchBrief


def _brief() -> ResearchBrief:
    return ResearchBrief(
        topic_title="ByteDance 10 Trillion Parameter Model",
        overview=(
            "ByteDance is reported to be training a foundation model at unprecedented scale. "
            "The claim centers on parameter count, data mixture, and competitive pressure "
            "from OpenAI, Google, and domestic Chinese labs."
        ),
        technical_details=(
            "Sparse and dense mixture-of-experts designs can inflate parameter counts while "
            "controlling active compute per token. Training clusters, interconnect, and "
            "data pipelines dominate cost. Inference economics may differ from training."
        ),
        benchmarks=(
            "Public head-to-head numbers remain thin. Prefer primary posts and independent "
            "evals over secondary recaps when scoring capability claims."
        ),
        implications=(
            "Enterprises watching China-scale models must plan for export controls, "
            "latency to users, and licensing. Creators care about quality and safety filters."
        ),
        historical_context=(
            "Parameter races have cycled through GPT-3, PaLM, Llama, and open Chinese models. "
            "Marketing often outruns independent verification."
        ),
        key_claims=[
            "Scale claim near 10 trillion parameters (verify primary source)",
            "ByteDance / TikTok parent competitive AI push",
        ],
        citations=[
            Citation(title="Primary report", url="https://example.com/report", publisher="Example")
        ],
        uncertainty_flags=["Parameter count may be sparse MoE marketing"],
    )


def test_section_plan_has_min_words():
    assert len(SECTION_PLAN) == 7
    for row in SECTION_PLAN:
        assert len(row) == 7
        assert row[6] > 0


def test_looks_incomplete_flags_stubs():
    assert _looks_incomplete("", 50)
    assert _looks_incomplete("todo insert research here", 50)
    assert _looks_incomplete("Short.", 80)
    assert not _looks_incomplete("word " * 100, 80)


def test_heuristic_script_meets_floor():
    script = _heuristic_script(_brief(), "Tech Frontier")
    assert script.word_count >= MIN_TOTAL_WORDS
    assert len(script.sections) == 7
    assert all(_word_count(s.narration) >= 40 for s in script.sections)
    assert "ByteDance" in script.full_narration or "parameter" in script.full_narration.lower()


def test_expand_brief_section_not_empty():
    b = _brief()
    for sid, title, _g, target, *_rest in SECTION_PLAN:
        text = _expand_brief_section(b, sid, title, "Tech Frontier", target)
        assert _word_count(text) >= 30
        assert "placeholder" not in text.lower()
