"""Une seconde piste de sous-titres, dans une autre langue.

Le minutage n'est jamais recalcule. Les reperes de la piste francaise viennent
des positions que le moteur de synthese renvoie pendant qu'il parle : ils sont
cales sur la voix reelle, a la milliseconde. La traduction reprend donc les
memes bornes et ne remplace que le texte — c'est pourquoi une langue peut
etre ajoutee a un cours deja produit sans toucher a une seule video.
"""

from __future__ import annotations

import re
from pathlib import Path

from s2m_pipeline.core import llm
from s2m_pipeline.core.chapter_subtitles import Cue, write_vtt

# Le suffixe de langue s'intercale avant l'extension : chapter_03.en.vtt tient
# a cote de chapter_03.vtt, et le lecteur les propose comme deux pistes.
LANGUES = {"en": "anglais"}

_BORNE = re.compile(
    r"(\d\d):(\d\d):(\d\d)[.,](\d\d\d)\s*-->\s*(\d\d):(\d\d):(\d\d)[.,](\d\d\d)"
)


def _secondes(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def read_vtt(path: Path) -> list[Cue]:
    """Relire une piste ecrite par write_vtt.

    Volontairement tolerant sur ce qui entoure les bornes : un numero de
    replique peut manquer, le texte peut tenir sur plusieurs lignes.
    """
    cues: list[Cue] = []
    debut = fin = None
    texte: list[str] = []

    def clore() -> None:
        if debut is not None and texte:
            cues.append(Cue(start=debut, end=fin, text=" ".join(texte).strip()))

    for ligne in path.read_text(encoding="utf-8").splitlines():
        borne = _BORNE.search(ligne)
        if borne:
            clore()
            texte = []
            debut = _secondes(*borne.groups()[:4])
            fin = _secondes(*borne.groups()[4:])
        elif not ligne.strip() or ligne.strip() == "WEBVTT" or ligne.strip().isdigit():
            continue
        elif debut is not None:
            texte.append(ligne.strip())
    clore()
    return cues


def chemin_traduit(vtt: Path, langue: str) -> Path:
    return vtt.with_suffix(f".{langue}.vtt")


def translate_track(vtt: Path, langue: str = "en") -> Path | None:
    """Ecrire la piste traduite a cote de l'originale, si elle manque.

    Rend le chemin ecrit, ou None si la piste existait deja — la traduction
    est reprise comme le reste de la chaine, pas refaite a chaque passage.
    """
    cible = chemin_traduit(vtt, langue)
    if cible.exists():
        return None

    cues = read_vtt(vtt)
    if not cues:
        return None

    traduites = llm.translate_lines([c.text for c in cues], langue=LANGUES[langue])
    write_vtt(
        # strict : sans lui, zip tronquerait en silence sur un compte
        # divergent et le chapitre perdrait ses dernieres repliques.
        [Cue(start=c.start, end=c.end, text=t) for c, t in zip(cues, traduites, strict=True)],
        cible,
    )
    return cible


def translate_directory(dossier: Path, langue: str = "en") -> tuple[int, int]:
    """Traduire toutes les pistes d'un cours. Rend (traduites, deja presentes)."""
    pistes = sorted(p for p in dossier.glob("*.vtt") if not p.stem.endswith(f".{langue}"))
    ecrites = 0
    for piste in pistes:
        if translate_track(piste, langue) is not None:
            ecrites += 1
    return ecrites, len(pistes) - ecrites
