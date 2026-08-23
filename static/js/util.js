export function fmt(n, d = 2) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return Number(n).toFixed(d);
}

export function fmtInt(n) {
  if (n === null || n === undefined || n === "") return "—";
  const v = Number(n);
  if (Number.isNaN(v)) return String(n);
  return String(Math.round(v));
}

export function deltaHtml(n, digits = 2) {
  if (n === null || n === undefined || Number(n) === 0) {
    return `<span class="delta-zero">·</span>`;
  }
  const v = Number(n);
  const cls = v > 0 ? "delta-pos" : "delta-neg";
  const arrow = v > 0 ? "▲" : "▼";
  return `<span class="${cls}">${arrow}${Math.abs(v).toFixed(digits)}</span>`;
}

export function teamHref(slug, name) {
  return `/s/${encodeURIComponent(slug)}/team?name=${encodeURIComponent(name)}`;
}

export function hideAdminIfPublic() {
  const local = location.hostname === "localhost" || location.hostname === "127.0.0.1";
  if (local) return;
  document.querySelectorAll('a[href="/admin"]').forEach((a) => a.remove());
}

const teamsCache = new Map();
let dataMode;

function staticFile(path) {
  if (path === "/api/status" || path === "/api/sports") return "/data/status.json";
  const rank = path.match(/^\/api\/sports\/([^/]+)\/rankings$/);
  if (rank) return `/data/${decodeURIComponent(rank[1])}/rankings.json`;
  const results = path.match(/^\/api\/sports\/([^/]+)\/results$/);
  if (results) return `/data/${decodeURIComponent(results[1])}/results.json`;
  const team = path.match(/^\/api\/sports\/([^/]+)\/teams\/([^/]+)$/);
  if (team) return `/data/${decodeURIComponent(team[1])}/teams.json`;
  return null;
}

function cmpTeams(a, b, key, dir) {
  const va = a[key];
  const vb = b[key];
  const na = va == null || va === "";
  const nb = vb == null || vb === "";
  if (na && nb) return String(a.name || "").localeCompare(b.name || "");
  if (na) return 1;
  if (nb) return -1;
  if (typeof va === "string" || typeof vb === "string") {
    return String(va).localeCompare(String(vb)) * dir;
  }
  return (Number(va) - Number(vb)) * dir;
}

function applyQuery(url, data) {
  const path = url.pathname;
  if (path.endsWith("/rankings")) {
    const q = (url.searchParams.get("q") || "").trim().toLowerCase();
    const sort = url.searchParams.get("sort") || "rank";
    const dir = url.searchParams.get("dir") === "desc" ? -1 : 1;
    let teams = data.teams || [];
    if (q) teams = teams.filter((t) => (t.name || "").toLowerCase().includes(q));
    teams = [...teams].sort((a, b) => cmpTeams(a, b, sort, dir));
    return { ...data, teams, total: teams.length };
  }
  if (path.endsWith("/results")) {
    const q = (url.searchParams.get("q") || "").trim().toLowerCase();
    if (!q) return data;
    return {
      ...data,
      games: (data.games || []).filter(
        (g) =>
          (g.team1 || "").toLowerCase().includes(q) ||
          (g.team2 || "").toLowerCase().includes(q)
      ),
    };
  }
  const team = path.match(/^\/api\/sports\/[^/]+\/teams\/([^/]+)$/);
  if (team) {
    const name = decodeURIComponent(team[1]);
    const byName = data.byName || {};
    let entry = byName[name];
    if (!entry) {
      const lower = name.toLowerCase();
      const key = Object.keys(byName).find((k) => k.toLowerCase() === lower);
      entry = key ? byName[key] : null;
    }
    if (!entry) throw new Error(`Team not found: ${name}`);
    return { sport: data.sport, kind: data.kind, ...entry };
  }
  return data;
}

export async function api(path) {
  const url = new URL(path, location.origin);
  const file = staticFile(url.pathname);
  if (file && dataMode !== "api") {
    const isTeams = url.pathname.includes("/teams/");
    let res;
    if (isTeams && teamsCache.has(file)) {
      const data = applyQuery(url, await teamsCache.get(file));
      dataMode = "static";
      return data;
    }
    res = await fetch(file);
    if (res.ok) {
      const parsed = res.json();
      if (isTeams) teamsCache.set(file, parsed);
      dataMode = "static";
      return applyQuery(url, await parsed);
    }
    if (dataMode === "static") {
      throw new Error(await res.text() || `HTTP ${res.status}`);
    }
  }
  dataMode = "api";
  const res = await fetch(path);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export function th(key, label, sortState, cls = "") {
  const sorted = sortState.key === key ? "sorted" : "";
  return `<th class="${cls} ${sorted}" data-sort="${key}">${label}</th>`;
}

export function bindSortHeaders(root, sortState, onChange) {
  root.querySelectorAll("th[data-sort]").forEach((el) => {
    el.addEventListener("click", () => {
      const key = el.dataset.sort;
      if (sortState.key === key) sortState.dir *= -1;
      else {
        sortState.key = key;
        sortState.dir = key === "name" || key === "rank" || key === "last_game" ? 1 : -1;
      }
      onChange();
    });
  });
}

export function ratingChart(points, width = 640, height = 160) {
  const vals = points.filter((p) => p.rating != null && p.date);
  if (vals.length < 2) {
    return `<p class="muted">Not enough games to chart.</p>`;
  }
  const pad = { t: 12, r: 12, b: 28, l: 40 };
  const w = width - pad.l - pad.r;
  const h = height - pad.t - pad.b;
  const ratings = vals.map((p) => p.rating);
  let min = Math.min(...ratings);
  let max = Math.max(...ratings);
  if (min === max) {
    min -= 0.5;
    max += 0.5;
  }
  const span = max - min;
  const xAt = (i) => pad.l + (i / (vals.length - 1)) * w;
  const yAt = (r) => pad.t + (1 - (r - min) / span) * h;
  const path = vals
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xAt(i).toFixed(1)} ${yAt(p.rating).toFixed(1)}`)
    .join(" ");
  const y0 = yAt(min).toFixed(1);
  const y1 = yAt(max).toFixed(1);
  return `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Rating over time">
      <line x1="${pad.l}" y1="${y0}" x2="${width - pad.r}" y2="${y0}" stroke="#ddd" />
      <line x1="${pad.l}" y1="${y1}" x2="${width - pad.r}" y2="${y1}" stroke="#eee" />
      <path d="${path}" fill="none" stroke="#111" stroke-width="1.75" />
      <text x="${pad.l}" y="${height - 8}" font-size="10" fill="#666">${vals[0].date}</text>
      <text x="${width - pad.r}" y="${height - 8}" font-size="10" fill="#666" text-anchor="end">${vals[vals.length - 1].date}</text>
      <text x="4" y="${Number(y1) + 3}" font-size="10" fill="#666">${max.toFixed(2)}</text>
      <text x="4" y="${Number(y0) + 3}" font-size="10" fill="#666">${min.toFixed(2)}</text>
    </svg>
    <p class="muted">${vals.length} games</p>
  `;
}

export function sportSlugFromPath() {
  const m = location.pathname.match(/^\/s\/([^/]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}
