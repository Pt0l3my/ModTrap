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
    else if (k.startsWith("data-")) e.setAttribute(k, v);
    else e[k] = v;
  }
  for (const k of kids) if (k != null) e.append(k);
  return e;
}
const plural = (n, one, many) => n + " " + (n === 1 ? one : (many || one + "s"));
const fold = (s) => s.toLowerCase();

// --- the instance bar ----------------------------------------------------------------------------------------------

function showMessage(text, bad) {
  const m = $("message");
  m.hidden = !text;
  m.textContent = text || "";
  m.classList.toggle("bad", !!bad);
}

function renderState(s) {
  $("version").textContent = s.version ? "version " + s.version : "";
  if (document.activeElement !== $("folder") && s.folder && !$("folder").value) $("folder").value = s.folder;
  const ready = s.status === "ready";
  $("summary").hidden = !ready;
  $("tabs").hidden = !ready;
  $("rescan").hidden = !ready;
  if (s.status === "reading") showMessage("Reading the modlist: its mods, and the header of every plugin…");
  else if (s.status === "error") showMessage(s.message, true);
  else if (s.status === "none") showMessage("Give the folder of an MO2 modlist (the one MO2 itself is in) and press Open. ModTrap only reads it.");
  else showMessage("");
  if (!ready) {
    document.querySelectorAll(".tab").forEach((t) => { t.hidden = true; });
    $("notes").hidden = true;
    $("profile").hidden = true;
    return;
  }
  $("s-game").textContent = (s.game || "Game unknown") + " · profile " + s.profile;
  $("s-mods").textContent = plural(s.mods, "mod") + ", " + s.mods_enabled + " enabled";
  $("s-plugins").textContent = plural(s.plugins, "plugin") + ", " + s.plugins_active + " active" +
    (s.unreadable ? ", " + s.unreadable + " unreadable" : "");
  $("s-tools").textContent = plural(s.tools.length, "tool") + " set up in MO2";
  $("s-tools").title = s.tools.map((t) => t.title + (t.output_mod ? " → " + t.output_mod : "")).join("\n");
  const h = $("s-health");
  h.textContent = s.issue_count ? plural(s.issue_count, "master problem") : "No missing or inactive masters";
  h.className = "chip " + (s.issue_count ? "bad" : "good");
  $("health-count").textContent = s.issue_count;
  $("health-count").classList.toggle("bad", s.issue_count > 0);
  const notes = $("notes");
  notes.replaceChildren(...s.notes.map((n) => el("li", { text: n })));
  notes.hidden = !s.notes.length;
  const sel = $("profile");
  sel.hidden = s.profiles.length < 2;
  sel.replaceChildren(...s.profiles.map((p) => el("option", { value: p, text: p, selected: p === s.profile })));
  renderHealth(s);
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

// --- the Mods tab ----------------------------------------------------------------------------------------------------

function renderMods() {
  const body = $("mods-table").tBodies[0];
  const frag = document.createDocumentFragment();
  for (const m of state.mods) {
    let tr;
    if (m.kind === "separator") {
      tr = el("tr", { class: "sep" }, el("td"), el("td", { class: "c-num", text: m.priority }),
        el("td", { colSpan: 3, text: m.name.replace(/_separator$/i, "") }));
    } else {
      const can = m.kind === "mod" && m.plugins.length > 0;
      const tick = el("input", { type: "checkbox", disabled: !can, checked: state.picked.has(m.name),
        title: can ? "Tick to see what a demaster of this mod would involve" : "Nothing to demaster: this mod provides no plugin" });
      tick.addEventListener("change", () => togglePick(m.name, tick.checked));
      const name = el("td", {}, m.name);
      if (m.kind === "foreign") name.append(el("span", { class: "tag", text: "not managed by MO2" }));
      if (m.kind === "game") name.replaceChildren("The game's own Data folder");
      if (m.kind === "overwrite") name.replaceChildren("Overwrite");
      if (!m.enabled) name.append(el("span", { class: "tag", text: "disabled" }));
      if (!m.listed) name.append(el("span", { class: "tag warn", text: "not in modlist.txt" }));
      if (m.files > m.plugins.length && m.enabled) name.append(el("span", { class: "tag", text: (m.files - m.plugins.length) + " plugin file(s) overridden" }));
      tr = el("tr", { class: (m.enabled ? "" : "off") + (state.picked.has(m.name) ? " picked" : "") },
        el("td", { class: "c-tick" }, tick), el("td", { class: "c-num", text: m.priority < 0 ? "" : m.priority }), name,
        el("td", { class: "plugs", text: m.plugins.slice(0, 4).join(", ") + (m.plugins.length > 4 ? " … +" + (m.plugins.length - 4) : "") }),
        el("td", { class: "c-num" + (m.dependants ? " badnum" : ""), text: m.plugins.length ? m.dependants : "" }));
    }
    tr.dataset.name = m.name;
    m.row = tr;
    m.hay = fold(m.name + " " + m.plugins.join(" "));
    frag.append(tr);
  }
  body.replaceChildren(frag);
  filterMods();
}

function filterMods() {
  const q = fold($("mods-search").value.trim());
  const en = $("f-enabled").checked, pl = $("f-plugins").checked, dp = $("f-deps").checked;
  const filtering = q || en || pl || dp;
  let shown = 0, total = 0;
  for (const m of state.mods) {
    let ok;
    if (m.kind === "separator") ok = !filtering;
    else {
      total++;
      ok = (!q || m.hay.includes(q)) && (!en || m.enabled) && (!pl || m.plugins.length > 0) && (!dp || m.dependants > 0);
      if (ok) shown++;
    }
    m.row.hidden = !ok;
  }
  $("mods-shown").textContent = filtering ? shown + " of " + total + " shown" : total + " entries";
}

function togglePick(name, on) {
  if (on) state.picked.add(name); else { state.picked.delete(name); state.details.delete(name); }
  const m = state.mods.find((x) => x.name === name);
  if (m && m.row) {
    m.row.classList.toggle("picked", on);
    const box = m.row.querySelector("input");
    if (box) box.checked = on;
  }
  $("sel-count").textContent = state.picked.size;
  $("sel-count").classList.toggle("on", state.picked.size > 0);
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
}

async function showPlugin(name, tr) {
  document.querySelectorAll("#plugins-table tr.picked").forEach((r) => r.classList.remove("picked"));
  if (tr) tr.classList.add("picked");
  const box = $("plugin-detail");
  let p;
  try { p = await api("/api/plugin?name=" + encodeURIComponent(name)); } catch (e) { box.replaceChildren(el("p", { class: "dim", text: e.message })); return; }
  const list = (title, items, mark) => [el("h3", { text: title + " (" + items.length + ")" }),
    items.length ? el("ul", {}, ...items.map((i) => {
      const li = el("li", { class: "mono", text: i });
      if (mark && mark.missing.includes(i)) li.append(el("span", { class: "tag bad", text: "missing" }));
      if (mark && mark.inactive.includes(i)) li.append(el("span", { class: "tag warn", text: "not active" }));
      return li;
    })) : el("p", { class: "dim", text: "none" })];
  box.replaceChildren(...[el("h2", { class: "mono", text: p.name }),
    el("p", { class: "dim", text: "Position " + (p.position == null ? "none" : p.position) + " · " + (p.kind || "kind unknown") + " · " +
      (p.active ? "active" : "not active") + " · in " + (p.mod === "<game>" ? "the game's Data folder" : p.mod ? "mod “" + p.mod + "”, priority " + p.mod_priority : "no enabled mod") }),
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
    box.replaceChildren(el("p", { class: "dim", text: "Tick mods on the Mods tab to see what depends on them." }));
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
    card.append(el("div", { class: "card-head" }, el("h2", { text: d.name }), un));
    if (d.error) { card.append(el("p", { class: "message bad", text: d.error })); cards.push(card); continue; }
    const n = d.groups.reduce((a, g) => a + g.plugins.length, 0);
    card.append(el("p", { class: "dim", text: "Priority " + d.priority + " · " + (d.enabled ? "enabled" : "disabled") + " · provides " +
      d.plugins.map((p) => p.name + " (position " + p.position + ", " + p.kind + ")").join(", ") }));
    card.append(el("p", { text: n ? plural(n, "plugin") + " in " + plural(d.groups.length, "other mod") + " list it as a master. Disabling it now would leave them with a missing master."
      : "Nothing depends on this mod's plugins: it can be disabled in MO2 as it is." }));
    for (const g of d.groups) {
      const [label, hint] = READING[g.reading];
      const head = el("div", { class: "head" }, el("strong", { text: g.mod }), el("span", { class: "dim", text: "priority " + g.priority }),
        el("span", { class: "tag " + (g.reading === "output" ? "warn" : ""), text: g.reading === "output" ? "made by " + g.made_by.join(", ") : label }));
      if (g.reading === "some plugins") head.append(el("span", { class: "dim", text: g.others + " other plugin(s) here do not depend on it" }));
      if (g.reading === "most of the mod") head.append(el("span", { class: "dim", text: "the rest: " + g.leftover.join(", ") }));
      card.append(el("div", { class: "group" }, head, el("div", { class: "dim", text: hint }),
        el("ul", {}, ...g.plugins.map((p) => el("li", {}, el("span", { class: "mono", text: p.name }),
          el("span", { class: "dim", text: "  position " + p.position + " · " + p.kind + " · " + plural(p.masters, "master") }))))));
    }
    cards.push(card);
  }
  box.replaceChildren(...cards);
}

// --- tabs, the log, and the loop -------------------------------------------------------------------------------------

function showTab(name) {
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
  document.querySelectorAll(".tab").forEach((t) => { t.hidden = t.id !== "tab-" + name; });
  state.tab = name;
}

async function pollLog() {
  try {
    const d = await api("/api/log?after=" + state.logAfter);
    if (d.lines.length) {
      const log = $("log");
      const atEnd = log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
      for (const ln of d.lines) {
        log.append(el("span", { class: ln.level, text: ln.t + "  " + ln.text + "\n" }));
        state.logAfter = ln.seq;
      }
      if (atEnd) log.scrollTop = log.scrollHeight;
    }
  } catch (e) { /* the next round tries again */ }
}

async function loadLists(key) {
  const [m, p] = await Promise.all([api("/api/mods"), api("/api/plugins")]);
  state.mods = m.mods;
  state.plugins = p.plugins;
  state.details.clear();
  const names = new Set(state.mods.map((x) => x.name));
  for (const n of [...state.picked]) if (!names.has(n)) state.picked.delete(n);
  state.loaded = key;
  renderMods();
  renderPlugins();
  $("sel-count").textContent = state.picked.size;
  renderSelection();
  showTab(state.tab || "mods");
}

async function tick() {
  let s;
  try { s = await api("/api/state"); } catch (e) { showMessage("ModTrap is not answering: " + e.message, true); return; }
  const was = state.status;
  state.status = s.status;
  renderState(s);
  const key = s.status === "ready" ? s.folder + "|" + s.profile + "|" + s.mods + "|" + s.plugins + "|" + s.issue_count + "|" + (state.gen || 0) : "";
  if (s.status === "ready" && (key !== state.loaded || was !== "ready")) {
    try { await loadLists(key); } catch (e) { showMessage(e.message, true); }
  }
  await pollLog();
}

function loop() {
  tick().finally(() => setTimeout(loop, state.status === "reading" ? 700 : 2500));
}

$("open-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const sel = $("profile");
  try {
    state.gen = (state.gen || 0) + 1;
    await api("/api/open", { folder: $("folder").value, profile: sel.hidden ? null : sel.value });
    state.status = "reading";
  } catch (e) { showMessage(e.message, true); }
  tick();
});
$("profile").addEventListener("change", () => $("open-form").requestSubmit());
$("rescan").addEventListener("click", async () => {
  try { state.gen = (state.gen || 0) + 1; await api("/api/rescan", {}); state.status = "reading"; } catch (e) { showMessage(e.message, true); }
  tick();
});
document.querySelectorAll("#tabs button").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
let debounce;
const later = (fn) => () => { clearTimeout(debounce); debounce = setTimeout(fn, 120); };
$("mods-search").addEventListener("input", later(filterMods));
$("plugins-search").addEventListener("input", later(filterPlugins));
for (const id of ["f-enabled", "f-plugins", "f-deps"]) $(id).addEventListener("change", filterMods);
for (const id of ["p-problems", "p-deps"]) $(id).addEventListener("change", filterPlugins);
loop();
