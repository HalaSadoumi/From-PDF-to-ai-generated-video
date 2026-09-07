"""Read a slide deck as course material.

The video pipeline starts from a recording; this front end starts from the
slide deck itself, for the case where the source material is a support
document rather than a session. Everything downstream is unchanged: the pages
are turned into the same `Scene` objects the video ingestion produces, so
chaptering, visual planning, rendering, quiz and publishing all run as they
already do.

A page becomes a Scene with the slide text as `ocr_text` and a render of the
page as `frame_path` — exactly what those stages expect from a video frame.
Pages are laid on a synthetic timeline (a fixed number of seconds each) so the
existing `start`/`end` overlap logic keeps working without a special case; the
real durations are measured after the narration is synthesised.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pymupdf

from s2m_pipeline.config import settings
from s2m_pipeline.models import Scene

# Each page occupies this much of the synthetic timeline. The value is
# arbitrary — only the ordering and the overlaps matter downstream.
PAGE_SECONDS = 10.0

# A slide carrying nothing but a section name in capitals is a divider, not
# content: it marks where one part of the deck ends and the next begins.
# Detecting it needs no knowledge of the subject, so the rule holds for any
# deck built the usual way.
_DIVIDER_MAX_CHARS = 70
_DIVIDER_MIN_UPPERCASE = 0.8

# Rendering resolution for the page images handed to the multimodal model.
_PAGE_DPI = 110


def _uppercase_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)


def is_section_divider(text: str) -> bool:
    """Whether a page only announces a section rather than teaching anything."""
    clean = " ".join(text.split())
    return bool(clean) and len(clean) <= _DIVIDER_MAX_CHARS and _uppercase_ratio(clean) >= _DIVIDER_MIN_UPPERCASE


def extract_pages(pdf_path: Path, image_dir: Path) -> list[Scene]:
    """One Scene per page, with its text and a render of the page."""
    image_dir.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open(pdf_path)

    scenes: list[Scene] = []
    for index, page in enumerate(document):
        image_path = image_dir / f"page_{index:03d}.png"
        if not image_path.exists():
            page.get_pixmap(dpi=_PAGE_DPI).save(image_path)

        scenes.append(
            Scene(
                id=f"page_{index:03d}",
                start=index * PAGE_SECONDS,
                end=(index + 1) * PAGE_SECONDS,
                ocr_text=" ".join(page.get_text().split()),
                frame_path=str(image_path),
            )
        )

    document.close()
    return scenes


def section_starts(scenes: list[Scene]) -> list[int]:
    """Indices where a new section of the deck begins.

    The document's own outline is used when it has one, since that is the
    author's intent. Most exported decks have none, so the fallback reads the
    divider slides described above.
    """
    starts = {0}
    for index, scene in enumerate(scenes):
        if is_section_divider(scene.ocr_text):
            starts.add(index)
    return sorted(starts)


def _words(scene: Scene) -> int:
    return len(scene.ocr_text.split())


def group_into_chapters(scenes: list[Scene]) -> list[list[Scene]]:
    """Group pages into chapters of roughly one narration's worth of material.

    Like the video chaptering, the target is expressed as a goal rather than a
    fixed number of chapters: a deck twice as long yields twice as many. Two
    rules bound the result — a chapter never spans two sections of the deck,
    and a group too thin to be worth a chapter is folded into its neighbour
    within the same section.
    """
    if not scenes:
        return []

    boundaries = section_starts(scenes)
    sections: list[list[Scene]] = []
    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else len(scenes)
        section = scenes[start:end]
        if section:
            sections.append(section)

    chapters: list[list[Scene]] = []
    for section in sections:
        total = sum(_words(s) for s in section)
        # How many chapters this section deserves, then split it evenly into
        # that many. Filling each chapter to the target and letting the
        # remainder form the last one leaves a stub: a 323-word section came
        # out as 251 + 72 rather than two balanced halves.
        count = max(1, round(total / settings.pdf_chapter_target_words))
        count = min(count, len(section))
        per_chapter = total / count if count else total

        current: list[Scene] = []
        made = 0
        for index, scene in enumerate(section):
            current.append(scene)
            pages_left = len(section) - index - 1
            chapters_left = count - made - 1
            accumulated = sum(_words(s) for s in current)
            next_words = _words(section[index + 1]) if pages_left else 0
            # Stop where the chapter lands closest to its share. Closing as
            # soon as the share is reached overshoots whenever a page is large:
            # a 602-word section came out as 202 / 300 / 100 instead of thirds.
            close = (
                chapters_left > 0
                # never take so many pages that the remaining chapters of this
                # section would have none left
                and pages_left >= chapters_left
                and abs(accumulated - per_chapter) <= abs(accumulated + next_words - per_chapter)
            )
            if close:
                chapters.append(current)
                current = []
                made += 1
        if current:
            chapters.append(current)

    return chapters


def main() -> None:
    parser = argparse.ArgumentParser(description="Read a slide deck as course material")
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="Where to write pages.json")
    parser.add_argument("--image-dir", type=Path, default=None)
    args = parser.parse_args()

    image_dir = args.image_dir or args.output.parent / "pages"
    scenes = extract_pages(args.pdf, image_dir)
    groups = group_into_chapters(scenes)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps([s.model_dump() for s in scenes], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total_words = sum(len(s.ocr_text.split()) for s in scenes)
    print(f"{len(scenes)} pages, {total_words} words -> {len(groups)} chapters")
    for i, group in enumerate(groups):
        words = sum(len(s.ocr_text.split()) for s in group)
        print(f"  chapter {i:02d}: pages {group[0].id}-{group[-1].id}, {words} words")


if __name__ == "__main__":
    main()
