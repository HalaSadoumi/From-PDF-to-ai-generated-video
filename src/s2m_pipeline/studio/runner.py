"""La file d'attente : un seul travail à la fois, repris après un redémarrage.

Un rendu sature le processeur. Deux productions simultanées ne vont pas deux
fois plus vite, elles se gênent et rendent les durées imprévisibles. La file
est donc volontairement d'une place, et l'attente est affichée plutôt que
masquée.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from s2m_pipeline.studio import jobs as jobs_mod
from s2m_pipeline.studio.jobs import (
    CANCELLED, DONE, FAILED, FINISHED_STATES, INTERRUPTED, QUEUED, RUNNING, Job,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
STUDIO_DIR = PROJECT_ROOT / "work" / "studio"
UPLOADS_DIR = STUDIO_DIR / "supports"
LOGS_DIR = STUDIO_DIR / "logs"
STORE_FILE = STUDIO_DIR / "jobs.json"
OUTPUT_ROOT = PROJECT_ROOT / "output"
RENDER_ROOT = PROJECT_ROOT / "remotion" / "out_pdf"
PUBLISHED_ROOT = PROJECT_ROOT / "web" / "data"


class Runner:
    """Un travailleur, une file, un état sur disque."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: dict[str, Job] = {}
        self._order: list[str] = []
        self._wake = threading.Event()
        self._process: subprocess.Popen | None = None
        self._current: str | None = None
        # Retires volontairement : sans cela, la fusion a l'ecriture les
        # ferait revenir depuis le fichier a la sauvegarde suivante.
        self._forgotten: set[str] = set()
        for directory in (UPLOADS_DIR, LOGS_DIR, OUTPUT_ROOT):
            directory.mkdir(parents=True, exist_ok=True)
        self._load()
        threading.Thread(target=self._loop, daemon=True, name="studio-runner").start()

    # ------------------------------------------------------------ persistance
    def _load(self) -> None:
        try:
            raw = json.loads(STORE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for entry in raw.get("jobs", []):
            job = Job.from_dict(entry)
            # Un travail « en cours » au démarrage est un travail dont le
            # processus est mort avec le serveur. On le dit, plutôt que de
            # laisser une barre de progression tourner dans le vide ; la
            # chaîne étant reprenable, relancer ne recommence pas de zéro.
            if job.state == RUNNING:
                job.state = INTERRUPTED
                job.error = "Le serveur s'est arrêté pendant la production."
            self._jobs[job.id] = job
            self._order.append(job.id)
        self._wake.set()

    def _save(self) -> None:
        """Ecrire sans effacer ce qu'on ne connait pas.

        Une deuxieme instance du serveur -- lancee par erreur, ou restee en vie
        apres un arret incomplet -- tient sa propre liste en memoire. Si elle
        ecrit ce fichier apres nous, la difference entre les deux listes est
        perdue : une production deposee sur une instance disparait de l'autre.
        C'est arrive. On repart donc de ce qui est sur le disque et on n'y
        remplace que les travaux dont on a la charge.

        Cela reduit la fenetre sans la fermer : deux instances qui lisent puis
        ecrivent en meme temps peuvent encore se marcher dessus. La vraie
        protection est qu'il n'y en ait qu'une, ce que le port occupe garantit
        -- uvicorn refuse de demarrer si 8123 est deja pris.
        """
        STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            existing = json.loads(STORE_FILE.read_text(encoding="utf-8")).get("jobs", [])
        except (OSError, ValueError):
            existing = []

        mine = {job_id: self._jobs[job_id].to_dict() for job_id in self._order}
        merged, seen = [], set()
        for entry in existing:
            job_id = entry.get("id")
            if job_id in self._forgotten:
                continue
            merged.append(mine.get(job_id, entry))
            seen.add(job_id)
        merged += [mine[job_id] for job_id in self._order if job_id not in seen]

        STORE_FILE.write_text(
            json.dumps({"jobs": merged}, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    # ------------------------------------------------------------------ lecture
    def output_dir(self, job: Job) -> Path:
        return OUTPUT_ROOT / job.course_id

    def log_path(self, job: Job) -> Path:
        return LOGS_DIR / f"{job.id}.log"

    def describe(self, job: Job) -> dict:
        report = jobs_mod.stage_report(
            self.output_dir(job), RENDER_ROOT / job.course_id, PUBLISHED_ROOT / job.course_id
        )
        data = job.to_dict()
        data["stages"] = report
        data["completed"] = jobs_mod.completed_stages(report)
        data["total"] = len(report)
        data["queue_position"] = self._queue_position(job.id)
        return data

    def _queue_position(self, job_id: str) -> int:
        waiting = [i for i in self._order if self._jobs[i].state == QUEUED]
        return waiting.index(job_id) + 1 if job_id in waiting else 0

    def list(self) -> list[dict]:
        with self._lock:
            return [self.describe(self._jobs[i]) for i in reversed(self._order)]

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return self.describe(job) if job else None

    def tail(self, job_id: str, lines: int = 60) -> str:
        with self._lock:
            job = self._jobs.get(job_id)
        if not job:
            return ""
        try:
            content = self.log_path(job).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        return "\n".join(content.splitlines()[-lines:])

    def taken_course_ids(self) -> set[str]:
        with self._lock:
            used = {job.course_id for job in self._jobs.values()}
        if PUBLISHED_ROOT.is_dir():
            used |= {p.name for p in PUBLISHED_ROOT.iterdir() if p.is_dir()}
        return used

    # ----------------------------------------------------------------- écriture
    def submit(self, job: Job) -> Job:
        with self._lock:
            self._jobs[job.id] = job
            self._order.append(job.id)
            self._save()
        self._wake.set()
        return job

    def retry(self, job_id: str) -> bool:
        """Remettre en file un travail arrêté. La chaîne saute ce qui est fait."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.state not in (FAILED, CANCELLED, INTERRUPTED):
                return False
            job.state = QUEUED
            job.error = None
            job.finished_at = None
            self._save()
        self._wake.set()
        return True

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.state in FINISHED_STATES:
                return False
            job.state = CANCELLED
            job.finished_at = jobs_mod.now()
            process, current = self._process, self._current
            self._save()
        if current == job_id and process and process.poll() is None:
            process.terminate()
        return True

    def forget(self, job_id: str) -> bool:
        """Retirer une ligne de l'historique. Ne touche ni au cours publié
        ni aux artefacts : effacer le travail de quelqu'un depuis un bouton
        d'historique serait une surprise coûteuse."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.state not in FINISHED_STATES:
                return False
            del self._jobs[job_id]
            self._order.remove(job_id)
            self._forgotten.add(job_id)
            self._save()
        return True

    # ------------------------------------------------------------------- boucle
    def _next_queued(self) -> Job | None:
        with self._lock:
            for job_id in self._order:
                if self._jobs[job_id].state == QUEUED:
                    return self._jobs[job_id]
        return None

    def _loop(self) -> None:
        while True:
            job = self._next_queued()
            if job is None:
                self._wake.wait(timeout=5)
                self._wake.clear()
                continue
            self._run(job)

    def _run(self, job: Job) -> None:
        output_dir = self.output_dir(job)
        output_dir.mkdir(parents=True, exist_ok=True)
        command = jobs_mod.command_for(job, output_dir, sys.executable)

        with self._lock:
            job.state = RUNNING
            job.started_at = jobs_mod.now()
            self._current = job.id
            self._save()

        log = self.log_path(job)
        log.parent.mkdir(parents=True, exist_ok=True)
        try:
            with log.open("a", encoding="utf-8") as stream:
                stream.write(f"\n=== {jobs_mod.now()} — {' '.join(command)}\n")
                stream.flush()
                # Sous Windows, un processus Python dont la sortie est
                # redirigee vers un fichier ecrit dans l'encodage du systeme,
                # pas en UTF-8 : sans ces deux variables, le journal relu en
                # UTF-8 affiche « D?finitions » a la place des accents, et
                # n'avance que lorsqu'un tampon se vide.
                environment = os.environ | {"PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
                process = subprocess.Popen(
                    command, cwd=PROJECT_ROOT, stdout=stream, stderr=subprocess.STDOUT,
                    text=True, env=environment,
                )
                with self._lock:
                    self._process = process
                code = process.wait()
        except OSError as exc:
            code, message = -1, str(exc)
        else:
            message = f"La chaîne s'est arrêtée avec le code {code}."

        with self._lock:
            self._process = None
            self._current = None
            if job.state == CANCELLED:
                pass
            elif code == 0:
                job.state = DONE
            else:
                job.state = FAILED
                job.error = message
            job.finished_at = jobs_mod.now()
            self._save()
