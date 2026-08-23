import { api } from "./util.js?v=13";

const content = document.getElementById("content");

try {
  const data = await api("/api/status");
  const bySlug = Object.fromEntries((data.sports || []).map((s) => [s.slug, s]));
  const groups = {};
  for (const spec of data.catalog) {
    const merged = { ...spec, ...(bySlug[spec.slug] || {}) };
    (groups[spec.group] ||= []).push(merged);
  }
  content.innerHTML = ["Fall", "Winter", "Spring"]
    .filter((g) => groups[g])
    .map(
      (g) => `<section class="season-block">
        <h2 class="season">${g}</h2>
        <div class="sport-list">${groups[g]
          .map((s) => {
            const meta = s.ranked ? `${s.ranked} teams` : "";
            return `<a class="sport-row" href="/s/${encodeURIComponent(s.slug)}">
              <span class="sport-name">${s.name}</span>
              ${meta ? `<span class="muted">${meta}</span>` : ""}
            </a>`;
          })
          .join("")}</div>
      </section>`
    )
    .join("");
} catch (err) {
  content.innerHTML = `<p class="muted">${err}</p>`;
}
