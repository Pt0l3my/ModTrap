"use strict";
// ModTrap's page (DESIGN§4). Version 0.1 only reads: every call below is a GET, except opening a folder.

const TOKEN = document.body.dataset.token;
const $ = (id) => document.getElementById(id);
const state = { status: "none", mods: [], plugins: [], picked: new Set(), logAfter: 0, loaded: "", details: new Map() };

// What changes MO2's lists must find MO2 closed: an open MO2 holds them in memory and writes its own back.
const NEEDS_MO2_CLOSED = new Set(["/api/add/run", "/api/add/revert", "/api/demaster/install", "/api/demaster/revert",
  "/api/probe/start", "/api/probe/cleanup"]);

async function api(path, body) {
  if (NEEDS_MO2_CLOSED.has(path) && !(await mo2Closed())) throw new Error("MO2 is still open; nothing was changed");
  return call(path, body);
}

async function call(path, body) {
  const opt = { headers: { "X-ModTrap-Token": TOKEN } };
  if (body !== undefined) {
    opt.method = "POST";
    opt.headers["Content-Type"] = "application/json";
    opt.body = JSON.stringify(body);
  }
  const r = await fetch(path, opt);
  const data = await r.json().catch(() => ({}));
  if (r.status === 403 && data.error === "no token") {
    // Another start of ModTrap answers at this address now (WHY§68): this page belongs to the one that closed.
    let last = 0;
    try { last = Number(sessionStorage.getItem("modtrap-reloaded") || 0); } catch (e) { /* no storage: no reload */ last = Date.now(); }
    if (Date.now() - last > 15000) {
      try { sessionStorage.setItem("modtrap-reloaded", String(Date.now())); } catch (e) { /* as above */ }
      location.reload();
    }
    throw new Error("ModTrap was started again; this page is the earlier one's. Reload it.");
  }
  if (!r.ok) throw new Error(data.error || ("the request failed (" + r.status + ")"));
  return data;
}

// MO2 open or closed for this modlist (state.mo2, from the server). Asks before closing it, and never forces.
async function mo2Closed() {
  let m = state.mo2;
  try { m = (await call("/api/state")).mo2 || m; } catch (e) { /* use what is known */ }
  if (!m || m.state !== "open") return true;         // closed; or it cannot be told, and the server then decides
  if (m.ours) return true;                            // ModTrap's own MO2 of the last run, leaving: the server waits for it
  if (!(state.settings || {}).close_mo2 &&
      !await confirmBox("MO2 is open on this modlist. This step changes MO2's lists, and MO2 must be closed for it.\n\nClose MO2 now?")) return false;
  try { await call("/api/mo2/close", {}); } catch (e) { toast(e.message); return false; }
  for (let i = 0; i < 60; i++) {
    await new Promise((r) => setTimeout(r, 500));
    try { m = (await call("/api/state")).mo2; } catch (e) { continue; }
    if (m && m.state !== "open") { state.mo2 = m; renderMo2(); return true; }
  }
  toast("MO2 has not closed. It may be asking you something: look at its window.");
  return false;
}

function renderMo2() {
  const b = $("s-mo2"), m = state.mo2;
  b.hidden = !m;
  if (!m) return;
  b.className = "chip link " + (m.state === "open" || m.other ? "warn" : m.state === "closed" ? "good" : "");
  b.textContent = m.other ? "Another modlist's MO2 is open" : m.state === "open" ? "MO2 is open · close it…" : m.state === "closed" ? "MO2 is closed · open it" : "MO2: cannot tell if it is open";
  b.title = m.state === "open" ? "ModTrap changes MO2's lists only while MO2 is closed. Reading and dry runs work either way."
    : m.other ? "A Mod Organizer for another modlist is open. MO2 hands every command to the one that is already open, so ModTrap starts nothing through MO2 until that one is closed."
    : m.state === "closed" ? "Starts this modlist's MO2, to look at the result."
    : "ModTrap could not find out whether MO2 is running; it will not change MO2's lists until it can.";
}

async function toggleMo2() {
  const m = state.mo2;
  if (!m || m.state === "unknown") return;
  try {
    if (m.state === "open") {
      if (!await confirmBox("Close MO2 now? It is asked to close as a click on its X does.")) return;
      await call("/api/mo2/close", {});
      toast("MO2 was asked to close.");
    } else {
      await call("/api/mo2/open", {});
      toast("MO2 is starting.");
    }
  } catch (e) { toast(e.message); }
}

// Who does a step: ModTrap, the owner, or ModTrap starts a tool that the owner then works in.
function copyButton(text, what) {
  const b = el("button", { type: "button", class: "nav-link", text: "copy" });
  b.addEventListener("click", () => copyText(text, what));
  return b;
}
function whoTag(who) {
  return el("span", { class: "who" + (who === "you" ? " you" : who === "both" ? " both" : ""),
    title: who === "both" ? "ModTrap starts the tool through MO2 with the button below; what is done inside the tool is yours" : "",
    text: who === "you" ? "You" : who === "both" ? "ModTrap starts it · you run it" : "ModTrap" });
}

// ModTrap's own question box, in the page's own look (WHY§61): a Promise of yes or no, or of the text typed.
function modalBox(text, opts) {
  return new Promise((resolve) => {
    const o = opts || {};
    const paras = String(text).split(/\n\s*\n/).map((t) => el("p", { text: t }));
    const input = o.input !== undefined ? el("input", { type: "text", value: o.input, spellcheck: "false" }) : null;
    const yes = el("button", { type: "button", class: "primary", text: o.yes || "Yes" });
    const no = el("button", { type: "button", text: o.no || "No" });
    const box = el("div", { class: "modal", role: "dialog", "aria-modal": "true" }, ...paras, input, el("div", { class: "actions" }, yes, no));
    const back = el("div", { class: "modal-back" }, box);
    const before = document.activeElement;
    const done = (answer) => {
      document.removeEventListener("keydown", key, true);
      back.remove();
      if (before && before.focus) before.focus();
      resolve(answer);
    };
    const key = (ev) => {
      if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); done(input ? null : false); }
      else if (ev.key === "Enter" && (input || document.activeElement !== no)) { ev.preventDefault(); ev.stopPropagation(); done(input ? input.value : true); }
      else if (ev.key === "Tab") {                       // the question keeps the keyboard until it is answered
        const stops = [input, yes, no].filter(Boolean);
        const i = stops.indexOf(document.activeElement);
        ev.preventDefault();
        stops[(i + (ev.shiftKey ? stops.length - 1 : 1)) % stops.length].focus();
      }
    };
    yes.addEventListener("click", () => done(input ? input.value : true));
    no.addEventListener("click", () => done(input ? null : false));
    back.addEventListener("mousedown", (ev) => { if (ev.target === back) done(input ? null : false); });
    document.addEventListener("keydown", key, true);
    document.body.append(back);
    (input || yes).focus();
    if (input) input.select();
  });
}
const confirmBox = (text, yes, no) => modalBox(text, { yes: yes, no: no });
const promptBox = (text, value) => modalBox(text, { input: value || "", yes: "OK", no: "Cancel" });

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
  if (tag === "button" && attrs && typeof attrs.text === "string" && GATED.test(attrs.text)) e.classList.add("gated");
  return e;
}

// ModTrap's own reading and scanning (WHY§92). While any of it goes, nothing that changes the modlist or starts a
// program can be begun: the buttons that would are greyed and do nothing, and the header says what ModTrap is at.
// The server refuses the same starts; the one go waits and takes its step again.
const GATED = /^(Dry run through xEdit|Start the dry run|Demaster Selected|Demaster what is left|Go ahead|Put them in place|Put them back in place|Revert|Take it out again|Start it through MO2|Start the tools one after another|Run the probe|Remove the test mods|Add it for me|Retire ModTrap|Check through xEdit|Check again through xEdit)/;
function settled() { return state.status === "ready" && !(state.working || []).length; }
function atWork() {
  if (state.status === "reading") return "reading the modlist";
  return (state.working || []).map((w) => w.text).join("; ");
}
function showWork() {
  const open = state.status === "ready" || state.status === "reading";
  const busy = open && !settled();
  document.body.classList.toggle("unsettled", busy);
  const chip = $("s-work");
  if (!chip) return;
  chip.hidden = !open;
  chip.className = "chip " + (busy ? "work" : "good");
  chip.replaceChildren(...(busy ? [el("span", { class: "spinner small", "aria-hidden": "true" }), " ModTrap is " + atWork() + "…"] : ["ModTrap is ready"]));
  chip.title = busy ? "Until this has finished, the buttons that change the modlist or start a program are greyed." : "ModTrap has finished reading and scanning: everything can be started.";
}
// The page's fixed buttons are gated by the same words as the ones made here, so that none is forgotten (WHY§100).
document.querySelectorAll("button").forEach((b) => { if (GATED.test(b.textContent.trim())) b.classList.add("gated"); });
document.addEventListener("click", (ev) => {
  const b = ev.target && ev.target.closest ? ev.target.closest("button.gated") : null;
  if (!b || !document.body.classList.contains("unsettled")) return;
  ev.preventDefault(); ev.stopImmediatePropagation();
  toast("Not yet: ModTrap is still " + atWork() + ". This opens again by itself as soon as that has finished.");
}, true);
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
  renderToolsMade();
  renderToolsScan();
  const box = $("tools-list");
  const rows = s.tools.map((t) => el("tr", {},
    el("td", {}, t.title, t.xedit ? el("span", { class: "tag good", text: "ModTrap starts this one for a dry run" }) : null),
    el("td", { class: "mono", text: t.file }),
    el("td", { text: t.output_mod || "" }),
    el("td", {}, toolButton(t.title))));
  const openMo2 = el("button", { type: "button", text: s.mo2 && s.mo2.state === "open" ? "MO2 is open" : "Open this modlist's MO2", disabled: !s.mo2 || s.mo2.state !== "closed" || !!s.mo2.other });
  openMo2.addEventListener("click", toggleMo2);
  box.replaceChildren(el("div", { class: "card" },
    el("h2", { text: plural(s.tools.length, "tool") + " set up in this MO2" }),
    el("p", { class: "dim", text: "These are the executables in MO2's own list. ModTrap only ever starts xEdit. “Output goes to” is the mod MO2 sends a tool's new files to; a plugin found there was made by that tool." }),
    el("p", {}, el("span", { class: "dim", text: "Any of them can be started from here, the way MO2's own Run button does, with the modlist's files in place; it is yours to work, and ModTrap says afterwards which of its output files changed. MO2 itself:  " }), openMo2),
    el("table", { class: "plain" }, el("thead", {}, el("tr", {}, el("th", { text: "Name in MO2" }), el("th", { text: "Program" }), el("th", { text: "Output goes to" }), el("th", {}))),
      el("tbody", {}, ...rows))));
}

// The Settings tab (DESIGN§19): how ModTrap goes about its work. Kept by the server, for every session.
const SETTING_TEXT = [
  ["auto_go", "After the dry run, go ahead without asking", "When the plan leaves nothing to you, the demaster goes on by itself: no “Go ahead” to press. If anything is left to you, or a plugin cannot be demastered, it still stops and asks. Off: it always shows the plan and waits."],
  ["follow", "Show the Process tab when a demaster starts", "“Demaster Selected” takes you to the Process tab, where each stage and task is shown as it happens."],
  ["close_mo2", "Close this modlist's MO2 without asking", "Some steps change MO2's lists and need MO2 closed (putting a demaster in place, Revert, adding a mod). On: ModTrap asks MO2 to close, as a click on its X does, without asking you first. It never ends MO2 by force. The one go closes MO2 for its last step either way: its plan says so."],
  ["open_mo2_after", "Open MO2 again when a demaster is in place", "Starts this modlist's MO2 once the demaster is in place, so that you can look at the result."],
  ["retire_copies", "After a tool's run, retire ModTrap's copy of a plugin the tool made anew", "ModTrap keeps demastered copies in a mod of its own, above the originals. When a tool you start from ModTrap makes such a plugin anew without the mod, ModTrap's copy would hide the new one. On: ModTrap moves its copy into the job's folder by itself (kept, not deleted). Off: it tells you on the Selection tab and waits for the button."],
  ["auto_tools", "After the demaster, start the tools that are to run again, one after another", "Once the demaster is in place, ModTrap starts each tool its steps name (through MO2, as the step's own button does) as soon as the one before it has closed, and the tool's step is done once ModTrap has seen the tool write its output. You still work each tool yourself: press its own Run or Patch button, then close it. A tool that closes without writing anything stops the row. With “go ahead without asking” on as well, one press of “Demaster Selected” carries the whole demaster through to the play test."],
  ["tools_self", "Let a tool that can do so run and close by itself", "Some tools have switches of their own to do their work and close without being touched; ModTrap knows these from the tool's own source, tool by tool (so far: Pandora, which then builds for the mods ticked in it when it was last used). On: ModTrap starts such a tool with those switches, beside the arguments MO2 has for it, and the tool's step is done once it has written its output. Synthesis has no such switch, only its run button: ModTrap presses that button once Synthesis has it ready (never while it is greyed), and asks the window to close when Synthesis's own log says the run has finished; if the press does not start a run, Synthesis stays open and is yours. Off: every tool is started as MO2's Run button starts it, and is yours to work and close. A tool without such switches is always yours to work."],
  ["tool_versions", "Before Synthesis starts, set library versions that do not fit it right", "Synthesis builds its patchers against two libraries whose versions its profile names (Nuget Versions). Versions newer than the Synthesis program can build for make every patcher fail. On: when Synthesis's own last log shows exactly that for the versions its profile is still set to, ModTrap sets the profile to the versions the program was built with (its log states them), in Synthesis's settings file, before it starts Synthesis; a copy of that file as it was is kept with the session, and the change is in the History. Off: ModTrap only says so. Nothing is set without that proof in the log."],
  ["tool_prebuild", "Before Synthesis starts, build its patchers outside MO2 when they are not built", "Synthesis builds its patchers on your PC, and on some PCs that fails inside MO2. On: when Synthesis's own last log names patchers whose build is not there, ModTrap first opens Synthesis by itself, outside MO2, waits until its log and its build records show every patcher built, and closes it again (as a click on its X does); then it starts it through MO2, where Synthesis takes the builds as done. Nothing in Synthesis is pressed, so no patcher runs and nothing is written to the game's folder; do not press Run in it yourself while it is open this way. If opening it changed its settings file, ModTrap puts the file back as it was. Off: Synthesis is only ever started through MO2."],
  ["updates_at_launch", "Look for updates when ModTrap starts", "Asks Nexus and GitHub whether the modlist's mods have newer files, once at each start (Updates tab). It asks only those two, reads the answers and changes nothing. Nexus is asked only when you have given ModTrap your Nexus key; without a key and without a mod from GitHub nothing is asked at all. Off: only when you press “Scan for updates”."],
  ["mo2_leave_alone", "When a tool's compiler crashes inside MO2, have MO2 leave the compiler alone", "MO2 hooks every program a tool starts, so that it sees the modlist's files. Synthesis starts the C# compiler to build its patchers; the compiler reads nothing of the modlist, and on some PCs it crashes when hooked. MO2 has its own list of programs it leaves alone (Settings, Workarounds, Executables Blacklist). On: when Synthesis's own log shows the compiler crashing, ModTrap adds the compiler (csc.exe and VBCSCompiler.dll) to that list in MO2's settings file, with MO2 closed and a copy of the file kept with the session, and the row of tools starts Synthesis once more. Off: ModTrap only says so."],
  ["script_props", "Take script properties that point at the mod out", "A script on another plugin's record can point at a record of the mod. On: that property is taken out, as a list entry is; the script then finds nothing there. Off: such a plugin is left to you, and the mod stays enabled until you have dealt with it. Takes effect at the next dry run."],
];
function renderSettings() {
  const box = $("settings-box");
  if (!box) return;
  const set = state.settings || {};
  const text = JSON.stringify(set);
  if (text === state.settingsText) return;
  state.settingsText = text;
  box.replaceChildren(el("div", { class: "card" }, el("h2", { text: "Settings" }),
    el("p", { class: "dim", text: "They are kept on this PC, in ModTrap's own folder, and hold for every session and modlist. What keeps your modlist safe is not a setting: the probe, the safe folder, the checks after xEdit, and Revert are always on." }),
    ...SETTING_TEXT.map(([key, name, what]) => {
      const box2 = el("input", { type: "checkbox", id: "set-" + key, checked: !!set[key] });
      box2.addEventListener("change", async () => {
        try {
          state.settings = await api("/api/settings", { name: key, value: box2.checked });
          const placed = state.demaster && state.demaster.state === "installed";
          toast(key === "auto_tools" && box2.checked && placed && state.dmChain !== "tools"
            ? "Kept. It holds from the next demaster on. For the one already in place: Demaster, Process, “Start the tools one after another”."
            : "Kept.");
        }
        catch (e) { toast(e.message); box2.checked = !box2.checked; }
        renderSettings();
      });
      return el("div", { class: "setting" }, box2, el("label", { class: "name", for: "set-" + key, text: name }), el("div", { class: "what", text: what }));
    })));
}

// What the modlist's tools made (WHY§74): each tool-made plugin, who made it, and its records by kind.
const KIND_WORDS = { NPC_: "characters", CELL: "cells", WRLD: "worldspaces", LAND: "landscape", REFR: "placed objects", ACHR: "placed characters",
  ARMO: "armour", ARMA: "armour parts", WEAP: "weapons", AMMO: "ammunition", ALCH: "potions and food", INGR: "ingredients", BOOK: "books", MISC: "items",
  LVLI: "levelled items", LVLN: "levelled characters", LVSP: "levelled spells", SPEL: "spells", MGEF: "magic effects", ENCH: "enchantments", PERK: "perks",
  RACE: "races", FACT: "factions", QUST: "quests", DIAL: "dialogue topics", INFO: "dialogue lines", STAT: "static objects", TREE: "trees", FLOR: "plants",
  FURN: "furniture", CONT: "containers", DOOR: "doors", LIGH: "lights", ACTI: "activators", MSTT: "moving statics", GRAS: "grass", LTEX: "land textures",
  TXST: "texture sets", WATR: "water", WTHR: "weather", CLMT: "climates", REGN: "regions", LCTN: "locations", NAVM: "navmeshes", NAVI: "navmesh info",
  OTFT: "outfits", KYWD: "keywords", FLST: "lists", GLOB: "globals", COBJ: "recipes", SOUN: "sounds", SNDR: "sound descriptors", IDLE: "idle animations",
  HDPT: "head parts", SCEN: "scenes", PACK: "packages", IMGS: "image spaces", EXPL: "explosions", PROJ: "projectiles", HAZD: "hazards", SLGM: "soul gems",
  KEYM: "keys", SCRL: "scrolls", SHOU: "shouts", WOOP: "words of power", EFSH: "effect shaders", MATO: "material objects", MATT: "material types" };
const kindText = (k, n) => (KIND_WORDS[k] ? KIND_WORDS[k] + " (" + k + ")" : k) + " " + n.toLocaleString("en-GB");

function renderToolsMade() {
  const box = $("tools-made");
  if (!box) return;
  const d = state.toolsMade, busy = state.toolsMadeBusy;
  const look = el("button", { type: "button", text: busy ? "Reading…" : d ? "Read again" : "Look at what the tools made", disabled: !!busy });
  look.addEventListener("click", async () => {
    state.toolsMadeBusy = true; renderToolsMade();
    try { state.toolsMade = await api("/api/tools/made"); state.toolsMadeFor = state.loaded; } catch (e) { toast(e.message); }
    state.toolsMadeBusy = false; renderToolsMade();
  });
  const kids = [el("div", { class: "card-head" }, el("h2", { text: "What the tools made for this modlist" }), look),
    el("p", { class: "dim", text: "Every plugin in the load order that a tool made: which tool, how ModTrap knows, and what is in it, by kind of record. For Synthesis, the patchers behind each of its plugins are read from Synthesis's own settings file. ModTrap reads record headers only; it takes some seconds on a large list." })];
  if (d) {
    if (state.toolsMadeFor !== state.loaded) kids.push(el("p", { class: "would-needs", text: "The modlist has been read again since this was made: press “Read again”." }));
    if (!d.plugins.length) kids.push(el("p", { class: "dim", text: "No plugin in this load order is known to be made by a tool." }));
    else kids.push(el("table", { class: "plain made" }, el("thead", {}, el("tr", {}, el("th", { text: "Plugin" }), el("th", { text: "Tool" }), el("th", { text: "Made by" }), el("th", { text: "What is in it" }))),
      el("tbody", {}, ...d.plugins.map((r) => {
        const mb = r.made_by;
        const by = mb ? el("td", {}, el("div", { class: "dim small", text: "group “" + mb.group + "”" + (mb.left_out ? " · " + plural(mb.left_out, "plugin") + " left out" : "") }),
          ...(mb.patchers.length ? mb.patchers.map((p) => el("div", { class: p.on ? "" : "dim", text: p.name + (p.on ? "" : " (switched off)") })) : [el("div", { class: "dim", text: "no patcher listed" })]))
          : el("td", { class: "dim", text: r.tool === "Synthesis" && !d.synthesis_settings ? "Synthesis's settings file was not found beside its program" : r.how });
        const shown = r.kinds.slice(0, 10);
        return el("tr", {}, el("td", {}, el("span", { class: "mono", text: r.plugin }), r.active ? null : el("span", { class: "tag", text: "not active" }),
            el("div", { class: "dim small", text: "in “" + r.mod + "” · " + plural(r.masters, "master") })),
          el("td", { text: r.tool }), by,
          el("td", {}, el("div", { text: r.records.toLocaleString("en-GB") + " record" + (r.records === 1 ? "" : "s") + (r.cut ? " (not read to the end)" : "") }),
            el("div", { class: "dim small", text: shown.map((k) => kindText(k[0], k[1])).join(" · ") + (r.kinds.length > shown.length ? " · and " + (r.kinds.length - shown.length) + " more kinds" : "") })));
      }))));
  }
  box.replaceChildren(el("div", { class: "card" }, ...kids));
}

// The scanner (WHY§98): the settings files in force in the modlist, their kinds and the frameworks installed.
function renderToolsScan() {
  const box = $("tools-scan");
  if (!box) return;
  const d = state.toolsScan, busy = state.toolsScanBusy;
  const look = el("button", { type: "button", text: busy ? "Scanning…" : d ? "Scan again" : "Scan the modlist's settings files", disabled: !!busy });
  look.addEventListener("click", async () => {
    state.toolsScanBusy = true; renderToolsScan();
    try { state.toolsScan = await api("/api/tools/scan"); state.toolsScanFor = state.loaded; } catch (e) { toast(e.message); }
    state.toolsScanBusy = false; renderToolsScan();
  });
  const num = (n) => n.toLocaleString("en-GB");
  const kids = [el("div", { class: "card-head" }, el("h2", { text: "Scanner: settings files and frameworks" }), look),
    el("p", { class: "dim", text: "Every settings file that is in force in the modlist, the winning copy of each as the game sees it, and the frameworks that read them while the game runs. ModTrap makes this same scan by itself for the steps of a demaster, and again after it; here you can see what it covers." })];
  if (d) {
    if (state.toolsScanFor !== state.loaded) kids.push(el("p", { class: "would-needs", text: "The modlist has been read again since this was made: press “Scan again”." }));
    if (d.failed) kids.push(el("p", { class: "would-needs", text: "The scanner failed (" + d.failed + ") and looked through nothing. The log says more." }));
    const places = Object.entries(d.by_place || {}).sort((x, y) => y[1] - x[1]).map(([place, n]) => num(n) + " in " + (place === "top folder" ? "a mod's top folder" : place));
    kids.push(el("p", { text: num(d.files) + " settings file" + (d.files === 1 ? "" : "s") + " in force, in the game's folder, " + plural(Math.max(0, d.mods - 2), "enabled mod") + " and Overwrite"
      + (d.hidden ? ", not counting " + num(d.hidden) + " hidden by a mod of higher priority" : "") + ". " + num(d.read) + " read to the end; " + num(d.naming) + " name a plugin of the modlist. It took " + d.seconds + " s." }));
    if (places.length) kids.push(el("p", { class: "dim small", text: "Where they lie: " + places.join(" · ") + "." + (d.tree_folders ? " " + plural(d.tree_folders, "folder") + " of animation replacers found." : "") }));
    kids.push(el("p", { class: "dim small", text: "Looked through: the top folder of each mod; to their end the folders " + d.places.join(", ")
      + (d.trees || []).map((t) => "; and all of " + t.under + " for folders named " + t.folders.join(" or ") + ", wherever they lie").join("")
      + ". Files ending in .ini, .json, .toml, .yaml, .yml or .txt. Every look is written to the Log, with each folder or file that failed and why." }));
    const missed = [];
    if (d.cut) missed.push(num(d.cut) + " folder" + (d.cut === 1 ? "" : "s") + " not listed to the end: " + d.cut_mods.join("; ") + (d.cut > d.cut_mods.length ? "; … the Log names them all" : ""));
    if (d.unreadable) missed.push(num(d.unreadable) + " could not be opened: " + d.unreadable_examples.join("; ") + (d.unreadable > d.unreadable_examples.length ? "; … the Log names them all" : ""));
    if (d.too_large) missed.push(num(d.too_large) + " too large to be a settings file, not read: " + d.too_large_examples.join("; ") + (d.too_large > d.too_large_examples.length ? "; … the Log names them all" : ""));
    if (!d.failed) kids.push(missed.length ? el("div", { class: "would-needs" }, ...missed.map((t) => el("div", { text: t })))
      : el("p", { class: "would-record", text: "Nothing was passed over: every folder was listed to its end and every file read." }));
    const known = d.frameworks.filter((f) => f.read_by_modtrap), other = d.frameworks.filter((f) => !f.read_by_modtrap);
    kids.push(el("h3", { text: "Settings files by kind" }));
    if (!d.kinds.length) kids.push(el("p", { class: "dim", text: "No settings file here is of a kind with a name of its own (a name ending in _WORD.ini, or a condition file of an animation replacer)." }));
    else kids.push(el("table", { class: "plain made" }, el("thead", {}, el("tr", {}, el("th", { text: "Files named" }), el("th", { text: "In force" }), el("th", { text: "Read by ModTrap" }))),
      el("tbody", {}, ...d.kinds.map((k) => el("tr", {}, el("td", {}, el("span", { class: /^…/.test(k.kind) ? "mono" : "", text: k.kind })), el("td", { text: num(k.files) }),
        el("td", { class: k.read_by_modtrap ? "" : "dim", text: k.read_by_modtrap ? "yes, line by line: " + k.framework
          : "found if it names the plugin, then left to you to judge" + (k.why_not ? " (" + k.framework + ": " + k.why_not + ")" : "") }))))));
    kids.push(el("h3", { text: "Frameworks installed" }));
    kids.push(el("p", { class: "dim small", text: "Programs that work inside the game, by their files in SKSE/Plugins of the enabled mods: " + num(d.frameworks.length) + "." }));
    if (known.length) kids.push(el("table", { class: "plain made" }, el("thead", {}, el("tr", {}, el("th", { text: "Framework" }), el("th", { text: "Program file" }), el("th", { text: "In mod" }))),
      el("tbody", {}, ...known.map((f) => el("tr", {}, el("td", { text: f.framework }), el("td", {}, el("span", { class: "mono", text: f.dll })), el("td", { text: f.mod }))))));
    else kids.push(el("p", { class: "dim", text: "None of the frameworks whose settings files ModTrap reads line by line is installed." }));
    if (other.length) {
      const more = el("details", {}, el("summary", { text: plural(other.length, "other program") + ": a settings file of theirs that names the mod's plugin is found and shown to you, with its line" }),
        el("div", { class: "dim small", text: other.map((f) => f.dll.replace(/\.dll$/i, "")).join(" · ") }));
      kids.push(more);
    }
  }
  box.replaceChildren(el("div", { class: "card" }, ...kids));
}

// A menu at the pointer, in the page's own look (WHY§103): rows of {text, run, note, off}; null draws a line.
function menuAt(x, y, title, rows) {
  closeMenu();
  const box = el("div", { class: "ctx", role: "menu" }, title ? el("div", { class: "ctx-title", text: title }) : null);
  for (const r of rows) {
    if (!r) { box.append(el("div", { class: "ctx-line" })); continue; }
    const b = el("button", { type: "button", role: "menuitem", text: r.text, disabled: !!r.off, title: r.note || "" });
    b.addEventListener("click", () => { closeMenu(); r.run(); });
    box.append(b);
  }
  document.body.append(box);
  const w = box.offsetWidth, h = box.offsetHeight;
  box.style.left = Math.max(4, Math.min(x, window.innerWidth - w - 6)) + "px";
  box.style.top = Math.max(4, Math.min(y, window.innerHeight - h - 6)) + "px";
  state.menu = box;
  const first = box.querySelector("button:not([disabled])");
  if (first) first.focus();
}
function closeMenu() { if (state.menu) { state.menu.remove(); state.menu = null; } }
document.addEventListener("mousedown", (ev) => { if (state.menu && !state.menu.contains(ev.target)) closeMenu(); }, true);
document.addEventListener("keydown", (ev) => {
  if (!state.menu) return;
  if (ev.key === "Escape") { ev.preventDefault(); closeMenu(); return; }
  if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
    const stops = [...state.menu.querySelectorAll("button:not([disabled])")];
    const i = stops.indexOf(document.activeElement);
    ev.preventDefault();
    if (stops.length) stops[(i + (ev.key === "ArrowDown" ? 1 : stops.length - 1)) % stops.length].focus();
  }
}, true);
window.addEventListener("blur", closeMenu);
document.addEventListener("scroll", closeMenu, true);

// The menu of one mod (WHY§103), on the Mods tab and on the Updates tab.
async function sourceLink(mod, now) {
  const text = "A source link for “" + mod + "”\n\nThe web address the mod comes from: its page at Nexus, its GitHub repository, or any other page. With a Nexus or GitHub address ModTrap can ask whether a newer file is out; any other address is kept for you to open."
    + "\n\nModTrap keeps the link in its own folder. The mod's own files are not touched.";
  const url = await modalBox(text, { input: now || "", yes: "Keep the link", no: "Cancel" });
  if (url === null) return;
  if (!url.trim() && !now) return;
  try {
    await api("/api/updates/link", { mod, url: url.trim() });
    toast(url.trim() ? "The source link is kept." : "The source link is forgotten.");
    state.upSig = "";
    await loadUpdates();
  } catch (e) { toast(e.message); }
}
async function modMenu(ev, mod) {
  ev.preventDefault();
  const x = ev.clientX, y = ev.clientY;
  if (!state.updates || state.updatesFor !== state.loaded) { try { state.updates = await api("/api/updates"); state.updatesFor = state.loaded; } catch (e) { /* the menu still serves */ } }
  const r = state.updates ? state.updates.rows.find((u) => u.mod === mod) : null;
  const m = findMod(mod);
  const page = r && r.page;
  const rows = [
    { text: r && r.given ? "Change the source link…" : "Add a source link…", run: () => sourceLink(mod, r ? r.given : "") },
    r && r.given ? { text: "Forget my source link", run: async () => { try { await api("/api/updates/link", { mod, url: "" }); toast("The source link is forgotten."); await loadUpdates(); } catch (e) { toast(e.message); } } } : undefined,
    r && r.get ? { text: r.state === "update" ? "Get the newer file" + (r.newest ? " (" + r.newest + ")" : "") + "…" : "Look at its files for a newer one…", note: r.get, run: () => window.open(r.get, "_blank", "noopener,noreferrer") } : undefined,
    r && (r.host === "nexus" || r.host === "github") ? { text: "Ask about this mod now", note: r.host === "nexus" && state.updates && !state.updates.key ? "Nexus is asked only with your key" : "", run: async () => { try { await api("/api/updates/scan", { mods: [mod] }); toast("Asking about “" + mod + "”…"); } catch (e) { toast(e.message); } state.upSig = ""; loadUpdates(); } } : undefined,
    { text: "Open its page", off: !page, note: page ? page : "No page is known for this mod: add a source link", run: () => window.open(page, "_blank", "noopener,noreferrer") },
    { text: "Copy its page's address", off: !page, run: () => navigator.clipboard.writeText(page).then(() => toast("The address is copied."), () => toast("The address could not be copied.")) },
    null,
    { text: "Copy the mod's name", run: () => navigator.clipboard.writeText(mod).then(() => toast("The name is copied."), () => toast("The name could not be copied.")) },
    state.tab === "updates" ? { text: "Show it on the Mods tab", run: () => focusMod(mod) } : { text: "Show it on the Updates tab", run: () => { state.upFilter = { state: "", origin: "", on: false, text: mod }; showTab("updates"); } },
    m && m.row && m.row.classList.contains("tickable") ? { text: state.picked.has(mod) ? "Untick it" : "Tick it, to take it out", run: () => { togglePick(mod, !state.picked.has(mod)); updateTray(); } } : undefined,
  ].filter((v) => v !== undefined);
  menuAt(x, y, mod, rows);
}

// Files dropped on the Updates tab, or chosen with its button (WHY§103): a Wabbajack file, meta files of downloads,
// mods' folders. A Wabbajack file can be gigabytes: only its list is cut out of it here and sent.
async function wabbajackList(file) {
  const view = async (from, to) => new DataView(await file.slice(from, to).arrayBuffer());
  const tailLen = Math.min(file.size, 65557 + 76);
  const tail = await view(file.size - tailLen, file.size);
  let e = -1;
  for (let i = tail.byteLength - 22; i >= 0; i--) if (tail.getUint32(i, true) === 0x06054b50) { e = i; break; }
  if (e < 0) throw new Error("it is not a Wabbajack file (no archive's directory was found in it)");
  let cdSize = tail.getUint32(e + 12, true), cdOff = tail.getUint32(e + 16, true);
  if (cdOff === 0xFFFFFFFF || cdSize === 0xFFFFFFFF || tail.getUint16(e + 10, true) === 0xFFFF) {
    const l = e - 20;
    if (l < 0 || tail.getUint32(l, true) !== 0x07064b50) throw new Error("its directory could not be found");
    const at = Number(tail.getBigUint64(l + 8, true));
    const rec = await view(at, at + 56);
    if (rec.getUint32(0, true) !== 0x06064b50) throw new Error("its directory could not be read");
    cdSize = Number(rec.getBigUint64(40, true)); cdOff = Number(rec.getBigUint64(48, true));
  }
  const cd = await view(cdOff, cdOff + cdSize);
  const words = new TextDecoder();
  let p = 0;
  while (p + 46 <= cd.byteLength && cd.getUint32(p, true) === 0x02014b50) {
    const method = cd.getUint16(p + 10, true), n = cd.getUint16(p + 28, true), x = cd.getUint16(p + 30, true), c = cd.getUint16(p + 32, true);
    let comp = cd.getUint32(p + 20, true), plain = cd.getUint32(p + 24, true), off = cd.getUint32(p + 42, true);
    if (n === 7 && words.decode(new Uint8Array(cd.buffer, cd.byteOffset + p + 46, n)) === "modlist") {
      let q = p + 46 + n;
      const end = q + x;
      while (q + 4 <= end) {                              // the entry's large sizes, where it has them
        const id = cd.getUint16(q, true), size = cd.getUint16(q + 2, true);
        if (id === 1) {
          let r = q + 4;
          if (plain === 0xFFFFFFFF) { plain = Number(cd.getBigUint64(r, true)); r += 8; }
          if (comp === 0xFFFFFFFF) { comp = Number(cd.getBigUint64(r, true)); r += 8; }
          if (off === 0xFFFFFFFF) off = Number(cd.getBigUint64(r, true));
        }
        q += 4 + size;
      }
      const head = await view(off, off + 30);
      if (head.getUint32(0, true) !== 0x04034b50) throw new Error("its list could not be found");
      const start = off + 30 + head.getUint16(26, true) + head.getUint16(28, true);
      return { method, blob: file.slice(start, start + comp) };
    }
    p += 46 + n + x + c;
  }
  throw new Error("it holds no list: it is not a Wabbajack file");
}
async function sendList(file) {
  let part;
  if (/\.wabbajack$/i.test(file.name)) part = await wabbajackList(file);
  else part = { method: 0, blob: file };                 // the list's own text, taken out of such a file by hand
  const q = "?name=" + encodeURIComponent(file.name) + "&size=" + file.size + "&date=" + Math.floor(file.lastModified || 0) + "&method=" + part.method;
  const r = await fetch("/api/updates/upload" + q, { method: "POST", headers: { "X-ModTrap-Token": TOKEN, "Content-Type": "application/octet-stream" }, body: part.blob });
  let data = {};
  try { data = await r.json(); } catch (e) { /* no answer to read */ }
  if (!r.ok) throw new Error(data.error || "the list was not accepted");
  return data;
}
const readText = (file) => file.slice(0, 64 * 1024).text();
const entryFile = (dir, name) => new Promise((resolve) => dir.getFile(name, {}, (fe) => fe.file(resolve, () => resolve(null)), () => resolve(null)));
const entryList = (dir) => new Promise((resolve) => {
  const all = [], reader = dir.createReader();
  const more = () => reader.readEntries((got) => { if (!got.length) resolve(all); else { all.push(...got); more(); } }, () => resolve(all));
  more();
});
async function takeForUpdates(files, entries) {
  // files: [{file, folder}] chosen or dropped singly; entries: dropped folders.
  const metas = [], lists = [], passed = [];
  const one = (file, folder) => {
    const low = file.name.toLowerCase();
    if (low.endsWith(".wabbajack") || low === "modlist") lists.push(file);
    else if (low.endsWith(".meta") || low === "meta.ini") metas.push({ file, folder: low === "meta.ini" ? folder || "" : "" });
    else passed.push(file.name);
  };
  for (const f of files) one(f.file, f.folder);
  state.updatesTaking = "looking through what was dropped";
  renderUpdates();
  for (const dir of entries) {
    // A mod's folder (its meta.ini), a folder of mods (each one's meta.ini), a folder of downloads (its .meta files).
    const own = await entryFile(dir, "meta.ini");
    if (own) metas.push({ file: own, folder: dir.name });
    for (const e of await entryList(dir)) {
      if (e.isDirectory) { const f = await entryFile(e, "meta.ini"); if (f) metas.push({ file: f, folder: e.name }); }
      else if (/\.(meta|wabbajack)$/i.test(e.name)) { const f = await new Promise((res) => e.file(res, () => res(null))); if (f) one(f, ""); }
    }
  }
  const told = { archives: 0, mods: 0, passed: passed.map((n) => n + ": not a meta file or a Wabbajack file") };
  try {
    for (let i = 0; i < metas.length;) {
      const batch = [];
      let bytes = 0;
      while (i < metas.length && batch.length < 300 && bytes < 1500000) {
        const text = await readText(metas[i].file);
        batch.push({ name: metas[i].file.name, folder: metas[i].folder, text });
        bytes += text.length + 200;
        i++;
      }
      state.updatesTaking = "taking in meta files: " + i + " of " + metas.length;
      renderUpdates();
      const got = await api("/api/updates/metas", { files: batch });
      told.archives += got.archives; told.mods += got.mods; told.passed.push(...got.passed);
    }
    for (const f of lists.slice(0, 1)) {
      state.updatesTaking = "taking the list out of “" + f.name + "”";
      renderUpdates();
      await sendList(f);
      told.list = f.name;
    }
  } catch (e) { told.error = e.message; }
  state.updatesTaking = "";
  state.updatesTold = told;
  await loadUpdates();
}
function updatesDropped(ev) {
  const dt = ev.dataTransfer;
  if (!dt) return;
  const items = dt.items ? Array.from(dt.items).filter((i) => i.kind === "file") : [];
  const entries = items.map((i) => (i.webkitGetAsEntry ? i.webkitGetAsEntry() : null));
  const files = Array.from(dt.files || []);
  const dirs = entries.filter((e) => e && e.isDirectory);
  const singles = entries.some(Boolean) ? files.filter((f, i) => !(entries[i] && entries[i].isDirectory)) : files;
  takeForUpdates(singles.map((file) => ({ file, folder: "" })), dirs);
}
function updatesChosen(input) {
  const files = Array.from(input.files || []).map((file) => {
    const parts = (file.webkitRelativePath || "").split("/");
    return { file, folder: parts.length >= 2 ? parts[parts.length - 2] : "" };
  });
  // Of a chosen folder only what is at its top or one folder down is taken, as with a dropped one.
  const near = files.filter((f) => ((f.file.webkitRelativePath || "").split("/").length <= 3));
  input.value = "";
  takeForUpdates(near, []);
}

// The update check (MT37, WHY§101): where each mod came from, and whether a newer file of it is out.
const UP_STATE = { update: ["Update out", "bad"], maybe: ["Unclear", "warn"], current: ["Up to date", "good"], "not asked": ["Not asked yet", ""], none: ["Cannot be asked", ""], gone: ["Gone from its page", "warn"] };
const UP_ORIGIN = { list: "the list's own", added: "added afterwards", modtrap: "added by ModTrap", "": "" };
const UP_HOST = { nexus: "Nexus", github: "GitHub", url: "web address", "": "not known" };
async function loadUpdates() {
  if (state.updatesBusy || state.status !== "ready") return;
  state.updatesBusy = true;
  try { state.updates = await api("/api/updates"); state.updatesFor = state.loaded; } catch (e) { state.updatesError = e.message; }
  state.updatesBusy = false;
  renderUpdates();
  const d = state.updates;
  clearTimeout(state.updatesTimer);
  if (d && (d.scan.state === "going" || d.list.reading)) state.updatesTimer = setTimeout(loadUpdates, 2000);
}
function upFilter(key, value) { state.upFilter = Object.assign({ state: "", origin: "", on: false, text: "" }, state.upFilter, { [key]: value }); renderUpdates(true); }
function renderUpdates(listOnly) {
  const head = $("updates-head"), box = $("updates-list");
  if (!head || !box) return;
  const d = state.updates;
  const num = (n) => (n || 0).toLocaleString("en-GB");
  const badge = $("updates-count");
  if (badge) { badge.hidden = !(d && d.counts.update); badge.textContent = d ? d.counts.update : ""; }
  if (!d) { head.replaceChildren(el("div", { class: "card" }, el("p", { class: "dim", text: state.updatesError || "Reading where the mods came from…" }))); box.replaceChildren(); return; }
  const f = Object.assign({ state: "", origin: "", on: false, text: "" }, state.upFilter);
  // What the owner is typing in the head is not wiped by a look at how the scan is getting on.
  const typing = head.contains(document.activeElement) && document.activeElement.tagName === "INPUT" && document.activeElement.value;
  if (!listOnly && !typing) {
    const going = d.scan.state === "going";
    const scan = el("button", { type: "button", class: "primary", text: going ? "Scanning…" : "Scan for updates", disabled: going });
    scan.addEventListener("click", async () => { try { await api("/api/updates/scan", {}); } catch (e) { toast(e.message); } loadUpdates(); });
    const stop = going ? el("button", { type: "button", text: "Stop the scan" }) : null;
    if (stop) stop.addEventListener("click", async () => { try { await api("/api/updates/stop", {}); } catch (e) { toast(e.message); } });
    const kids = [el("div", { class: "card-head" }, el("h2", { text: "Updates" }), el("span", {}, stop, " ", scan)),
      el("p", { class: "dim", text: "Where each mod came from, read from MO2's own records on this PC, and whether a newer file of it is out, asked of Nexus and GitHub. ModTrap only asks and reads: it downloads nothing and changes nothing in the modlist." })];
    if (going) kids.push(el("p", { class: "would-needs" }, el("span", { class: "spinner small", "aria-hidden": "true" }), " ModTrap is " + (d.scan.text || "scanning") + "…"));
    if (d.scan.error) kids.push(el("p", { class: "would-needs", text: d.scan.error }));
    const last = d.last;
    if (last && last.nexus) {
      const when = new Date(last.when * 1000).toLocaleString("en-GB");
      kids.push(el("p", { text: "Last scan, " + when + ": Nexus was asked about " + plural(last.nexus.asked, "mod") + (last.nexus.left ? ", " + num(last.nexus.left) + " are left for the next scan" : "")
        + "; GitHub about " + plural(last.github.asked, "repository", "repositories") + (last.github.left ? ", " + num(last.github.left) + " left" : "") + "." }));
      for (const why of [last.nexus.why_stopped, last.github.why_stopped]) if (why) kids.push(el("p", { class: "dim small", text: why.charAt(0).toUpperCase() + why.slice(1) + "." }));
      if (last.nexus.day_left !== null && last.nexus.day_left !== undefined) kids.push(el("p", { class: "dim small", text: "Your Nexus account has " + num(last.nexus.day_left) + " questions left today and " + num(last.nexus.hour_left) + " this hour; ModTrap stops well short of both." }));
    } else kids.push(el("p", { class: "dim", text: "No scan has been made yet." }));
    // The Nexus key.
    const keyIn = el("input", { type: "password", autocomplete: "off", spellcheck: "false", placeholder: d.key ? "a key is kept; paste another to replace it" : "paste your personal Nexus key here", size: "46" });
    const keep = el("button", { type: "button", text: "Keep the key" });
    keep.addEventListener("click", async () => { try { await api("/api/updates/key", { key: keyIn.value }); keyIn.value = ""; toast("The key is kept on this PC."); } catch (e) { toast(e.message); } loadUpdates(); });
    const forget = d.key ? el("button", { type: "button", text: "Forget the key" }) : null;
    if (forget) forget.addEventListener("click", async () => { try { await api("/api/updates/key", { key: null }); } catch (e) { toast(e.message); } loadUpdates(); });
    kids.push(el("h3", { text: "Your Nexus key" }),
      el("p", { class: "dim small", text: "Nexus answers a program only with a key of your account: you make one on Nexus, in your account's settings, under API keys, as a personal key. ModTrap keeps it on this PC, protected by Windows for your Windows account. It is sent to Nexus only, never shown again, and never written to the log or to a session file." }),
      el("p", {}, el("span", { class: "tag " + (d.key ? "good" : "warn"), text: d.key ? "a key is kept" : "no key: Nexus is not asked" }), " ", keyIn, " ", keep, " ", forget));
    // Files given by hand: a drop zone, with its button in the middle.
    const pickFiles = el("input", { type: "file", multiple: "multiple", accept: ".wabbajack,.meta,.ini", hidden: "hidden" });
    pickFiles.addEventListener("change", () => updatesChosen(pickFiles));
    const pickDir = el("input", { type: "file", hidden: "hidden" });
    pickDir.setAttribute("webkitdirectory", "");
    pickDir.addEventListener("change", () => updatesChosen(pickDir));
    const add = el("button", { type: "button", class: "primary", text: "Add files…" });
    add.addEventListener("click", () => pickFiles.click());
    const addDir = el("button", { type: "button", text: "Add a folder…" });
    addDir.addEventListener("click", () => pickDir.click());
    const zone = el("div", { class: "upzone", id: "upzone" },
      el("div", { class: "upzone-title", text: "Drop files here that say where mods come from" }),
      el("div", { class: "upzone-buttons" }, add, addDir, pickFiles, pickDir),
      el("div", { class: "dim small", text: "The modlist's .wabbajack file · .meta files of downloads, or the whole downloads folder · a mod's folder, or the whole mods folder (for their meta.ini). ModTrap only reads them; of a Wabbajack file only its list is taken." }));
    zone.addEventListener("dragenter", () => zone.classList.add("over"));
    zone.addEventListener("dragleave", (ev) => { if (!zone.contains(ev.relatedTarget)) zone.classList.remove("over"); });
    zone.addEventListener("drop", () => zone.classList.remove("over"));
    kids.push(el("h3", { text: "Sources given by hand" }), zone);
    if (state.updatesTaking) kids.push(el("p", { class: "would-needs" }, el("span", { class: "spinner small", "aria-hidden": "true" }), " ModTrap is " + state.updatesTaking + "…"));
    const told = state.updatesTold;
    if (told) {
      const bits = [];
      if (told.list) bits.push("the list of “" + told.list + "” is being read");
      if (told.archives) bits.push(plural(told.archives, "download's meta file") + " taken");
      if (told.mods) bits.push(plural(told.mods, "mod's meta file") + " taken");
      if (!bits.length && !told.error) bits.push("nothing in it names a source");
      kids.push(el("p", { class: told.error ? "would-needs" : "would-record", text: told.error ? "That did not work: " + told.error + "." : "Taken in: " + bits.join("; ") + "." }));
      if (told.passed.length) kids.push(el("details", {}, el("summary", { class: "dim small", text: plural(told.passed.length, "file") + " passed over" }), ...told.passed.slice(0, 40).map((t) => el("div", { class: "dim small", text: t }))));
    }
    if (d.list.reading) kids.push(el("p", { class: "would-needs" }, el("span", { class: "spinner small", "aria-hidden": "true" }), " ModTrap is " + (d.list.text || "reading the Wabbajack list") + "… A large list takes a few minutes the first time."));
    if (d.list.error) kids.push(el("p", { class: "would-needs", text: d.list.error }));
    const g = d.given || { links: 0, archives: 0, mods: 0 };
    const have = [];
    if (d.list.named && d.list.counts) have.push("the Wabbajack list “" + d.list.file + "”: " + (d.list.name || "a list") + (d.list.version ? " " + d.list.version : "") + ", " + plural(d.list.counts.archives, "archive") + ", " + plural(d.list.counts.mods, "mod folder"));
    if (g.archives) have.push(plural(g.archives, "download's meta file"));
    if (g.mods) have.push(plural(g.mods, "mod's meta file"));
    if (g.links) have.push(plural(g.links, "source link") + " of your own (right-click a mod)");
    kids.push(el("p", { class: have.length ? "" : "dim", text: have.length ? "ModTrap has: " + have.join("; ") + "." : "Nothing has been given yet. Right-click a mod below to add a source link for it alone." }));
    // The Wabbajack file by its path, for a file too awkward to drag.
    const pathIn = el("input", { type: "text", spellcheck: "false", placeholder: "or the Wabbajack file's full path, such as C:\\Lists\\Example\\Example List.wabbajack", size: "70" });
    const name = el("button", { type: "button", text: "Read this file" });
    name.addEventListener("click", async () => { try { await api("/api/updates/list", { path: pathIn.value }); pathIn.value = ""; } catch (e) { toast(e.message); } loadUpdates(); });
    const drop = d.list.named ? el("button", { type: "button", text: "Forget the Wabbajack list" }) : null;
    if (drop) drop.addEventListener("click", async () => { try { await api("/api/updates/list", { path: "" }); } catch (e) { toast(e.message); } loadUpdates(); });
    kids.push(el("p", {}, pathIn, " ", name, " ", drop));
    // The two parts that are set up once fold away once they are, so that the list is near the top (WHY§104).
    state.upOpen = state.upOpen || {};
    const parts = [];
    let cur = null;
    for (const k of kids) {
      if (!k) continue;
      if (k.tagName === "H3") {
        const title = k.textContent, isKey = /key/i.test(title);
        const hint = isKey ? (d.key ? "a key is kept" : "no key: Nexus is not asked") : (have.length ? have.length + " kind" + (have.length === 1 ? "" : "s") + " of record given" : "nothing given yet");
        cur = el("details", { class: "upfold" }, el("summary", {}, el("b", { text: title }), el("span", { class: "dim", text: " · " + hint })));
        const wanted = state.upOpen[title] !== undefined ? state.upOpen[title] : (isKey ? !d.key : !have.length) || !!state.updatesTaking || d.list.reading || !!d.list.error;
        if (wanted) cur.setAttribute("open", "");
        const mine = cur;
        cur.addEventListener("toggle", () => { state.upOpen[title] = mine.open; });
        parts.push(cur);
      } else if (cur) cur.append(k); else parts.push(k);
    }
    head.replaceChildren(el("div", { class: "card" }, ...parts));
  }
  // The list, as the modlist itself is laid out (WHY§104): lowest priority first, each separator heading its mods.
  const sig = JSON.stringify([d.rows.map((r) => r.state.charAt(0) + (r.newest || "") + (r.given ? "g" : "") + r.host.charAt(0)).join(""), d.origins, d.given, d.list.named, f, state.loaded, [...(state.upCollapsed || [])]]);
  const going = d.scan.state === "going";
  if (state.upSig === sig && box.firstChild) return;
  if (going && box.firstChild && state.upDrawn && Date.now() - state.upDrawn < 10000 && state.upF === JSON.stringify(f) + [...(state.upCollapsed || [])].join("|")) return;
  state.upSig = sig; state.upDrawn = Date.now(); state.upF = JSON.stringify(f) + [...(state.upCollapsed || [])].join("|");
  state.upCollapsed = state.upCollapsed || new Set();
  const pick = (key, value, label, n) => {
    const b = el("button", { type: "button", class: "chip link" + (f[key] === value ? " on" : ""), text: label + (n === undefined ? "" : " " + num(n)) });
    b.addEventListener("click", () => upFilter(key, value));
    return b;
  };
  const search = el("input", { type: "search", placeholder: "Search by mod or note", value: f.text, size: "26" });
  search.addEventListener("input", () => { state.upFilter = Object.assign({}, f, { text: search.value }); clearTimeout(state.upTimer); state.upTimer = setTimeout(() => { renderUpdates(true); const again = document.querySelector("#updates-list input[type=search]"); if (again) { again.focus(); again.setSelectionRange(again.value.length, again.value.length); } }, 300); });
  const onlyOn = el("input", { type: "checkbox", id: "up-on" });
  onlyOn.checked = !!f.on;
  onlyOn.addEventListener("change", () => upFilter("on", onlyOn.checked));
  const foldAll = el("button", { type: "button", text: "Fold all" }), unfoldAll = el("button", { type: "button", text: "Unfold all" });
  const known = d.list.named && d.list.counts;
  const bar = [el("div", { class: "chips" }, el("span", { class: "dim", text: "State:" }), pick("state", "", "All", d.rows.length),
    ...["update", "maybe", "current", "not asked", "none", "gone"].filter((k) => d.counts[k]).map((k) => pick("state", k, UP_STATE[k][0], d.counts[k]))),
    el("div", { class: "chips" }, el("span", { class: "dim", text: "Mods:" }), pick("origin", "", "All"),
      ...(known ? [pick("origin", "list", "The list's own", d.origins.list), pick("origin", "added", "Added afterwards", d.origins.added)] : []),
      pick("origin", "modtrap", "Added by ModTrap", d.origins.modtrap),
      known ? null : el("span", { class: "dim small", text: "Give the modlist's Wabbajack file above to tell the list's own mods from the ones added afterwards." })),
    el("div", { class: "chips" }, search, el("label", { for: "up-on" }, onlyOn, " enabled mods only"), foldAll, unfoldAll)];
  const text = (f.text || "").trim().toLowerCase();
  const filtering = !!(f.state || f.origin || f.on || text);
  const fits = (r) => (!f.state || r.state === f.state) && (!f.origin || r.origin === f.origin) && (!f.on || r.enabled)
    && (!text || r.mod.toLowerCase().includes(text) || (r.comments || "").toLowerCase().includes(text) || (r.notes || "").toLowerCase().includes(text));
  const byName = new Map(d.rows.map((r) => [r.mod, r]));
  // The groups, from the modlist as the Mods tab has it: the same order, the same separators.
  const groups = [{ sep: null, rows: [] }];
  for (const m of [...(state.mods || [])].reverse()) {
    if (m.kind === "separator") groups.push({ sep: m, rows: [] });
    else if (byName.has(m.name)) groups[groups.length - 1].rows.push(byName.get(m.name));
  }
  const link = (r) => {
    if (!r.page) return null;
    const a = el("a", { target: "_blank", rel: "noopener noreferrer", text: "its page" });
    a.setAttribute("href", r.page);
    return a;
  };
  const getButton = (r) => {
    if (!r.get) return null;
    const sure = r.state === "update";
    const b = el("button", { type: "button", class: "upget" + (sure ? "" : " unsure"), text: "↑", "aria-label": "Get the newer file of " + r.mod,
      title: (sure ? "Get the newer file" + (r.newest ? " (" + r.newest + ")" : "") : "Unclear whether a newer file is out: look at the mod's files")
        + ". Opens its page" + (r.host === "nexus" ? " at Nexus, for a download through MO2" : " at GitHub") + ". ModTrap itself downloads nothing." });
    b.addEventListener("click", (ev) => { ev.stopPropagation(); window.open(r.get, "_blank", "noopener,noreferrer"); });
    return b;
  };
  const COLS = 8;
  const body = el("tbody", {});
  let shown = 0;
  const seps = [];
  for (const g of groups) {
    const rows = g.rows.filter(fits);
    if (g.sep) {
      if (filtering && !rows.length) continue;
      seps.push(g.sep.name);
      const folded = state.upCollapsed.has(g.sep.name) && !filtering;
      const outs = g.rows.filter((r) => r.state === "update").length;
      const btn = el("button", { type: "button", class: "gtoggle", "aria-expanded": folded ? "false" : "true" }, el("span", { class: "arrow", text: folded ? "▸" : "▾" }), g.sep.name.replace(/_separator$/i, ""));
      btn.addEventListener("click", () => { if (state.upCollapsed.has(g.sep.name)) state.upCollapsed.delete(g.sep.name); else state.upCollapsed.add(g.sep.name); renderUpdates(true); });
      body.append(el("tr", { class: "sep" }, el("td", { colSpan: COLS }, btn,
        el("span", { class: "dim ginfo", text: (filtering ? rows.length + " of " + g.rows.length + " shown" : plural(g.rows.length, "mod")) }),
        outs ? el("span", { class: "tag bad", text: plural(outs, "update") + " out" }) : null)));
      if (folded) continue;
    } else if (!rows.length) continue;
    for (const r of rows) {
      shown++;
      body.append(el("tr", { class: r.enabled ? "" : "off", "data-mod": r.mod, title: "Right-click for more: add a source link, get the newer file, ask about this mod now" },
        el("td", { class: "c-num", text: r.priority < 0 ? "" : r.priority }),
        el("td", { class: "modname" }, modLink(r.mod), r.enabled ? null : el("span", { class: "tag", text: "disabled" }), r.origin ? el("div", { class: "dim small", text: UP_ORIGIN[r.origin] }) : null),
        el("td", {}, (UP_HOST[r.host] || r.host) + (r.id ? " " + r.id : ""), r.page ? el("div", { class: "small" }, link(r)) : null,
          r.given ? el("div", { class: "dim small", text: "by your link" }) : null),
        el("td", { text: r.version || "" }),
        el("td", { class: "small upnote" }, r.comments || "", r.notes ? el("span", { class: "tag", title: r.notes, text: "note" }) : null),
        el("td", { class: "upstate" }, el("span", { class: "tag " + UP_STATE[r.state][1], text: UP_STATE[r.state][0] }), r.newest ? el("div", { class: "small", text: r.newest + (r.when ? " · " + r.when : "") }) : null),
        el("td", { class: "c-get" }, getButton(r)),
        el("td", { class: "small" }, r.text.charAt(0).toUpperCase() + r.text.slice(1) + ".", r.asked ? el("span", { class: "dim", text: " Asked " + r.asked + "." }) : null)));
    }
  }
  foldAll.addEventListener("click", () => { for (const n of seps) state.upCollapsed.add(n); renderUpdates(true); });
  unfoldAll.addEventListener("click", () => { state.upCollapsed.clear(); renderUpdates(true); });
  const table = el("table", { class: "updates", id: "updates-table" }, el("thead", {}, el("tr", {}, el("th", { class: "c-num", title: "The mod's place in MO2's list: a higher number wins a conflict", text: "Priority" }), el("th", { text: "Mod" }), el("th", { text: "From" }), el("th", { text: "Installed" }),
    el("th", { title: "What you wrote of the mod in MO2: its Notes column, and a longer note where there is one", text: "Notes" }), el("th", { title: "Whether a newer file of the mod is out, by the last asking", text: "Update" }),
    el("th", { class: "c-get", title: "Get the newer file: opens the mod's page for it", text: "" }), el("th", { text: "What is known" }))), body);
  table.addEventListener("contextmenu", (ev) => { const tr = ev.target.closest("tr[data-mod]"); if (tr) modMenu(ev, tr.dataset.mod); });
  box.replaceChildren(el("div", { class: "card" }, ...bar,
    el("p", { class: "dim small", text: num(shown) + " of " + num(d.rows.length) + " mods shown, in the modlist's own order: lowest priority first, under their separators." }),
    shown || seps.length ? table : el("p", { class: "dim", text: "No mod matches." })));
}

function renderState(s) {
  state.session = s.session;
  renderSessions(s);
  $("version").textContent = s.version ? "version " + s.version + (s.version_differs ? " · files differ" : "") : "";
  $("version").title = s.version_differs ? "The files in ModTrap's folder are not exactly those of this version: an update unpacked over an older folder, a copy cut short, or files changed by hand. Best unpack an update into an empty folder." : "";
  if (document.activeElement !== $("folder") && s.folder && (!$("folder").value || s.status === "ready")) $("folder").value = s.folder;
  const ready = s.status === "ready";
  $("summary").hidden = !ready;
  $("tabs").hidden = !ready;
  $("groups").hidden = !ready;
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
  const toolsKey = JSON.stringify(s.tools) + "|" + (s.tool ? s.tool.state + s.tool.title : "") + "|" + (s.mo2 ? s.mo2.state + s.mo2.other : "");
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
    ticksJob: state.ticksJob === undefined ? null : state.ticksJob,
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
    state.ticksJob = typeof ui.ticksJob === "string" ? ui.ticksJob : undefined;
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
      // A ticked mod stays ticked once it is disabled (its plugins no longer count as provided): the demaster
      // disables it, and the steps that are left are still its steps (WHY§61).
      if (m && m.kind === "mod" && (m.plugins.length || m.files)) state.picked.add(n);
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
    $("group-count").textContent = state.picked.size;
    $("group-count").classList.toggle("on", state.picked.size > 0);
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

// --- the demaster itself (DESIGN§6.3 to §6.5), behind the switch (WHY§46) -------------------------------------------

function sameMods(a, b) { return JSON.stringify([...a].sort()) === JSON.stringify([...b].sort()); }

function updateDemasterButton() {
  const b = $("demaster");
  const d = state.demaster;
  const job = state.job;
  const dryDone = job && job.state === "done" && !job.past && !job.stale && sameMods(job.plan.trapped_mods, state.picked);
  const locked = state.session && state.session.locked;
  const going = d && (d.state === "working" || d.state === "verified");
  const dryBusy = job && !["done", "failed", "stopped"].includes(job.state);
  const probing = state.probe && state.probe.state === "working";
  const probe = state.changes ? probeReason() : "";
  b.disabled = !state.changes || !state.picked.size || !!locked || !!going || !!dryBusy || !!probing;
  b.title = !state.changes ? "Switched off. ModTrap changes a modlist only when it is started with --allow-changes, which is for once it has been proven on your PC. Until then the Steps tab lists the steps to do by hand." :
    locked ? "Not now: " + locked : !state.picked.size ? "Tick a mod first" : probing ? "The probe is running; the demaster follows by itself if you started it from here" :
    dryBusy ? "The dry run is going" : going ? "A demaster is already in hand: see below" :
    probe ? "First runs the probe (" + probe + "), then goes on by itself" :
    !dryDone ? "Runs the dry run first, then shows what ModTrap would do and asks before doing it" : "Shows what ModTrap would do, and asks before doing it";
  const pg = $("process-go");                       // the same button on the Process tab
  pg.disabled = b.disabled; pg.title = b.title;
  // What the button will do first is said in plain sight, not only when the mouse rests on it (WHY§60).
  const hint = $("demaster-hint");
  hint.className = probe && state.picked.size ? "would-needs" : "dim";
  hint.textContent = probing ? "The probe is running (Tools tab)." :
    probe && state.picked.size ? "“Demaster Selected” will first run the probe again (a few minutes, on invented test plugins, undone afterwards): " + probe + ". Then it goes on by itself." :
    state.changes ? "“Demaster Selected” does the whole demaster in one go: the dry run if needed, its plan for you to confirm, then everything. “Dry run through xEdit” only looks, and changes nothing." :
    "The dry run starts your xEdit through MO2 and lists what would be taken out of each dependant. It changes nothing.";
}

// "Demaster Selected" in one go (WHY§59): the dry run first if there is none of the modlist as it is now, then
// the plan and one question, then everything ModTrap can do by itself.
// A step of the one go started from the Process tab stays there: that tab shows it, with its buttons (WHY§71).
function goTab(name) { if (state.tab !== "process") showTab(name); }
const BEING_READ = /being read|still at work/;

async function demasterGo() {
  if (!state.changes || !state.picked.size) { showTab("selection"); return; }
  if ((state.settings || {}).follow) showTab("process");            // the owner's setting: watch it where it shows
  if (state.probe && state.probe.state === "working") { goTab("tools"); return; }
  if (probeReason()) {
    if (!await confirmBox("Before ModTrap changes real plugins it proves its scripts on invented test plugins, in your own MO2 and xEdit (the probe).\n\n" +
        probeReason() + ".\n\nRun the probe now? It takes a few minutes and undoes itself. The demaster then goes on by itself.")) return;
    try {
      state.probe = await api("/api/probe/start", {});
      state.probeError = ""; state.probeText = ""; state.dmChain = "probe";
      goTab("tools");
      toast("The probe has started. The demaster follows when it has passed.");
      tick();
    } catch (e) {
      if (OTHER_MO2.test(e.message)) { waitThen("mo2", demasterGo); return; }
      state.dmChain = ""; state.dmError = e.message; goTab("selection"); renderDemaster(true);
    }
    return;
  }
  // ModTrap reads the modlist again after a probe, a Revert or a Rescan. Until it has, nothing can start: the one
  // go waits for it instead of giving up (WHY§71).
  if (!settled()) { waitForModlist(); return; }
  const job = state.job;
  const dryDone = job && job.state === "done" && !job.past && !job.stale && sameMods(job.plan.trapped_mods, state.picked);
  goTab("selection");
  if (dryDone) {
    await askDemasterPlan();
    autoGo();
    if (state.dmChain === "wait") return;                              // the modlist is being read: it goes on by itself
    if (!state.dmError || !/dry run/.test(state.dmError)) return;      // the plan is shown, or something else is wrong
  }
  try {
    state.dmError = ""; state.dmPlan = null;
    state.dmChainFrom = job ? job.id : "";
    await api("/api/dryrun/start", { mods: [...state.picked] });
    state.dmChain = "dry";
    state.jobSeen = "";
    goTab("job");
    toast("First the dry run: xEdit reads what depends on the mod. The plan follows by itself.");
    tick();
  } catch (e) {
    if (BEING_READ.test(e.message)) { waitForModlist(); return; }
    if (OTHER_MO2.test(e.message)) { waitThen("mo2", demasterGo); return; }
    state.dmChain = ""; state.dmError = e.message; renderDemaster(true);
  }
}

// The one go holds its place while something stands in its way, and takes the same step again once it is gone
// (WHY§71, WHY§77): the modlist being read, or another modlist's MO2 being open.
const OTHER_MO2 = /Another Mod Organizer is open/;
const WAITS = {
  modlist: { over: () => settled(), text: "ModTrap is still reading or scanning the modlist; the demaster goes on by itself when it has finished." },
  mo2: { over: () => !(state.mo2 && state.mo2.other), text: "Another Mod Organizer is open, for another modlist. MO2 hands every command to the one that is already open, so ModTrap's would go to the wrong modlist. Close that MO2: the demaster goes on by itself, from the step it stopped at." },
};
function waitThen(kind, retry, quiet) {
  state.dmChain = "wait";
  state.dmWait = { kind: kind, retry: retry };
  state.dmError = "";
  if (!quiet) toast(WAITS[kind].text);
  renderDemaster(true);
  state.processText = ""; renderProcess();
}
function waitForModlist() { waitThen("modlist", demasterGo); }
function waitNote() {
  const w = state.dmChain === "wait" && state.dmWait;
  if (!w) return null;
  const now = el("button", { type: "button", text: "Try again now" });
  now.addEventListener("click", () => { tick(); });
  const stop = el("button", { type: "button", text: "Stop waiting" });
  stop.addEventListener("click", () => { state.dmChain = ""; state.dmWait = null; renderDemaster(true); state.processText = ""; renderProcess(); });
  return el("p", { class: "wait-note", role: "status" }, "Paused: " + WAITS[w.kind].text, w.kind === "mo2" ? now : null, stop);
}

// What follows by itself: the plan after the dry run, and putting the plugins in place once they are verified.
function demasterChain() {
  const job = state.job, d = state.demaster;
  if (state.dmChain === "wait" && state.dmWait) {
    if (WAITS[state.dmWait.kind].over() && !state.dmGoing) {
      const again = state.dmWait.retry;
      state.dmChain = ""; state.dmWait = null; state.dmGoing = true;
      renderDemaster(true); state.processText = "";
      Promise.resolve(again()).finally(() => { state.dmGoing = false; });
    }
    return;
  }
  if (state.dmChain === "tools") { toolsInARow(); return; }
  if (state.dmChain === "probe" && state.probe) {
    if (state.probe.state === "passed" && !probeReason()) waitThen("modlist", demasterGo, true);   // then the modlist is read again
    if (state.probe.state === "failed") { state.dmChain = ""; toast("The probe did not pass: the Tools tab says where. Nothing real was changed."); }
  }
  if (state.dmChain === "dry" && job && job.id !== state.dmChainFrom) {
    if (job.state === "done") { state.dmChain = ""; goTab("selection"); askDemasterPlan().then(autoGo); }
    else if (["failed", "stopped"].includes(job.state)) state.dmChain = "";
  }
  if (state.dmChain === "install" && d) {
    if (d.state === "verified") {
      if (!settled()) return;                              // ModTrap is still reading or scanning: the next round
      state.dmChain = "";
      demasterCall("/api/demaster/install", { close_mo2: true }, "In place. ModTrap is reading the modlist again.", true).then(() => {
        if (BEING_READ.test(state.dmError || "")) { state.dmError = ""; state.dmChain = "install"; renderDemaster(true); return; }
        const set = state.settings || {}, placed = state.demaster && state.demaster.state === "installed";
        if (placed && set.auto_tools) { state.dmChain = "tools"; state.toolsTried = {}; state.toolsAgain = {}; state.toolsNow = ""; toast("In place. The tools that are to run again are started one after another."); }
        else if (placed && set.open_mo2_after) call("/api/mo2/open", {}).catch((e) => toast(e.message));
      });
    }
    else if (d.state === "failed") state.dmChain = "";
  }
}

async function planGoAhead() {
  try { await api("/api/demaster/start", {}); }
  catch (e) {
    if (OTHER_MO2.test(e.message)) { waitThen("mo2", planGoAhead); return; }     // the plan stays; the step is taken again
    if (BEING_READ.test(e.message)) { waitThen("modlist", planGoAhead); return; }
    state.dmError = e.message; state.dmPlan = null; await tick(); renderDemaster(true); return;
  }
  state.dmChain = "install"; state.dmError = ""; state.dmPlan = null;
  toast("The demaster has started: xEdit opens through MO2.");
  state.gen = (state.gen || 0) + 1;
  await tick();
  renderDemaster(true);
}
// The owner's setting (DESIGN§19): after the dry run, go ahead without asking, but only when the plan leaves
// nothing to them. Anything left to the owner, and the plan waits for them as always.
function autoGo() {
  const p = state.dmPlan, set = state.settings || {};
  if (!p || !set.auto_go || state.dmChain === "wait") return;
  if ((p.needs_you || []).length || p.blocked) { toast("The plan leaves something to you, so ModTrap asks before going on."); return; }
  toast("Nothing in the plan is left to you: going ahead, as set in Settings.");
  planGoAhead();
}

// The owner's setting (DESIGN§19): after the demaster, each tool that is to run again is started through MO2 as soon
// as the one before it has closed. The owner still works each tool; ModTrap cannot press a tool's own buttons. A tool
// that closes without having written anything ends the row: something did not go as meant, and that is the owner's.
function startToolsRow() {
  state.dmChain = "tools"; state.toolsTried = {}; state.toolsAgain = {}; state.toolsNow = "";
  toast("The tools that are to run again are started one after another. ModTrap runs and closes the ones it can; any other is yours to work, then close.");
  state.processText = ""; renderProcess();
}

function toolsInARow() {
  const t = state.tool, d = state.stepsData;
  if (state.status !== "ready" || state.toolsBusy) return;
  if (toolGoing(t)) return;                                                    // one at a time
  state.toolsAgain = state.toolsAgain || {};
  if (state.toolsNow) {                                                          // the one that has just closed
    const key = state.toolsNow, title = state.toolsTitle;
    state.toolsNow = "";
    if (t && t.title === title && t.state === "done" && t.changed_count > 0) {
      // It wrote its output: ModTrap has noted the run with the demaster, and the steps, read again, say done.
      state.stepsText = ""; state.stepsKey = ""; state.processText = "";
    } else if (t && t.title === title && t.state === "done" && t.retry && (state.toolsAgain[key] || 0) < 2) {
      // It wrote nothing, and there is a reason, not a guess, to start it once more (WHY§94): something ModTrap sets
      // right before a start, which this run has shown to be needed, or a refusal by Windows of the kind that passes.
      state.toolsAgain[key] = (state.toolsAgain[key] || 0) + 1;
      delete state.toolsTried[key];
      toast("“" + title + "” wrote nothing: " + t.retry + ". ModTrap starts it once more.");
      state.stepsText = ""; state.stepsKey = ""; state.processText = "";
    } else {
      state.dmChain = "";
      toast(t && t.title === title && t.state === "failed" ? "“" + title + "” did not get to its run, so ModTrap stops here: " + (t.message || "see the Tools tab") : "“" + title + "” closed without writing anything new, so ModTrap stops here. The tool's card on the Tools tab says what its own log holds.");
      return;
    }
  }
  if (!d || state.stepsLooking || state.stepsKey === "" || !settled()) return;   // the steps are being worked out again
  const next = d.steps.find((st) => st.key.startsWith("tool:") && st.state === "to do" && !st.manual &&
    !state.toolsTried[st.key] && (st.items || []).some((i) => i.tool));
  if (!next) {
    state.dmChain = "";
    toast("Every tool that was to run again has had its run. What is left is yours: the Process tab's last box.");
    if ((state.settings || {}).open_mo2_after) call("/api/mo2/open", {}).catch((e) => toast(e.message));
    return;
  }
  const title = next.items.find((i) => i.tool).tool;
  state.toolsTried[next.key] = true; state.toolsNow = next.key; state.toolsTitle = title; state.toolsBusy = true;
  api("/api/tool/start", { title: title }).then((r) => { state.tool = r; toast(r.by_itself ? "“" + title + "” is started to run and close by itself: nothing to press. The next one follows." : "Starting “" + title + "” through MO2. Work it, then close it: the next one follows."); })
    .catch((e) => {
      state.toolsNow = ""; delete state.toolsTried[next.key];
      if (OTHER_MO2.test(e.message)) waitThen("mo2", () => { state.dmChain = "tools"; });
      else if (BEING_READ.test(e.message)) { /* ModTrap is still at work: the row takes this tool up again in the next round */ }
      else { state.dmChain = ""; toast(e.message); }
    }).finally(() => { state.toolsBusy = false; });
}

function planNotNow() { state.dmPlan = null; renderDemaster(true); state.processText = ""; renderProcess(); }
async function putInPlace() {
  const d = state.demaster;
  if (!d || d.state !== "verified") return;
  if (!await confirmBox("Add the mod “" + d.plan.mod_name + "” with the demastered plugins, deactivate the patches made only for the mod" + (d.plan.blocked ? "" : ", and disable " + d.plan.mods.join(", ")) + "? Revert undoes it.")) return;
  await demasterCall("/api/demaster/install", {}, "In place. ModTrap is reading the modlist again.");
}

async function askDemasterPlan() {
  try { state.dmPlan = await api("/api/demaster/plan", {}); state.dmError = ""; }
  catch (e) {
    state.dmPlan = null; state.dmError = e.message;
    if (BEING_READ.test(e.message)) { waitForModlist(); return; }
  }
  renderDemaster(true);
  state.processText = ""; renderProcess();
}

async function demasterCall(path, body, done, noAsk) {
  // In the one go the confirmed plan already said MO2 is closed for the last step: no second question (WHY§67).
  try { await (noAsk ? call : api)(path, body || {}); state.dmError = ""; if (done) toast(done); }
  catch (e) { state.dmError = e.message; }
  state.dmPlan = null;
  state.gen = (state.gen || 0) + 1;
  await tick();
  renderDemaster(true);
}

// A plugin ModTrap demastered that a tool has since made anew: ModTrap's copy, in its own mod, hides the new one
// (WHY§56). Where the new one stands without the mod, the copy can be retired (WHY§80).
function remadeNote(j) {
  const list = j.remade || [];
  if (!list.length) return [];
  const can = list.filter((x) => x.ok), cannot = list.filter((x) => !x.ok);
  const out = [];
  if (can.length) {
    const go = el("button", { type: "button", class: "primary", text: "Retire ModTrap's cop" + (can.length === 1 ? "y" : "ies") });
    go.title = "Moves ModTrap's copy out of its mod into the job's folder (it is kept, not deleted). The plugin keeps its place in the load order.";
    go.addEventListener("click", async () => {
      go.disabled = true;
      try { const r = await api("/api/demaster/retire", { job: j.job }); toast(r.retired.length ? "Retired: " + r.retired.join(", ") + ". The plugin a tool made anew now counts." : "Nothing was retired."); }
      catch (e) { toast(e.message); }
      state.dmText = ""; state.historyText = ""; state.gen = (state.gen || 0) + 1;
      await tick();
    });
    out.push(el("p", { class: "message" }, "Made anew by a tool, without the mod: " + can.map((x) => x.plugin + " (in “" + x.original + "”)").join(", ") +
      ". ModTrap’s older copy in “" + j.mod_name + "” still wins over it and is no longer needed.  ", go));
  }
  if (cannot.length) out.push(el("p", { class: "message bad", text: "Made again since, but ModTrap’s copy must stay for now: " +
    cannot.map((x) => x.plugin + " (" + x.why + ")").join("; ") + ". Run the tool again with the mod disabled; ModTrap’s copy in “" + j.mod_name + "” keeps the load order whole until then." }));
  return out;
}

// Revert of a demaster (WHY§81): always back to how things stood before it, whatever came after.
const REVERT_ASKS = "Put everything back as it was before this demaster?\n\nThe three lists as they were; ModTrap's own mod removed; any plugin a tool has made anew since put back as it was; and the output of each tool that ModTrap started since, as it was kept before the tool ran. What is there now is set aside in the job's folder, not deleted.";
// Revert never runs while this modlist's MO2 is open (an open MO2 writes its own lists back over ModTrap's): pressed
// with MO2 open, ModTrap first asks MO2 to close (it asks you before, unless Settings says to close it without asking),
// and the program itself refuses the Revert while MO2 is still there. So the button is safe to press at any time.
const REVERT_WITH_MO2 = "Safe to press with MO2 open: ModTrap closes MO2 first (it asks you, unless Settings says to close it without asking), and never reverts while MO2 is still open.";
function revertSaid(r) {
  if (r.how === "finish") return (r.placed ? plural(r.placed, "plugin") + " back at " + (r.placed === 1 ? "its place" : "their places") + " in the load order. " : "") +
    (r.set_aside ? plural(r.set_aside, "plugin") + " left in ModTrap's own mod set aside in the job's folder; the mod's folder is gone. " : "") +
    (!r.placed && !r.set_aside ? "Nothing was left to do. " : "") + ((r.notes || []).length ? "Not done: " + r.notes.join("; ") + "." : "");
  return "Put back as it was before the demaster." + (r.placed ? " " + plural(r.placed, "plugin") + " MO2 had dropped from its lists " + (r.placed === 1 ? "is" : "are") + " back in place in the load order." : "") +
    ((r.notes || []).length ? " Not done: " + r.notes.join("; ") + "." : "") + ((r.tools || []).length ? " Tool output put back too: " + r.tools.join(", ") + "." : "") +
    ((r.tools_not_kept || []).length ? " Too large to have been kept, so run again: " + r.tools_not_kept.join(", ") + "." : "") +
    (r.set_aside ? " What was there (" + plural(r.set_aside, "file") + ") is set aside in the job's folder." : "");
}
// A Revert that enabled the mods again but left their plugins out of the load order (WHY§83): MO2 had dropped the
// lines while the mods were disabled. ModTrap puts them back where they stood.
function finishButton(j, after, label) {
  const b = el("button", { type: "button", class: "primary gated", text: label || "Put them back in place" });
  b.title = "Puts these plugins back where they stood in the load order before the demaster. Nothing else is touched.";
  b.addEventListener("click", async () => {
    b.disabled = true;
    try { toast(revertSaid(await api("/api/demaster/revert", { job: j.job, finish: true }))); } catch (e) { toast(e.message); }
    state.historyText = ""; state.dmText = ""; state.gen = (state.gen || 0) + 1;
    await tick(); if (after) after();
  });
  return b;
}
function unfinishedCard(j) {
  const n = (j.unfinished || []).length, b = (j.left_behind || []).length;
  const parts = [];
  if (n) parts.push(el("p", { text: "The mods are enabled again, but while they were disabled MO2 dropped their plugins from its lists, and the Revert did not put them back where they stood: " + j.unfinished.slice(0, 12).join(", ") + (n > 12 ? " and " + (n - 12) + " more" : "") + ". Left like this, MO2 adds them at the end of the load order, after the plugins that need them." }));
  if (b) parts.push(el("p", { text: "ModTrap's own mod “" + j.mod_name + "” is still in MO2's mods folder with " + plural(b, "plugin") + " a tool had written anew in it (" + j.left_behind.join(", ") + "). It is no longer in the mod list, so the game does not get it and your modlist is as it was before the demaster; MO2 would only show the folder as a new, disabled mod. ModTrap can set the " + (b === 1 ? "plugin" : "plugins") + " aside in the job's folder and take the folder away." }));
  return el("div", { class: "card warn" }, el("h2", { text: n ? "The last Revert left " + plural(n, "plugin") + " out of place in the load order" : "The last Revert left ModTrap's own mod behind" }),
    ...parts,
    el("p", {}, state.changes ? finishButton(j, () => renderDemaster(true), n ? "Put them back in place" : "Tidy it away") : null, el("span", { class: "dim", text: "  Close MO2 first. Nothing is deleted; the change is in the history." })));
}
async function revertDemaster(job) {
  let said = "";
  try { said = revertSaid(await api("/api/demaster/revert", { job: job })); state.dmError = ""; }
  catch (e) { state.dmError = e.message; }
  if (said) toast(said);
  state.dmPlan = null; state.dmChain = ""; state.dmWait = null;
  state.gen = (state.gen || 0) + 1;
  await tick();
  renderDemaster(true);
}

function renderDemaster(force) {
  const d = state.demaster;
  const text = JSON.stringify(d || 0) + JSON.stringify(state.dmPlan || 0) + (state.dmError || "");
  if (!force && text === state.dmText) return;
  state.dmText = text;
  const box = $("demaster-box");
  const cards = [];
  const planList = (p) => el("dl", { class: "kv" },
    el("dt", { text: "Taking out" }), el("dd", {}, p.mods.join(", "), el("span", { class: "dim mono", text: "  " + p.trapped.join(", ") })),
    el("dt", { text: "Demastered" }), el("dd", {}, p.demaster.length ? p.demaster.map((x) => x.plugin + " (" + x.actions + ")").join(", ") : "none"),
    el("dt", { text: "Switched off" }), el("dd", { text: p.switch_off.length ? p.switch_off.join(", ") + "  (patches made only for the mod: deactivated, not changed)" : "none" }),
    ...((p.disable_mods || []).length ? [el("dt", { text: "Disabled too" }), el("dd", { text: p.disable_mods.join(", ") + "  (mods that are patches for the mod: disabled whole, never removed)" })] : []),
    el("dt", { text: "Left to you" }), el("dd", { class: p.needs_you.length ? "would-needs" : "", text: p.needs_you.length ? p.needs_you.join(", ") : "none" }),
    el("dt", { text: "New mod" }), el("dd", { text: "“" + p.mod_name + "”, with the highest priority: it holds the demastered copies; the originals stay untouched in their own mods" }));
  if (state.dmPlan) {
    const p = state.dmPlan;
    const go = el("button", { type: "button", class: "primary", text: "Go ahead" });
    go.addEventListener("click", () => { go.disabled = true; planGoAhead(); });
    const cancel = el("button", { type: "button", text: "Not now" });
    cancel.addEventListener("click", planNotNow);
    cards.push(el("div", { class: "card installer" }, el("h2", { text: "What the demaster is about to do" }), planList(p),
      el("p", { text: "First: copies of every plugin above and of the profile's three lists go into the job's safe folder. Then xEdit opens through MO2 with ModTrap's script, takes out of each plugin exactly what the dry run listed, in memory only, and writes each finished plugin as a new file in ModTrap's own folder. ModTrap checks every new file, and only then puts them in place: its own mod with the new plugins is added, the patches are switched off and the mod is disabled. This is the whole demaster, in one go. MO2 must be closed for the last part: if it is open, ModTrap closes it then, as a click on its X does (never by force). Revert undoes all of it." }),
      p.blocked ? el("p", { class: "would-needs", text: "Some plugins are left to you, so the mod itself will stay enabled until those no longer need it." }) : null,
      ...p.notes.map((n) => el("p", { class: "dim", text: n })),
      el("div", { class: "actions" }, go, cancel)));
  }
  if (waitNote()) cards.push(el("div", { class: "card" }, waitNote()));
  if (state.dmError) cards.push(el("div", { class: "card" }, el("p", { class: "would-needs", text: state.dmError })));
  if (d && d.state === "working") cards.push(el("div", { class: "card installer" }, el("h2", {}, el("span", { class: "spinner", "aria-hidden": "true" }), " The demaster is running"),
    el("p", { class: "dim", text: "xEdit is open through MO2 and closes by itself. Leave it alone. When every new plugin is checked, ModTrap puts them in place." }),
    el("div", { class: "actions" }, (() => { const b = el("button", { type: "button", text: "Watch it on the Process tab" }); b.addEventListener("click", () => showTab("process")); return b; })())));
  if (d && d.state === "failed") cards.push(el("div", { class: "card" }, el("h2", { text: "The demaster stopped" }),
    el("p", { class: "would-needs", text: d.message }), el("p", { class: "dim", text: "Nothing in your modlist was changed. “Save this session” on the Log tab packs everything about this run into one file to send when asking for help." }),
    el("div", { class: "actions" }, (() => {
      const ok = el("button", { type: "button", text: "Close this" });
      ok.addEventListener("click", () => demasterCall("/api/demaster/drop", {}));
      return ok;
    })())));
  if (d && d.state === "verified") {
    const closed = d.mo2_closed === true;
    const put = el("button", { type: "button", class: "primary", text: "Put them in place", disabled: d.mo2_closed == null });
    put.addEventListener("click", putInPlace);
    cards.push(el("div", { class: "card installer" }, el("h2", { text: "The new plugins are ready and verified" }),
      el("p", {}, plural(d.written.length, "plugin") + " no longer need the mod: ", el("span", { class: "mono", text: d.written.join(", ") })),
      d.plan.needs_you.length ? el("p", { class: "would-needs", text: "Left to you: " + d.plan.needs_you.join(", ") + ". " + d.plan.notes.join(" ") }) : null,
      el("p", { class: closed ? "would-record" : "would-needs", text: closed ? "MO2 is closed: good. Keep it closed until this is done." :
        d.mo2_closed === false ? "MO2 is open. An open MO2 writes its own lists back over ModTrap's, so it must be closed for this: press the button and ModTrap asks whether to close it for you." : "ModTrap cannot tell whether MO2 is open on this PC, so it will not change the lists." }),
      el("div", { class: "actions" }, put, (() => {
        const not = el("button", { type: "button", text: "Not now" });
        not.title = "Drops these new plugins. Nothing of them is in your modlist; “Demaster Selected” makes them again.";
        not.addEventListener("click", () => demasterCall("/api/demaster/drop", {}));
        return not;
      })())));
  }
  if (d && d.state === "installed" && d.check) cards.push(el("div", { class: "card" }, el("h2", { text: d.check.ok ? "The demaster is in place, and the load order is clean" : "The demaster is in place, with something to look at" }),
    d.check.new_problems.length ? el("ul", {}, ...d.check.new_problems.map((x) => el("li", { class: "would-needs", text: x[0] + " needs " + x[1] + ", which is " + (x[2] === "inactive" ? "not active" : "missing") }))) : null,
    ...(d.check.needs_you.length ? (() => {
      const again = el("button", { type: "button", text: "Demaster what is left…" });
      again.title = "Reads the modlist as it is now (a dry run), shows the plan and asks";
      again.addEventListener("click", demasterGo);
      return [el("p", { class: "would-needs", text: "Not demastered this time: " + d.check.needs_you.join(", ") + ". The mod stays enabled until nothing needs it." }),
        ...((d.plan && d.plan.notes) || []).map((n) => el("p", { class: "dim", text: n })),
        el("p", {}, again, el("span", { class: "dim", text: "  ModTrap reads the modlist afresh and takes up what is left. If the same plugin is left again, send “Save this session” (Log tab)." }))];
    })() : []),
    el("p", { class: "dim", text: "Open MO2 and look: the new mod is at the end of the list, the patches are unticked" + (d.check.disabled ? ", and the mod is disabled" : "") + ". The Steps tab shows what is left, such as tools to run again." })));
  const allJobs = (d && d.jobs) || [];
  const earlier = allJobs.filter((j) => j.state !== "installed").length;
  for (const j of allJobs.filter((x) => x.state === "installed").slice(0, 12)) {
    const undo = el("button", { type: "button", text: "Revert" });
    undo.title = REVERT_WITH_MO2;
    undo.addEventListener("click", async () => {
      if (!await confirmBox(REVERT_ASKS)) return;
      revertDemaster(j.job);
    });
    cards.push(el("div", { class: "card" }, el("p", {}, el("span", { class: "tag " + (j.state === "installed" ? "good" : ""), text: j.state === "installed" ? "demastered by ModTrap" : "reverted" }),
      " " + j.when.replace("T", " ") + ": " + j.mods.join(", ") + "  ", j.state === "installed" && state.changes ? undo : null),
      el("p", { class: "dim", text: "New plugins in “" + j.mod_name + "”: " + (j.plugins.join(", ") || "none") + ". Disabled: " + (j.disabled.join(", ") || "none") + ". Deactivated: " + (j.deactivated.join(", ") || "none") + "." }),
      ...remadeNote(j)));
  }
  for (const j of allJobs.filter((x) => x.state === "reverted" && ((x.unfinished || []).length || (x.left_behind || []).length)).slice(0, 1)) cards.push(unfinishedCard(j));
  if (earlier) {
    const go = el("button", { type: "button", class: "linkish", text: "the History tab" });
    go.addEventListener("click", () => showTab("history"));
    cards.push(el("p", { class: "dim" }, plural(earlier, "earlier job") + " that no longer " + (earlier === 1 ? "stands is" : "stand are") + " kept on ", go, "."));
  }
  box.hidden = !cards.length;
  box.replaceChildren(...cards);
}

// --- the probe (DESIGN§9): proving ModTrap on this PC with invented plugins, before any real mod is touched ----------

const probeReason = () => (state.changes && state.probe && state.probe.needed ? state.probe.reason || "" : "");

// Where something waits for the probe, the button that runs it is right there (WHY§60).
function probeButton() {
  if (!probeReason() || (state.probe && state.probe.state === "working")) return null;
  const b = el("button", { type: "button", text: "Run the probe now" });
  b.title = "A few minutes, on invented test plugins in your own MO2 and xEdit; it undoes itself";
  b.addEventListener("click", async () => {
    b.disabled = true;
    try { state.probe = await api("/api/probe/start", {}); state.probeError = ""; state.probeText = ""; showTab("tools"); toast("The probe has started."); }
    catch (e) { toast(e.message); b.disabled = false; }
    tick();
  });
  return b;
}

function renderProbe() {
  const pr = state.probe;
  const text = JSON.stringify(pr || 0) + state.changes + (state.probeError || "");
  if (text === state.probeText) return;
  state.probeText = text;
  const box = $("probe-box");
  const what = el("p", { text: "Before ModTrap changes anything real, it proves itself on this PC: it puts two test mods of its own into MO2, holding three tiny invented plugins, and does its whole work on them: a dry run through your xEdit, a demaster, putting the result in place, and Revert. Then it removes them again. No mod of yours is read into them or changed." });
  if (!state.changes) {
    box.replaceChildren(el("div", { class: "card" }, el("h2", { text: "Prove ModTrap on this PC" }), what,
      el("p", { class: "dim", text: "The probe changes MO2's lists for its test mods, so it runs only when ModTrap is started with --allow-changes. Until it has passed, “Add it for me” and “Demaster Selected” stay off." })));
    return;
  }
  const working = pr && pr.state === "working";
  const go = el("button", { type: "button", class: "primary", text: pr && pr.state ? "Run the probe again" : "Run the probe", disabled: !!working || !!(state.session && state.session.locked) });
  go.addEventListener("click", async () => {
    go.disabled = true;
    try { state.probe = await api("/api/probe/start", {}); state.probeError = ""; toast("The probe has started."); }
    catch (e) { state.probeError = e.message; }
    state.probeText = "";
    tick();
  });
  const stop = el("button", { type: "button", text: "Stop" });
  stop.addEventListener("click", async () => { try { await api("/api/probe/stop", {}); } catch (e) { toast(e.message); } tick(); });
  const marks = { passed: ["✓", "good"], failed: ["✗", "bad"], going: ["…", "warn"], "": ["", ""] };
  const steps = (pr && pr.steps && pr.steps.length) ? el("ul", { class: "probe-steps" }, ...pr.steps.map((st) => {
    const [mark, cls] = marks[st.result || ""] || ["", ""];
    return el("li", { class: st.result === "failed" ? "would-needs" : st.result ? "" : "dim" }, el("span", { class: "tag " + cls, text: mark || "·" }), " " + st.title,
      st.detail ? el("span", { class: st.result === "failed" ? "" : "dim", text: st.result === "failed" ? ": " + st.detail : "  (" + st.detail + ")" }) : null);
  })) : null;
  const kids = [el("h2", {}, "Prove ModTrap on this PC",
    pr && pr.state === "passed" ? el("span", { class: "tag good", text: "passed" + (pr.when ? " " + pr.when.replace("T", " ") : "") }) :
    pr && pr.state === "failed" ? el("span", { class: "tag bad", text: "did not pass" }) : working ? el("span", { class: "tag warn", text: "running" }) : el("span", { class: "tag", text: "not run yet" })),
    what,
    el("p", { class: "dim", text: "MO2 must be closed when it starts, and stays closed except while ModTrap itself runs xEdit through it. It takes a few minutes; xEdit opens and closes twice by itself." }),
    steps,
    pr && pr.message ? el("p", { class: "would-needs", text: pr.message }) : null,
    state.probeError ? el("p", { class: "would-needs", text: state.probeError }) : null,
    pr && pr.state === "passed" ? el("p", { class: "would-record", text: "Every step passed" + (pr.xedit ? " with xEdit version number " + pr.xedit : "") + ". “Add it for me” and “Demaster Selected” are now allowed on this modlist. If you change your xEdit, run the probe again." }) : null,
    pr && pr.state === "failed" ? el("p", { text: "ModTrap will not change real mods on this modlist while a step fails. Press “Save this session” on the Log tab and send the file it downloads: it holds what your xEdit and MO2 did, with your folders taken out." }) : null];
  if (pr && pr.left_behind && pr.left_behind.length) {
    const rm = el("button", { type: "button", text: "Remove the test mods" });
    rm.addEventListener("click", async () => {
      try { const r = await api("/api/probe/cleanup", {}); toast(r.left.length ? "Still there: " + r.left.join(", ") : "The test mods are gone."); state.probeError = ""; }
      catch (e) { state.probeError = e.message; }
      state.probeText = "";
      tick();
    });
    kids.push(el("p", { class: "would-needs" }, "Still in MO2 from the probe: " + pr.left_behind.join(", ") + ". They are invented and safe to remove; close MO2 and press  ", rm));
  }
  kids.push(el("div", { class: "actions" }, go, working ? stop : null));
  box.replaceChildren(el("div", { class: "card" + (working ? " installer" : "") }, ...kids.filter(Boolean)));
}

// --- "Save this session" (WHY§48): the session's logs in one .7z, downloaded from the page ----------------------------

async function saveSession() {
  try { state.save = await api("/api/save/start", {}); state.saveWanted = true; }
  catch (e) { toast(e.message); }
  renderSave();
  tick();
}

async function fetchSaved(name) {
  // The download needs this page's token, which a plain link cannot send: the file is fetched, then handed to the
  // browser's own "save" from memory.
  const r = await fetch("/api/save/download", { headers: { "X-ModTrap-Token": TOKEN } });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || "the download failed (" + r.status + ")");
  const url = URL.createObjectURL(await r.blob());
  const a = el("a", { href: url, download: name || "ModTrap-session.7z" });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}

function renderSave() {
  const sv = state.save || { state: "idle" };
  const b = $("save-session");
  const packing = sv.state === "packing";
  b.disabled = packing || state.status !== "ready";
  b.textContent = packing ? "Packing… " + sv.done + " of " + (sv.total || "?") : "Save this session";
  $("save-status").textContent = packing ? "" : sv.state === "failed" || sv.state === "nothing" ? sv.message : state.saveNote || "";
  if (!state.saveWanted || packing) return;
  if (sv.state === "ready") {
    state.saveWanted = false;
    fetchSaved(sv.name).then(() => {
      state.saveNote = "Saved as " + sv.name + " (" + Math.max(1, Math.round(sv.size / 1024)) + " KB), in your browser's downloads.";
      toast("This session is saved: " + sv.name);
      renderSave();
    }).catch((e) => { state.saveNote = "Not saved: " + e.message + "."; renderSave(); });
  } else if (sv.state === "failed" || sv.state === "nothing") {
    state.saveWanted = false;
    toast(sv.message);
  }
}

// --- the History tab (MT15, DESIGN§12) ------------------------------------------------------------------------------

const HISTORY_WORDS = { "mod disabled": "Mod disabled", "mod enabled": "Mod enabled", "mod added": "Mod added", "plugin deactivated": "Plugin deactivated",
  "plugin activated": "Plugin activated", "plugin demastered": "Plugin demastered", "reverted": "Reverted", "revert finished": "Revert finished", "tool settings changed": "A tool's settings changed", "mo2 settings changed": "MO2's settings changed", "tool ran": "Tool run", "verified": "Checked" };

function historyLine(e) {
  const bits = [];
  if (e.mod) bits.push("“" + e.mod + "”" + (e.priority != null ? ", priority " + e.priority : "") + (e.priority_before != null ? " (was " + e.priority_before + ")" : ""));
  if (e.plugin) bits.push(e.plugin + (e.position != null ? ", position " + e.position : "") + (e.plugin_kind ? " [" + e.plugin_kind + "]" : "") + (e.mod && !bits.length ? "" : ""));
  if (e.now_in) bits.push("new copy in “" + e.now_in + "”");
  if (e.masters_before) bits.push("masters " + e.masters_before.join(", ") + " → " + (e.masters_after || []).join(", "));
  if (e.before) bits.push("placed directly before " + e.before);
  if (e.archive) bits.push("from " + e.archive);
  if (Array.isArray(e.plugins) && e.plugins.length) bits.push("plugins: " + e.plugins.map((p) => p.name + (p.position != null ? " at " + p.position : "")).join(", "));
  if (e.why) bits.push(e.why);
  if (e.kind === "verified") bits.push(e.ok === false ? "something to look at" : "as planned" + (e.what ? " (" + e.what + ")" : ""));
  if (Array.isArray(e.restored) && e.restored.length) bits.push("put back: " + e.restored.join(", "));
  if (Array.isArray(e.left) && e.left.length) bits.push("left in place: " + e.left.join(", "));
  if (e.tool) bits.push("“" + e.tool + "”" + (e.file ? ", " + e.file : "") + (e.profile ? ", its profile “" + e.profile + "”" : ""));
  if (!e.tool && e.file) bits.push(e.file);
  if (e.was && e.now) bits.push("was " + e.was + " · now " + e.now);
  if (e.kind === "tool ran") bits.push(e.files ? plural(e.files, "file") + " of its output written" : "none of its output files changed");
  if (e.kept) bits.push("a copy as it was: " + e.kept);
  if (Array.isArray(e.placed) && e.placed.length) bits.push("back at their places in the load order: " + e.placed.join(", "));
  if (Array.isArray(e.notes) && e.notes.length) bits.push("not done: " + e.notes.join("; "));
  return bits.join(" · ");
}

async function pollHistory() {
  if (state.status !== "ready" || state.tab !== "history") return;
  try {
    const d = await api("/api/history");
    const text = JSON.stringify(d);
    if (text === state.historyText) return;
    state.historyText = text;
    const box = $("history");
    const jobCards = [];
    if ((d.jobs || []).length) {
      const gone = d.jobs.filter((j) => j.state !== "installed" && j.state !== "added").length;
      const clear = el("button", { type: "button", text: "Clear job history", disabled: !gone });
      clear.title = gone ? "Takes the jobs that no longer stand off this list. Jobs still in place stay; the list of changes below is not touched." : "Every job listed is still in place";
      clear.addEventListener("click", async () => {
        if (!await confirmBox("Take the " + plural(gone, "job") + " that no longer " + (gone === 1 ? "stands" : "stand") + " (reverted or stopped) off this list?\n\nJobs that are still in place stay, with their Revert. Nothing in your modlist changes, and the list of changes below is kept.")) return;
        try { const r = await api("/api/jobs/clear", {}); toast(plural(r.cleared, "job") + " cleared."); } catch (e) { toast(e.message); }
        state.historyText = ""; state.dmText = ""; state.addText = "";
        pollHistory(); tick();
      });
      const row = (j) => {
        const stands = j.state === "installed" || j.state === "added";
        const what = j.what === "add" ? "added" : "demastered";
        const tr = el("tr", {}, el("td", { class: "c-num", text: String(j.when || "").replace("T", " ") }),
          el("td", {}, el("span", { class: "tag " + (stands ? "good" : ""), text: stands ? what + ", in place" : j.state === "reverted" ? what + ", reverted" : "stopped" })),
          el("td", { text: (j.mods || []).join(", ") }),
          el("td", { class: "dim", text: j.what === "add" ? "plugins: " + ((j.plugins || []).join(", ") || "none")
            : "new plugins in “" + j.mod_name + "”: " + ((j.plugins || []).join(", ") || "none") + " · disabled: " + ((j.disabled || []).join(", ") || "none") + " · deactivated: " + plural((j.deactivated || []).length, "patch", "patches") }));
        const cell = el("td", {});
        if (stands && d.can_change) {
          const undo = el("button", { type: "button", text: j.what === "add" ? "Take it out again" : "Revert" });
          undo.title = REVERT_WITH_MO2;
          undo.addEventListener("click", async () => {
            if (!await confirmBox(j.what === "add" ? "Put the mod list and the load order back as they were before this add, and remove ModTrap's copy of the mod from MO2's mods folder?" : REVERT_ASKS)) return;
            try { const r = await api(j.what === "add" ? "/api/add/revert" : "/api/demaster/revert", { job: j.job }); toast(j.what === "add" ? "Put back as it was." : revertSaid(r)); } catch (e) { toast(e.message); }
            state.historyText = ""; state.dmText = ""; state.addText = ""; state.gen = (state.gen || 0) + 1;
            await tick(); pollHistory();
          });
          cell.append(undo);
        }
        if (j.what !== "add" && ((j.unfinished || []).length || (j.left_behind || []).length) && d.can_change) {
          cell.append(el("div", { class: "dim", text: (j.unfinished || []).length ? plural(j.unfinished.length, "plugin") + " left out of place" : "ModTrap's own mod left behind" }),
            finishButton(j, pollHistory, (j.unfinished || []).length ? "Put them back in place" : "Tidy it away"));
        }
        tr.append(cell);
        return tr;
      };
      jobCards.push(el("div", { class: "card" }, el("div", { class: "card-head" }, el("h2", { text: "Jobs of this session" }), clear),
        el("p", { class: "dim", text: "Every demaster and every add ModTrap carried out here, newest first. A job in place can be undone from here or from its own tab; one that no longer stands is only kept for looking at." }),
        el("table", { class: "plain" }, el("thead", {}, el("tr", {}, el("th", { text: "When" }), el("th", { text: "State" }), el("th", { text: "Mods" }), el("th", { text: "What it did" }), el("th", {}))),
          el("tbody", {}, ...d.jobs.map(row)))));
    }
    if (!d.events.length) {
      box.replaceChildren(...jobCards, el("div", { class: "card" }, el("h2", { text: "Nothing yet" }),
        el("p", { class: "dim", text: "ModTrap has changed nothing in this modlist in this session. When it adds a mod or demasters one, every change is listed here with its date and time, the mod's priority and each plugin's place in the load order." })));
      return;
    }
    box.replaceChildren(...[...jobCards, el("h2", { class: "pad-top", text: "Every change, one by one" }),
      el("table", {}, el("thead", {}, el("tr", {}, el("th", { text: "When" }), el("th", { text: "What" }), el("th", { text: "Details" }))),
      el("tbody", {}, ...d.events.map((e) => el("tr", {}, el("td", { class: "c-num", text: String(e.when || "").replace("T", " ") }),
        el("td", { text: HISTORY_WORDS[e.kind] || e.kind }), el("td", { text: historyLine(e) }))))),
      d.total > d.events.length ? el("p", { class: "dim", text: "Showing the newest " + d.events.length + " of " + d.total + "." }) : null].filter(Boolean));
  } catch (e) { /* the next round tries again */ }
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
      r.addEventListener("click", async () => {
        const name = await promptBox("A name for this session:", x.name);
        if (name != null && name.trim() && name.trim() !== x.name) sessionCall("/api/session/rename", { id: x.id, name: name }, "Renamed.");
      });
      const f = el("button", { type: "button", text: "Finish", title: "Mark this session finished. ModTrap first checks that nothing of it is still going; the modlist is then free for the session that waits for it." });
      f.addEventListener("click", async () => {
        if (await confirmBox("Finish session “" + x.name + "”?\n\nModTrap checks that nothing of it is still going. A finished session stays to be looked at, but no more work is done in it; the modlist is then free for the next session.")) sessionCall("/api/session/finish", { id: x.id }, "Session finished.");
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
      if (force || !await confirmBox(e.message + "\n\nQuit anyway?")) return;
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
  const can = m.kind === "mod" && (m.plugins.length > 0 || state.picked.has(m.name));
  const tick = el("input", { type: "checkbox", disabled: !can, checked: state.picked.has(m.name),
    "aria-label": "Tick " + m.name,
    title: can ? "Tick to choose this mod for demastering (a click on the row only shows it)" : "Nothing to demaster: this mod provides no plugin" });
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
  // A click on the row only shows the mod and what is tied to it; ticking is the box's alone (WHY§59).
  tr.addEventListener("click", (ev) => {
    if (ev.target.closest("input, button, a")) return;
    focusMod(m.name);
  });
  tr.dataset.name = m.name;
  if (m.kind === "mod") tr.addEventListener("contextmenu", (ev) => modMenu(ev, m.name));
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
  if (state.focus) paintFocus();
  filterMods();
}

function filterMods() {
  const q = fold($("mods-search").value.trim());
  const en = $("f-enabled").checked, pl = $("f-plugins").checked, dp = $("f-deps").checked;
  const rel = state.onlyRelated && state.focus ? relatedTo(state.focus) : null;
  const filtering = !!(q || en || pl || dp || rel);
  let shown = 0, total = 0;
  for (const g of state.groups) {
    const folded = state.grouped && g.sep && state.collapsed.has(g.sep.name) && !filtering;
    let match = 0, ticked = 0;
    for (const m of g.mods) {
      total++;
      const ok = (!q || m.hay.includes(q)) && (!en || m.enabled) && (!pl || m.plugins.length > 0) && (!dp || m.dependants > 0) &&
        (!rel || rel.has(m.name)) && (state.grouped || state.flat.has(m));
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
  state.onlyRelated = false;
  $("mods-search").value = "";
  for (const id of ["f-enabled", "f-plugins", "f-deps"]) $(id).checked = false;
  filterMods();
}

// --- looking at one mod: what it is, and the mods tied to it as a demaster sees it (WHY§59) -----------------------

function relatedTo(name) {
  const f = findMod(name);
  return new Set(f ? [f.name, ...(f.needs || []), ...(f.needed_by || [])] : []);
}

function focusMod(name, keep) {
  state.focus = state.focus === name && !keep ? "" : name;
  if (!state.focus) state.onlyRelated = false;
  paintFocus();
  if (state.groups) filterMods();
}

function paintFocus() {
  const f = state.focus ? findMod(state.focus) : null;
  const needs = new Set(f ? f.needs || [] : []), neededBy = new Set(f ? f.needed_by || [] : []);
  for (const g of state.groups || []) for (const m of g.mods) if (m.row) {
    m.row.classList.toggle("focus", !!f && m.name === f.name);
    m.row.classList.toggle("rel-needed", neededBy.has(m.name));
    m.row.classList.toggle("rel-needs", needs.has(m.name) && !neededBy.has(m.name));
  }
  const box = $("mod-info");
  box.hidden = !f;
  if (!f) return;
  const chips = (names) => names.slice(0, 60).map((n) => {
    const b = el("button", { type: "button", class: "linkish", text: n, title: "Show this mod" });
    b.addEventListener("click", () => { gotoMod(n); focusMod(n, true); });
    return b;
  }).reduce((acc, b, i) => acc.concat(i ? [", ", b] : [b]), []);
  const can = f.kind === "mod" && f.plugins.length > 0;
  const tick = el("button", { type: "button", class: can && !state.picked.has(f.name) ? "primary" : "", disabled: !can,
    text: state.picked.has(f.name) ? "Untick" : "Tick for demaster" });
  tick.title = can ? "" : "Nothing to demaster: this mod provides no plugin";
  tick.addEventListener("click", () => { togglePick(f.name, !state.picked.has(f.name)); paintFocus(); });
  const only = el("input", { type: "checkbox", checked: !!state.onlyRelated });
  only.addEventListener("change", () => { state.onlyRelated = only.checked; filterMods(); });
  const close = el("button", { type: "button", text: "Close" });
  close.addEventListener("click", () => focusMod(f.name));
  const nb = f.needed_by || [], nd = f.needs || [];
  box.replaceChildren(...[
    el("div", { class: "card-head" }, el("h2", { text: f.kind === "game" ? "The game's own Data folder" : f.name }),
      el("span", { class: "tag " + (f.enabled ? "good" : ""), text: f.enabled ? "enabled" : "disabled" }),
      state.picked.has(f.name) ? el("span", { class: "tag good", text: "ticked for demaster" }) : null),
    el("p", { class: "dim" }, f.priority < 0 ? "" : "Priority " + f.priority + " · ", f.plugins.length ? "provides " : "provides no plugin",
      ...f.plugins.slice(0, 12).map((p, i) => { const a = el("button", { type: "button", class: "linkish mono", text: p }); a.addEventListener("click", () => gotoPlugin(p)); return i ? [", ", a] : [a]; }).flat(),
      f.plugins.length > 12 ? " … +" + (f.plugins.length - 12) : ""),
    el("p", { class: "rel-line" }, el("span", { class: "swatch needed" }), nb.length
      ? el("span", {}, "Needs this mod: " + plural(f.dependants, "plugin") + " in " + plural(nb.length, "other mod") + " (these would be switched off or demastered with it): ", ...chips(nb), nb.length > 60 ? " …" : "")
      : el("span", { class: "dim", text: "No other mod's plugin needs this mod: it can simply be disabled in MO2." })),
    nd.length ? el("p", { class: "rel-line" }, el("span", { class: "swatch needs" }),
      el("span", {}, "This mod needs: ", ...chips(nd), nd.length > 60 ? " …" : "")) : null,
    el("div", { class: "actions" }, tick, el("label", { title: "Hide every mod that is not tied to this one" }, only, " Show only this mod and the mods tied to it"), close)].filter(Boolean));
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
  $("tray").hidden = !n || tab === "selection" || tab === "job" || tab === "steps" || tab === "process";
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
  $("group-count").textContent = state.picked.size; $("group-count").classList.toggle("on", state.picked.size > 0);
  $("sel-count").classList.toggle("on", state.picked.size > 0);
  updateDryButton();
  $("plan").hidden = true;
  if (state.groups) filterMods();
  if (state.focus) paintFocus();
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
  preparing: "Preparing", starting: "Starting xEdit through MO2", loading: "xEdit is loading the plugins (if its “Module Selection” window stays open, press OK: nothing needs choosing)",
  reading: "xEdit is reading the dependants", checking: "Checking the result", done: "Dry run done",
  failed: "The dry run failed", stopped: "Stopped",
};
const WOULD = {
  "record": ["would be taken out", "would-record", "The dependant's own copy of one of the trapped mod's records."],
  "entry": ["entry would be taken out", "would-entry", "An entry of a list that can be shortened; the record stays."],
  "part": ["part would be put back", "would-entry", "The plugin only carries this part on from the trapped mod. It would be put back as the plugin's remaining masters have it; the record stays."],
  "needs you": ["needs you", "would-needs", "ModTrap would not change this by itself."],
};
const FILE_READING = {
  "patch only": ["patch only: would be switched off", "good", "A patch made for the trapped mod: without the mod it has no purpose."],
  "can be demastered": ["can be demastered", "good", "Everything in it that needs the trapped mod can be taken out automatically."],
  "needs you": ["needs you", "warn", "Some of what needs the trapped mod is not something ModTrap takes out by itself."],
  "not finished": ["not read to the end", "bad", ""],
};

// Where a part that needs the owner came from, as the dry run found it (reported only, for now: MT4).
function cameFrom(e) {
  if (e.would === "part") return e.action === "take out"
    ? "  · carried on from " + e.same_as + "; " + e.from + " has no such part: it would be taken out"
    : "  · carried on from " + e.same_as + "; it would be put back as " + e.from + " has it";
  if (e.would === "entry" && e.came === "added") return "  · an entry from the mod, not this plugin's own: it would be taken out";
  if (e.would === "needs you" && e.same_as !== undefined) return e.same_as
    ? "  · the same as in " + e.same_as + ", but ModTrap cannot tell what to put in its place"
    : "  · this plugin's own doing, or not found in an earlier plugin";
  return "";
}

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
  const key = job.id + "|" + job.state + "|" + (job.stale ? "stale" : "");
  if (key === state.jobSeen) return;
  state.jobSeen = key;
  const box = $("job-result");
  const parts = [];
  if (job.message) parts.push(el("p", { class: "message " + (job.state === "failed" ? "bad" : ""), text: job.message }));
  if (job.stale) parts.push(el("p", { class: "message", text: "The modlist has been read again since this dry run (after a demaster, a Rescan or a change in MO2), so this is how things stood before. “Demaster Selected” runs a fresh dry run by itself; “Dry run through xEdit” on the Selection tab does one without changing anything." }));
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
        el("p", { class: "dim", text: f.reading === "patch only" ? (f.why === "named for the mod"
          ? "A patch for the trapped mod, by its name and its few masters: without the mod it has no purpose, so it would be switched off, not changed."
          : "Every record in it belongs to the trapped mod: nothing of it would remain.") : hint }),
        el("p", { text: f.records + " records; " + f.needing + " need the trapped mod: " + f.own + " of its own records, " +
          plural(f.entries, "list entry", "list entries") + ", " + plural(f.parts || 0, "part") + " carried on from the mod, " +
          f.needs_you + " that need you." }));
      const shown = f.items.slice(0, 400);
      const list = el("ul");
      for (const it of shown) {
        const [w, wc, wh] = WOULD[it.would];
        const li = el("li", {}, el("span", { class: "mono", text: it.signature + " " + it.form + (it.editor_id ? " " + it.editor_id : "") }),
          el("span", { class: "tag " + wc, title: wh, text: w }));
        if (!it.own && it.elements.length) {
          li.append(el("ul", {}, ...it.elements.slice(0, 40).map((e) => el("li", { class: "mono dim",
            text: (e.kind === "entry" ? "entry of " + e.array + " (" + e.array_length + " long)" : "field " + e.path) + " → " + e.target_file + " " + e.target_form + cameFrom(e) }))));
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
  try { const d = await api("/api/job"); state.job = d.job; renderJob(d.job); renderSteps(); demasterChain(); } catch (e) { /* next round */ }
}

// --- the Steps tab (DESIGN§14) --------------------------------------------------------------------------------------

const STEP_STATE = {
  "done": ["done", "good"], "not needed": ["not needed", "good"], "to do": ["to do", ""], "going": ["going…", "warn"],
  "waiting": ["waits for the steps above", ""], "waiting for the dry run": ["waits for the dry run", ""],
};

// "I have done this" on a tool's step or on the play test says: done after the demaster that is in place. A
// Revert takes that away, and so does a new demaster: the ticks go with the demaster they were made for (WHY§87).
function ticksOfThisDemaster() {
  if (state.status !== "ready" || !state.demaster || !state.session) return;
  const placed = (state.demaster.jobs || []).find((j) => j.state === "installed");
  const now = placed ? placed.job : "";
  if (state.ticksJob !== now) {                        // also when it was never kept: an older page's ticks are not trusted
    const ticks = state.stepsDone || {};
    let gone = 0;
    for (const k of Object.keys(ticks)) if (/::(tool:|play$)/.test(k)) { delete ticks[k]; gone++; }
    if (gone) { state.stepsText = ""; state.stepsKey = ""; state.processText = ""; }
  }
  if (state.ticksJob !== now) { state.ticksJob = now; saveUi(); }
}

function stepKey(k) { return [...state.picked].sort().join("|") + "::" + k; }

// Starting one of the modlist's tools through MO2 (DESIGN§16.8): the button, and what came of it.
function toolGoing(t) { return !!t && ["starting", "preparing", "running"].includes(t.state); }

function toolButton(title) {
  const t = state.tool;
  const going = toolGoing(t);
  const b = el("button", { type: "button", text: going && t.title === title ? "Running…" : "Start it through MO2", disabled: !!going || !!(state.session && state.session.locked),
    title: "Starts “" + title + "” the way MO2's own Run button does. It is yours to work; ModTrap waits for it to close and then says which of its output files changed." });
  b.addEventListener("click", async () => {
    b.disabled = true;
    try { state.tool = await api("/api/tool/start", { title: title }); toast(state.tool.by_itself ? "“" + title + "” is started to run and close by itself: nothing to press." : "Starting “" + title + "” through MO2…"); }
    catch (e) { toast(e.message); }
    state.addText = ""; state.stepsText = "";
    tick();
  });
  return b;
}

function toolCard() {
  const t = state.tool;
  if (!t) return null;
  const going = toolGoing(t), preparing = t.state === "preparing";
  const stop = el("button", { type: "button", text: "Stop waiting" });
  stop.addEventListener("click", async () => { try { state.tool = await api("/api/tool/stop", {}); } catch (e) { toast(e.message); } tick(); });
  const mins = Math.floor(t.seconds / 60), secs = t.seconds % 60;
  return el("div", { class: "card" + (going ? " installer" : "") },
    el("h2", {}, going ? el("span", { class: "spinner", "aria-hidden": "true" }) : null, (preparing ? " “" + t.title + "” is open outside MO2, building its patchers: leave it alone, ModTrap closes it" : going ? (t.drive === "left to the owner" ? " “" + t.title + "” is open and yours: run it, then close it" : t.by_itself ? " “" + t.title + "” is running by itself and closes when it is done" : " “" + t.title + "” is open: work it, then close it") :
      t.state === "done" ? "“" + t.title + "” has closed" : "“" + t.title + "”: " + (t.message || t.state))),
    ...(t.before || []).map((x) => el("p", { class: "would-record", text: "Before the start: " + x + "." })),
    t.drive_note && (going || t.drive === "left to the owner") ? el("p", { class: t.drive === "left to the owner" ? "would-needs" : "dim", text: t.drive_note.charAt(0).toUpperCase() + t.drive_note.slice(1) + "." }) : null,
    going ? el("p", { class: "dim", text: "Started " + (mins ? mins + " min " : "") + secs + " s ago" + (t.profile ? ", through MO2 with its profile “" + t.profile + "”" : "") + ". ModTrap is waiting, and changes nothing meanwhile." }) : null,
    t.state === "done" ? el("p", { class: t.changed_count ? "would-record" : "would-needs", text: t.changed_count ?
      plural(t.changed_count, "file") + " of its output " + (t.changed_count === 1 ? "was" : "were") + " written" + (t.output_mod ? " (its output goes to “" + t.output_mod + "”)" : "") + ". ModTrap has read the modlist again." :
      "None of its output files changed. If you meant it to build its output, it may not have been run to the end." }) : null,
    t.state === "done" && t.own_log ? el("div", {}, el("p", { text: "What its own log of this run says (" + t.own_log.file + (t.own_log.kept ? "; a copy is kept with this session" : "") + "):" }),
      t.own_log.findings.length ? el("ul", {}, ...t.own_log.findings.map((f) => el("li", { class: f.level === "error" ? "would-needs" : "dim", text: f.text })))
        : el("p", { class: "dim", text: "None of the signs ModTrap knows shows in it." })) : null,
    t.state === "done" && !t.changed_count && t.retry ? el("p", { text: "One more start is worth it: " + t.retry + "." }) : null,
    t.state === "done" && !t.changed_count && t.hint && !(t.own_log && t.own_log.findings.some((f) => f.level === "error")) ? el("p", { class: "dim", text: t.hint }) : null,
    t.state === "done" && t.profile ? el("p", { class: "dim", text: "It was started through MO2 with MO2's profile “" + t.profile + "”: that profile's mods and load order are what it was given." }) : null,
    t.changed_count ? el("details", {}, el("summary", { text: "The files" }), el("ul", {}, ...t.changed.map((c) => el("li", { class: "mono", text: c })))) : null,
    going ? el("div", { class: "actions" }, stop) : null);
}

// The evidence behind a step, folded away until asked for (WHY§64).
function evidenceFold(d) {
  return el("details", { class: "evidence" }, el("summary", { text: "Evidence: " + d.summary }),
    el("ul", {}, ...d.lines.map((l) => el("li", { class: "mono dim", text: l }))));
}

function stepItem(it) {
  if (it.details) return el("li", { class: "plain" }, evidenceFold(it.details));
  if (it.text) return el("li", {}, it.text, ...(it.evidence || []).map(evidenceFold));
  if (it.tool) return el("li", {}, "“" + it.tool + "” in MO2's list of tools  ", toolButton(it.tool));
  if (it.file) return el("li", {}, modLink(it.mod), ": ", el("span", { class: "mono", text: it.file }),
    it.kind ? el("span", { class: "dim", text: "  " + it.kind }) : null,
    el("span", { class: "dim", text: "  names " + it.names.join(", ") + (it.count ? " in " + plural(it.count, "line") : "") }),
    it.verdict ? el("span", { class: "tag " + (it.open ? "warn" : "good"), text: it.verdict }) : null,
    // What is left to the owner is said in full (WHY§97): where the file is, which line, what it means, what to do.
    (it.look || []).length ? el("div", { class: "look" },
      it.path ? el("p", {}, "The file: ", el("span", { class: "mono", text: it.path }), copyButton(it.path, "The file's path")) : null,
      ...it.look.map((ln) => el("div", { class: "look-line" },
        el("p", {}, ln.n ? el("b", { text: "Line " + ln.n + ": " }) : null, el("span", { class: ln.n ? "mono" : "", text: ln.text })),
        el("p", { class: "dim", text: "What it means: " + ln.means + "." }),
        ln.todo ? el("p", { text: "What to do: " + ln.todo }) : null))) : null,
    it.evidence ? evidenceFold(it.evidence) : null);
  if (it.master) return el("li", {}, pluginLink(it.plugin), " needs ", el("span", { class: "mono", text: it.master }),
    el("span", { class: "tag " + (it.what === "missing" ? "bad" : "warn"), text: it.what === "missing" ? "missing" : "not active" }));
  if (it.plugin) {
    const li = el("li", {}, pluginLink(it.plugin), el("span", { class: "dim", text: "  position " + it.position + ", in " }), modLink(it.mod));
    if (it.made_by && it.made_by.length) li.append(el("span", { class: "tag warn", title: it.how || "", text: "made by " + it.made_by.join(", ") }));
    if (it.tool_title && !it.verdict) li.append("  ", toolButton(it.tool_title));
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
      el("h3", {}, st.title, whoTag(st.who),
        el("span", { class: "tag " + cls, text: word })),
      el("p", { class: "dim", text: st.why }),
      st.note ? el("p", { text: st.note }) : null,
      st.items.length ? el("ul", {}, ...st.items.slice(0, 200).map(stepItem)) : null,
      st.items.length > 200 ? el("p", { class: "dim", text: "Showing the first 200 of " + st.items.length + "." }) : null);
    if (st.action === "demaster") {
      const go = el("button", { type: "button", text: "Demaster Selected…" });
      go.title = "Shows what ModTrap would do, and asks before doing it";
      go.addEventListener("click", demasterGo);
      body.append(el("p", {}, go, el("span", { class: "dim", text: "  ModTrap does this step for you: it shows its plan first and asks before changing anything." })));
    }
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
  $("steps-summary").textContent = d.needs_dry ? "A dry run comes first" : open ? plural(open, "step") + " to go" : "Every step is done";
  const carries = Object.entries(d.contents || {}).filter(([k]) => k !== "other files").map(([k, n]) => n + " " + k);
  $("steps-info").textContent = "Taking out " + d.mods.join(", ") + (d.looking ? " · still looking into the mods' folders…" : carries.length ? " · besides plugins it carries: " + carries.join(", ") : "");
  const intro = el("div", { class: "card" },
    el("p", { text: "Everything it takes to get " + (d.mods.length === 1 ? "this mod" : "these mods") + " out of the modlist, in order. " + (state.changes
      ? "Each step says who does it: “ModTrap” steps are carried out by “Demaster Selected”, which shows its plan and asks first; “ModTrap starts it · you run it” steps have a button that starts the tool through MO2; “You” steps are things only you can do or judge. ModTrap checks the steps against the modlist's files each time it is read."
      : "ModTrap was started without --allow-changes, so it changes nothing: the steps marked “You” are done by hand in MO2 and xEdit, and ModTrap checks them against the modlist's files each time it is read.") }),
    el("p", { class: "dim", text: "Plugins to take out: " + d.trapped.join(", ") }));
  box.replaceChildren(...[toolCard(), intro, ...cards].filter(Boolean));
}

// --- the Process tab (DESIGN§18): the demaster as it goes, stage by stage ---------------------------------------------

const STAGE_TAB = { probe: "tools", dry: "job", plan: "selection", change: "selection", install: "selection", after: "steps" };
const TASK_ICON = { waiting: "○", going: "◐", done: "✓", failed: "✕", yours: "➜", skipped: "–" };
const STAGE_WORD = { waiting: ["to come", ""], going: ["going on", "warn"], done: ["done", "good"], failed: ["stopped", "bad"], yours: ["waits for you", ""], skipped: ["not needed", ""] };

function stageState(tasks) {
  const st = tasks.map((t) => t.state);
  if (!st.length) return "waiting";
  if (st.includes("failed")) return "failed";
  if (st.includes("going")) return "going";
  if (st.every((x) => x === "done" || x === "skipped")) return "done";
  if (st.includes("yours")) return "yours";
  return st.includes("done") ? "going" : "waiting";
}

// What comes after ModTrap's own part: the tools to run again and what only the owner can judge, from the steps.
function afterStage() {
  const d = state.stepsData;
  if (!d || !d.steps) return null;
  const ticks = state.stepsDone || {};
  const tasks = [];
  for (const st of d.steps) {
    // What ModTrap's own part left open counts here too: a plugin it could not demaster, a mod that stays enabled.
    const leftOpen = ["demaster", "disable"].includes(st.key) && st.state !== "done" && st.state !== "not needed";
    if (!(st.key.startsWith("tool:") || ["after-dry", "regenerate", "tools-wait", "mentions", "health", "play"].includes(st.key) || leftOpen)) continue;
    const ticked = st.manual && !!ticks[stepKey(st.key)];
    const done = ticked || st.state === "done";
    tasks.push({ key: st.key, text: st.title, note: leftOpen ? (st.note || "") : done || st.state === "not needed" ? "" : (st.who === "ModTrap" ? (st.key.startsWith("tool:") ? "ModTrap runs it and closes it" : "") : st.who === "both" ? "ModTrap starts it, you run it" : "yours to do or judge"),
      state: done ? "done" : st.state === "not needed" ? "skipped" : leftOpen && st.key === "demaster" ? "yours" : st.state.startsWith("wait") ? "waiting" : st.who === "ModTrap" ? "waiting" : "yours" });
  }
  if (!tasks.length) return null;
  // Until the demaster is in place these are to come, not yet the owner's turn.
  const placed = (state.process || []).some((s) => s.key === "install" && s.state === "done") || !state.changes;
  if (!placed) for (const t of tasks) if (t.state === "yours") t.state = "waiting";
  const all = stageState(tasks);
  if (placed && (d.checks || []).length) {
    const passed = d.checks.filter((c) => c.ok).length;
    tasks.push({ key: "checks", text: d.checked ? "ModTrap's checks after the demaster: all " + d.checks.length + " passed" : "ModTrap's checks after the demaster: " + passed + " of " + d.checks.length + " passed so far",
      note: d.checks.map((c) => (c.ok ? "✓ " : "· ") + c.text).join("  "), state: d.checked ? "done" : "waiting" });
  }
  return { key: "after", title: "After the demaster", who: "you", tasks: tasks, state: !placed && all !== "done" ? "waiting" : all, note: "The tools to run again, and what only you can judge. The Steps tab has the reasons and the evidence." };
}

// What the owner can press, at the task it belongs to (WHY§71): the same actions as on the tabs they come from,
// and beside them a way to that tab, to look before pressing.
function navButton(tab, label) {
  const b = el("button", { type: "button", class: "nav-link", text: label + " ↗", title: "Opens that tab, where this comes from" });
  b.addEventListener("click", () => showTab(tab));
  return b;
}
function actButton(label, run, primary) {
  const b = el("button", { type: "button", class: primary ? "primary" : "", text: label });
  b.addEventListener("click", async () => { b.disabled = true; try { await run(); } finally { state.processText = ""; renderProcess(); } });
  return b;
}
function tickBox(key) {
  const box = el("input", { type: "checkbox", checked: !!(state.stepsDone || {})[stepKey(key)] });
  box.addEventListener("change", () => {
    state.stepsDone = state.stepsDone || {};
    if (box.checked) state.stepsDone[stepKey(key)] = true; else delete state.stepsDone[stepKey(key)];
    saveUi();
    state.stepsText = ""; pollSteps(true);
    state.processText = ""; renderProcess();
  });
  return el("label", { class: "tickoff" }, box, "I have done this");
}

function processIdle() {
  const d = state.demaster, job = state.job;
  return state.status === "ready" && !state.dmChain && !(state.session && state.session.locked) &&
    !(d && (d.state === "working" || d.state === "verified")) && !(job && !["done", "failed", "stopped"].includes(job.state)) &&
    !(state.probe && state.probe.state === "working");
}

function taskActions(stage, task, first, firstOpen) {
  const d = state.demaster, out = [];
  const can = state.changes && state.picked.size;
  if (stage.key === "plan" && task.key === "confirm" && task.state === "yours" && can) {
    const p = state.dmPlan;
    if (p) {
      out.push(el("span", { class: "act-note", text: plural(p.demaster.length, "plugin") + " to demaster, " + plural(p.switch_off.length, "patch", "patches") + " to switch off, " +
        plural((p.disable_mods || []).length + (p.blocked ? 0 : p.mods.length), "mod") + " to disable" + (p.needs_you.length ? ", " + p.needs_you.length + " left to you" : "") + "." }));
      out.push(actButton("Go ahead", planGoAhead, true), actButton("Not now", async () => planNotNow()), navButton("selection", "The whole plan, on Selection"));
    } else if (processIdle()) {
      out.push(actButton("Show the plan", askDemasterPlan, true), navButton("selection", "Selection"));
    }
  }
  if (first && firstOpen && can && processIdle() && ["probe", "dry"].includes(stage.key) && ["waiting", "failed"].includes(stage.state) && !state.dmPlan) {
    const probe = probeReason();
    out.push(actButton(stage.state === "failed" ? "Try again: Demaster Selected" : "Demaster Selected", demasterGo, true),
      el("span", { class: "act-note", text: probe ? "Runs the probe first, then the dry run, then asks you with the plan." : "Runs the dry run, then asks you with the plan." }),
      navButton(stage.key === "probe" ? "tools" : "selection", stage.key === "probe" ? "The probe, on Tools" : "Selection"));
  }
  if (task.state === "failed") {
    if (stage.key === "change" && d && d.state === "failed") out.push(actButton("Close this", () => demasterCall("/api/demaster/drop", {})));
    out.push(navButton(stage.key === "probe" ? "tools" : stage.key === "dry" ? "job" : "selection", stage.key === "probe" ? "Tools" : stage.key === "dry" ? "Dry run" : "Selection"),
      navButton("log", "Log"));
  }
  if (stage.key === "install" && first && d && d.state === "verified" && state.dmChain !== "install") {
    out.push(actButton("Put them in place", putInPlace, true), actButton("Not now", () => demasterCall("/api/demaster/drop", {})),
      navButton("selection", "What is ready, on Selection"));
  }
  if (stage.key === "install" && task.key === "left") {
    out.push(navButton("steps", "What is left, on Steps"), navButton("job", "What it takes from the mod, on Dry run"));
  }
  // The tools one after another (WHY§82): offered at the first tool that is still to run, whenever a demaster is in
  // place, whether or not the setting was on when it was put in place.
  if (stage.key === "after" && stage.tasks.find((t) => t.key.startsWith("tool:") && t.state === "yours") === task) {
    if (state.dmChain === "tools") {
      out.push(el("span", { class: "act-note", text: "The tools are being started one after another. ModTrap runs and closes the ones it can; any other is yours to work, then close." }),
        actButton("Stop the row", async () => { state.dmChain = ""; state.toolsNow = ""; toast("Stopped. A tool that is open stays open; the rest are yours."); }));
    } else if (processIdle() && !toolGoing(state.tool)) {
      out.push(actButton("Start the tools one after another", async () => startToolsRow(), true));
    }
  }
  if (stage.key === "after" && (task.state === "yours" || task.state === "done")) {
    const st = ((state.stepsData || {}).steps || []).find((x) => x.key === task.key);
    if (st) {
      if (task.state === "yours") for (const it of (st.items || [])) if (it.tool) out.push(toolButton(it.tool));
      if (st.manual) out.push(tickBox(st.key));
      out.push(navButton("steps", "Why, with the evidence, on Steps"));
    }
  }
  return out;
}

function renderProcess() {
  const stages = (state.process || []).slice();
  const after = afterStage();
  if (after) stages.push(after);
  const tool = state.tool;
  const text = JSON.stringify(stages) + "#" + [state.status, state.dmChain || "", state.dmPlan ? 1 : 0, state.picked.size, state.changes ? 1 : 0,
    state.changes ? probeReason() : "", state.demaster ? state.demaster.state : "", tool ? tool.state + tool.title : "",
    state.dmWait ? state.dmWait.kind : "", state.dmChain === "tools" ? "row" : "",
    state.session && state.session.locked ? 1 : 0].join("|");
  const going = stages.find((s) => s.state === "going"), failed = stages.find((s) => s.state === "failed");
  const yours = !going && !failed && stages.find((s) => s.state === "yours" && s.key !== "after");
  const dot = $("process-dot");
  dot.hidden = !(going || failed || yours);
  dot.className = "live-dot" + (failed && !going ? " bad" : yours ? " yours" : "");
  const gd = $("group-dot");
  gd.hidden = dot.hidden; gd.className = dot.className;
  if (text === state.processText) return;
  state.processText = text;
  const flow = $("process-flow");
  $("process-summary").textContent = !stages.length ? "Process" : going ? "Now: " + going.title : failed ? "Stopped at: " + failed.title
    : yours ? "Waits for you: " + yours.title : stages.every((s) => s.state === "done") ? "Everything is done"
    : after && after.state === "yours" && stages.every((s) => s === after || s.state === "done")
      ? ((state.stepsData || {}).checked ? "The demaster is complete and checked. Left to you: " + (((state.stepsData || {}).left_to_owner || []).map((t) => t.charAt(0).toLowerCase() + t.slice(1)).join("; ") || "nothing")
        : "ModTrap's part is done. Yours now: " + after.title) : "Process";
  $("process-intro").hidden = !stages.length;
  if (!stages.length) { flow.replaceChildren(el("div", { class: "card" }, el("p", { class: "dim", text: "Open a modlist and tick a mod: its demaster shows here as it goes." }))); return; }
  const paused = waitNote(), pw = $("process-wait");
  pw.hidden = !paused;
  pw.replaceChildren(...(paused ? [paused] : []));
  if (paused) $("process-summary").textContent = "Paused: waits for you";
  flow.replaceChildren(...stages.map((s, i) => {
    const word = STAGE_WORD[s.state] || STAGE_WORD.waiting;
    const title = el("button", { type: "button", text: s.title, title: "Go to where this stage is worked" });
    title.addEventListener("click", () => showTab(STAGE_TAB[s.key] || "selection"));
    const done = s.tasks.filter((t) => t.state === "done" || t.state === "skipped").length;
    return el("div", { class: "stage s-" + s.state },
      el("div", { class: "stage-head" }, el("span", { class: "n", text: String(i + 1) }), title,
        el("span", { class: "tag " + word[1] + (s.state === "yours" ? " t-yours" : ""), text: word[0] + " · " + done + "/" + s.tasks.length })),
      s.note ? el("p", { class: "stage-note", text: s.note }) : null,
      el("ul", { class: "tasks" }, ...s.tasks.map((t, k) => {
        const acts = taskActions(s, t, k === s.tasks.findIndex((x) => !["done", "skipped"].includes(x.state)), i === stages.findIndex((x) => x.state !== "done"));
        return el("li", { class: "t-" + t.state },
          el("span", { class: "ico", "aria-hidden": "true", text: TASK_ICON[t.state] || "○" }),
          el("span", { text: t.text + (t.state === "going" ? " …" : "") }),
          t.note ? el("span", { class: "note", text: t.note }) : null,
          acts.length ? el("span", { class: "acts" }, ...acts) : null);
      })));
  }));
}

async function pollSteps(force) {
  if (state.status !== "ready") return;
  const mods = [...state.picked];
  const key = mods.slice().sort().join("|") + "#" + state.loaded + "#" + (state.job ? state.job.id + state.job.state : "") +
    "#" + (state.demaster ? state.demaster.state : "");
  if (!force && key === state.stepsKey && !state.stepsLooking && state.tab !== "steps") return;
  try {
    const d = await api("/api/steps", { mods: mods });
    state.stepsKey = key;
    state.stepsLooking = d.looking;
    const text = JSON.stringify(d);
    if (text !== state.stepsText) { state.stepsText = text; state.stepsData = d; renderSteps2(d); renderProcess(); }
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
    const go = el("button", { type: "button", class: "primary", text: "Go ahead", disabled: p.mo2_closed == null || p.nothing });
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
        p.mo2_closed === false ? "MO2 is open. An open MO2 writes its own lists back over ModTrap's, so it must be closed for this: press the button and ModTrap asks whether to close it for you." : "ModTrap cannot tell whether MO2 is open on this PC, so it will not change the lists." }),
      el("div", { class: "actions" }, go, closed ? null : again, cancel));
  } else {
    const b = el("button", { type: "button", class: "primary", text: "Add it for me", disabled: !state.changes || !todo || st("needs").state !== "done" || d.looking || !!probeReason() });
    b.title = probeReason() ? "Not yet: " + probeReason() + "." : !state.changes ? "Switched off. ModTrap changes a modlist only when it is started with --allow-changes, which is for once it has been proven on your PC." :
      st("needs").state !== "done" ? "First get what the mod needs: see step “Get what the mod needs”." : !todo ? "There is nothing left for ModTrap to do here." : "Shows what ModTrap would do, and asks before doing it";
    b.addEventListener("click", askAddPlan);
    kids.push(el("div", { class: "actions" }, b, probeButton(), el("span", { class: probeReason() ? "would-needs" : "dim", text: probeReason() ? "Not yet: " + probeReason() + "." : !state.changes ?
      "Switched off for now: ModTrap putting the mod in for you waits until it has been proven on your modlist. The steps below say how to do it by hand." :
      "ModTrap copies the mod in, places and enables it, places and activates its plugins, and checks the result. It shows the plan and asks first." })),
      state.addPlanError ? el("p", { class: "would-needs", text: state.addPlanError }) : null);
  }
  for (const j of (d.added || []).filter((x) => x.state === "added").slice(0, 12)) {
    const undo = el("button", { type: "button", text: "Take it out again" });
    undo.addEventListener("click", async () => {
      if (!await confirmBox("Put the mod list and the load order back as they were before this add, and remove ModTrap's copy of the mod from MO2's mods folder? MO2 must be closed.")) return;
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

// The record check (DESIGN§16.5): start it from its step, and show what xEdit reported.
const REC_WORDS = { preparing: "preparing…", starting: "starting xEdit through MO2…", loading: "xEdit is loading the whole load order…", reading: "xEdit is reading the records…", checking: "checking…" };

function recordsBlock(d) {
  const r = d.records;
  const active = (d.mods || []).filter((x) => x.enabled && x.plugins.some((p) => p.active)).map((x) => x.name);
  const going = r && !["done", "failed", "stopped"].includes(r.state);
  const start = el("button", { type: "button", class: "primary", text: r && r.state === "done" ? "Check again through xEdit" : "Check through xEdit", disabled: !active.length || going || !!(state.session && state.session.locked),
    title: active.length ? "Starts your xEdit through MO2 with ModTrap's script, which only reads. The whole load order is loaded, so on a large modlist it takes many minutes." : "The plugin must be active first: xEdit can only read what is in the load order." });
  start.addEventListener("click", async () => {
    start.disabled = true;
    try { await api("/api/records/start", { mods: active }); toast("Starting xEdit through MO2…"); } catch (e) { toast(e.message); }
    state.addText = "";
    pollAdd(true);
  });
  const kids = [el("div", { class: "actions" }, start, going ? (() => {
    const b = el("button", { type: "button", text: "Stop waiting" });
    b.addEventListener("click", async () => { try { await api("/api/records/stop", {}); } catch (e) { toast(e.message); } pollAdd(true); });
    return b;
  })() : null, going ? el("span", {}, el("span", { class: "spinner", "aria-hidden": "true" }), " " + (REC_WORDS[r.state] || r.state) + " The Log tab shows its lines.") : null)];
  if (r && (r.state === "failed" || r.state === "stopped")) kids.push(el("p", { class: "would-needs", text: "The check did not finish: " + (r.message || r.state) + "." }));
  if (r && r.state === "done" && r.result) {
    for (const f of r.result.files) {
      const names = (list) => list.slice(0, 8).map(([n, c, tool]) => n + " (" + c + (tool ? ", made by a tool" : "") + ")").join(", ") + (list.length > 8 ? " and " + (list.length - 8) + " more" : "");
      const recList = (list, how) => el("details", {}, el("summary", { text: "The records" + (list.length >= 400 ? " (the first 400)" : "") }),
        el("ul", {}, ...list.map((x) => el("li", { class: "mono", text: x.sig + " " + x.form + " " + x.edid + "   " + how(x) }))));
      kids.push(el("div", { class: "plug" },
        el("p", {}, pluginLink(f.name), el("span", { class: "tag " + (f.reading === "clean" ? "good" : "warn"), text: f.reading === "clean" ? "nothing that needs a patch" : "needs a look" })),
        el("p", { class: "dim", text: plural(f.own, "record") + " of its own, " + f.overrides + " that override another plugin's: " + f.alone + " that only it changes or that agree, " + f.same + " identical to what they override." }),
        f.takes_count ? el("p", { class: f.needs_patch ? "would-needs" : "" }, f.takes_count + " record(s) it wins that other plugins also change: their change to those records is lost. From: " + names(f.from) + ".") : null,
        f.takes_count ? recList(f.takes, (x) => "also changed by " + x.from.join(", ")) : null,
        f.loses_count ? el("p", { class: f.lost_to_hand ? "would-needs" : "" }, f.loses_count + " record(s) a later plugin wins, so its own change to them does not show. To: " + names(f.to) + ".") : null,
        f.loses_count ? recList(f.loses, (x) => "won by " + x.to) : null,
        f.needs_patch || f.lost_to_hand ? el("p", { text: "Where both changes matter, a small patch that carries both is the fix: in xEdit, copy the record as override into a new plugin loaded after both and merge the fields. What a tool made is settled by running the tool again." }) : null));
    }
    for (const n of r.result.missing) kids.push(el("p", { class: "would-needs", text: n + " was not loaded by xEdit." }));
  }
  return el("div", {}, ...kids.filter(Boolean));
}

function addStepCard(st, d) {
  const done = state.stepsDone || {};
  const ticked = st.manual && !!done[addKey(st.key)];
  const isDone = ticked || st.state === "done" || st.state === "not needed";
  const waiting = !isDone && st.state.startsWith("waiting");
  const [word, cls] = ticked ? ["ticked off by you", "good"] : STEP_STATE[st.state] || [st.state, ""];
  const body = el("div", {},
    el("h3", {}, st.title, whoTag(st.who),
      el("span", { class: "tag " + cls, text: word })),
    el("p", { class: "dim", text: st.why }),
    st.note ? el("p", { text: st.note }) : null,
    st.items.length ? el("ul", {}, ...st.items.map((it) => el("li", {}, it.text,
      it.tag ? el("span", { class: "tag " + (it.cls || ""), text: it.tag }) : null,
      it.start ? el("span", {}, "  ", toolButton(it.start)) : null,
      it.add && findMod(it.add) ? (() => {
        const b = el("button", { type: "button", class: "linkish", text: "  add it too" });
        b.addEventListener("click", () => addCandidate(it.add));
        return b;
      })() : null))) : null);
  if (st.key === "records") body.append(recordsBlock(d));
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
    el("div", { class: "card" }, el("p", { text: "What ModTrap can tell from the files; what is inside the plugins' records is read through xEdit in its own step. ModTrap checks every step against the modlist's files each time the modlist is read." }), room,
      d.cut ? el("p", { class: "would-needs", text: "The search for shared files was cut short: there may be more than is listed." }) : null,
      d.unknown && d.unknown.length ? el("p", { class: "would-needs", text: "No longer in MO2: " + d.unknown.join(", ") }) : null),
    toolCard(), addActionCard(d),
    ...askCards,
    ...d.mods.map((x) => addModCard(x, d.place, (d.staged || []).find((r) => r.installer && r.state === "ready" && r.name === x.name))),
    el("h2", { text: "The steps, in order" }), ...cards].filter(Boolean));
}

async function pollAdd(force) {
  if (state.status !== "ready") return;
  const mods = (state.adding || []).slice();
  const staged = (state.staged || []).slice();
  const key = mods.join("|") + "#" + staged.join("|") + "#" + state.loaded;
  if (!force && key === state.addKeySeen && !state.addLooking && !state.recGoing) return;
  try {
    const d = mods.length || staged.length ? await api("/api/add", { mods: mods, staged: staged }) : { looking: false, mods: [], steps: [] };
    state.addKeySeen = key;
    state.addLooking = d.looking || d.unpacking;
    state.recGoing = !!(d.records && !["done", "failed", "stopped"].includes(d.records.state));
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
      + JSON.stringify(state.addPlan || 0) + (state.addPlanError || "") + state.changes + probeReason();
    if (text !== state.addText) { state.addText = text; renderAdd(d); }
  } catch (e) { /* the next round tries again */ }
}

// --- tabs, the log, and the loop -------------------------------------------------------------------------------------

function showTab(name) {
  // Two rows (DESIGN§4): the section the tab belongs to, and that section's tabs.
  const mine = document.querySelector('#tabs button[data-tab="' + name + '"]');
  const group = mine ? mine.dataset.group : "modlist";
  state.groupTab = state.groupTab || {};
  state.groupTab[group] = name;
  let shown = 0;
  document.querySelectorAll("#tabs button").forEach((b) => {
    b.classList.toggle("on", b.dataset.tab === name);
    b.hidden = b.dataset.group !== group;
    if (!b.hidden) shown++;
  });
  $("tabs").classList.toggle("single", shown < 2);
  document.querySelectorAll("#groups button[data-group]").forEach((b) => b.classList.toggle("on", b.dataset.group === group));
  document.querySelectorAll(".tab").forEach((t) => { t.hidden = t.id !== "tab-" + name; });
  state.tab = name;
  updateTray();
  saveUi();
  if (name === "history") { state.historyText = ""; pollHistory(); }
  if (name === "updates") loadUpdates();
  if (name === "job") paneFollow("job-log");
  if (name === "log") paneFollow("log");
}

// The log panes keep to the latest line (WHY§85): each shows its newest line at the bottom, at every start and
// whenever its tab is opened, until the owner scrolls away from it; then it stays where they left it, and takes up
// the latest line again once they scroll back down to it. A pane that is not shown cannot be scrolled, so what
// the owner last did is kept here, not asked of the pane.
const PANES = { "log": { follow: true, top: 0 }, "job-log": { follow: true, top: 0 } };
function paneFollow(id) {
  const p = $(id), s = PANES[id];
  if (!p || !p.offsetParent) return;                       // not shown: set when it comes into view
  p.scrollTop = s.follow ? p.scrollHeight : s.top;
  s.top = p.scrollTop;
}
function paneWatch(id) {
  const p = $(id);
  p.addEventListener("scroll", () => {
    if (!p.offsetParent) return;
    const s = PANES[id], atEnd = p.scrollTop + p.clientHeight >= p.scrollHeight - 30;
    // Only the owner's own move away from the end stops the following: a move up. Lines that come, a pane that
    // is emptied or shown again, and a window that changes size also move it, and mean nothing.
    if (atEnd) s.follow = true; else if (p.scrollTop < s.top - 1) s.follow = false;
    s.top = p.scrollTop;
  });
  // A pane that comes into view (its tab opens, the page is shown after a start) or changes size takes its place
  // again: the last line if it follows, else where it was left.
  if (typeof ResizeObserver === "function") new ResizeObserver(() => paneFollow(id)).observe(p);
}

async function pollLog() {
  try {
    const d = await api("/api/log?after=" + state.logAfter);
    if (d.lines.length) {
      const log = $("log"), jl = $("job-log");
      for (const ln of d.lines) {
        log.append(el("span", { class: ln.level, text: ln.t + "  " + ln.text + "\n" }));
        if (ln.source === "dryrun") {
          if (/^dry run \S+: \d+ trapped plugin/.test(ln.text)) { jl.replaceChildren(); PANES["job-log"].follow = true; }     // a new run: its own lines only
          jl.append(el("span", { class: ln.level, text: ln.t + "  " + ln.text + "\n" }));
        }
        state.logAfter = ln.seq;
      }
      if (PANES.log.follow) paneFollow("log");
      if (PANES["job-log"].follow) paneFollow("job-log");
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
  state.mo2 = s.mo2 || null;
  renderMo2();
  state.settings = s.settings || {};
  renderSettings();
  state.process = s.process || [];
  renderProcess();
  const up = $("updated");
  up.hidden = !s.updated_on_disk;
  const onDisk = s.updated_on_disk ? (s.updated_on_disk.version || "?") : "";
  if (s.updated_on_disk && up.dataset.v !== onDisk) {
    up.dataset.v = onDisk;
    const quit = el("button", { type: "button", text: "Quit ModTrap" });
    quit.addEventListener("click", quitModTrap);
    up.replaceChildren("This is ModTrap " + s.version + ", still running, but the files in its folder have changed since it was started" + (onDisk && onDisk !== s.version ? ": they are version " + onDisk + " now" : "") + ". Quit it and start it again: until then the program in memory and the scripts on disk are of different versions, and ModTrap starts nothing.  ", quit);
  }
  state.working = s.working || [];
  showWork();
  state.demaster = s.demaster || null;
  state.probe = s.probe || null;
  ticksOfThisDemaster();
  demasterChain();
  state.save = s.save || null;
  renderSave();
  const toolText = JSON.stringify(s.tool || null);
  if (toolText !== state.toolText) { state.toolText = toolText; state.tool = s.tool || null; state.addText = ""; state.stepsText = ""; state.stepsKey = ""; state.addKeySeen = ""; }
  renderState(s);
  if (s.log_epoch !== state.logEpoch) {             // another session's log: read it from the start
    state.logEpoch = s.log_epoch;
    state.logAfter = 0;
    state.jobSeen = "";
    $("log").replaceChildren();
    $("job-log").replaceChildren();
    for (const k in PANES) { PANES[k].follow = true; PANES[k].top = 0; }       // a log read afresh: its latest line
  }
  const key = s.status === "ready" ? (s.session ? s.session.id : "") + "|" + s.folder + "|" + s.profile + "|" + s.mods + "|" + s.plugins + "|" + s.issue_count + "|" + (state.gen || 0) : "";
  if (s.status === "ready" && (key !== state.loaded || was !== "ready")) {
    try { await loadLists(key, s); } catch (e) { showMessage(e.message, true); }
  }
  updateDryButton();
  await pollJob();
  await pollSteps(false);
  await pollAdd(false);
  renderDemaster(false);
  updateDemasterButton();
  renderProbe();
  await pollHistory();
  await pollLog();
}

function loop() {
  if (state.quit) return;
  const busy = state.status === "reading" || state.addLooking || state.recGoing || (state.save && state.save.state === "packing") || (state.demaster && state.demaster.state === "working") || (state.probe && state.probe.state === "working") || (state.tool && (state.tool.state === "starting" || state.tool.state === "running")) || (state.job && !["done", "failed", "stopped"].includes(state.job.state));
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
document.addEventListener("drop", (e) => {
  e.preventDefault(); dragDepth = 0; dragOn(false);
  if (state.tab === "updates" && state.status === "ready") updatesDropped(e); else dropped(e);
});

$("profile").addEventListener("change", () => $("open-form").requestSubmit());
$("rescan").addEventListener("click", async () => {
  try { state.gen = (state.gen || 0) + 1; await api("/api/rescan", {}); state.status = "reading"; } catch (e) { problem(e.message); }
  tick();
});
document.querySelectorAll("#tabs button").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
const GROUP_FIRST = { modlist: "mods", demaster: "selection", add: "add", record: "history", settings: "settings" };
document.querySelectorAll("#groups button[data-group]").forEach((b) => b.addEventListener("click", () =>
  showTab((state.groupTab || {})[b.dataset.group] || GROUP_FIRST[b.dataset.group])));
$("dry-run").addEventListener("click", showPlan);
$("demaster").addEventListener("click", demasterGo);
$("process-go").addEventListener("click", demasterGo);
$("job-stop").addEventListener("click", async () => {
  if (!await confirmBox("Stop waiting for this dry run? xEdit itself stays open for you to close; it has changed nothing.")) return;
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
$("s-mo2").addEventListener("click", toggleMo2);
$("s-tools").addEventListener("click", () => showTab("tools"));
for (const li of $("steps").children) li.addEventListener("click", () => { if (li.dataset.tab) showTab(li.dataset.tab); });
$("log-copy").addEventListener("click", () => copyText($("log").textContent, "The log"));
$("save-session").addEventListener("click", saveSession);
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
paneWatch("log"); paneWatch("job-log");
loop();
