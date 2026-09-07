"""Sous-titres : une piste par chapitre, calee sur la parole reelle.

Chaque phrase est placee au moment ou la voix la prononce, a partir des
reperes que le moteur de synthese renvoie — rien n'est estime.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Cue:
    start: float
    end: float
    text: str


def _format(seconds: float) -> str:
    millis = max(0, round(seconds * 1000))
    h, millis = divmod(millis, 3_600_000)
    m, millis = divmod(millis, 60_000)
    s, ms = divmod(millis, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def write_vtt(cues: list[Cue], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["WEBVTT", ""]
    for i, cue in enumerate(cues, start=1):
        lines += [str(i), f"{_format(cue.start)} --> {_format(cue.end)}", cue.text, ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
