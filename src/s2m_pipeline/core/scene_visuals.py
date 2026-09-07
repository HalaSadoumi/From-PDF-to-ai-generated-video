"""Sprint 3 (visual generation): map every narration scene to an animated
scene archetype.

This is the layer that makes the visual generation a *system* rather than a
set of hand-authored scenes: for each storyboard scene, the LLM picks one of
the closed vocabulary of archetypes in llm.SCENE_ARCHETYPES (each backed by a
self-animating Remotion component) and fills in its text slots, driven by
what the narration actually says plus the OCR text of the slides on screen at
that moment.

Output (scene_visuals.json) is consumed directly by the renderer, so adding a
new archetype means adding one component + one vocabulary entry, never
per-scene code.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tqdm import tqdm

from s2m_pipeline.core import llm
from s2m_pipeline.models import Scene, StoryboardScene


def _overlapping_ocr(scenes: list[Scene], start: float, end: float) -> str:
    overlapping = [s for s in scenes if s.start < end and s.end > start]
    return "\n".join(dict.fromkeys(s.ocr_text for s in overlapping if s.ocr_text))


def build_scene_visuals(
    storyboard: list[StoryboardScene],
    scenes: list[Scene],
    chapters_bounds: dict[str, tuple[float, float]],
    output_path: Path,
    resume: bool = False,
) -> dict[str, dict]:
    """Returns {scene_id: visual plan dict}, checkpointed per chapter."""
    plans: dict[str, dict] = {}
    if resume and output_path.exists():
        plans = json.loads(output_path.read_text(encoding="utf-8"))

    by_chapter: dict[str, list[StoryboardScene]] = {}
    for s in storyboard:
        by_chapter.setdefault(s.chapter_id, []).append(s)

    for chapter_id, chapter_scenes in tqdm(by_chapter.items(), desc="Planning scene visuals"):
        if all(s.scene_id in plans for s in chapter_scenes):
            continue

        start, end = chapters_bounds.get(chapter_id, (0.0, 0.0))
        ocr_text = _overlapping_ocr(scenes, start, end)
        indexed = [(i, s.narration) for i, s in enumerate(chapter_scenes)]

        chapter_plans = llm.generate_scene_visual_plans(indexed, ocr_text)

        chapter_dicts = []
        for i, scene in enumerate(chapter_scenes):
            # Dump every field the plan model carries rather than listing them
            # here: an earlier version enumerated them by hand and silently
            # dropped two fields added later, which the renderer then never saw.
            chapter_dicts.append(chapter_plans[i].model_dump(exclude={"index"}))

        # Variety is enforced here rather than asked of the model: the planner
        # cannot see the chapter as a whole, so it repeats a diagram without
        # knowing it.
        reassigned = diversify(chapter_dicts)
        if reassigned:
            print(f"    {chapter_id}: {reassigned} scene(s) redrawn to avoid repetition", flush=True)

        for scene, plan in zip(chapter_scenes, chapter_dicts):
            plans[scene.scene_id] = plan

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(plans, f, ensure_ascii=False, indent=2)

    return plans


def main() -> None:
    parser = argparse.ArgumentParser(description="S2M scene visual planning")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--scenes", required=True, type=Path)
    parser.add_argument("--chapters", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("output/scene_visuals.json"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    storyboard = [
        StoryboardScene.model_validate(s)
        for s in json.loads(args.storyboard.read_text(encoding="utf-8"))
    ]
    scenes = [Scene.model_validate(s) for s in json.loads(args.scenes.read_text(encoding="utf-8"))]
    chapters = json.loads(args.chapters.read_text(encoding="utf-8"))
    bounds = {c["id"]: (c["start"], c["end"]) for c in chapters}

    plans = build_scene_visuals(storyboard, scenes, bounds, args.output, resume=args.resume)

    counts: dict[str, int] = {}
    for p in plans.values():
        counts[p["archetype"]] = counts.get(p["archetype"], 0) + 1

    print(f"\nDone. {len(plans)} scene visual plans written to {args.output}")
    for archetype, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {archetype:18s} {n}")

# Archetypes that take the same shape of content, so one can stand in for
# another without misrepresenting the scene: the items keep their meaning and
# only the drawing changes. The groups stay narrow because swapping across them
# would lie — a sequence is not a set, a proportion is not a ranking.
_INTERCHANGEABLE: tuple[tuple[str, ...], ...] = (
    ("checklist", "pillars", "hierarchy", "pyramid", "concentric_layers"),
    ("timeline", "funnel", "cycle"),
    ("bar_chart", "stat_row", "ranking_list"),
    ("stat_reveal", "donut_share"),
    ("title_statement", "quote_highlight"),
    ("comparison", "separated_groups", "do_dont"),
)

# Any scene carrying two or more named items can be drawn as one of these,
# whatever the planner first chose: they only need a list of short labels.
_LIST_SHAPED = ("checklist", "pillars", "hierarchy", "pyramid", "concentric_layers")

# How far back to look before calling an archetype "just seen".
_RECENT_WINDOW = 3


def _alternatives(archetype: str, plan: dict) -> list[str]:
    """Archetypes that could draw this same plan without changing its meaning."""
    options: list[str] = []
    for group in _INTERCHANGEABLE:
        if archetype in group:
            options.extend(a for a in group if a != archetype)
            break
    # A two-member group runs out after one swap. Any scene that carries named
    # items can also be drawn as a list-shaped diagram, which gives the pass
    # somewhere to go on a long run of the same card.
    if len([i for i in (plan.get("items") or []) if i and i.strip()]) >= 2:
        options.extend(a for a in _LIST_SHAPED if a != archetype and a not in options)
    return options


def diversify(plans: list[dict]) -> int:
    """Break up runs of the same diagram inside one chapter, in place.

    The planner judges each scene on its own merits, so a chapter about figures
    came out as four bar charts in a row and a chapter of definitions as four
    typographic cards. Every choice was defensible; watched end to end they read
    as one slide repeated — which is exactly the complaint the visuals were
    meant to answer.

    Returns how many scenes were reassigned.
    """
    seen: list[str] = []
    changed = 0
    for plan in plans:
        archetype = plan.get("archetype", "")
        recent = seen[-_RECENT_WINDOW:]
        if archetype in recent:
            for candidate in _alternatives(archetype, plan):
                if candidate not in recent:
                    plan["archetype"] = candidate
                    archetype = candidate
                    changed += 1
                    break
        seen.append(archetype)
    return changed


if __name__ == "__main__":
    main()
