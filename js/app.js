(() => {
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

  let DATA = null;
  let sortState = { key: "rank", dir: 1 };

  const $ = (s) => document.querySelector(s);
  const content = () => $("#content");
  const meta = () => $("#meta");
  const slug = (n) => encodeURIComponent(n);

  function fmt(n, d = 3) {
    if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
    return Number(n).toFixed(d);
  }

  function fmtInt(n) {
    if (n === null || n === undefined) return "—";
    return String(n);
  }

  function delta(n, digits = 3) {
    if (n === null || n === undefined || Number(n) === 0) {
      return `<span class="flat">0</span>`;
    }
    const v = Number(n);
    const cls = v > 0 ? "up" : "down";
    return `<span class="${cls}">${v > 0 ? "+" : ""}${v.toFixed(digits)}</span>`;
  }

  function setNav(active) {
    document.querySelectorAll("#nav a").forEach((a) => {
      a.classList.toggle("current", a.dataset.nav === active);
    });
  }

  function parseRoute() {
    const hash = location.hash.replace(/^#\/?/, "");
    const parts = hash.split("/").filter(Boolean);
    if (!parts.length) return { page: "ratings", view: "current" };
    if (parts[0] === "team") {
      return { page: "team", team: decodeURIComponent(parts.slice(1).join("/")) };
    }
    if (parts[0] === "division" || parts[0] === "group") {
      return { page: "division", group: decodeURIComponent(parts[1] || "") };
    }
    if (parts[0] === "ratings" || parts[0] === "rankings") {
      return { page: "ratings", view: parts[1] || "current" };
    }
    // legacy redirects
    if (parts[0] === "last-week") return { page: "ratings", view: "previous" };
    if (parts[0] === "movers") return { page: "ratings", view: "movers" };
    if (parts[0] === "groups") return { page: "divisions" };
    if (parts[0] === "odds") return { page: "season" };
    if (parts[0] === "our-games") return { page: "schedule" };
    return { page: parts[0] };
  }

  function sortRows(rows) {
    const { key, dir } = sortState;
    return rows.slice().sort((a, b) => {
      let av = a[key];
      let bv = b[key];
      if (av === null || av === undefined) av = dir > 0 ? Infinity : -Infinity;
      if (bv === null || bv === undefined) bv = dir > 0 ? Infinity : -Infinity;
      if (typeof av === "string") return av.localeCompare(bv) * dir;
      return (Number(av) - Number(bv)) * dir;
    });
  }

  function bindSort(rerender) {
    document.querySelectorAll("th[data-sort]").forEach((th) => {
      th.addEventListener("click", () => {
        const key = th.dataset.sort;
        if (sortState.key === key) sortState.dir *= -1;
        else {
          sortState.key = key;
          sortState.dir =
            key === "team" || key === "rank" || key === "date" || key === "game" || key === "n"
              ? 1
              : -1;
        }
        rerender();
      });
    });
  }

  function th(key, label, cls = "") {
    const sorted = sortState.key === key ? "sorted" : "";
    return `<th class="${cls} ${sorted}" data-sort="${key}">${label}</th>`;
  }

  function ratingsSubnav(view) {
    return `<div class="subnav">
      <a class="${view === "current" ? "current" : ""}" href="#/">Current</a>
      <a class="${view === "previous" ? "current" : ""}" href="#/ratings/previous">Previous week</a>
      <a class="${view === "movers" ? "current" : ""}" href="#/ratings/movers">Biggest movers</a>
    </div>`;
  }

  function divisionPills(active) {
    const links = Object.keys(DATA.groups)
      .map((g) => {
        const cur = active === g ? "current" : "";
        return `<a class="${cur}" href="#/division/${encodeURIComponent(g)}">${GROUP_LABELS[g] || g}</a>`;
      })
      .join("");
    return `<div class="subnav"><a class="${!active ? "current" : ""}" href="#/divisions">All divisions</a>${links}</div>`;
  }

  function renderRatingsCurrent() {
    setNav("ratings");
    meta().textContent = `As of ${DATA.as_of} · ${DATA.totals.ranked} teams`;
    const q = ($("#search")?.value || "").trim().toLowerCase();
    let rows = DATA.ranked;
    if (q) rows = rows.filter((t) => t.team.toLowerCase().includes(q));
    rows = sortRows(rows);
    content().innerHTML = `
      ${ratingsSubnav("current")}
      <h2 class="page-title">Overall ratings</h2>
      <p class="note">Offense + defense ratings for New Jersey high school boys soccer.</p>
      <div class="toolbar">
        <input id="search" type="search" placeholder="Search teams…" value="${($("#search")?.value || "").replace(/"/g, "&quot;")}" />
        <span>${rows.length} teams</span>
      </div>
      <div class="table-wrap"><table class="data">
        <thead><tr>
          ${th("rank", "Rank")}
          ${th("team", "Team", "left")}
          ${th("rating", "Rating")}
          ${th("off", "Offense")}
          ${th("def", "Defense")}
          ${th("change", "Change")}
          ${th("n", "Matches")}
          ${th("date", "Last game")}
        </tr></thead>
        <tbody>
          ${rows
            .map(
              (t) => `<tr>
              <td class="rank mono">${fmtInt(t.rank)}</td>
              <td class="left"><a href="#/team/${slug(t.team)}">${t.team}</a></td>
              <td class="mono">${fmt(t.rating)}</td>
              <td class="mono">${fmt(t.off)}</td>
              <td class="mono">${fmt(t.def)}</td>
              <td class="mono">${delta(t.change)}</td>
              <td class="mono">${fmtInt(t.n)}</td>
              <td class="mono">${t.date || "—"}</td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table></div>
    `;
    $("#search").addEventListener("input", () => renderRatingsCurrent());
    bindSort(() => renderRatingsCurrent());
  }

  function renderRatingsPrevious() {
    setNav("ratings");
    meta().textContent = `Previous week snapshot · ${DATA.last_week.length} teams`;
    sortState = { key: "rank", dir: 1 };
    const rows = sortRows(DATA.last_week);
    content().innerHTML = `
      ${ratingsSubnav("previous")}
      <h2 class="page-title">Previous week</h2>
      <p class="note">Ratings from the prior week for comparison.</p>
      <div class="table-wrap"><table class="data">
        <thead><tr>
          ${th("rank", "Rank")}
          ${th("team", "Team", "left")}
          ${th("rating", "Rating")}
          ${th("off", "Offense")}
          ${th("def", "Defense")}
          ${th("change", "Change")}
          ${th("n", "Matches")}
          ${th("date", "Last game")}
        </tr></thead>
        <tbody>
          ${rows
            .map(
              (t) => `<tr>
              <td class="rank mono">${fmtInt(t.rank)}</td>
              <td class="left"><a href="#/team/${slug(t.team)}">${t.team}</a></td>
              <td class="mono">${fmt(t.rating)}</td>
              <td class="mono">${fmt(t.off)}</td>
              <td class="mono">${fmt(t.def)}</td>
              <td class="mono">${delta(t.change)}</td>
              <td class="mono">${fmtInt(t.n)}</td>
              <td class="mono">${t.date || "—"}</td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table></div>
    `;
    bindSort(() => renderRatingsPrevious());
  }

  function renderRatingsMovers() {
    setNav("ratings");
    meta().textContent = `Biggest movers · ${DATA.movers.length} teams`;
    sortState = { key: "n", dir: 1 };
    const rows = sortRows(DATA.movers);
    content().innerHTML = `
      ${ratingsSubnav("movers")}
      <h2 class="page-title">Biggest movers</h2>
      <p class="note">Teams ordered by movement in the ratings model.</p>
      <div class="table-wrap"><table class="data">
        <thead><tr>
          ${th("n", "#")}
          ${th("team", "Team", "left")}
          ${th("rating", "Rating")}
          ${th("off", "Offense")}
          ${th("def", "Defense")}
          ${th("good", "High")}
          ${th("bad", "Low")}
          ${th("date", "Date")}
        </tr></thead>
        <tbody>
          ${rows
            .map(
              (t) => `<tr>
              <td class="rank mono">${fmtInt(t.n)}</td>
              <td class="left"><a href="#/team/${slug(t.team)}">${t.team}</a></td>
              <td class="mono">${fmt(t.rating)}</td>
              <td class="mono">${fmt(t.off)}</td>
              <td class="mono">${fmt(t.def)}</td>
              <td class="mono">${fmt(t.good)}</td>
              <td class="mono">${fmt(t.bad)}</td>
              <td class="mono">${t.date || "—"}</td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table></div>
    `;
    bindSort(() => renderRatingsMovers());
  }

  function renderResults() {
    setNav("results");
    meta().textContent = `${DATA.totals.games_2025.toLocaleString()} games in 2025`;
    const games = DATA.latest_games || [];
    content().innerHTML = `
      <h2 class="page-title">Recent results</h2>
      <p class="note">Latest scores from the 2025 season.</p>
      <div class="table-wrap"><table class="data">
        <thead><tr>
          <th class="left">Date</th>
          <th class="left">Home / Team 1</th>
          <th>Score</th>
          <th class="left">Away / Team 2</th>
        </tr></thead>
        <tbody>
          ${games
            .map(
              (g) => `<tr>
              <td class="left mono">${g.date || "—"}</td>
              <td class="left"><a href="#/team/${slug(g.team1)}">${g.team1}</a></td>
              <td class="mono">${g.score1}–${g.score2}</td>
              <td class="left"><a href="#/team/${slug(g.team2)}">${g.team2}</a></td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table></div>
    `;
  }

  function renderDivisions() {
    setNav("divisions");
    meta().textContent = "State groups and conferences";
    content().innerHTML = `
      ${divisionPills(null)}
      <h2 class="page-title">Divisions</h2>
      <p class="note">Pick a group to see the full table, or browse the leaders below.</p>
      <div class="cards">
        ${Object.keys(DATA.groups)
          .map((g) => {
            const list = DATA.groups[g];
            const top = list
              .slice(0, 5)
              .map(
                (t) =>
                  `<li>${t.rank}. <a href="#/team/${slug(t.team)}">${t.team}</a> <span class="mono flat">${fmt(t.rating)}</span></li>`
              )
              .join("");
            return `<div class="card">
              <h3><a href="#/division/${encodeURIComponent(g)}">${GROUP_LABELS[g] || g}</a></h3>
              <p class="note">${list.length} teams</p>
              <ol>${top}</ol>
            </div>`;
          })
          .join("")}
      </div>
    `;
  }

  function renderDivision(key) {
    setNav("divisions");
    const teams = DATA.groups[key] || [];
    meta().textContent = `${GROUP_LABELS[key] || key} · ${teams.length} teams`;
    content().innerHTML = `
      ${divisionPills(key)}
      <h2 class="page-title">${GROUP_LABELS[key] || key}</h2>
      <div class="table-wrap"><table class="data">
        <thead><tr>
          <th>Rank</th>
          <th class="left">Team</th>
          <th>Rating</th>
          <th>Offense</th>
          <th>Defense</th>
        </tr></thead>
        <tbody>
          ${teams
            .map(
              (t) => `<tr>
              <td class="rank mono">${t.rank}</td>
              <td class="left"><a href="#/team/${slug(t.team)}">${t.team}</a></td>
              <td class="mono">${fmt(t.rating)}</td>
              <td class="mono">${fmt(t.off)}</td>
              <td class="mono">${fmt(t.def)}</td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table></div>
    `;
  }

  function renderStandings() {
    setNav("standings");
    meta().textContent = `${DATA.standings.length} teams`;
    sortState = { key: "pts", dir: -1 };
    const rows = sortRows(DATA.standings);
    content().innerHTML = `
      <h2 class="page-title">Standings</h2>
      <p class="note">Wins, draws, losses, and points with offense/defense ratings.</p>
      <div class="table-wrap"><table class="data">
        <thead><tr>
          ${th("team", "Team", "left")}
          ${th("w", "W")}
          ${th("d", "D")}
          ${th("l", "L")}
          ${th("pts", "Pts")}
          ${th("gf", "GF")}
          ${th("ga", "GA")}
          ${th("gd", "GD")}
          ${th("off", "Offense")}
          ${th("def", "Defense")}
        </tr></thead>
        <tbody>
          ${rows
            .map(
              (t) => `<tr>
              <td class="left"><a href="#/team/${slug(t.team)}">${t.team}</a></td>
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
    bindSort(() => renderStandings());
  }

  function renderSeason() {
    setNav("season");
    meta().textContent = `${DATA.odds.length} schools`;
    sortState = { key: "pts", dir: -1 };
    const q = ($("#search")?.value || "").trim().toLowerCase();
    let rows = DATA.odds;
    if (q) rows = rows.filter((t) => t.team.toLowerCase().includes(q));
    rows = sortRows(rows);
    content().innerHTML = `
      <h2 class="page-title">Season table</h2>
      <p class="note">Points, group, spread, and win probability for each school.</p>
      <div class="toolbar">
        <input id="search" type="search" placeholder="Search schools…" value="${($("#search")?.value || "").replace(/"/g, "&quot;")}" />
        <span>${rows.length} schools</span>
      </div>
      <div class="table-wrap"><table class="data">
        <thead><tr>
          ${th("team", "School", "left")}
          ${th("group", "Group")}
          ${th("w", "W")}
          ${th("d", "D")}
          ${th("pts", "Pts")}
          ${th("off", "Offense")}
          ${th("def", "Defense")}
          ${th("spread", "Spread")}
          ${th("odds", "Win prob")}
          ${th("adjp", "Adj pts")}
          ${th("dist", "Dist")}
        </tr></thead>
        <tbody>
          ${rows
            .map(
              (t) => `<tr>
              <td class="left"><a href="#/team/${slug(t.team)}">${t.team}</a></td>
              <td class="mono">${fmtInt(t.group)}</td>
              <td class="mono">${fmtInt(t.w)}</td>
              <td class="mono">${fmtInt(t.d)}</td>
              <td class="mono"><strong>${fmtInt(t.pts)}</strong></td>
              <td class="mono">${fmt(t.off)}</td>
              <td class="mono">${fmt(t.def)}</td>
              <td class="mono">${fmt(t.spread)}</td>
              <td class="mono">${fmt(t.odds, 4)}</td>
              <td class="mono">${fmt(t.adjp, 2)}</td>
              <td class="mono">${fmtInt(t.dist)}</td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table></div>
    `;
    $("#search").addEventListener("input", () => renderSeason());
    bindSort(() => renderSeason());
  }

  function renderProjections() {
    setNav("projections");
    meta().textContent = `${DATA.projections.length} teams`;
    sortState = { key: "exp_pp", dir: -1 };
    const rows = sortRows(DATA.projections);
    content().innerHTML = `
      <h2 class="page-title">Projections</h2>
      <p class="note">Quality rating, projected points, and win odds.</p>
      <div class="table-wrap"><table class="data">
        <thead><tr>
          ${th("team", "Team", "left")}
          ${th("quality", "Quality")}
          ${th("pp", "Proj. pts")}
          ${th("qual_diff", "Qual. gap")}
          ${th("win_odds", "Win odds")}
          ${th("exp_pp", "Exp. pts")}
          ${th("notes", "Notes", "left")}
        </tr></thead>
        <tbody>
          ${rows
            .map(
              (t) => `<tr>
              <td class="left"><a href="#/team/${slug(t.team)}">${t.team}</a></td>
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
    bindSort(() => renderProjections());
  }

  function renderSchedule() {
    setNav("schedule");
    meta().textContent = `${DATA.our_games.length} tracked games`;
    content().innerHTML = `
      <h2 class="page-title">Tracked schedule</h2>
      <p class="note">Game-by-game offense, defense, and running rating.</p>
      <div class="table-wrap"><table class="data">
        <thead><tr>
          <th class="left">Matchup</th>
          <th>Date</th>
          <th>Offense</th>
          <th>Defense</th>
          <th>Rating</th>
          <th>Running</th>
        </tr></thead>
        <tbody>
          ${DATA.our_games
            .map(
              (g) => `<tr>
              <td class="left">${g.game}</td>
              <td class="mono">${g.date || "—"}</td>
              <td class="mono">${fmt(g.off)}</td>
              <td class="mono">${fmt(g.def)}</td>
              <td class="mono">${fmt(g.rating)}</td>
              <td class="mono">${fmt(g.running)}</td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table></div>
    `;
  }

  function renderTeam(name) {
    setNav("ratings");
    const t = DATA.team_pages[name];
    if (!t) {
      meta().textContent = "Not found";
      content().innerHTML = `<p>No data for <strong>${name}</strong>.</p><a class="back" href="#/">← Ratings</a>`;
      return;
    }
    meta().textContent = t.team;
    const recent = t.recent || [];
    content().innerHTML = `
      <a class="back" href="#/">← Ratings</a>
      <h2 class="page-title">${t.team}</h2>
      <div class="stats">
        <div class="stat"><span class="label">Rank</span><div class="value">${fmtInt(t.rank)}</div></div>
        <div class="stat"><span class="label">Rating</span><div class="value">${fmt(t.rating)}</div></div>
        <div class="stat"><span class="label">Offense</span><div class="value">${fmt(t.off)}</div></div>
        <div class="stat"><span class="label">Defense</span><div class="value">${fmt(t.def)}</div></div>
        <div class="stat"><span class="label">Change</span><div class="value">${delta(t.change)}</div></div>
        <div class="stat"><span class="label">Matches</span><div class="value">${fmtInt(t.n)}</div></div>
        <div class="stat"><span class="label">Last game</span><div class="value" style="font-size:.95rem">${t.date || "—"}</div></div>
      </div>
      <h2 class="page-title">2025 results</h2>
      ${
        recent.length
          ? `<div class="table-wrap"><table class="data">
              <thead><tr>
                <th class="left">Date</th>
                <th>Result</th>
                <th class="left">Opponent</th>
                <th>Score</th>
              </tr></thead>
              <tbody>
                ${recent
                  .map((g) => {
                    const loc = g.home ? "vs" : "@";
                    const cls = g.result === "W" ? "up" : g.result === "L" ? "down" : "flat";
                    return `<tr>
                      <td class="left mono">${g.date || "—"}</td>
                      <td class="${cls}">${g.result}</td>
                      <td class="left">${loc} <a href="#/team/${slug(g.opponent)}">${g.opponent}</a></td>
                      <td class="mono">${g.gf}–${g.ga}</td>
                    </tr>`;
                  })
                  .join("")}
              </tbody>
            </table></div>`
          : `<p class="note">No 2025 games found for this team.</p>`
      }
    `;
  }

  function go() {
    if (!DATA) return;
    const r = parseRoute();
    if (r.page === "team") return renderTeam(r.team);
    if (r.page === "division") return renderDivision(r.group);
    if (r.page === "ratings") {
      if (r.view === "previous") return renderRatingsPrevious();
      if (r.view === "movers") return renderRatingsMovers();
      sortState = { key: "rank", dir: 1 };
      return renderRatingsCurrent();
    }
    if (r.page === "results") return renderResults();
    if (r.page === "divisions") return renderDivisions();
    if (r.page === "standings") return renderStandings();
    if (r.page === "season") return renderSeason();
    if (r.page === "projections") return renderProjections();
    if (r.page === "schedule") return renderSchedule();
    sortState = { key: "rank", dir: 1 };
    return renderRatingsCurrent();
  }

  async function boot() {
    try {
      const res = await fetch("data/soccer.json");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      DATA = await res.json();
      go();
    } catch (err) {
      meta().textContent = "Error";
      content().innerHTML = `<p class="note">Serve with <code>python3 -m http.server</code>.</p><pre>${err}</pre>`;
    }
  }

  window.addEventListener("hashchange", go);
  boot();
})();
