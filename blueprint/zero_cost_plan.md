# Zero-Cost Content Factory — Free Stack & Mobile Remote Plan

## Problem

Paid APIs (xAI Grok, ElevenLabs, Tavily, Kling/Runway, etc.) block you until you have budget.  
You need the factory to work **without spending money**, and later a **mobile app that remote-controls** agents on your PC (not run everything on the phone).

## Honest reality check

| Need | Paid default today | Free alternatives that work |
|------|--------------------|-----------------------------|
| LLM “brain” | xAI / OpenAI / Anthropic | **Ollama** local models (best $0 default); optional free tiers (Gemini, Groq, HF) with quotas |
| Web search | Tavily / Serper | **DuckDuckGo** (no key), RSS, Wikipedia, arXiv (already free) |
| Voiceover | ElevenLabs | **edge-tts** (free Microsoft voices), **Piper** (offline), Windows SAPI / pyttsx3 |
| Music / SFX | Epidemic Sound | Free libraries (Pixabay Audio, FreePD) + FFmpeg |
| B-roll video | Kling / Runway | Free stock APIs (Pexels/Pixabay), screen recordings, public domain, optional local SD/ComfyUI if GPU |
| Thumbnails | Midjourney / paid | **Pillow** + templates; free stock stills; optional local image models |
| YouTube upload | API is free | OAuth is free; only ads/monetization are separate |
| Hosting agents | Cloud | **Your PC** is free; phone only remote-controls |

**You cannot get frontier-model quality + studio VO + AI video gen for $0 forever.**  
You *can* get a complete, publishable pipeline at $0 with **local models + free public data + free TTS + stock/edit bible**.

---

## Recommended default: **Local-First Free Mode**

```
Phone (remote UI)
      │  free local Wi‑Fi / LAN
      ▼
PC Free Control API (FastAPI, localhost)
      │
      ▼
LangGraph Content Factory (already built)
      │
      ├── LLM  → Ollama (OpenAI-compatible)  [fallback: template/heuristic]
      ├── Search → DuckDuckGo + RSS + arXiv + Wikipedia
      ├── Voice → edge-tts or Piper
      ├── Visuals → shot lists + free stock search + Pillow thumbnails
      ├── Assemble → FFmpeg + edit bible (CapCut free desktop is $0)
      └── Publish → ready-to-post packages + optional free YouTube OAuth
```

### Why this is the best default
- Truly **$0 software cost** (open source / free tiers only)
- Uses the factory you already have; swap **providers**, not architecture
- Mobile app stays thin (control panel), so phones don’t need heavy GPUs
- When you later have funds, flip `LLM_PROVIDER=xai` / `TTS_PROVIDER=elevenlabs` without rewrite

---

## What already works for $0 (today, in repo)

The scaffold already degrades without keys:

- **No `XAI_API_KEY`** → heuristic topic ranking, research snippets, shorter template scripts  
- **No search key** → RSS + arXiv only  
- **No ElevenLabs** → dry-run narration text + markers  
- **Distribution** → writes ready-to-post files, no paid APIs  

**Gap:** heuristic scripts are short (~2 min). For real 12–16 min quality without Grok, you need a **local LLM provider** (Ollama).

---

## Free stack design (implementation target)

### 1. Multi-provider LLM layer (`tools/llm.py` upgrade)

```
LLM_PROVIDER=auto|ollama|xai|openai_compatible|none
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
OLLAMA_MODEL=qwen2.5:7b   # or llama3.2, mistral, phi4 — pick by RAM
```

Resolution order for `auto`:
1. xAI if key set (when you can pay later)
2. Else Ollama if reachable
3. Else `none` → existing heuristics

Same OpenAI-compatible client path — Ollama exposes `/v1/chat/completions`.

**Hardware guide (free models):**

| RAM | Suggested model | Expectation |
|-----|-----------------|-------------|
| 8 GB | `phi3:mini` / `llama3.2:3b` | Usable short scripts, thinner research |
| 16 GB | `qwen2.5:7b` / `mistral:7b` | Good core loop quality |
| 32 GB+ or GPU | `qwen2.5:14b` / `llama3.1:8b` | Closer to “real channel” scripts |

### 2. Free search (`tools/web_search.py`)

Add **DuckDuckGo** backend (no API key) as default when paid keys missing:

- `ddgs` / duckduckgo-search Python package  
- Keep Tavily/Serper as optional upgrades  
- Wikipedia summary API for grounding  
- Existing RSS + arXiv stay primary free sources  

### 3. Free voice (`tools/tts.py` + Voice Director)

Priority order:

| Provider | Cost | Notes |
|----------|------|-------|
| **edge-tts** | Free | Best $0 quality; needs network |
| **Piper** | Free offline | Fully local WAV; install once |
| pyttsx3 / SAPI | Free | Lowest quality; always works offline |
| ElevenLabs | Paid | Later |

CLI: `--tts edge|piper|none` (none = text-only markers)

### 4. Free visuals & assembly

- Visual Director: keep prompt packs + add **Pexels/Pixabay free API** optional (free keys)  
- Thumbnail concepts → generate simple **Pillow** PNGs (title + gradient)  
- Video Assembler: generate **FFmpeg concat script** from VO + stills/B-roll when assets exist  
- CapCut free desktop remains the human polish path (no license fee)

### 5. Free distribution & analytics

- Packages on disk (already)  
- YouTube Data API OAuth is free (Google Cloud free project) — only optional  
- Analytics: manual JSON import (already) + later free YT analytics OAuth  

### 6. “Zero-cost profile” config

```yaml
# config/profiles/free.yaml
llm_provider: ollama
search_provider: duckduckgo
tts_provider: edge-tts
media_mode: free
stock_provider: none   # or pexels if free key
auto_approve: false
```

CLI:

```bash
python run.py --profile free --mode core --topic "..." 
python run.py --profile free --mode media --auto-approve
```

---

## Mobile remote control (not on-device agents)

### Goal
Phone = **dashboard + remote control**.  
PC = **runs all agents** (Ollama, TTS, pipeline).

### Architecture

```
┌──────────────────┐         LAN / tailscale (free)        ┌─────────────────────┐
│ Flutter/React    │  REST + WebSocket                     │ PC Free Control API  │
│ Native app       │ ───────────────────────────────────►  │ FastAPI + auth token │
│ (Android first)  │ ◄───────────────────────────────────  │ spawns run.py stages │
└──────────────────┘   progress, logs, artifacts preview   └──────────┬──────────┘
                                                                      │
                                                                      ▼
                                                           content_factory graph
                                                           Ollama · edge-tts · data/
```

### Mobile app screens (v1)
1. **Home** — start Scout / Core / Media / Full  
2. **Topic picker** — approve candidates (HITL on phone)  
3. **Script review** — read final script, approve/reject  
4. **Run monitor** — live stage status + logs  
5. **Artifacts** — download/view research.md, script.md, audio  
6. **Settings** — PC host URL, free token, profile=free  

### Communication protocol (simple, free)
- `POST /runs` `{ mode, topic, profile: "free" }`  
- `GET /runs/{id}` status  
- `GET /runs/{id}/events` WebSocket/SSE log stream  
- `POST /runs/{id}/approve/topic` `{ index | title }`  
- `POST /runs/{id}/approve/script` `{ approve: true }`  
- `GET /runs/{id}/artifacts/...`  

Auth: shared secret token in `.env` (`CONTROL_API_TOKEN`) — no paid Auth0.

### Why not “spin Grok Build from the phone”?
- Grok Build is a **developer TUI session**, not a free always-on production API for your app  
- Phone → PC agents is reliable, offline-capable (on LAN), and $0  
- You can still use Grok Build *while developing* the free stack; production runs use **your local pipeline**

---

## Alternative free strategies (menu of options)

| Strategy | $0? | Quality | Effort | When to use |
|----------|-----|---------|--------|-------------|
| **A. Local-first (recommended)** | Yes | Medium–good | Medium | Default path |
| **B. Free cloud LLM quotas** | Yes until limit | Medium | Low | Laptop too weak for Ollama |
| **C. Template-only (no LLM)** | Yes | Low | Already mostly done | Offline demos, structure testing |
| **D. Human-in-loop hybrid** | Yes | High if you write | Low | You research; agents only format/SEO/TTS |
| **E. Community compute** | Sometimes | Varies | High | Not reliable for a channel |
| **F. Wait for paid keys** | No | Highest | Low | Later upgrade path |

**Hybrid D tip:** `--stages seo,voice` after you paste your own research into `research/brief.json` — zero LLM cost for packaging + free TTS.

---

## Implementation phases (this plan)

### Phase F0 — Document free path (quick)
- README section “Running with $0”
- `.env.example` free vars
- `config/profiles/free.yaml`
- Copy this plan to `blueprint/zero_cost_plan.md`

### Phase F1 — Free providers (desktop, highest value)
1. Ollama provider in `tools/llm.py` + health check  
2. DuckDuckGo search fallback  
3. edge-tts (+ optional Piper) in Voice Director  
4. `--profile free` CLI flag  
5. Tests with mocked Ollama / no-network heuristics  

### Phase F2 — Free media polish
1. Pillow thumbnail generator  
2. Optional free stock search  
3. FFmpeg assembly script generator from VO + images  

### Phase F3 — Free Control API (PC)
1. FastAPI server wrapping existing CLI/graph  
2. Token auth, run lifecycle, approval endpoints  
3. SSE log stream  

### Phase F4 — Mobile remote (Android first)
1. Minimal app (Flutter or React Native — pick one; Flutter recommended for free tooling)  
2. Connect to PC, start run, approve topic/script, view artifacts  
3. Document “same Wi‑Fi” setup; optional free Tailscale for away-from-home  

### Phase F5 — Quality without money
1. Better free prompts tuned for 7B models  
2. Chunked long-script generation (section-by-section) so small models can hit 12–16 min  
3. Caching so free tiers / local CPU aren’t re-spent  

---

## Key product decision: chunked free scriptwriting

7B local models often fail at one-shot 2000-word scripts.  
**Free-mode Scriptwriter should:**
1. Outline sections via LLM  
2. Write each section separately  
3. Stitch + fact-check pass  

This is the main technique to get **channel-length scripts for $0**.

---

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Weak scripts from small models | Chunked generation; human edit gate; better 7B/14B models |
| edge-tts needs net | Piper offline fallback |
| Ollama install friction | Documented one-time setup; `none` heuristic mode still works |
| Mobile security on LAN | Token + bind to LAN IP only; no public internet by default |
| “Grok Build as production backend” | Don’t; use local factory + optional paid APIs later |
| Time vs quality | Free stack is free in money, not in your time/CPU |

---

## Success criteria

- [ ] `python run.py --profile free --mode core --topic "..." --auto-approve` works **with no paid keys**
- [ ] Ollama produces multi-section script longer than heuristic templates  
- [ ] Free TTS writes a real `.mp3`/`.wav` under `data/runs/.../voice/`  
- [ ] DuckDuckGo/RSS/arXiv research brief without Tavily  
- [ ] Control API can start a run and return status  
- [ ] Mobile can approve topic/script and see artifact list on LAN  

---

## Defaults locked from your answers

| Decision | Choice |
|----------|--------|
| Free brain | **Local-first Ollama** + free tools; optional free cloud later |
| Mobile | **Remote control for PC pipeline** (not on-device agents) |
| Paid APIs | Optional upgrade path only; never required for free profile |

---

## Suggested first coding sprint after approval

1. Ollama LLM provider + free profile  
2. DuckDuckGo search  
3. edge-tts voice  
4. Chunked scriptwriter for small models  
5. README “$0 mode”  

Then Control API → mobile shell.

---

## Non-goals for free sprint

- Paying for xAI/ElevenLabs/Kling  
- On-phone multi-agent runtime  
- Pixel-perfect CapCut binary export  
- Guaranteeing AI Revolution–level quality on a 3B CPU model  

---

## Next step after you approve

Implement **Phase F0 + F1** in the existing repo (provider swaps + free profile), then F3 control API, then thin mobile remote.
