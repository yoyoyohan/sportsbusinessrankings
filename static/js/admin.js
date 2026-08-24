import { api } from "./util.js?v=13";

const list = document.getElementById("sport-list");
const logAll = document.getElementById("log-all");
const refreshMeta = document.getElementById("refresh-meta");
const adminToken = new URLSearchParams(location.search).get("token") || "";

function adminHeaders() {
  return adminToken ? { "X-Admin-Token": adminToken } : {};
}

async function load() {
  const data = await api("/api/status");
  const bySlug = Object.fromEntries((data.sports || []).map((s) => [s.slug, s]));
  if (refreshMeta) {
    const when = data.last_refresh_at ? `Last auto refresh: ${data.last_refresh_at}` : "No auto refresh yet";
    const ok =
      data.last_refresh_ok == null
        ? ""
        : data.last_refresh_ok === "1"
          ? " (ok)"
          : " (with errors)";
    refreshMeta.textContent = `Scheduled 4× daily from Drive (read-only). ${when}${ok}.`;
  }
  list.innerHTML = `<table class="data">
    <thead><tr>
      <th class="left">Sport</th><th class="left">Kind</th><th class="left">As of</th><th></th>
    </tr></thead>
    <tbody>
      ${data.catalog
        .map((spec) => {
          const s = bySlug[spec.slug] || {};
          const kind = s.kind || "";
          const recompute = `<button class="btn ghost" data-recompute="${spec.slug}">Recompute</button>`;
          return `<tr>
            <td class="left">${spec.name}</td>
            <td class="left">${kind || "—"}</td>
            <td class="left">${s.as_of || "—"}</td>
            <td class="left">
              <button class="btn ghost" data-refresh="${spec.slug}">Drive</button>
              ${recompute}
            </td>
          </tr>`;
        })
        .join("")}
    </tbody>
  </table>`;
  list.querySelectorAll("[data-refresh]").forEach((btn) => {
    btn.addEventListener("click", () => run(`/api/admin/refresh/${btn.dataset.refresh}`, btn));
  });
  list.querySelectorAll("[data-recompute]").forEach((btn) => {
    btn.addEventListener("click", () => run(`/api/admin/recompute/${btn.dataset.recompute}`, btn));
  });
}

async function run(url, btn) {
  const prev = btn.textContent;
  btn.disabled = true;
  logAll.hidden = false;
  logAll.textContent = "Working… this can take several minutes.";
  try {
    const res = await fetch(url, { method: "POST", headers: adminHeaders() });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || JSON.stringify(body));
    logAll.textContent = JSON.stringify(body, null, 2);
    await load();
  } catch (err) {
    logAll.textContent = String(err);
  } finally {
    btn.disabled = false;
    btn.textContent = prev;
  }
}

document.getElementById("btn-refresh-all").addEventListener("click", (e) => {
  run("/api/admin/refresh-all", e.currentTarget);
});

const btnRecompute = document.getElementById("btn-recompute-offdef")
  || document.getElementById("btn-recompute-all");
if (btnRecompute) {
  btnRecompute.addEventListener("click", (e) => {
    run("/api/admin/recompute-offdef", e.currentTarget);
  });
}

load().catch((err) => {
  list.innerHTML = `<p class="muted">${err}</p>`;
});
