# Du support PDF au cours vidéo

Transforme un support de formation au format PDF en cours e-learning : chapitres
courts, narration synthétisée, schémas animés, sous-titres calés sur la parole,
évaluation finale, et publication dans une plateforme de consultation.

Une seule commande, ou une page web où l'on dépose le document.

**S2M Casablanca** — stage de 4ᵉ année Intelligence Artificielle & Data Science,
EMSI Casablanca.

---

## Ce que ça produit

Mesuré sur le support de sensibilisation sécurité, 28 pages :

| | |
|---|---|
| Chapitres | 8, de 1,4 à 3,2 minutes |
| Durée totale | 17 minutes |
| Narration | 1 405 mots de source → 2 625 mots — le système explique, il ne recopie pas |
| Scènes animées | 68, 17 formes de schéma distinctes |
| Sous-titres | 110, calés sur la parole réelle |
| Évaluation | 8 questions, reprises du quiz officiel des formateurs |

---

## Démarrer

### Prérequis

- **Python 3.11** ou plus récent
- **Node.js 20** ou plus récent — le moteur de rendu vidéo
- **FFmpeg** sur le `PATH` — [builds Windows](https://www.gyan.dev/ffmpeg/builds/)
- Une **clé d'API Google Gemini**, gratuite sur [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

Aucune carte graphique n'est nécessaire.

### Installation

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pip install -e .

cd remotion
npm install
cd ..

copy .env.example .env
```

Renseignez `GEMINI_API_KEY` dans `.env`, puis activez l'environnement à chaque
session :

```bash
.venv\Scripts\Activate.ps1
```

> La ligne `pip install -e .` est **indispensable** : le code vit dans `src/`, et
> sans elle toutes les commandes échouent avec `ModuleNotFoundError`. Le mode
> édition signifie que vos modifications sont prises en compte immédiatement,
> sans réinstaller.

### Vérifier que tout est en place

```bash
pytest
```

Trente et un tests, sans réseau ni clé d'API. Ils passent en quelques secondes.

---

## Produire un cours

### Depuis le navigateur

```bash
course-studio
```

- Catalogue : <http://127.0.0.1:8123/>
- Studio : <http://127.0.0.1:8123/studio.html>

Déposez le support PDF, un titre, et éventuellement le quiz officiel au format
Word. La chaîne s'exécute et publie le cours au catalogue à la fin. La page peut
être fermée : la production continue.

### Depuis le terminal

```bash
course-from-pdf --pdf "docs/exemple/support.pdf" ^
                --course-id securite_si ^
                --title "Securite SI : une priorite pour chacun" ^
                --quiz-docx "docs/exemple/quiz.docx"
```

Un exemple complet — support et quiz — est fourni dans `docs/exemple/`.

### Ce qu'il faut savoir avant de lancer

- **Environ 1 h 30 par cours** sur un poste sans carte graphique. Le rendu vidéo
  en représente l'essentiel.
- **Une production à la fois.** Deux rendus simultanés se disputent le
  processeur sans aller plus vite.
- **Le quota de rédaction est affiché** en haut du studio. Un chapitre coûte une
  requête au modèle de rédaction, plafonné à vingt par jour en offre gratuite.
  Au-delà, la chaîne bascule sur le modèle allégé, qui écrit une prose plus plate
  et perd parfois les accents.
- **Reprendre plutôt que recommencer.** Une production arrêtée — annulée, échouée
  ou coupée par un redémarrage — se reprend à l'étape où elle s'est arrêtée.
- **Le support doit avoir une couche de texte.** Un document scanné rend zéro
  mot et le découpage s'effondre.
- **Français uniquement** : les consignes de rédaction et la voix le sont.

---

## Comment ça marche

Neuf étages. Chacun écrit son résultat sur le disque et se saute si ce résultat
existe déjà — c'est ce qui rend une exécution reprenable.

| # | Étage | Ce qu'il produit |
|---|---|---|
| 1 | Lecture du support | une scène par page : texte, image, intervalle |
| 2 | Rédaction | titre, résumé, points clés et narration par chapitre |
| 3 | Découpage | des scènes d'une dizaine de secondes, une idée chacune |
| 4 | Synthèse vocale | l'audio, et le repère exact de chaque phrase prononcée |
| 5 | Sous-titres | une piste par chapitre |
| 6 | Plan visuel | un schéma, des libellés et une phrase à retenir par scène |
| 7 | Arrière-plans | une image d'ambiance par scène |
| 8 | Rendu | une vidéo par chapitre |
| 9 | Publication | vidéos, sous-titres, quiz et métadonnées dans la plateforme |

Deux décisions expliquent la forme du code.

**Le système ne sait rien du sujet traité.** Il ne connaît que des formes de
raisonnement — « des étapes qui se suivent », « un tout et ses parties », « deux
choses opposées » — parmi lesquelles le modèle choisit. C'est cette ignorance
délibérée qui lui permet de traiter n'importe quelle formation sans être
réécrit.

**Chaque étage communique par fichiers, jamais en mémoire.** Le coût est une
sérialisation systématique ; le bénéfice est que chaque décision du système est
lisible dans un fichier, qu'une exécution interrompue reprend, et que remplacer
un composant revient à écrire un module produisant le même fichier.

---

## Organisation du dépôt

```
src/s2m_pipeline/
    config.py           parametres, lus par tout le monde
    models.py           structures de donnees partagees

    core/               ce qui ne sait pas d'ou vient le contenu
        llm.py                  appels au modele, invites, schemas de sortie
        pdf : voir from_slides
        scene_visuals.py        archetype, points et phrase par scene
        scene_images.py         arriere-plans generes
        chapter_subtitles.py    ecriture des pistes de sous-titres
        render.py               mise en scene et rendu video
        quiz.py                 generation des questions
        quiz_reference.py       lecture d'un quiz officiel au format Word
        web_export.py           publication vers la plateforme
        audio.py                mesures et conversions

    from_slides/        ce qui est propre au support de formation
        pdf_source.py           lecture du document, decoupage en chapitres
        storyboard.py           decoupage de la narration en scenes
        narration.py, tts.py    synthese vocale
        build_course_from_pdf.py    orchestrateur des neuf etages

    studio/             la porte d'entree pour qui n'ouvre pas de terminal
        jobs.py                 ce qu'est une production, et son avancement
        runner.py               la file d'attente d'un poste
        server.py               le HTTP, et le site lui-meme

remotion/               le moteur de rendu : 24 schemas animes
web/                    la plateforme de consultation et le studio
tests/                  31 tests, sans reseau ni cle d'API
docs/                   documentation technique et un support d'exemple
```

Les imports internes sont **absolus** — `from s2m_pipeline.core import llm` —
plutôt que relatifs : on voit d'où vient chaque chose sans compter les points.

---

## Modifier le système

**Ajouter un schéma animé.** Écrire le composant dans `remotion/src/scenes/`, en
faisant passer tout libellé par `WrappedText` ; l'inscrire au vocabulaire
`SCENE_ARCHETYPES` dans `core/llm.py` avec une définition d'une ligne, sans
référence à un domaine ; ajouter un cas dans `SceneRenderer`. Si le nouveau
schéma peut se substituer à un existant, l'ajouter au groupe correspondant de
`_INTERCHANGEABLE` dans `core/scene_visuals.py` pour que la diversification
puisse l'utiliser.

**Changer le rythme ou la taille des chapitres.** Tout est dans `config.py` :
`pdf_chapter_target_words` fixe la taille visée, `chapter_max_seconds` le
plafond vérifié après synthèse de la voix.

**Ajouter une source** — un document Word, une page web. Écrire un module de
lecture qui produit une liste d'objets `Scene`, et un orchestrateur qui enchaîne
les étages en réutilisant ceux de `core/`. Tout le reste fonctionne sans
modification : c'est ainsi que cette chaîne est née d'une chaîne qui partait
d'un enregistrement vidéo.

---

## Limites connues

- **Validé sur un seul support.** Les règles sont écrites pour être générales,
  mais n'ont été éprouvées que sur un document.
- **Pas de suivi nominatif.** Progression, notes et surlignages vivent dans le
  navigateur de chacun : rien ne remonte à un responsable de formation.
- **Le studio n'a pas d'authentification.** Prévu pour un poste ou un réseau
  interne, pas une adresse publique.
- **La synthèse vocale** utilise un point d'accès Microsoft qui n'est pas prévu
  pour un usage professionnel par un tiers. Convient à une démonstration ; une
  diffusion officielle demande une offre commerciale.
- **Le service d'arrière-plans** est gratuit et sans garantie de disponibilité.
  Ces images sont décoratives : leur absence dégrade proprement.
- **Pas d'empaquetage SCORM** : les cours n'entrent pas tels quels dans un LMS.

Le détail de chacune, et ce qu'il faudrait faire, figure dans
`docs/Documentation_technique.pdf`.
