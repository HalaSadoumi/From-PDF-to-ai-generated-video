"""Ce qu'est une production, et comment lire son avancement.

Aucun effet de bord ici : ce module décrit un travail et déduit son état des
fichiers que la chaîne écrit. C'est délibéré. La chaîne pose déjà un fichier
par étage terminé ; inventer un second canal de progression serait une source
de vérité de plus à tenir d'accord avec la première.
"""

from __future__ import annotations

import dataclasses
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
CANCELLED = "cancelled"
INTERRUPTED = "interrupted"

#: Un travail dans l'un de ces états ne bougera plus tout seul.
FINISHED_STATES = (DONE, FAILED, CANCELLED, INTERRUPTED)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- identifiant
_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(title: str, fallback: str = "cours") -> str:
    """Un identifiant de dossier à partir d'un titre saisi par un humain.

    Il devient un nom de dossier, un segment d'URL et une clé de catalogue :
    accents, apostrophes et deux-points doivent disparaître avant, pas après.
    """
    plain = unicodedata.normalize("NFKD", title)
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    slug = _SLUG_STRIP.sub("_", plain.lower()).strip("_")
    return slug[:60] or fallback


def unique_course_id(title: str, taken: set[str]) -> str:
    """Ne jamais écraser un cours existant à cause de deux titres proches."""
    base = slugify(title)
    if base not in taken:
        return base
    for suffix in range(2, 100):
        candidate = f"{base}_{suffix}"
        if candidate not in taken:
            return candidate
    return f"{base}_{int(datetime.now().timestamp())}"


# --------------------------------------------------------------------- étages
@dataclass(frozen=True)
class Stage:
    key: str
    label: str


#: Les neuf étages de `s2m-course-pdf`, dans l'ordre où ils s'exécutent.
STAGES: tuple[Stage, ...] = (
    Stage("pages", "Lecture du support"),
    Stage("chapters", "Rédaction de la narration"),
    Stage("storyboard", "Découpage en scènes"),
    Stage("narration", "Synthèse de la voix"),
    Stage("subtitles", "Sous-titres"),
    Stage("visuals", "Plan visuel"),
    Stage("images", "Arrière-plans"),
    Stage("render", "Rendu des vidéos"),
    Stage("publish", "Publication"),
)


def _count(directory: Path, pattern: str) -> int:
    return len(list(directory.glob(pattern))) if directory.is_dir() else 0


def _json_len(path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    return len(data)


def stage_report(output_dir: Path, videos_dir: Path, published_dir: Path) -> list[dict]:
    """L'avancement, déduit des artefacts présents.

    Un étage est terminé quand son résultat est là. Le premier qui ne l'est pas
    est celui en cours — la chaîne étant strictement séquentielle, il n'y a pas
    d'ambiguïté possible.
    """
    pages = output_dir / "pages.json"
    chapters = output_dir / "chapters.json"
    storyboard = output_dir / "storyboard.json"
    marks = output_dir / "narration_marks.json"
    visuals = output_dir / "scene_visuals.json"

    page_count = _json_len(pages)
    chapter_count = _json_len(chapters)
    scene_count = _json_len(storyboard)
    backdrops = _count(output_dir / "work" / "backdrops", "*.jpg")
    videos = _count(videos_dir, "*.mp4")
    cues = _count(output_dir / "subtitles", "*.vtt")

    facts: dict[str, tuple[bool, str]] = {
        "pages": (pages.exists(), f"{page_count} pages" if page_count else ""),
        "chapters": (chapters.exists(), f"{chapter_count} chapitres" if chapter_count else ""),
        "storyboard": (storyboard.exists(), f"{scene_count} scènes" if scene_count else ""),
        "narration": (marks.exists(), ""),
        "subtitles": (cues > 0, f"{cues} pistes" if cues else ""),
        "visuals": (visuals.exists(), ""),
        "images": (
            scene_count > 0 and backdrops >= scene_count,
            f"{backdrops} / {scene_count}" if scene_count else "",
        ),
        "render": (
            chapter_count > 0 and videos >= chapter_count,
            f"{videos} / {chapter_count}" if chapter_count else "",
        ),
        "publish": ((published_dir / "course_chapters.json").exists(), ""),
    }

    report: list[dict] = []
    running_marked = False
    for stage in STAGES:
        complete, detail = facts[stage.key]
        if complete:
            state = "done"
        elif not running_marked:
            state, running_marked = "current", True
        else:
            state = "pending"
        report.append({"key": stage.key, "label": stage.label, "state": state, "detail": detail})
    return report


def completed_stages(report: list[dict]) -> int:
    return sum(1 for stage in report if stage["state"] == "done")


# --------------------------------------------------------------------- travail
@dataclass
class Job:
    id: str
    course_id: str
    title: str
    description: str
    track: str
    pdf_name: str
    pdf_path: str
    quiz_path: str | None = None
    quiz_questions: int | None = None
    state: str = QUEUED
    created_at: str = field(default_factory=now)
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


def command_for(job: Job, output_dir: Path, python: str) -> list[str]:
    """La commande lancée est exactement celle de la documentation.

    Le studio n'appelle pas les fonctions de la chaîne dans son propre
    processus : un sous-processus isole l'échec, borne la mémoire, et garantit
    que ce qui est lancé depuis le navigateur est ce qui est lancé à la main.
    """
    command = [
        python, "-m", "s2m_pipeline.from_slides.build_course_from_pdf",
        "--pdf", job.pdf_path,
        "--course-id", job.course_id,
        "--title", job.title,
        "--description", job.description,
        "--track", job.track,
        "--output-dir", str(output_dir),
    ]
    if job.quiz_path:
        command += ["--quiz-docx", job.quiz_path]
    return command
