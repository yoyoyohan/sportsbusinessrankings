import { api, bindSortHeaders, deltaHtml, fmt, fmtInt, teamHref, th } from "./util.js";

const GROUP_LABELS = {
  "G4 State": "Group 4",
  "G3 State": "Group 3",
  "G2 State": "Group 2",
  "G1 State": "Group 1",
  "NPA State": "Non-Public A",
  "NPB State": "Non-Public B",
  "HV State": "HV / North",
  GMC: "GMC",
};

const content = document.getElementById("content");
const meta = document.getElementById("meta");
const filtersEl = document.getElementById("filters");
const groupWrap = document.getElementById("filter-group-wrap");

let sortState = { key: "rank", dir: 1 };
let status = null;

function setNav() {
  const hash = location.hash.replace("#", "") || "ratings";
  document.querySelectorAll(".nav a").forEach((a) => {
    const href = a.getAttribute("href") || "";
    const key = href.includes("#") ? href.split("#")[1] : href === "/" ? "ratings" : "";
    a.classList.toggle("current", key === hash || (hash === "ratings" && href === "/"));
  });
}

function showFilters(mode) {
  filtersEl.hidden = !mode;
  groupWrap.hidden = mode !== "season";
}

function filterParams() {
  const q = document.getElementById("filter-q").value.trim();
  const minR = document.getElementById("filter-min-rating").value;
  const maxR = document.getElementById("filter-max-rating").value;
  const minM = document.getElementById("filter-min-matches").value;
  const group = document.getElementById("filter-group").value;
  return { q, minR, maxR, minM, group };
}

async function renderRatings() {
  showFilters("ratings");
  setNav();
  const { q, minR, maxR, minM } = filterParams();
  const sort = sortState.key === "name" ? "name" : sortState.key;
  const dir = sortState.dir === 1 ? "asc" : "desc";
  const params = new URLSearchParams({
    ranked_only: "true",
    sort,
    dir,
    limit: "500",
  });
  if (q) params.set("q", q);
  if (minR !== "") params.set("min_rating", minR);
  if (maxR !== "") params.set("max_rating", maxR);
  if (minM !== "") params.set("min_matches", minM);

  const data = await api(`/api/rankings?${params}`);
  meta.textContent = `As of ${data.as_of || "—"} · ${data.total} teams`;

  content.innerHTML = `
    <h2 class="page-title">Overall ratings</h2>
    <p class="note">Click a column to sort. Open any team for match history and rating shifts.</p>
    <div class="table-wrap"><table class="data">
      <thead><tr>
        ${th("rank", "Rank", sortState)}
        ${th("name", "Team", sortState, "left")}
        ${th("rating", "Rating", sortState)}
        ${th("off", "Offense", sortState)}
        ${th("def", "Defense", sortState)}
        ${th("change", "Change", sortState)}
        ${th("n", "Matches", sortState)}
        ${th("last_game", "Last game", sortState)}
      </tr></thead>
      <tbody>
        ${data.teams
          .map(
            (t) => `<tr>
            <td class="rank mono">${fmtInt(t.rank)}</td>
            <td class="left"><a href="${teamHref(t.name)}">${t.name}</a></td>
            <td class="mono">${fmt(t.rating)}</td>
            <td class="mono">${fmt(t.off)}</td>
            <td class="mono">${fmt(t.def)}</td>
            <td class="mono">${deltaHtml(t.change)}</td>
            <td class="mono">${fmtInt(t.n)}</td>
            <td class="mono">${t.last_game || "—"}</td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table></div>
  `;
  bindSortHeaders(content, sortState, () => renderRatings());
}

async function renderResults() {
  showFilters("results");
  setNav();
  const { q } = filterParams();
  const params = new URLSearchParams({ season: "2025", limit: "250" });
  if (q) params.set("q", q);
  const data = await api(`/api/results?${params}`);
  meta.textContent = `${data.games.length} recent 2025 results`;
  content.innerHTML = `
    <h2 class="page-title">Results</h2>
    <p class="note">Filter by team name above. Scores from the games ledger.</p>
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
            <td class="left mono">${g.date || "—"}</td>
            <td class="left"><a href="${teamHref(g.team1)}">${g.team1}</a></td>
            <td class="mono">${g.score1}–${g.score2}</td>
            <td class="left"><a href="${teamHref(g.team2)}">${g.team2}</a></td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table></div>
  `;
}

async function renderDivisions() {
  showFilters(null);
  setNav();
  const data = await api("/api/divisions");
  meta.textContent = "State groups and conferences";
  const hash = location.hash;
  const match = hash.match(/division\/(.+)/);
  const active = match ? decodeURIComponent(match[1]) : null;

  if (active && data.groups[active]) {
    const teams = data.groups[active];
    content.innerHTML = `
      <div class="subnav">
        <a href="#divisions">All divisions</a>
        ${Object.keys(data.groups)
          .map(
            (g) =>
              `<a class="${g === active ? "current" : ""}" href="#division/${encodeURIComponent(g)}">${GROUP_LABELS[g] || g}</a>`
          )
          .join("")}
      </div>
      <h2 class="page-title">${GROUP_LABELS[active] || active}</h2>
      <div class="table-wrap"><table class="data">
        <thead><tr>
          <th>Rank</th><th class="left">Team</th><th>Rating</th><th>Offense</th><th>Defense</th>
        </tr></thead>
        <tbody>
          ${teams
            .map(
              (t) => `<tr>
              <td class="rank mono">${t.rank}</td>
              <td class="left"><a href="${teamHref(t.team)}">${t.team}</a></td>
              <td class="mono">${fmt(t.rating)}</td>
              <td class="mono">${fmt(t.off)}</td>
              <td class="mono">${fmt(t.def)}</td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table></div>
    `;
    return;
  }

  content.innerHTML = `
    <h2 class="page-title">Divisions</h2>
    <p class="note">Leaders by division. Open a card for the full table.</p>
    <div class="cards">
      ${Object.keys(data.groups)
        .map((g) => {
          const list = data.groups[g];
          const top = list
            .slice(0, 5)
            .map(
              (t) =>
                `<li>${t.rank}. <a href="${teamHref(t.team)}">${t.team}</a> <span class="muted mono">${fmt(t.rating)}</span></li>`
            )
            .join("");
          return `<div class="card">
            <h3><a href="#division/${encodeURIComponent(g)}">${GROUP_LABELS[g] || g}</a></h3>
            <p class="note">${list.length} teams</p>
            <ol>${top}</ol>
          </div>`;
        })
        .join("")}
    </div>
  `;
}

async function renderStandings() {
  showFilters("standings");
  setNav();
  const { q } = filterParams();
  const params = q ? `?q=${encodeURIComponent(q)}` : "";
  const data = await api(`/api/standings${params}`);
  meta.textContent = `${data.rows.length} teams`;
  content.innerHTML = `
    <h2 class="page-title">Standings</h2>
    <div class="table-wrap"><table class="data">
      <thead><tr>
        <th class="left">Team</th><th>W</th><th>D</th><th>L</th><th>Pts</th>
        <th>GF</th><th>GA</th><th>GD</th><th>Offense</th><th>Defense</th>
      </tr></thead>
      <tbody>
        ${data.rows
          .map(
            (t) => `<tr>
            <td class="left"><a href="${teamHref(t.team)}">${t.team}</a></td>
            <td class="mono">${fmtInt(t.w)}</td>
            <td class="mono">${fmtInt(t.d)}</td>
            <td class="mono">${fmtInt(t.l)}</td>
            <td class="mono"><strong>${fmtInt(t.pts)}</strong></td>
            <td class="mono">${fmtInt(t.gf)}</td>
            <td class="mono">${fmtInt(t.ga)}</td>
            <td class="mono">${fmtInt(t.gd)}</td>
            <td class="mono">${fmt(t.off)}</td>
            <td class="mono">${fmt(t.def)}</td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table></div>
  `;
}

async function renderSeason() {
  showFilters("season");
  setNav();
  const { q, group } = filterParams();
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (group) params.set("group", group);
  const data = await api(`/api/season?${params}`);
  meta.textContent = `${data.rows.length} schools`;
  content.innerHTML = `
    <h2 class="page-title">Season table</h2>
    <p class="note">Points, group, spread, and win probability.</p>
    <div class="table-wrap"><table class="data">
      <thead><tr>
        <th class="left">School</th><th>Group</th><th>W</th><th>D</th><th>Pts</th>
        <th>Offense</th><th>Defense</th><th>Spread</th><th>Win prob</th><th>Adj pts</th>
      </tr></thead>
      <tbody>
        ${data.rows
          .map(
            (t) => `<tr>
            <td class="left"><a href="${teamHref(t.team)}">${t.team}</a></td>
            <td class="mono">${fmtInt(t.grp)}</td>
            <td class="mono">${fmtInt(t.w)}</td>
            <td class="mono">${fmtInt(t.d)}</td>
            <td class="mono"><strong>${fmtInt(t.pts)}</strong></td>
            <td class="mono">${fmt(t.off)}</td>
            <td class="mono">${fmt(t.def)}</td>
            <td class="mono">${fmt(t.spread)}</td>
            <td class="mono">${fmt(t.odds, 4)}</td>
            <td class="mono">${fmt(t.adjp, 2)}</td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table></div>
  `;
}

async function renderProjections() {
  showFilters("projections");
  setNav();
  const { q } = filterParams();
  const params = q ? `?q=${encodeURIComponent(q)}` : "";
  const data = await api(`/api/projections${params}`);
  meta.textContent = `${data.rows.length} teams`;
  content.innerHTML = `
    <h2 class="page-title">Projections</h2>
    <div class="table-wrap"><table class="data">
      <thead><tr>
        <th class="left">Team</th><th>Quality</th><th>Proj. pts</th>
        <th>Qual. gap</th><th>Win odds</th><th>Exp. pts</th><th class="left">Notes</th>
      </tr></thead>
      <tbody>
        ${data.rows
          .map(
            (t) => `<tr>
            <td class="left"><a href="${teamHref(t.team)}">${t.team}</a></td>
            <td class="mono">${fmt(t.quality)}</td>
            <td class="mono">${fmt(t.pp, 2)}</td>
            <td class="mono">${fmt(t.qual_diff)}</td>
            <td class="mono">${t.win_odds == null ? "—" : fmt(t.win_odds, 4)}</td>
            <td class="mono">${fmt(t.exp_pp, 2)}</td>
            <td class="left">${t.notes || ""}</td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table></div>
  `;
}

async function route() {
  const hash = location.hash.replace(/^#/, "") || "ratings";
  try {
    if (hash.startsWith("division/") || hash === "divisions") return renderDivisions();
    if (hash === "results") return renderResults();
    if (hash === "standings") return renderStandings();
    if (hash === "season") return renderSeason();
    if (hash === "projections") return renderProjections();
    return renderRatings();
  } catch (err) {
    meta.textContent = "Error";
    content.innerHTML = `<p class="note">Could not load data. Is the server running?</p><pre class="log">${err}</pre>`;
  }
}

document.getElementById("filter-apply").addEventListener("click", () => route());
document.getElementById("filter-clear").addEventListener("click", () => {
  ["filter-q", "filter-min-rating", "filter-max-rating", "filter-min-matches"].forEach((id) => {
    document.getElementById(id).value = "";
  });
  document.getElementById("filter-group").value = "";
  route();
});
document.getElementById("filter-q").addEventListener("keydown", (e) => {
  if (e.key === "Enter") route();
});

window.addEventListener("hashchange", () => {
  sortState = { key: "rank", dir: 1 };
  route();
});

(async function boot() {
  try {
    status = await api("/api/status");
    if (!status.games) {
      meta.textContent = "Database empty — run an import from Update";
      content.innerHTML = `<p class="note">No games loaded yet. Go to <a href="/admin">Update</a> and run an import from the spreadsheet.</p>`;
      return;
    }
  } catch {
    /* ignore; route will surface errors */
  }
  route();
})();
