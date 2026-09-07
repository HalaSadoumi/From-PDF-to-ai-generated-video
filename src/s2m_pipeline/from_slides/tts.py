"""Narration synthesis via edge-tts — free, no API key required.

Cahier des charges section 6.2, option 2 ("Narration IA / TTS"): generate
narration from the rewritten pedagogical script for consistency and clarity,
rather than reusing the (noisy, hesitation-filled) original recording.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

from s2m_pipeline.core.audio import audio_duration_seconds  # re-exported for existing callers
from s2m_pipeline.config import settings

__all__ = ["synthesize", "synthesize_with_marks", "audio_duration_seconds"]


async def _synthesize_async(text: str, output_path: Path, voice: str) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def synthesize(text: str, output_path: Path, voice: str | None = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_synthesize_async(text, output_path, voice or settings.tts_voice))
    return output_path


async def _synthesize_with_marks_async(text: str, output_path: Path, voice: str) -> list[dict]:
    communicate = edge_tts.Communicate(text, voice)
    marks: list[dict] = []
    with open(output_path, "wb") as handle:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                handle.write(chunk["data"])
            elif chunk["type"] in ("SentenceBoundary", "WordBoundary"):
                # Offsets arrive in 100-nanosecond ticks.
                marks.append(
                    {
                        "start": chunk["offset"] / 10_000_000,
                        "end": (chunk["offset"] + chunk["duration"]) / 10_000_000,
                        "text": chunk["text"],
                    }
                )
    return marks


def synthesize_with_marks(text: str, output_path: Path, voice: str | None = None) -> list[dict]:
    """Synthesise speech and return when each sentence is actually spoken.

    The engine reports a boundary per sentence, which is exactly the unit a
    subtitle needs. Timing the cues from the speech itself, rather than
    spreading the text evenly across the scene, is what keeps them from
    drifting — and drift only shows up on playback, long after it is
    introduced.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return asyncio.run(_synthesize_with_marks_async(text, output_path, voice or settings.tts_voice))
