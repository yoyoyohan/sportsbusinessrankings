import { api } from "./util.js?v=8";

const list = document.getElementById("sport-list");
const logAll = document.getElementById("log-all");
const adminToken = new URLSearchParams(location.search).get("token") || "";

function adminHeaders() {
  return adminToken ? { "X-Admin-Token": adminToken } : {};
}

async function load() {
  const data = await api("/api/status");
  const bySlug = Object.fromEntries((data.sports || []).map((s) => [s.slug, s]));
  list.innerHTML = `<table class="data">
    <thead><tr>
      <th class="left">Sport</th><th class="left">As of</th><th></th>
    </tr></thead>
    <tbody>
      ${data.catalog
        .map((spec) => {
          const s = bySlug[spec.slug] || {};
          return `<tr>
            <td class="left">${spec.name}</td>
            <td class="left">${s.as_of || "—"}</td>
            <td class="left"><button class="btn ghost" data-refresh="${spec.slug}">Update</button></td>
          </tr>`;
        })
        .join("")}
    </tbody>
  </table>`;
  list.querySelectorAll("[data-refresh]").forEach((btn) => {
    btn.addEventListener("click", () =>
      run(`/api/admin/refresh/${btn.dataset.refresh}`, btn)
    );
  });
}

async function run(url, btn) {
  const prev = btn.textContent;
  btn.disabled = true;
  logAll.hidden = false;
  logAll.textContent = "Working…";
  try {
    const res = await fetch(url, { method: "POST", headers: adminHeaders() });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || JSON.stringify(body));
    logAll.textContent = "Done.";
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

load().catch((err) => {
  list.innerHTML = `<p class="muted">${err}</p>`;
});
