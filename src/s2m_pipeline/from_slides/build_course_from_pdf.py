"""Build a course from a slide deck instead of a recording.

Le support de formation entre, le cours en sort. Les deux premiers etages
sont propres a cette source — lire le document et ecrire la narration ; tous
les suivants sont communs et vivent dans core/ :

    1. pages       read the deck, one Scene per page          (pdf_source)
    2. chapters    group pages, write title + narration       (llm)
    3. storyboard  split each narration into scenes           (storyboard)
    4. narration   synthesise the voice, measure durations    (narration/tts)
    5. visuals     archetype, points and takeaway per scene   (scene_visuals)
    6. images      ambience backdrop per scene                (scene_images)
    7. render      one video per chapter                      (Remotion)
    8. publish     subtitles, quiz, navigation, web           (as before)

Every stage writes its result to disk and is skipped when that result already
exists, so an interrupted run resumes where it stopped.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from s2m_pipeline.core import chapter_subtitles
from s2m_pipeline.core import render
from s2m_pipeline.core import llm
from s2m_pipeline.from_slides import narration
from s2m_pipeline.from_slides import pdf_source
from s2m_pipeline.core import quiz as quiz_mod
from s2m_pipeline.core import scene_images
from s2m_pipeline.core import scene_visuals as scene_visuals_mod
from s2m_pipeline.from_slides import storyboard as storyboard_mod
from s2m_pipeline.config import settings
from s2m_pipeline.models import Chapter, Scene, StoryboardScene

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REMOTION_DIR = PROJECT_ROOT / "remotion"

# Narration budget per chapter. At roughly 150 words a minute in French this
# lands each chapter between two and three minutes — well under the ceiling in
# `settings.chapter_max_seconds`, which is verified once the voice is measured.
WORDS_MIN = 280
WORDS_MAX = 460


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def pages(self) -> Path:
        return self.root / "pages.json"

    @property
    def page_images(self) -> Path:
        return self.root / "work" / "pages"

    @property
    def chapters(self) -> Path:
        return self.root / "chapters.json"

    @property
    def storyboard(self) -> Path:
        return self.root / "storyboard.json"

    @property
    def narration_dir(self) -> Path:
        return self.root / "work" / "narration"

    @property
    def visuals(self) -> Path:
        return self.root / "scene_visuals.json"

    @property
    def backdrops(self) -> Path:
        return self.root / "work" / "backdrops"

    @property
    def subtitles(self) -> Path:
        return self.root / "subtitles"

    @property
    def quiz(self) -> Path:
        return self.root / "quiz.json"

    @property
    def course(self) -> Path:
        return self.root / "course"


def _step(n: int, total: int, title: str) -> None:
    print(f"\n{'=' * 62}\n[{n}/{total}] {title}\n{'=' * 62}", flush=True)


def _done(message: str) -> None:
    print(f"  -> {message}", flush=True)


# --------------------------------------------------------------------- pages
def run_pages(paths: Paths, pdf: Path) -> list[Scene]:
    if paths.pages.exists():
        pages = [Scene.model_validate(s) for s in json.loads(paths.pages.read_text(encoding="utf-8"))]
        _done(f"already read — {len(pages)} pages")
        return pages

    pages = pdf_source.extract_pages(pdf, paths.page_images)
    paths.pages.parent.mkdir(parents=True, exist_ok=True)
    paths.pages.write_text(
        json.dumps([p.model_dump() for p in pages], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    words = sum(len(p.ocr_text.split()) for p in pages)
    _done(f"{len(pages)} pages, {words} words of source material")
    return pages


# ------------------------------------------------------------------ chapters
def run_chapters(paths: Paths, pages: list[Scene]) -> tuple[list[Chapter], dict[str, str]]:
    """Group pages into chapters and write each one's narration."""
    scripts_path = paths.root / "scripts.json"
    groups = pdf_source.group_into_chapters(pages)

    # Checkpoint per chapter: a quota failure halfway costs only what is left.
    # Completion is judged against the number of groups, not the mere presence
    # of the file — a run stopped at seven chapters out of eight left a file
    # that looked finished, and the missing chapter was never picked up.
    chapters: list[Chapter] = []
    scripts: dict[str, str] = {}
    if paths.chapters.exists():
        chapters = [Chapter.model_validate(c) for c in json.loads(paths.chapters.read_text(encoding="utf-8"))]
    if scripts_path.exists():
        scripts = json.loads(scripts_path.read_text(encoding="utf-8"))
    done = {c.id for c in chapters} & set(scripts)

    if len(done) == len(groups):
        _done(f"already written — {len(chapters)} chapters")
        return chapters, scripts
    if done:
        _done(f"resuming — {len(done)}/{len(groups)} chapters already written")

    for index, group in enumerate(groups):
        chapter_id = f"chapter_{index:02d}"
        if chapter_id in done:
            continue

        slides_text = "\n\n".join(p.ocr_text for p in group if p.ocr_text)
        images = [Path(p.frame_path) for p in group if p.frame_path][:6]
        content = llm.generate_slide_chapter(slides_text, images, WORDS_MIN, WORDS_MAX)

        chapters.append(
            Chapter(
                id=chapter_id,
                title=content.title,
                # Page timeline, so the later stages can tell which slides a
                # chapter covers. The course timeline is computed at assembly
                # from the rendered durations.
                start=group[0].start,
                end=group[-1].end,
                summary=content.summary,
                key_points=content.key_points,
            )
        )
        scripts[chapter_id] = content.narration
        print(f"  {chapter_id}: {content.title} ({len(content.narration.split())} words)", flush=True)

        chapters.sort(key=lambda c: c.id)
        paths.chapters.write_text(
            json.dumps([c.model_dump() for c in chapters], ensure_ascii=False, indent=2), encoding="utf-8"
        )
        scripts_path.write_text(json.dumps(scripts, ensure_ascii=False, indent=2), encoding="utf-8")

    _done(f"{len(chapters)} chapters, {sum(len(s.split()) for s in scripts.values())} words of narration")
    return chapters, scripts


# ---------------------------------------------------------------- storyboard
def run_storyboard(paths: Paths, chapters: list[Chapter], scripts: dict[str, str],
                   pages: list[Scene]) -> list[StoryboardScene]:
    if paths.storyboard.exists():
        scenes = [StoryboardScene.model_validate(s) for s in json.loads(paths.storyboard.read_text(encoding="utf-8"))]
        _done(f"already built — {len(scenes)} scenes")
        return scenes

    all_scenes: list[StoryboardScene] = []
    for chapter in chapters:
        built = storyboard_mod.build_storyboard(chapter, scripts[chapter.id], pages)
        all_scenes.extend(built)
        print(f"  {chapter.id}: {len(built)} scenes", flush=True)
        paths.storyboard.write_text(
            json.dumps([s.model_dump() for s in all_scenes], ensure_ascii=False, indent=2), encoding="utf-8"
        )

    _done(f"{len(all_scenes)} scenes")
    return all_scenes


# ----------------------------------------------------------------- narration
def run_narration(paths: Paths, scenes: list[StoryboardScene]) -> list[StoryboardScene]:
    """Synthesise the voice and replace estimated durations with measured ones."""

    from tqdm import tqdm

    from s2m_pipeline.core import audio as audio_mod
    from s2m_pipeline.from_slides import tts

    paths.narration_dir.mkdir(parents=True, exist_ok=True)
    marks_path = paths.root / "narration_marks.json"
    marks: dict[str, list[dict]] = {}

    if marks_path.exists():
        marks = json.loads(marks_path.read_text(encoding="utf-8"))

    spoken: list[StoryboardScene] = []
    for scene in tqdm(scenes, desc="  synthesising"):
        mp3 = paths.narration_dir / f"{scene.scene_id}.mp3"
        wav = paths.narration_dir / f"{scene.scene_id}.wav"
        # Skip what is already spoken: re-synthesising a scene would shift its
        # duration by a few hundredths and desynchronise a chapter already
        # rendered against the old value.
        if not (wav.exists() and scene.scene_id in marks):
            marks[scene.scene_id] = tts.synthesize_with_marks(scene.narration, mp3)
            audio_mod.to_wav(mp3, wav)
        spoken.append(
            scene.model_copy(
                update={
                    "duration": round(audio_mod.audio_duration_seconds(wav), 2),
                    "audio_path": str(wav),
                }
            )
        )

    paths.storyboard.write_text(
        json.dumps([s.model_dump() for s in spoken], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    marks_path.write_text(json.dumps(marks, ensure_ascii=False, indent=2), encoding="utf-8")

    total = sum(s.duration for s in spoken)
    _done(f"{len(spoken)} scenes, {total / 60:.1f} min of narration")
    return spoken


def check_chapter_lengths(scenes: list[StoryboardScene], chapters: list[Chapter]) -> list[str]:
    """Report chapters over the ceiling, now that the real durations are known."""
    by_chapter: dict[str, float] = {}
    for scene in scenes:
        by_chapter[scene.chapter_id] = by_chapter.get(scene.chapter_id, 0.0) + scene.duration

    over: list[str] = []
    for chapter in chapters:
        seconds = by_chapter.get(chapter.id, 0.0)
        flag = "" if seconds <= settings.chapter_max_seconds else "  DEPASSE LA LIMITE"
        print(f"  {chapter.id}: {seconds / 60:4.1f} min  {chapter.title}{flag}", flush=True)
        if seconds > settings.chapter_max_seconds:
            over.append(chapter.id)
    return over


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a complete e-learning course from a slide deck, end to end"
    )
    parser.add_argument("--pdf", required=True, type=Path, help="The support document")
    parser.add_argument("--course-id", required=True, help="Folder name under web/data/")
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--description",
        default="Cours structuré à partir du support de formation : chapitres courts, "
        "narration, transcription annotable et évaluation finale.",
    )
    parser.add_argument(
        "--quiz-docx", type=Path, default=None,
        help="Official quiz (Word). Without it, questions are generated from the narration.",
    )
    parser.add_argument(
        "--track", default="essentiel", choices=["detaille", "essentiel"],
        help="How the catalogue presents this reading of the material",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--stop-after", default=None,
        help="pages | chapters | storyboard | narration | subtitles | visuals | images | render",
    )
    args = parser.parse_args()

    paths = Paths(args.output_dir or PROJECT_ROOT / "output" / args.course_id)
    paths.root.mkdir(parents=True, exist_ok=True)
    total = 9

    # Verifie des maintenant ce dont le huitieme etage aura besoin : mieux vaut
    # refuser de partir que s'arreter apres quarante minutes de travail.
    if args.stop_after in (None, "render"):
        render.check_toolchain()

    _step(1, total, "Pages — read the deck")
    pages = run_pages(paths, args.pdf)
    if args.stop_after == "pages":
        return

    _step(2, total, "Chapters — group the slides, write the narration")
    chapters, scripts = run_chapters(paths, pages)
    if args.stop_after == "chapters":
        return

    _step(3, total, "Storyboard — split each narration into scenes")
    scenes = run_storyboard(paths, chapters, scripts, pages)
    if args.stop_after == "storyboard":
        return

    _step(4, total, "Narration — synthesise the voice")
    scenes = run_narration(paths, scenes)
    print("\n  Chapter lengths (measured):", flush=True)
    over = check_chapter_lengths(scenes, chapters)
    if over:
        print(f"  WARNING: {len(over)} chapter(s) over the ceiling: {', '.join(over)}", flush=True)
    if args.stop_after == "narration":
        return

    _step(5, total, "Subtitles — one cue per spoken sentence")
    run_subtitles(paths, scenes)
    if args.stop_after == "subtitles":
        return

    _step(6, total, "Visuals — archetype, points and takeaway per scene")
    run_visuals(paths, scenes, pages, chapters)
    if args.stop_after == "visuals":
        return

    _step(7, total, "Images — ambience backdrop per scene")
    render.run_images(paths)
    if args.stop_after == "images":
        return

    _step(8, total, "Render — one video per chapter")
    render.run_render(paths, out_name=f"out_pdf/{args.course_id}")
    if args.stop_after == "render":
        return

    _step(9, total, "Publish — quiz, thumbnail and web platform")
    run_quiz(paths, chapters, scripts, official=args.quiz_docx)
    run_publish(paths, args.course_id, args.title, args.description, args.pdf, chapters, args.track)

    print("\nDone.", flush=True)


# --------------------------------------------------------------- later stages
def run_visuals(paths: Paths, scenes: list[StoryboardScene], pages: list[Scene],
                chapters: list[Chapter]) -> None:
    bounds = {c.id: (c.start, c.end) for c in chapters}
    plans = scene_visuals_mod.build_scene_visuals(scenes, pages, bounds, paths.visuals, resume=True)
    archetypes = {p["archetype"] for p in plans.values()}
    empty = sum(1 for p in plans.values() if not p.get("items"))
    _done(f"{len(plans)} plans, {len(archetypes)} distinct archetypes, {empty} without points")


def run_subtitles(paths: Paths, scenes: list[StoryboardScene]) -> None:
    """Cue every sentence at the moment the voice actually says it."""
    marks_path = paths.root / "narration_marks.json"
    marks = json.loads(marks_path.read_text(encoding="utf-8"))

    by_chapter: dict[str, list[StoryboardScene]] = {}
    for scene in scenes:
        by_chapter.setdefault(scene.chapter_id, []).append(scene)

    total_cues = 0
    for chapter_id, chapter_scenes in by_chapter.items():
        cues: list[chapter_subtitles.Cue] = []
        cursor = 0.0
        for scene in chapter_scenes:
            for mark in marks.get(scene.scene_id, []):
                cues.append(
                    chapter_subtitles.Cue(
                        start=cursor + mark["start"],
                        end=min(cursor + mark["end"], cursor + scene.duration),
                        text=mark["text"].strip(),
                    )
                )
            cursor += scene.duration
        chapter_subtitles.write_vtt(cues, paths.subtitles / f"{chapter_id}.vtt")
        total_cues += len(cues)

    _done(f"{len(by_chapter)} tracks, {total_cues} cues")


def run_quiz(
    paths: Paths,
    chapters: list[Chapter],
    scripts: dict[str, str],
    official: Path | None = None,
) -> None:
    """Use the training's own quiz when there is one, generate one otherwise.

    A quiz written by the people who gave the training beats anything a model
    invents: it reflects what they actually want checked. Generation is the
    fallback for a deck that arrives without one."""
    if official and official.exists():
        from s2m_pipeline.core import quiz_reference

        questions = quiz_reference.parse_document(official)
        if questions:
            paths.quiz.parent.mkdir(parents=True, exist_ok=True)
            paths.quiz.write_text(
                json.dumps({"questions": questions}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            _done(f"{len(questions)} questions from the official quiz")
            return
        # A Word file the parser cannot read yields an empty list. Writing it
        # would publish a course whose final exam has no questions, and nobody
        # would find out until a learner reached the end.
        print(
            f"  WARNING: no question could be read from {official.name} — "
            "falling back to generated questions",
            flush=True,
        )

    _generate_quiz(paths, chapters, scripts)


def _generate_quiz(paths: Paths, chapters: list[Chapter], scripts: dict[str, str]) -> None:
    # The quiz is grounded in the narration rather than the slide text: it is
    # the narration the learner actually hears. One pseudo-segment per chapter,
    # laid on the page timeline the chapters use, so the existing overlap
    # lookup finds exactly that chapter's words.
    from s2m_pipeline.models import TranscriptSegment

    segments = [
        TranscriptSegment(start=c.start, end=c.end, text=scripts.get(c.id, ""))
        for c in chapters
    ]
    quizzes = quiz_mod.build_quiz(chapters, segments, paths.quiz, questions_per_chapter=3)
    _done(f"{sum(len(q) for q in quizzes.values())} questions across {len(quizzes)} chapters")


def render_dir(course_id: str) -> Path:
    """Where this course's videos land. One folder per course, never shared."""
    return REMOTION_DIR / "out_pdf" / course_id


def make_thumbnail(paths: Paths, chapters: list[Chapter], course_id: str) -> Path | None:
    """A still from the first chapter, so the catalogue card is not a grey box."""
    if not chapters:
        return None
    source = render_dir(course_id) / f"{chapters[0].id}.mp4"
    if not source.exists():
        return None
    target = paths.root / "work" / "thumbnail.jpg"
    target.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", "20", "-i", str(source),
         "-frames:v", "1", "-vf", "scale=960:-1", str(target)],
        capture_output=True,
    )
    return target if result.returncode == 0 and target.exists() else None


def run_publish(
    paths: Paths, course_id: str, title: str, description: str, pdf: Path,
    chapters: list[Chapter], track: str,
) -> None:
    from s2m_pipeline.core import web_export

    web_export.export(
        course_id=course_id,
        title=title,
        description=description,
        chapters_path=paths.chapters,
        video_dir=render_dir(course_id),
        quiz_path=paths.quiz if paths.quiz.exists() else None,
        pdf_path=pdf,
        thumbnail_path=make_thumbnail(paths, chapters, course_id),
        subtitle_dir=paths.subtitles if paths.subtitles.exists() else None,
        copy_videos=True,
        track=track,
    )
    _done(f"published as '{course_id}'")


if __name__ == "__main__":
    main()
