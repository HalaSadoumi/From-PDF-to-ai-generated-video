"""Mise en scene et rendu : ce qui transforme un plan en videos.

Ces trois fonctions ne savent pas d'ou vient le contenu. Elles lisent un objet
qui expose storyboard, visuals, narration_dir et backdrops, et produisent une
video par chapitre. C'est pourquoi elles vivent dans core/ : la chaine issue
d'un enregistrement et celle issue d'un support s'en servent a l'identique.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Protocol

from s2m_pipeline.core import scene_images


class Paths(Protocol):
    """Le contrat que ces fonctions attendent d'une production.

    Volontairement minimal : un orchestrateur peut ranger ses fichiers comme il
    l'entend du moment qu'il expose ces cinq chemins.
    """

    storyboard: Path
    visuals: Path
    chapters: Path
    narration_dir: Path
    backdrops: Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REMOTION_DIR = PROJECT_ROOT / "remotion"


def run_images(paths: Paths) -> None:
    plans: dict[str, dict] = json.loads(paths.visuals.read_text(encoding="utf-8"))
    paths.backdrops.mkdir(parents=True, exist_ok=True)

    pending = [
        (sid, p) for sid, p in plans.items() if not (paths.backdrops / f"{sid}.jpg").exists()
    ]
    print(f"  {len(plans) - len(pending)}/{len(plans)} already generated, {len(pending)} to go")

    from tqdm import tqdm

    failed = 0
    for scene_id, plan in tqdm(pending, desc="  backdrops"):
        prompt = plan.get("image_prompt") or plan.get("label") or "abstract professional background"
        seed = scene_images.seed_for(scene_id)
        if not scene_images.fetch_image(prompt, paths.backdrops / f"{scene_id}.jpg", seed):
            failed += 1

    present = sum(1 for s in plans if (paths.backdrops / f"{s}.jpg").exists())
    _done(f"{present}/{len(plans)} backdrops" + (f", {failed} failed (re-run to retry)" if failed else ""))


def _sync_remotion_inputs(paths: Paths) -> None:
    """Stage this run's data where the Remotion project reads it.

    Le dossier est vide au depart de chaque rendu. C'est indispensable, pas une
    precaution : les deux entrees numerotent leurs scenes de la meme facon, donc
    `chapter_03_scene_00.wav` existe dans les deux cours. Une version qui ne
    copiait que les fichiers absents a laisse la voix de l'intervenant en place
    pour toutes les scenes dont l'identifiant existait deja, et le cours issu du
    support est sorti avec la mauvaise voix sur trente-deux scenes.
    """
    public = REMOTION_DIR / "public"
    for nom in ("audio", "backdrops"):
        shutil.rmtree(public / nom, ignore_errors=True)
        (public / nom).mkdir(parents=True, exist_ok=True)

    shutil.copy(paths.storyboard, public / "storyboard.json")
    shutil.copy(paths.visuals, public / "scene_visuals.json")

    # public/ ne contient que des copies de travail : il doit pouvoir etre vide
    # sans rien perdre. Le logo est un asset source, il vit donc dans
    # remotion/assets/ et est remis en place ici a chaque rendu.
    logo = REMOTION_DIR / "assets" / "s2m-logo.png"
    if logo.exists():
        shutil.copy(logo, public / logo.name)

    for src in paths.narration_dir.glob("*.wav"):
        shutil.copy(src, public / "audio" / src.name)
    for src in paths.backdrops.glob("*.jpg"):
        shutil.copy(src, public / "backdrops" / src.name)

    available = sorted(p.stem for p in (public / "backdrops").glob("*.jpg"))
    (public / "backdrops.json").write_text(json.dumps(available), encoding="utf-8")


def run_render(paths: Paths, out_name: str = "out") -> None:
    """Render one video per chapter.

    `out_name` lets a second course render beside the first instead of
    overwriting it. It may name a nested folder -- the slide-deck pipeline
    passes out_pdf/<course_id>, so two courses never share a target: without
    that, the second course would find the first's chapter_00.mp4, consider it
    already rendered, and publish someone else's video."""
    _sync_remotion_inputs(paths)
    out_dir = REMOTION_DIR / out_name
    out_dir.mkdir(parents=True, exist_ok=True)

    chapters = json.loads(paths.chapters.read_text(encoding="utf-8"))
    npx = shutil.which("npx") or "npx"

    for i, chapter in enumerate(chapters, start=1):
        chapter_id = chapter["id"]
        target = out_dir / f"{chapter_id}.mp4"
        if target.exists() and target.stat().st_size > 0:
            print(f"  [{i}/{len(chapters)}] {chapter_id} — already rendered")
            continue

        print(f"  [{i}/{len(chapters)}] {chapter_id} — rendering...")
        composition_id = chapter_id.replace("_", "-")
        result = subprocess.run(
            [
                npx, "remotion", "render", "src/index.ts", composition_id,
                str(Path(out_name) / f"{chapter_id}.mp4"),
                "--log=error",
                # The generated backdrops are blurred and composited, so a
                # frame can take well over Remotion's 30s default on a busy
                # CPU-only machine; a long per-frame budget avoids losing a
                # whole chapter to one slow frame.
                "--timeout=180000",
                # Leave a core free so the machine stays usable during the
                # multi-hour batch.
                "--concurrency=50%",
            ],
            cwd=REMOTION_DIR,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            target.unlink(missing_ok=True)
            print(f"      FAILED:\n{result.stderr[-1500:]}")
        else:
            print(f"      done ({target.stat().st_size // 1_000_000} MB)")
