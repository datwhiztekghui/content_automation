# Content Factory

Modular, production-oriented **multi-agent YouTube content factory** for a channel covering tech, inventions, robotics, AI breakthroughs, science, and related news.

Orchestration: **LangGraph** · Agents: clear role packages · CLI: `python run.py`  
**$0 path:** Ollama + DuckDuckGo + edge-tts (`--profile free`) · Paid APIs optional later

Architecture blueprint: [`blueprint/plan.md`](blueprint/plan.md)  
Zero-cost plan: [`blueprint/zero_cost_plan.md`](blueprint/zero_cost_plan.md)  
Agent roles & voice: [`AGENTS.md`](AGENTS.md)

---

## Features

- **10 specialized agents** from trend discovery through analytics feedback  
- **Modular stages** — run research + scripting first; enable voice/visuals/distribution later  
- **Human-in-the-loop** topic and script approvals (interactive or headless files)  
- **Headless / scheduled** runs via CLI + OS scheduler  
- **Artifact-first** design — every stage writes JSON/Markdown under `data/runs/<id>/`  
- **Graceful degradation** without optional API keys (heuristics + dry-run media)

---

## Architecture

```
CLI / Scheduler
      │
      ▼
LangGraph pipeline (checkpoint-friendly linear stages)
      │
      ├── Trend Scout → [approve topic]
      ├── Deep Research → Scriptwriter → Fact-Checker → [approve script]
      ├── Voice → Visual → Assembler
      ├── SEO → Distribution
      └── Analytics → learnings store
```

| Layer | Free default | Paid upgrade (optional) |
|--------|--------------|-------------------------|
| Orchestration | LangGraph | — |
| LLM | **Ollama** local models | xAI Grok / OpenAI-compatible |
| Search | **DuckDuckGo** + RSS + arXiv + Wikipedia | Tavily / Serper / Brave |
| Voice | **edge-tts** (free) | ElevenLabs |
| Assembler | Edit bible + FFmpeg later | CapCut free desktop |
| Config | pydantic-settings + profiles | — |

---

## Project layout

```
content_automation/
├── AGENTS.md
├── README.md
├── blueprint/plan.md
├── blueprint/zero_cost_plan.md
├── .env.example
├── pyproject.toml
├── run.py
├── config/
│   ├── settings.py
│   ├── channel_style.yaml
│   └── profiles/free.yaml
├── src/content_factory/
│   ├── cli.py
│   ├── graph.py
│   ├── state.py
│   ├── agents/          # one package per role
│   ├── tools/
│   ├── gates/
│   ├── memory/
│   ├── models/
│   └── utils/
├── data/runs/           # per-run outputs (gitignored)
├── tests/
└── scripts/schedule_example.ps1
```

---

## Setup

### Requirements

- Python **3.11+**
- An [xAI](https://console.x.ai) API key for full LLM quality (optional for smoke tests)

### Install

```powershell
cd content_automation
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
```

Edit `.env` only if you want paid upgrades. **For $0 mode you do not need API keys.**

### Free stack one-time setup (recommended: Ollama Cloud free tier)

You already have **Cloud usage (Free)** with session + weekly bars. Use that first — no GPU required.

1. Create an API key: [ollama.com/settings/keys](https://ollama.com/settings/keys)
2. Put it in `.env`:

```env
OLLAMA_API_KEY=your_ollama_cloud_key
OLLAMA_CLOUD_MODEL=gpt-oss:20b
DEFAULT_PROFILE=free
```

3. Install deps and verify:

```powershell
pip install -e ".[dev]"
python run.py doctor
```

**Optional local fallback** (offline / when cloud quota is empty):

```powershell
# install Ollama desktop, then:
ollama pull qwen2.5:7b
```

Watch the free **session** and **weekly** usage bars so long runs don’t surprise you mid-script.

---

## Running with $0 (`--profile free`)

No xAI, ElevenLabs, or Tavily required.

```powershell
# Core research + script via Ollama Cloud free tier
python run.py --profile free --mode core --topic "Humanoid robots in warehouses" --auto-approve

# Free voice (edge-tts) + visuals + edit bible
python run.py --profile free --mode media --topic "Humanoid robots in warehouses" --auto-approve

# Health check
python run.py doctor
```

| Component | Free backend |
|-----------|----------------|
| Brain | **Ollama Cloud free tier** (`OLLAMA_API_KEY`) → local Ollama fallback |
| Search | DuckDuckGo + Wikipedia + RSS + arXiv |
| Voice | edge-tts (`EDGE_TTS_VOICE`) |
| Scripts | **Chunked** section-by-section (better quality; uses more free quota) |

**Quota tip:** chunked scriptwriting issues several LLM calls. Prefer one solid `--mode core` run per session window. Use a smaller `OLLAMA_CLOUD_MODEL` if you hit limits.

When you later have budget: set `XAI_API_KEY` / `ELEVENLABS_*`. Mobile remote control (phone → PC) is in `blueprint/zero_cost_plan.md`.

---

## Usage

### Help

```powershell
python run.py --help
python run.py list-stages
```

### Core loop (research → script → fact-check)

```powershell
# Forced topic, auto-approve gates (good first test)
python run.py --mode core --topic "Kimi K3 release" --auto-approve

# Interactive topic/script approval
python run.py --mode core --topic "Humanoid robots in warehouses"
```

### Discover topics only

```powershell
python run.py --mode scout --auto-approve
```

### Explicit stages

```powershell
python run.py --stages research,script,factcheck --topic "Solid-state battery breakthrough" --auto-approve
```

### Full pipeline (dry-run media, no paid VO/upload)

```powershell
python run.py --mode full --topic "Open-source robotics stack 2026" --auto-approve --dry-run-media
```

### Headless / scheduled

```powershell
python run.py --mode full --headless --auto-approve --dry-run-media
```

Without `--auto-approve`, headless mode writes:

- `data/runs/<id>/approvals/pending_topic.json`
- Expect `approvals/topic_decision.json` e.g. `{"approve_index": 0}`

Then resume:

```powershell
python run.py --resume <run_id> --mode core --auto-approve
```

Windows Task Scheduler example: `scripts/schedule_example.ps1`.

---

## Mode presets

| Mode | What runs |
|------|-----------|
| `scout` | Trend Scout |
| `core` | Topic gate → Research → Script → Fact-check → Script gate |
| `media` | core + voice + visual + assembler |
| `publish` | media + SEO + distribution |
| `full` | All agents |
| `analytics` | Analytics / learnings only |

---

## Artifacts

Each run creates `data/runs/<run_id>/`, for example:

```
topics/candidates.md
research/brief.md
script/draft.md
script/final.md
script/changelog.json
voice/
visuals/
assembly/EDIT_BIBLE.md
seo/
distribution/
analytics/
run_config.json
final_state.json
```

---

## Channel style

Edit:

- `config/channel_style.yaml` — structure, tone, scoring weights  
- `AGENTS.md` — full role contracts and voice rules  
- `CHANNEL_NAME` in `.env`

---

## Development

```powershell
pytest
```

Design notes and phased roadmap: **`blueprint/plan.md`**.

### Implementation status

| Phase | Status |
|-------|--------|
| 0 Scaffold + docs | Done |
| 1 Core: Scout → Research → Script | Done (LLM + heuristic fallback) |
| 2 Fact-checker + script HITL | Done |
| 3 Voice / visual / assembler | Scaffold + dry-run packages |
| 4 SEO / distribution / analytics | Scaffold + packages; YouTube live upload TBD |
| 5 Hardening / memory / exporters | Planned |

---

## Environment variables

See [`.env.example`](.env.example) for the full list. Core:

| Variable | Purpose |
|----------|---------|
| `XAI_API_KEY` | Grok LLM |
| `XAI_MODEL` | Default `grok-4.5` |
| `TAVILY_API_KEY` | Web search (or Serper/Brave) |
| `ELEVENLABS_*` | Voiceover |
| `YOUTUBE_*` | Upload / analytics (future) |
| `AUTO_APPROVE` | Default gate bypass (prefer CLI flag) |
| `DEFAULT_MODE` | Default `core` |

---

## Safety & accuracy

- Research and fact-check agents are instructed **not to invent citations or benchmarks**  
- Uncertainty flags and changelogs are first-class artifacts  
- Human approval is the default for publish-critical script decisions  

---

## License

MIT (or your preferred license — adjust `pyproject.toml`).
