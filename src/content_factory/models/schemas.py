"""Shared Pydantic contracts between agents and disk artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StageName(str, Enum):
    TREND_SCOUT = "trend_scout"
    AWAIT_TOPIC = "await_topic"
    DEEP_RESEARCH = "deep_research"
    SCRIPTWRITER = "scriptwriter"
    FACT_CHECKER = "fact_checker"
    AWAIT_SCRIPT = "await_script"
    VOICE_DIRECTOR = "voice_director"
    VISUAL_DIRECTOR = "visual_director"
    VIDEO_ASSEMBLER = "video_assembler"
    SEO_PACKAGING = "seo_packaging"
    DISTRIBUTION = "distribution"
    ANALYTICS = "analytics"


class PipelineMode(str, Enum):
    SCOUT = "scout"
    CORE = "core"
    MEDIA = "media"
    PUBLISH = "publish"
    FULL = "full"
    ANALYTICS = "analytics"
    CUSTOM = "custom"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"


class Citation(BaseModel):
    title: str
    url: str = ""
    publisher: str = ""
    published_at: str = ""
    note: str = ""


class TopicScores(BaseModel):
    virality: float = Field(default=5.0, ge=0, le=10, description="Viral potential 0-10")
    uniqueness: float = Field(default=5.0, ge=0, le=10)
    competition: float = Field(
        default=5.0,
        ge=0,
        le=10,
        description="Higher = more competition (worse)",
    )
    channel_fit: float = Field(default=5.0, ge=0, le=10)
    composite: float = Field(default=0.0, ge=0, le=10)

    def recompute(
        self,
        weights: dict[str, float] | None = None,
    ) -> TopicScores:
        w = weights or {
            "virality": 0.30,
            "uniqueness": 0.25,
            "competition": 0.20,
            "channel_fit": 0.25,
        }
        # Invert competition so lower competition raises score
        competition_score = 10.0 - self.competition
        composite = (
            self.virality * w.get("virality", 0.3)
            + self.uniqueness * w.get("uniqueness", 0.25)
            + competition_score * w.get("competition", 0.2)
            + self.channel_fit * w.get("channel_fit", 0.25)
        )
        return self.model_copy(update={"composite": round(composite, 2)})


class TopicCandidate(BaseModel):
    title: str
    summary: str
    why_it_matters: str
    suggested_angle: str = ""
    sources: list[Citation] = Field(default_factory=list)
    scores: TopicScores = Field(default_factory=TopicScores)
    keywords: list[str] = Field(default_factory=list)
    discovered_at: datetime = Field(default_factory=utc_now)

    def with_composite(self, weights: dict[str, float] | None = None) -> TopicCandidate:
        return self.model_copy(update={"scores": self.scores.recompute(weights)})


class ResearchBrief(BaseModel):
    topic_title: str
    overview: str
    technical_details: str
    benchmarks: str = ""
    expert_reactions: str = ""
    historical_context: str = ""
    implications: str = ""
    open_questions: list[str] = Field(default_factory=list)
    key_claims: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    uncertainty_flags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class ScriptSection(BaseModel):
    id: str
    title: str
    start_timestamp: str = "00:00"
    end_timestamp: str = "00:00"
    narration: str
    visual_cues: list[str] = Field(default_factory=list)
    on_screen_text: list[str] = Field(default_factory=list)
    source_callouts: list[str] = Field(default_factory=list)


class VideoScript(BaseModel):
    title_working: str
    topic_title: str
    estimated_runtime_minutes: float = 14.0
    word_count: int = 0
    sections: list[ScriptSection] = Field(default_factory=list)
    full_narration: str = ""
    soft_cta: str = ""
    created_at: datetime = Field(default_factory=utc_now)

    def recompute_stats(self, wpm: int = 150) -> VideoScript:
        text = self.full_narration or " ".join(s.narration for s in self.sections)
        words = len(text.split())
        runtime = round(words / wpm, 1) if words else 0.0
        return self.model_copy(
            update={
                "full_narration": text.strip(),
                "word_count": words,
                "estimated_runtime_minutes": runtime,
            }
        )


class ChangeLogEntry(BaseModel):
    category: str  # accuracy | flow | retention | voice | policy
    severity: str = "info"  # info | warning | critical
    original: str = ""
    revised: str = ""
    rationale: str


class VoicePackage(BaseModel):
    voice_id: str = ""
    voice_settings: dict[str, Any] = Field(default_factory=dict)
    audio_paths: list[str] = Field(default_factory=list)
    timing_markers: list[dict[str, Any]] = Field(default_factory=list)
    dry_run: bool = True
    narration_text_path: str = ""


class ThumbnailConcept(BaseModel):
    concept_id: str
    headline: str
    subtext: str = ""
    visual_description: str
    text_overlay: str
    emotion: str = ""


class VisualPackage(BaseModel):
    shot_list: list[dict[str, Any]] = Field(default_factory=list)
    broll_prompts: list[dict[str, Any]] = Field(default_factory=list)
    lower_thirds: list[dict[str, Any]] = Field(default_factory=list)
    thumbnail_concepts: list[ThumbnailConcept] = Field(default_factory=list)


class AssemblyPackage(BaseModel):
    edit_bible_markdown: str = ""
    asset_manifest: list[dict[str, Any]] = Field(default_factory=list)
    timeline_notes: list[str] = Field(default_factory=list)
    target_editors: list[str] = Field(
        default_factory=lambda: ["CapCut", "Descript", "Premiere"]
    )


class SEOPackage(BaseModel):
    titles: list[str] = Field(default_factory=list)
    description: str = ""
    chapters: list[dict[str, str]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    end_screen: dict[str, Any] = Field(default_factory=dict)
    shorts_hooks: list[dict[str, str]] = Field(default_factory=list)


class AnalyticsSnapshot(BaseModel):
    video_id: str = ""
    views: int = 0
    watch_time_hours: float = 0.0
    avg_view_duration_seconds: float = 0.0
    ctr: float = 0.0
    likes: int = 0
    comments: int = 0
    insights: list[str] = Field(default_factory=list)
    captured_at: datetime = Field(default_factory=utc_now)


class PublishResult(BaseModel):
    platform: str
    status: str
    url: str = ""
    external_id: str = ""
    notes: str = ""


# Mode → default stage sequence
MODE_STAGES: dict[PipelineMode, list[StageName]] = {
    PipelineMode.SCOUT: [StageName.TREND_SCOUT],
    PipelineMode.CORE: [
        StageName.TREND_SCOUT,
        StageName.AWAIT_TOPIC,
        StageName.DEEP_RESEARCH,
        StageName.SCRIPTWRITER,
        StageName.FACT_CHECKER,
        StageName.AWAIT_SCRIPT,
    ],
    PipelineMode.MEDIA: [
        StageName.TREND_SCOUT,
        StageName.AWAIT_TOPIC,
        StageName.DEEP_RESEARCH,
        StageName.SCRIPTWRITER,
        StageName.FACT_CHECKER,
        StageName.AWAIT_SCRIPT,
        StageName.VOICE_DIRECTOR,
        StageName.VISUAL_DIRECTOR,
        StageName.VIDEO_ASSEMBLER,
    ],
    PipelineMode.PUBLISH: [
        StageName.TREND_SCOUT,
        StageName.AWAIT_TOPIC,
        StageName.DEEP_RESEARCH,
        StageName.SCRIPTWRITER,
        StageName.FACT_CHECKER,
        StageName.AWAIT_SCRIPT,
        StageName.VOICE_DIRECTOR,
        StageName.VISUAL_DIRECTOR,
        StageName.VIDEO_ASSEMBLER,
        StageName.SEO_PACKAGING,
        StageName.DISTRIBUTION,
    ],
    PipelineMode.FULL: list(StageName),
    PipelineMode.ANALYTICS: [StageName.ANALYTICS],
    PipelineMode.CUSTOM: [],
}


STAGE_ALIASES: dict[str, StageName] = {
    "scout": StageName.TREND_SCOUT,
    "trend_scout": StageName.TREND_SCOUT,
    "topic": StageName.AWAIT_TOPIC,
    "await_topic": StageName.AWAIT_TOPIC,
    "research": StageName.DEEP_RESEARCH,
    "deep_research": StageName.DEEP_RESEARCH,
    "script": StageName.SCRIPTWRITER,
    "scriptwriter": StageName.SCRIPTWRITER,
    "factcheck": StageName.FACT_CHECKER,
    "fact_checker": StageName.FACT_CHECKER,
    "await_script": StageName.AWAIT_SCRIPT,
    "voice": StageName.VOICE_DIRECTOR,
    "voice_director": StageName.VOICE_DIRECTOR,
    "visual": StageName.VISUAL_DIRECTOR,
    "visual_director": StageName.VISUAL_DIRECTOR,
    "assemble": StageName.VIDEO_ASSEMBLER,
    "video_assembler": StageName.VIDEO_ASSEMBLER,
    "seo": StageName.SEO_PACKAGING,
    "seo_packaging": StageName.SEO_PACKAGING,
    "distribute": StageName.DISTRIBUTION,
    "distribution": StageName.DISTRIBUTION,
    "analytics": StageName.ANALYTICS,
}


def resolve_stages(
    mode: PipelineMode,
    stage_csv: str | None = None,
    skip_scout: bool = False,
) -> list[StageName]:
    if stage_csv:
        stages: list[StageName] = []
        for part in stage_csv.split(","):
            key = part.strip().lower()
            if not key:
                continue
            if key not in STAGE_ALIASES:
                raise ValueError(f"Unknown stage: {part!r}")
            stages.append(STAGE_ALIASES[key])
        return stages
    stages = list(MODE_STAGES.get(mode, []))
    if skip_scout and StageName.TREND_SCOUT in stages:
        stages = [s for s in stages if s != StageName.TREND_SCOUT]
        # Forced topic: still allow await_topic optionally, but can skip
    return stages
