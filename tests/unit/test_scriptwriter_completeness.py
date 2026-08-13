from content_factory.agents.scriptwriter.agent import (
    HARD_MAX_WORDS,
    MIN_TOTAL_WORDS,
    SECTION_PLAN,
    TARGET_TOTAL_WORDS,
    _expand_brief_section,
    _heuristic_script,
    _looks_bloated,
    _looks_incomplete,
    _trim_to_max,
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


def test_section_plan_has_min_and_max_words():
    assert len(SECTION_PLAN) == 7
    for row in SECTION_PLAN:
        assert len(row) == 8
        assert row[6] > 0  # min
        assert row[7] >= row[6]  # max >= min
    assert MIN_TOTAL_WORDS < TARGET_TOTAL_WORDS[0]
    assert HARD_MAX_WORDS >= TARGET_TOTAL_WORDS[1]


def test_looks_incomplete_flags_stubs():
    assert _looks_incomplete("", 50)
    assert _looks_incomplete("todo insert research here", 50)
    assert _looks_incomplete("Short.", 80)
    assert not _looks_incomplete("word " * 100, 80)


def test_looks_bloated_and_trim():
    assert _looks_bloated("word " * 200, 100)
    trimmed = _trim_to_max("One sentence. " * 50, 40)
    assert _word_count(trimmed) <= 40


def test_heuristic_script_meets_floor_not_bloated():
    script = _heuristic_script(_brief(), "Clarion Frame")
    # Tight hybrid: complete, not padded to old 1800–2400
    assert script.word_count >= 200
    assert script.word_count <= HARD_MAX_WORDS
    assert len(script.sections) == 7
    assert all(_word_count(s.narration) >= 20 for s in script.sections)
    assert "ByteDance" in script.full_narration or "parameter" in script.full_narration.lower()
    # Anti-bloat: no repeated "Picture" openers
    assert script.full_narration.lower().count("picture this") == 0


def test_expand_brief_section_not_empty():
    b = _brief()
    for sid, title, _g, target, *_rest in SECTION_PLAN:
        text = _expand_brief_section(b, sid, title, "Clarion Frame", target)
        assert _word_count(text) >= 15
        assert "placeholder" not in text.lower()
