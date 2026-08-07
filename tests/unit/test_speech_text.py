from content_factory.tools.speech_text import narration_for_tts, normalize_spoken_text


def test_spaces_after_punctuation():
    assert "end. Start" in normalize_spoken_text("end.Start")


def test_unit_spacing():
    out = normalize_spoken_text("packs hit 300Wh/kg and 20% gains")
    assert "300 Wh" in out or "300 Wh" in out.replace("  ", " ")
    assert "percent" in out


def test_soft_hyphen_removed():
    glued = "inter\u00adfacial"
    assert "\u00ad" not in normalize_spoken_text(glued)


def test_ai_tells_stripped():
    out = normalize_spoken_text("Let's dive in to the landscape of AI.")
    assert "dive in" not in out.lower() or "Look" in out
    assert "landscape" not in out.lower()


def test_ssml_markup_never_reaches_tts_payload():
    dirty = (
        "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
        "xml:lang='en-GB'><voice name='en-GB-RyanNeural'>"
        "<prosody rate='-8%' pitch='+0Hz'>"
        "Hello world. "
        '<break time="320ms"/>'
        "Second sentence."
        "</prosody></voice></speak>"
    )
    out = narration_for_tts(dirty)
    assert "<speak" not in out.lower()
    assert "<break" not in out.lower()
    assert "prosody" not in out.lower()
    assert "xmlns" not in out.lower()
    assert "Hello world" in out
    assert "Second sentence" in out
    assert "<" not in out
    assert ">" not in out


def test_break_time_phrase_stripped():
    out = narration_for_tts('Hello break time="320ms" there')
    assert "break time" not in out.lower()
