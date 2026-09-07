"""Tests des fonctions qui portent les decisions de la chaine.

Ce sont celles qu'un repreneur voudra modifier, et celles dont les regressions
sont invisibles dans la video finie : un decoupage desequilibre ou un
arriere-plan qui change d'une execution a l'autre ne se voit qu'a la lecture,
des heures apres l'erreur.

Toutes sont pures : ni reseau, ni modele, ni cle d'API.
"""

from __future__ import annotations

import json

import pytest

from s2m_pipeline.core.llm import _clip_on_word

# --------------------------------------------------------------------------
# Fallback card: never cut a sentence mid-word on screen
# --------------------------------------------------------------------------

def test_clipping_falls_on_a_word_boundary():
    text = "ça concerne la protection des données contre tout accès au début de l'exercice"
    clipped = _clip_on_word(text, limit=60)

    assert clipped.endswith("…")
    assert not clipped[:-1].endswith(" ")
    assert clipped[:-1] in text


def test_short_text_is_left_alone():
    assert _clip_on_word("phrase courte", limit=60) == "phrase courte"


def test_whitespace_is_normalised():
    assert _clip_on_word("  deux   espaces  ", limit=60) == "deux espaces"


# --------------------------------------------------------------------------
# Reproductibilité : relancer le système doit redonner le même résultat
# --------------------------------------------------------------------------

def test_backdrop_seed_is_stable_across_processes():
    """The seed must not move between runs.

    It used to be `hash(scene_id)`, which Python randomises per process: three
    runs gave 20468, 8410 and 54640 for the same scene, so every execution
    fetched a fresh set of images while the comment claimed the opposite.
    """
    from s2m_pipeline.core.scene_images import seed_for

    # Valeur figée : si elle change, les arrière-plans de tous les cours
    # déjà produits ne seraient plus reproductibles.
    assert seed_for("chapter_00_scene_00") == 15188
    assert seed_for("chapter_00_scene_00") == seed_for("chapter_00_scene_00")
    assert seed_for("chapter_00_scene_00") != seed_for("chapter_00_scene_01")
    assert 0 <= seed_for("chapter_12_scene_07") < 100_000


def test_every_model_call_is_forced_to_temperature_zero():
    """Sampling made the pipeline give a different edit on each run.

    The temperature is applied in `_generate_content`, the single entry point,
    so a call site added later cannot forget it.
    """
    from s2m_pipeline.core import llm

    class FakeConfig:
        temperature = None

    class FakeClient:
        class models:
            @staticmethod
            def generate_content(**kwargs):
                return kwargs

    config = FakeConfig()
    llm._generate_content(FakeClient(), model="x", contents=[], config=config)

    assert config.temperature == 0.0


def test_an_explicit_temperature_is_left_alone():
    """A call that deliberately asks for sampling keeps its own setting."""
    from s2m_pipeline.core import llm

    class FakeConfig:
        temperature = 0.8

    class FakeClient:
        class models:
            @staticmethod
            def generate_content(**kwargs):
                return kwargs

    config = FakeConfig()
    llm._generate_content(FakeClient(), model="x", contents=[], config=config)

    assert config.temperature == 0.8


# --------------------------------------------------------------------------
# Support de cours : lecture du document et découpage en chapitres
# --------------------------------------------------------------------------

def slide(index: int, text: str):
    from s2m_pipeline.models import Scene
    from s2m_pipeline.from_slides.pdf_source import PAGE_SECONDS

    return Scene(
        id=f"page_{index:03d}",
        start=index * PAGE_SECONDS,
        end=(index + 1) * PAGE_SECONDS,
        ocr_text=text,
    )


def test_section_dividers_are_recognised_without_knowing_the_subject():
    """A divider is short and in capitals — a rule that holds for any deck."""
    from s2m_pipeline.from_slides import pdf_source

    assert pdf_source.is_section_divider("DÉFINITIONS ET PRINCIPES DE BASE")
    assert pdf_source.is_section_divider("IMPACT DE LA CYBERCRIMINALITÉ")
    # La page de clôture est courte mais pas en capitales : ce n'est pas un
    # séparateur, et la confondre couperait un chapitre en trop.
    assert not pdf_source.is_section_divider(
        "Sécurité SI : Une priorité pour chacun Questions & Réponses"
    )
    # Une page de contenu, même brève, n'en est pas un non plus.
    assert not pdf_source.is_section_divider(
        "Le risque cyber est la priorité numéro 1 des entreprises marocaines en 2024"
    )


def test_chapters_never_span_two_sections():
    from s2m_pipeline.from_slides import pdf_source

    pages = [
        slide(0, "PREMIERE SECTION"),
        slide(1, "contenu " * 40),
        slide(2, "DEUXIEME SECTION"),
        slide(3, "contenu " * 40),
    ]
    groups = pdf_source.group_into_chapters(pages)

    assert len(groups) == 2
    assert [s.id for s in groups[0]] == ["page_000", "page_001"]
    assert [s.id for s in groups[1]] == ["page_002", "page_003"]


def test_a_long_section_is_split_evenly_rather_than_leaving_a_stub():
    """Filling to the target and letting the remainder trail produced a
    251-word chapter followed by a 72-word one; the split is now balanced."""
    from s2m_pipeline.from_slides import pdf_source

    pages = [slide(0, "SECTION UNIQUE")] + [slide(i, "mot " * 100) for i in range(1, 7)]
    groups = pdf_source.group_into_chapters(pages)
    sizes = [sum(len(s.ocr_text.split()) for s in g) for g in groups]

    assert len(groups) >= 2
    assert max(sizes) <= 2 * min(sizes)


def test_deck_length_drives_the_number_of_chapters():
    """Twice the material, roughly twice the chapters — no fixed count."""
    from s2m_pipeline.from_slides import pdf_source

    short = [slide(0, "SECTION")] + [slide(i, "mot " * 100) for i in range(1, 4)]
    long = [slide(0, "SECTION")] + [slide(i, "mot " * 100) for i in range(1, 8)]

    assert len(pdf_source.group_into_chapters(long)) > len(
        pdf_source.group_into_chapters(short)
    )


# --------------------------------------------------------------------------
# Quiz officiel fourni en Word
# --------------------------------------------------------------------------

def test_official_question_is_read_exactly():
    """The wording, the options and the answers must survive untouched: this
    is the trainer's quiz, not one to paraphrase."""
    from s2m_pipeline.core.quiz_reference import parse_question

    parsed = parse_question(
        'Question: Quels sont les trois objectifs fondamentaux de la cybersécurité, '
        'souvent désignés par le sigle "CID" ? (Sélectionnez toutes les réponses '
        "pertinentes) A) Confidentialité B) Intégrité C) Disponibilité D) Conformité "
        "E) Durabilité Bonnes Réponses: A, B et C"
    )

    assert parsed is not None
    assert parsed["question"].startswith("Quels sont les trois objectifs")
    assert [o["letter"] for o in parsed["options"]] == ["A", "B", "C", "D", "E"]
    assert parsed["options"][0]["text"] == "Confidentialité"
    assert parsed["correct_letters"] == ["A", "B", "C"]


def test_single_answer_question_is_read():
    from s2m_pipeline.core.quiz_reference import parse_question

    parsed = parse_question(
        "Question: Qu'est-ce que la \"Confidentialité\" ? "
        "A) La garantie que les données sont exactes. "
        "B) La protection des données contre l'accès non autorisé. "
        "Bonne Réponse: B"
    )

    assert parsed["correct_letters"] == ["B"]
    assert len(parsed["options"]) == 2


def test_a_paragraph_that_is_not_a_question_is_ignored():
    from s2m_pipeline.core.quiz_reference import parse_question

    assert parse_question("Module La Sécurité SI – Une priorité pour chacun Quiz") is None
    assert parse_question("") is None


# --------------------------------------------------------------------------
# Variété des schémas à l'intérieur d'un chapitre
# --------------------------------------------------------------------------

def plans_of(*archetypes, items=3):
    return [{"archetype": a, "items": ["x"] * items} for a in archetypes]


def test_a_run_of_identical_diagrams_is_broken_up():
    """Four bar charts in a row read as one slide repeated — the complaint the
    visuals exist to answer."""
    from s2m_pipeline.core.scene_visuals import diversify

    plans = plans_of("bar_chart", "bar_chart", "bar_chart", "bar_chart")
    diversify(plans)
    drawn = [p["archetype"] for p in plans]

    assert all(a != b for a, b in zip(drawn, drawn[1:]))


def test_diversifying_never_leaves_two_neighbours_alike():
    from s2m_pipeline.core.scene_visuals import diversify

    for run in (
        ["timeline"] * 4 + ["pillars"],
        ["title_statement"] * 5,
        ["checklist", "checklist", "checklist", "hierarchy", "checklist"],
    ):
        plans = plans_of(*run)
        diversify(plans)
        drawn = [p["archetype"] for p in plans]
        assert all(a != b for a, b in zip(drawn, drawn[1:])), drawn


def test_a_substitute_keeps_the_meaning_of_the_scene():
    """A sequence must not become a set, nor a proportion a ranking: swaps stay
    inside a group of diagrams that take the same shape of content."""
    from s2m_pipeline.core.scene_visuals import _INTERCHANGEABLE, _alternatives

    groups = {a: g for g in _INTERCHANGEABLE for a in g}
    for archetype in ("timeline", "bar_chart", "stat_reveal"):
        # Le premier choix reste dans le groupe d'origine.
        assert _alternatives(archetype, {"items": []})[0] in groups[archetype]


def test_an_already_varied_chapter_is_left_alone():
    from s2m_pipeline.core.scene_visuals import diversify

    plans = plans_of("timeline", "pillars", "bar_chart", "checklist", "data_flow")
    before = [p["archetype"] for p in plans]

    assert diversify(plans) == 0
    assert [p["archetype"] for p in plans] == before


# ------------------------------------------------- mise en scene pour le rendu
def test_staging_replaces_a_file_left_by_another_course(tmp_path, monkeypatch):
    """Le dossier de rendu ne doit rien garder de la production precedente.

    Les deux entrees numerotent leurs scenes de la meme facon : le fichier
    chapter_03_scene_00.wav existe dans le cours issu de l'enregistrement comme
    dans celui issu du support. Une version qui ne copiait que les fichiers
    absents a laisse la voix de l'intervenant en place sur trente-deux scenes du
    cours qui devait etre lu par la voix de synthese, et le defaut ne s'entendait
    qu'a la lecture du montage.
    """
    from types import SimpleNamespace

    from s2m_pipeline.core import render as build_course

    remotion = tmp_path / "remotion"
    (remotion / "public" / "audio").mkdir(parents=True)
    (remotion / "public" / "backdrops").mkdir(parents=True)
    monkeypatch.setattr(build_course, "REMOTION_DIR", remotion)

    # Ce qu'une production precedente a laisse derriere elle.
    (remotion / "public" / "audio" / "chapter_03_scene_00.wav").write_bytes(b"voix precedente")
    (remotion / "public" / "audio" / "chapter_09_scene_00.wav").write_bytes(b"scene inconnue ici")
    (remotion / "public" / "backdrops" / "chapter_09_scene_00.jpg").write_bytes(b"vieux fond")

    course = tmp_path / "course"
    (course / "work" / "narration").mkdir(parents=True)
    (course / "work" / "backdrops").mkdir(parents=True)
    (course / "work" / "narration" / "chapter_03_scene_00.wav").write_bytes(b"voix attendue")
    (course / "work" / "backdrops" / "chapter_03_scene_00.jpg").write_bytes(b"fond attendu")
    (course / "storyboard.json").write_text("[]", encoding="utf-8")
    (course / "scene_visuals.json").write_text("{}", encoding="utf-8")

    # `Paths` est un protocole, pas une classe : la mise en scene accepte
    # n'importe quel objet exposant ces cinq chemins.
    build_course._sync_remotion_inputs(SimpleNamespace(
        storyboard=course / "storyboard.json",
        visuals=course / "scene_visuals.json",
        chapters=course / "chapters.json",
        narration_dir=course / "work" / "narration",
        backdrops=course / "work" / "backdrops",
    ))

    audio = remotion / "public" / "audio"
    assert (audio / "chapter_03_scene_00.wav").read_bytes() == b"voix attendue"
    # La scene qui n'appartient pas a cette production ne doit plus etre la :
    # c'est elle qui, restee en place, avait fourni la mauvaise voix.
    assert not (audio / "chapter_09_scene_00.wav").exists()
    assert not (remotion / "public" / "backdrops" / "chapter_09_scene_00.jpg").exists()

    listing = json.loads((remotion / "public" / "backdrops.json").read_text(encoding="utf-8"))
    assert listing == ["chapter_03_scene_00"]


# ------------------------------------------------- integrite des modules
def test_no_module_uses_an_undefined_name():
    """Aucun module n'appelle un nom qui n'existe pas chez lui.

    Ce test est ne d'un defaut reel : en deplacant les fonctions de rendu vers
    core/render.py, la fonction d'affichage _done qu'elles appellent est restee
    dans le module d'origine. Rien ne le signalait — ni l'import, ni la
    compilation — parce qu'un nom manquant ne leve une erreur qu'a l'instant ou
    la ligne s'execute. La production s'est arretee apres une heure de calcul,
    sur la derniere ligne de l'etage des arriere-plans.
    """
    import ast
    import builtins
    import pathlib

    racine = pathlib.Path(__file__).resolve().parents[1] / "src"
    connus = set(dir(builtins)) | {"__file__", "__name__", "__doc__"}
    fautifs: dict[str, list[str]] = {}

    for fichier in sorted(racine.rglob("*.py")):
        arbre = ast.parse(fichier.read_text(encoding="utf-8"))
        definis: set[str] = set()
        for noeud in ast.walk(arbre):
            if isinstance(noeud, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                definis.add(noeud.name)
            elif isinstance(noeud, ast.Name) and isinstance(noeud.ctx, ast.Store):
                definis.add(noeud.id)
            elif isinstance(noeud, ast.arg):
                definis.add(noeud.arg)
            elif isinstance(noeud, (ast.Import, ast.ImportFrom)):
                for alias in noeud.names:
                    definis.add((alias.asname or alias.name).split(".")[0])
            elif isinstance(noeud, ast.ExceptHandler) and noeud.name:
                definis.add(noeud.name)
            elif isinstance(noeud, ast.comprehension) and isinstance(noeud.target, ast.Name):
                definis.add(noeud.target.id)

        manquants = sorted({
            noeud.id for noeud in ast.walk(arbre)
            if isinstance(noeud, ast.Name) and isinstance(noeud.ctx, ast.Load)
            and noeud.id not in definis and noeud.id not in connus
        })
        if manquants:
            fautifs[str(fichier.relative_to(racine))] = manquants

    assert not fautifs, f"noms utilises mais jamais definis : {fautifs}"
