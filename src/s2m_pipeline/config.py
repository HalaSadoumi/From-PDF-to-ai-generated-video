"""Configuration centrale, lue depuis les variables d'environnement.

Voir `.env.example` pour ce qui doit etre renseigne. Tout ce qui n'est pas un
secret porte ici une valeur par defaut utilisable telle quelle : la chaine
tourne avec une seule cle d'API et rien d'autre.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None

    # Deux modeles, deux usages. L'allege traite les taches mecaniques
    # — decoupage en scenes, plan visuel, quiz — et dispose d'un quota gratuit
    # genereux.
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    # Le modele complet est reserve a la redaction de la narration. L'allege
    # perd regulierement les accents et ecrit une prose plate ; la redaction ne
    # coute qu'un appel par chapitre, ce qui tient dans son quota plus etroit.
    gemini_model_writing: str = os.getenv("GEMINI_MODEL_WRITING", "gemini-3.6-flash")

    # Voix de synthese. `edge-tts --list-voices` en montre d'autres.
    tts_voice: str = os.getenv("TTS_VOICE", "fr-FR-DeniseNeural")

    # Taille d'un chapitre, exprimee en mots du support plutot qu'en nombre de
    # chapitres : un document deux fois plus long donne deux fois plus de
    # chapitres, et rien n'est regle pour un document en particulier.
    pdf_chapter_target_words: int = 190
    pdf_chapter_min_words: int = 70

    # Plafond d'un chapitre fini, verifie une fois la voix synthetisee et sa
    # duree reelle connue — pas estimee avant.
    chapter_max_seconds: float = 300.0  # 5 minutes


settings = Settings()
