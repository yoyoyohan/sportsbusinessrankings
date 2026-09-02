import { api } from "./util.js?v=15";

const list = document.getElementById("sport-list");
const logAll = document.getElementById("log-all");
const refreshMeta = document.getElementById("refresh-meta");
const adminToken = new URLSearchParams(location.search).get("token") || "";

function adminHeaders() {
  return adminToken ? { "X-Admin-Token": adminToken } : {};
}

async function parseJsonResponse(res) {
  const text = await res.text();
  if (!text.trim()) {
    throw new Error(
      `Empty response (HTTP ${res.status}). Often a timeout or memory restart on Render. ` +
        `Use one sport at a time, or wait for the scheduled GitHub refresh.`
    );
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(
      `Server returned non-JSON (HTTP ${res.status}). ` +
        `Long updates can crash the free Render instance — update sports one at a time.`
    );
  }
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
    refreshMeta.textContent = `Scheduled 4× daily via GitHub Actions (read-only Drive). ${when}${ok}.`;
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
          const recompute = `<button class="btn ghost" data-recompute="${spec.slug}" title="Rebuild from games — will not match Excel">Test engine</button>`;
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
    btn.addEventListener("click", () => runOne(`/api/admin/refresh/${btn.dataset.refresh}`, btn));
  });
  list.querySelectorAll("[data-recompute]").forEach((btn) => {
    btn.addEventListener("click", () => runOne(`/api/admin/recompute/${btn.dataset.recompute}`, btn));
  });
  return data;
}

async function runOne(url, btn) {
  const prev = btn.textContent;
  btn.disabled = true;
  logAll.hidden = false;
  logAll.textContent = "Working…";
  try {
    const res = await fetch(url, { method: "POST", headers: adminHeaders() });
    const body = await parseJsonResponse(res);
    if (!res.ok) throw new Error(body.detail || JSON.stringify(body));
    logAll.textContent = JSON.stringify(body, null, 2);
    await load();
  } catch (err) {
    logAll.textContent = String(err);
    try {
      await load();
    } catch {
      /* ignore */
    }
  } finally {
    btn.disabled = false;
    btn.textContent = prev;
  }
}

/** One sport per request so Render does not OOM on all 27 at once. */
async function runAllSequential(btn) {
  const prev = btn.textContent;
  btn.disabled = true;
  logAll.hidden = false;
  const lines = [];
  const log = (msg) => {
    lines.push(msg);
    logAll.textContent = lines.join("\n");
  };
  try {
    const data = await load();
    const catalog = data.catalog || [];
    log(`Updating ${catalog.length} sports one at a time (avoids Render memory crash)…`);
    let ok = 0;
    let fail = 0;
    for (let i = 0; i < catalog.length; i++) {
      const spec = catalog[i];
      log(`[${i + 1}/${catalog.length}] ${spec.name}…`);
      try {
        const res = await fetch(`/api/admin/refresh/${spec.slug}`, {
          method: "POST",
          headers: adminHeaders(),
        });
        const body = await parseJsonResponse(res);
        if (!res.ok) throw new Error(body.detail || JSON.stringify(body));
        const applied = body.forward?.applied;
        log(
          `  ok teams=${body.teams} games=${body.games}` +
            (applied != null ? ` forward=${applied}` : "")
        );
        ok += 1;
      } catch (err) {
        fail += 1;
        log(`  FAIL ${err}`);
      }
    }
    log(`Done. ok=${ok} fail=${fail}`);
    await load();
  } catch (err) {
    log(String(err));
  } finally {
    btn.disabled = false;
    btn.textContent = prev;
  }
}

document.getElementById("btn-refresh-all").addEventListener("click", (e) => {
  runAllSequential(e.currentTarget);
});

const btnRecompute = document.getElementById("btn-recompute-offdef")
  || document.getElementById("btn-recompute-all");
if (btnRecompute) {
  btnRecompute.addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    const prev = btn.textContent;
    btn.disabled = true;
    logAll.hidden = false;
    logAll.textContent =
      "Full engine recompute of all sports is heavy for Render.\n" +
      "Use “Test engine” per sport, or run: python backend/recompute.py --all on a machine with more RAM.";
    btn.disabled = false;
    btn.textContent = prev;
  });
}

load().catch((err) => {
  list.innerHTML = `<p class="muted">${err}</p>`;
});
