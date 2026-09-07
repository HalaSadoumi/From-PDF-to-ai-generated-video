"""Stage a course for the web player, and register it in the catalog.

Each course gets its own folder under web/data/<course_id>/ holding its
chapter metadata, quiz, videos and optional reading support (PDF). A shared
web/data/courses.json lists every exported course, which is what the catalog
page reads — so adding a second course is just another run of this command.

Only chapters that have actually been rendered are exported, and files a
render is still writing are skipped, so the player can be used while a long
batch is running.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from s2m_pipeline.core.audio import audio_duration_seconds
from s2m_pipeline.models import Chapter

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WEB_DIR = PROJECT_ROOT / "web"
DATA_DIR = WEB_DIR / "data"
CATALOG_PATH = DATA_DIR / "courses.json"


def _export_chapters(
    chapters: list[Chapter],
    video_dir: Path,
    course_dir: Path,
    copy_videos: bool,
    subtitle_dir: Path | None,
) -> tuple[list[dict], list[str]]:
    videos_dir = course_dir / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    exported: list[dict] = []
    missing: list[str] = []
    cursor = 0.0

    for chapter in chapters:
        source = video_dir / f"{chapter.id}.mp4"
        if not source.exists() or source.stat().st_size == 0:
            missing.append(chapter.id)
            continue

        try:
            duration = audio_duration_seconds(source)
        except RuntimeError:
            # A render still writing this file leaves it unreadable (no moov
            # atom yet); treat it as not ready rather than aborting.
            missing.append(chapter.id)
            continue

        exported.append(
            {
                "id": chapter.id,
                "title": chapter.title,
                "start": round(cursor, 3),
                "end": round(cursor + duration, 3),
                "duration": round(duration, 3),
                "timestamp": _format_timestamp(cursor),
                "summary": chapter.summary,
                "key_points": chapter.key_points,
            }
        )
        cursor += duration

        if copy_videos:
            target = videos_dir / source.name
            if not target.exists() or target.stat().st_size != source.stat().st_size:
                shutil.copy(source, target)

        # Subtitles ride alongside the video so the player can offer them as a
        # switchable track; a chapter without one simply has no track.
        if subtitle_dir:
            vtt = subtitle_dir / f"{chapter.id}.vtt"
            if vtt.exists():
                shutil.copy(vtt, videos_dir / vtt.name)
                exported[-1]["subtitles"] = f"{chapter.id}.vtt"

    return exported, missing


def _update_catalog(entry: dict) -> list[dict]:
    catalog: list[dict] = []
    if CATALOG_PATH.exists():
        try:
            catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8")).get("courses", [])
        except json.JSONDecodeError:
            catalog = []

    catalog = [c for c in catalog if c.get("id") != entry["id"]]
    catalog.append(entry)
    catalog.sort(key=lambda c: c.get("title", ""))

    CATALOG_PATH.write_text(
        json.dumps({"courses": catalog}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return catalog


def _format_timestamp(seconds: float) -> str:
    """hh:mm:ss, pour les reperes de navigation affiches dans la plateforme."""
    total = round(seconds)
    h, total = divmod(total, 3600)
    m, s = divmod(total, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def export(
    course_id: str,
    title: str,
    description: str,
    chapters_path: Path,
    video_dir: Path,
    quiz_path: Path | None,
    pdf_path: Path | None,
    thumbnail_path: Path | None,
    subtitle_dir: Path | None,
    copy_videos: bool,
    # Which reading of the same material this course is. Two courses can be
    # built from one training: a full one that keeps everything the speaker
    # said, and a short one written from the support document. The catalogue
    # shows the difference so a learner picks knowingly.
    track: str = "detaille",
) -> None:
    chapters = [
        Chapter.model_validate(c) for c in json.loads(chapters_path.read_text(encoding="utf-8"))
    ]
    course_dir = DATA_DIR / course_id
    course_dir.mkdir(parents=True, exist_ok=True)

    exported, missing = _export_chapters(
        chapters, video_dir, course_dir, copy_videos, subtitle_dir
    )
    (course_dir / "course_chapters.json").write_text(
        json.dumps(exported, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    questions = 0
    filtered: dict = {}
    if quiz_path and quiz_path.exists():
        quiz = json.loads(quiz_path.read_text(encoding="utf-8"))
        if isinstance(quiz.get("questions"), list):
            # An official quiz written for the training as a whole: it is not
            # attached to chapters, so there is nothing to filter.
            filtered = {"questions": quiz["questions"]}
            questions = len(quiz["questions"])
        else:
            exported_ids = {c["id"] for c in exported}
            # Never advertise a quiz for a chapter the player cannot play.
            filtered = {k: v for k, v in quiz.items() if k in exported_ids}
            questions = sum(len(v) for v in filtered.values())
    (course_dir / "quiz.json").write_text(
        json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    pdf_name = None
    if pdf_path and pdf_path.exists():
        pdf_name = "support.pdf"
        shutil.copy(pdf_path, course_dir / pdf_name)

    thumb_name = None
    if thumbnail_path and thumbnail_path.exists():
        thumb_name = "thumbnail" + thumbnail_path.suffix
        shutil.copy(thumbnail_path, course_dir / thumb_name)

    total_minutes = round(sum(c["duration"] for c in exported) / 60)
    catalog = _update_catalog(
        {
            "id": course_id,
            "title": title,
            "description": description,
            "chapters": len(exported),
            "duration_minutes": total_minutes,
            "questions": questions,
            "pdf": pdf_name,
            "thumbnail": thumb_name,
            "track": track,
        }
    )

    print(f"Exported '{title}' -> {course_dir}")
    print(f"  {len(exported)}/{len(chapters)} chapters ({total_minutes} min), {questions} questions")
    if pdf_name:
        print("  reading support included")
    if missing:
        print(f"  {len(missing)} not yet rendered: {', '.join(missing)}")
    print(f"  catalog now lists {len(catalog)} course(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage a course for the web player")
    parser.add_argument("--course-id", required=True, help="Folder name under web/data/")
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--chapters", required=True, type=Path)
    parser.add_argument("--video-dir", required=True, type=Path)
    parser.add_argument("--quiz", type=Path, default=None)
    parser.add_argument("--pdf", type=Path, default=None, help="Reading support to offer")
    parser.add_argument("--thumbnail", type=Path, default=None)
    parser.add_argument(
        "--subtitles", type=Path, default=None, help="Directory of <chapter_id>.vtt tracks"
    )
    parser.add_argument(
        "--no-videos", action="store_true", help="Only refresh metadata, skip copying videos"
    )
    parser.add_argument(
        "--track", default="detaille", choices=["detaille", "essentiel"],
        help="Which reading of the material this course is, shown in the catalogue",
    )
    args = parser.parse_args()

    export(
        args.course_id,
        args.title,
        args.description,
        args.chapters,
        args.video_dir,
        args.quiz,
        args.pdf,
        args.thumbnail,
        args.subtitles,
        copy_videos=not args.no_videos,
        track=args.track,
    )


if __name__ == "__main__":
    main()
