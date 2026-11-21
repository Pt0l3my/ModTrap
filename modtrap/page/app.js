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
    adding: [...(state.adding || [])], staged: [...(state.staged || [])],
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
    state.adding = (Array.isArray(ui.adding) ? ui.adding : []).filter((n) => { const m = findMod(n); return m && m.kind === "mod"; });
    state.staged = (Array.isArray(ui.staged) ? ui.staged : []).filter((x) => typeof x === "string").slice(0, 20);
    state.stagedInfo = {};
    state.uploads = [];
    state.addNotes = [];
    state.addText = "";
    renderAddPicked();
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

// --- the Add mods tab (MT21, DESIGN§16) ------------------------------------------------------------------------------

function addKey(k) { return "add::" + (state.adding || []).slice().sort().join("|") + "::" + k; }

function addCandidate(name) {
  state.adding = state.adding || [];
  if (state.adding.some((n) => fold(n) === fold(name))) return false;
  if (state.adding.length >= 20) { toast("Twenty mods at a time is the most ModTrap analyses."); return false; }
  state.adding.push(name);
  renderAddPicked();
  saveUi();
  pollAdd(true);
  return true;
}

const STAGED_WORDS = { copying: ["copying…", "warn"], unpacking: ["unpacking…", "warn"], ready: ["unpacked", "good"], installed: ["now in MO2", "good"],
  installer: ["waiting for your answers", "warn"], failed: ["not taken in", "bad"] };

function renderAddPicked() {
  const box = $("add-picked");
  const list = state.adding || [];
  const staged = state.staged || [];
  const ups = state.uploads || [];
  const n = list.length + staged.length + ups.length;
  box.hidden = !n;
  const badge = $("add-count");
  badge.hidden = !n;
  badge.textContent = n;
  box.replaceChildren(el("span", { class: "dim", text: "To add:" }), ...list.map((name) => {
    const x = el("button", { type: "button", title: "Take “" + name + "” off this list. Nothing in MO2 changes.", "aria-label": "Take " + name + " off the list", text: "×" });
    x.addEventListener("click", () => { state.adding = state.adding.filter((y) => y !== name); renderAddPicked(); saveUi(); pollAdd(true); });
    return el("span", { class: "pick" }, modLink(name), x);
  }), ...staged.map((id) => {
    const info = (state.stagedInfo || {})[id] || { name: "…", state: "unpacking", archive: "" };
    const [word, cls] = STAGED_WORDS[info.state] || [info.state, ""];
    const x = el("button", { type: "button", title: "Take it off this list. ModTrap removes its own unpacked copy; nothing in MO2 changes.", "aria-label": "Take " + info.name + " off the list", text: "×" });
    x.addEventListener("click", async () => {
      try { await api("/api/add/forget", { id: id }); } catch (e) { toast(e.message); return; }
      state.staged = state.staged.filter((y) => y !== id);
      renderAddPicked(); saveUi(); pollAdd(true);
    });
    return el("span", { class: "pick", title: info.archive ? "From " + info.archive : "" }, el("span", { text: info.name }), el("span", { class: "tag " + cls, text: word }), x);
  }), ...ups.map((u) => el("span", { class: "pick" }, el("span", { text: u.name }),
    el("span", { class: "tag warn", text: u.pct == null ? "copying…" : "copying " + u.pct + "%" }))));
}

function addMatches() {
  const q = fold($("add-search").value.trim());
  const box = $("add-matches");
  if (!q) { box.hidden = true; return; }
  const have = new Set((state.adding || []).map(fold));
  const hits = state.mods.filter((m) => m.kind === "mod" && !have.has(fold(m.name)) && fold(m.name).includes(q));
  hits.sort((a, b) => (a.enabled - b.enabled) || (fold(a.name).indexOf(q) - fold(b.name).indexOf(q)) || a.name.localeCompare(b.name));
  box.replaceChildren(...hits.slice(0, 40).map((m) => {
    const b = el("button", { type: "button", role: "option" }, el("span", { class: "name", text: m.name }),
      el("span", { class: "tag " + (m.enabled ? "good" : ""), text: m.enabled ? "enabled" : "disabled" }),
      el("span", { class: "dim", text: plural(m.files, "plugin") }));
    b.addEventListener("click", () => { addCandidate(m.name); $("add-search").value = ""; box.hidden = true; $("add-search").focus(); });
    return b;
  }));
  if (!hits.length) box.append(el("p", { class: "dim", text: "MO2 has no mod with that in its name. Install the mod in MO2 first (leave it disabled), then press Rescan." }));
  else if (hits.length > 40) box.append(el("p", { class: "dim", text: "Showing 40 of " + hits.length + ": type more of the name." }));
  box.hidden = false;
}

// Dropped files and folders (DESIGN§16.1). What MO2 has installed is found by name; an archive MO2 does not have
// is taken in: read in MO2's Downloads if it lies there, or else sent to ModTrap, which unpacks it in its own folder.
const ARCHIVE_NAME = /\.(7z|zip|rar)$/i;

function sendArchive(file) {
  const up = { name: file.name, pct: 0 };
  state.uploads = (state.uploads || []).concat(up);
  renderAddPicked();
  return new Promise((resolve, reject) => {
    const x = new XMLHttpRequest();
    x.open("POST", "/api/add/upload?name=" + encodeURIComponent(file.name));
    x.setRequestHeader("X-ModTrap-Token", TOKEN);
    x.setRequestHeader("Content-Type", "application/octet-stream");
    x.upload.onprogress = (ev) => { if (ev.lengthComputable) { up.pct = Math.floor(100 * ev.loaded / ev.total); renderAddPicked(); } };
    const done = () => { state.uploads = state.uploads.filter((u) => u !== up); renderAddPicked(); };
    x.onload = () => {
      done();
      let data = {};
      try { data = JSON.parse(x.responseText); } catch (e) { /* no answer to read */ }
      if (x.status === 200) resolve(data); else reject(new Error(data.error || (x.status === 413 ? "that file is larger than ModTrap takes in" : "the file was not accepted (" + x.status + ")")));
    };
    x.onerror = () => { done(); reject(new Error("the file did not reach ModTrap")); };
    x.send(file);
  });
}

async function dropMods(drops) {
  showTab("add");
  drops = drops.slice(0, 50);
  try {
    const d = await api("/api/add/resolve", { items: drops.map((x) => ({ name: x.name })) });
    const notes = [];
    let added = 0;
    for (let i = 0; i < d.items.length; i++) {
      const it = d.items[i];
      const file = drops[i] && drops[i].file;
      if (it.mods.length) {
        for (const m of it.mods) if (addCandidate(m)) added++;
        if (!it.sure) notes.push({ name: it.name, text: "Taken to be the mod “" + it.mods[0] + "”, because " + it.how + ". Take it off the list if that is not the one." });
        else if (it.mods.length > 1) notes.push({ name: it.name, text: "MO2 installed " + it.mods.length + " mods from this file: all of them are on the list. Take off the ones you do not mean." });
        continue;
      }
      if (!file || !ARCHIVE_NAME.test(it.name)) {
        notes.push({ name: it.name, bad: true, text: file ? "ModTrap takes in .zip, .7z and .rar archives, and mods MO2 has installed. This is neither." :
          "MO2 has no mod of this name. Drop the mod's archive (.zip, .7z or .rar) instead of a folder." });
        continue;
      }
      if ((state.staged || []).length + (state.adding || []).length >= 20) { notes.push({ name: it.name, bad: true, text: "Twenty mods at a time is the most ModTrap analyses." }); continue; }
      try {
        const rec = it.downloaded ? await api("/api/add/take", { name: it.name, size: file.size }).catch(() => sendArchive(file)) : await sendArchive(file);
        state.staged = (state.staged || []).concat(rec.id);
        state.stagedInfo = Object.assign({}, state.stagedInfo, { [rec.id]: rec });
        added++;
        renderAddPicked();
        saveUi();
      } catch (e) { notes.push({ name: it.name, bad: true, text: "Not taken in: " + e.message + "." }); }
    }
    state.addNotes = notes;
    state.addText = "";
    if (added) toast(plural(added, "mod") + " put on the list to add."); else if (!notes.length) toast("Already on the list.");
    pollAdd(true);
  } catch (e) { problem(e.message); }
}

const KIND_ONE = { "plugin": "plugin", "textures": "texture", "meshes": "mesh", "scripts": "script", "animations": "animation file", "menus": "menu file",
  "archive": "archive", "other files": "other file", "script extender plugin": "script extender plugin", "sequence file": "sequence file" };
const KIND_MANY = { "plugin": "plugins", "archive": "archives", "script extender plugin": "script extender plugins", "sequence file": "sequence files",
  "voice or sound": "voice or sound files", "face data": "face files", "lod": "LOD files", "grass cache": "grass cache files",
  "settings for a script extender plugin": "settings files", "bodyslide data": "BodySlide files" };
const kindsText = (kinds) => Object.entries(kinds).sort((a, b) => b[1] - a[1])
  .map(([k, n]) => n + " " + (n === 1 && KIND_ONE[k] ? KIND_ONE[k] : KIND_MANY[k] || k)).join(", ");

function shareTable(title, list, word) {
  if (!list.length) return null;
  const files = list.reduce((n, c) => n + c.files, 0);
  const rows = list.slice(0, 300).map((c) => el("tr", {},
    el("td", { class: "c-num", text: c.files }),
    el("td", {}, modLink(c.mod), c.output ? el("span", { class: "tag warn", title: c.output, text: "a tool's output" }) : null,
      c.adding ? el("span", { class: "tag", text: "also being added" }) : null,
      ...c.notable.map((k) => el("span", { class: "tag warn", text: k }))),
    el("td", { class: "dim" }, kindsText(c.kinds), el("span", { class: "mono", text: "   " + c.examples.join("  ·  ") + (c.files > c.examples.length ? "  …" : "") }))));
  return el("details", {}, el("summary", {}, title + ": " + plural(files, "file") + " " + word + " " + plural(list.length, "mod")),
    el("table", { class: "share" }, el("tbody", {}, ...rows)),
    list.length > 300 ? el("p", { class: "dim", text: "Showing the first 300 mods." }) : null);
}

function addModCard(x, place, built) {
  const where = place.before ? "directly before “" + place.before + "” in MO2's list" : "last in MO2's list (the highest priority)";
  const plugs = x.plugins.map((p) => {
    if (p.unreadable) return el("div", { class: "plug" }, el("p", {}, el("span", { class: "mono", text: p.name }), el("span", { class: "tag bad", text: "could not be read" })), el("p", { class: "dim", text: p.unreadable }));
    const pr = p.proposed;
    const bad = p.masters.filter((m) => m.state !== "active" && m.state !== "comes along");
    return el("div", { class: "plug" },
      el("p", {}, p.active ? pluginLink(p.name) : el("span", { class: "mono", text: p.name }), el("span", { class: "tag", text: p.kind }),
        el("span", { class: "tag " + (p.active ? "good" : ""), text: p.active ? "active, position " + p.position : "not active yet" })),
      p.active ? null : el("p", {}, "Goes " + (pr.before ? "directly before " : "at the end of the load order"), pr.before ? pluginLink(pr.before) : null,
        el("span", { class: "dim", text: "  (" + pr.why + ")" })),
      el("p", { class: "dim" }, "Masters: " + (p.masters.length ? p.masters.map((m) => m.name).join(", ") : "none"),
        bad.length ? el("span", { class: "tag bad", text: plural(bad.length, "master") + " not ready" }) : p.masters.length ? el("span", { class: "tag good", text: "all there" }) : null),
      ...bad.map((m) => el("p", { class: "would-needs", text: m.name + ": " + (m.state === "missing" ? "no mod in this MO2 has it" : m.state === "inactive" ? "in the modlist, not active" : "in a disabled mod: " + m.mods.join(" or ")) })),
      p.replaces ? el("p", { class: "would-needs" }, "Another mod has a plugin of this name: ", modLink(p.replaces.mod), ". This mod's copy would be the one used; " + plural(p.replaces.dependants, "plugin") + " name it as a master.") : null,
      ...p.notes.map((n) => el("p", { class: "would-needs", text: n })));
  });
  const carries = Object.keys(x.kinds).length ? kindsText(x.kinds) : "no files";
  return el("div", { class: "card" },
    el("div", { class: "card-head" }, el("h2", {}, modLink(x.name),
      el("span", { class: "tag " + (x.enabled ? "good" : x.staged ? "warn" : ""), text: x.enabled ? "enabled, priority " + x.priority : x.staged ? "unpacked by ModTrap, not in MO2 yet" : "installed, not enabled" })),
      built ? (() => {
        const b = el("button", { type: "button", text: "Change the installer's answers", title: "Show this mod's installer questions again" });
        b.addEventListener("click", () => { state.installers = state.installers || {}; state.installers[built.id] = { picks: null, open: true }; loadInstaller(built.id); });
        return b;
      })() : null),
    el("p", { class: "dim", text: "Brings " + carries + (x.cut ? " (the listing was cut short: it is a very large mod)" : "") + "." }),
    x.enabled ? null : el("p", {}, "Its place among the mods: " + where + "."),
    ...plugs,
    x.plugins.length ? null : el("p", { class: "dim", text: "It has no plugin: nothing goes into the load order." }),
    shareTable(x.enabled ? "It replaces" : "There it would replace", x.wins, "of"),
    shareTable(x.enabled ? "It loses" : "There it would lose", x.loses, "to"),
    !x.wins.length && !x.loses.length ? el("p", { class: "dim", text: "It shares no loose file with any enabled mod." }) : null);
}

// An installer's questions (DESIGN§16.1): every step that shows for the answers so far, on one card.
const OPTION_WORDS = { Required: ["required", "good"], Recommended: ["recommended", "good"], NotUsable: ["not usable here", "bad"], CouldBeUsable: ["may not suit your modlist", "warn"] };

async function loadInstaller(id) {
  state.installers = state.installers || {};
  const cur = state.installers[id] || { picks: null };
  if (cur.picks === null) cur.picks = Object.assign({}, ((state.stagedInfo || {})[id] || {}).picks || {});
  state.installers[id] = cur;
  try { cur.view = await api("/api/add/installer", { id: id, picks: cur.picks }); cur.error = ""; }
  catch (e) { cur.error = e.message; }
  state.addText = "";
  pollAdd(true);
}

function installerCard(info) {
  const cur = (state.installers || {})[info.id];
  if (!cur || (!cur.view && !cur.error)) { loadInstaller(info.id); return el("div", { class: "card" }, el("h2", { text: info.name }), el("p", { class: "dim", text: "Reading its installer…" })); }
  if (cur.error) return el("div", { class: "card" }, el("h2", { text: info.name }), el("p", { class: "would-needs", text: cur.error }));
  const v = cur.view;
  const steps = v.steps.map((st) => el("div", { class: "istep" }, st.name ? el("h3", { text: st.name }) : null, ...st.groups.map((g) => {
    const name = "inst-" + info.id + "-" + g.key;
    const set = (list) => { cur.picks[g.key] = list; loadInstaller(info.id); };
    const rows = g.options.map((o) => {
      const box = el("input", { type: g.single ? "radio" : "checkbox", name: name, checked: o.chosen, disabled: o.locked });
      box.addEventListener("change", () => {
        if (g.single) set([o.n]);
        else set(g.options.filter((x) => (x.n === o.n ? box.checked : x.chosen)).map((x) => x.n));
      });
      const [word, cls] = OPTION_WORDS[o.type] || ["", ""];
      return el("label", { class: "iopt" + (o.locked && !o.chosen ? " off" : "") }, box, el("span", {}, el("strong", { text: o.name }),
        word ? el("span", { class: "tag " + cls, text: word }) : null, o.description ? el("span", { class: "dim idesc", text: o.description }) : null));
    });
    if (g.none_allowed) {
      const none = el("input", { type: "radio", name: name, checked: !g.options.some((o) => o.chosen) });
      none.addEventListener("change", () => set([]));
      rows.push(el("label", { class: "iopt" }, none, el("span", {}, el("strong", { text: "None" }))));
    }
    const rule = { SelectExactlyOne: "choose one", SelectAtMostOne: "choose one or none", SelectAtLeastOne: "choose at least one", SelectAny: "choose any", SelectAll: "all of these are installed" }[g.type] || "";
    return el("fieldset", { class: "igroup" }, el("legend", {}, g.name || "Options", el("span", { class: "dim", text: "  " + rule })), ...rows);
  })));
  const go = el("button", { type: "button", class: "primary", text: info.state === "ready" ? "Build it again with these answers" : "Use these answers", disabled: v.problems.length > 0 });
  go.addEventListener("click", async () => {
    go.disabled = true;
    try { await api("/api/add/choose", { id: info.id, picks: cur.picks }); cur.open = false; toast("Built “" + info.name + "” from your answers."); }
    catch (e) { cur.error = e.message; }
    state.addText = "";
    pollAdd(true);
  });
  return el("div", { class: "card installer" }, el("h2", {}, v.name || info.name, el("span", { class: "tag warn", text: "asks which parts to install" })),
    el("p", { class: "dim", text: "These are the mod's own installer questions. What is recommended is already chosen; options that do not suit your load order are marked. Nothing is installed into MO2 by answering: ModTrap builds the mod in its own folder and analyses it." }),
    ...steps, ...v.problems.map((t) => el("p", { class: "would-needs", text: t })),
    v.steps.length ? null : el("p", { class: "dim", text: "It asks nothing: everything it installs is fixed." }),
    el("div", { class: "actions" }, go, el("span", { class: "dim", text: plural(v.files, "file entry", "file entries") + " would be installed" })));
}

// "Add it for me" (DESIGN§16.8): the plan first, then the go-ahead; and the adds already carried out, with Revert.
const addBody = () => ({ mods: (state.adding || []).slice(), staged: (state.staged || []).slice() });

async function askAddPlan() {
  try { state.addPlan = await api("/api/add/plan", addBody()); state.addPlanError = ""; }
  catch (e) { state.addPlan = null; state.addPlanError = e.message; }
  state.addText = "";
  pollAdd(true);
}

function addActionCard(d) {
  const st = (k) => (d.steps || []).find((x) => x.key === k) || { state: "done" };
  const todo = ["install", "enable", "activate"].some((k) => (d.steps || []).some((x) => x.key === k && x.state !== "done"));
  const kids = [];
  if (state.addPlan) {
    const p = state.addPlan;
    const lines = [];
    for (const x of p.mods) {
      if (x.staged) lines.push("Copy “" + x.name + "” from ModTrap's work folder into MO2's mods folder.");
      if (!x.enabled) lines.push("Put “" + x.name + "” " + (x.before ? "directly before “" + x.before + "”" : "last") + " in MO2's mod list, and enable it.");
    }
    for (const x of p.plugins) lines.push("Put " + x.name + " " + (x.before ? "directly before " + x.before : "at the end") + " in the load order, and activate it.");
    const closed = p.mo2_closed === true;
    const go = el("button", { type: "button", class: "primary", text: "Go ahead", disabled: !closed || p.nothing });
    go.addEventListener("click", async () => {
      go.disabled = true;
      try {
        await api("/api/add/run", addBody());
        const names = Object.values(state.stagedInfo || {}).filter((r) => (state.staged || []).includes(r.id) && r.state === "ready").map((r) => r.name);
        state.addPlan = null;
        toast("Added. ModTrap is reading the modlist again.");
        for (const n of names) if (!(state.adding || []).includes(n)) state.adding.push(n);
        saveUi();
      } catch (e) { state.addPlanError = e.message; state.addPlan = null; }
      state.addText = "";
      state.gen = (state.gen || 0) + 1;
      tick();
    });
    const again = el("button", { type: "button", text: "Check again" });
    again.addEventListener("click", askAddPlan);
    const cancel = el("button", { type: "button", text: "Not now" });
    cancel.addEventListener("click", () => { state.addPlan = null; state.addText = ""; pollAdd(true); });
    kids.push(el("h2", { text: "What ModTrap is about to do" }),
      p.nothing ? el("p", { text: "Nothing: every mod is enabled and every plugin active already." }) : el("ol", {}, ...lines.map((t) => el("li", { text: t }))),
      el("p", { class: "dim", text: "First the three list files of the profile are copied into the job's safe folder. Afterwards ModTrap reads the modlist again and checks it; if anything is not as planned, everything is put back. “Take it out again” undoes it later." }),
      el("p", { class: closed ? "would-record" : "would-needs", text: closed ? "MO2 is closed: good. Keep it closed until this is done." :
        p.mo2_closed === false ? "MO2 is open. Close it first: an open MO2 writes its own lists back over ModTrap's." : "ModTrap cannot tell whether MO2 is open on this PC, so it will not change the lists." }),
      el("div", { class: "actions" }, go, closed ? null : again, cancel));
  } else {
    const b = el("button", { type: "button", class: "primary", text: "Add it for me", disabled: !state.changes || !todo || st("needs").state !== "done" || d.looking });
    b.title = !state.changes ? "Switched off. ModTrap changes a modlist only when it is started with --allow-changes, which is for once it has been proven on your PC." :
      st("needs").state !== "done" ? "First get what the mod needs: see step “Get what the mod needs”." : !todo ? "There is nothing left for ModTrap to do here." : "Shows what ModTrap would do, and asks before doing it";
    b.addEventListener("click", askAddPlan);
    kids.push(el("div", { class: "actions" }, b, el("span", { class: "dim", text: !state.changes ?
      "Switched off for now: ModTrap putting the mod in for you waits until it has been proven on your modlist. The steps below say how to do it by hand." :
      "ModTrap copies the mod in, places and enables it, places and activates its plugins, and checks the result. It shows the plan and asks first." })),
      state.addPlanError ? el("p", { class: "would-needs", text: state.addPlanError }) : null);
  }
  for (const j of (d.added || []).slice(0, 12)) {
    const undo = el("button", { type: "button", text: "Take it out again" });
    undo.addEventListener("click", async () => {
      if (!window.confirm("Put the mod list and the load order back as they were before this add, and remove ModTrap's copy of the mod from MO2's mods folder? MO2 must be closed.")) return;
      try {
        const r = await api("/api/add/revert", { job: j.job });
        for (const x of r.restored || []) {                // a dropped mod is back in ModTrap's folder only
          state.adding = (state.adding || []).filter((n) => n !== x.name);
          if (!(state.staged || []).includes(x.id)) state.staged = (state.staged || []).concat(x.id);
        }
        renderAddPicked();
        saveUi();
        toast(r.left.length ? "Put back. Left in place, because it changed since: " + r.left.join(", ") : "Put back as it was.");
        state.addPlanError = "";
      }
      catch (e) { state.addPlanError = e.message; }
      state.addText = "";
      state.gen = (state.gen || 0) + 1;
      tick();
    });
    kids.push(el("p", {}, el("span", { class: "tag " + (j.state === "added" ? "good" : ""), text: j.state === "added" ? "added by ModTrap" : j.state === "reverted" ? "taken out again" : "did not go through" }),
      " " + j.when.replace("T", " ") + ": " + j.mods.join(", ") + (j.plugins.length ? "  (" + j.plugins.join(", ") + ")" : "") + "  ", j.state === "added" && state.changes ? undo : null));
  }
  return el("div", { class: "card" }, ...kids.filter(Boolean));
}

function addStepCard(st, d) {
  const done = state.stepsDone || {};
  const ticked = st.manual && !!done[addKey(st.key)];
  const isDone = ticked || st.state === "done" || st.state === "not needed";
  const waiting = !isDone && st.state.startsWith("waiting");
  const [word, cls] = ticked ? ["ticked off by you", "good"] : STEP_STATE[st.state] || [st.state, ""];
  const body = el("div", {},
    el("h3", {}, st.title, el("span", { class: "who" + (st.who === "you" ? " you" : ""), text: st.who === "you" ? "You" : "ModTrap" }),
      el("span", { class: "tag " + cls, text: word })),
    el("p", { class: "dim", text: st.why }),
    st.note ? el("p", { text: st.note }) : null,
    st.items.length ? el("ul", {}, ...st.items.map((it) => el("li", {}, it.text,
      it.tag ? el("span", { class: "tag " + (it.cls || ""), text: it.tag }) : null,
      it.add && findMod(it.add) ? (() => {
        const b = el("button", { type: "button", class: "linkish", text: "  add it too" });
        b.addEventListener("click", () => addCandidate(it.add));
        return b;
      })() : null))) : null);
  if (st.manual) {
    const box = el("input", { type: "checkbox", checked: ticked });
    box.addEventListener("change", () => {
      state.stepsDone = state.stepsDone || {};
      if (box.checked) state.stepsDone[addKey(st.key)] = true; else delete state.stepsDone[addKey(st.key)];
      saveUi();
      renderAdd(d);
    });
    body.append(el("label", { class: "tickoff" }, box, "I have done this"));
  }
  return [isDone, el("div", { class: "step " + (isDone ? "done" : waiting ? "waiting" : "todo") }, el("div", { class: "num", text: isDone ? "✓" : st.n }), body)];
}

function renderAdd(d) {
  const box = $("add-report");
  const notes = (state.addNotes || []).concat((d.staged || []).filter((r) => r.note).map((r) => ({ name: r.archive, text: r.note, bad: r.state !== "ready" })));
  const noteCard = notes.length ? el("div", { class: "card add-notes" }, el("h2", { text: "About what you dropped" }),
    el("ul", {}, ...notes.map((n) => el("li", {}, el("span", { class: "mono", text: n.name }), ": " + n.text)))) : null;
  if (!(state.adding || []).length && !(state.staged || []).length && !(state.uploads || []).length) {
    $("add-summary").textContent = "";
    box.replaceChildren(...[noteCard, el("div", { class: "card" }, el("h2", { text: "Add a mod to this modlist, safely" }),
      el("p", { text: "Drop the mod's archive (.zip, .7z or .rar) anywhere on this page. ModTrap unpacks it in its own work folder, not in your modlist, reads it against the whole modlist and tells you:" }),
      el("ul", {},
        el("li", { text: "what it needs: masters that are missing, switched off or in a disabled mod, and whether the load order has room;" }),
        el("li", { text: "where it should go, among the mods and in the load order, and why: after everything made by hand, before what the modlist's tools made;" }),
        el("li", { text: "which files of which mods it would replace there, and which it would lose, with the kinds that go wrong quietly pointed out;" }),
        el("li", { text: "which of the modlist's tools must run again, and every step in order." })),
      el("p", { class: "dim", text: "A mod MO2 has already installed can be found by name in the box above instead. A mod whose installer asks which parts you want is installed in MO2 first, for now." }),
      el("p", { class: "dim", text: "Nothing in MO2 changes yet. Putting the mod into MO2 and in its place for you, with a safe folder and Revert, is the part that is still switched off." }))].filter(Boolean));
    return;
  }
  const asking = (d.staged || []).filter((r) => r.installer && (r.state === "installer" || ((state.installers || {})[r.id] || {}).open));
  const askCards = asking.map(installerCard);
  if (!d.looking && !(d.mods || []).length && !d.failed) {
    $("add-summary").textContent = d.unpacking || (state.uploads || []).length ? "Unpacking…" : asking.length ? "Waiting for your answers" : "";
    box.replaceChildren(...[noteCard, ...askCards, d.unpacking || (state.uploads || []).length ? el("div", { class: "card" }, el("h2", {}, el("span", { class: "spinner", "aria-hidden": "true" }), " Taking the archive in…"),
      el("p", { class: "dim", text: "It is copied into ModTrap's own work folder and unpacked there. A large mod takes a while; nothing in your modlist is being changed." })) : null].filter(Boolean));
    return;
  }
  if (d.looking) {
    $("add-summary").textContent = "Reading…";
    box.replaceChildren(...[noteCard, el("div", { class: "card" }, el("h2", {}, el("span", { class: "spinner", "aria-hidden": "true" }), " Reading the mod against the whole modlist…"),
      el("p", { class: "dim", text: "Its plugins' headers, and the file names of every enabled mod it shares a folder with. Seconds on a large modlist; nothing is being changed." }))].filter(Boolean));
    return;
  }
  if (d.failed) { $("add-summary").textContent = ""; box.replaceChildren(el("div", { class: "card" }, el("p", { class: "would-needs", text: d.failed }))); return; }
  let open = 0;
  const cards = d.steps.map((st) => { const [isDone, card] = addStepCard(st, d); if (!isDone) open++; return card; });
  $("add-summary").textContent = open ? plural(open, "step") + " to go" : "Every step is done";
  const s = d.slots;
  const room = el("p", { class: s.full.after > s.full.limit || s.light.after > s.light.limit ? "would-needs" : "dim",
    text: "Room in the load order: full plugins " + s.full.now + (s.full.after !== s.full.now ? " → " + s.full.after : "") + " of " + s.full.limit +
      ", light plugins " + s.light.now + (s.light.after !== s.light.now ? " → " + s.light.after : "") + " of " + s.light.limit + "." });
  box.replaceChildren(...[noteCard,
    el("div", { class: "card" }, el("p", { text: "What ModTrap can tell from the files, without xEdit. Nothing in MO2 has been changed: the steps marked “You” are done by hand in MO2 for now, and ModTrap checks them each time the modlist is read." }), room,
      d.cut ? el("p", { class: "would-needs", text: "The search for shared files was cut short: there may be more than is listed." }) : null,
      d.unknown && d.unknown.length ? el("p", { class: "would-needs", text: "No longer in MO2: " + d.unknown.join(", ") }) : null),
    addActionCard(d),
    ...askCards,
    ...d.mods.map((x) => addModCard(x, d.place, (d.staged || []).find((r) => r.installer && r.state === "ready" && r.name === x.name))),
    el("h2", { text: "The steps, in order" }), ...cards].filter(Boolean));
}

async function pollAdd(force) {
  if (state.status !== "ready") return;
  const mods = (state.adding || []).slice();
  const staged = (state.staged || []).slice();
  const key = mods.join("|") + "#" + staged.join("|") + "#" + state.loaded;
  if (!force && key === state.addKeySeen && !state.addLooking) return;
  try {
    const d = mods.length || staged.length ? await api("/api/add", { mods: mods, staged: staged }) : { looking: false, mods: [], steps: [] };
    state.addKeySeen = key;
    state.addLooking = d.looking || d.unpacking;
    const info = {};
    for (const r of d.staged || []) info[r.id] = r;
    const infoText = JSON.stringify(info);
    if (d.gone && d.gone.length) { state.staged = state.staged.filter((id) => !d.gone.includes(id)); saveUi(); }
    for (const r of d.staged || []) {
      if (r.state !== "installed") continue;
      state.staged = state.staged.filter((id) => id !== r.id);
      if (findMod(r.name) && !(state.adding || []).includes(r.name)) state.adding.push(r.name);
      saveUi();
    }
    if (infoText !== JSON.stringify(state.stagedInfo || {}) || (d.gone && d.gone.length)) { state.stagedInfo = info; renderAddPicked(); }
    const text = JSON.stringify(d) + JSON.stringify(state.addNotes || []) + (state.uploads || []).length + JSON.stringify(state.installers || {})
      + JSON.stringify(state.addPlan || 0) + (state.addPlanError || "") + state.changes;
    if (text !== state.addText) { state.addText = text; renderAdd(d); }
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
  state.changes = !!s.changes;
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
  await pollAdd(false);
  await pollLog();
}

function loop() {
  if (state.quit) return;
  const busy = state.status === "reading" || state.addLooking || (state.job && !["done", "failed", "stopped"].includes(state.job.state));
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

// --- the folder picker (WHY§38) -------------------------------------------------------------------------------------

const picker = { path: "", data: null };

async function pickerGo(path) {
  const msg = $("picker-message");
  let d;
  try { d = await api("/api/browse", { path: path }); } catch (e) { msg.hidden = false; msg.textContent = e.message; return; }
  msg.hidden = true;
  picker.path = d.path;
  picker.data = d;
  $("picker-filter").value = "";
  const crumbs = [el("button", { type: "button", text: "This PC" })];
  crumbs[0].addEventListener("click", () => pickerGo(""));
  for (const c of d.crumbs) {
    const b = el("button", { type: "button", text: c.name });
    b.addEventListener("click", () => pickerGo(c.path));
    crumbs.push(el("span", { class: "sep", text: "›" }), b);
  }
  $("picker-crumbs").replaceChildren(...crumbs);
  $("picker-open").disabled = !d.modlist;
  $("picker-here").textContent = !d.path ? "Pick a drive to start." : d.modlist ? "This folder holds an MO2 modlist." :
    "This folder is not a modlist: it has no ModOrganizer.ini. Go into the folder that has ModOrganizer.exe in it.";
  pickerList();
}

function pickerList() {
  const d = picker.data;
  if (!d) return;
  const q = fold($("picker-filter").value.trim());
  const rows = d.folders.filter((f) => !q || fold(f.name).includes(q)).map((f) => {
    const b = el("button", { type: "button", class: "prow" + (f.modlist ? " is-modlist" : "") },
      el("span", { class: "name", text: f.name }), f.modlist ? el("span", { class: "tag good", text: "MO2 modlist" }) : null);
    b.addEventListener("click", () => pickerGo(f.path));
    return b;
  });
  if (d.cut) rows.push(el("p", { class: "dim small pad", text: "More folders than are shown: use the filter, or paste the path." }));
  $("picker-list").replaceChildren(...(rows.length ? rows : [el("p", { class: "empty", text: d.folders.length ? "No folder matches." : "No folders in here." })]));
}

function pickerOpen() {
  $("picker").hidden = false;
  const start = state.session ? state.session.folder.replace(/[\\/][^\\/]*$/, "") : "";
  pickerGo(start || "").then(() => { if (!picker.data) pickerGo(""); $("picker-filter").focus(); });
}

function pickerClose() { $("picker").hidden = true; $("browse").focus(); }

$("browse").addEventListener("click", pickerOpen);
$("picker-close").addEventListener("click", pickerClose);
$("picker").addEventListener("click", (ev) => { if (ev.target === $("picker")) pickerClose(); });
$("picker-filter").addEventListener("input", pickerList);
$("picker-open").addEventListener("click", () => {
  const path = picker.path;
  pickerClose();
  $("folder").value = path;
  openFolder(path, null);
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
  const entries = items.map((i) => (i.webkitGetAsEntry ? i.webkitGetAsEntry() : null)).filter(Boolean);
  const files = Array.from(dt.files || []);
  const names = entries.length ? entries.map((e, i) => ({ name: e.name, file: e.isDirectory ? null : files[i] || null }))
    : files.map((f) => ({ name: f.name, file: f }));
  const ready = state.status === "ready";             // a modlist is open: what is dropped may be a mod to add
  const entry = entries.length === 1 ? entries[0] : null;
  if (entry && entry.isDirectory) {
    entry.getFile("ModOrganizer.ini", {}, (fe) => fe.file((f) => giveIni(entry.name, f), () => problem("ModOrganizer.ini in that folder could not be read.")),
      () => (ready ? dropMods(names) : problem("There is no ModOrganizer.ini in “" + entry.name + "”. Drop the modlist's own folder: the one with ModOrganizer.exe in it.")));
    return;
  }
  if (entry && entry.isFile && /^modorganizer\.ini$/i.test(entry.name)) { entry.file((f) => giveIni(null, f), () => problem("That file could not be read.")); return; }
  if (names.length && ready) { dropMods(names); return; }
  if (names.length) {
    problem("Drop the modlist's folder itself (the one with ModOrganizer.exe in it), not a file from it. A page cannot tell where a dropped file lives.");
    return;
  }
  const text = (dt.getData && dt.getData("text/plain") || "").trim();
  if (text && text.length < 1000 && !text.includes("\n")) { $("folder").value = text; openFolder(text, null); return; }
  problem("That could not be used. Drop the modlist's folder, or paste its path into the box.");
}

let dragDepth = 0;
const dragOn = (yes) => {
  document.body.classList.toggle("dragging", yes);
  $("drop-words").textContent = state.status === "ready" ? "Drop a mod's archive here to add it, or another modlist's folder to open that" : "Drop your modlist folder here";
};
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
$("add-rescan").addEventListener("click", () => $("rescan").click());
$("add-search").addEventListener("input", () => addMatches());
$("add-search").addEventListener("focus", () => addMatches());
$("add-search").addEventListener("keydown", (ev) => {
  if (ev.key === "Escape") { $("add-matches").hidden = true; return; }
  if (ev.key === "Enter") { const first = $("add-matches").querySelector("button"); if (first && !$("add-matches").hidden) first.click(); }
  if (ev.key === "ArrowDown") { const first = $("add-matches").querySelector("button"); if (first) { ev.preventDefault(); first.focus(); } }
});
document.addEventListener("click", (ev) => { if (!ev.target.closest(".combo")) $("add-matches").hidden = true; });
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
  if (ev.key === "Escape" && !$("picker").hidden) { pickerClose(); return; }
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
