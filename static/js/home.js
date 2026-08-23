import { api } from "./util.js?v=10";

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
      (g) => `<h2 class="season">${g}</h2>
        <div class="sport-grid">${groups[g]
          .map((s) => {
            const bits = [];
            if (s.as_of) bits.push(s.as_of);
            if (s.ranked) bits.push(`${s.ranked} teams`);
            return `<a class="sport-card" href="/s/${encodeURIComponent(s.slug)}">
              <span class="sport-name">${s.name}</span>
              ${bits.length ? `<span class="muted">${bits.join(" · ")}</span>` : ""}
            </a>`;
          })
          .join("")}</div>`
    )
    .join("");
} catch (err) {
  content.innerHTML = `<p class="muted">${err}</p>`;
}
