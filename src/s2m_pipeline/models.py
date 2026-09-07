"""Data schemas shared across the pipeline (cahier des charges, section 8).

Sprint 1 (ingestion) populates: id, start, end, speaker, transcript, ocr_text,
frame_path. `topic` and `importance` are left None here — they are filled in
during Sprint 2's LLM-based semantic comprehension pass, which reads this
scene list as input. `visual_description` is left None for the same reason
(free-form visual captioning is a comprehension task, not an ingestion task).
"""

from __future__ import annotations

from pydantic import BaseModel


class Scene(BaseModel):
    id: str
    start: float
    end: float
    speaker: str | None = None
    transcript: str = ""
    ocr_text: str = ""
    visual_description: str | None = None
    topic: str | None = None
    importance: float | None = None
    frame_path: str | None = None


class Chapter(BaseModel):
    id: str
    title: str
    start: float
    end: float
    summary: str = ""
    key_points: list[str] = []


class StoryboardScene(BaseModel):
    scene_id: str
    chapter_id: str
    duration: float
    narration: str
    visual_type: str
    visual_description: str
    on_screen_text: str = ""
    transition: str = "fade"
    # Populated by narration.py once the narration audio is synthesized;
    # `duration` is then corrected to match this file's real length.
    audio_path: str | None = None


class TranscriptSegment(BaseModel):
    """Raw ASR output segment, before merging with visual scene boundaries."""

    start: float
    end: float
    text: str
    speaker: str | None = None
