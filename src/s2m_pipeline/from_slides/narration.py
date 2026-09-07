"""Sprint 3 (part 3): narration audio synthesis per storyboard scene.

storyboard.py estimates each scene's `duration` from narration word count,
before any audio exists. This module synthesizes the real narration audio
(edge-tts) per scene and corrects `duration` to match the actual audio
length, since downstream visual timing (Sprint 3-4) needs to sync to real
audio, not a word-count guess.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tqdm import tqdm

from s2m_pipeline.from_slides import tts
from s2m_pipeline.models import StoryboardScene


def synthesize_narration(
    scenes: list[StoryboardScene], output_dir: Path
) -> list[StoryboardScene]:
    updated: list[StoryboardScene] = []
    for scene in tqdm(scenes, desc="Synthesizing narration"):
        audio_path = output_dir / f"{scene.scene_id}.mp3"
        tts.synthesize(scene.narration, audio_path)
        real_duration = tts.audio_duration_seconds(audio_path)

        updated.append(
            scene.model_copy(
                update={"duration": round(real_duration, 2), "audio_path": str(audio_path)}
            )
        )
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="S2M Sprint 3 narration synthesis")
    parser.add_argument("--storyboard", required=True, type=Path, help="Path to storyboard.json")
    parser.add_argument(
        "--output-dir", required=True, type=Path, help="Where to write narration audio files"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Updated storyboard JSON path (default: overwrite --storyboard)",
    )
    args = parser.parse_args()

    scenes = [
        StoryboardScene.model_validate(s)
        for s in json.loads(args.storyboard.read_text(encoding="utf-8"))
    ]
    updated = synthesize_narration(scenes, args.output_dir)

    output_path = args.output or args.storyboard
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([s.model_dump() for s in updated], f, ensure_ascii=False, indent=2)

    total_duration = sum(s.duration for s in updated)
    print(f"\nDone. {len(updated)} narration clips written to {args.output_dir}")
    print(f"      Updated storyboard (real durations) written to {output_path}")
    print(f"      Total narration duration: {total_duration / 60:.1f} min")


if __name__ == "__main__":
    main()
