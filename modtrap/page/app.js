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
    li.classList.toggle("now", k === at && !done && k !== "trap");
  }
  steps.querySelector('[data-step="dry"]').dataset.tab = job ? "job" : "selection";
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
  $("tray").hidden = !n || tab === "selection" || tab === "job";
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
  $("dry-run").disabled = !state.picked.size;
  $("plan").hidden = true;
  if (state.groups) filterMods();
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
        el("span", { class: "tag " + (g.reading === "output" ? "warn" : ""), text: g.reading === "output" ? "made by " + g.made_by.join(", ") : label }));
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
  $("dry-run").disabled = active || !state.picked.size;
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

// --- tabs, the log, and the loop -------------------------------------------------------------------------------------

function showTab(name) {
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
  document.querySelectorAll(".tab").forEach((t) => { t.hidden = t.id !== "tab-" + name; });
  state.tab = name;
  updateTray();
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

async function loadLists(key) {
  const [m, p] = await Promise.all([api("/api/mods"), api("/api/plugins")]);
  state.mods = m.mods;
  state.plugins = p.plugins;
  state.details.clear();
  const names = new Set(state.mods.filter((x) => x.kind === "mod" && x.plugins.length).map((x) => x.name));
  for (const n of [...state.picked]) if (!names.has(n)) state.picked.delete(n);
  state.loaded = key;
  renderMods();
  renderPlugins();
  $("sel-count").textContent = state.picked.size;
  $("sel-count").classList.toggle("on", state.picked.size > 0);
  $("dry-run").disabled = !state.picked.size;
  renderSelection();
  renderSteps();
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
  await pollJob();
  await pollLog();
}

function loop() {
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
  if (ev.key === "Escape" && document.activeElement === box && box.value) { box.value = ""; (state.tab === "plugins" ? filterPlugins : filterMods)(); }
});
let debounce;
const later = (fn) => () => { clearTimeout(debounce); debounce = setTimeout(fn, 120); };
$("mods-search").addEventListener("input", later(filterMods));
$("plugins-search").addEventListener("input", later(filterPlugins));
for (const id of ["f-enabled", "f-plugins", "f-deps"]) $(id).addEventListener("change", filterMods);
for (const id of ["p-problems", "p-deps"]) $(id).addEventListener("change", filterPlugins);
loop();
