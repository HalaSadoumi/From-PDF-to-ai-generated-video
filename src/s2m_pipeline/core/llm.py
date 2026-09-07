"""Gemini-based content generation: chapter titling (Sprint 2), and later
script/storyboard generation (Sprint 3).

Multimodal by design (cahier des charges section 5.2, "point critique du
projet"): the model is given the transcript text, the OCR'd slide text, AND
the actual frame image(s) together, so it can reason about what's shown on
screen even when that information never appears in speech or OCR (e.g. a
diagram's layout, a highlighted region, a demo).
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from PIL import Image
from pydantic import BaseModel
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from s2m_pipeline.config import settings


def _is_transient(exc: BaseException) -> bool:
    """Retry on rate limits / server-side overload, not on bad requests."""
    return isinstance(exc, genai_errors.APIError) and exc.code in (429, 500, 503, 504)


@retry(
    retry=retry_if_exception(_is_transient),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
)
def _generate_content(client: genai.Client, **kwargs):
    """Single entry point for every call to the model.

    A temperature of zero is forced here rather than at each call site, so a
    new call cannot forget it. Without it the model samples, and re-running the
    pipeline on the same recording produces a different cut: the keep/cut pass
    re-run on the validation video dropped 23 further seconds of filler and
    changed the chapter from 6:49 to 6:26. Nothing was wrong with either
    result, but a system meant to be re-run must give the same answer twice.

    This makes the pipeline as reproducible as the API allows — providers do
    not guarantee bit-identical output even at temperature zero, but the
    variation drops from "a different edit" to "a word here and there".
    """
    config = kwargs.get("config")
    if config is not None and getattr(config, "temperature", None) is None:
        config.temperature = 0.0
    return client.models.generate_content(**kwargs)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not set. Add it to .env (see .env.example).")
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


class ChapterContent(BaseModel):
    title: str
    summary: str
    key_points: list[str]


class SlideChapterContent(BaseModel):
    """A course chapter written from slides: its metadata and its narration."""

    title: str
    summary: str
    key_points: list[str]
    narration: str


class ScriptOutput(BaseModel):
    script: str


VISUAL_TYPES = [
    "title_card",
    "bullet_list",
    "icon_row",
    "process_flow",
    "comparison",
    "stat_highlight",
    "quote",
    "timeline",
]


class StoryboardSceneLLM(BaseModel):
    narration: str
    visual_type: str
    visual_description: str
    on_screen_text: str
    transition: str


class StoryboardLLMOutput(BaseModel):
    scenes: list[StoryboardSceneLLM]


_CHAPTER_PROMPT = """Tu es un ingenieur pedagogique qui prepare un cours e-learning \
a partir d'un enregistrement de formation interne d'entreprise.

Voici un extrait : la transcription de ce que dit l'intervenant, le texte OCR \
extrait des diapositives ou de l'ecran partage a ce moment, et une ou plusieurs \
captures d'ecran representatives.

Analyse ensemble ce que l'intervenant DIT et ce qui est MONTRE a l'ecran : une \
diapositive peut contenir des informations (schemas, listes, titres) absentes de \
la transcription, et inversement. Les deux se completent.

Produis pour ce segment :
- un titre de chapitre court et precis (5-8 mots)
- un resume fidele de 2-3 phrases
- 3 a 5 points cles a retenir

Reponds en francais, avec un contenu strictement fidele a la source (pas d'invention).
Utilise systematiquement les accents et diacritiques francais corrects (é, è, à, ç, etc.) :
"securite" est une faute, la forme correcte est "sécurité".

--- TRANSCRIPTION ---
{transcript}

--- TEXTE OCR DES DIAPOSITIVES / ECRAN ---
{ocr_text}
"""


def generate_chapter_content(
    transcript: str, ocr_text: str, frame_paths: list[Path]
) -> ChapterContent:
    client = _get_client()
    prompt = _CHAPTER_PROMPT.format(
        transcript=transcript or "(aucune parole detectee)",
        ocr_text=ocr_text or "(aucun texte detecte a l'ecran)",
    )

    contents: list = [prompt]
    for frame_path in frame_paths:
        contents.append(Image.open(frame_path))

    response = _generate_content(
        client,
        model=settings.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ChapterContent,
        ),
    )
    return ChapterContent.model_validate_json(response.text)


_SCRIPT_PROMPT = """Tu es un redacteur pedagogique qui transforme la transcription brute \
d'un chapitre de formation en un script de narration pour un cours e-learning.

Le script doit :
- preserver fidelement le sens et les faits de la transcription originale (aucune invention)
- supprimer les elements conversationnels superflus (hesitations, repetitions, "euh", \
"donc voila", apartes hors-sujet, interruptions techniques)
- ameliorer la clarte et la fluidite : une vraie narration de cours, pas une copie du transcript
- conserver la terminologie technique exacte
- relier les idees de maniere naturelle, comme un texte continu destine a etre lu a voix haute
- NE PAS resumer agressivement : l'objectif est de transformer, pas de condenser. Le script \
doit couvrir tous les points substantiels de la transcription (voir le principe fondamental \
du projet : ce n'est pas un resume video).

Utilise systematiquement les accents et diacritiques francais corrects (é, è, à, ç, etc.).
Reponds uniquement avec le script final, en francais, sans titre ni note.

--- TRANSCRIPTION BRUTE DU CHAPITRE ---
{transcript}

--- TEXTE OCR DES DIAPOSITIVES / ECRAN (contexte additionnel) ---
{ocr_text}
"""


def generate_script(transcript: str, ocr_text: str) -> str:
    client = _get_client()
    prompt = _SCRIPT_PROMPT.format(
        transcript=transcript or "(aucune parole detectee)",
        ocr_text=ocr_text or "(aucun texte detecte a l'ecran)",
    )
    response = _generate_content(
        client,
        model=settings.gemini_model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ScriptOutput,
        ),
    )
    return ScriptOutput.model_validate_json(response.text).script


_STORYBOARD_PROMPT = """Tu es un realisateur de motion design qui transforme un script de \
narration en storyboard pour une video de cours e-learning : motion graphics (texte anime, \
icones, diagrammes), PAS de diapositives brutes ni de capture de reunion (cahier des \
charges, section 6.1).

Decoupe le script ci-dessous en une sequence de scenes visuelles courtes (environ 10 a 25 \
secondes de narration chacune, decoupees a des frontieres de phrases naturelles). Pour \
chaque scene, fournis :
- "narration" : l'extrait EXACT et complet du script correspondant a cette scene. Mises bout \
a bout dans l'ordre, les narrations de toutes les scenes doivent reconstituer exactement le \
script original, sans rien omettre ni modifier.
- "visual_type" : un type choisi EXACTEMENT parmi cette liste : {visual_types}
- "visual_description" : description concrete de l'animation (ce qui apparait, bouge, \
s'enchaine a l'ecran)
- "on_screen_text" : texte court affiche a l'ecran (mots-cles, chiffres, titre) ; chaine vide \
si non pertinent
- "transition" : "fade", "cut", ou "slide"

Chaque visuel doit avoir une fonction explicative claire, jamais purement decorative.
Utilise systematiquement les accents et diacritiques francais corrects (é, è, à, ç, etc.).
Reponds en francais.

--- SCRIPT ---
{script}

--- TEXTE OCR DES DIAPOSITIVES / ECRAN (contexte additionnel, pour t'inspirer des schemas / \
donnees presentes) ---
{ocr_text}
"""


def generate_storyboard_scenes(script: str, ocr_text: str) -> list[StoryboardSceneLLM]:
    client = _get_client()
    prompt = _STORYBOARD_PROMPT.format(
        script=script,
        ocr_text=ocr_text or "(aucun texte detecte a l'ecran)",
        visual_types=", ".join(VISUAL_TYPES),
    )
    response = _generate_content(
        client,
        model=settings.gemini_model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=StoryboardLLMOutput,
        ),
    )
    return StoryboardLLMOutput.model_validate_json(response.text).scenes


class SegmentDecision(BaseModel):
    index: int
    decision: str  # "garder" | "couper"


class SegmentClassification(BaseModel):
    decisions: list[SegmentDecision]


_CLASSIFY_PROMPT = """Tu es un monteur audio qui prepare la narration originale (voix reelle \
de l'intervenant, pas de synthese vocale) d'un cours e-learning a partir d'un enregistrement \
de formation.

Pour CHAQUE segment de transcription numerote ci-dessous, decide s'il faut :
- "garder" : contenu a preserver (explications, definitions, exemples, procedures, faits \
techniques, demonstrations, conclusions) ou contenu a traiter avec discernement mais qui \
apporte une valeur reelle (questions pertinentes, echanges utiles) ;
- "couper" : contenu a nettoyer (hesitations, "euh", repetitions accidentelles, silences, \
apartes hors-sujet, interruptions techniques, redondances pures d'un meme point deja fait).

L'objectif n'est PAS une compression agressive : dans le doute, garde le segment. Le resultat \
sera assemble tel quel (audio reel decoupe et recolle), donc chaque segment "garde" doit rester \
comprehensible seul, sans dependre d'un segment coupe juste avant.

Reponds pour CHAQUE segment ci-dessous, avec le meme index, sans en omettre aucun.

--- SEGMENTS ---
{segments_text}
"""


def classify_segments(indexed_texts: list[tuple[int, str]]) -> dict[int, str]:
    """Returns {segment_index: "garder" | "couper"}."""
    client = _get_client()
    segments_text = "\n".join(f"[{i}] {text}" for i, text in indexed_texts)
    prompt = _CLASSIFY_PROMPT.format(segments_text=segments_text)

    response = _generate_content(
        client,
        model=settings.gemini_model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SegmentClassification,
        ),
    )
    parsed = SegmentClassification.model_validate_json(response.text)
    return {d.index: d.decision for d in parsed.decisions}


class VisualPlanLLM(BaseModel):
    index: int
    visual_type: str
    visual_description: str
    on_screen_text: str
    transition: str


class VisualPlanOutput(BaseModel):
    plans: list[VisualPlanLLM]


_VISUAL_PLAN_PROMPT = """Tu es un realisateur de motion design qui habille visuellement la \
narration originale (voix reelle de l'intervenant, deja decoupee en scenes) d'un cours \
e-learning : motion graphics (texte anime, icones, diagrammes), PAS de diapositives brutes ni \
de capture de reunion (cahier des charges, section 6.1).

Pour CHAQUE scene de narration numerotee ci-dessous, propose le visuel qui l'accompagne. \
Reponds pour CHAQUE scene, avec le meme index, sans en omettre aucune :
- "index" : le meme numero que le segment d'entree correspondant
- "visual_type" : un type choisi EXACTEMENT parmi cette liste : {visual_types}
- "visual_description" : description concrete de l'animation (ce qui apparait, bouge, \
s'enchaine a l'ecran)
- "on_screen_text" : texte court affiche a l'ecran (mots-cles, chiffres, titre) ; chaine vide \
si non pertinent
- "transition" : "fade", "cut", ou "slide"

Chaque visuel doit avoir une fonction explicative claire, jamais purement decorative.
Utilise systematiquement les accents et diacritiques francais corrects (é, è, à, ç, etc.).
Reponds en francais.

--- SCENES DE NARRATION (texte reel, deja fixe - ne le modifie pas) ---
{scenes_text}

--- TEXTE OCR DES DIAPOSITIVES / ECRAN (contexte additionnel) ---
{ocr_text}
"""


def generate_visual_plan(
    indexed_narrations: list[tuple[int, str]], ocr_text: str
) -> dict[int, VisualPlanLLM]:
    client = _get_client()
    scenes_text = "\n".join(f"[{i}] {text}" for i, text in indexed_narrations)
    prompt = _VISUAL_PLAN_PROMPT.format(
        scenes_text=scenes_text,
        ocr_text=ocr_text or "(aucun texte detecte a l'ecran)",
        visual_types=", ".join(VISUAL_TYPES),
    )
    response = _generate_content(
        client,
        model=settings.gemini_model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VisualPlanOutput,
        ),
    )
    parsed = VisualPlanOutput.model_validate_json(response.text)
    by_index = {plan.index: plan for plan in parsed.plans}

    default_plan = VisualPlanLLM(
        index=-1, visual_type="bullet_list", visual_description="", on_screen_text="", transition="fade"
    )
    return {idx: by_index.get(idx, default_plan) for idx, _ in indexed_narrations}


# --- Animated explainer scenes (Sprint 3, visual generation) -----------------
#
# Controlled vocabulary of animated scene archetypes. Each maps 1:1 to a
# React/Remotion component that draws and animates itself; keeping the list
# closed (rather than free-form visual descriptions) is what makes the
# renderer generic - the LLM picks an archetype and fills its text slots,
# and no scene needs bespoke code.
SCENE_ARCHETYPES = {
    "pillars": "2 a 4 fondements/piliers nommes qui s'elevent (les composantes d'un concept)",
    "actor_action_target": "un acteur agit sur une cible, avec un effet (un envoi, une demande, une attaque, une sollicitation)",
    "data_flow": "des sources alimentent une etape centrale puis un resultat (collecte, traitement, validation)",
    "concentric_layers": "des couches/niveaux successifs autour d'un element central",
    "comparison": "deux situations opposees cote a cote (bon vs mauvais, avant/apres, deux options)",
    "checklist": "une liste de points/regles qui se cochent une a une",
    "stat_reveal": "un chiffre cle mis en avant avec son contexte (pourcentage, montant, duree)",
    "timeline": "des etapes qui se succedent dans le temps (processus, evolution, chronologie)",
    "state_change": "des elements qui passent d'un etat a un autre (verrouillage, validation, transformation)",
    "permission_matrix": "des roles/profils avec des droits ou acces differencies",
    "separated_groups": "des groupes ou zones cloisonnes, separes par une barriere",
    "cycle": "des etapes qui bouclent et recommencent (processus continu, amelioration, repetition)",
    "quadrant_matrix": "quatre cas / categories croisant deux dimensions",
    "do_dont": "plusieurs bonnes pratiques face a plusieurs erreurs a eviter",
    "hierarchy": "un ensemble et les elements qui le composent (categories, sous-parties)",
    "stat_row": "PLUSIEURS chiffres cites cote a cote (ex. 61%, 45%, 30%)",
    "quote_highlight": "une phrase forte ou une definition marquante, mise en exergue",
    "title_statement": "un message cle affiche sobrement, quand aucun autre schema ne convient",
    "bar_chart": "PLUSIEURS valeurs mesurees que l'on compare (barres). items au format \"84% Rancongiciel\"",
    "donut_share": "UNE proportion rapportee a un tout (ex. 32% des repondants). primary = le chiffre",
    "ranking_list": "un classement ordonne, le rang porte l'information (1er, 2e...). items au format \"18 000 detections au Maroc\"",
    "venn_overlap": "une notion contenue dans une autre, ou deux notions qui se recouvrent. items[0] = le grand ensemble, items[1] = celui qui est dedans",
    "funnel": "des etapes successives qui filtrent : chacune ne laisse passer qu'une partie de la precedente",
    "pyramid": "des niveaux empiles par ordre de priorite, la base porte le sommet. items[0] = la base",
}

# Domain-neutral icon vocabulary, validated against the installed
# lucide-react package. The LLM picks one per scene, so the visuals adapt to
# any subject matter instead of depending on a hardcoded keyword dictionary
# built for one domain.
SCENE_ICONS = [
    "User", "Users", "UserCheck", "UserX", "UserPlus", "UserMinus", "Handshake", "Baby",
    "GraduationCap", "Briefcase", "Crown", "Contact", "Mail", "MessageSquare", "MessageCircle", "Phone",
    "Megaphone", "Bell", "Send", "Share2", "Video", "Mic", "Languages", "FileText",
    "Files", "Folder", "FolderOpen", "ClipboardList", "ClipboardCheck", "BookOpen", "Newspaper", "Database",
    "Table", "Archive", "FileSignature", "Receipt", "Stamp", "Banknote", "Coins", "CreditCard",
    "PiggyBank", "TrendingUp", "TrendingDown", "ChartBar", "ChartPie", "ChartLine", "Calculator", "ShoppingCart",
    "Tag", "Landmark", "Building2", "Store", "Factory", "Clock", "Calendar", "CalendarDays",
    "Timer", "Hourglass", "History", "AlarmClock", "Laptop", "Smartphone", "Monitor", "Server",
    "Cloud", "Wifi", "Globe", "Code", "Terminal", "Cpu", "HardDrive", "Printer",
    "Plug", "Settings", "Wrench", "Cog", "Shield", "ShieldCheck", "ShieldAlert", "Lock",
    "Unlock", "Key", "KeyRound", "Fingerprint", "Eye", "EyeOff", "Bug", "Siren",
    "Flame", "Radar", "Check", "CheckCheck", "X", "Ban", "Plus", "Minus",
    "ArrowRight", "ArrowUp", "ArrowDown", "RefreshCw", "Play", "Pause", "Search", "Filter",
    "Download", "Upload", "Link", "Copy", "Trash2", "Pencil", "Save", "AlertCircle",
    "AlertTriangle", "AlertOctagon", "Info", "HelpCircle", "CircleQuestionMark", "Lightbulb", "Sparkles", "Star",
    "Award", "Trophy", "Target", "Flag", "MapPin", "Map", "Truck", "Package",
    "Plane", "Car", "Home", "Warehouse", "Route", "Navigation", "HeartPulse", "Stethoscope",
    "Activity", "Brain", "Hand", "Smile", "Frown", "ThumbsUp", "ThumbsDown", "Scale",
    "Gavel", "Leaf", "Droplet", "Zap", "Sun", "Recycle", "Layers", "GitBranch",
    "Workflow", "Network", "Puzzle", "Scissors", "Compass", "Bookmark", "Percent",
]


class SceneVisualPlan(BaseModel):
    index: int
    archetype: str
    label: str
    items: list[str]
    primary: str
    secondary: str
    # One full sentence stating what the viewer should retain from this scene.
    # Rendered on every archetype, so the screen explains the point being made
    # rather than only naming it. Defaulted so plans written before this field
    # existed still validate.
    takeaway: str = ""
    icon: str
    image_prompt: str


class SceneVisualPlanOutput(BaseModel):
    plans: list[SceneVisualPlan]


_SCENE_VISUAL_PROMPT = """Tu es un directeur artistique de video pedagogique. Pour chaque \
scene de narration ci-dessous (texte reel, deja fixe - ne le reecris jamais), choisis le \
schema anime qui ILLUSTRE ce qui est dit, et redige les textes affiches a l'ecran.

REGLE ABSOLUE : l'ecran doit EXPLIQUER le propos, pas seulement le nommer. Un apprenant \
qui regarde la scene SANS LE SON doit comprendre l'essentiel de ce qui est dit. Un ecran \
qui n'affiche qu'un titre est un echec : il faut y faire figurer les elements concrets \
enonces dans la narration (les termes, les etapes, les chiffres, les exemples, les \
conditions). Ne resume pas a l'extreme et n'invente rien : reprends ce qui est reellement \
dit, dans les mots de l'intervenant quand c'est possible.

Archetypes disponibles (choisis l'identifiant exact) :
{archetypes}

Pour chaque scene, reponds avec :
- "index" : le meme numero que la scene d'entree
- "archetype" : un identifiant EXACT de la liste ci-dessus
- "label" : titre de la scene (2 a 6 mots), affiche en haut
- "items" : TOUJOURS 2 a 4 elements, JAMAIS une liste vide, quel que soit l'archetype.
  Chacun fait 2 a 6 mots et doit porter du sens : "Verifier l'expediteur" et non
  "Expediteur", "Acces limite aux habilites" et non "Acces". Selon l'archetype :
  les fondements (pillars), les sources (data_flow), les couches (concentric_layers),
  les deux cotes (comparison), les points a cocher (checklist), les etapes (timeline),
  les roles et leurs droits (permission_matrix), les groupes (separated_groups), les
  etapes du cycle (cycle), les quatre cas (quadrant_matrix), les elements composants
  (hierarchy), les chiffres au format "61% messagerie" (stat_row), et pour do_dont :
  en alternance une bonne pratique puis une erreur, une bonne pratique puis une erreur.
  Pour les cinq archetypes suivants, les items developpent le propos central :
  * title_statement : 2 a 4 points qui detaillent ou justifient le message affiche
  * stat_reveal     : 2 a 4 elements de contexte du chiffre (source, perimetre, effet)
  * state_change    : 2 a 4 etapes ou consequences du passage d'un etat a l'autre
  * actor_action_target : 2 a 4 precisions sur le mecanisme (comment, par quel moyen,
    avec quel effet)
  * quote_highlight : 2 a 4 points qui explicitent la phrase mise en exergue
- "primary" : selon l'archetype - l'etape centrale (data_flow), le chiffre (stat_reveal,
  ex. "61%"), le message principal (title_statement), l'acteur qui agit
  (actor_action_target), l'etat final (state_change), l'element central
  (concentric_layers), sinon chaine vide
- "secondary" : selon l'archetype - le resultat final (data_flow), le libelle du chiffre
  (stat_reveal), la synthese (pillars), la cible qui subit l'action (actor_action_target),
  la precision sous le schema (state_change, permission_matrix, separated_groups),
  sinon chaine vide
- "takeaway" : TOUJOURS rempli. Une phrase complete de 8 a 16 mots enoncant ce que
  l'apprenant doit retenir de cette scene precise. C'est une explication, pas un titre :
  "Un mot de passe reutilise compromet tous les comptes qui l'emploient" et non
  "Mots de passe". Elle doit decouler de ce qui est dit dans CETTE scene.
- "icon" : une icone illustrant le concept principal de la scene, choisie EXACTEMENT dans
  cette liste : {icons}
- "image_prompt" : une description visuelle EN ANGLAIS, en 6 a 12 mots, de l'illustration
  d'ambiance a generer en fond de scene. Elle reste un simple decor discret derriere le
  schema : ne lui confie aucune information. Decris une situation ou un objet concret lie
  au propos (ex. "employee reviewing documents at office desk"). N'y mets JAMAIS de texte,
  de mot ecrit, de chiffre, de logo ni de marque.

Choisis l'archetype d'apres le SENS de la narration, pas au hasard, et varie les archetypes \
d'une scene a l'autre quand le contenu s'y prete. N'utilise "title_statement" qu'en dernier \
recours, quand aucun schema ne convient vraiment - et meme dans ce cas, remplis ses items.

Regles de choix a appliquer AVANT de retomber sur une liste a puces ou des blocs :
- la scene cite PLUSIEURS valeurs chiffrees que l'on compare -> "bar_chart"
- elle cite UNE proportion rapportee a un tout (x % des entreprises, des repondants,
  des attaques) -> "donut_share"
- elle etablit un classement ou un rang (premier, deuxieme, en tete de...) -> "ranking_list"
- elle presente une notion comme incluse dans une autre, ou deux notions qui se
  recouvrent -> "venn_overlap"
- elle decrit des etapes qui filtrent, chacune ne laissant passer qu'une partie de la
  precedente -> "funnel"
- elle presente des niveaux dont l'un porte les autres, des fondations -> "pyramid"
Quand une scene parle de grandeurs, un schema qui MONTRE la grandeur vaut toujours mieux
qu'une liste qui l'enonce.

Tous les textes affiches doivent etre en francais et utiliser les accents corrects \
(é, è, à, ç) - sauf "image_prompt" qui est en anglais. Reponds pour CHAQUE scene, sans en \
omettre aucune.

--- SCENES DE NARRATION ---
{scenes_text}

--- TEXTE OCR DES DIAPOSITIVES (contexte, pour reprendre les termes affiches a l'ecran) ---
{ocr_text}
"""


def _clip_on_word(text: str, limit: int = 90) -> str:
    """Cut at a word boundary. Slicing on a character count put sentences like
    "... contre tout acces au debut de l'" on screen, mid-word."""
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    cut = clean[:limit].rsplit(" ", 1)[0].rstrip(" ,;:'’-")
    return f"{cut}…"


def _request_scene_plans(
    indexed_narrations: list[tuple[int, str]], ocr_text: str
) -> dict[int, SceneVisualPlan]:
    client = _get_client()
    scenes_text = "\n".join(f"[{i}] {text}" for i, text in indexed_narrations)
    archetypes = "\n".join(f"- {k} : {v}" for k, v in SCENE_ARCHETYPES.items())
    prompt = _SCENE_VISUAL_PROMPT.format(
        scenes_text=scenes_text,
        ocr_text=ocr_text or "(aucun texte detecte a l'ecran)",
        archetypes=archetypes,
        icons=", ".join(SCENE_ICONS),
    )
    response = _generate_content(
        client,
        model=settings.gemini_model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SceneVisualPlanOutput,
        ),
    )
    parsed = SceneVisualPlanOutput.model_validate_json(response.text)
    return {p.index: p for p in parsed.plans}


def generate_scene_visual_plans(
    indexed_narrations: list[tuple[int, str]], ocr_text: str
) -> dict[int, SceneVisualPlan]:
    """Map each narration scene to an animated archetype + its text slots."""
    by_index = _request_scene_plans(indexed_narrations, ocr_text)

    def unusable(idx: int) -> bool:
        plan = by_index.get(idx)
        return plan is None or plan.archetype not in SCENE_ARCHETYPES

    # Asked for a whole chapter at once, the model occasionally omits a scene
    # or two. Those used to land straight on the bare fallback card, which is
    # visible in the finished video; ask again for just the missing ones.
    missing = [(i, t) for i, t in indexed_narrations if unusable(i)]
    if missing:
        for idx, plan in _request_scene_plans(missing, ocr_text).items():
            if plan.archetype in SCENE_ARCHETYPES:
                by_index[idx] = plan

    result: dict[int, SceneVisualPlan] = {}
    for idx, text in indexed_narrations:
        plan = by_index.get(idx)
        if plan is None or plan.archetype not in SCENE_ARCHETYPES:
            # Last resort after the retry: a quote card carrying the speaker's
            # own words, cut at a word boundary so it reads as a deliberate
            # pull-quote rather than a truncated sentence.
            plan = SceneVisualPlan(
                index=idx,
                archetype="quote_highlight",
                label="",
                items=[],
                primary=_clip_on_word(text),
                secondary="",
                takeaway="",
                icon="Info",
                image_prompt="abstract professional workspace atmosphere",
            )
        elif plan.icon not in SCENE_ICONS:
            # The model occasionally invents an icon name; snap it back to a
            # valid one so the renderer never has to guess.
            plan = plan.model_copy(update={"icon": "Info"})
        result[idx] = plan
    return result


# --- Comprehension quiz (post-MVP feature, cahier des charges section 14) ---


class QuizOption(BaseModel):
    letter: str
    text: str


class QuizQuestion(BaseModel):
    question: str
    options: list[QuizOption]
    correct_letters: list[str]
    explanation: str


class QuizOutput(BaseModel):
    questions: list[QuizQuestion]


_QUIZ_PROMPT = """Tu es un concepteur pedagogique. A partir du contenu d'un chapitre de \
formation ci-dessous, redige {count} questions de comprehension pour verifier que \
l'apprenant a retenu l'essentiel.

Regles :
- Les questions portent UNIQUEMENT sur ce qui est dit dans le contenu fourni. N'invente
  jamais un fait, un chiffre ou une regle qui n'y figure pas.
- Chaque question a 4 propositions, notees A, B, C, D.
- Certaines questions ont une seule bonne reponse, d'autres en ont plusieurs : varie.
  Indique toutes les bonnes lettres dans "correct_letters".
- Les mauvaises propositions doivent rester plausibles (pas d'absurdite evidente), sinon
  la question ne teste rien.
- "explanation" rappelle en une phrase pourquoi la ou les bonnes reponses le sont.
- Redige en francais, avec les accents corrects (é, è, à, ç).

--- TITRE DU CHAPITRE ---
{title}

--- RESUME ---
{summary}

--- POINTS CLES ---
{key_points}

--- CONTENU DETAILLE (transcription) ---
{transcript}
"""


def generate_quiz(
    title: str, summary: str, key_points: list[str], transcript: str, count: int = 3
) -> list[QuizQuestion]:
    """Write comprehension questions grounded in one chapter's actual content."""
    client = _get_client()
    prompt = _QUIZ_PROMPT.format(
        count=count,
        title=title,
        summary=summary,
        key_points="\n".join(f"- {k}" for k in key_points) or "(aucun)",
        transcript=transcript[:6000],
    )
    response = _generate_content(
        client,
        model=settings.gemini_model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=QuizOutput,
        ),
    )
    parsed = QuizOutput.model_validate_json(response.text)

    valid: list[QuizQuestion] = []
    for q in parsed.questions:
        letters = {o.letter.strip().upper() for o in q.options}
        correct = [c.strip().upper() for c in q.correct_letters]
        # Drop questions whose answer key doesn't match the options offered,
        # rather than shipping a quiz that cannot be scored correctly.
        if correct and all(c in letters for c in correct):
            valid.append(q)
    return valid


# --- Slide-deck front end: write a chapter's narration from its slides ---

_SLIDE_CHAPTER_PROMPT = """Tu es un ingenieur pedagogique. A partir des diapositives \
d'un chapitre ci-dessous, redige la NARRATION de ce chapitre de cours e-learning : le \
texte qui sera lu a voix haute par-dessus les animations.

Le critere n'est pas la longueur, c'est la DENSITE. Un chapitre doit rester court ET \
contenir tout ce que l'apprenant doit savoir sur ce point : a la fin, il ne doit avoir \
aucune raison d'ouvrir les diapositives pour completer ce qu'il vient d'entendre.

Ce qui se coupe : les tournures de remplissage, les redites, les phrases de liaison qui \
n'apportent rien, les adjectifs decoratifs.
Ce qui ne se coupe JAMAIS : les donnees. Chaque pourcentage, montant, date, duree, \
classement et source nommee presents sur les diapositives — y compris ceux qui ne sont que \
dans un graphique, un tableau ou un encadre de l'image — doit figurer dans la narration. \
Un chiffre coute trois mots : il n'y a aucune raison de le sacrifier. Ecrire "les fuites \
de donnees et la compromission des messageries" alors que le support indique 61 % et 45 % \
fait perdre l'essentiel de l'information.

Longueur indicative : {words_min} a {words_max} mots ({minutes} minutes). Depasse-la \
plutot que d'omettre une donnee, mais n'ecris jamais un mot qui n'apprend rien.

Regles de fond :
- Tu DEVELOPPES les diapositives, tu ne les recopies pas. Une diapositive donne des
  mots-cles ; la narration en fait un enseignement : chaque terme est defini, chaque
  mecanisme est explique, chaque chiffre est commente. Un apprenant qui ecoute sans voir
  le support doit comprendre.
- La distinction a tenir : n'invente aucun FAIT, CHIFFRE, DATE, NOM ni NORME absent des
  diapositives. En revanche expliquer, reformuler, illustrer et relier les idees entre
  elles est exactement ce qu'on te demande — c'est cela, enseigner.
- Si tu es nettement en dessous de {words_min} mots, c'est que tu t'es contente de lire :
  reprends et explique davantage.
- Avant de repondre, relis chaque diapositive et son image, et verifie qu'aucun chiffre,
  aucune date et aucune source nommee n'a ete laisse de cote.
- Droit au but. Pas de formule d'introduction, pas de "dans ce chapitre nous allons voir",
  pas de conclusion qui resume ce qui vient d'etre dit. Chaque phrase apporte quelque
  chose.
- Ne parle jamais du support : ni "cette diapositive", ni "comme vous le voyez", ni "la
  presentation". L'apprenant suit un cours, pas un diaporama.
- Enchaine naturellement d'une idee a la suivante.

Regles de forme, parce que ce texte sera lu par une voix de synthese :
- Phrases courtes, une idee par phrase. Evite les incises et les parentheses.
- Ecris les nombres comme ils se prononcent quand c'est plus naturel a l'oral
  (ecris "quatre-vingt-quatre pour cent" plutot que "84%").
- Developpe les sigles a leur premiere apparition.
- Francais correct avec TOUS les accents et diacritiques (é, è, ê, à, ù, ç). Ecrire
  "securite", "cybersecurite" ou "couts" est une faute : la forme correcte est
  "sécurité", "cybersécurité", "coûts". Cela vaut aussi pour le titre.

Reponds avec :
- "title" : titre du chapitre, 3 a 8 mots, sans numero
- "summary" : deux phrases resumant ce que l'apprenant retiendra
- "key_points" : 3 a 5 points cles, une ligne chacun
- "narration" : le texte a lire, en un seul bloc de prose

--- TEXTE DES DIAPOSITIVES DU CHAPITRE ---
{slides_text}
"""


# --------------------------------------------------------------------- quota
# Le modele de redaction est plafonne a 20 requetes par jour en offre gratuite.
# Rien ne permet d'interroger ce compteur chez le fournisseur, donc on tient le
# notre : sans lui, l'interface ne peut pas prevenir qu'un support trop long
# finira redige par le modele de repli, et le defaut ne se voit qu'au montage.
WRITING_DAILY_QUOTA = 20
_QUOTA_FILE = Path(__file__).resolve().parents[3] / "work" / "writing_quota.json"


def _record_writing_call(fell_back: bool) -> None:
    today = datetime.date.today().isoformat()
    try:
        data = json.loads(_QUOTA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if data.get("day") != today:
        data = {"day": today, "calls": 0, "fallbacks": 0}
    data["calls"] += 1
    if fell_back:
        data["fallbacks"] += 1
    try:
        _QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
        _QUOTA_FILE.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        # Un compteur d'affichage ne doit jamais faire echouer une production.
        pass


def writing_quota_today() -> dict:
    """Ce qui a ete consomme aujourd'hui, pour affichage."""
    today = datetime.date.today().isoformat()
    try:
        data = json.loads(_QUOTA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if data.get("day") != today:
        data = {"day": today, "calls": 0, "fallbacks": 0}
    used = min(data["calls"], WRITING_DAILY_QUOTA)
    return {
        "limit": WRITING_DAILY_QUOTA,
        "used": used,
        "remaining": max(0, WRITING_DAILY_QUOTA - used),
        "fallbacks": data["fallbacks"],
    }


def generate_slide_chapter(
    slides_text: str,
    page_images: list[Path],
    words_min: int = 280,
    words_max: int = 400,
) -> SlideChapterContent:
    """Write one course chapter from its slides.

    The page renders are sent alongside the extracted text: a slide's meaning
    often sits in a diagram or a chart that the text layer does not carry, and
    the model has to see it to narrate it. This is the same multimodal reading
    the video pipeline applies to frames.
    """
    client = _get_client()
    minutes = f"{words_min / 150:.1f} a {words_max / 150:.1f}"
    prompt = _SLIDE_CHAPTER_PROMPT.format(
        slides_text=slides_text or "(diapositive sans texte)",
        words_min=words_min,
        words_max=words_max,
        minutes=minutes,
    )

    contents: list = [prompt]
    for image_path in page_images:
        contents.append(Image.open(image_path))

    def call(model: str):
        return _generate_content(
            client,
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SlideChapterContent,
            ),
        )

    try:
        response = call(settings.gemini_model_writing)
        _record_writing_call(fell_back=False)
    except genai_errors.APIError as exc:
        # The writing model's free tier is capped at 20 requests a day, which a
        # long deck plus a re-run exhausts. Falling back keeps the run going;
        # the lighter model writes flatter French and sometimes drops accents,
        # so the chapter is flagged rather than silently accepted.
        if exc.code != 429:
            raise
        print(
            f"    quota du modele de redaction epuise, repli sur {settings.gemini_model}",
            flush=True,
        )
        response = call(settings.gemini_model)
        _record_writing_call(fell_back=True)

    return SlideChapterContent.model_validate_json(response.text)
