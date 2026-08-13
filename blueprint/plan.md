# Content Factory — Architecture & Implementation Plan

## Goal

Build a **modular, production-ready Python multi-agent content factory** for a YouTube channel covering tech, inventions, robotics, AI breakthroughs, science, and related news (broader than pure-AI channels; style inspired by AI Revolution–class explainers).

The system must support:
- Interactive CLI runs and fully headless/scheduled runs
- Human-in-the-loop (HITL) approval gates (topic + final script minimum)
- Partial pipelines (e.g. research + scripting only)
- Clean expansion path for more platforms, video tools, and learning memory

---

## Recommended stack (with rationale)

| Layer | Choice | Why |
|--------|--------|-----|
| Orchestration | **LangGraph** | Stateful pipeline, conditional stages, checkpoint/resume, native interrupt for HITL, production headless runs |
| Agent roles | **Plain Python modules + Pydantic I/O** | CrewAI-style clarity (one role per package) without dual-framework complexity |
| LLM | **xAI Grok** via OpenAI-compatible client (`XAI_API_KEY`, `https://api.x.ai/v1`, default `grok-4.5`) | Aligns with xAI tooling; single primary provider; swappable later |
| Config | `pydantic-settings` + `.env` | Typed settings, all secrets via env |
| CLI | `typer` | Clean `run.py` / `python -m content_factory` UX |
| Schemas | Pydantic v2 models | Shared contracts between agents and disk artifacts |
| Persistence (v1) | Filesystem JSON/Markdown under `data/` + optional SQLite for analytics | Simple, git-friendly, no infra required |
| Voice | ElevenLabs API (optional stage) | Industry standard VO |
| Video gen prompts | Provider-agnostic prompt packs (Kling / Runway / Grok Imagine / stock) | No hard lock-in |
| Distribution | YouTube Data API v3 first; other platforms as stub adapters | Real upload path where it matters most |
| Scheduling | CLI + OS scheduler (Task Scheduler / cron) wrapping `run.py --mode full --headless` | Avoid heavy job infra in v1 |

**Why not CrewAI as the core?** CrewAI shines for simple role collaboration. This product needs **branching stages, skippable modules, approval interrupts, checkpoint resume, and analytics feedback** — LangGraph maps cleanly to that. We still document every agent like a Crew (role, goal, tools, I/O) in `AGENTS.md`.

**Fallback if you prefer CrewAI:** Same package layout; replace `graph.py` with CrewAI Flows / sequential crews. Not recommended for v1 production HITL.

---

## High-level architecture

```
                    ┌─────────────────────────┐
                    │  CLI (typer) / Scheduler │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  LangGraph Pipeline      │
                    │  (checkpointed state)    │
                    └───────────┬─────────────┘
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
   [enabled stages]      [HITL interrupts]     [artifact store]
          │                     │                     │
   Agent modules          approve topic          data/runs/<id>/
   (tools + LLM)          approve script         topics, research,
                                                 scripts, audio,
                                                 visuals, seo, etc.
```

### Pipeline stages (nodes)

```
trend_scout → [HITL: approve topic] → deep_research → scriptwriter
  → fact_checker → [HITL: approve script] → voice_director → visual_director
  → video_assembler → seo_packaging → distribution → analytics
```

Each stage is **optional via feature flags** (`--stages research,script` or config profile `core|media|full`).

### Shared state (typed)

`PipelineState` (TypedDict / Pydantic) roughly:

- `run_id`, `mode`, `channel_config`
- `topic_candidates[]`, `approved_topic`
- `research_brief`
- `script_draft`, `script_final`, `edit_changelog`
- `voiceover_paths`, `timing_markers`
- `shot_list`, `broll_prompts`, `thumbnail_concepts`
- `assembly_package` (edit instructions + asset list)
- `seo_package` (title, description, tags, shorts)
- `publish_results`, `analytics_snapshot`
- `errors[]`, `approvals{}`, `stage_status{}`

Artifacts are **also written to disk** so partial runs and human review work without replaying the whole graph.

---

## Project structure

```
content_automation/
├── AGENTS.md                 # Roles, tools, channel voice (source of truth)
├── README.md                 # Setup, architecture, usage
├── .env.example
├── pyproject.toml            # modern packaging + deps
├── run.py                    # thin CLI entrypoint
├── config/
│   ├── settings.py           # pydantic-settings
│   └── channel_style.yaml    # tone, structure, CTA patterns, forbidden phrases
├── src/
│   └── content_factory/
│       ├── __init__.py
│       ├── cli.py
│       ├── state.py
│       ├── graph.py          # LangGraph definition + interrupts
│       ├── models/
│       │   └── schemas.py    # TopicCandidate, ResearchBrief, Script, etc.
│       ├── agents/
│       │   ├── base.py       # shared agent runner (LLM + prompt + validate)
│       │   ├── trend_scout/
│       │   ├── deep_research/
│       │   ├── scriptwriter/
│       │   ├── fact_checker/
│       │   ├── voice_director/
│       │   ├── visual_director/
│       │   ├── video_assembler/
│       │   ├── seo_packaging/
│       │   ├── distribution/
│       │   └── analytics/
│       ├── tools/
│       │   ├── llm.py        # xAI client wrapper
│       │   ├── web_search.py
│       │   ├── arxiv_tool.py
│       │   ├── news_feeds.py
│       │   ├── elevenlabs_tool.py
│       │   ├── youtube_tool.py
│       │   └── social_stubs.py
│       ├── gates/
│       │   └── approval.py   # CLI + file-based HITL for headless
│       ├── memory/
│       │   └── learnings.py  # analytics → insights store (v1 JSON/SQLite)
│       └── utils/
│           ├── artifacts.py  # run folders, write md/json
│           └── logging.py
├── data/
│   ├── runs/                 # per-run outputs (gitignored)
│   ├── learnings/            # aggregated insights
│   └── cache/                # optional search/API cache
├── prompts/                  # versioned system prompts (optional mirror of AGENTS)
├── tests/
│   ├── unit/
│   └── fixtures/
└── scripts/
    └── schedule_example.ps1  # Windows Task Scheduler example
```

---

## Channel style (embedded deeply)

Captured in `AGENTS.md` + `config/channel_style.yaml` and injected into Scriptwriter / Fact-Checker / SEO prompts:

| Dimension | Rule |
|-----------|------|
| Tone | Excited but analytical; clear, authoritative, accessible |
| Hook | 15–30s cold open; concrete claim or tension before intro |
| Arc | Hook → why it matters → clear explanation → benchmarks/demos → implications → bigger picture → soft CTA |
| Length target | 12–16 minutes spoken (~1,800–2,400 words depending on pace) |
| Citations | On-screen source cues in script; research brief is citation-rich |
| CTA | Soft: free resource, next video, community — never hard sell |
| Avoid | Hype without substance, unfounded claims, clickbait that the script cannot pay off |

Working channel name: **"Clarion Frame"** (override via `CHANNEL_NAME` / `config/channel_style.yaml`).

---

## Agent contracts (I/O)

### 1. Trend Scout
- **In:** mode flags, optional seed keywords, learnings priors
- **Out:** `list[TopicCandidate]` ranked by: virality, uniqueness, competition, channel fit
- **Fields:** title, summary, why_it_matters, sources[], scores{}, suggested_angle
- **Tools:** web/news search, arXiv, RSS/company blogs, (optional) X search when keys present
- **Notes:** v1 uses public web + arXiv + curated RSS; X is optional adapter

### 2. Deep Research
- **In:** approved topic + initial sources
- **Out:** `ResearchBrief` (sections: overview, tech details, benchmarks, expert reactions, history, geo/business implications, open questions, citations[])
- **Quality bar:** Prefer primary sources; flag uncertainty; no invented stats

### 3. Scriptwriter
- **In:** ResearchBrief + style config
- **Out:** `VideoScript` with sections, approximate timestamps, visual cues, on-screen text, source callouts, word count / estimated runtime

### 4. Fact-Checker & Editor
- **In:** Script + ResearchBrief
- **Out:** revised script + `ChangeLog[]` (accuracy, flow, retention, voice, policy)

### 5. Voice Director
- **In:** approved script
- **Out:** audio file(s), voice settings used, timed markers JSON
- **Integration:** ElevenLabs; dry-run mode writes SSML/text + marker plan without API spend

### 6. Visual Director
- **In:** script + markers
- **Out:** shot list, B-roll prompts (multi-provider), lower-thirds, 3–5 thumbnail concepts with overlay text

### 7. Video Assembler
- **In:** script, audio markers, visuals package
- **Out:** **v1:** detailed edit bible + asset manifest (import-ready for CapCut/Descript humans)  
  **v1.1:** structured project JSON schema we own (not fragile binary reverse-engineering)

### 8. SEO & Packaging
- **In:** final script + topic
- **Out:** title options, description w/ chapters, tags, end screen, 5–8 Shorts/Reels hooks + captions

### 9. Distribution
- **In:** packaged assets + SEO + schedule time
- **Out:** upload/schedule results per platform
- **v1:** YouTube upload/schedule real; X/IG/TikTok/LinkedIn/Threads = adapter stubs that write ready-to-post packages (or post if credentials present)

### 10. Analytics & Learning
- **In:** video_id / run_id after publish
- **Out:** metrics snapshot + extracted insights written to `data/learnings/` for Trend Scout / Scriptwriter priors
- **v1:** YouTube Analytics when OAuth available; otherwise manual metrics import JSON

---

## Human-in-the-loop design

Two mandatory gates (configurable):

1. **Topic approval** — after Trend Scout (or after `--topic` still optional confirm)
2. **Script approval** — after Fact-Checker

Modes:
- **Interactive:** terminal prompt (`y/n/edit`)
- **Headless:** write `data/runs/<id>/pending_approval.json`; poll or require `--approve-file` / auto-approve flag only if explicitly set (`--auto-approve` for CI demos, default off)

LangGraph `interrupt_before` / checkpointing so a run can pause and resume.

---

## CLI design

```bash
# Discover topics only
python run.py --mode scout

# Full pipeline with HITL
python run.py --mode full

# Forced topic, core content only
python run.py --mode core --topic "Kimi K3 release"

# Explicit stages
python run.py --stages research,script,factcheck --topic "..."

# Headless scheduled
python run.py --mode full --headless --run-id auto

# Resume after approval
python run.py --resume <run_id> --approve-topic

# Dry-run media (no ElevenLabs / no upload)
python run.py --mode full --dry-run-media
```

**Mode presets:**

| Mode | Stages |
|------|--------|
| `scout` | trend_scout |
| `core` | research → script → factcheck (+ HITL) |
| `media` | core + voice + visual + assemble |
| `publish` | media + seo + distribution |
| `full` | all stages |
| `analytics` | analytics only (needs video_id) |

---

## Configuration & secrets

`.env.example` keys (non-exhaustive):

```
XAI_API_KEY=
XAI_MODEL=grok-4.5
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
YOUTUBE_CLIENT_SECRETS=  # path to OAuth client secrets JSON
YOUTUBE_CREDENTIALS_PATH=
# Optional research / social
TAVILY_API_KEY=          # or SERPER_API_KEY / BRAVE_API_KEY
X_BEARER_TOKEN=
# Feature flags
AUTO_APPROVE=false
DEFAULT_MODE=core
```

`config/settings.py` loads env + defaults; never hardcode keys.

---

## Implementation phases

### Phase 0 — Scaffold (first PR / session)
- Repo layout, `pyproject.toml`, package installs
- `.env.example`, logging, artifact helpers
- `AGENTS.md` (full role specs + voice)
- `README.md` (setup, architecture, examples)
- Pydantic schemas + empty agent stubs
- CLI + LangGraph skeleton with stage flags
- **No heavy external calls required to validate structure**

### Phase 1 — Core value loop (highest priority)
1. **Trend Scout** — real tools (web/news/arXiv/RSS), scoring, ranked JSON/MD output
2. **Deep Research** — structured brief with citations; source gathering tools
3. **Scriptwriter** — 12–16 min script with timestamps + visual cues
4. HITL topic gate + wire `core` mode end-to-end
5. Unit tests on schemas + scoring + artifact I/O; light integration test with mocked LLM

### Phase 2 — Quality gate
- Fact-Checker & Editor agent
- Script HITL gate
- Changelog + revised script artifacts

### Phase 3 — Media package
- Voice Director (ElevenLabs + dry-run)
- Visual Director (shot list, prompts, thumbnails concepts)
- Video Assembler (edit bible + asset manifest)

### Phase 4 — Publish loop
- SEO & Packaging
- Distribution (YouTube real; other platforms packages/stubs)
- Analytics & Learning store + feed into Trend Scout priors

### Phase 5 — Hardening
- Caching, retries, rate limits
- Better search tooling
- Vector/memory store for learnings (optional Chroma/SQLite-vec)
- Optional CapCut/Descript structured export
- CI tests + sample fixture run

---

## LangGraph graph sketch

```python
# Conceptual — not final code
builder = StateGraph(PipelineState)
builder.add_node("trend_scout", trend_scout_node)
builder.add_node("await_topic", await_topic_approval)
builder.add_node("deep_research", deep_research_node)
builder.add_node("scriptwriter", scriptwriter_node)
builder.add_node("fact_checker", fact_checker_node)
builder.add_node("await_script", await_script_approval)
# ... media + publish nodes
builder.add_conditional_edges("START", route_by_mode_and_flags)
# edges only connect enabled stages; skipped stages pass-through
```

Checkpointing: `MemorySaver` for dev; `SqliteSaver` for headless resume.

---

## Tooling strategy (research accuracy)

| Need | v1 approach |
|------|-------------|
| Web/news | Tavily/Serper/Brave if key present; else careful LLM + user-provided URLs + RSS |
| Papers | `arxiv` Python client |
| Company blogs | Curated RSS list in config + search |
| X/Twitter | Optional official API when token present |
| Grounding | Research agent must attach URLs; Fact-Checker cross-checks claims against brief |

**Accuracy policy:** If a claim cannot be sourced, mark as speculative or remove. Prefer under-claiming to hallucinated benchmarks.

---

## Testing strategy

- **Unit:** schema validation, topic scoring pure functions, stage routing, artifact paths
- **Agent contract tests:** mock LLM returns fixture JSON → node produces valid state
- **Golden fixtures:** sample research brief → script structure checks (hook present, CTA, timestamp monotonicity)
- **Manual e2e:** `core` mode with real `XAI_API_KEY` documented in README

---

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Hallucinated research | Citation-required schema; fact-checker; tool-first research |
| API cost (voice/LLM) | Dry-run flags; stage selection; caching |
| YouTube OAuth complexity | Documented setup; offline package mode if OAuth missing |
| CapCut project format fragility | Edit bible first, not reverse-engineered binaries |
| Overbuilding all 10 agents at once | Phased delivery; stubs with clear interfaces from day one |
| Framework lock-in | Thin agent interface (`run(state) -> state_delta`); graph is one orchestrator |

---

## Deliverables order (what you will review first)

1. **This plan** (architecture approval)
2. Scaffold: structure + `AGENTS.md` + `README` + schemas + CLI/graph skeleton
3. Working **core** pipeline: Scout → Research → Script (+ topic HITL)
4. Remaining agents in phase order

---

## Open decisions (defaults locked unless you change them)

| Decision | Default |
|----------|---------|
| Orchestrator | LangGraph |
| LLM | xAI Grok (`grok-4.5`) |
| Channel name | **Clarion Frame** (override in config / `CHANNEL_NAME`) |
| Assembler v1 | Edit bible + asset list (not binary CapCut) |
| Non-YouTube social | Ready-to-post packages; live post if creds exist |
| Memory v1 | JSON/SQLite files under `data/learnings/` |
| Package manager | `pyproject.toml` + pip/uv compatible |

---

## Success criteria for Phase 1

- [ ] Fresh clone → copy `.env.example` → install → `python run.py --help` works
- [ ] `AGENTS.md` fully defines all 10 roles + voice
- [ ] `README` explains architecture, setup, modular usage
- [ ] `python run.py --mode core --topic "..."` produces research brief + script under `data/runs/<id>/`
- [ ] Topic HITL works in interactive mode
- [ ] Disabled stages never run; no hard dependency on ElevenLabs/YouTube for core mode

---

## Next step after plan approval

Implement **Phase 0 scaffold** immediately, then **Phase 1 core agents** without waiting for media/distribution APIs.
