"use strict";
// ModTrap's page (DESIGN§4). Version 0.1 only reads: every call below is a GET, except opening a folder.

const TOKEN = document.body.dataset.token;
const $ = (id) => document.getElementById(id);
const state = { status: "none", mods: [], plugins: [], picked: new Set(), logAfter: 0, loaded: "", details: new Map() };

async function api(path, body) {
  const opt = { headers: { "X-ModTrap-Token": TOKEN } };
  if (body !== undefined) {
    opt.method = "POST";
    opt.headers["Content-Type"] = "application/json";
    opt.body = JSON.stringify(body);
  }
  const r = await fetch(path, opt);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || ("the request failed (" + r.status + ")"));
  return data;
}

function el(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v == null) continue;
    if (k === "class") e.className = v;
    else if (k === "text") e.textContent = v;
    else if (k.startsWith("data-") || k.startsWith("aria-")) e.setAttribute(k, v);
    else e[k] = v;
  }
  for (const k of kids) if (k != null) e.append(k);
  return e;
}
const plural = (n, one, many) => n + " " + (n === 1 ? one : (many || one + "s"));
const fold = (s) => s.toLowerCase();

// --- the instance bar ----------------------------------------------------------------------------------------------

// A message the owner must get to read (a refused folder, a failed drop) stays until a modlist is being read.
function problem(text) {
  state.sticky = text;
  showMessage(text, true);
}

function showMessage(text, bad) {
  const m = $("message");
  m.hidden = !text;
  m.textContent = text || "";
  m.classList.toggle("bad", !!bad);
}

function toast(text) {
  const t = $("toast");
  t.textContent = text;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, 2600);
}

async function copyText(text, what) {
  try {
    await navigator.clipboard.writeText(text);
    toast(what + " copied. Your folders are already replaced by placeholders.");
  } catch (e) {
    toast("The browser did not allow copying. Select the lines and press Ctrl+C.");
  }
}

function renderRecent(s) {
  const list = (s.recent || []).filter((r) => r !== s.folder || s.status !== "ready");
  $("recent").hidden = !list.length;
  $("recent-list").replaceChildren(...list.map((path) => {
    const parts = path.split(/[\\/]/).filter(Boolean);
    const b = el("button", { type: "button", class: "recent", title: "Open this modlist again" },
      el("strong", { text: parts[parts.length - 1] || path }), el("span", { class: "dim mono", text: path }));
    b.addEventListener("click", () => { $("folder").value = path; openFolder(path, null); });
    return b;
  }));
}

function renderSteps() {
  const steps = $("steps");
  const job = state.job;
  const picked = state.picked.size;
  const dryDone = job && job.state === "done";
  const dryBusy = job && !["done", "failed", "stopped"].includes(job.state);
  const at = dryDone ? "trap" : dryBusy || picked ? "dry" : "pick";
  $("step-pick").textContent = picked ? plural(picked, "mod") + " ticked" : "Tick the mods to take out";
  $("step-dry").textContent = dryBusy ? "Dry run going…" : dryDone ? "Dry run done" : "Dry run";
  for (const li of steps.children) {
    const k = li.dataset.step;
    const done = k === "open" || (k === "pick" && picked > 0) || (k === "dry" && dryDone);
    li.classList.toggle("done", done);
    li.classList.toggle("now", k === at && !done);
  }
  steps.querySelector('[data-step="dry"]').dataset.tab = job ? "job" : "selection";
  steps.querySelector('[data-step="trap"]').dataset.tab = "steps";
}

function renderTools(s) {
  const box = $("tools-list");
  const rows = s.tools.map((t) => el("tr", {},
    el("td", {}, t.title, t.xedit ? el("span", { class: "tag good", text: "ModTrap starts this one for a dry run" }) : null),
    el("td", { class: "mono", text: t.file }),
    el("td", { text: t.output_mod || "" })));
  box.replaceChildren(el("div", { class: "card" },
    el("h2", { text: plural(s.tools.length, "tool") + " set up in this MO2" }),
    el("p", { class: "dim", text: "These are the executables in MO2's own list. ModTrap only ever starts xEdit. “Output goes to” is the mod MO2 sends a tool's new files to; a plugin found there was made by that tool." }),
    el("table", { class: "plain" }, el("thead", {}, el("tr", {}, el("th", { text: "Name in MO2" }), el("th", { text: "Program" }), el("th", { text: "Output goes to" }))),
      el("tbody", {}, ...rows))));
}

function renderState(s) {
  state.session = s.session;
  renderSessions(s);
  $("version").textContent = s.version ? "version " + s.version : "";
  if (document.activeElement !== $("folder") && s.folder && (!$("folder").value || s.status === "ready")) $("folder").value = s.folder;
  const ready = s.status === "ready";
  $("summary").hidden = !ready;
  $("tabs").hidden = !ready;
  $("steps").hidden = !ready;
  $("rescan").hidden = !ready;
  $("drop").classList.toggle("compact", ready);
  $("folder-label").textContent = ready ? "Modlist" : "or paste its path";
  $("welcome").hidden = ready || s.status === "reading";
  $("reading").hidden = s.status !== "reading";
  if (s.status === "reading" || ready) state.sticky = "";
  if (state.sticky) showMessage(state.sticky, true);
  else if (s.status === "error") showMessage(s.message, true);
  else showMessage("");
  renderRecent(s);
  if (!ready) {
    document.querySelectorAll(".tab").forEach((t) => { t.hidden = true; });
    $("notes").hidden = true;
    $("profile").hidden = true;
    $("tray").hidden = true;
    return;
  }
  $("s-game").textContent = (s.game || "Game unknown") + " · profile " + s.profile;
  $("s-mods").textContent = plural(s.mods, "mod") + ", " + s.mods_enabled + " enabled";
  $("s-plugins").textContent = plural(s.plugins, "plugin") + ", " + s.plugins_active + " active" +
    (s.unreadable ? ", " + s.unreadable + " unreadable" : "");
  $("s-tools").textContent = plural(s.tools.length, "tool") + " set up in MO2";
  const h = $("s-health");
  h.textContent = s.issue_count ? plural(s.issue_count, "master problem") : "No missing or inactive masters";
  h.className = "chip link " + (s.issue_count ? "bad" : "good");
  $("health-count").textContent = s.issue_count;
  $("health-count").classList.toggle("bad", s.issue_count > 0);
  const notes = $("notes");
  notes.replaceChildren(...s.notes.map((n) => el("li", { text: n })));
  notes.hidden = !s.notes.length;
  const sel = $("profile");
  sel.hidden = s.profiles.length < 2;
  if (document.activeElement !== sel)
    sel.replaceChildren(...s.profiles.map((p) => el("option", { value: p, text: p, selected: p === s.profile })));
  const toolsKey = JSON.stringify(s.tools);
  if (toolsKey !== state.toolsKey) { state.toolsKey = toolsKey; renderTools(s); }
  renderHealth(s);
  renderSteps();
}

function renderHealth(s) {
  const box = $("health");
  if (!s.issue_count) {
    box.replaceChildren(el("div", { class: "card" }, el("h2", { text: "The load order is clean" }),
      el("p", { class: "dim", text: "No active plugin lists a master that is missing or not active. This is what MO2's own warning checks." })));
    return;
  }
  const by = new Map();
  for (const i of s.issues) {
    if (!by.has(i.plugin)) by.set(i.plugin, []);
    by.get(i.plugin).push(i);
  }
  const card = el("div", { class: "card" }, el("h2", { text: plural(s.issue_count, "master problem") }),
    el("p", { class: "dim", text: "Each of these plugins is active and needs a master that is missing or not active. MO2 shows the same as a warning." }));
  const ul = el("ul");
  for (const [plugin, items] of by) {
    ul.append(el("li", {}, el("span", { class: "mono", text: plugin }), " needs ",
      ...items.flatMap((i, n) => [n ? ", " : "", el("span", { class: "mono", text: i.master }),
        el("span", { class: "tag " + (i.what === "missing" ? "bad" : "warn"), text: i.what === "missing" ? "missing" : "not active" })])));
  }
  card.append(ul);
  if (s.issue_count > s.issues.length) card.append(el("p", { class: "dim", text: "Showing the first " + s.issues.length + "." }));
  box.replaceChildren(card);
}

// --- sessions, and what the page remembers (MT20) -------------------------------------------------------------------

const STATUS_WORDS = { active: "holds the modlist", waiting: "waiting, locked", finished: "finished" };

function currentUi() {
  return {
    tab: state.tab || "mods", picked: [...state.picked], order: $("mods-order").value,
    search: $("mods-search").value, fEnabled: $("f-enabled").checked, fPlugins: $("f-plugins").checked, fDeps: $("f-deps").checked,
    pSearch: $("plugins-search").value, pProblems: $("p-problems").checked, pDeps: $("p-deps").checked,
    collapsed: [...(state.collapsed || [])], plugin: state.plugin || "", stepsDone: state.stepsDone || {},
  };
}

let uiTimer;
function saveUi() {
  if (state.applying || !state.session || state.status !== "ready" || state.quit) return;
  clearTimeout(uiTimer);
  uiTimer = setTimeout(async () => {
    const ui = currentUi();
    const text = JSON.stringify(ui);
    if (text === state.uiSaved) return;
    try { await api("/api/session/ui", { ui: ui }); state.uiSaved = text; } catch (e) { /* tried again at the next change */ }
  }, 500);
}

// Puts the page back as the session last had it.
function applyUi(ui) {
  ui = ui || {};
  state.applying = true;
  try {
    $("mods-order").value = ["mo2", "rev", "deps"].includes(ui.order) ? ui.order : "mo2";
    $("mods-search").value = ui.search || "";
    $("f-enabled").checked = !!ui.fEnabled; $("f-plugins").checked = !!ui.fPlugins; $("f-deps").checked = !!ui.fDeps;
    $("plugins-search").value = ui.pSearch || "";
    $("p-problems").checked = !!ui.pProblems; $("p-deps").checked = !!ui.pDeps;
    state.collapsed = new Set(Array.isArray(ui.collapsed) ? ui.collapsed : []);
    state.stepsDone = ui.stepsDone && typeof ui.stepsDone === "object" ? ui.stepsDone : {};
    state.stepsText = "";
    state.picked = new Set();
    for (const n of Array.isArray(ui.picked) ? ui.picked : []) {
      const m = findMod(n);
      if (m && m.kind === "mod" && m.plugins.length) state.picked.add(n);
    }
    for (const g of state.groups) for (const m of g.mods) {
      const on = state.picked.has(m.name);
      m.row.classList.toggle("picked", on);
      const box = m.row.querySelector("input");
      if (box) box.checked = on;
    }
    state.details.clear();
    layoutMods();
    filterPlugins();
    $("sel-count").textContent = state.picked.size;
    $("sel-count").classList.toggle("on", state.picked.size > 0);
    $("plan").hidden = true;
    renderSelection();
    const tabs = [...document.querySelectorAll("#tabs button")].map((b) => b.dataset.tab);
    showTab(tabs.includes(ui.tab) ? ui.tab : "mods");
    state.plugin = "";
    if (ui.plugin) {
      const p = state.plugins.find((x) => x.name === ui.plugin);
      if (p) showPlugin(p.name, p.row);
    }
    state.uiSaved = JSON.stringify(currentUi());
  } finally { state.applying = false; }
  updateDryButton();
  updateTray();
  renderSteps();
}

function updateDryButton() {
  const busy = state.job && !["done", "failed", "stopped"].includes(state.job.state);
  const locked = state.session && state.session.locked;
  const b = $("dry-run");
  b.disabled = !state.picked.size || busy || !!locked;
  b.title = locked ? "Not now: " + locked : !state.picked.size ? "Tick a mod first" : "";
}

async function sessionCall(path, body, done) {
  try { await api(path, body); if (done) toast(done); } catch (e) { problem(e.message); }
  $("session-panel").hidden = true;
  $("session-btn").setAttribute("aria-expanded", "false");
  tick();
}

function renderSessions(s) {
  const btn = $("session-btn");
  const cur = s.session;
  btn.hidden = !cur;
  if (cur) btn.textContent = "Session: " + cur.name;
  const lock = $("locked");
  lock.hidden = !(cur && cur.locked);
  if (cur && cur.locked) {
    const kids = [el("span", { text: cur.locked.charAt(0).toUpperCase() + cur.locked.slice(1) + "." })];
    const holder = s.sessions.find((x) => x.status === "active" && x.folder === cur.folder && x.id !== cur.id);
    if (cur.status === "waiting" && holder) {
      const go = el("button", { type: "button", text: "Go to “" + holder.name + "”" });
      go.addEventListener("click", () => sessionCall("/api/session/switch", { id: holder.id }));
      kids.push(go);
    }
    if (cur.status === "finished") {
      const nw = el("button", { type: "button", text: "Start a new session on this modlist" });
      nw.addEventListener("click", () => sessionCall("/api/session/new", {}, "A new session is open."));
      kids.push(nw);
    }
    lock.replaceChildren(...kids);
  }
  const panel = $("session-panel");
  const key = JSON.stringify([s.sessions, cur && cur.id]);
  if (panel.hidden || key === state.sessionsKey) return;
  state.sessionsKey = key;
  const rows = s.sessions.map((x) => {
    const isCur = cur && x.id === cur.id;
    const row = el("div", { class: "srow" + (isCur ? " current" : "") },
      el("div", { class: "who" }, el("strong", { text: x.name + (isCur ? "  (this one)" : "") }),
        el("span", { class: "dim small", text: x.modlist + (x.profile ? " · profile " + x.profile : "") + " · started " + x.created.replace("T", " ").slice(0, 16) })),
      el("span", { class: "tag " + (x.status === "active" ? "good" : x.status === "waiting" ? "warn" : ""), text: STATUS_WORDS[x.status] }));
    if (!isCur) {
      const b = el("button", { type: "button", text: x.status === "finished" ? "Look at it" : "Switch to it" });
      b.addEventListener("click", () => sessionCall("/api/session/switch", { id: x.id }));
      row.append(b);
    }
    if (x.status !== "finished") {
      const r = el("button", { type: "button", text: "Rename" });
      r.addEventListener("click", () => {
        const name = window.prompt("A name for this session:", x.name);
        if (name != null && name.trim() && name.trim() !== x.name) sessionCall("/api/session/rename", { id: x.id, name: name }, "Renamed.");
      });
      const f = el("button", { type: "button", text: "Finish", title: "Mark this session finished. ModTrap first checks that nothing of it is still going; the modlist is then free for the session that waits for it." });
      f.addEventListener("click", () => {
        if (window.confirm("Finish session “" + x.name + "”?\n\nModTrap checks that nothing of it is still going. A finished session stays to be looked at, but no more work is done in it; the modlist is then free for the next session.")) sessionCall("/api/session/finish", { id: x.id }, "Session finished.");
      });
      row.append(r, f);
    }
    return row;
  });
  const nw = el("button", { type: "button", class: "primary", text: "New session on this modlist", disabled: !cur });
  nw.addEventListener("click", () => sessionCall("/api/session/new", {}, "A new session is open."));
  panel.replaceChildren(el("h2", { text: "Sessions" }),
    el("p", { class: "dim small", text: "A session is one piece of work on one modlist. It is saved as you go: quit ModTrap and you come back exactly where you were. Only one session at a time works on a modlist; another one on the same modlist waits, locked, until the first is finished. Opening a different modlist starts a session of its own." }),
    ...rows, el("div", { class: "actions" }, nw));
}

async function quitModTrap() {
  let force = false;
  for (;;) {
    try { await api("/api/quit", force ? { force: true } : {}); break; } catch (e) {
      if (force || !window.confirm(e.message + "\n\nQuit anyway?")) return;
      force = true;
    }
  }
  state.quit = true;
  const name = state.session ? state.session.name : "";
  document.body.replaceChildren(el("div", { class: "farewell" }, el("div", {},
    el("h1", { text: "ModTrap has closed" }),
    el("p", { text: (name ? "Session “" + name + "” is saved. " : "") + "Start ModTrap again and you are back exactly where you were: the same modlist, the same ticks, the same tab, the last dry run." }),
    el("p", { text: "You can close this tab." }))));
  window.close();          // works only where the browser allows a page to close its own tab
}

// --- the Mods tab ----------------------------------------------------------------------------------------------------

// The mods are shown as MO2 shows them: lowest priority first, each separator heading the mods that follow it.
function buildGroups() {
  const asc = [...state.mods].reverse();              // the API lists the highest priority first
  const groups = [{ sep: null, mods: [] }];
  for (const m of asc) {
    if (m.kind === "separator") groups.push({ sep: m, mods: [] });
    else groups[groups.length - 1].mods.push(m);
  }
  state.groups = groups.filter((g) => g.sep || g.mods.length);
}

function modRow(m) {
  const can = m.kind === "mod" && m.plugins.length > 0;
  const tick = el("input", { type: "checkbox", disabled: !can, checked: state.picked.has(m.name),
    "aria-label": "Tick " + m.name,
    title: can ? "Tick to see what taking this mod out would involve" : "Nothing to demaster: this mod provides no plugin" });
  tick.addEventListener("change", () => togglePick(m.name, tick.checked));
  const name = el("td", { class: "modname" }, m.name);
  if (m.kind === "foreign") name.append(el("span", { class: "tag", title: "A DLC or Creation Club item MO2 lists but does not manage", text: "not managed by MO2" }));
  if (m.kind === "game") name.replaceChildren("The game's own Data folder");
  if (m.kind === "overwrite") name.replaceChildren("Overwrite");
  if (!m.enabled) name.append(el("span", { class: "tag", text: "disabled" }));
  if (!m.listed) name.append(el("span", { class: "tag warn", text: "not in modlist.txt" }));
  if (m.files > m.plugins.length && m.enabled) name.append(el("span", { class: "tag", title: "Another mod of higher priority provides a plugin of the same name", text: (m.files - m.plugins.length) + " plugin file(s) overridden" }));
  const plugs = el("td", { class: "plugs" });
  m.plugins.slice(0, 4).forEach((p, i) => {
    if (i) plugs.append(", ");
    const a = el("button", { type: "button", class: "linkish", text: p, title: "Show this plugin's masters and what needs it" });
    a.addEventListener("click", (ev) => { ev.stopPropagation(); gotoPlugin(p); });
    plugs.append(a);
  });
  if (m.plugins.length > 4) plugs.append(" … +" + (m.plugins.length - 4));
  const tr = el("tr", { class: (m.enabled ? "" : "off") + (state.picked.has(m.name) ? " picked" : "") + (can ? " tickable" : "") },
    el("td", { class: "c-tick" }, tick), el("td", { class: "c-num", text: m.priority < 0 ? "" : m.priority }), name, plugs,
    el("td", { class: "c-num" + (m.dependants ? " badnum" : ""), text: m.plugins.length ? m.dependants : "" }));
  if (can) tr.addEventListener("click", (ev) => {
    if (ev.target.closest("input, button, a")) return;
    togglePick(m.name, !state.picked.has(m.name));
  });
  tr.dataset.name = m.name;
  m.row = tr;
  m.hay = fold(m.name + " " + m.plugins.join(" "));
}

function groupRow(g) {
  const arrow = el("span", { class: "arrow", text: "▾" });
  const info = el("span", { class: "dim ginfo" });
  const btn = el("button", { type: "button", class: "gtoggle", "aria-expanded": "true" }, arrow, g.sep.name.replace(/_separator$/i, ""));
  const tr = el("tr", { class: "sep" }, el("td", { colSpan: 5 }, btn, info));
  btn.addEventListener("click", () => {
    if (state.collapsed.has(g.sep.name)) state.collapsed.delete(g.sep.name); else state.collapsed.add(g.sep.name);
    filterMods();
  });
  g.row = tr; g.arrow = arrow; g.info = info; g.btn = btn;
}

function renderMods() {
  state.collapsed = state.collapsed || new Set();
  buildGroups();
  for (const g of state.groups) {
    if (g.sep) groupRow(g);
    g.mods.forEach(modRow);
  }
  layoutMods();
}

function layoutMods() {
  const order = $("mods-order").value;
  const frag = document.createDocumentFragment();
  state.grouped = order !== "deps";
  if (order === "deps") {
    const flat = state.groups.flatMap((g) => g.mods).filter((m) => m.kind === "mod" && m.plugins.length);
    flat.sort((a, b) => b.dependants - a.dependants || a.priority - b.priority);
    flat.forEach((m) => frag.append(m.row));
    state.flat = new Set(flat);
  } else {
    const groups = order === "rev" ? [...state.groups].reverse() : state.groups;
    for (const g of groups) {
      if (g.sep) frag.append(g.row);
      (order === "rev" ? [...g.mods].reverse() : g.mods).forEach((m) => frag.append(m.row));
    }
    state.flat = null;
  }
  $("mods-table").tBodies[0].replaceChildren(frag);
  $("collapse-all").disabled = $("expand-all").disabled = !state.grouped;
  filterMods();
}

function filterMods() {
  const q = fold($("mods-search").value.trim());
  const en = $("f-enabled").checked, pl = $("f-plugins").checked, dp = $("f-deps").checked;
  const filtering = !!(q || en || pl || dp);
  let shown = 0, total = 0;
  for (const g of state.groups) {
    const folded = state.grouped && g.sep && state.collapsed.has(g.sep.name) && !filtering;
    let match = 0, ticked = 0;
    for (const m of g.mods) {
      total++;
      const ok = (!q || m.hay.includes(q)) && (!en || m.enabled) && (!pl || m.plugins.length > 0) && (!dp || m.dependants > 0) &&
        (state.grouped || state.flat.has(m));
      if (ok) { match++; shown++; }
      if (state.picked.has(m.name)) ticked++;
      m.row.hidden = !ok || folded;
    }
    if (g.sep) {
      g.row.hidden = !state.grouped || (filtering && !match);
      g.arrow.textContent = folded ? "▸" : "▾";
      g.btn.setAttribute("aria-expanded", folded ? "false" : "true");
      g.info.textContent = (filtering ? match + " of " + g.mods.length + " shown" : plural(g.mods.length, "mod")) +
        (ticked ? " · " + ticked + " ticked" : "");
    }
  }
  saveUi();
  $("mods-shown").textContent = filtering || !state.grouped ? shown + " of " + total + " shown" : total + " entries in " + plural(state.groups.filter((g) => g.sep).length, "group");
  $("mods-empty").hidden = shown > 0;
}

function clearModFilters() {
  $("mods-search").value = "";
  for (const id of ["f-enabled", "f-plugins", "f-deps"]) $(id).checked = false;
  filterMods();
}

function findMod(name) {
  for (const g of state.groups || []) for (const m of g.mods) if (m.name === name) return m;
  return null;
}

function flash(row) {
  row.scrollIntoView({ block: "center" });
  row.classList.add("flash");
  setTimeout(() => row.classList.remove("flash"), 1600);
}

function gotoMod(name) {
  const m = findMod(name);
  if (!m) return;
  showTab("mods");
  clearModFilters();
  if ($("mods-order").value === "deps") { $("mods-order").value = "mo2"; layoutMods(); }
  const g = state.groups.find((x) => x.mods.includes(m));
  if (g && g.sep && state.collapsed.delete(g.sep.name)) filterMods();
  flash(m.row);
}

function updateTray() {
  const n = state.picked.size;
  const tab = state.tab || "mods";
  $("tray").hidden = !n || tab === "selection" || tab === "job" || tab === "steps";
  const names = [...state.picked];
  $("tray-review").textContent = n === 1 ? "See what depends on it" : "See what depends on them";
  $("tray-text").textContent = plural(n, "mod") + " ticked: " + names.slice(0, 3).join(", ") + (n > 3 ? " and " + (n - 3) + " more" : "");
}

function togglePick(name, on) {
  if (on) state.picked.add(name); else { state.picked.delete(name); state.details.delete(name); }
  const m = findMod(name);
  if (m && m.row) {
    m.row.classList.toggle("picked", on);
    const box = m.row.querySelector("input");
    if (box) box.checked = on;
  }
  $("sel-count").textContent = state.picked.size;
  $("sel-count").classList.toggle("on", state.picked.size > 0);
  updateDryButton();
  $("plan").hidden = true;
  if (state.groups) filterMods();
  saveUi();
  updateTray();
  renderSteps();
  renderSelection();
}

// --- the Plugins tab -------------------------------------------------------------------------------------------------

function renderPlugins() {
  const body = $("plugins-table").tBodies[0];
  const frag = document.createDocumentFragment();
  for (const p of state.plugins) {
    const name = el("td", {}, p.name);
    if (!p.active) name.append(el("span", { class: "tag", text: "not active" }));
    if (p.primary) name.append(el("span", { class: "tag", text: "game" }));
    if (p.unreadable) name.append(el("span", { class: "tag bad", text: p.mod ? "unreadable" : "no file" }));
    if (p.missing.length) name.append(el("span", { class: "tag bad", text: plural(p.missing.length, "missing master") }));
    if (p.inactive.length) name.append(el("span", { class: "tag warn", text: plural(p.inactive.length, "inactive master") }));
    const mod = p.mod === "<game>" ? "the game" : p.mod === "<overwrite>" ? "Overwrite" : p.mod;
    const tr = el("tr", { class: "clickable" + (p.active ? "" : " off") },
      el("td", { class: "c-num", text: p.position == null ? "" : p.position }), name, el("td", { text: p.kind }),
      el("td", { text: mod }), el("td", { class: "c-num", text: p.mod_priority == null || p.mod_priority < 0 ? "" : p.mod_priority }),
      el("td", { class: "c-num", text: p.masters }), el("td", { class: "c-num" + (p.dependants ? " badnum" : ""), text: p.dependants }));
    tr.addEventListener("click", () => showPlugin(p.name, tr));
    p.row = tr;
    p.hay = fold(p.name + " " + p.mod);
    frag.append(tr);
  }
  body.replaceChildren(frag);
  filterPlugins();
}

function filterPlugins() {
  const q = fold($("plugins-search").value.trim());
  const pr = $("p-problems").checked, dp = $("p-deps").checked;
  let shown = 0;
  for (const p of state.plugins) {
    const ok = (!q || p.hay.includes(q)) && (!pr || p.missing.length || p.inactive.length || p.unreadable) && (!dp || p.dependants > 0);
    p.row.hidden = !ok;
    if (ok) shown++;
  }
  $("plugins-shown").textContent = (q || pr || dp) ? shown + " of " + state.plugins.length + " shown" : state.plugins.length + " plugins";
  $("plugins-empty").hidden = shown > 0;
  saveUi();
}

function clearPluginFilters() {
  $("plugins-search").value = "";
  $("p-problems").checked = $("p-deps").checked = false;
  filterPlugins();
}

function gotoPlugin(name) {
  const p = state.plugins.find((x) => fold(x.name) === fold(name));
  if (!p) { toast(name + " is not in this profile's load order."); return; }
  showTab("plugins");
  if (p.row.hidden) clearPluginFilters();
  flash(p.row);
  showPlugin(p.name, p.row);
}

function pluginLink(name) {
  const b = el("button", { type: "button", class: "linkish mono", text: name, title: "Show this plugin" });
  b.addEventListener("click", () => gotoPlugin(name));
  return b;
}

function modLink(name, text) {
  if (!findMod(name)) return el("span", { text: text || name });
  const b = el("button", { type: "button", class: "linkish", text: text || name, title: "Show this mod in the Mods tab" });
  b.addEventListener("click", () => gotoMod(name));
  return b;
}

async function showPlugin(name, tr) {
  document.querySelectorAll("#plugins-table tr.picked").forEach((r) => r.classList.remove("picked"));
  if (tr) tr.classList.add("picked");
  state.plugin = name;
  saveUi();
  const box = $("plugin-detail");
  let p;
  try { p = await api("/api/plugin?name=" + encodeURIComponent(name)); } catch (e) { box.replaceChildren(el("p", { class: "dim", text: e.message })); return; }
  const list = (title, items, mark) => [el("h3", { text: title + " (" + items.length + ")" }),
    items.length ? el("ul", {}, ...items.map((i) => {
      const li = el("li", {}, pluginLink(i));
      if (mark && mark.missing.includes(i)) li.append(el("span", { class: "tag bad", text: "missing" }));
      if (mark && mark.inactive.includes(i)) li.append(el("span", { class: "tag warn", text: "not active" }));
      return li;
    })) : el("p", { class: "dim", text: "none" })];
  const where = p.mod === "<game>" ? ["the game's Data folder"] : p.mod === "<overwrite>" ? ["Overwrite"]
    : p.mod ? ["mod ", modLink(p.mod, "“" + p.mod + "”"), ", priority " + p.mod_priority] : ["no enabled mod"];
  box.replaceChildren(...[el("h2", { class: "mono", text: p.name }),
    el("p", { class: "dim" }, "Position " + (p.position == null ? "none" : p.position) + " · " + (p.kind || "kind unknown") + " · " +
      (p.active ? "active" : "not active") + " · in ", ...where),
    p.unreadable ? el("p", { class: "message bad", text: "Could not be read: " + p.unreadable }) : null,
    p.also_in.length ? el("p", { class: "dim", text: "Also in, and overridden: " + p.also_in.join(", ") }) : null,
    p.author ? el("p", { class: "dim", text: "Author field: " + p.author }) : null,
    ...list("Masters", p.masters, p), ...list("Needed by", p.dependants)].filter(Boolean));
}

// --- the Selection tab -----------------------------------------------------------------------------------------------

const READING = {
  "whole mod": ["every plugin of this mod depends on it", "Either a patch made only for it (to be disabled), or a mod of its own that needs demastering. The dry run through xEdit will tell which."],
  "most of the mod": ["most of this mod depends on it", "Probably a set of patches for it: ModTrap would propose disabling the whole mod, for you to judge."],
  "some plugins": ["one of several plugins in this mod", "A patch inside a collection: ModTrap would switch off or demaster just these plugins, never the whole mod."],
  "output": ["made by a tool", "A generated or tool-written plugin: to be rebuilt with its tool, or demastered if it came from an editor."],
};

async function renderSelection() {
  const box = $("selection");
  if (!state.picked.size) {
    const go = el("button", { type: "button", text: "Go to the Mods tab" });
    go.addEventListener("click", () => showTab("mods"));
    box.replaceChildren(el("div", { class: "card" }, el("h2", { text: "Nothing is ticked yet" }),
      el("p", { class: "dim", text: "Tick the mods you want to take out on the Mods tab. This tab then shows every plugin that depends on them, and from here you start the dry run. Tip: “Has dependants” on the Mods tab shows the mods that cannot simply be disabled." }), go));
    return;
  }
  const cards = [];
  for (const name of state.picked) {
    let d = state.details.get(name);
    if (!d) {
      try { d = await api("/api/mod?name=" + encodeURIComponent(name)); } catch (e) { d = { name, error: e.message }; }
      state.details.set(name, d);
    }
    if (!state.picked.has(name)) continue;
    const card = el("div", { class: "card" });
    const un = el("button", { text: "Untick" });
    un.addEventListener("click", () => togglePick(name, false));
    card.append(el("div", { class: "card-head" }, el("h2", {}, modLink(d.name)), un));
    if (d.error) { card.append(el("p", { class: "message bad", text: d.error })); cards.push(card); continue; }
    const n = d.groups.reduce((a, g) => a + g.plugins.length, 0);
    card.append(el("p", { class: "dim" }, "Priority " + d.priority + " · " + (d.enabled ? "enabled" : "disabled") + " · provides ",
      ...d.plugins.flatMap((p, i) => [i ? ", " : "", pluginLink(p.name), " (position " + p.position + ", " + p.kind + ")"])));
    card.append(el("p", { text: n ? plural(n, "plugin") + " in " + plural(d.groups.length, "other mod") + " list it as a master. Disabling it now would leave them with a missing master."
      : "Nothing depends on this mod's plugins: it can be disabled in MO2 as it is." }));
    for (const g of d.groups) {
      const [label, hint] = READING[g.reading];
      const head = el("div", { class: "head" }, el("strong", {}, modLink(g.mod)), el("span", { class: "dim", text: "priority " + g.priority }),
        el("span", { class: "tag " + (g.reading === "output" ? "warn" : ""), text: g.reading === "output" ? "made by " + g.made_by.join(", ") : label,
          title: g.reading === "output" ? [...new Set(g.evidence.map((e) => e.tool + ": " + e.how + (e.strong ? "" : " (weak evidence)")))].join("\n") : "" }));
      if (g.reading === "output" && g.proposal) head.append(el("span", { class: "dim", text: g.proposal === "demaster" ? "written through an editor: it would be demastered" : "would be rebuilt: " + g.proposal }));
      if (g.reading === "some plugins") head.append(el("span", { class: "dim", text: g.others + " other plugin(s) here do not depend on it" }));
      if (g.reading === "most of the mod") head.append(el("span", { class: "dim", text: "the rest: " + g.leftover.join(", ") }));
      card.append(el("div", { class: "group" }, head, el("div", { class: "dim", text: hint }),
        el("ul", {}, ...g.plugins.map((p) => el("li", {}, pluginLink(p.name),
          el("span", { class: "dim", text: "  position " + p.position + " · " + p.kind + " · " + plural(p.masters, "master") }))))));
    }
    cards.push(card);
  }
  box.replaceChildren(...cards);
}

// --- the dry run (DESIGN§6.1, DESIGN§6.2) ---------------------------------------------------------------------------

const JOB_WORDS = {
  preparing: "Preparing", starting: "Starting xEdit through MO2", loading: "xEdit is loading the plugins",
  reading: "xEdit is reading the dependants", checking: "Checking the result", done: "Dry run done",
  failed: "The dry run failed", stopped: "Stopped",
};
const WOULD = {
  "record": ["would be taken out", "would-record", "The dependant's own copy of one of the trapped mod's records."],
  "entry": ["entry would be taken out", "would-entry", "An entry of a list that can be shortened; the record stays."],
  "needs you": ["needs you", "would-needs", "ModTrap would not change this by itself."],
};
const FILE_READING = {
  "patch only": ["patch only: would be switched off", "good", "Every record in it belongs to the trapped mod: nothing of it would remain."],
  "can be demastered": ["can be demastered", "good", "Everything in it that needs the trapped mod can be taken out automatically."],
  "needs you": ["needs you", "warn", "Some of what needs the trapped mod is not something ModTrap takes out by itself."],
  "not finished": ["not read to the end", "bad", ""],
};

async function showPlan() {
  const box = $("plan");
  let p;
  try { p = await api("/api/dryrun/plan", { mods: [...state.picked] }); } catch (e) {
    box.hidden = false;
    box.replaceChildren(el("div", { class: "card" }, el("p", { class: "message bad", text: e.message })));
    return;
  }
  const start = el("button", { class: "go", text: "Start the dry run" });
  const cancel = el("button", { text: "Cancel" });
  cancel.addEventListener("click", () => { box.hidden = true; });
  start.addEventListener("click", async () => {
    start.disabled = true;
    try { await api("/api/dryrun/start", { mods: [...state.picked] }); box.hidden = true; state.jobSeen = ""; showTab("job"); tick(); }
    catch (e) { start.disabled = false; box.append(el("p", { class: "message bad", text: e.message })); }
  });
  box.hidden = false;
  box.replaceChildren(el("div", { class: "card" },
    el("h2", { text: "The plan for this dry run" }),
    el("dl", { class: "kv" },
      el("dt", { text: "Trapped" }), el("dd", { class: "mono", text: p.trapped.join(", ") }),
      el("dt", { text: "Dependants to read" }), el("dd", {}, plural(p.dependants.length, "plugin") + ": ", el("span", { class: "mono", text: p.dependants.join(", ") })),
      el("dt", { text: "xEdit will load" }), el("dd", { text: plural(p.load, "plugin") + ": the dependants and every master under them, nothing else" }),
      el("dt", { text: "Started as" }), el("dd", { text: "“" + p.tool + "” (" + p.tool_file + ") through MO2, profile “" + p.profile + "”, with ModTrap's own script in report mode" })),
    el("p", { text: "What will happen: xEdit's window opens, loads those plugins, runs the script and closes by itself. The script only reads. Before it starts, ModTrap copies every dependant into its own safe folder and records its checksum; afterwards it checks that each is still exactly that file." }),
    el("p", { class: "dim", text: "MO2 may be open or closed. If xEdit is already open, close it first. Loading can take several minutes; the Dry run tab shows the progress." }),
    ...p.warnings.map((w) => el("p", { class: "message", text: w })),
    el("div", { class: "actions" }, start, cancel)));
}

function renderJob(job) {
  const badge = $("job-badge");
  if (!job) { badge.hidden = true; return; }
  const active = !["done", "failed", "stopped"].includes(job.state);
  badge.hidden = false;
  badge.textContent = active ? "…" : job.state === "done" ? "✓" : "!";
  badge.className = "count " + (active ? "run" : job.state === "done" ? "ok" : "bad");
  $("job-state").textContent = JOB_WORDS[job.state] || job.state;
  const mins = Math.floor(job.seconds / 60), secs = job.seconds % 60;
  $("job-info").textContent = job.plan.trapped.join(", ") + " · " + plural(job.plan.dependants.length, "dependant") + " · " +
    (mins ? mins + " min " : "") + secs + " s" + (job.unchanged === true ? " · every dependant is unchanged on disk" : "");
  $("job-stop").hidden = !active;
  updateDryButton();
  const key = job.id + "|" + job.state;
  if (key === state.jobSeen) return;
  state.jobSeen = key;
  const box = $("job-result");
  const parts = [];
  if (job.message) parts.push(el("p", { class: "message " + (job.state === "failed" ? "bad" : ""), text: job.message }));
  if (!active) parts.push(el("p", { class: "dim" }, "This run's files (the report, xEdit's own log, the copies of the dependants): ", el("span", { class: "mono", text: job.folder })));
  if (active) parts.push(el("p", { class: "dim", text: "Watch xEdit's own window and the lines on the right. Nothing is being changed." }));
  const r = job.result;
  if (r && r.files.length) {
    const n = (k) => r.files.filter((f) => f.reading === k).length;
    const bits = [[n("can be demastered"), "can be demastered automatically", "good"], [n("patch only"), "patch only: would be switched off", "good"],
      [n("needs you"), "need you", "warn"], [n("not finished"), "not read to the end", "bad"]].filter((b) => b[0]);
    const all = el("button", { type: "button", text: "Show every record" });
    all.addEventListener("click", () => {
      const ds = [...box.querySelectorAll("details")];
      const open = ds.some((d) => !d.open);
      ds.forEach((d) => { d.open = open; });
      all.textContent = open ? "Hide the records" : "Show every record";
    });
    parts.push(el("div", { class: "card summary-card" }, el("h2", { text: "Of " + plural(r.files.length, "dependant") + ":" }),
      el("div", { class: "summary" }, ...bits.map((b) => el("span", { class: "chip " + b[2], text: b[0] + " " + b[1] }))),
      el("p", { class: "dim", text: "Nothing was changed: this is what a demaster would do. “Needs you” means ModTrap would leave that plugin alone and tell you what to look at." }), all));
  }
  if (r) {
    if (r.not_loaded.length) parts.push(el("p", { class: "message bad", text: "xEdit did not load: " + r.not_loaded.join(", ") }));
    if (r.held_changed.length) parts.push(el("p", { class: "message", text: "xEdit held these as changed although the script changed nothing; the marks were cleared and the files are unchanged on disk: " + r.held_changed.join(", ") }));
    for (const f of r.files) {
      const [label, cls, hint] = FILE_READING[f.reading] || [f.reading, "", ""];
      const card = el("div", { class: "card" },
        el("div", { class: "card-head" }, el("h2", { class: "mono", text: f.name }), el("span", { class: "tag " + cls, text: label })),
        el("p", { class: "dim", text: hint }),
        el("p", { text: f.records + " records; " + f.needing + " need the trapped mod: " + f.own + " of its own records, " +
          plural(f.entries, "list entry", "list entries") + ", " + f.needs_you + " that need you." }));
      const shown = f.items.slice(0, 400);
      const list = el("ul");
      for (const it of shown) {
        const [w, wc, wh] = WOULD[it.would];
        const li = el("li", {}, el("span", { class: "mono", text: it.signature + " " + it.form + (it.editor_id ? " " + it.editor_id : "") }),
          el("span", { class: "tag " + wc, title: wh, text: w }));
        if (!it.own && it.elements.length) {
          li.append(el("ul", {}, ...it.elements.slice(0, 40).map((e) => el("li", { class: "mono dim",
            text: (e.kind === "entry" ? "entry of " + e.array + " (" + e.array_length + " long)" : "field " + e.path) + " → " + e.target_file + " " + e.target_form }))));
        }
        list.append(li);
      }
      const det = el("details", {}, el("summary", { text: "Show the " + plural(f.items.length, "record") }), list);
      if (f.items.length > shown.length) det.append(el("p", { class: "dim", text: "Showing the first " + shown.length + "; the full report is in the job's folder." }));
      if (f.items.length) card.append(det);
      parts.push(card);
    }
  }
  box.replaceChildren(...parts);
}

async function pollJob() {
  try { const d = await api("/api/job"); state.job = d.job; renderJob(d.job); renderSteps(); } catch (e) { /* next round */ }
}

// --- the Steps tab (DESIGN§14) --------------------------------------------------------------------------------------

const STEP_STATE = {
  "done": ["done", "good"], "not needed": ["not needed", "good"], "to do": ["to do", ""], "going": ["going…", "warn"],
  "waiting": ["waits for the steps above", ""], "waiting for the dry run": ["waits for the dry run", ""],
};

function stepKey(k) { return [...state.picked].sort().join("|") + "::" + k; }

function stepItem(it) {
  if (it.tool) return el("li", { text: "“" + it.tool + "” in MO2's list of tools" });
  if (it.file) return el("li", {}, modLink(it.mod), ": ", el("span", { class: "mono", text: it.file }), el("span", { class: "dim", text: "  names " + it.names.join(", ") }));
  if (it.master) return el("li", {}, pluginLink(it.plugin), " needs ", el("span", { class: "mono", text: it.master }),
    el("span", { class: "tag " + (it.what === "missing" ? "bad" : "warn"), text: it.what === "missing" ? "missing" : "not active" }));
  if (it.plugin) {
    const li = el("li", {}, pluginLink(it.plugin), el("span", { class: "dim", text: "  position " + it.position + ", in " }), modLink(it.mod));
    if (it.made_by && it.made_by.length) li.append(el("span", { class: "tag warn", title: it.how || "", text: "made by " + it.made_by.join(", ") }));
    if (it.verdict) li.append(el("span", { class: "tag " + (it.verdict === "needs you" ? "warn" : "good"), text: it.verdict }),
      el("span", { class: "dim", text: "  " + it.own + " of the mod's own records, " + it.entries + " list entries, " + it.needs_you + " that need you" }));
    return li;
  }
  const li = el("li", {}, modLink(it.mod), it.priority == null ? null : el("span", { class: "dim", text: "  priority " + it.priority }),
    el("span", { class: "tag " + (it.enabled ? "" : "good"), text: it.enabled ? "enabled" : "disabled" }));
  if (it.why && it.why !== "ticked") li.append(el("span", { class: "dim", text: "  " + it.why }));
  return li;
}

function renderSteps2(d) {
  const done = state.stepsDone || {};
  let open = 0;
  const cards = d.steps.map((st) => {
    const ticked = st.manual && !!done[stepKey(st.key)];
    const isDone = ticked || st.state === "done" || st.state === "not needed";
    const waiting = !isDone && st.state.startsWith("waiting");
    if (!isDone) open++;
    const [word, cls] = ticked ? ["ticked off by you", "good"] : STEP_STATE[st.state] || [st.state, ""];
    const body = el("div", {},
      el("h3", {}, st.title, el("span", { class: "who" + (st.who === "you" ? " you" : ""), text: st.who === "you" ? "You" : "ModTrap" }),
        el("span", { class: "tag " + cls, text: word })),
      el("p", { class: "dim", text: st.why }),
      st.note ? el("p", { text: st.note }) : null,
      st.items.length ? el("ul", {}, ...st.items.slice(0, 200).map(stepItem)) : null,
      st.items.length > 200 ? el("p", { class: "dim", text: "Showing the first 200 of " + st.items.length + "." }) : null);
    if (st.manual) {
      const box = el("input", { type: "checkbox", checked: ticked });
      box.addEventListener("change", () => {
        state.stepsDone = state.stepsDone || {};
        if (box.checked) state.stepsDone[stepKey(st.key)] = true; else delete state.stepsDone[stepKey(st.key)];
        saveUi();
        renderSteps2(d);
      });
      body.append(el("label", { class: "tickoff" }, box, "I have done this"));
    }
    return el("div", { class: "step " + (isDone ? "done" : waiting ? "waiting" : "todo") }, el("div", { class: "num", text: isDone ? "✓" : st.n }), body);
  });
  const box = $("steps-list");
  const badge = $("steps-count");
  if (!d.steps.length) {
    badge.hidden = true;
    $("steps-summary").textContent = "Steps";
    $("steps-info").textContent = "";
    box.replaceChildren(el("div", { class: "card" }, el("h2", { text: "No mod is ticked" }),
      el("p", { class: "dim", text: "Tick the mods you want to take out on the Mods tab. This tab then lists every step that takes: what ModTrap does, what is yours to do, and which steps the modlist's own files already show as done." })));
    return;
  }
  badge.hidden = false;
  badge.textContent = open ? open : "✓";
  badge.className = "count " + (open ? "todo" : "ok");
  $("steps-summary").textContent = open ? plural(open, "step") + " to go" : "Every step is done";
  const carries = Object.entries(d.contents || {}).filter(([k]) => k !== "other files").map(([k, n]) => n + " " + k);
  $("steps-info").textContent = "Taking out " + d.mods.join(", ") + (d.looking ? " · still looking into the mods' folders…" : carries.length ? " · besides plugins it carries: " + carries.join(", ") : "");
  const intro = el("div", { class: "card" },
    el("p", { text: "Everything it takes to get " + (d.mods.length === 1 ? "this mod" : "these mods") + " out of the modlist, in order. ModTrap cannot change your modlist yet, so the steps marked “You” are done by hand in MO2 and xEdit for now; ModTrap checks them against the modlist's files each time it is read." }),
    el("p", { class: "dim", text: "Plugins to take out: " + d.trapped.join(", ") }));
  box.replaceChildren(intro, ...cards);
}

async function pollSteps(force) {
  if (state.status !== "ready") return;
  const mods = [...state.picked];
  const key = mods.slice().sort().join("|") + "#" + state.loaded + "#" + (state.job ? state.job.id + state.job.state : "");
  if (!force && key === state.stepsKey && !state.stepsLooking && state.tab !== "steps") return;
  try {
    const d = await api("/api/steps", { mods: mods });
    state.stepsKey = key;
    state.stepsLooking = d.looking;
    const text = JSON.stringify(d);
    if (text !== state.stepsText) { state.stepsText = text; renderSteps2(d); }
  } catch (e) { /* the next round tries again */ }
}

// --- tabs, the log, and the loop -------------------------------------------------------------------------------------

function showTab(name) {
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
  document.querySelectorAll(".tab").forEach((t) => { t.hidden = t.id !== "tab-" + name; });
  state.tab = name;
  updateTray();
  saveUi();
}

async function pollLog() {
  try {
    const d = await api("/api/log?after=" + state.logAfter);
    if (d.lines.length) {
      const log = $("log");
      const atEnd = log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
      const jl = $("job-log");
      const jAtEnd = jl.scrollTop + jl.clientHeight >= jl.scrollHeight - 30;
      for (const ln of d.lines) {
        log.append(el("span", { class: ln.level, text: ln.t + "  " + ln.text + "\n" }));
        if (ln.source === "dryrun") jl.append(el("span", { class: ln.level, text: ln.t + "  " + ln.text + "\n" }));
        state.logAfter = ln.seq;
      }
      if (atEnd) log.scrollTop = log.scrollHeight;
      if (jAtEnd) jl.scrollTop = jl.scrollHeight;
    }
  } catch (e) { /* the next round tries again */ }
}

async function loadLists(key, s) {
  const [m, p] = await Promise.all([api("/api/mods"), api("/api/plugins")]);
  state.mods = m.mods;
  state.plugins = p.plugins;
  state.details.clear();
  state.loaded = key;
  const keep = currentUi();                       // a rescan of the same session keeps the page as it is
  renderMods();
  renderPlugins();
  const sid = s.session ? s.session.id : "";
  const fresh = sid !== state.sessionApplied;
  state.sessionApplied = sid;
  applyUi(fresh ? (s.session && s.session.ui) || {} : keep);
}

async function tick() {
  if (state.quit) return;
  let s;
  try { s = await api("/api/state"); } catch (e) { showMessage("ModTrap is not answering: " + e.message, true); return; }
  const was = state.status;
  state.status = s.status;
  renderState(s);
  if (s.log_epoch !== state.logEpoch) {             // another session's log: read it from the start
    state.logEpoch = s.log_epoch;
    state.logAfter = 0;
    state.jobSeen = "";
    $("log").replaceChildren();
    $("job-log").replaceChildren();
  }
  const key = s.status === "ready" ? (s.session ? s.session.id : "") + "|" + s.folder + "|" + s.profile + "|" + s.mods + "|" + s.plugins + "|" + s.issue_count + "|" + (state.gen || 0) : "";
  if (s.status === "ready" && (key !== state.loaded || was !== "ready")) {
    try { await loadLists(key, s); } catch (e) { showMessage(e.message, true); }
  }
  updateDryButton();
  await pollJob();
  await pollSteps(false);
  await pollLog();
}

function loop() {
  if (state.quit) return;
  const busy = state.status === "reading" || (state.job && !["done", "failed", "stopped"].includes(state.job.state));
  tick().finally(() => setTimeout(loop, busy ? 800 : 2500));
}

async function openFolder(folder, profile) {
  state.sticky = "";
  try {
    state.gen = (state.gen || 0) + 1;
    await api("/api/open", { folder: folder, profile: profile || null });
    state.status = "reading";
  } catch (e) { problem(e.message); }
  tick();
}

$("open-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const folder = $("folder").value.trim().replace(/^"|"$/g, "");
  if (!folder) {
    problem("The box is empty. Paste the modlist folder's path into it (in Explorer, click the address bar and copy it), or drag the folder onto this page.");
    $("folder").focus();
    return;
  }
  const sel = $("profile");
  openFolder(folder, sel.hidden ? null : sel.value);
});

// --- dropping the modlist folder (WHY§30) ---------------------------------------------------------------------------

function toBase64(buf) {
  const u = new Uint8Array(buf);
  let s = "";
  for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
  return btoa(s);
}

async function giveIni(name, file) {
  if (file.size > 2 * 1024 * 1024) { problem("That ModOrganizer.ini is larger than ModTrap reads."); return; }
  showMessage("Finding " + (name ? "“" + name + "”" : "that modlist") + " on this PC…");
  state.sticky = "";
  try {
    const buf = await file.arrayBuffer();
    state.gen = (state.gen || 0) + 1;
    await api("/api/locate", { name: name, ini: toBase64(buf) });
    $("folder").value = "";
    state.status = "reading";
  } catch (e) { problem(e.message); }
  tick();
}

function dropped(ev) {
  const dt = ev.dataTransfer;
  if (!dt) return;
  // The entries must be taken while the drop event is still being handled.
  const items = dt.items ? Array.from(dt.items).filter((i) => i.kind === "file") : [];
  const entry = items.length && items[0].webkitGetAsEntry ? items[0].webkitGetAsEntry() : null;
  if (entry && entry.isDirectory) {
    entry.getFile("ModOrganizer.ini", {}, (fe) => fe.file((f) => giveIni(entry.name, f), () => problem("ModOrganizer.ini in that folder could not be read.")),
      () => problem("There is no ModOrganizer.ini in “" + entry.name + "”. Drop the modlist's own folder: the one with ModOrganizer.exe in it."));
    return;
  }
  if (entry && entry.isFile) {
    if (/^modorganizer\.ini$/i.test(entry.name)) { entry.file((f) => giveIni(null, f), () => problem("That file could not be read.")); return; }
    problem("Drop the modlist's folder itself (the one with ModOrganizer.exe in it), not a file from it. A page cannot tell where a dropped file lives.");
    return;
  }
  const text = (dt.getData && dt.getData("text/plain") || "").trim();
  if (text && text.length < 1000 && !text.includes("\n")) { $("folder").value = text; openFolder(text, null); return; }
  problem("That could not be used. Drop the modlist's folder, or paste its path into the box.");
}

let dragDepth = 0;
const dragOn = (yes) => document.body.classList.toggle("dragging", yes);
document.addEventListener("dragenter", (e) => { e.preventDefault(); dragDepth++; dragOn(true); });
document.addEventListener("dragover", (e) => { e.preventDefault(); if (e.dataTransfer) e.dataTransfer.dropEffect = "copy"; });
document.addEventListener("dragleave", () => { dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) dragOn(false); });
document.addEventListener("drop", (e) => { e.preventDefault(); dragDepth = 0; dragOn(false); dropped(e); });

$("profile").addEventListener("change", () => $("open-form").requestSubmit());
$("rescan").addEventListener("click", async () => {
  try { state.gen = (state.gen || 0) + 1; await api("/api/rescan", {}); state.status = "reading"; } catch (e) { problem(e.message); }
  tick();
});
document.querySelectorAll("#tabs button").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
$("dry-run").addEventListener("click", showPlan);
$("job-stop").addEventListener("click", async () => {
  if (!window.confirm("Stop waiting for this dry run? xEdit itself stays open for you to close; it has changed nothing.")) return;
  try { await api("/api/job/stop", {}); } catch (e) { problem(e.message); }
  tick();
});
$("quit").addEventListener("click", quitModTrap);
$("steps-rescan").addEventListener("click", () => $("rescan").click());
$("session-btn").addEventListener("click", () => {
  const panel = $("session-panel");
  panel.hidden = !panel.hidden;
  $("session-btn").setAttribute("aria-expanded", panel.hidden ? "false" : "true");
  state.sessionsKey = "";
  tick();
});
document.addEventListener("click", (ev) => {
  const panel = $("session-panel");
  if (!panel.hidden && !ev.target.closest("#session-panel, #session-btn")) { panel.hidden = true; $("session-btn").setAttribute("aria-expanded", "false"); }
});
$("mods-order").addEventListener("change", layoutMods);
$("collapse-all").addEventListener("click", () => { for (const g of state.groups) if (g.sep) state.collapsed.add(g.sep.name); filterMods(); });
$("expand-all").addEventListener("click", () => { state.collapsed.clear(); filterMods(); });
$("mods-clear").addEventListener("click", clearModFilters);
$("plugins-clear").addEventListener("click", clearPluginFilters);
$("tray-review").addEventListener("click", () => showTab("selection"));
$("tray-clear").addEventListener("click", () => { for (const n of [...state.picked]) togglePick(n, false); });
$("s-health").addEventListener("click", () => showTab("health"));
$("s-tools").addEventListener("click", () => showTab("tools"));
for (const li of $("steps").children) li.addEventListener("click", () => { if (li.dataset.tab) showTab(li.dataset.tab); });
$("log-copy").addEventListener("click", () => copyText($("log").textContent, "The log"));
$("job-copy").addEventListener("click", () => copyText($("job-log").textContent, "The dry run's lines"));
document.addEventListener("keydown", (ev) => {
  const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
  const box = state.tab === "plugins" ? $("plugins-search") : state.tab === "mods" ? $("mods-search") : null;
  if (ev.key === "/" && !typing && box && !$("tabs").hidden) { ev.preventDefault(); box.focus(); box.select(); }
  if (ev.key === "Escape" && !$("session-panel").hidden) { $("session-panel").hidden = true; $("session-btn").setAttribute("aria-expanded", "false"); $("session-btn").focus(); }
  if (ev.key === "Escape" && document.activeElement === box && box.value) { box.value = ""; (state.tab === "plugins" ? filterPlugins : filterMods)(); }
});
let debounce;
const later = (fn) => () => { clearTimeout(debounce); debounce = setTimeout(fn, 120); };
$("mods-search").addEventListener("input", later(filterMods));
$("plugins-search").addEventListener("input", later(filterPlugins));
for (const id of ["f-enabled", "f-plugins", "f-deps"]) $(id).addEventListener("change", filterMods);
for (const id of ["p-problems", "p-deps"]) $(id).addEventListener("change", filterPlugins);
loop();
