"""Prepare narration for natural, clearly spaced TTS (edge-tts friendly).

IMPORTANT: edge-tts expects PLAIN TEXT only. It builds its own internal SSML.
Never pass <speak>, <break>, or other markup to the synthesizer — it will be
read aloud as words.
"""

from __future__ import annotations

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

# Markup that must never be spoken (if accidentally present in source text)
SSML_OR_XML_RE = re.compile(
    r"</?\s*(?:speak|voice|prosody|break|p|s|emphasis|say-as|sub|audio|mark)"
    r"(?:\s[^>]*)?>",
    re.I,
)
XML_TAG_RE = re.compile(r"<[^>]+>")
XML_ATTR_SPEAK_RE = re.compile(
    r"\b(?:version|xmlns|xml:lang|name|rate|pitch|time)\s*=\s*['\"][^'\"]*['\"]",
    re.I,
)


def strip_ai_tells(text: str) -> str:
    out = text
    for pat, repl in AI_TELL_PATTERNS:
        out = pat.sub(repl, out)
    return out


def strip_ssml_and_markup(text: str) -> str:
    """Remove SSML/XML so synthesizers never read tags aloud."""
    t = text
    t = SSML_OR_XML_RE.sub(" ", t)
    t = XML_TAG_RE.sub(" ", t)
    t = XML_ATTR_SPEAK_RE.sub(" ", t)
    # Leftover phrases if tags were partially spoken from bad prior outputs
    t = re.sub(
        r"\b(?:speak version|xmlns|xml lang|prosody rate|prosody pitch|"
        r"break time|voice name)\b[:\s=]*",
        " ",
        t,
        flags=re.I,
    )
    return t


def normalize_spoken_text(text: str) -> str:
    """Clean narration so TTS speaks distinct words and natural pauses.

    Returns PLAIN TEXT only — safe to pass to edge-tts Communicate().
    """
    if not text:
        return ""

    t = unicodedata.normalize("NFKC", text)
    t = strip_ssml_and_markup(t)

    # Drop markdown / stage directions that shouldn't be spoken
    t = re.sub(r"```[\s\S]*?```", " ", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"^#+\s*", "", t, flags=re.M)

    # Unify dashes / quotes
    t = t.replace("\u2014", " — ")
    t = t.replace("\u2013", " – ")
    t = t.replace("\u2011", "-")
    t = t.replace("\u00ad", "")
    t = t.replace("\u00a0", " ")
    t = t.replace("\u200b", "")
    t = t.replace("\u200c", "").replace("\u200d", "")
    t = t.replace(""", '"').replace(""", '"')
    t = t.replace("'", "'").replace("'", "'")

    # Units / tech tokens: force space so TTS does not glue words
    t = re.sub(r"(\d)\s*[–—-]\s*(\d)", r"\1 to \2", t)
    t = re.sub(
        r"(\d)(Wh|kWh|mAh|GHz|MHz|GB|TB|MB|kg|km|mm|nm|ms|μs)\b",
        r"\1 \2",
        t,
        flags=re.I,
    )
    t = re.sub(r"(\d)%", r"\1 percent", t)
    t = re.sub(
        r"\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion|thousand)?",
        _expand_money_simple,
        t,
        flags=re.I,
    )
    t = re.sub(r"\b(\d+)x\b", r"\1 times", t, flags=re.I)

    # Missing space after punctuation
    t = re.sub(r"([.!?])([A-Z])", r"\1 \2", t)
    t = re.sub(r"([,;:])([A-Za-z])", r"\1 \2", t)
    t = re.sub(r"([a-z])([A-Z])", r"\1 \2", t)
    t = re.sub(r"([A-Za-z]{2,})/([A-Za-z]{2,})", r"\1 \2", t)

    # Plain-text pacing: keep sentence ends; paragraph → blank line for human read
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" *\n+ *", "\n\n", t)
    t = re.sub(r" {2,}", " ", t)
    t = t.strip()

    t = strip_ai_tells(t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" +([,.!?;:])", r"\1", t)
    t = re.sub(r"([.!?])([A-Za-z])", r"\1 \2", t)

    # Final safety: if any angle brackets remain, strip them
    t = re.sub(r"[<>]", " ", t)
    t = re.sub(r" {2,}", " ", t)
    return t.strip()


def _expand_money_simple(m: re.Match[str]) -> str:
    num = m.group(1).replace(",", "")
    scale = (m.group(2) or "").lower()
    if scale:
        return f"{num} {scale} dollars"
    return f"{num} dollars"


def narration_for_tts(text: str) -> str:
    """Plain text for edge-tts — never includes SSML/XML markup."""
    return normalize_spoken_text(text)
