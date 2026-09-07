/* Lecteur de cours S2M.
 *
 * Trois choses le distinguent d'un simple lecteur vidéo :
 *  - la transcription du chapitre est affichée sous la vidéo et synchronisée
 *    avec elle ; cliquer une ligne déplace la lecture ;
 *  - l'apprenant peut surligner un passage et y attacher une note, conservés
 *    dans le navigateur ;
 *  - l'évaluation porte sur l'ensemble du cours et n'est proposée qu'à la fin,
 *    pas sous chaque chapitre.
 *
 * Aucune base de données : progression, surlignages et notes vivent dans le
 * localStorage du navigateur, propres à chaque poste. */

const params = new URLSearchParams(location.search);
const COURSE_ID = params.get("course");
const BASE = `data/${COURSE_ID}`;
const KEY_PROGRESS = `s2m-course-progress:${COURSE_ID}`;
const KEY_NOTES = `s2m-course-notes:${COURSE_ID}`;

const el = (id) => document.getElementById(id);
const video = el("player");

let chapters = [];
let quiz = {};
let current = 0;
let progress = { completed: [] };
let annotations = {}; // { "chapter_00": { "12": {marked:true, note:"..."} } }
let cues = []; // transcription du chapitre courant
let followPlayback = true;

/* ----------------------------------------------------------- utilitaires */
function formatDuration(seconds) {
  const total = Math.round(seconds || 0);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m} min ${String(s).padStart(2, "0")}`;
}

function formatClock(seconds) {
  const total = Math.floor(seconds || 0);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function readStore(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeStore(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* navigation privée ou stockage plein : la lecture reste possible */
  }
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]),
  );
}

/* ------------------------------------------------------------ WebVTT */
/** Analyse une piste WebVTT en repères { start, end, text }.
 *  La piste est produite par le pipeline à partir de la parole réelle, donc
 *  elle sert à la fois de sous-titres et de transcription navigable. */
function parseVtt(text) {
  const result = [];
  const blocks = text.replace(/\r/g, "").split("\n\n");
  for (const block of blocks) {
    const lines = block.split("\n").filter(Boolean);
    const timing = lines.find((l) => l.includes("-->"));
    if (!timing) continue;
    const [from, to] = timing.split("-->").map((t) => t.trim().split(" ")[0]);
    const body = lines.slice(lines.indexOf(timing) + 1).join(" ").trim();
    if (!body) continue;
    result.push({ start: toSeconds(from), end: toSeconds(to), text: body });
  }
  return result;
}

function toSeconds(stamp) {
  const parts = stamp.split(":").map(parseFloat);
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return parts[0] || 0;
}

/* --------------------------------------------------------- progression */
function chapterDone(id) {
  return progress.completed.includes(id);
}

function markDone(id) {
  if (!chapterDone(id)) {
    progress.completed.push(id);
    writeStore(KEY_PROGRESS, progress);
    renderChapterList();
    renderProgress();
    refreshExamAvailability();
  }
}

function renderProgress() {
  const pct = chapters.length
    ? Math.round((progress.completed.length / chapters.length) * 100)
    : 0;
  el("progress-fill").style.width = `${pct}%`;
  el("progress-label").textContent = `${pct} %`;
}

/* ------------------------------------------------------------ sommaire */
function renderChapterList() {
  const list = el("chapter-list");
  list.innerHTML = "";
  chapters.forEach((chapter, index) => {
    const item = document.createElement("li");
    item.className =
      "chapter-item" +
      (index === current ? " active" : "") +
      (chapterDone(chapter.id) ? " done" : "");
    item.innerHTML = `
      <span class="chapter-num">${chapterDone(chapter.id) ? "✓" : index + 1}</span>
      <span class="chapter-text">
        <span class="t">${escapeHtml(chapter.title)}</span>
        <span class="d">${formatDuration(chapter.duration)}</span>
      </span>`;
    item.addEventListener("click", () => selectChapter(index));
    list.appendChild(item);
  });
}

/* -------------------------------------------------------- transcription */
function annotationsFor(chapterId) {
  if (!annotations[chapterId]) annotations[chapterId] = {};
  return annotations[chapterId];
}

function renderTranscript() {
  const host = el("transcript");
  host.innerHTML = "";

  if (!cues.length) {
    host.innerHTML =
      `<p class="muted" style="padding:14px">Transcription indisponible pour ce chapitre.</p>`;
    return;
  }

  const marks = annotationsFor(chapters[current].id);
  cues.forEach((cue, index) => {
    const state = marks[index] || {};
    const row = document.createElement("div");
    row.className =
      "cue" + (state.marked ? " marked" : "") + (state.note ? " has-note" : "");
    row.dataset.index = index;
    row.innerHTML = `
      <span class="time">${formatClock(cue.start)}</span>
      <span class="txt">${escapeHtml(cue.text)}</span>
      <button class="btn ghost small note-btn" title="Ajouter ou modifier une note">✎</button>`;

    row.addEventListener("click", (event) => {
      if (event.target.closest(".note-btn")) return;
      video.currentTime = cue.start + 0.05;
      video.play().catch(() => {});
    });
    row.addEventListener("dblclick", (event) => {
      event.preventDefault();
      toggleMark(index);
    });
    row.querySelector(".note-btn").addEventListener("click", (event) => {
      event.stopPropagation();
      editNote(index);
    });

    host.appendChild(row);

    if (state.note) {
      const note = document.createElement("div");
      note.className = "cue-note";
      note.innerHTML = `<span class="lbl">Note</span><br />${escapeHtml(state.note)}`;
      host.appendChild(note);
    }
  });
}

function toggleMark(index) {
  const marks = annotationsFor(chapters[current].id);
  const state = marks[index] || {};
  state.marked = !state.marked;
  if (!state.marked && !state.note) delete marks[index];
  else marks[index] = state;
  writeStore(KEY_NOTES, annotations);
  renderTranscript();
  renderNotes();
}

function editNote(index) {
  const marks = annotationsFor(chapters[current].id);
  const state = marks[index] || {};
  const value = window.prompt(
    `Note sur : « ${cues[index].text.slice(0, 90)} »`,
    state.note || "",
  );
  if (value === null) return;
  const text = value.trim();
  if (text) {
    state.note = text;
    marks[index] = state;
  } else {
    delete state.note;
    if (!state.marked) delete marks[index];
  }
  writeStore(KEY_NOTES, annotations);
  renderTranscript();
  renderNotes();
}

/** Surligne le passage en cours de lecture, sans avoir à viser la ligne. */
function markCurrentCue() {
  if (!cues.length) return;
  const time = video.currentTime;
  const index = cues.findIndex((c) => time >= c.start && time < c.end);
  if (index >= 0) {
    toggleMark(index);
    document.querySelector(`.cue[data-index="${index}"]`)?.scrollIntoView({
      block: "center",
      behavior: "smooth",
    });
  }
}

function syncTranscript() {
  if (!cues.length) return;
  const time = video.currentTime;
  const index = cues.findIndex((c) => time >= c.start && time < c.end);
  document.querySelectorAll(".cue.current").forEach((n) => n.classList.remove("current"));
  if (index < 0) return;
  const row = document.querySelector(`.cue[data-index="${index}"]`);
  if (!row) return;
  row.classList.add("current");
  if (followPlayback) {
    const host = el("transcript");
    const offset = row.offsetTop - host.offsetTop - host.clientHeight / 2 + row.clientHeight / 2;
    host.scrollTo({ top: offset, behavior: "smooth" });
  }
}

/* -------------------------------------------------------------- notes */
function renderNotes() {
  const host = el("notes-container");
  const rows = [];

  chapters.forEach((chapter, chapterIndex) => {
    const marks = annotations[chapter.id] || {};
    Object.keys(marks)
      .map(Number)
      .sort((a, b) => a - b)
      .forEach((cueIndex) => {
        const state = marks[cueIndex];
        rows.push({ chapter, chapterIndex, cueIndex, state });
      });
  });

  el("notes-count").textContent = rows.length;

  if (!rows.length) {
    host.innerHTML = `<p class="notes-empty">
      Aucune note pour l'instant. Dans la transcription, double-cliquez une ligne
      pour la surligner, ou utilisez ✎ pour y attacher une note.
    </p>`;
    return;
  }

  host.innerHTML = "";
  rows.forEach(({ chapter, chapterIndex, cueIndex, state }) => {
    const row = document.createElement("div");
    row.className = "note-row";
    const quote =
      chapterIndex === current && cues[cueIndex] ? cues[cueIndex].text : null;
    row.innerHTML = `
      <div class="meta">
        <b>Chapitre ${chapterIndex + 1}</b>
        ${escapeHtml(chapter.title.slice(0, 40))}
      </div>
      <div class="body">
        ${quote ? `<div class="quote">${escapeHtml(quote)}</div>` : ""}
        ${state.note ? `<div class="txt">${escapeHtml(state.note)}</div>` : `<div class="txt muted">Passage surligné</div>`}
      </div>`;
    row.addEventListener("click", () => {
      if (chapterIndex !== current) selectChapter(chapterIndex);
      setTimeout(() => {
        document.querySelector(`.cue[data-index="${cueIndex}"]`)?.scrollIntoView({
          block: "center",
        });
      }, 350);
    });
    host.appendChild(row);
  });
}

/* ------------------------------------------------------------- chapitre */
async function loadTranscript(chapter) {
  cues = [];
  if (!chapter.subtitles) return;
  try {
    const response = await fetch(`${BASE}/videos/${chapter.subtitles}`, { cache: "no-store" });
    if (response.ok) cues = parseVtt(await response.text());
  } catch {
    cues = [];
  }
}

async function selectChapter(index) {
  current = index;
  const chapter = chapters[index];

  el("view-exam").hidden = true;
  el("view-chapter").hidden = false;
  el("exam-btn").classList.remove("active");

  video.src = `${BASE}/videos/${chapter.id}.mp4`;
  while (video.firstChild) video.removeChild(video.firstChild);
  if (chapter.subtitles) {
    const track = document.createElement("track");
    track.kind = "subtitles";
    track.label = "Français";
    track.srclang = "fr";
    track.src = `${BASE}/videos/${chapter.subtitles}`;
    track.default = false;
    video.appendChild(track);
  }
  el("subtitle-btn").disabled = !chapter.subtitles;

  el("chapter-title").textContent = chapter.title;
  el("chapter-time").textContent = `${chapter.timestamp} · ${formatDuration(chapter.duration)}`;
  el("chapter-summary").textContent = chapter.summary || "—";
  el("chapter-points").innerHTML = (chapter.key_points || [])
    .map((p) => `<li>${escapeHtml(p)}</li>`)
    .join("");

  el("prev-btn").disabled = index === 0;
  el("next-btn").disabled = index === chapters.length - 1;

  await loadTranscript(chapter);
  renderTranscript();
  renderNotes();
  renderChapterList();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* ------------------------------------------------------ évaluation finale */
function allQuestions() {
  // Un quiz officiel, rédigé pour la formation entière, n'est rattaché à
  // aucun chapitre : il arrive sous la clé "questions". Un quiz généré reste
  // indexé par chapitre. Le lecteur accepte les deux.
  if (Array.isArray(quiz.questions)) return quiz.questions.map((q) => ({ ...q }));

  const out = [];
  chapters.forEach((chapter, index) => {
    (quiz[chapter.id] || []).forEach((question) => {
      out.push({ ...question, chapterTitle: chapter.title, chapterNumber: index + 1 });
    });
  });
  return out;
}

function refreshExamAvailability() {
  const questions = allQuestions();
  const button = el("exam-btn");
  const seenAll = chapters.length > 0 && progress.completed.length >= chapters.length;
  button.disabled = questions.length === 0;
  el("exam-hint").textContent = questions.length
    ? seenAll
      ? `${questions.length} questions sur tout le cours`
      : `${questions.length} questions · ${chapters.length - progress.completed.length} chapitre(s) restant(s)`
    : "Aucune question disponible";
}

function renderExam() {
  const questions = allQuestions();
  const host = el("exam-container");
  host.innerHTML = "";

  if (!questions.length) {
    host.innerHTML = `<p class="muted">Aucune question disponible pour ce cours.</p>`;
    return;
  }

  el("exam-desc").textContent =
    `${questions.length} questions portant sur les ${chapters.length} chapitres du cours. ` +
    `Répondez à toutes, puis validez pour obtenir votre score.`;

  questions.forEach((question, index) => {
    const multiple = (question.correct_letters || []).length > 1;
    const block = document.createElement("div");
    block.className = "quiz-q";
    block.innerHTML = `
      <div class="q"><span class="n">${index + 1}</span><span>${escapeHtml(question.question)}${
        multiple ? ' <span class="muted">(plusieurs réponses)</span>' : ""
      }</span></div>
      ${question.chapterTitle ? `<div class="from">Chapitre ${question.chapterNumber} — ${escapeHtml(question.chapterTitle)}</div>` : ""}
      ${(question.options || [])
        .map(
          (option) => `
        <label class="opt" data-letter="${option.letter}">
          <input type="${multiple ? "checkbox" : "radio"}" name="q${index}" value="${option.letter}" />
          <span><b>${option.letter}.</b> ${escapeHtml(option.text)}</span>
        </label>`,
        )
        .join("")}
      ${question.explanation ? `<div class="explanation" hidden>${escapeHtml(question.explanation)}</div>` : ""}`;
    block.addEventListener("change", () => block.classList.remove("unanswered"));
    host.appendChild(block);
  });

  const actions = document.createElement("div");
  actions.className = "quiz-actions";
  actions.innerHTML = `
    <button class="btn primary" id="exam-check">Valider mes réponses</button>
    <button class="btn" id="exam-reset">Recommencer</button>
    <span id="exam-score"></span>`;
  host.appendChild(actions);

  el("exam-check").addEventListener("click", () => gradeExam(questions));
  el("exam-reset").addEventListener("click", renderExam);
}

// « A, B et C » plutot que « A et B et C ».
function frenchList(items) {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} et ${items[items.length - 1]}`;
}

function gradeExam(questions) {
  const blocks = [...document.querySelectorAll("#exam-container .quiz-q")];
  const score = el("exam-score");

  // Une question laissee vide n'est pas une erreur de l'apprenant : c'est un oubli.
  // On le lui dit avant de noter, plutot que de compter un zero qu'il ne comprendra pas.
  const blank = blocks.filter((block) => !block.querySelector("input:checked"));
  if (blank.length) {
    blocks.forEach((block) => block.classList.remove("unanswered"));
    blank.forEach((block) => block.classList.add("unanswered"));
    score.className = "score warn";
    score.textContent =
      blank.length === 1
        ? "Une question est encore sans réponse."
        : `${blank.length} questions sont encore sans réponse.`;
    blank[0].scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }

  let correct = 0;

  blocks.forEach((block, index) => {
    block.classList.remove("unanswered");
    const expected = new Set(questions[index].correct_letters || []);
    const chosen = new Set(
      [...block.querySelectorAll("input:checked")].map((input) => input.value),
    );

    const missed = [];
    block.querySelectorAll(".opt").forEach((option) => {
      const letter = option.dataset.letter;
      option.classList.remove("hit", "miss", "bad");
      option.querySelector(".mark")?.remove();

      // Trois etats distincts, la ou il n'y en avait que deux : une bonne reponse
      // oubliee ne doit pas ressembler a une bonne reponse trouvee.
      let mark = "";
      if (expected.has(letter) && chosen.has(letter)) {
        option.classList.add("hit");
        mark = "✓";
      } else if (expected.has(letter)) {
        option.classList.add("miss");
        mark = "manquait";
        missed.push(letter);
      } else if (chosen.has(letter)) {
        option.classList.add("bad");
        mark = "✗";
      }
      if (mark) {
        const tag = document.createElement("span");
        tag.className = "mark";
        tag.textContent = mark;
        option.appendChild(tag);
      }
      option.querySelector("input").disabled = true;
    });

    const exact =
      chosen.size === expected.size && [...chosen].every((letter) => expected.has(letter));
    if (exact) correct += 1;

    const verdict = document.createElement("div");
    if (exact) {
      verdict.className = "verdict ok";
      verdict.textContent = "Réponse correcte";
    } else if (missed.length && missed.length < expected.size) {
      verdict.className = "verdict partial";
      verdict.textContent =
        `Réponse incomplète — il fallait aussi ${frenchList(missed)}. ` +
        `Cette question attendait ${expected.size} réponses.`;
    } else {
      verdict.className = "verdict ko";
      const right = frenchList([...expected]);
      verdict.textContent =
        expected.size > 1
          ? `Réponse incorrecte — les bonnes réponses étaient ${right}.`
          : `Réponse incorrecte — la bonne réponse était ${right}.`;
    }
    block.querySelector(".verdict")?.remove();
    const explanation = block.querySelector(".explanation");
    if (explanation) {
      explanation.hidden = false;
      block.insertBefore(verdict, explanation);
    } else {
      block.appendChild(verdict);
    }
  });

  const pct = Math.round((correct / questions.length) * 100);
  score.className = `score ${pct >= 70 ? "pass" : "fail"}`;
  score.textContent = `${correct} / ${questions.length} — ${pct} %${pct >= 70 ? " · réussi" : " · non atteint (70 % requis)"}`;
  el("exam-check").disabled = true;
}

function showExam() {
  el("view-chapter").hidden = true;
  el("view-exam").hidden = false;
  el("exam-btn").classList.add("active");
  document.querySelectorAll(".chapter-item").forEach((n) => n.classList.remove("active"));
  renderExam();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* ---------------------------------------------------------------- init */
function wireTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      el(tab.dataset.panel).classList.add("active");
    });
  });
}

function wireControls() {
  el("prev-btn").addEventListener("click", () => current > 0 && selectChapter(current - 1));
  el("next-btn").addEventListener(
    "click",
    () => current < chapters.length - 1 && selectChapter(current + 1),
  );

  el("subtitle-btn").addEventListener("click", () => {
    const track = video.textTracks && video.textTracks[0];
    if (!track) return;
    const on = track.mode === "showing";
    track.mode = on ? "disabled" : "showing";
    el("subtitle-btn").classList.toggle("active", !on);
    el("subtitle-btn").textContent = on ? "Sous-titres" : "Sous-titres : activés";
  });

  el("mark-btn").addEventListener("click", markCurrentCue);

  el("follow-btn").addEventListener("click", () => {
    followPlayback = !followPlayback;
    el("follow-btn").classList.toggle("active", followPlayback);
  });

  el("exam-btn").addEventListener("click", showExam);
  el("exam-back").addEventListener("click", () => selectChapter(current));

  video.addEventListener("timeupdate", syncTranscript);
  video.addEventListener("ended", () => {
    markDone(chapters[current].id);
    if (current < chapters.length - 1) selectChapter(current + 1);
    else showExam();
  });
}

async function init() {
  if (!COURSE_ID) {
    location.href = "index.html";
    return;
  }

  progress = readStore(KEY_PROGRESS, { completed: [] });
  annotations = readStore(KEY_NOTES, {});

  try {
    const [chaptersResponse, quizResponse, catalogResponse] = await Promise.all([
      fetch(`${BASE}/course_chapters.json`, { cache: "no-store" }),
      fetch(`${BASE}/quiz.json`, { cache: "no-store" }).catch(() => null),
      fetch("data/courses.json", { cache: "no-store" }).catch(() => null),
    ]);

    chapters = await chaptersResponse.json();
    quiz = quizResponse && quizResponse.ok ? await quizResponse.json() : {};

    const catalog = catalogResponse && catalogResponse.ok ? await catalogResponse.json() : null;
    const entry = catalog?.courses?.find((c) => c.id === COURSE_ID);
    if (entry) {
      document.title = `${entry.title} — S2M`;
      el("course-title").textContent = entry.title;
      const totalMinutes = Math.round(
        chapters.reduce((sum, c) => sum + (c.duration || 0), 0) / 60,
      );
      el("course-meta").textContent = `${chapters.length} chapitres · ${totalMinutes} minutes`;
      if (entry.pdf) {
        el("tab-read").hidden = false;
        el("pdf-frame").src = `${BASE}/${entry.pdf}`;
        el("pdf-download").href = `${BASE}/${entry.pdf}`;
      }
    }
  } catch (error) {
    el("course-meta").textContent = `Cours indisponible (${error.message})`;
    return;
  }

  wireTabs();
  wireControls();
  renderProgress();
  refreshExamAvailability();
  await selectChapter(0);
}

init();
