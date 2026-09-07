"""Le serveur du studio : dépôt d'un support, avancement, et le site lui-même.

Il sert aussi les fichiers statiques de `web/`, pour que la plateforme et son
administration vivent à la même adresse. C'est ce qui fait que la publication
n'a rien à transporter : l'étage final de la chaîne écrit dans web/data/, et
le catalogue relit ce dossier au chargement suivant.
"""

from __future__ import annotations

import argparse
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from s2m_pipeline.core import llm
from s2m_pipeline.core import quiz_reference
from s2m_pipeline.studio import jobs as jobs_mod
from s2m_pipeline.studio.runner import PROJECT_ROOT, UPLOADS_DIR, Runner

WEB_DIR = PROJECT_ROOT / "web"
MAX_UPLOAD_BYTES = 80 * 1024 * 1024

app = FastAPI(title="Studio S2M", docs_url=None, redoc_url=None)
runner = Runner()


def _store_upload(upload: UploadFile, job_id: str, suffix: str) -> Path:
    target = UPLOADS_DIR / f"{job_id}{suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with target.open("wb") as out:
        while chunk := upload.file.read(1 << 20):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                out.close()
                target.unlink(missing_ok=True)
                raise HTTPException(413, "Fichier trop volumineux (80 Mo maximum).")
            out.write(chunk)
    return target


@app.post("/api/jobs")
async def create_job(
    pdf: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    track: str = Form("essentiel"),
    quiz: UploadFile | None = File(None),
) -> JSONResponse:
    title = title.strip()
    if not title:
        raise HTTPException(422, "Le titre est obligatoire.")
    if not (pdf.filename or "").lower().endswith(".pdf"):
        raise HTTPException(422, "Le support doit être un fichier PDF.")
    if track not in ("essentiel", "detaille"):
        raise HTTPException(422, "Parcours inconnu.")

    job_id = uuid.uuid4().hex[:12]
    pdf_path = _store_upload(pdf, job_id, ".pdf")
    quiz_path, quiz_questions = None, None
    if quiz is not None and quiz.filename:
        if not quiz.filename.lower().endswith(".docx"):
            pdf_path.unlink(missing_ok=True)
            raise HTTPException(422, "Le quiz officiel doit être un fichier Word (.docx).")
        quiz_path = _store_upload(quiz, job_id, ".docx")
        # Lire le quiz maintenant plutôt qu'au neuvième étage : un document au
        # mauvais format publierait un cours sans évaluation, et le défaut ne
        # se verrait qu'une heure et demie plus tard.
        try:
            quiz_questions = len(quiz_reference.parse_document(quiz_path))
        except Exception:
            quiz_questions = 0
        if not quiz_questions:
            pdf_path.unlink(missing_ok=True)
            quiz_path.unlink(missing_ok=True)
            raise HTTPException(
                422,
                "Aucune question n'a pu être lue dans ce quiz. Le document attend un "
                "paragraphe par question, ses options notées « A) », « B) »… et une "
                "ligne « Bonnes réponses : A, B ».",
            )

    job = jobs_mod.Job(
        id=job_id,
        course_id=jobs_mod.unique_course_id(title, runner.taken_course_ids()),
        title=title,
        description=description.strip() or (
            "Cours structuré à partir du support de formation : chapitres courts, "
            "narration, transcription annotable et évaluation finale."
        ),
        track=track,
        pdf_name=pdf.filename or "support.pdf",
        pdf_path=str(pdf_path),
        quiz_path=str(quiz_path) if quiz_path else None,
        quiz_questions=quiz_questions,
    )
    runner.submit(job)
    return JSONResponse(runner.get(job.id), status_code=201)


@app.get("/api/jobs")
async def list_jobs() -> dict:
    return {"jobs": runner.list(), "quota": llm.writing_quota_today()}


@app.get("/api/jobs/{job_id}")
async def read_job(job_id: str) -> dict:
    job = runner.get(job_id)
    if not job:
        raise HTTPException(404, "Production inconnue.")
    job["log"] = runner.tail(job_id)
    return job


@app.post("/api/jobs/{job_id}/retry")
async def retry_job(job_id: str) -> dict:
    if not runner.retry(job_id):
        raise HTTPException(409, "Cette production ne peut pas être relancée.")
    return runner.get(job_id)


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict:
    if not runner.cancel(job_id):
        raise HTTPException(409, "Cette production est déjà terminée.")
    return runner.get(job_id)


@app.delete("/api/jobs/{job_id}")
async def forget_job(job_id: str) -> dict:
    if not runner.forget(job_id):
        raise HTTPException(409, "Une production en cours ne peut pas être retirée.")
    return {"removed": job_id}


@app.get("/api/quota")
async def read_quota() -> dict:
    return llm.writing_quota_today()


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


# Monté en dernier : les routes de l'API ci-dessus gardent la priorité.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description="Espace de formation S2M et son studio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8123)
    args = parser.parse_args()

    print(f"Espace de formation : http://{args.host}:{args.port}/")
    print(f"Studio              : http://{args.host}:{args.port}/studio.html")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
