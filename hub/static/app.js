const $ = (s) => document.querySelector(s);
const roles = ["L", "R", "SUB", "MID", "SIDE", "EXTRA", "UNASSIGNED"];

async function api(path, body) {
  const opt = body
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    : { method: path.includes("/api/state") ? "GET" : "POST" };
  const r = await fetch(path, opt);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function escapeHtml(t) {
  return String(t).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

function render(state) {
  $("#status").textContent = [
    state.dry_run ? "dry-run" : "hub",
    state.preset,
    `${state.sinks.length} sinks`,
    `${state.adapters.length} radios`,
  ].join(" · ");
  document.querySelectorAll("[data-preset]").forEach((b) => {
    b.classList.toggle("active", b.dataset.preset === state.preset);
  });
  $("#master").value = state.master_volume;
  $("#masterVal").textContent = Number(state.master_volume).toFixed(2);
  $("#sinks").innerHTML = state.sinks.map((s) => `
    <article class="card" data-mac="${s.mac}">
      <h2><span class="dot ${s.connected ? "on" : "off"}"></span>${escapeHtml(s.name)}</h2>
      <div class="meta">${s.mac} · ${s.adapter || "hci?"} · ${s.codec || (s.a2dp ? "A2DP" : "—")}</div>
      <div class="row">
        <label>rol</label>
        <select data-act="role">
          ${roles.map((r) => `<option value="${r}" ${s.role === r ? "selected" : ""}>${r}</option>`).join("")}
        </select>
        <label>delay ms</label>
        <input data-act="delay" type="number" min="0" max="500" value="${s.delay_ms}" />
      </div>
      <div class="row">
        <label>vol</label>
        <input data-act="vol" type="range" min="0" max="1.5" step="0.01" value="${s.volume}" />
        <button data-act="mute" class="ghost">${s.mute ? "unmute" : "mute"}</button>
        <button data-act="connect" class="ghost">${s.connected ? "desconectar" : "conectar"}</button>
      </div>
    </article>`).join("") || `<p class="meta">No hay sinks. Emparejá parlantes desde el hub o usá Buscar.</p>`;
  if (state.message) $("#log").textContent = state.message;
}

async function reload() { render(await api("/api/state")); }

document.querySelectorAll("[data-preset]").forEach((b) => {
  b.onclick = async () => render(await api("/api/preset", { preset: b.dataset.preset }));
});
$("#master").onchange = async (e) => {
  render(await api("/api/volume", { master: true, volume: Number(e.target.value) }));
};
$("#refresh").onclick = reload;
$("#apply").onclick = async () => render(await api("/api/apply"));
$("#scan").onclick = async () => {
  $("#found").hidden = false;
  $("#found").textContent = "Escaneando 8s…";
  const list = await api("/api/scan");
  $("#found").innerHTML = `<h3>Encontrados</h3>` + (list.map((d) =>
    `<div class="item"><span>${escapeHtml(d.name)}<br><small>${d.mac}</small></span>
     <button data-pair="${d.mac}">Emparejar</button></div>`
  ).join("") || "<p>Nada nuevo.</p>");
};
$("#found").onclick = async (e) => {
  const mac = e.target.dataset.pair;
  if (!mac) return;
  render(await api("/api/connect", { mac }));
};
$("#sinks").onchange = async (e) => {
  const card = e.target.closest(".card");
  if (!card) return;
  const mac = card.dataset.mac;
  if (e.target.dataset.act === "role") render(await api("/api/assign", { mac, role: e.target.value }));
  if (e.target.dataset.act === "delay") render(await api("/api/delay", { mac, delay_ms: Number(e.target.value) }));
};
$("#sinks").onclick = async (e) => {
  const card = e.target.closest(".card");
  if (!card) return;
  const mac = card.dataset.mac;
  const act = e.target.dataset.act;
  if (act === "connect") {
    const label = e.target.textContent;
    render(await api(label.includes("desconectar") ? "/api/disconnect" : "/api/connect", { mac }));
  }
  if (act === "mute") {
    const muted = e.target.textContent === "mute";
    render(await api("/api/volume", { mac, volume: 1, mute: muted }));
  }
};
reload().catch((err) => {
  $("#status").textContent = "sin hub";
  $("#log").textContent = String(err);
});
