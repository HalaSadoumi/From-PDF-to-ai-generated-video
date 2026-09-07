"""Le studio, sans serveur ni réseau.

Ce qui est testé ici est la partie qui décide : l'identifiant tiré d'un titre
saisi à la main, et la lecture de l'avancement sur le disque. Le reste — HTTP,
sous-processus — n'a pas de logique propre à vérifier.
"""

import json

from s2m_pipeline.studio import jobs


# ------------------------------------------------------------- identifiants
def test_slugify_strips_accents_and_punctuation():
    assert jobs.slugify("Sécurité SI : une priorité pour chacun") == "securite_si_une_priorite_pour_chacun"


def test_slugify_never_returns_an_empty_identifier():
    # Le titre devient un nom de dossier et un segment d'URL : une chaîne vide
    # publierait le cours à la racine de web/data/.
    assert jobs.slugify("!!! ???") == "cours"


def test_unique_course_id_does_not_overwrite_an_existing_course():
    taken = {"securite_si", "securite_si_2"}
    assert jobs.unique_course_id("Sécurité SI", taken) == "securite_si_3"


def test_unique_course_id_keeps_the_plain_name_when_it_is_free():
    assert jobs.unique_course_id("Sécurité SI", set()) == "securite_si"


# ---------------------------------------------------------------- avancement
def _tree(tmp_path, *, pages=0, chapters=0, scenes=0, backdrops=0, videos=0, cues=0,
          marks=False, visuals=False, published=False):
    output = tmp_path / "output"
    videos_dir = tmp_path / "render"
    published_dir = tmp_path / "web"
    output.mkdir(parents=True, exist_ok=True)

    if pages:
        (output / "pages.json").write_text(json.dumps([{}] * pages), encoding="utf-8")
    if chapters:
        (output / "chapters.json").write_text(json.dumps([{}] * chapters), encoding="utf-8")
    if scenes:
        (output / "storyboard.json").write_text(json.dumps([{}] * scenes), encoding="utf-8")
    if marks:
        (output / "narration_marks.json").write_text("{}", encoding="utf-8")
    if visuals:
        (output / "scene_visuals.json").write_text("{}", encoding="utf-8")
    for index in range(cues):
        (output / "subtitles").mkdir(exist_ok=True)
        (output / "subtitles" / f"chapter_{index:02d}.vtt").write_text("", encoding="utf-8")
    for index in range(backdrops):
        (output / "work" / "backdrops").mkdir(parents=True, exist_ok=True)
        (output / "work" / "backdrops" / f"s{index}.jpg").write_bytes(b"")
    for index in range(videos):
        videos_dir.mkdir(exist_ok=True)
        (videos_dir / f"chapter_{index:02d}.mp4").write_bytes(b"")
    if published:
        published_dir.mkdir(exist_ok=True)
        (published_dir / "course_chapters.json").write_text("[]", encoding="utf-8")

    return jobs.stage_report(output, videos_dir, published_dir)


def test_a_fresh_run_shows_the_first_stage_as_current(tmp_path):
    report = _tree(tmp_path)
    assert [s["state"] for s in report][:2] == ["current", "pending"]
    assert jobs.completed_stages(report) == 0


def test_exactly_one_stage_is_current(tmp_path):
    report = _tree(tmp_path, pages=28, chapters=8, scenes=68)
    assert sum(1 for s in report if s["state"] == "current") == 1


def test_a_partial_render_is_not_reported_as_finished(tmp_path):
    # Cinq vidéos sur huit : l'étage est en cours, pas terminé. Se contenter de
    # l'existence du dossier ferait afficher « publié » à mi-parcours.
    report = _tree(tmp_path, pages=28, chapters=8, scenes=68, marks=True, visuals=True,
                   cues=8, backdrops=68, videos=5)
    render = next(s for s in report if s["key"] == "render")
    assert render["state"] == "current"
    assert render["detail"] == "5 / 8"


def test_a_complete_run_reports_every_stage_done(tmp_path):
    report = _tree(tmp_path, pages=28, chapters=8, scenes=68, marks=True, visuals=True,
                   cues=8, backdrops=68, videos=8, published=True)
    assert jobs.completed_stages(report) == len(jobs.STAGES)
    assert all(s["state"] == "done" for s in report)


def test_the_report_always_covers_every_stage(tmp_path):
    report = _tree(tmp_path, pages=28)
    assert [s["key"] for s in report] == [s.key for s in jobs.STAGES]


# -------------------------------------------------------------------- commande
def test_command_matches_the_documented_one(tmp_path):
    job = jobs.Job(
        id="abc", course_id="mon_cours", title="Mon cours", description="Une description",
        track="essentiel", pdf_name="support.pdf", pdf_path="/tmp/support.pdf",
    )
    command = jobs.command_for(job, tmp_path, "python")
    assert command[:3] == ["python", "-m", "s2m_pipeline.from_slides.build_course_from_pdf"]
    assert "--quiz-docx" not in command
    for flag, value in (("--course-id", "mon_cours"), ("--title", "Mon cours"),
                        ("--track", "essentiel")):
        assert command[command.index(flag) + 1] == value


def test_the_official_quiz_is_passed_when_there_is_one(tmp_path):
    job = jobs.Job(
        id="abc", course_id="c", title="T", description="D", track="essentiel",
        pdf_name="s.pdf", pdf_path="/tmp/s.pdf", quiz_path="/tmp/quiz.docx",
    )
    command = jobs.command_for(job, tmp_path, "python")
    assert command[command.index("--quiz-docx") + 1] == "/tmp/quiz.docx"


# ------------------------------------------------------- persistance du studio
def test_saving_keeps_jobs_written_by_another_instance(tmp_path, monkeypatch):
    """Une production deposee ailleurs ne doit pas disparaitre a notre ecriture.

    Deux serveurs qui tournent en meme temps tiennent chacun leur liste en
    memoire. Le second qui ecrit effacait la difference : c'est ainsi qu'une
    production reelle a ete perdue.
    """
    from s2m_pipeline.studio import runner as runner_mod

    store = tmp_path / "jobs.json"
    monkeypatch.setattr(runner_mod, "STORE_FILE", store)
    monkeypatch.setattr(runner_mod, "UPLOADS_DIR", tmp_path / "supports")
    monkeypatch.setattr(runner_mod, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(runner_mod, "OUTPUT_ROOT", tmp_path / "output")

    worker = runner_mod.Runner()
    # Deja terminee : le fil d'execution la laisse tranquille, et le test porte
    # sur la fusion a l'ecriture plutot que sur une course avec le travailleur.
    worker.submit(jobs.Job(id="a", course_id="a", title="A", description="", track="essentiel",
                           pdf_name="a.pdf", pdf_path="a.pdf", state=jobs.DONE))

    # Une autre instance ajoute sa propre production, directement sur le disque.
    data = json.loads(store.read_text(encoding="utf-8"))
    data["jobs"].append({"id": "b", "course_id": "b", "title": "B", "description": "",
                         "track": "essentiel", "pdf_name": "b.pdf", "pdf_path": "b.pdf",
                         "state": "queued"})
    store.write_text(json.dumps(data), encoding="utf-8")

    worker._save()
    kept = {entry["id"] for entry in json.loads(store.read_text(encoding="utf-8"))["jobs"]}
    assert kept == {"a", "b"}


def test_a_forgotten_job_does_not_come_back(tmp_path, monkeypatch):
    from s2m_pipeline.studio import runner as runner_mod

    store = tmp_path / "jobs.json"
    monkeypatch.setattr(runner_mod, "STORE_FILE", store)
    monkeypatch.setattr(runner_mod, "UPLOADS_DIR", tmp_path / "supports")
    monkeypatch.setattr(runner_mod, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(runner_mod, "OUTPUT_ROOT", tmp_path / "output")

    worker = runner_mod.Runner()
    job = jobs.Job(id="a", course_id="a", title="A", description="", track="essentiel",
                   pdf_name="a.pdf", pdf_path="a.pdf", state=jobs.DONE)
    worker.submit(job)
    assert worker.forget("a")
    worker._save()
    assert json.loads(store.read_text(encoding="utf-8"))["jobs"] == []
