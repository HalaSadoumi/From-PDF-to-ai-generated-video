"""Sprint 3 (part 2): storyboard visuel generation, per chapter.

Cahier des charges section 5.6: for each part of the transformed course,
determine the narration, the visual type, the on-screen text, what should be
animated, and when the visual changes. The storyboard is the "blueprint"
used to generate the final video (section 7, "AGENT STORYBOARD").
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tqdm import tqdm

from s2m_pipeline.core import llm
from s2m_pipeline.models import Chapter, Scene, StoryboardScene

# ~2.3 words/second is a reasonable French narration speech rate, used to
# estimate scene duration from the narration text rather than trusting the
# LLM's own timing guess.
_WORDS_PER_SECOND = 2.3


def _overlapping_ocr(scenes: list[Scene], start: float, end: float) -> str:
    overlapping = [s for s in scenes if s.start < end and s.end > start]
    return "\n".join(dict.fromkeys(s.ocr_text for s in overlapping if s.ocr_text))


def _estimate_duration(narration: str) -> float:
    word_count = len(narration.split())
    return max(2.0, word_count / _WORDS_PER_SECOND)


def build_storyboard(chapter: Chapter, script: str, scenes: list[Scene]) -> list[StoryboardScene]:
    ocr_text = _overlapping_ocr(scenes, chapter.start, chapter.end)
    llm_scenes = llm.generate_storyboard_scenes(script, ocr_text)

    storyboard: list[StoryboardScene] = []
    for i, s in enumerate(llm_scenes):
        storyboard.append(
            StoryboardScene(
                scene_id=f"{chapter.id}_scene_{i:02d}",
                chapter_id=chapter.id,
                duration=round(_estimate_duration(s.narration), 1),
                narration=s.narration,
                visual_type=s.visual_type,
                visual_description=s.visual_description,
                on_screen_text=s.on_screen_text,
                transition=s.transition,
            )
        )
    return storyboard


def main() -> None:
    parser = argparse.ArgumentParser(description="S2M Sprint 3 storyboard generation")
    parser.add_argument("--chapters", required=True, type=Path, help="Path to chapters.json")
    parser.add_argument("--scripts", required=True, type=Path, help="Path to scripts.json")
    parser.add_argument("--scenes", required=True, type=Path, help="Path to scenes.json")
    parser.add_argument("--output", type=Path, default=Path("output/storyboard.json"))
    parser.add_argument(
        "--chapter-ids",
        nargs="*",
        default=None,
        help="Only generate storyboard scenes for these chapter ids. Default: all chapters "
        "that have a script.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip chapters whose storyboard scenes are already present in --output",
    )
    args = parser.parse_args()

    chapters = [
        Chapter.model_validate(c) for c in json.loads(args.chapters.read_text(encoding="utf-8"))
    ]
    scenes = [Scene.model_validate(s) for s in json.loads(args.scenes.read_text(encoding="utf-8"))]
    scripts: dict[str, str] = json.loads(args.scripts.read_text(encoding="utf-8"))

    if args.chapter_ids:
        chapters = [c for c in chapters if c.id in args.chapter_ids]

    all_scenes: list[StoryboardScene] = []
    done_chapter_ids: set[str] = set()
    if args.resume and args.output.exists():
        existing = [
            StoryboardScene.model_validate(s)
            for s in json.loads(args.output.read_text(encoding="utf-8"))
        ]
        all_scenes.extend(existing)
        done_chapter_ids = {s.chapter_id for s in existing}

    for chapter in tqdm(chapters, desc="Generating storyboards"):
        if chapter.id in done_chapter_ids:
            continue
        script = scripts.get(chapter.id)
        if not script:
            continue

        all_scenes.extend(build_storyboard(chapter, script, scenes))

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump([s.model_dump() for s in all_scenes], f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(all_scenes)} storyboard scenes written to {args.output}")


if __name__ == "__main__":
    main()
