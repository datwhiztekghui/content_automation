from content_factory.tools.speech_text import normalize_spoken_text, to_ssml


def test_spaces_after_punctuation():
    assert "end. Start" in normalize_spoken_text("end.Start")


def test_unit_spacing():
    out = normalize_spoken_text("packs hit 300Wh/kg and 20% gains")
    assert "300 Wh" in out or "300 Wh" in out.replace("  ", " ")
    assert "percent" in out


def test_soft_hyphen_removed():
    # soft hyphen often glues words in TTS
    glued = "inter\u00adfacial"
    assert "\u00ad" not in normalize_spoken_text(glued)


def test_ai_tells_stripped():
    out = normalize_spoken_text("Let's dive in to the landscape of AI.")
    assert "dive in" not in out.lower() or "Look" in out
    assert "landscape" not in out.lower()


def test_ssml_contains_breaks_and_voice():
    ssml = to_ssml(
        "First sentence. Second sentence.",
        voice="en-GB-RyanNeural",
        rate="-8%",
    )
    assert "en-GB-RyanNeural" in ssml
    assert "break" in ssml
    assert "First sentence" in ssml
