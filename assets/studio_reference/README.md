# Virtual Studio reference plates (Chloe)

Canonical **image-to-image** references for Clarion Frame’s Virtual News Studio.

Use these as the first input when generating subsequent stills (Grok Imagine
`image_edit`, Gemini image edit, etc.) so **Chloe’s face, wardrobe, and set**
stay consistent. Change only panel content, pose micro-variations, and story
assets — not the studio identity.

| File | Role |
|------|------|
| `chloe_studio_base.jpg` | **Primary base plate** — Chloe + glass panel (hook kinetic-stat energy). Prefer this for most new shots. |
| `chloe_studio_logo_panel.jpg` | **Secondary** — same shell with logo-forward glass panel. Use when the beat is brand/logo sting. |

## How to use

1. Load `chloe_studio_base.jpg` as the reference / edit source.
2. Prompt: keep Chloe, teal sofa, cyan globe, glass tablet, Clarion Frame badge.
3. Describe only what changes on the floating glass panel(s) (stat, logo, portrait, quote, UI).
4. CapCut composites real logos/portraits when AI text/logo accuracy is weak.

## Code paths

```python
from content_factory.agents.visual_director.peer_style import studio_reference_paths
paths = studio_reference_paths()  # {"base": Path(...), "logo_panel": Path(...)}
```

Do not invent a new anchor face from text alone when these files exist.
