/* Catalogue des formations.
 *
 * Les cours sont écrits à partir du support de formation. Le catalogue annonce
 * ce que l'apprenant y trouvera avant qu'il ne s'engage. */

const TRACKS = {
  essentiel: {
    label: "Parcours essentiel",
    hint: "Droit au but, chapitres de moins de cinq minutes.",
  },
};

function progressFor(courseId, chapterCount) {
  try {
    const raw = localStorage.getItem(`s2m-course-progress:${courseId}`);
    if (!raw || !chapterCount) return 0;
    const seen = JSON.parse(raw).completed || [];
    return Math.round((seen.length / chapterCount) * 100);
  } catch {
    return 0;
  }
}

function card(course) {
  const track = TRACKS[course.track] || TRACKS.essentiel;
  const done = progressFor(course.id, course.chapters);
  const href = `course.html?course=${encodeURIComponent(course.id)}`;

  const el = document.createElement("article");
  el.className = "course-card";
  el.innerHTML = `
    <a class="course-thumb" href="${href}" aria-label="${course.title}">
      ${
        course.thumbnail
          ? `<img src="data/${course.id}/${course.thumbnail}" alt="" loading="lazy" />`
          : ""
      }
      <span class="track-badge ${course.track === "essentiel" ? "essentiel" : ""}">${track.label}</span>
    </a>
    <div class="course-body">
      <h3>${course.title}</h3>
      <p class="desc">${course.description || track.hint}</p>
      <div class="course-stats">
        <span><b>${course.chapters}</b> chapitres</span>
        <span><b>${course.duration_minutes}</b> min</span>
        ${course.questions ? `<span><b>${course.questions}</b> questions</span>` : ""}
      </div>
      <div class="course-progress">
        <div class="bar"><div style="width:${done}%"></div></div>
        <span>${done ? `${done} % suivi` : "Non commencé"}</span>
      </div>
      <div class="course-actions">
        <a class="btn primary" href="${href}">${done ? "Reprendre" : "Commencer"}</a>
        ${
          course.pdf
            ? `<a class="btn" href="data/${course.id}/${course.pdf}" target="_blank" rel="noopener">Support PDF</a>`
            : ""
        }
      </div>
    </div>`;
  return el;
}

async function init() {
  const host = document.getElementById("catalog");
  try {
    const response = await fetch("data/courses.json", { cache: "no-store" });
    if (!response.ok) throw new Error(response.statusText);
    const courses = (await response.json()).courses || [];

    if (!courses.length) {
      host.innerHTML = `<p class="muted">Aucune formation publiée pour le moment.</p>`;
      return;
    }

    // Le parcours essentiel d'abord : c'est celui qu'on conseille pour une
    // première lecture, le détaillé restant disponible pour approfondir.
    courses.sort((a, b) => (a.track === "essentiel" ? -1 : 1) - (b.track === "essentiel" ? -1 : 1));

    host.innerHTML = "";
    courses.forEach((course) => host.appendChild(card(course)));
  } catch (error) {
    host.innerHTML = `<p class="muted">Catalogue indisponible (${error.message}).</p>`;
  }
}

init();
