"""Generate one ambience illustration per scene, used as an animated backdrop.

Complements the programmatic diagrams rather than replacing them: diffusion
models cannot render legible text, so anything information-bearing (labels,
figures, process steps) stays vector-drawn on top, while the generated image
supplies subject-appropriate atmosphere behind it. This is also what keeps
the visuals from being tied to one subject matter - the prompt comes from the
narration, so a video on any topic gets fitting imagery.

Images are requested from a free, key-less endpoint and cached on disk;
re-running skips whatever already exists, so an interrupted batch resumes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

from tqdm import tqdm

# Shared look so the 261 backdrops feel like one production rather than a
# grab-bag. Deliberately dark and low-contrast: text and diagrams are drawn
# over these, and they must stay readable.
STYLE_SUFFIX = (
    "dark navy background, subtle abstract corporate illustration, "
    "deep blue and violet tones, minimal, cinematic soft lighting, "
    "no text, no letters, no words, low contrast, professional"
)

ENDPOINT = "https://image.pollinations.ai/prompt/{prompt}"
WIDTH = 1280
HEIGHT = 720


def seed_for(scene_id: str) -> int:
    """Stable per-scene seed for the image service.

    Python randomises string hashing per process, so `hash(scene_id)` gives a
    different value on every run — the opposite of what the seed is for. A
    digest of the id is stable across processes and machines, so re-running
    the pipeline reproduces the same backdrops instead of a fresh set.
    """
    digest = hashlib.sha1(scene_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % 100_000


def build_url(image_prompt: str, seed: int) -> str:
    full = f"{image_prompt}, {STYLE_SUFFIX}"
    quoted = urllib.parse.quote(full, safe="")
    return (
        ENDPOINT.format(prompt=quoted)
        + f"?width={WIDTH}&height={HEIGHT}&nologo=true&seed={seed}"
    )


def fetch_image(image_prompt: str, output_path: Path, seed: int, timeout: int = 120) -> bool:
    """Fetch one image; returns False on failure instead of aborting the batch."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        request = urllib.request.Request(
            build_url(image_prompt, seed), headers={"User-Agent": "Mozilla/5.0"}
        )
        data = urllib.request.urlopen(request, timeout=timeout).read()
    except Exception:
        return False

    # A truncated/blank response would render as a broken backdrop; treat
    # anything implausibly small as a failure so it can be retried later.
    if len(data) < 2000:
        return False

    output_path.write_bytes(data)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="S2M scene backdrop generation")
    parser.add_argument("--visuals", required=True, type=Path, help="scene_visuals.json")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--limit", type=int, default=None, help="Only generate the first N missing images"
    )
    args = parser.parse_args()

    plans: dict[str, dict] = json.loads(args.visuals.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    pending = [
        (scene_id, plan)
        for scene_id, plan in plans.items()
        if not (args.output_dir / f"{scene_id}.jpg").exists()
    ]
    if args.limit:
        pending = pending[: args.limit]

    print(f"{len(plans)} scenes, {len(pending)} images to generate")

    failed: list[str] = []
    for scene_id, plan in tqdm(pending, desc="Generating backdrops"):
        prompt = plan.get("image_prompt") or plan.get("label") or "abstract professional background"
        seed = seed_for(scene_id)
        if not fetch_image(prompt, args.output_dir / f"{scene_id}.jpg", seed):
            failed.append(scene_id)

    done = len(plans) - len(
        [s for s in plans if not (args.output_dir / f"{s}.jpg").exists()]
    )
    print(f"\nDone. {done}/{len(plans)} backdrops present in {args.output_dir}")
    if failed:
        print(f"      {len(failed)} failed this run — re-run to retry them:")
        for scene_id in failed[:10]:
            print(f"        {scene_id}")


if __name__ == "__main__":
    main()
