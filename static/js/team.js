import { api, deltaHtml, fmt, fmtInt, hideAdminIfPublic, ratingChart, teamHref } from "./util.js?v=8";

hideAdminIfPublic();

const slug = location.pathname.split("/")[2];
const name = new URLSearchParams(location.search).get("name");
const content = document.getElementById("content");

document.getElementById("nav-ratings").href = `/s/${slug}`;
document.getElementById("back").href = `/s/${slug}`;

if (!name) {
  content.innerHTML = `<p class="muted"><a href="/s/${slug}">Back</a></p>`;
} else {
  try {
    const data = await api(
      `/api/sports/${encodeURIComponent(slug)}/teams/${encodeURIComponent(name)}`
    );
    const t = data.team;
    const sport = data.sport || {};
    document.title = t.name;
    document.getElementById("sport-title").textContent = t.name;
    const showOff = data.kind === "offdef";
    const history = data.history || [];
    const resultClass = (r) =>
      r === "W" ? "result-w" : r === "L" ? "result-l" : "";
    content.innerHTML = `
      <div class="page-head">
        <h2>${t.name}</h2>
        <p class="meta">${sport.name || ""}${sport.as_of ? ` · as of ${sport.as_of}` : ""}</p>
      </div>
      <div class="stats">
        <div class="stat"><span class="label">Rank</span><div class="value">${fmtInt(t.rank)}</div></div>
        <div class="stat"><span class="label">Rating</span><div class="value">${fmt(t.rating, 2)}</div></div>
        ${
          showOff
            ? `<div class="stat"><span class="label">Off</span><div class="value">${fmt(t.off, 2)}</div></div>
        <div class="stat"><span class="label">Def</span><div class="value">${fmt(t.def, 2)}</div></div>`
            : ""
        }
        <div class="stat"><span class="label">+/−</span><div class="value">${deltaHtml(t.change, 2)}</div></div>
        <div class="stat"><span class="label">Games</span><div class="value">${fmtInt(t.n)}</div></div>
      </div>
      <div class="chart-wrap">${ratingChart(data.chart || [])}</div>
      <div class="table-wrap"><table class="data">
        <thead><tr>
          <th class="left">Date</th><th></th><th class="left">Opponent</th>
          <th>Score</th><th>Before</th><th>After</th><th>+/−</th>
        </tr></thead>
        <tbody>
          ${history
            .map((g) => {
              const loc = g.home ? "vs" : "@";
              return `<tr>
                <td class="left">${g.date || ""}</td>
                <td class="${resultClass(g.result)}">${g.result || ""}</td>
                <td class="left">${loc} <a href="${teamHref(slug, g.opponent)}">${g.opponent}</a></td>
                <td>${g.gf}–${g.ga}</td>
                <td>${fmt(g.ori_rating, 2)}</td>
                <td>${fmt(g.new_rating, 2)}</td>
                <td>${deltaHtml(g.rating_delta, 2)}</td>
              </tr>`;
            })
            .join("")}
        </tbody>
      </table></div>
    `;
  } catch (err) {
    content.innerHTML = `<p class="muted">${err}</p>`;
  }
}
