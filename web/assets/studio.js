/* Studio — dépôt d'un support et suivi des productions.
   Le suivi est un sondage plutôt qu'une connexion permanente : une production
   dure une heure et demie et avance par paliers de plusieurs minutes, donc
   rafraîchir toutes les cinq secondes suffit largement et survit à une coupure
   réseau sans rien de particulier à écrire. */

const POLL_MS = 5000;
const el = (id) => document.getElementById(id);

const STATE_LABEL = {
  queued: "En attente",
  running: "En cours",
  done: "Publié",
  failed: "Échec",
  cancelled: "Annulée",
  interrupted: "Interrompue",
};

let timer = null;
let openLogs = new Set();

function escapeHtml(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );
}

function since(iso) {
  if (!iso) return "";
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "à l'instant";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `il y a ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return `il y a ${hours} h ${String(minutes % 60).padStart(2, "0")}`;
}

/* ------------------------------------------------------------------ quota */
function renderQuota(quota) {
  const node = el("quota");
  if (!quota) return;
  const { remaining, limit, fallbacks } = quota;
  // Un chapitre coûte une requête. Le dire ainsi évite d'avoir à expliquer
  // pourquoi un long support sort moins bien en fin de journée.
  node.textContent = `Rédaction : ${remaining} / ${limit} chapitres aujourd'hui`;
  node.className = "quota" + (remaining === 0 ? " empty" : remaining <= 5 ? " low" : "");
  node.title = fallbacks
    ? `${fallbacks} chapitre(s) déjà écrits par le modèle de repli aujourd'hui.`
    : "Quota journalier du modèle de rédaction. Un chapitre coûte une requête.";
}

/* ------------------------------------------------------------- une production */
function stagesHtml(job) {
  return `<ol class="stages">${job.stages
    .map(
      (stage) => `
      <li class="stage ${stage.state}">
        <span class="dot"></span>
        <span class="lbl">${escapeHtml(stage.label)}</span>
        ${stage.detail ? `<span class="det">${escapeHtml(stage.detail)}</span>` : ""}
      </li>`,
    )
    .join("")}</ol>`;
}

function actionsHtml(job) {
  const buttons = [];
  if (job.state === "done") {
    buttons.push(
      `<a class="btn primary" href="course.html?course=${encodeURIComponent(job.course_id)}">Voir le cours</a>`,
    );
  }
  if (job.state === "queued" || job.state === "running") {
    buttons.push(`<button class="btn" data-act="cancel" data-id="${job.id}">Annuler</button>`);
  }
  if (["failed", "cancelled", "interrupted"].includes(job.state)) {
    buttons.push(`<button class="btn" data-act="retry" data-id="${job.id}">Reprendre</button>`);
  }
  if (["done", "failed", "cancelled", "interrupted"].includes(job.state)) {
    buttons.push(`<button class="btn quiet" data-act="forget" data-id="${job.id}">Retirer</button>`);
  }
  buttons.push(
    `<button class="btn quiet" data-act="log" data-id="${job.id}">${
      openLogs.has(job.id) ? "Masquer le journal" : "Journal"
    }</button>`,
  );
  return `<div class="job-actions">${buttons.join("")}</div>`;
}

function jobHtml(job) {
  const pct = Math.round((job.completed / job.total) * 100);
  const waiting = job.state === "queued" && job.queue_position > 1;
  return `
    <article class="job ${job.state}" data-id="${job.id}">
      <div class="job-head">
        <div>
          <h3>${escapeHtml(job.title)}</h3>
          <p class="job-meta">
            <code>${escapeHtml(job.course_id)}</code> ·
            ${escapeHtml(job.pdf_name)}
            ${job.quiz_path ? ` · quiz officiel, ${job.quiz_questions} questions` : ""}
            · ${escapeHtml(since(job.started_at || job.created_at))}
          </p>
        </div>
        <span class="badge ${job.state}">${STATE_LABEL[job.state] || job.state}</span>
      </div>

      <div class="bar"><span style="width:${pct}%"></span></div>
      <p class="job-line">
        ${job.completed} / ${job.total} étapes
        ${waiting ? ` · ${job.queue_position - 1} production(s) devant` : ""}
        ${job.error ? ` · <span class="err">${escapeHtml(job.error)}</span>` : ""}
      </p>

      ${stagesHtml(job)}
      ${actionsHtml(job)}
      <pre class="job-log" ${openLogs.has(job.id) ? "" : "hidden"} id="log-${job.id}">Chargement…</pre>
    </article>`;
}

/* ------------------------------------------------------------------ rendu */
async function refresh() {
  let payload;
  try {
    payload = await fetch("api/jobs").then((r) => r.json());
  } catch {
    return; // Le prochain tour réessaiera ; inutile d'alarmer sur un hoquet.
  }
  renderQuota(payload.quota);

  const host = el("jobs");
  if (!payload.jobs.length) {
    host.innerHTML = `<p class="muted">Aucune production pour l'instant.</p>`;
    return;
  }
  host.innerHTML = payload.jobs.map(jobHtml).join("");
  for (const id of openLogs) loadLog(id);
}

async function loadLog(id) {
  const node = el(`log-${id}`);
  if (!node) return;
  try {
    const job = await fetch(`api/jobs/${id}`).then((r) => r.json());
    node.textContent = job.log || "(journal vide)";
    node.scrollTop = node.scrollHeight;
  } catch {
    node.textContent = "(journal indisponible)";
  }
}

/* --------------------------------------------------------------- actions */
document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-act]");
  if (!button) return;
  const { act, id } = button.dataset;

  if (act === "log") {
    if (openLogs.has(id)) openLogs.delete(id);
    else openLogs.add(id);
    await refresh();
    return;
  }
  if (act === "forget" && !confirm("Retirer cette ligne de l'historique ? Le cours publié n'est pas supprimé.")) {
    return;
  }
  if (act === "cancel" && !confirm("Arrêter cette production ? Ce qui est déjà produit est conservé.")) {
    return;
  }
  const method = act === "forget" ? "DELETE" : "POST";
  const path = act === "forget" ? `api/jobs/${id}` : `api/jobs/${id}/${act}`;
  await fetch(path, { method });
  await refresh();
});

/* ---------------------------------------------------------------- dépôt */
el("job-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = el("submit-btn");
  const message = el("form-msg");
  const data = new FormData(event.target);
  if (!data.get("quiz")?.size) data.delete("quiz");

  button.disabled = true;
  message.className = "form-msg";
  message.textContent = "Envoi du support…";

  try {
    const response = await fetch("api/jobs", { method: "POST", body: data });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || "La production n'a pas pu être lancée.");
    }
    event.target.reset();
    message.className = "form-msg ok";
    message.textContent = "Production lancée. Elle apparaît ci-dessous.";
    await refresh();
  } catch (error) {
    message.className = "form-msg ko";
    message.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

refresh();
timer = setInterval(refresh, POLL_MS);
document.addEventListener("visibilitychange", () => {
  // Ne pas sonder un onglet que personne ne regarde.
  clearInterval(timer);
  if (!document.hidden) {
    refresh();
    timer = setInterval(refresh, POLL_MS);
  }
});
