"""Comprehension quiz per chapter.

Listed as a post-MVP feature in the cahier des charges (section 14) and built
once the core pipeline was working. Questions are grounded in each chapter's
own transcript, summary and key points, so they test what the training
actually said rather than general knowledge about the topic.

Checkpointed per chapter like the other LLM stages, so a quota error costs
only the chapters not yet written.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tqdm import tqdm

from s2m_pipeline.core import llm
from s2m_pipeline.models import Chapter, TranscriptSegment


def _overlapping_text(segments: list[TranscriptSegment], start: float, end: float) -> str:
    return " ".join(s.text for s in segments if s.start < end and s.end > start).strip()


def build_quiz(
    chapters: list[Chapter],
    transcript_segments: list[TranscriptSegment],
    output_path: Path,
    questions_per_chapter: int = 3,
    resume: bool = True,
) -> dict[str, list[dict]]:
    quizzes: dict[str, list[dict]] = {}
    if resume and output_path.exists():
        quizzes = json.loads(output_path.read_text(encoding="utf-8"))

    for chapter in tqdm(chapters, desc="Writing quizzes"):
        if chapter.id in quizzes:
            continue

        transcript = _overlapping_text(transcript_segments, chapter.start, chapter.end)
        questions = llm.generate_quiz(
            chapter.title, chapter.summary, chapter.key_points, transcript, questions_per_chapter
        )
        quizzes[chapter.id] = [q.model_dump() for q in questions]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(quizzes, f, ensure_ascii=False, indent=2)

    return quizzes


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a comprehension quiz per chapter")
    parser.add_argument("--chapters", required=True, type=Path)
    parser.add_argument("--transcript", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("output/quiz.json"))
    parser.add_argument("--questions", type=int, default=3)
    args = parser.parse_args()

    chapters = [
        Chapter.model_validate(c) for c in json.loads(args.chapters.read_text(encoding="utf-8"))
    ]
    segments = [
        TranscriptSegment.model_validate(s)
        for s in json.loads(args.transcript.read_text(encoding="utf-8"))
    ]

    quizzes = build_quiz(chapters, segments, args.output, args.questions)
    total = sum(len(q) for q in quizzes.values())
    print(f"\nDone. {total} questions across {len(quizzes)} chapters -> {args.output}")


if __name__ == "__main__":
    main()
