# AGENTS.md — Content Factory Roles, Tools & Channel Voice

This document is the **source of truth** for every specialized agent in the pipeline.  
Orchestration is LangGraph; each agent is a modular Python package under `src/content_factory/agents/`.

---

## Channel identity

| Field | Value |
|--------|--------|
| Working name | **Tech Frontier** (override via `CHANNEL_NAME` / `config/channel_style.yaml`) |
| Niche | Tech, inventions, robotics, AI breakthroughs, science, and related news |
| Peer style | Clear, high-retention explainers (inspired by channels like AI Revolution, but **broader than pure AI**) |
| Audience | Curious professionals and smart generalists |

### Voice & tone (non-negotiable)

- **Excited but analytical** — energy without empty hype  
- **Clear, authoritative, accessible** — explain hard ideas without dumbing down  
- **Cite on screen** where claims and numbers appear  
- **Soft CTA only** — free resource, next video, community — never hard sell  
- **Avoid:** unfounded claims, clickbait the script cannot pay off, jargon without a plain-language bridge  

### Canonical script arc (12–16 minutes)

1. **Hook** (15–30s) — cold open; concrete claim or tension  
2. **Why it matters** — stakes  
3. **Explanation** — how it works  
4. **Benchmarks / demos** — evidence  
5. **Implications** — business / geo / industry / society  
6. **Bigger picture** — history and arc  
7. **CTA** — soft close  

Style knobs also live in `config/channel_style.yaml` and are injected into prompts.

---

## Pipeline overview

```
trend_scout → [HITL topic] → deep_research → scriptwriter
  → fact_checker → [HITL script] → voice_director → visual_director
  → video_assembler → seo_packaging → distribution → analytics
```

Modes:

| Mode | Stages |
|------|--------|
| `scout` | trend_scout |
| `core` | research path through fact_checker + script gate |
| `media` | core + voice + visual + assemble |
| `publish` | media + seo + distribution |
| `full` | all stages |
| `analytics` | analytics only |

---

## Shared contracts

- **State:** `PipelineState` in `state.py`  
- **Schemas:** Pydantic models in `models/schemas.py`  
- **Artifacts:** `data/runs/<run_id>/` (JSON + Markdown)  
- **LLM:** xAI Grok via `XAI_API_KEY` (`tools/llm.py`)  
- **HITL:** `gates/approval.py` (interactive prompts or headless decision files)

---

## 1. Trend Scout Agent

| | |
|--|--|
| **Package** | `agents/trend_scout` |
| **Stage** | `trend_scout` |
| **Goal** | Continuously discover and rank high-potential topics |
| **Inputs** | Optional `topic_hint`, channel style, optional learnings priors |
| **Outputs** | Ranked `TopicCandidate[]` → `topics/candidates.json` + `.md` |
| **Tools** | RSS feeds, web search (Tavily/Serper/Brave), arXiv, LLM ranking |
| **Scoring** | virality, uniqueness, competition (inverted in composite), channel fit |

**Why it matters field:** every candidate must explain audience stakes in plain language.

**Quality bar:** Prefer timely primary signals. Do not invent source URLs.

---

## 2. Deep Research Agent

| | |
|--|--|
| **Package** | `agents/deep_research` |
| **Stage** | `deep_research` |
| **Goal** | Produce an extremely accurate, citation-rich research brief |
| **Inputs** | `approved_topic` |
| **Outputs** | `ResearchBrief` → `research/brief.json` + `.md` |
| **Tools** | Web search, arXiv, seed sources from topic, LLM synthesis |

**Brief sections:** overview, technical details, benchmarks, expert reactions, historical context, implications, open questions, key claims, citations, uncertainty flags.

**Accuracy policy:** No invented stats. Uncertainty must be flagged. Prefer primary sources.

---

## 3. Scriptwriter Agent

| | |
|--|--|
| **Package** | `agents/scriptwriter` |
| **Stage** | `scriptwriter` |
| **Goal** | High-retention 12–16 minute script in channel voice |
| **Inputs** | `ResearchBrief` + channel style |
| **Outputs** | `VideoScript` → `script/draft.json` + `.md` + `narration.txt` |

**Must include:** timestamps, visual cues, on-screen text, source callouts, soft CTA.

**Word target:** ~1,800–2,400 words (~150 wpm).

---

## 4. Fact-Checker & Editor Agent

| | |
|--|--|
| **Package** | `agents/fact_checker` |
| **Stage** | `fact_checker` |
| **Goal** | Accuracy, flow, retention, brand voice, policy review |
| **Inputs** | Script draft + research brief |
| **Outputs** | Revised `script/final.*` + `script/changelog.json` |

**Change categories:** `accuracy` | `flow` | `retention` | `voice` | `policy`  
**Severity:** `info` | `warning` | `critical`

Prefer under-claiming over hallucinated polish.

---

## 5. Voice Director Agent

| | |
|--|--|
| **Package** | `agents/voice_director` |
| **Stage** | `voice_director` |
| **Goal** | Optimal voice settings, full VO, timed markers |
| **Inputs** | Approved script |
| **Outputs** | `VoicePackage` → `voice/` |
| **Tools** | ElevenLabs (`ELEVENLABS_*`); **dry-run by default** |

Dry-run writes narration text + marker plan without API spend.

---

## 6. Visual Director Agent

| | |
|--|--|
| **Package** | `agents/visual_director` |
| **Stage** | `visual_director` |
| **Goal** | **News-grounded** creative direction: story-linked shots, proof cards, brand-trust visuals, thumbnails |
| **Inputs** | Final script + **research brief** + live news search |
| **Outputs** | `VisualPackage` + `creative_strategy.json` + `story_beats.json` + Imagine queue → `visuals/` |

**Competitive bar:** AI Revolution–class tech news  
(ref: dense cuts, kinetic numbers, logos, real people, product UI —  
see `config/channel_visual_style.yaml`).

**Credibility + retention rules (non-negotiable):**
- Mix: `kinetic_stat` · `logo_card` · `person_plate` · `ui_screen` · `cinematic_broll` · `comparison_card` · `geo_map` · `timeline`
- **Companies → logos ON the image** where the story is about that company (sharp brand mark / holographic sign)
- **Burned-in titles** for the main claim on hero frames (peer style); CapCut for extra captions
- **CEOs / public figures → REAL photos** when they drive the news (capture / reference-first — never invent faces)
- **Proof screenshots** of real articles/product pages
- **Thumbnails:** hero (robot/CEO/product) + logo + 2–6 word mega text
- **Only ban AI watermarks** (Gemini/Grok/Midjourney stamps) — not logos or titles
- Hook cuts ~2–4s; body ~4–7s
- Gemini handoff: `scripts/build_gemini_prompts.py` → `visuals/GEMINI_PROMPTS.md`

---

## 7. Video Assembler Agent

| | |
|--|--|
| **Package** | `agents/video_assembler` |
| **Stage** | `video_assembler` |
| **Goal** | Make final edit fast for a human editor |
| **Inputs** | Script, voice package, visual package |
| **Outputs** | Edit bible + asset manifest → `assembly/` |

v1 does **not** reverse-engineer CapCut binaries. It produces an import-ready **edit bible** for CapCut / Descript / Premiere.

---

## 8. SEO & Packaging Agent

| | |
|--|--|
| **Package** | `agents/seo_packaging` |
| **Stage** | `seo_packaging` |
| **Goal** | Titles, description (chapters), tags, end screen, Shorts/Reels hooks |
| **Inputs** | Final script + topic |
| **Outputs** | `SEOPackage` → `seo/` |

Titles must be optimized **and** honest. 5–8 Shorts/Reels hooks with captions.

---

## 9. Distribution Agent

| | |
|--|--|
| **Package** | `agents/distribution` |
| **Stage** | `distribution` |
| **Goal** | YouTube upload/schedule + cross-post packages |
| **Inputs** | SEO package + media artifacts |
| **Outputs** | `distribution/results.json` + per-platform post files |

**v1:** YouTube live upload is stubbed until OAuth is configured; all platforms get ready-to-post packages.  
Platforms: YouTube, X, Instagram, TikTok, LinkedIn, Threads.

---

## 10. Analytics & Learning Agent

| | |
|--|--|
| **Package** | `agents/analytics` |
| **Stage** | `analytics` |
| **Goal** | Pull performance data; feed insights back into topic/script priors |
| **Inputs** | Optional `analytics/manual_metrics.json` or future YouTube Analytics |
| **Outputs** | Snapshot + append to `data/learnings/insights.jsonl` |

---

## Human-in-the-loop gates

| Gate | Stage | Interactive | Headless |
|------|--------|-------------|----------|
| Topic | `await_topic` | Choose index / custom title | `approvals/topic_decision.json` |
| Script | `await_script` | Y/n | `approvals/script_decision.json` with `{"approve": true}` |

`--auto-approve` bypasses gates (demos/CI only). Default is **off**.

---

## Tooling map

| Tool | Module | Env |
|------|--------|-----|
| LLM (free) | `tools/llm.py` | **Ollama Cloud** (`OLLAMA_API_KEY`) or local Ollama; provider `auto\|ollama_cloud\|ollama\|xai\|none` |
| LLM (paid optional) | `tools/llm.py` | `XAI_API_KEY`, `XAI_MODEL` |
| Web search (free) | `tools/web_search.py` | DuckDuckGo + Wikipedia (no key) |
| Web search (paid optional) | same | `TAVILY_API_KEY` / Serper / Brave |
| arXiv | `tools/arxiv_tool.py` | — |
| RSS | `tools/news_feeds.py` | — |
| TTS (free) | `tools/tts.py` | edge-tts (`EDGE_TTS_VOICE`); Piper optional |
| ElevenLabs (paid optional) | voice agent | `ELEVENLABS_*` |
| YouTube | distribution (planned) | `YOUTUBE_CLIENT_SECRETS` (OAuth free) |
| Free profile | `config/profiles/free.yaml` | `--profile free` |

---

## Agent implementation rules

1. Each agent exposes `run_<name>(state: PipelineState) -> dict` partial state update.  
2. Always write durable artifacts under the run folder.  
3. Degrade gracefully without API keys (heuristic / dry-run paths).  
4. Never hardcode secrets.  
5. Prefer structured JSON validated by Pydantic before writing.  
6. Keep prompts aligned with this document and `channel_style.yaml`.  
7. **Git discipline:** after every new implementation or modification, commit and push to GitHub before moving on (never leave uncommitted work).

---

## Expansion hooks

- Vector store over `data/learnings/` for smarter Trend Scout priors  
- Live ElevenLabs multi-segment synthesis with word-level timestamps  
- YouTube Data API upload + Analytics API  
- Structured CapCut/Descript project exporters  
- Additional social adapters with native APIs  

When adding an agent or tool, update this file in the same PR.
