"""Read an official quiz supplied as a Word document.

Some trainings come with a quiz written by the people who gave them. That
quiz beats anything generated: it reflects what the trainer actually wants
checked. This reads such a document and produces the same JSON the player
already consumes, so an official quiz and a generated one are interchangeable
downstream.

The expected shape is one paragraph per question:

    Question: <énoncé> (…) A) … B) … C) … Bonnes Réponses: A et B

Questions are course-level, not per chapter — the file is emitted under a
"questions" key rather than keyed by chapter id, and the player accepts both.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import docx

# "A)" … "E)" starting an option, kept in the split so the letter survives.
_OPTION = re.compile(r"(?=\b([A-H])\)\s)")
_ANSWERS = re.compile(r"Bonnes?\s+R[ée]ponses?\s*:\s*(.+)$", re.I)
_LETTER = re.compile(r"\b([A-H])\b")


def parse_question(text: str) -> dict | None:
    """Turn one paragraph into a question, or None if it is not one."""
    clean = " ".join(text.split())
    if not clean.lower().startswith("question"):
        return None

    answer_match = _ANSWERS.search(clean)
    if not answer_match:
        return None
    correct = _LETTER.findall(answer_match.group(1))
    body = clean[: answer_match.start()].strip()

    # Everything before the first "A)" is the wording; the rest are options.
    parts = _OPTION.split(body)
    if len(parts) < 3:
        return None

    wording = parts[0]
    wording = re.sub(r"^Question\s*:\s*", "", wording, flags=re.I).strip()

    options: list[dict] = []
    # split() with a capturing group yields [head, letter, chunk, letter, chunk…]
    for i in range(1, len(parts) - 1, 2):
        letter = parts[i]
        chunk = parts[i + 1]
        label = re.sub(r"^[A-H]\)\s*", "", chunk).strip().rstrip(".").strip()
        if label:
            options.append({"letter": letter, "text": label})

    if not options or not correct:
        return None

    return {
        "question": wording,
        "options": options,
        "correct_letters": [c for c in correct if any(o["letter"] == c for o in options)],
        # The source document gives no rationale, and inventing one would put
        # words in the trainer's mouth.
        "explanation": "",
    }


def parse_document(path: Path) -> list[dict]:
    document = docx.Document(path)
    questions = []
    for paragraph in document.paragraphs:
        parsed = parse_question(paragraph.text)
        if parsed:
            questions.append(parsed)
    return questions


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert an official Word quiz to the player format")
    parser.add_argument("--docx", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    questions = parse_document(args.docx)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"questions": questions}, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"{len(questions)} questions -> {args.output}")
    for i, question in enumerate(questions, 1):
        letters = ", ".join(question["correct_letters"])
        print(f"  {i}. {question['question'][:64]}… ({len(question['options'])} options, réponse {letters})")


if __name__ == "__main__":
    main()
