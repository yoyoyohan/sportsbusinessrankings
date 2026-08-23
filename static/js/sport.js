import { api, bindSortHeaders, deltaHtml, fmt, fmtInt, teamHref, th } from "./util.js?v=12";
const slug = location.pathname.split("/")[2];
const content = document.getElementById("content");
let sortState = { key: "rank", dir: 1 };
let kind = "rating";

document.getElementById("nav-ratings").href = `/s/${slug}`;
document.getElementById("nav-results").href = `/s/${slug}#results`;

async function renderRatings() {
  const q = document.getElementById("filter-q").value.trim();
  const params = new URLSearchParams({
    ranked_only: "true",
    sort: sortState.key,
    dir: sortState.dir === 1 ? "asc" : "desc",
  });
  if (q) params.set("q", q);
  const data = await api(`/api/sports/${encodeURIComponent(slug)}/rankings?${params}`);
  kind = data.kind || "rating";
  const sport = data.sport || {};
  document.title = sport.name || slug;
  document.getElementById("sport-title").textContent = sport.name || "NJ HS Ratings";
  const showOff = kind === "offdef";
  const asOf = sport.as_of ? `as of ${sport.as_of}` : "";
  content.innerHTML = `
    <div class="page-head">
      <h2>Rankings</h2>
      <p class="meta">${asOf}${data.total ? ` · ${data.total} teams` : ""}</p>
    </div>
    <div class="table-wrap"><table class="data">
      <thead><tr>
        ${th("rank", "Rk", sortState)}
        ${th("name", "Team", sortState, "left")}
        ${th("rating", "Rating", sortState)}
        ${showOff ? th("off", "Off", sortState) : ""}
        ${showOff ? th("def", "Def", sortState) : ""}
        ${th("change", "+/−", sortState)}
        ${th("n", "G", sortState)}
        ${th("last_game", "Last", sortState)}
      </tr></thead>
      <tbody>
        ${data.teams
          .map(
            (t) => `<tr>
            <td class="rank">${fmtInt(t.rank)}</td>
            <td class="left"><a href="${teamHref(slug, t.name)}">${t.name}</a></td>
            <td>${fmt(t.rating, 2)}</td>
            ${showOff ? `<td>${fmt(t.off, 2)}</td><td>${fmt(t.def, 2)}</td>` : ""}
            <td>${deltaHtml(t.change, 2)}</td>
            <td>${fmtInt(t.n)}</td>
            <td>${t.last_game || "—"}</td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table></div>
  `;
  bindSortHeaders(content, sortState, () => renderRatings());
}

async function renderResults() {
  const q = document.getElementById("filter-q").value.trim();
  const params = q ? `?q=${encodeURIComponent(q)}` : "";
  const data = await api(`/api/sports/${encodeURIComponent(slug)}/results${params}`);
  const sport = data.sport || {};
  document.getElementById("sport-title").textContent = sport.name || slug;
  document.title = `${sport.name || slug} results`;
  content.innerHTML = `
    <div class="page-head">
      <h2>Results</h2>
      <p class="meta">${data.games.length} recent games</p>
    </div>
    <div class="table-wrap"><table class="data">
      <thead><tr>
        <th class="left">Date</th>
        <th class="left">Team</th>
        <th>Score</th>
        <th class="left">Opponent</th>
      </tr></thead>
      <tbody>
        ${data.games
          .map(
            (g) => `<tr>
            <td class="left">${g.date || ""}</td>
            <td class="left"><a href="${teamHref(slug, g.team1)}">${g.team1}</a></td>
            <td>${g.score1}–${g.score2}</td>
            <td class="left"><a href="${teamHref(slug, g.team2)}">${g.team2}</a></td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table></div>
  `;
}

async function route() {
  try {
    const results = location.hash === "#results";
    document.getElementById("nav-ratings").classList.toggle("current", !results);
    document.getElementById("nav-results").classList.toggle("current", results);
    return results ? renderResults() : renderRatings();
  } catch (err) {
    content.innerHTML = `<p class="muted">${err}</p>`;
  }
}

document.getElementById("filter-q").addEventListener("input", () => route());
window.addEventListener("hashchange", route);
route();
