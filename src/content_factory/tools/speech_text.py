"""Prepare narration for natural, clearly spaced TTS (edge-tts friendly)."""

from __future__ import annotations

import html
import re
import unicodedata


# Phrases that sound robotic / AI-generated — strip or rewrite at polish time
AI_TELL_PATTERNS = [
    (re.compile(r"\bIn this (section|video|episode),?\s+we(?:'ll| will)\b", re.I), "Here's"),
    (re.compile(r"\bLet's dive (?:right )?in\b", re.I), "Look"),
    (re.compile(r"\bWithout further ado,?\s*", re.I), ""),
    (re.compile(r"\bIn conclusion,?\s*", re.I), "So — "),
    (re.compile(r"\bIt is (?:important|worth noting) (?:that|to)\b", re.I), "Keep in mind"),
    (re.compile(r"\bIn today's (?:fast-paced|digital) world,?\s*", re.I), ""),
    (re.compile(r"\bAs (?:an AI|a language model)\b", re.I), ""),
    (re.compile(r"\bDelve(?:s|d)? into\b", re.I), "look at"),
    (re.compile(r"\bTapestry of\b", re.I), "mix of"),
    (re.compile(r"\bLandscape of\b", re.I), "world of"),
    (re.compile(r"\bGame-?changer\b", re.I), "big shift"),
    (re.compile(r"\bUnlock(?:s|ing)? the (?:power|potential)\b", re.I), "open up"),
    (re.compile(r"\bRevolutioniz(?:e|es|ing)\b", re.I), "reshape"),
    (re.compile(r"\bCutting-?edge\b", re.I), "advanced"),
    (re.compile(r"\bAt the end of the day,?\s*", re.I), ""),
    (re.compile(r"\bIt's (?:important|crucial) to (?:note|understand) that\b", re.I), ""),
]


def strip_ai_tells(text: str) -> str:
    out = text
    for pat, repl in AI_TELL_PATTERNS:
        out = pat.sub(repl, out)
    return out


def normalize_spoken_text(text: str) -> str:
    """Clean narration so TTS speaks distinct words and natural pauses."""
    if not text:
        return ""

    t = unicodedata.normalize("NFKC", text)

    # Drop markdown / stage directions that shouldn't be spoken
    t = re.sub(r"```[\s\S]*?```", " ", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"^#+\s*", "", t, flags=re.M)

    # Unify dashes / quotes
    t = t.replace("\u2014", " — ")  # em dash → spaced
    t = t.replace("\u2013", " – ")
    t = t.replace("\u2011", "-")  # non-breaking hyphen
    t = t.replace("\u00ad", "")  # soft hyphen (causes word join bugs)
    t = t.replace("\u00a0", " ")  # nbsp
    t = t.replace("\u200b", "")  # zero-width space
    t = t.replace("\u200c", "").replace("\u200d", "")
    t = t.replace(""", '"').replace(""", '"')
    t = t.replace("'", "'").replace("'", "'")

    # Units / tech tokens: force space so TTS does not glue words
    t = re.sub(r"(\d)\s*[–—-]\s*(\d)", r"\1 to \2", t)
    t = re.sub(r"(\d)(Wh|kWh|mAh|GHz|MHz|GB|TB|MB|kg|km|mm|nm|ms|μs)\b", r"\1 \2", t, flags=re.I)
    t = re.sub(r"(\d)%", r"\1 percent", t)
    t = re.sub(
        r"\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion|thousand)?",
        _expand_money_simple,
        t,
        flags=re.I,
    )
    t = re.sub(r"\b(\d+)x\b", r"\1 times", t, flags=re.I)

    # Missing space after punctuation between words: "end.Start" → "end. Start"
    t = re.sub(r"([.!?])([A-Z])", r"\1 \2", t)
    t = re.sub(r"([,;:])([A-Za-z])", r"\1 \2", t)
    # Missing space before capital mid-sentence glue: "wordWord" is hard; fix camel only after lower
    t = re.sub(r"([a-z])([A-Z])", r"\1 \2", t)

    # Slash phrases: "and/or" ok; "power/density" → "power density"
    t = re.sub(r"([A-Za-z]{2,})/([A-Za-z]{2,})", r"\1 \2", t)

    # Collapse whitespace; keep paragraph breaks as double newline for SSML
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" *\n+ *", "\n\n", t)
    t = re.sub(r" {2,}", " ", t)
    t = t.strip()

    t = strip_ai_tells(t)
    # Second whitespace pass after phrase rewrites
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" +([,.!?;:])", r"\1", t)
    t = re.sub(r"([.!?])([A-Za-z])", r"\1 \2", t)
    return t.strip()


def _expand_money_simple(m: re.Match[str]) -> str:
    num = m.group(1).replace(",", "")
    scale = (m.group(2) or "").lower()
    if scale:
        return f"{num} {scale} dollars"
    return f"{num} dollars"


def to_ssml(
    text: str,
    *,
    voice: str = "en-GB-RyanNeural",
    rate: str = "-8%",
    pitch: str = "+0Hz",
    lang: str = "en-GB",
) -> str:
    """Build SSML with sentence/paragraph breaks for clearer word separation."""
    cleaned = normalize_spoken_text(text)
    if not cleaned:
        cleaned = " "

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]
    if not paragraphs:
        paragraphs = [cleaned]

    body_parts: list[str] = []
    for pi, para in enumerate(paragraphs):
        # Split on sentence end while keeping the terminator
        sentences = re.split(r"(?<=[.!?])\s+", para)
        sent_parts: list[str] = []
        for si, sent in enumerate(sentences):
            sent = sent.strip()
            if not sent:
                continue
            # Light comma breathing: already in text; escape XML
            safe = html.escape(sent, quote=True)
            # Prefer period endings for pause; if missing, still speak
            sent_parts.append(safe)
            if si < len(sentences) - 1:
                sent_parts.append('<break time="320ms"/>')
        body_parts.append(" ".join(sent_parts))
        if pi < len(paragraphs) - 1:
            body_parts.append('<break time="550ms"/>')

    inner = " ".join(body_parts)
    # edge-tts expects rate/pitch on Communicate kwargs OR in prosody
    return (
        f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='{lang}'>"
        f"<voice name='{html.escape(voice)}'>"
        f"<prosody rate='{html.escape(rate)}' pitch='{html.escape(pitch)}'>"
        f"{inner}"
        f"</prosody></voice></speak>"
    )


def narration_for_tts(text: str) -> str:
    """Plain text path (non-SSML): normalized spoken prose."""
    return normalize_spoken_text(text)
