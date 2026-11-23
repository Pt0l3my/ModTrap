"use strict";
// ModTrap's page (DESIGN§4). Version 0.1 only reads: every call below is a GET, except opening a folder.

const TOKEN = document.body.dataset.token;
const $ = (id) => document.getElementById(id);
const state = { status: "none", mods: [], plugins: [], picked: new Set(), logAfter: 0, loaded: "", details: new Map() };

// What changes MO2's lists must find MO2 closed: an open MO2 holds them in memory and writes its own back.
const NEEDS_MO2_CLOSED = new Set(["/api/separator/add", "/api/list/move", "/api/list/rename", "/api/list/undo", "/api/add/run", "/api/add/revert", "/api/updater/revert", "/api/demaster/install", "/api/demaster/revert",
  "/api/probe/start", "/api/probe/cleanup"]);

async function api(path, body) {
  if (NEEDS_MO2_CLOSED.has(path) && !(await mo2Closed())) throw new Error("MO2 is still open; nothing was changed");
  return call(path, body);
}

// This page's own mark (MT64): ModTrap knows by it which pages are open, and closes when the last one is gone.
const PAGE_MARK = Array.from(crypto.getRandomValues(new Uint8Array(12)), (b) => b.toString(16).padStart(2, "0")).join("");
const lastWord = (what) => { try { navigator.sendBeacon("/bye", new URLSearchParams({ page: PAGE_MARK, token: TOKEN, what })); } catch (e) { /* the silence says it instead */ } };
window.addEventListener("pagehide", () => lastWord("bye"));
document.addEventListener("freeze", () => lastWord("asleep"));
// ModTrap's worker in the browser: it keeps one small page, which offers to start ModTrap when it is not running.
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => { /* a browser that keeps none: its own error page shows instead */ });

async function call(path, body) {
  const opt = { headers: { "X-ModTrap-Token": TOKEN, "X-ModTrap-Page": PAGE_MARK } };
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
    const box = el("div", { class: "modal" + (o.wide ? " wide" : ""), role: "dialog", "aria-modal": "true" }, ...paras, ...(o.nodes || []), input, el("div", { class: "actions" }, yes, no));
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
const GATED = /^(Dry run through xEdit|Start the dry run|Demaster Selected|Demaster what is left|Go ahead|Put them in place|Put them back in place|Revert|Uninstall|Start it through MO2|Start the tools one after another|Run the probe|Remove the test mods|Install mod$|Update mod$|Manual placement|OK, install it there|Retire ModTrap|Check through xEdit|Check again through xEdit)/;
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
  toast.timer = setTimeout(() => { t.hidden = true; }, Math.min(9000, Math.max(2600, String(text).length * 45)));      // a longer line stays longer
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
  ["updates_at_launch", "Look for updates when ModTrap starts", "Asks Nexus and GitHub whether the modlist's mods have newer files, once at each start (Updater list). It asks only those two, reads the answers and changes nothing. No key is needed. Off: only when you press “Scan for updates”."],
  ["site_window", "Open a site's page for a download in a small window, not a tab", "Where ModTrap cannot fetch a file itself, it opens the mod's page for you to press its download button. Off: the page opens as a new tab. On: it opens in a small window beside ModTrap. Either way the browser puts it in front: a page has no way to open a tab behind itself. To open it behind ModTrap's tab, press the update button with Ctrl held, or with the middle mouse button: that is the browser's own doing, and such a tab ModTrap cannot close."],
  ["site_window_closes", "Close the site's page when the download is here", "On: when the file is whole and taken, or the waiting ends, ModTrap closes the tab or window it opened for the download, and your browser returns to ModTrap. For that the site's page stays tied to ModTrap's tab, and a page that is tied can send the tab that opened it to another address; so this is done only for Nexus, GitHub and LoversLab, and while such a page is open your browser asks before ModTrap's tab goes anywhere. Off: the page is cut loose from ModTrap before it loads, and you close it yourself."],
  ["install_on_drop", "Install a dropped mod by itself", "Off: a mod's archive dropped on the Installer tool is unpacked and read, ModTrap shows what it overwrites and the tools that have to do with it, and one press on “Install mod” installs it. On: it is installed as soon as it is read, with no press; with “Always place a new mod by hand”, ModTrap takes you to the Mods tab to choose its place instead. It waits where the mod's installer asks which parts to install, and stops, saying why, where something the mod needs is missing."],
  ["scan_on_enable", "Scan a mod when it is enabled on the Modlist page", "On: when you tick a mod with plugins on, ModTrap then looks through the load order for what the mod's plugins overwrite and what overwrites them, and tells you in a note at the bottom of the page. It only reads. Off: the scan runs when you ask for it, from the mod's right-click menu or its card."],
  ["quit_with_page", "Close ModTrap when its page is closed", "ModTrap has no window, so its page is all there is of it. On: when the last tab with ModTrap's page is closed (or its browser is), ModTrap saves its session and closes, a few seconds later; a page only loaded anew is back before that. It never closes in the middle of a job, a tool's run or a scan: it waits for that to end. A browser that is ended without a word is noticed after four minutes. Off: ModTrap runs until “Quit”."],
  ["start_from_page", "Let ModTrap's page start ModTrap", "When ModTrap has closed and your browser brings its tab back, a small page ModTrap left in the browser shows instead and starts ModTrap again; then you are back where you were. For that, ModTrap enters one kind of link (modtrap:) for your Windows account, which starts this ModTrap.exe. Your browser asks before it opens such a link; you can let it remember the answer for this page. The link carries nothing: whatever it says, ModTrap is started the one same way, as a double-click does. Off: the entry is taken out again, and the page only tells you to start ModTrap.exe yourself."],
  ["console_window", "Show ModTrap's console window", "ModTrap's program writes what it does to a console window. Every line of it is on this page too (History, then Log), and nothing ModTrap does needs the window, so it is hidden: the browser is all you see. On: the window is shown, minimised, in the taskbar. Either way “Quit” at the top ends ModTrap, and closing this tab does not: start ModTrap again and its page is back. A start that fails shows the window, with what went wrong. Windows only, and only for a ModTrap started by ModTrap.exe: one started from a command prompt of yours leaves that window alone."],
  ["mod_pictures", "Show a mod's picture in its web", "A click on a mod's name opens its web. On: where the mod's page at Nexus or its GitHub repository is known, ModTrap fetches the one picture that page opens with, from the site, and shows it there; it is kept in ModTrap's own folder for a month, so it is fetched once. Only the picture is asked for, and no key is sent. Off: no picture is fetched."],
  ["manual_placement", "Always place a new mod by hand", "Off: “Install mod” puts a new mod last (before what the modlist's tools made) with one press, and tells what it overwrites there. On: “Install mod” takes you to the Mods tab instead, where you click between two mods to choose its place; ModTrap shows what the mod overwrites at that place and installs it there on your OK. An update always takes the older version's place."],
  ["stay_on_tab", "Stay on ModTrap's tab when a site's page is opened", "A browser always puts a new tab in front, and a page cannot change that. On: ModTrap's program takes the browser straight back to ModTrap's tab, with the browser's own key for the tab before (Ctrl+Page Up), pressed only when the window in front is your browser's; the site's page stays open in its tab behind. Off: you stay on the site's page. Windows only."],
  ["downloads_move", "Move a mod's download from the browser's folder into ModTrap's downloads folder", "A file you download for an update in your browser lands in the browser's Downloads folder. On: ModTrap moves it into its own downloads folder (see the Downloads tab), where it is kept with where it came from and found again instead of being downloaded twice. Off: ModTrap copies it there and leaves yours where it is. A file in MO2's own downloads folder is always used from there and never moved."],
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

// The menu of one mod (WHY§103), on the Mods tab and on the Updater list.
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
  if (!state.installed || state.installedFor !== state.loaded) { try { state.installed = await api("/api/installed"); state.installedFor = state.loaded; } catch (e) { /* the menu still serves */ } }
  const inst = state.installed ? state.installed.rows.find((u) => u.mod === mod && u.there) : null;
  const page = r && r.page;
  const rows = [
    { text: r && r.given ? "Change the source link…" : "Add a source link…", run: () => sourceLink(mod, r ? r.given : "") },
    r && r.given ? { text: "Forget my source link", run: async () => { try { await api("/api/updates/link", { mod, url: "" }); toast("The source link is forgotten."); await loadUpdates(); } catch (e) { toast(e.message); } } } : undefined,
    r && r.get ? { text: r.state === "update" ? "Update it" + (r.newest ? " to " + r.newest : "") : "Look at its files for a newer one…", note: "The Updater carries the update through; where the site gives the file only to your browser, its page is opened for your press on its download button", run: () => getUpdate(mod) } : undefined,
    m && m.kind === "mod" ? { text: "Manual update…", note: "For a file you downloaded yourself, from any site: it goes to Install mods as a newer version of this mod", off: !state.changes, run: () => manualUpdate(mod) } : undefined,
    r ? { text: r.fav ? "Remove from favourites" : "Mark as favourite", run: () => setFavourite(mod, !r.fav) } : undefined,
    r && (r.host === "nexus" || r.host === "github") ? { text: "Ask about this mod now", note: r.host === "nexus" && state.updates && !state.updates.key ? "Nexus is asked only with your key" : "", run: async () => { try { await api("/api/updates/scan", { mods: [mod] }); toast("Asking about “" + mod + "”…"); } catch (e) { toast(e.message); } state.upSig = ""; loadUpdates(); } } : undefined,
    { text: "Open its page", off: !page, note: page ? page : "No page is known for this mod: add a source link", run: () => openTab(page) },
    { text: "Copy its page's address", off: !page, run: () => navigator.clipboard.writeText(page).then(() => toast("The address is copied."), () => toast("The address could not be copied.")) },
    ...(onMods() && m && m.kind === "mod" ? [null,
      { text: m.enabled ? "Disable it" : "Enable it", off: !state.changes || !m.listed, note: state.changes ? "As its tick does: the mod's line in MO2's list, and its plugins by MO2's own rule" : NO_CHANGES, run: () => listSet([mod], !m.enabled) },
      { text: "Move to priority…", off: !state.changes || !m.listed, note: state.changes ? "For a place far away; nearby, drag the row" : NO_CHANGES, run: () => moveToPriority(mod) },
      { text: "Show its web…", note: "The mod in the middle of every mod it has to do with: what it needs, what needs it, patches, what it overwrites and what overwrites it, conflicts. As a click on its name does.", run: () => webOpen(mod) },
      { text: "Evaluate it at its place…", note: "What its overwrites come to: which change nothing, which are what a patch or a retexture is for, and which are the usual ways a modlist breaks; and whether its own files fit this game. It only reads.", run: () => evaluateMod(mod) },
      { text: "Scan what it overwrites", note: "Whether its plugins stand safely in the load order, the records and files it overwrites, and what overwrites its own. It only reads.", run: () => scanMod(mod, true) },
      { text: "Add separator below…", off: !state.changes, note: state.changes ? "A separator of MO2's list, right below this mod" : NO_CHANGES, run: () => addSeparator(mod) }] : []),
    ...(m && m.kind === "mod" ? [null, inst
      ? { text: "Uninstall…", off: !state.changes, note: state.changes ? "ModTrap installed this mod" + (inst.with.length ? ", together with " + inst.with.map((n) => "“" + n + "”").join(", ") : "") + ": MO2's lists are put back as they were before that install, and ModTrap's copy of the mod is taken out again" : NO_CHANGES,
        run: () => uninstallJob(inst.job, [mod].concat(inst.with).map((n) => "“" + n + "”").join(", ")) }
      : { text: "Uninstall…", off: true, note: "ModTrap takes out only what it installed itself, and this mod it did not. It can disable it: the mod's files stay where they are (ModTrap never deletes a mod)." }] : []),
    null,
    { text: "Copy the mod's name", run: () => navigator.clipboard.writeText(mod).then(() => toast("The name is copied."), () => toast("The name could not be copied.")) },
    state.tab === "updates" ? { text: "Show it on the Mods tab", run: () => { showInList(mod); } } : { text: "Show it on the Updater list", run: () => { state.upFilter = { state: "", origin: "", on: false, text: mod }; showTab("updates"); } },
    !onMods() && m && m.row && m.row.classList.contains("tickable") ? { text: state.picked.has(mod) ? "Untick it" : "Tick it, to take it out", run: () => { togglePick(mod, !state.picked.has(mod)); updateTray(); } } : undefined,
  ].filter((v) => v !== undefined);
  menuAt(x, y, mod, rows);
}

// Files dropped on the Updater list, or chosen with its button (WHY§103): a Wabbajack file, meta files of downloads,
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
const UP_STATE = { update: ["Update out", "bad"], maybe: ["Unclear", "warn"], current: ["Up to date", "good"], "not asked": ["Not asked yet", ""], none: ["Cannot be asked", ""], gone: ["Gone from its page", "warn"], replaced: ["Older version", ""] };
const UP_ORIGIN = { list: "the list's own", added: "added afterwards", modtrap: "added by ModTrap", "": "" };
const UP_HOST = { nexus: "Nexus", github: "GitHub", loverslab: "LoversLab", url: "web address", "": "not known" };
// The update button of one mod (MT40): ModTrap fetches the newer file where it can and takes it to Install mods; where it
// cannot, the file's page is opened and the reason said.
// A site's page for a download (MT46, MT47). It opens as a new tab, which a browser puts in front; a page has no way
// to open one behind itself. With "site_window" it is a small window beside ModTrap instead. A page opened by another
// can reach the tab that opened it and send it elsewhere, so the tab or window is cut loose from ModTrap before the
// site's page loads, and ModTrap can then not close it either. Only where the owner chose so ("site_window_closes"),
// and only for the three sites ModTrap knows, is the tie kept: ModTrap then closes the site's page when the file is
// here or the waiting ends, which brings the owner back to ModTrap's tab, and asks before its own tab is sent
// anywhere while such a page is open.
const SITE_KNOWN = /(^|\.)(nexusmods\.com|github\.com|loverslab\.com)$/i;
// A new tab for an address, with no tie to ModTrap's tab: by a link pressed for the owner, never by window.open with
// "noopener" among its features, which Firefox answers with a window of its own instead of a tab (WHY§113).
function openTab(url) {
  const a = el("a", { href: url, target: "_blank", rel: "noopener noreferrer", hidden: "hidden" });
  document.body.append(a);
  a.click();
  a.remove();
}
function siteWindow() {
  const st = state.settings || {};
  try {
    const w = st.site_window
      ? window.open("", "modtrap-site", "popup=yes,width=1040,height=820,left=" + Math.max(0, window.screenX + window.outerWidth - 1080) + ",top=" + Math.max(0, window.screenY + 60))
      : window.open("", "_blank");
    if (w) { try { w.document.title = "Opening the mod's page…"; } catch (e) { /* a page of a site is in it: not ours to write to */ } }
    return w || null;
  } catch (e) { return null; }
}
function siteGuard(ev) { ev.preventDefault(); ev.returnValue = ""; }
function siteWindowsLeft() {
  const wins = state.siteWins || {};
  for (const mod of Object.keys(wins)) { let shut = true; try { shut = wins[mod].closed; } catch (e) { /* counted as shut */ } if (shut) delete wins[mod]; }
  if (!Object.keys(wins).length) window.removeEventListener("beforeunload", siteGuard);
}
function closeSiteWindow(mod) {
  const w = (state.siteWins || {})[mod];
  if (w) { try { w.close(); } catch (e) { /* gone already */ } delete state.siteWins[mod]; }
  siteWindowsLeft();
}
function openSite(url, mod, win) {
  if (win) {
    try {
      let host = "";
      try { host = new URL(url).hostname; } catch (e) { /* no tie for an address that does not read */ }
      const tied = !!(state.settings || {}).site_window_closes && SITE_KNOWN.test(host);
      if (!tied) win.opener = null;
      win.location.replace(url);
      if (tied) {
        for (const other of Object.keys(state.siteWins || {})) if (state.siteWins[other] === win) delete state.siteWins[other];   // the one window, now for this mod
        state.siteWins = Object.assign({}, state.siteWins, { [mod]: win });
        window.addEventListener("beforeunload", siteGuard);
      }
      return;
    } catch (e) { try { win.close(); } catch (e2) { /* gone */ } }
  }
  openTab(url);
}
// The update button (MT50): one press starts the mod's update in the Updater, which carries it through by itself and
// shows each stage on the Updater tool. Where the site gives the file only to the owner's browser, its page is opened
// for their press on its download button; `byBrowser`: the browser opened that page itself (Ctrl+click, a middle
// click), so ModTrap opens nothing.
async function getUpdate(mod, byBrowser) {
  const r = state.updates ? state.updates.rows.find((u) => u.mod === mod) : null;
  if (!state.changes) {                 // without the switch for changes nothing is installed: the page is all there is
    if (!byBrowser && r && (r.get || r.page)) openTab(r.get || r.page);
    toast("ModTrap updates a mod only when it is started with its switch for changes; the mod's page is opened for you.");
    return;
  }
  // The tab is opened at once, while the press still counts as the owner's; it is closed again if it is not needed.
  const win = byBrowser || (r && r.fetches) ? null : siteWindow();
  let got;
  try { got = await api("/api/updater/start", { mod }); } catch (e) { if (win) { try { win.close(); } catch (e2) { /* gone */ } } toast(e.message); return; }
  if (got.open && !byBrowser) {
    openSite(got.open, mod, win);
    // The browser puts a new tab in front. ModTrap's program takes it back to this tab (MT52; a setting, on Windows).
    if ((state.settings || {}).stay_on_tab && !(state.settings || {}).site_window) api("/api/updater/back", {}).catch(() => {});
  } else if (win) { try { win.close(); } catch (e) { /* gone */ } }
  if (got.open) toast("Its download page is opened in another tab. Without a Nexus key of a Premium account the download starts with your press on that page's download button; ModTrap does everything after it. See the Download box below.");
  showTab("updater");
  pollUpdater(true);
  state.upSig = "";
}
document.addEventListener("visibilitychange", () => { if (!document.hidden) { if (state.tab === "updates" && state.updates) loadUpdates(); pollUpdater(true); } });

// The Updater tool (MT50): each update a row of boxes, a stage each, as the Demaster's process is shown.
async function pollUpdater(now) {
  if (state.updaterBusy || state.status !== "ready") return;
  clearTimeout(state.updaterTimer);
  state.updaterBusy = true;
  try { state.updater = await api("/api/updater"); } catch (e) { /* asked again at the next turn */ }
  state.updaterBusy = false;
  const d = state.updater;
  if (!d) return;
  // A site's page ModTrap opened for a download is closed once its update no longer waits for it.
  for (const mod of Object.keys(state.siteWins || {})) if (!d.runs.some((r) => r.mod === mod && r.waits_page)) closeSiteWindow(mod);
  siteWindowsLeft();
  const ended = d.runs.filter((r) => r.ended).map((r) => r.id + r.state).join(",");
  if (state.updaterEnded !== undefined && ended !== state.updaterEnded) {       // an update ended: the lists it changed are read again
    state.upSig = "";
    if (state.tab === "updates") loadUpdates();
    if (state.tab === "downloads") loadDownloads();
  }
  state.updaterEnded = ended;
  renderUpdater();
  if (d.going || state.tab === "updater") state.updaterTimer = setTimeout(pollUpdater, d.going ? 800 : 4000);
}
function renderUpdater() {
  const d = state.updater || { runs: [] };
  const going = d.runs.find((r) => r.state === "going"), yours = d.runs.find((r) => r.state === "yours" && !r.handed), failed = d.runs.find((r) => r.state === "failed");
  for (const id of ["updater-dot", "updater-group-dot"]) {
    const dot = $(id);
    dot.hidden = !(going || yours);
    dot.className = "live-dot" + (yours && !going ? " yours" : "");
  }
  const text = JSON.stringify(d.runs);
  if (text === state.updaterText) return;
  state.updaterText = text;
  $("updater-summary").textContent = yours ? "Waits for you: “" + yours.mod + "”" : going ? "Now: “" + going.mod + "”" : failed && d.runs[0] === failed ? "Stopped: “" + failed.mod + "”" : "Updater tool";
  $("updater-clear").disabled = !d.runs.some((r) => !["going", "yours"].includes(r.state) || r.handed);
  if (!d.runs.length) { $("updater-runs").replaceChildren(el("div", { class: "card" }, el("p", { class: "dim", text: "No update has been started. On the Updater list, press the arrow beside a mod that has a newer version." }))); return; }
  const WORD = { going: ["going on", "warn"], yours: ["waits for you", ""], done: ["done", "good"], failed: ["stopped", "bad"], stopped: ["stopped by you", ""], reverted: ["taken out again", ""] };
  $("updater-runs").replaceChildren(...d.runs.map((r) => {
    const word = WORD[r.state] || WORD.going;
    const acts = [];
    const act = (label, title, run, cls) => { const b = el("button", { type: "button", text: label, title, class: cls || "" }); b.addEventListener("click", run); acts.push(b); };
    if (r.waits_page && r.open) act(r.needs_open ? "Open its download page" : "Open its download page again", "Opens the page where you press the site's download button", () => { openSite(r.open, r.mod, siteWindow()); }, r.needs_open ? "primary" : "");
    if (r.waits_page && /nexusmods\.com/.test(r.open || "") && state.updates && state.updates.premium !== true) act(state.updates.key ? "Your Nexus key…" : "Do it without this page: give your Nexus key…",
      "With the key of a Premium account ModTrap downloads the file itself: no page, no press", () => nexusKeyBox(async (premium) => {
        if (!premium) return;
        try { await api("/api/updater/stop", { run: r.id }); await api("/api/updater/start", { mod: r.mod }); } catch (e) { toast(e.message); }      // the same update, now fetched by ModTrap
        pollUpdater(true);
      }), "primary");
    if (["going", "yours"].includes(r.state) && !r.handed) act("Stop", "Stop this update; nothing of the modlist is changed before the add itself", async () => { try { await api("/api/updater/stop", { run: r.id }); } catch (e) { toast(e.message); } pollUpdater(true); });
    if (r.handed && r.staged) act("Go to Install mods", "The archive waits there, with the steps of an update", () => { if (!(state.staged || []).includes(r.staged)) state.staged = (state.staged || []).concat(r.staged); saveUi(); showTab("add"); pollAdd(true); }, "primary");
    if (r.state === "done" && r.job) act("Uninstall", "Puts the modlist back as it was before this update: the older version enabled again, the newer one taken out", async () => {
      if (!await confirmBox("Take “" + r.new + "” out again and enable “" + r.mod + "”, the older version, as before? The downloaded file stays where it is.")) return;
      try { await api("/api/updater/revert", { run: r.id }); toast("Put back as it was."); } catch (e) { toast(e.message); }
      pollUpdater(true);
    });
    return el("div", { class: "uprun card s-" + r.state },
      el("div", { class: "uprun-head" }, el("b", { text: "“" + r.mod + "”" + (r.version ? " → " + r.version : "") }),
        el("span", { class: "tag " + word[1] + (r.state === "yours" ? " t-yours" : ""), text: word[0] }),
        el("span", { class: "dim small", text: new Date(r.started * 1000).toLocaleTimeString() + (r.ended ? " · " + Math.max(1, Math.round(r.ended - r.started)) + " s" : "") }),
        el("span", { class: "spacer" }), ...acts),
      r.summary ? el("p", { class: r.state === "failed" ? "would-needs" : "", text: r.summary }) : null,
      el("div", { class: "flow" }, ...r.stages.map((s, i) => {
        const w = STAGE_WORD[s.state] || STAGE_WORD.waiting;
        return el("div", { class: "stage s-" + s.state },
          el("div", { class: "stage-head" }, el("span", { class: "n", text: String(i + 1) }), el("b", { text: s.title }),
            el("span", { class: "tag " + w[1] + (s.state === "yours" ? " t-yours" : ""), text: w[0] })),
          s.note ? el("p", { class: "stage-note", text: s.note }) : null,
          el("ul", { class: "tasks" }, ...s.tasks.map((t) => el("li", { class: "t-" + t.state },
            el("span", { class: "ico", "aria-hidden": "true", text: TASK_ICON[t.state] || "○" }),
            el("span", { text: t.text + (t.state === "going" ? " …" : "") }),
            t.note ? el("span", { class: "note", text: t.note }) : null))));
      })));
  }));
}

// The Nexus key, asked for where it is needed (MT52): with the key of a Premium account ModTrap fetches a file
// itself, with no page of Nexus's and no press there. The box says what the key is and where it is made, keeps it,
// and says at once which kind of account it is of.
async function nexusKeyBox(after) {
  if (!state.updates) { try { state.updates = await api("/api/updates"); state.updatesFor = state.loaded; } catch (e) { /* the box still serves */ } }
  const d = state.updates || {};
  const keyIn = el("input", { type: "password", autocomplete: "off", spellcheck: "false", placeholder: "paste your personal API key from Nexus here", size: "52" });
  const page = el("a", { target: "_blank", rel: "noopener noreferrer", text: "Open Nexus's page for API keys" });
  page.setAttribute("href", d.key_page || "");            // the address comes from ModTrap's program: the page holds no outside address
  const keep = el("button", { type: "button", class: "primary", text: "Keep the key" });
  const cancel = el("button", { type: "button", text: "Cancel" });
  const said = el("p", { class: "would-needs", hidden: "hidden" });
  const box = el("div", { class: "modal wide", role: "dialog", "aria-modal": "true" },
    el("p", {}, el("b", { text: "One press, with no page of Nexus's: your Nexus API key" })),
    el("p", { text: "Nexus gives a file to a program only through its key service, and only for a Premium account. With your account's key ModTrap downloads a newer file itself: no tab opens, and there is no download button to press." }),
    el("ol", { class: "small upsteps" },
      el("li", {}, "Signed in at Nexus Mods: ", page, "."),
      el("li", { text: "At the bottom of that page, “Personal API Key”: make one if there is none, and copy it." }),
      el("li", { text: "Paste it below and press “Keep the key”." })),
    el("p", {}, keyIn),
    el("p", { class: "dim small", text: "The key is not your password, and you can take it back at any time on that same page of Nexus's. ModTrap keeps it on this PC only, locked by Windows to your Windows account, sends it to Nexus's key service and nowhere else, and never writes it to the log or a session file. “Forget the key”, on the Updater list, removes it." }),
    said, el("div", { class: "actions" }, cancel, keep));
  const back = el("div", { class: "modal-back" }, box);
  const done = () => { document.removeEventListener("keydown", key, true); back.remove(); };
  const key = (ev) => { if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); done(); } };
  cancel.addEventListener("click", done);
  keep.addEventListener("click", async () => {
    keep.disabled = true;
    let got;
    try { got = await api("/api/updates/key", { key: keyIn.value }); } catch (e) { said.textContent = e.message; said.hidden = false; keep.disabled = false; return; }
    keyIn.value = "";
    done();
    state.upSig = "";
    loadUpdates();
    if (got.premium === true) {
      toast("The key is kept, and Nexus says the account is Premium: from now on ModTrap downloads a newer file itself, with no page and no press.");
      if (after) after(true);
    } else if (got.premium === false) {
      toast("The key is kept, but Nexus says the account is not Premium. Nexus lets a program download only for a Premium account, so for this account the press on Nexus's own download button stays.");
      if (after) after(false);
    } else toast("The key is kept, but Nexus could not be asked what kind of account it is of just now. Press a mod's update button to try.");
  });
  document.addEventListener("keydown", key, true);
  document.body.append(back);
  keyIn.focus();
}

// The update button of one mod's row: on the Updater list and on Installed mods.
function upGetButton(r) {
const d = state.updates || {};
  if (!r.get) return null;
  const sure = r.state === "update";
  const busy = (d.fetching || {})[r.mod];
  if (busy && busy.state === "going") return el("span", { class: "dim small", title: busy.text || "fetching", text: (busy.pct ? busy.pct + "%" : "…") });
  const waits = ((d.watch || {}).waiting || {})[r.mod];
  if (waits) {
    const stop = el("button", { type: "button", class: "upget unsure", text: "×", "aria-label": "Stop waiting for the download of " + r.mod,
      title: "ModTrap is waiting for the download you start on the mod's page (" + waits.minutes + " more minutes)" + (waits.saw ? ": " + waits.saw : "; nothing new has come into the watched folders yet") + ". Press to stop waiting." });
    stop.addEventListener("click", async (ev) => { ev.stopPropagation(); closeSiteWindow(r.mod); try { await api("/api/updates/wait", { mod: r.mod }); } catch (e) { toast(e.message); } state.upSig = ""; loadUpdates(); });
    const pct = /(\d+)%/.exec(waits.saw || ""), size = /\(([^()]+)\)/.exec(waits.saw || "");
    return el("span", {}, el("span", { class: "spinner small", "aria-hidden": "true" }), stop,
      el("div", { class: "small upsaw" + (waits.saw ? " upcoming" : " dim"), text: waits.saw ? "downloading" + (pct ? " " + pct[1] + "%" : size ? " · " + size[1] : "…")
        : r.host === "nexus" ? "press “Start download” on Nexus's page" : "press download on the site's page" }));
  }
  const known = r.state === "update" || r.state === "maybe";
  const title = (sure ? "Get the newer file" + (r.newest ? " (" + r.newest + ")" : "") : known ? "Unclear whether a newer file is out: look at the mod's files" : "This site cannot be asked for versions: look at the mod's page yourself") + ". "
      + (r.fetches ? "One press: ModTrap fetches it and updates the mod; the Updater tool shows each stage."
        : "One press starts the update. Where the file is not on this PC yet, its page" + (r.host === "nexus" ? " at Nexus" : "") + " opens for your press on its download button; ModTrap does the rest. Ctrl+click or a middle click opens that page in a tab behind this one.");
  if (r.fetches || !r.get) {
    const b = el("button", { type: "button", class: "upget" + (sure ? "" : " unsure"), text: known ? "↑" : "↗", "aria-label": "Get the newer file of " + r.mod, title });
    b.addEventListener("click", (ev) => { ev.stopPropagation(); getUpdate(r.mod); });
    return b;
  }
  // A real link (MT47): a plain press is ModTrap's own; with Ctrl, Shift or the middle button the browser itself
  // opens the page, behind this tab or in a window as the owner's browser does, and ModTrap only starts watching.
  const link = el("a", { class: "upget" + (sure ? "" : " unsure"), href: r.get, target: "_blank", rel: "noopener noreferrer", role: "button", text: known ? "↑" : "↗", "aria-label": "Get the newer file of " + r.mod, title });
  link.addEventListener("click", (ev) => {
    ev.stopPropagation();
    if (ev.ctrlKey || ev.metaKey || ev.shiftKey) { getUpdate(r.mod, true); return; }       // the browser opens it its own way
    ev.preventDefault();
    getUpdate(r.mod);
  });
  link.addEventListener("auxclick", (ev) => { if (ev.button === 1) { ev.stopPropagation(); getUpdate(r.mod, true); } });
  return link;
}

// Column titles that sort (MT55): a click on a title sorts the list by that column, a second click turns the order
// round; an arrow beside the title says which way, up for ascending, down for descending. By priority is how each
// list comes.
function sortHeads(table, keys, sort, onSort) {
  [...table.tHead.rows[0].cells].forEach((th, i) => {
    const key = keys[th.dataset.c !== undefined ? Number(th.dataset.c) : i];        // a column that was moved is still itself (MT62)
    if (!key) return;
    th.classList.add("sortable");
    th.tabIndex = 0;
    th.setAttribute("role", "button");
    const old = th.querySelector(".sortarrow");
    if (old) old.remove();
    const on = sort.key === key;
    th.setAttribute("aria-sort", on ? (sort.desc ? "descending" : "ascending") : "none");
    if (on) th.append(el("span", { class: "sortarrow", "aria-hidden": "true", text: sort.desc ? " ▼" : " ▲" }));
    if (th.dataset.sortBound) return;
    th.dataset.sortBound = "1";
    const go = () => onSort(key);
    th.addEventListener("click", go);
    th.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); go(); } });
  });
}
function nextSort(sort, key) { return { key, desc: sort.key === key ? !sort.desc : false }; }
const naturally = (a, b) => String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });

// The Mods tab's order, as its select names it and as its column titles set it.
const MOD_ORDERS = { "mo2": ["priority", false], "rev": ["priority", true], "deps": ["deps", true], "deps-asc": ["deps", false],
  "name": ["name", false], "name-desc": ["name", true], "plugins": ["plugins", false], "plugins-desc": ["plugins", true] };
function modSort() { const o = MOD_ORDERS[$("mods-order").value] || MOD_ORDERS.mo2; return { key: o[0], desc: o[1] }; }
function setModSort(key) {
  if (state.placing) return;                     // while a place is chosen the list stays in MO2's order
  const next = nextSort(modSort(), key);
  $("mods-order").value = Object.keys(MOD_ORDERS).find((k) => MOD_ORDERS[k][0] === next.key && MOD_ORDERS[k][1] === next.desc) || "mo2";
  layoutMods();
  saveUi();
}

// A separator of MO2's list, added below a mod or another separator (MT55).
async function addSeparator(below) {
  const name = await modalBox("Add a separator below “" + below.replace(/_separator$/i, "") + "”\n\nIts name, as MO2 will show it. ModTrap makes the separator in MO2's own way, so MO2 has it too; MO2 must be closed.", { input: "", yes: "OK", no: "Cancel" });
  if (name === null || !name.trim()) return;
  try {
    const got = await api("/api/separator/add", { name: name.trim(), below });
    toast("The separator “" + got.name.replace(/_separator$/i, "") + "” is added at priority " + got.priority + ". ModTrap is reading the modlist again.");
  } catch (e) { toast(e.message); }
  state.gen = (state.gen || 0) + 1;
  tick();
}

// The Downloads tab (MT50): the mod files ModTrap fetched or took over, each with where it came from.
async function loadDownloads() {
  if (state.status !== "ready") return;
  let d;
  try { d = await api("/api/downloads"); } catch (e) { toast(e.message); return; }
  state.downloads = d;
  const folderIn = el("input", { type: "text", spellcheck: "false", placeholder: "another folder's full path, such as C:\\ModTrap downloads", size: "56" });
  const set = el("button", { type: "button", text: "Keep downloads there" });
  set.addEventListener("click", async () => { try { await api("/api/downloads/folder", { path: folderIn.value }); } catch (e) { toast(e.message); } loadDownloads(); });
  const own = el("button", { type: "button", text: "Back to ModTrap's own folder", disabled: d.own });
  own.addEventListener("click", async () => { try { await api("/api/downloads/folder", { path: "" }); } catch (e) { toast(e.message); } loadDownloads(); });
  const total = d.rows.filter((r) => r.there && r.where === "ModTrap's downloads folder").reduce((n, r) => n + r.size, 0);
  $("downloads-head").replaceChildren(el("div", { class: "card" },
    el("h3", { text: "Downloads" }),
    el("p", { class: "dim", text: "The mod files ModTrap fetched for an update, or took over from your browser's Downloads folder, each with where it came from. Before anything is downloaded, ModTrap looks here, in MO2's own downloads folder and in your browser's: a file that is already on this PC is not downloaded again. Nothing here is deleted by ModTrap." }),
    el("p", {}, "ModTrap's downloads folder: ", el("span", { class: "mono", text: d.folder }), el("span", { class: "dim", text: "  ·  " + plural(d.rows.length, "file") + ", " + (total / (1024 * 1024)).toFixed(1) + " MB kept here" })),
    el("p", {}, folderIn, " ", set, " ", own),
    el("p", { class: "dim small", text: "Naming another folder moves nothing: the files downloaded so far stay in the folder named before, with its list." })));
  if (!d.rows.length) { $("downloads-list").replaceChildren(el("div", { class: "card" }, el("p", { class: "dim", text: "Nothing has been downloaded yet. A mod's update, started on the Updater list, brings its file here." }))); return; }
  const HOW_HOST = { nexus: "Nexus", github: "GitHub", loverslab: "LoversLab", url: "web address" };
  const table = el("table", { class: "grid", id: "downloads-table" },
    el("thead", {}, el("tr", {}, ...["File", "For the mod", "From", "Version", "Size", "How it came here", "When", "Where it lies"].map((h) => el("th", { text: h })))),
    el("tbody", {}, ...d.rows.map((r) => el("tr", { class: r.there ? "" : "dimrow" },
      el("td", { class: "mono small", text: r.file }),
      el("td", {}, r.for_mod ? modLink(r.for_mod) : el("span", { class: "dim", text: "not said" }), r.installed_as ? el("div", { class: "dim small" }, "installed as ", modLink(r.installed_as)) : null,
        r.this_modlist ? null : el("div", { class: "dim small", text: "of another modlist" })),
      el("td", {}, (HOW_HOST[r.host] || "not known") + (r.mod_id ? " " + r.mod_id : ""), r.file_id ? el("div", { class: "dim small", text: "file " + r.file_id }) : null,
        r.page || r.url ? el("div", {}, el("a", { href: r.page || r.url, target: "_blank", rel: "noopener noreferrer", text: "its page" })) : null),
      el("td", { text: r.version || "" }),
      el("td", { class: "num", text: (r.size / (1024 * 1024)).toFixed(1) + " MB" }),
      el("td", { class: "small", text: r.how }),
      el("td", { class: "small", text: r.when ? new Date(r.when * 1000).toLocaleString() : "" }),
      el("td", {}, r.where, r.there ? null : el("span", { class: "tag warn", text: "no longer there" }))))));
  $("downloads-list").replaceChildren(el("div", { class: "card" }, table));
}

// "Manual update" (MT46): a box with a drop zone and a button, for a file the owner downloaded themselves. The file
// goes to Install mods as the mod's newer version.
function manualUpdate(mod) {
  const pick = el("input", { type: "file", accept: ".zip,.7z,.rar", hidden: "hidden" });
  const add = el("button", { type: "button", class: "primary", text: "Add file…" });
  const cancel = el("button", { type: "button", text: "Cancel" });
  const zone = el("div", { class: "upzone manual" },
    el("div", { class: "upzone-title", text: "Drop the newer version's archive here" }),
    el("div", { class: "upzone-buttons" }, add, pick),
    el("div", { class: "dim small", text: "A .zip, .7z or .rar file you downloaded yourself, from any site." }));
  const box = el("div", { class: "modal wide", role: "dialog", "aria-modal": "true" },
    el("p", {}, el("b", { text: "Manual update of “" + mod + "”" })),
    el("p", { class: "dim", text: "The Updater takes the file as this mod's newer version: it goes right after “" + mod + "” in MO2's list, and “" + mod + "” is disabled, not deleted. The Updater tool shows each stage." }),
    zone, el("div", { class: "actions" }, cancel));
  const back = el("div", { class: "modal-back" }, box);
  const done = () => { document.removeEventListener("keydown", key, true); back.remove(); };
  const key = (ev) => { if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); done(); } };
  const take = async (file) => {
    if (!file) return;
    if (!/\.(zip|7z|rar)$/i.test(file.name)) { toast("“" + file.name + "” is not an archive ModTrap unpacks: a .zip, .7z or .rar file."); return; }
    done();
    try {
      toast("Taking in “" + file.name + "” as a newer version of “" + mod + "”…");
      const rec = await sendArchive(file, mod);
      await api("/api/updater/start", { mod, staged: rec.id });
      showTab("updater");
      pollUpdater(true);
    } catch (e) { toast(e.message); }
  };
  add.addEventListener("click", () => pick.click());
  pick.addEventListener("change", () => take(pick.files && pick.files[0]));
  cancel.addEventListener("click", done);
  back.addEventListener("mousedown", (ev) => { if (ev.target === back) done(); });
  for (const name of ["dragenter", "dragover"]) back.addEventListener(name, (ev) => { ev.preventDefault(); ev.stopPropagation(); zone.classList.add("over"); });
  back.addEventListener("dragleave", (ev) => { if (!back.contains(ev.relatedTarget)) zone.classList.remove("over"); });
  back.addEventListener("drop", (ev) => { ev.preventDefault(); ev.stopPropagation(); zone.classList.remove("over"); take(ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0]); });
  document.addEventListener("keydown", key, true);
  document.body.append(back);
  add.focus();
}
async function setFavourite(mod, on) {
  try { await api("/api/updates/favourite", { mod, on }); toast(on ? "“" + mod + "” is marked as a favourite." : "“" + mod + "” is no longer a favourite."); } catch (e) { toast(e.message); }
  state.upSig = "";
  await loadUpdates();
}
function fetchingEnded(d) {
  for (const [mod, f] of Object.entries(d.fetching || {})) {
    if (f.state === "going") continue;
    api("/api/updates/seen", { mod }).catch(() => {});
  }
}
async function loadUpdates() {
  if (state.updatesBusy || state.status !== "ready") return;
  state.updatesBusy = true;
  try { state.updates = await api("/api/updates"); state.updatesFor = state.loaded; } catch (e) { state.updatesError = e.message; }
  state.updatesBusy = false;
  renderUpdates();
  const d = state.updates;
  clearTimeout(state.updatesTimer);
  if (d) fetchingEnded(d);
  if (d) for (const mod of Object.keys(state.siteWins || {})) if (!((d.watch || {}).waiting || {})[mod] && !(d.fetching || {})[mod]) closeSiteWindow(mod);
  siteWindowsLeft();
  if (d && state.upScanAsked && d.scan.state !== "going") {              // the scan the owner asked for has ended: say what came of it
    state.upScanAsked = false;
    const l = d.last;
    if (d.scan.error) toast(d.scan.error);
    else if (l && l.nexus) {
      const why = l.nexus.why_stopped || l.github.why_stopped;
      const about = (l.nexus.way === "public" ? l.nexus.month_list : l.nexus.asked) + l.github.asked;
      toast("Scan done: asked about " + plural(about, "mod") + ", " + plural(d.counts.update || 0, "update") + " out"
        + (l.nexus.left ? ", " + l.nexus.left.toLocaleString("en-GB") + " mods left for the next scan" : "") + "." + (why ? " " + why.charAt(0).toUpperCase() + why.slice(1) + "." : ""));
    }
  }
  if (d && (d.scan.state === "going" || d.list.reading || Object.values(d.fetching || {}).some((f) => f.state === "going")
    || Object.keys((d.watch || {}).waiting || {}).length)) state.updatesTimer = setTimeout(loadUpdates, 2000);
}
function upFilter(key, value) { state.upFilter = Object.assign({ state: "", origin: "", on: false, fav: false, text: "" }, state.upFilter, { [key]: value }); renderUpdates(true); }
function renderUpdates(listOnly) {
  const head = $("updates-head"), box = $("updates-list");
  if (!head || !box) return;
  const d = state.updates;
  const num = (n) => (n || 0).toLocaleString("en-GB");
  const badge = $("updates-count");
  if (badge) { badge.hidden = !(d && d.counts.update); badge.textContent = d ? d.counts.update : ""; }
  if (!d) { head.replaceChildren(el("div", { class: "card" }, el("p", { class: "dim", text: state.updatesError || "Reading where the mods came from…" }))); box.replaceChildren(); return; }
  const f = Object.assign({ state: "", origin: "", on: false, fav: false, text: "" }, state.upFilter);
  // What the owner is typing in the head is not wiped by a look at how the scan is getting on.
  const typing = head.contains(document.activeElement) && document.activeElement.tagName === "INPUT" && document.activeElement.value;
  if (!listOnly && !typing) {
    const going = d.scan.state === "going";
    const scan = el("button", { type: "button", class: "primary", text: going ? "Scanning…" : "Scan for updates", disabled: going });
    scan.addEventListener("click", async () => {
      const nexus = (d.hosts || {}).nexus || 0, github = (d.hosts || {}).github || 0;
      if (!nexus && !github) {
        // Nothing can be asked: said at once (WHY§107). Nexus itself needs no key (MT44).
        toast("None of the mods has a source that can be asked: give the Wabbajack file, or add source links (right-click a mod).");
        return;
      }
      state.upScanAsked = true;
      try { await api("/api/updates/scan", {}); toast("Scanning for updates: asking Nexus about " + num(nexus) + " mods" + (github ? " and GitHub about " + num(github) : "") + ". On a large list the first scan takes a few minutes."); } catch (e) { toast(e.message); }
      loadUpdates();
    });
    const stop = going ? el("button", { type: "button", text: "Stop the scan" }) : null;
    if (stop) stop.addEventListener("click", async () => { try { await api("/api/updates/stop", {}); } catch (e) { toast(e.message); } });
    const kids = [el("div", { class: "card-head" }, el("h2", { text: "Updates" }), el("span", {}, stop, " ", scan)),
      el("p", { class: "dim", text: "Where each mod came from, read from MO2's own records on this PC, and whether a newer file of it is out, asked of Nexus and GitHub. A scan only asks and reads. A newer file is fetched only when you press a mod's update button, and nothing in the modlist changes before Install mods has shown you its plan." })];
    if (going) kids.push(el("p", { class: "would-needs" }, el("span", { class: "spinner small", "aria-hidden": "true" }), " ModTrap is " + (d.scan.text || "scanning") + "…"));
    if (d.scan.error) kids.push(el("p", { class: "would-needs", text: d.scan.error }));
    const last = d.last;
    if (last && last.nexus) {
      const when = new Date(last.when * 1000).toLocaleString("en-GB");
      const nexusLine = !last.nexus.asked && !last.nexus.month_list && last.nexus.left ? "Nexus was not asked (" + num(last.nexus.left) + " mods wait)"
        : last.nexus.way === "public" ? "Nexus was asked, without a key, when " + num(last.nexus.month_list) + " mods last had a new file, and for the files of " + num(last.nexus.asked) + (last.nexus.left ? "; " + num(last.nexus.left) + " are left for the next scan" : "")
        : "Nexus was asked about " + plural(last.nexus.asked, "mod") + (last.nexus.left ? ", " + num(last.nexus.left) + " are left for the next scan" : "");
      kids.push(el("p", { text: "Last scan, " + when + ": " + nexusLine
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
    kids.push(el("h3", { text: "Your Nexus key (optional)" }),
      el("p", { class: "dim small", text: "Not needed to scan for updates: Nexus answers that without a key. A key is for one thing only: with the key of a Premium account, a mod's update button fetches the newer file itself; without one, or with a free account's, it opens the file's page and you press download there. ModTrap keeps the key on this PC, protected by Windows for your Windows account. It is sent to Nexus only, never shown again, and never written to the log or to a session file." }),
      (() => {
        const a = el("a", { target: "_blank", rel: "noopener noreferrer", text: "Open Nexus's page for API keys" });
        a.setAttribute("href", d.key_page || "");
        return el("ol", { class: "small upsteps" },
          el("li", {}, "Sign in at Nexus Mods in your browser, then: ", a, ". (Or by hand: your picture at the top right, Account settings, API Keys.)"),
          el("li", { text: "Go to the bottom of that page, to “Personal API Key”. If there is none yet, press the button there to make one." }),
          el("li", { text: "Copy the long line of letters and digits, paste it into the field below, and press “Keep the key”." }));
      })(),
      el("p", {}, el("span", { class: "tag " + (d.key ? "good" : ""), text: d.key ? "a key is kept" : "no key kept" }), " ", keyIn, " ", keep, " ", forget));
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
    // The folders ModTrap watches for a download the owner starts in the browser (MT42).
    const w = d.watch || { folder: "", there: false, waiting: {} };
    const folderIn = el("input", { type: "text", spellcheck: "false", placeholder: "another folder's full path, if your browser saves elsewhere", size: "60" });
    const setFolder = el("button", { type: "button", text: "Watch this folder" });
    setFolder.addEventListener("click", async () => { try { await api("/api/updates/folder", { path: folderIn.value }); folderIn.value = ""; } catch (e) { toast(e.message); } loadUpdates(); });
    const usual = el("button", { type: "button", text: "Back to Windows' own Downloads folder" });
    usual.addEventListener("click", async () => { try { await api("/api/updates/folder", { path: "" }); } catch (e) { toast(e.message); } loadUpdates(); });
    const waitingFor = Object.keys(w.waiting || {});
    kids.push(el("h3", { text: "Downloads ModTrap watches" }),
      el("p", { class: "dim small", text: "Where ModTrap cannot fetch a file itself, the button opens the mod's page and you press download there, in the browser where you are signed in. ModTrap then watches two folders for the file, for 45 minutes, and takes it to Install mods as the mod's newer version once it is whole: MO2's own downloads folder, and the folder your browser saves to. It reads the file where it lies; it moves and deletes nothing." }),
      el("p", {}, "Your browser's folder: ", el("span", { class: "mono", text: w.folder }), w.there ? null : el("span", { class: "tag warn", text: "not found" })),
      el("p", {}, folderIn, " ", setFolder, " ", usual),
      waitingFor.length ? el("p", { class: "would-needs" }, el("span", { class: "spinner small", "aria-hidden": "true" }), " Waiting for the download of: " + waitingFor.join(", ") + ". "
        + ((w.waiting[waitingFor[0]] || {}).saw ? "Seen: " + w.waiting[waitingFor[0]].saw + "." : "Nothing new has come into the watched folders yet: the download starts with your press on the site's own download button.")) : null);
    // The two parts that are set up once fold away once they are, so that the list is near the top (WHY§104).
    state.upOpen = state.upOpen || {};
    const parts = [];
    let cur = null;
    for (const k of kids) {
      if (!k) continue;
      if (k.tagName === "H3") {
        const title = k.textContent, isKey = /key/i.test(title);
        const isWatch = /watches/i.test(title);
        const hint = isKey ? (d.key ? "a key is kept" + (d.premium === true ? ", of a Premium account: ModTrap fetches files itself" : d.premium === false ? ", not of a Premium account: downloads go through Nexus's page" : "") : "none kept; scanning needs none")
          : isWatch ? (waitingFor.length ? "waiting for " + plural(waitingFor.length, "download") : w.there ? "ready" : "your browser's folder was not found")
          : (have.length ? have.length + " kind" + (have.length === 1 ? "" : "s") + " of record given" : "nothing given yet");
        cur = el("details", { class: "upfold" }, el("summary", {}, el("b", { text: title }), el("span", { class: "dim", text: " · " + hint })));
        const wanted = state.upOpen[title] !== undefined ? state.upOpen[title] : isWatch ? !w.there : isKey ? false : !have.length || !!state.updatesTaking || d.list.reading || !!d.list.error;
        if (wanted) cur.setAttribute("open", "");
        const mine = cur;
        cur.addEventListener("toggle", () => { state.upOpen[title] = mine.open; });
        parts.push(cur);
      } else if (cur) cur.append(k); else parts.push(k);
    }
    head.replaceChildren(el("div", { class: "card" }, ...parts));
  }
  // The list, as the modlist itself is laid out (WHY§104): lowest priority first, each separator heading its mods.
  const sig = JSON.stringify([d.rows.map((r) => r.state.charAt(0) + (r.newest || "") + (r.given ? "g" : "") + (r.fav ? "f" : "") + r.host.charAt(0)).join(""), d.origins, d.given, d.list.named, f, state.upSort || "", state.loaded, [...(state.upCollapsed || [])],
    Object.entries((d.watch || {}).waiting || {}).map(([k, v]) => k + (v.saw || "")), Object.entries(d.fetching || {}).map(([k, v]) => k + v.state + (v.pct || ""))]);
  const going = d.scan.state === "going";
  if (state.upSig === sig && box.firstChild) return;
  if (going && box.firstChild && state.upDrawn && Date.now() - state.upDrawn < 10000 && state.upF === JSON.stringify([f, state.upSort || ""]) + [...(state.upCollapsed || [])].join("|")) return;
  state.upSig = sig; state.upDrawn = Date.now(); state.upF = JSON.stringify([f, state.upSort || ""]) + [...(state.upCollapsed || [])].join("|");
  state.upCollapsed = state.upCollapsed || new Set();
  const pick = (key, value, label, n) => {
    const b = el("button", { type: "button", class: "chip link" + (f[key] === value ? " on" : ""), text: label + (n === undefined ? "" : " " + num(n)) });
    b.addEventListener("click", () => upFilter(key, value));
    return b;
  };
  const search = el("input", { type: "search", placeholder: "Search by mod or note, or *138 for priority 138", value: f.text, size: "42",
    title: "Type a part of a mod's name or of your note on it. A star and a number, like *138, goes to the mod with that priority; Enter goes there again." });
  search.addEventListener("keydown", (ev) => { if (ev.key === "Enter") { state.upJumped = ""; renderUpdates(true); } });
  search.addEventListener("input", () => { state.upFilter = Object.assign({}, f, { text: search.value }); clearTimeout(state.upTimer); state.upTimer = setTimeout(() => { renderUpdates(true); const again = document.querySelector("#updates-list input[type=search]"); if (again) { again.focus(); again.setSelectionRange(again.value.length, again.value.length); } }, 300); });
  const onlyOn = el("input", { type: "checkbox", id: "up-on" });
  onlyOn.checked = !!f.on;
  onlyOn.addEventListener("change", () => upFilter("on", onlyOn.checked));
  const foldAll = el("button", { type: "button", text: "Fold all" }), unfoldAll = el("button", { type: "button", text: "Unfold all" });
  const known = d.list.named && d.list.counts;
  const favChip = el("button", { type: "button", class: "chip link" + (f.fav ? " on" : ""), text: "★ Favourites " + num(d.counts.fav || 0), title: "Show only the mods you marked as favourites (right-click a mod to mark it)" });
  favChip.addEventListener("click", () => upFilter("fav", !f.fav));
  const instChip = el("button", { type: "button", class: "chip link" + (f.origin === "modtrap" ? " on" : ""), text: "Installed " + num(d.origins.modtrap || 0), title: "Show only the mods installed through ModTrap" });
  instChip.addEventListener("click", () => upFilter("origin", f.origin === "modtrap" ? "" : "modtrap"));
  const bar = [el("div", { class: "chips" }, el("span", { class: "dim", text: "Filter:" }), pick("state", "", "All", d.rows.length),
    ...["update", "maybe", "current", "replaced", "not asked", "none", "gone"].filter((k) => d.counts[k]).map((k) => pick("state", k, UP_STATE[k][0], d.counts[k])), favChip, instChip),
    el("div", { class: "chips" }, el("span", { class: "dim", text: "Mods:" }), pick("origin", "", "All"),
      ...(known ? [pick("origin", "list", "The list's own", d.origins.list), pick("origin", "added", "Added afterwards", d.origins.added)] : []),
      pick("origin", "modtrap", "Installed by ModTrap", d.origins.modtrap),
      known ? null : el("span", { class: "dim small", text: "Give the modlist's Wabbajack file above to tell the list's own mods from the ones added afterwards." })),
    el("div", { class: "chips" }, search, el("label", { for: "up-on" }, onlyOn, " enabled mods only"), foldAll, unfoldAll)];
  const star = starNumber(f.text || "");                   // *138: the mod with priority 138, the list not narrowed (MT60)
  const text = star === null ? (f.text || "").trim().toLowerCase() : "";
  const filtering = !!(f.state || f.origin || f.on || f.fav || text);
  const fits = (r) => (!f.state || r.state === f.state) && (!f.origin || r.origin === f.origin) && (!f.on || r.enabled) && (!f.fav || r.fav)
    && (!text || r.mod.toLowerCase().includes(text) || (r.comments || "").toLowerCase().includes(text) || (r.notes || "").toLowerCase().includes(text));
  const byName = new Map(d.rows.map((r) => [r.mod, r]));
  // The groups, from the modlist as the Mods tab has it: the same order, the same separators.
  let groups = [{ sep: null, rows: [] }];
  for (const m of [...(state.mods || [])].reverse()) {
    if (m.kind === "separator") groups.push({ sep: m, rows: [] });
    else if (byName.has(m.name)) groups[groups.length - 1].rows.push(byName.get(m.name));
  }
  // Sorted by a column's title (MT55): by priority the groups stay, turned round for descending; by any other
  // column the mods are one list, without the separators.
  const sort = state.upSort || { key: "priority", desc: false };
  if (sort.key !== "priority") {
    const rank = { update: 0, maybe: 1, replaced: 2, current: 3, "not asked": 4, none: 5, gone: 6 };
    const by = { mod: (a, b) => naturally(a.mod, b.mod), from: (a, b) => naturally((a.host || "~") + " " + String(a.id || ""), (b.host || "~") + " " + String(b.id || "")),
      version: (a, b) => naturally(a.version || "", b.version || ""), update: (a, b) => rank[a.state] - rank[b.state] || naturally(a.newest || "", b.newest || "") }[sort.key];
    const all = groups.flatMap((g) => g.rows);
    all.sort((a, b) => (sort.desc ? -by(a, b) : by(a, b)) || a.priority - b.priority);
    groups = [{ sep: null, rows: all }];
  } else if (sort.desc) groups = groups.reverse().map((g) => ({ sep: g.sep, rows: [...g.rows].reverse() }));
  const link = (r) => {
    if (!r.page) return null;
    const a = el("a", { target: "_blank", rel: "noopener noreferrer", text: "its page" });
    a.setAttribute("href", r.page);
    return a;
  };
  const getButton = upGetButton;
  const COLS = 8;
  const body = el("tbody", {});
  let shown = 0;
  const seps = [];
  // What the search found glows (MT60): the rows found by words, when they are not too many; and the one row a
  // star and a number names, whose group is unfolded for it.
  const glow = !!text && d.rows.filter(fits).length <= FOUND_MAX;
  if (Number.isFinite(star)) { const g = groups.find((x) => x.sep && x.rows.some((r) => r.priority === star)); if (g) state.upCollapsed.delete(g.sep.name); }
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
      body.append(el("tr", { class: (r.enabled ? "" : "off") + (r.priority === star ? " found jump" : glow ? " found" : ""), "data-mod": r.mod, title: "Right-click for more: add a source link, get the newer file, ask about this mod now" },
        el("td", { class: "c-num", text: r.priority < 0 ? "" : r.priority }),
        el("td", { class: "modname" }, r.fav ? el("span", { class: "upfav", title: "A favourite of yours", text: "★ " }) : null, modLink(r.mod), r.enabled ? null : el("span", { class: "tag", text: "disabled" }), r.origin ? el("div", { class: "dim small", text: UP_ORIGIN[r.origin] }) : null),
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
  sortHeads(table, ["priority", "mod", "from", "version", null, "update", null, null], sort, (key) => { state.upSort = nextSort(sort, key); renderUpdates(true); });
  colSetup(table);                                          // its kept widths and order, before it is shown
  const how = sort.key === "priority" ? (sort.desc ? "highest priority first, under their separators" : "in the modlist's own order: lowest priority first, under their separators")
    : "sorted by " + { mod: "name", from: "where they come from", version: "installed version", update: "update state" }[sort.key] + (sort.desc ? ", descending" : ", ascending") + "; click “Priority” for the modlist's own order";
  box.replaceChildren(el("div", { class: "card" }, ...bar,
    el("p", { class: "dim small", text: num(shown) + " of " + num(d.rows.length) + " mods shown, " + how + "." }),
    star !== null ? el("p", { class: "dim small", text: !Number.isFinite(star) ? "A star and a number, like *138, goes to the mod with that priority."
      : body.querySelector("tr.jump") ? "Priority " + star + ": “" + body.querySelector("tr.jump").dataset.mod + "”."
      : "No mod shown here has priority " + star + (d.rows.some((r) => r.priority === star) ? ": the filters hide it." : " (a separator, or a mod without a source to ask).") }) : null,
    shown || seps.length ? table : el("p", { class: "dim", text: "No mod matches." })));
  const went = body.querySelector("tr.jump");
  if (!went) state.upJumped = "";
  else if (state.upJumped !== "*" + star) { state.upJumped = "*" + star; went.scrollIntoView({ block: "center" }); }
}

function renderState(s) {
  state.session = s.session;
  renderSessions(s);
  $("version").textContent = s.version ? "version " + s.version + (s.version_differs ? " · files differ" : "") : "";
  state.version = s.version || "";
  $("version").title = "Press to update ModTrap from a release file. " + (s.version_differs ? "The files in ModTrap's folder are not exactly those of this version: an update unpacked over an older folder, a copy cut short, or files changed by hand. Best unpack an update into an empty folder." : "");
  if (document.activeElement !== $("folder") && s.folder && (!$("folder").value || s.status === "ready")) $("folder").value = s.folder;
  const ready = s.status === "ready";
  $("summary").hidden = !ready;
  $("tabs").hidden = !ready;
  $("groups").hidden = !ready;
  $("steps").hidden = !ready;
  $("rescan").hidden = !ready;
  $("scan-list").hidden = !ready;
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
  const sc = s.scan || { found: 0, bad: 0, going: false };
  $("health-count").textContent = s.issue_count + sc.found;
  $("health-count").classList.toggle("bad", s.issue_count + sc.bad > 0);
  const chip = $("s-scan");
  chip.hidden = !sc.found && !sc.going;
  chip.textContent = sc.going ? "Scanning the modlist…" : plural(sc.found, "finding") + " of the scan";
  chip.className = "chip link " + (sc.going ? "" : sc.bad ? "bad" : "warn");
  $("scan-list").disabled = sc.going;
  if (state.listScan && state.scanGoing && !sc.going) listScan(false);          // it has ended: its findings are fetched
  state.scanGoing = sc.going;
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

// A list that shows its first rows and the rest on a press (MT65). What was opened stays open when the list is
// drawn anew, by its key.
const moreOpen = new Set();
function moreList(rows, first, beyond, key) {
  const ul = el("ul", { class: "small morelist" });
  const all = () => { ul.replaceChildren(...rows, ...(beyond ? [el("li", { class: "dim", text: "… and " + beyond.toLocaleString("en-GB") + " more that are not listed here" })] : [])); };
  if (rows.length <= first && !beyond || moreOpen.has(key)) { all(); return ul; }
  const b = el("button", { type: "button", class: "linkish morebtn", text: "and " + (rows.length - first + (beyond || 0)).toLocaleString("en-GB") + " more", title: "Show the whole list" });
  b.addEventListener("click", () => { moreOpen.add(key); all(); });
  ul.replaceChildren(...rows.slice(0, first), el("li", { class: "dim" }, b));
  return ul;
}
// What a scan or an evaluation found (MT65, DESIGN§25): each finding with how grave it is, why it matters, and what
// it is about. `onMod`, where given, makes the mods a finding names into links.
const LEVEL_WORD = { bad: ["likely a fault", "bad"], warn: ["worth a look", "warn"], info: ["note", ""], good: ["fine", "good"] };
function findingList(findings, key, onMod) {
  return el("div", { class: "findings" }, ...findings.map((f, i) => {
    const mods = onMod && (f.mods || []).length ? el("p", { class: "small f-mods" }, "Show: ", ...f.mods.flatMap((n, j) => {
      const b = el("button", { type: "button", class: "linkish", text: n }); b.addEventListener("click", () => onMod(n)); return j ? [", ", b] : [b]; })) : null;
    return el("div", { class: "finding f-" + f.level }, el("p", { class: "f-head" }, el("span", { class: "tag " + LEVEL_WORD[f.level][1], text: LEVEL_WORD[f.level][0] }), el("b", { text: f.title })),
      el("p", { class: "f-text", text: f.text }), (f.items || []).length ? moreList(f.items.map((t) => el("li", { text: t })), 6, f.more, key + ":" + f.key + ":" + i) : null, mods);
  }));
}
// A box of ModTrap's own for something to read: a title, what there is to read, and its buttons.
function sheetBox(title, nodes, actions) {
  const close = () => { document.removeEventListener("keydown", key, true); back.remove(); };
  const acts = (actions || []).concat([["Close", null, "primary"]]).map(([label, run, cls]) => { const b = el("button", { type: "button", text: label, class: cls || "" }); b.addEventListener("click", () => { close(); if (run) run(); }); return b; });
  const body = el("div", { class: "sheet-body" }, ...nodes);
  const box = el("div", { class: "modal dropbox sheet", role: "dialog", "aria-modal": "true" }, el("div", { class: "uprun-head" }, el("b", { text: title })), body, el("div", { class: "actions" }, ...acts));
  const back = el("div", { class: "modal-back" }, box);
  const key = (ev) => { if (ev.key === "Escape" && back === [...document.querySelectorAll(".modal-back")].pop()) { ev.preventDefault(); ev.stopPropagation(); close(); } };
  back.addEventListener("mousedown", (ev) => { if (ev.target === back) close(); });
  document.addEventListener("keydown", key, true);
  document.body.append(back);
  acts[acts.length - 1].focus();
  return { body, close };
}
// One mod weighed at the place it has (MT65): asked of the server, which reads the mod's files and the files it shares.
async function evaluateMod(name) {
  const sheet = sheetBox("“" + name + "” at its place", [el("p", { class: "dim" }, el("span", { class: "spinner small" }), " Looking at its own files and at every file it shares with another mod…")],
    [["Show it in the list", () => showInList(name)]]);
  try { sheet.body.replaceChildren(...evalNodes(await api("/api/mod/evaluate", { mod: name }), "eval:" + name)); }
  catch (e) { sheet.body.replaceChildren(el("p", { class: "would-needs", text: e.message })); }
}
function evalNodes(d, key) {
  const cls = { problem: "bad", look: "warn", clean: "good" }[d.verdict];
  return [el("p", { class: "eval-sum" }, el("span", { class: "tag " + cls, text: { problem: "needs your attention", look: "worth a look", clean: "clean" }[d.verdict] }), " " + d.summary),
    d.cut ? el("p", { class: "small would-needs", text: "The look was cut short, so that it does not hold you up: on a mod this large there may be more." }) : null,
    d.findings.length ? findingList(d.findings, key, null) : null,
    el("p", { class: "dim small", text: "ModTrap compares files byte for byte and reads the first bytes that say what format a file is in. What two plugins change inside the same record it does not read: the mod's web shows which records, xEdit what is in them." })].filter(Boolean);
}

// The scan of the whole modlist (MT65): doubles are looked for when the modlist opens; the header's button lists every
// enabled mod's files once, for mods that do nothing where they stand and for the older game's formats.
async function listScan(start) {
  try { state.listScan = await api(start ? "/api/listscan/start" : "/api/listscan", start ? {} : undefined); }
  catch (e) { toast(e.message); return; }
  state.listScanFor = state.loaded;
  renderHealth(state.last || {});
  if (state.listScan.state === "going") { clearTimeout(state.listScanTimer); state.listScanTimer = setTimeout(() => listScan(false), 700); }
}
function scanCard() {
  const d = state.listScan;
  const go = el("button", { type: "button", class: d && d.deep ? "" : "primary", text: d && d.deep ? "Scan again" : "Scan the modlist", disabled: !!(d && d.state === "going"),
    title: "Lists every enabled mod's files once and compares them: mods that do nothing where they stand, mods that are mostly inside another, archives and script extender plugins that do not fit this game. It only reads; on a large modlist it takes a while." });
  go.addEventListener("click", () => listScan(true));
  const card = el("div", { class: "card" }, el("div", { class: "card-head" }, el("h2", { text: "Doubles, and mods that do nothing" }), go));
  if (!d) { card.append(el("p", { class: "dim", text: "Looking…" })); return card; }
  const onMod = (n) => showInList(n);
  if (d.state === "going") card.append(el("p", {}, el("span", { class: "spinner small" }), " Looking through the mods' files: " + (d.progress[1] ? d.progress[0].toLocaleString("en-GB") + " of " + d.progress[1].toLocaleString("en-GB") + " mods" : "starting") + "…"));
  if (d.error) card.append(el("p", { class: "would-needs", text: "The scan stopped: " + d.error }));
  card.append(el("p", { class: "dim", text: "Looked for when the modlist was opened: the same mod installed twice, a mod named as a copy of another, a plugin or a script extender plugin of the same name in two enabled mods." }));
  card.append(d.quick.length ? findingList(d.quick, "quick", onMod) : el("p", {}, el("span", { class: "tag good", text: "fine" }), " No mod is in the modlist twice, and no plugin of the same name is in two enabled mods."));
  if (d.deep) {
    const l = d.looked || {};
    card.append(el("h3", { text: "The scan of every mod's files" }),
      el("p", { class: "dim", text: (l.mods || 0).toLocaleString("en-GB") + " enabled mods, " + (l.files || 0).toLocaleString("en-GB") + " files, in " + (l.seconds || 0) + " s" + (l.cut ? ". It was cut short: there may be more." : ".") }),
      d.deep.length ? findingList(d.deep, "deep", onMod) : el("p", {}, el("span", { class: "tag good", text: "fine" }), " No enabled mod is wholly overwritten, and no archive or script extender plugin is of a kind this game does not load."));
  } else if (d.state !== "going") card.append(el("p", { class: "dim", text: "“Scan the modlist” looks further: through every enabled mod's files, for mods that do nothing where they stand and for files this game does not load." }));
  return card;
}

function renderHealth(s) {
  const box = $("health");
  if (s.issue_count !== undefined) state.last = s;
  const key = JSON.stringify([state.status, s.issue_count, s.issues, state.listScan, state.listScanFor === state.loaded]);
  if (key === state.healthKey && box.firstChild) return;
  state.healthKey = key;
  if (state.status === "ready" && state.listScanFor !== state.loaded && !state.listScanAsking) {
    state.listScanAsking = true;
    listScan(false).finally(() => { state.listScanAsking = false; });
  }
  const scan = state.status === "ready" ? scanCard() : null;
  if (!s.issue_count) {
    box.replaceChildren(el("div", { class: "card" }, el("h2", { text: "The load order is clean" }),
      el("p", { class: "dim", text: "No active plugin lists a master that is missing or not active. This is what MO2's own warning checks." })), scan);
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
  box.replaceChildren(card, scan);
}

// --- sessions, and what the page remembers (MT20) -------------------------------------------------------------------

const STATUS_WORDS = { active: "holds the modlist", waiting: "waiting, locked", finished: "finished" };

function currentUi() {
  return {
    tab: state.tab || "mods", split: state.splitAt || 50, swap: !!state.splitSwap, cols: state.cols || {}, picked: [...state.picked], order: $("mods-order").value,
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
    state.splitAt = Number.isFinite(ui.split) ? Math.max(15, Math.min(85, ui.split)) : 50;
    state.cols = ui.cols && typeof ui.cols === "object" && !Array.isArray(ui.cols) ? ui.cols : {};
    colSetupAll(true);
    state.splitSwap = !!ui.swap;
    $("mods-order").value = Object.keys(MOD_ORDERS).includes(ui.order) ? ui.order : "mo2";
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
    const tabs = [...document.querySelectorAll("#tabs button[data-tab]")].map((b) => b.dataset.tab);
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
      el("p", { class: "dim", text: "The probe changes MO2's lists for its test mods, so it runs only when ModTrap is started with --allow-changes. Until it has passed, “Install mod” and “Demaster Selected” stay off." })));
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
    pr && pr.state === "passed" ? el("p", { class: "would-record", text: "Every step passed" + (pr.xedit ? " with xEdit version number " + pr.xedit : "") + ". “Install mod” and “Demaster Selected” are now allowed on this modlist. If you change your xEdit, run the probe again." }) : null,
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
  "plugin activated": "Plugin activated", "mod moved": "Mod moved", "separator moved": "Separator moved", "separator renamed": "Separator renamed", "plugin demastered": "Plugin demastered", "reverted": "Reverted", "revert finished": "Revert finished", "tool settings changed": "A tool's settings changed", "mo2 settings changed": "MO2's settings changed", "tool ran": "Tool run", "verified": "Checked" };

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
          const undo = el("button", { type: "button", text: j.what === "add" ? "Uninstall" : "Revert" });
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
  try { sessionStorage.setItem("modtrap-quit", "1"); } catch (e) { /* no storage */ }       // a page brought back after a Quit does not start ModTrap by itself
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
  tick.className = "pickbox";
  tick.addEventListener("change", () => togglePick(m.name, tick.checked));
  // On the Modlist page the box is MO2's own: the mod is enabled or not (MT56).
  const canSet = m.kind === "mod" && m.listed && state.changes;
  const on = el("input", { type: "checkbox", class: "onbox", disabled: !canSet, checked: !!m.enabled, "aria-label": "Enable " + m.name,
    title: canSet ? (m.enabled ? "Enabled. Untick to disable the mod; its plugins are then switched off" : "Disabled. Tick to enable the mod; its plugins become active, placed by MO2's own rule")
      : m.kind !== "mod" ? "Always on: MO2 does not manage this entry" : !m.listed ? "Not in modlist.txt yet: open MO2 once" : NO_CHANGES });
  on.addEventListener("change", () => listSet([m.name], on.checked, on));
  // The mod's name is a button of its own (MT62): it opens the mod's web. The rest of the row only shows the mod.
  const title = el("span", { class: "modtitle", role: "button", tabIndex: 0, text: m.kind === "overwrite" ? "Overwrite" : m.name, title: "Show this mod and every mod it has to do with: what it needs, what needs it, what it overwrites and what overwrites it" });
  title.addEventListener("click", (ev) => { if (state.placing) return; ev.stopPropagation(); webOpen(m.name); });
  title.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); ev.stopPropagation(); webOpen(m.name); } });
  const name = el("td", { class: "modname" }, title);
  if (m.kind === "foreign") name.append(el("span", { class: "tag", title: "A DLC or Creation Club item MO2 lists but does not manage", text: "not managed by MO2" }));
  if (m.kind === "game") name.replaceChildren("The game's own Data folder");
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
    el("td", { class: "c-tick" }, tick, on), el("td", { class: "c-num", text: m.priority < 0 ? "" : m.priority }), name, plugs,
    el("td", { class: "c-num" + (m.dependants ? " badnum" : ""), text: m.plugins.length ? m.dependants : "" }));
  // A click on the row only shows the mod and what is tied to it; ticking is the box's alone (WHY§59).
  tr.addEventListener("click", (ev) => {
    if (ev.target.closest("input, button, a")) return;
    focusMod(m.name);
  });
  tr.dataset.name = m.name;
  if (m.kind === "mod") tr.addEventListener("contextmenu", (ev) => modMenu(ev, m.name));
  else if (m.kind === "foreign") tr.addEventListener("contextmenu", (ev) => { if (picking()) return; ev.preventDefault(); menuAt(ev.clientX, ev.clientY, m.name, [
    { text: "Add separator below…", off: !state.changes, note: state.changes ? "" : NO_CHANGES, run: () => addSeparator(m.name) }]); });
  m.row = tr;
  m.hay = fold(m.name + " " + m.plugins.join(" "));
}

function groupRow(g) {
  const arrow = el("span", { class: "arrow", text: "▾" });
  const info = el("span", { class: "dim ginfo" });
  const btn = el("button", { type: "button", class: "gtoggle", "aria-expanded": "true" }, arrow, g.sep.name.replace(/_separator$/i, ""));
  const tr = el("tr", { class: "sep" }, el("td", { colSpan: 5 }, btn, info));
  tr.dataset.sep = g.sep.name;
  tr.addEventListener("contextmenu", (ev) => sepMenu(ev, g));
  btn.addEventListener("click", () => {
    if (state.placing) return;                     // while a place is chosen, a click on the list means the place
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
  colSetup($("mods-table"));
}

function layoutMods() {
  const sort = modSort();
  const frag = document.createDocumentFragment();
  state.grouped = sort.key === "priority";
  if (!state.grouped) {
    // By a column other than priority: one list of the mods, without the separators, which belong to the priority order.
    const flat = state.groups.flatMap((g) => g.mods).filter((m) => m.kind === "mod" && (sort.key !== "deps" || m.plugins.length));
    const by = sort.key === "name" ? (a, b) => naturally(a.name, b.name) : sort.key === "plugins" ? (a, b) => a.plugins.length - b.plugins.length : (a, b) => a.dependants - b.dependants;
    flat.sort((a, b) => (sort.desc ? -by(a, b) : by(a, b)) || a.priority - b.priority);
    flat.forEach((m) => frag.append(m.row));
    state.flat = new Set(flat);
  } else {
    const groups = sort.desc ? [...state.groups].reverse() : state.groups;
    for (const g of groups) {
      if (g.sep) frag.append(g.row);
      (sort.desc ? [...g.mods].reverse() : g.mods).forEach((m) => frag.append(m.row));
    }
    state.flat = null;
  }
  sortHeads($("mods-table"), [null, "priority", "name", "plugins", "deps"], sort, setModSort);
  $("mods-table").tBodies[0].replaceChildren(frag);
  $("collapse-all").disabled = $("expand-all").disabled = !state.grouped;
  if (state.focus) paintFocus();
  filterMods();
}

// A search box takes a star and a number, like *138 (MT60): the list is not narrowed then; the entry with that
// number (a mod's priority, a plugin's position) is brought into view. `starNumber` is that number, null for a
// search by words, and NaN while only the star, or something that is no number, stands there.
function starNumber(text) {
  const t = text.trim();
  if (!t.startsWith("*")) return null;
  const m = /^\*\s*(\d{1,7})$/.exec(t);
  return m ? Number(m[1]) : NaN;
}
// The rows a search found glow (MT60): `rows` take the mark, the ones marked before lose it. `jump` is the one row
// a star and a number went to: it is brought to the middle of its list, once for each number typed.
const FOUND_MAX = 100;                          // more rows than this found by words: none glows, the list is the result
function markFound(key, rows, jump, jumpKey) {
  state.found = state.found || {};
  for (const r of state.found[key] || []) r.classList.remove("found", "jump");
  state.found[key] = rows.length <= FOUND_MAX || jump ? rows : [];
  for (const r of state.found[key]) r.classList.add("found");
  state.jumped = state.jumped || {};
  if (!jump) { state.jumped[key] = ""; return; }
  jump.classList.add("found", "jump");
  if (!state.found[key].includes(jump)) state.found[key] = state.found[key].concat(jump);
  if (state.jumped[key] !== jumpKey && jump.offsetParent !== null) { state.jumped[key] = jumpKey; jump.scrollIntoView({ block: "center" }); }
}

function filterMods() {
  const typed = $("mods-search").value.trim();
  const star = starNumber(typed);
  const q = star === null ? fold(typed) : "";
  const en = $("f-enabled").checked, pl = $("f-plugins").checked, dp = $("f-deps").checked;
  // The entry a star and a number names: a mod, or a separator. A folded group that holds it is unfolded.
  let target = null, targetRow = null;
  if (Number.isFinite(star)) for (const g of state.groups) {
    if (g.sep && g.sep.priority === star) { target = g.sep; targetRow = g.row; }
    const m = g.mods.find((x) => x.priority === star && x.kind !== "game" && x.kind !== "overwrite");
    if (m) { target = m; targetRow = m.row; if (g.sep) state.collapsed.delete(g.sep.name); }
  }
  const found = [];
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
      if (ok && q && !folded) found.push(m.row);
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
  const there = targetRow && !targetRow.hidden ? targetRow : null;
  markFound("mods", found, there, "*" + star);
  if (star !== null) $("mods-shown").textContent = !Number.isFinite(star) ? "a star and a number, like *138, goes to that priority"
    : there ? "priority " + star + ": “" + bare(target.name) + "”" + (target.kind === "separator" ? ", a separator" : "")
    : target ? "priority " + star + " (“" + bare(target.name) + "”) is not shown: " + (target.kind === "separator" ? "separators show only in the order by priority" : "the filters hide it")
    : "no entry has priority " + star;
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
  linkPlugins(state.focus, true);
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
    b.addEventListener("click", () => { showInList(n); });
    return b;
  }).reduce((acc, b, i) => acc.concat(i ? [", ", b] : [b]), []);
  const can = f.kind === "mod" && f.plugins.length > 0;
  const tick = el("button", { type: "button", class: can && !state.picked.has(f.name) ? "primary" : "", disabled: !can,
    text: state.picked.has(f.name) ? "Untick" : "Tick for demaster" });
  tick.title = can ? "" : "Nothing to demaster: this mod provides no plugin";
  tick.addEventListener("click", () => { togglePick(f.name, !state.picked.has(f.name)); paintFocus(); });
  const listMode = !picking();
  const setBtn = el("button", { type: "button", text: f.enabled ? "Disable" : "Enable", disabled: !(f.kind === "mod" && f.listed && state.changes),
    title: state.changes ? "As the mod's tick does" : NO_CHANGES });
  setBtn.addEventListener("click", () => listSet([f.name], !f.enabled));
  const scanBtn = el("button", { type: "button", text: state.scan && state.scan.mod === f.name && state.scan.data ? "Scan again" : "Scan what it overwrites", disabled: !["mod", "overwrite"].includes(f.kind),
    title: "Whether its plugins stand safely in the load order, the records and files it overwrites, and what overwrites its own. It only reads." });
  scanBtn.addEventListener("click", () => scanMod(f.name, true));
  const only = el("input", { type: "checkbox", checked: !!state.onlyRelated });
  only.addEventListener("change", () => { state.onlyRelated = only.checked; filterMods(); });
  const close = el("button", { type: "button", text: "Close" });
  close.addEventListener("click", () => focusMod(f.name));
  const webBtn = el("button", { type: "button", text: "Its web…", title: "The mod in the middle of every mod it has to do with, as a click on its name shows" });
  webBtn.addEventListener("click", () => webOpen(f.name));
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
    el("div", { class: "actions" }, ...(listMode ? [setBtn, scanBtn] : [tick]), f.kind !== "game" ? webBtn : null, el("label", { title: "Hide every mod that is not tied to this one" }, only, " Show only this mod and the mods tied to it"), close),
    listMode ? scanView(f.name) : null].filter(Boolean));
}

function findMod(name) {
  for (const g of state.groups || []) for (const m of g.mods) if (m.name === name) return m;
  return null;
}

// A row brought to the middle of its list. What is drawn right after (the mod's card above the list, a list read
// anew) moves the list under it, so the row is looked for again once the page has settled, and brought back.
function flash(row) {
  const seen = () => { const pane = row.closest(".scroll") || row.parentElement, a = row.getBoundingClientRect(), b = pane.getBoundingClientRect(); return a.top >= b.top + 30 && a.bottom <= b.bottom - 4; };
  row.scrollIntoView({ block: "center" });
  row.classList.add("flash");
  setTimeout(() => row.classList.remove("flash"), 1600);
  for (const ms of [60, 300, 900]) setTimeout(() => { if (document.contains(row) && row.offsetParent !== null && !seen()) row.scrollIntoView({ block: "center" }); }, ms);
}
// The mod's card first, then its row: the card takes room above the list.
function showInList(name) {
  if (!findMod(name)) return;
  focusMod(name, true);
  gotoMod(name);
}

function gotoMod(name) {
  const m = findMod(name);
  if (!m) return;
  if (state.tab !== "split") showTab(picking() ? "pick" : "mods");
  clearModFilters();
  if (modSort().key !== "priority") { $("mods-order").value = "mo2"; layoutMods(); }
  const g = state.groups.find((x) => x.mods.includes(m));
  if (g && g.sep && state.collapsed.delete(g.sep.name)) filterMods();
  flash(findMod(name).row);
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
    const box = m.row.querySelector("input.pickbox");
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

// --- the Modlist page as MO2's own list (MT56): tick to enable, drag to move, a separator's name, undo, the scanner ---
// The mods' table serves two tabs: Modlist › Mods, where the box is MO2's (the mod is enabled), and Demaster › Pick
// mods, where it chooses the mod for demastering. Every change goes to ModTrap's program, which makes it as a small
// job of its own: MO2 closed, the lists copied first, the result read back, the change in the history, and Undo.
const NO_CHANGES = "ModTrap changes a modlist only when it is started with its switch for changes";
function picking() { return state.tab === "pick"; }
const bare = (name) => name.replace(/_separator$/i, "");

function modsMode() {
  const pick = picking();
  $("mods-table").classList.toggle("picking", pick);
  $("mods-tick-head").title = pick ? "Tick a mod to choose it for demastering" : "Ticked: the mod is enabled in MO2. Tick or untick it to enable or disable the mod";
  $("mods-hint").textContent = pick ? "Tick the mods to take out." : state.changes ? "Tick to enable or disable · drag a row to move it · right-click for more" : "";
  renderUndo();
  if (state.focus) paintFocus();
}

// One change after the other: each waits until ModTrap has read the modlist again after the one before it.
let listChain = Promise.resolve();
function listDo(run) {
  const next = listChain.then(async () => {
    for (let i = 0; i < 300; i++) {
      let s;
      try { s = await api("/api/state"); } catch (e) { break; }
      if (s.status !== "reading") break;
      await new Promise((r) => setTimeout(r, 200));
    }
    return run();
  });
  listChain = next.catch(() => {});
  return next;
}
function listChanged(text) {
  if (text) toast(text);
  state.pscan = {};                                // what plugins overwrite depends on the order: asked anew
  state.scan = null;
  $("scan-note").hidden = true;
  clearTimeout(state.scanTimer);
  state.gen = (state.gen || 0) + 1;
  state.status = "reading";
  tick();
}
async function loadListState() {
  try { state.listState = await api("/api/list"); } catch (e) { state.listState = null; }
  renderUndo();
}
function renderUndo() {
  const u = state.listState && state.listState.undo;
  for (const b of [$("list-undo"), $("plugins-undo")]) {
    b.hidden = (b.id === "list-undo" && picking()) || !u || !state.changes;
    if (!u) continue;
    b.textContent = "Undo: " + u.text;
    b.title = "Turns back the last change made on the Modlist section's lists (Ctrl+Z): " + u.text + ". MO2 must be closed.";
  }
  $("plugins-hint").textContent = state.changes ? "Tick to activate or deactivate · drag a row to move it · ⚠ and ⇄ on a row: press for what they stand for" : "";
}
function listUndo() {
  if (!state.changes || !(state.listState && state.listState.undo)) return;
  listDo(async () => {
    try { const got = await api("/api/list/undo", {}); listChanged("Undone: " + got.text + "." + (got.notes && got.notes.length ? " Not turned back: " + got.notes.join("; ") : "")); }
    catch (e) { toast(e.message); }
  });
}

// What a change would do and what is not safe about it, as a list for the question box and the notes.
function findings(plan) {
  const items = [];
  for (const w of plan.warnings || []) items.push(el("li", { class: w.level, text: w.text }));
  for (const p of plan.plugins || []) items.push(el("li", { text: p.name + " [" + p.kind + "]: " + (p.how === "deactivated" ? "switched off; its line stays in the load order" : "active, " + p.why + (p.before ? ", directly before " + p.before : "")) }));
  for (const n of plan.notes || []) items.push(el("li", { class: "dim", text: n }));
  return items.length ? el("ul", { class: "findings" }, ...items) : null;
}

// Enables or disables mods, as their tick in MO2 does. What is not safe is asked first; the rest is one press.
function listSet(names, on, box) {
  const put = (v) => { if (box) box.checked = v; };
  if (!state.changes) { put(!on); toast(NO_CHANGES); return Promise.resolve(false); }
  const label = names.length === 1 ? "“" + names[0] + "”" : plural(names.length, "mod");
  return listDo(async () => {
    let got;
    try {
      if (!await mo2Closed()) { put(!on); return false; }
      got = await api("/api/list/set", { mods: names, on });
      if (!got.done && got.ask) {
        const ok = await modalBox((on ? "Enable " : "Disable ") + label + "?\n\nNot everything about it is safe:", { nodes: [findings(got.plan)].filter(Boolean), wide: true, yes: on ? "Enable anyway" : "Disable anyway", no: "Cancel" });
        if (!ok) { put(!on); return false; }
        got = await api("/api/list/set", { mods: names, on, sure: true });
      }
    } catch (e) { put(!on); toast(e.message); return false; }
    if (got.nothing) return true;
    const warn = (got.plan.warnings || []).filter((w) => w.level === "warn").map((w) => w.text);
    const placed = (got.plan.plugins || []).filter((p) => p.how !== "deactivated").map((p) => p.name + " " + p.why);
    for (const n of names) { const m = findMod(n); if (m && m.row) m.row.classList.toggle("off", !on); }
    listChanged(got.text + "." + (placed.length ? " " + placed.slice(0, 2).join("; ") + (placed.length > 2 ? "; …" : "") + "." : "") + (warn.length ? " Note: " + warn[0] : ""));
    const first = names.length === 1 ? findMod(names[0]) : null;
    if (on && first && first.files > 0 && (state.settings || {}).scan_on_enable !== false) state.scanTimer = setTimeout(() => scanMod(names[0], false), 1200);
    return true;
  });
}

function listMove(names, before) {
  if (!state.changes) { toast(NO_CHANGES); return; }
  listDo(async () => {
    try { const got = await api("/api/list/move", { mods: names, before }); listChanged(got.text + "."); } catch (e) { if (e.message !== "it is there already") toast(e.message); }
  });
}

async function moveToPriority(name) {
  const listed = state.mods.filter((m) => ["mod", "separator", "foreign"].includes(m.kind) && m.listed).sort((a, b) => a.priority - b.priority);
  const me = listed.find((m) => m.name === name);
  if (!me) return;
  const lo = listed[0].priority, hi = listed[listed.length - 1].priority;
  const v = await modalBox("Move “" + bare(name) + "” to another priority\n\nIts priority now is " + me.priority + ". Give the priority it is to have, from " + lo + " to " + hi + ": a higher number wins a conflict. MO2 must be closed.", { input: String(me.priority), yes: "OK", no: "Cancel" });
  if (v === null) return;
  const want = Number.parseInt(v.trim(), 10);
  if (!Number.isFinite(want) || String(want) !== v.trim()) { toast("Give a whole number from " + lo + " to " + hi + "."); return; }
  if (want === me.priority) return;
  const rest = listed.filter((m) => m.name !== name);
  const i = Math.max(0, Math.min(rest.length, want - lo));
  listMove([name], i < rest.length ? rest[i].name : "");
}

async function renameSeparator(name) {
  const to = await modalBox("Rename the separator “" + bare(name) + "”\n\nIts new name, as MO2 will show it. ModTrap renames it in MO2's own way, in every profile of the modlist; MO2 must be closed.", { input: bare(name), yes: "OK", no: "Cancel" });
  if (to === null || !to.trim() || to.trim() === bare(name)) return;
  listDo(async () => {
    try {
      const got = await api("/api/list/rename", { name, to: to.trim() });
      if (state.collapsed.delete(name)) state.collapsed.add(got.name);
      listChanged(got.text + ".");
    } catch (e) { toast(e.message); }
  });
}

// A separator's menu: on the Modlist page it names, adds and switches; on Pick mods a separator has none.
function sepMenu(ev, g) {
  if (picking()) return;
  ev.preventDefault();
  const off = !state.changes, note = off ? NO_CHANGES : "";
  const mods = g.mods.filter((m) => m.kind === "mod" && m.listed);
  const offs = mods.filter((m) => !m.enabled).map((m) => m.name), ons = mods.filter((m) => m.enabled).map((m) => m.name);
  menuAt(ev.clientX, ev.clientY, bare(g.sep.name), [
    { text: "Rename separator…", off, note: note || "Its folder in MO2's mods folder and its line in every profile's list, as MO2 itself renames one", run: () => renameSeparator(g.sep.name) },
    { text: "Add separator below…", off, note: note || "Right below this separator, above its mods", run: () => addSeparator(g.sep.name) },
    null,
    { text: "Enable all under it" + (offs.length ? " (" + offs.length + ")" : ""), off: off || !offs.length, note, run: () => listSet(offs, true) },
    { text: "Disable all under it" + (ons.length ? " (" + ons.length + ")" : ""), off: off || !ons.length, note, run: () => listSet(ons, false) },
    null,
    { text: "Copy the separator's name", run: () => navigator.clipboard.writeText(bare(g.sep.name)).then(() => toast("The name is copied."), () => toast("The name could not be copied.")) },
  ]);
}

// MO2's list by name, lowest priority first; and the place a line stands for, exactly. Below a row means right after
// it in MO2's list, whatever the search or the filters hide in between. Below a folded separator means after the
// mods under it, which is the next row shown: as placeAt has it.
function listedNames() { return state.mods.filter((m) => ["mod", "separator", "foreign"].includes(m.kind) && m.listed).sort((a, b) => a.priority - b.priority).map((m) => m.name); }
function exactPlace(at, listed) {
  if (at && at.below && !(at.tr.dataset.sep && state.collapsed.has(at.tr.dataset.sep))) {
    const here = at.tr.dataset.sep || at.tr.dataset.name || "", i = listed.indexOf(here);
    at.before = i >= 0 ? (i + 1 < listed.length ? listed[i + 1] : "*last*") : (findMod(here) || {}).kind === "game" ? (listed[0] || "*last*") : "*last*";
  }
  if (at) at.words = at.before === "*last*" ? "last of all in MO2's list" : "right before “" + bare(at.before) + "”" + (at.after ? ", after “" + bare(at.after) + "”" : "");
  return at;
}

// Dragging a row to another place, as in MO2: the mouse held down on a mod or a separator and moved. A folded
// separator takes the mods under it along; an unfolded one moves alone. The line shows where the row would go.
let drag = null;
function dragWhat(tr) {
  if (tr.dataset.sep) {
    const g = state.groups.find((x) => x.sep && x.sep.name === tr.dataset.sep);
    if (!g) return null;
    const along = state.collapsed.has(tr.dataset.sep) ? g.mods.filter((m) => m.kind === "mod" && m.listed).map((m) => m.name) : [];
    return { names: [tr.dataset.sep, ...along], label: bare(tr.dataset.sep) + (along.length ? " and its " + plural(along.length, "mod") : " (the separator alone: fold it to take its mods along)") };
  }
  const m = findMod(tr.dataset.name || "");
  return m && m.kind === "mod" && m.listed ? { names: [m.name], label: m.name } : null;
}
function dragEnd() {
  if (!drag) return;
  clearInterval(drag.timer);
  if (drag.ghost) drag.ghost.remove();
  if (drag.tr) drag.tr.classList.remove("drag-src");
  document.body.classList.remove("dragging-mod");
  placeLine(null);
  drag = null;
}
$("mods-table").addEventListener("mousedown", (ev) => {
  if (ev.button !== 0 || picking() || state.placing || !state.changes || ev.target.closest("input")) return;
  const tr = ev.target.closest("#mods-table tbody tr");
  const what = tr ? dragWhat(tr) : null;
  if (what) drag = { tr, x: ev.clientX, y: ev.clientY, going: false, at: null, names: what.names, label: what.label, listed: listedNames() };
});
document.addEventListener("mousemove", (ev) => {
  if (!drag) return;
  if (!drag.going) {
    if (Math.abs(ev.clientX - drag.x) + Math.abs(ev.clientY - drag.y) < 7) return;
    if (!state.grouped || modSort().desc) { dragEnd(); toast("To move a mod, order the list as in MO2: by priority, lowest first."); return; }
    drag.going = true;
    drag.ghost = el("div", { class: "dragghost", text: drag.label });
    document.body.append(drag.ghost);
    document.body.classList.add("dragging-mod");
    drag.tr.classList.add("drag-src");
    const sel = window.getSelection && window.getSelection();
    if (sel) sel.removeAllRanges();
    const pane = $("mods-table").closest(".scroll");
    drag.timer = setInterval(() => {                        // near the list's upper or lower edge, the list moves on
      if (!drag || !pane || drag.py == null) return;
      const r = pane.getBoundingClientRect();
      const d = drag.py < r.top + 36 ? -1 : drag.py > r.bottom - 36 ? 1 : 0;
      if (d) pane.scrollTop += d * 26;
    }, 40);
  }
  ev.preventDefault();
  drag.py = ev.clientY;
  drag.ghost.style.left = (ev.clientX + 14) + "px";
  drag.ghost.style.top = (ev.clientY + 12) + "px";
  const at = exactPlace(placeAt(ev), drag.listed);
  // No place: on itself, or where it already stands.
  const last = drag.names[drag.names.length - 1], after = drag.listed.indexOf(last) + 1;
  const mine = at && (drag.names.includes(at.before) || at.before === (after < drag.listed.length ? drag.listed[after] : "*last*"));
  drag.at = at && !mine ? at : null;
  placeLine(drag.at ? drag.at.tr : null, drag.at && drag.at.below);
});
document.addEventListener("mouseup", () => {
  if (!drag) return;
  const d = drag, went = drag.going;
  dragEnd();
  if (!went) return;
  state.dragged = Date.now();                              // the click that ends a drag is not a click on the row
  if (d.at) listMove(d.names, d.at.before === "*last*" ? "" : d.at.before);
});
document.addEventListener("click", (ev) => { if (state.dragged && Date.now() - state.dragged < 400) { ev.preventDefault(); ev.stopPropagation(); } state.dragged = 0; }, true);
document.addEventListener("keydown", (ev) => { if (drag && ev.key === "Escape") dragEnd(); });
window.addEventListener("blur", dragEnd);
$("list-undo").addEventListener("click", listUndo);

// The scanner (MT56): for one mod, whether its plugins stand safely in the load order and what they overwrite there,
// and the files it shares with the mods below and above it. Asked for from the mod's menu or card, and by itself
// after a mod with plugins is enabled; then the verdict comes as a note at the foot of the page, which moves nothing.
async function scanMod(name, show) {
  const token = (state.scanToken || 0) + 1;
  state.scanToken = token;
  state.scan = { mod: name, going: true };
  if (show) { $("scan-note").hidden = true; if (state.focus !== name) focusMod(name, true); else paintFocus(); }
  for (let i = 0; i < 300; i++) {                           // the modlist as it now is, not as it was a moment ago
    let s;
    try { s = await api("/api/state"); } catch (e) { break; }
    if (s.status !== "reading") break;
    await new Promise((r) => setTimeout(r, 200));
  }
  let d = null, error = "";
  try { d = await api("/api/list/scan", { mod: name }); } catch (e) { error = e.message; }
  if (state.scanToken !== token) return;
  state.scan = { mod: name, data: d, error };
  if (state.focus === name) paintFocus();
  if (!show) scanNote(name, d, error);
}
function scanCounts(d) {
  const sum = (list, key) => list.reduce((a, x) => a + x[key], 0);
  const c = { problems: 0, over: 0, overPlugins: 0, under: 0, underPlugins: 0, wins: sum(d.files.wins, "files"), winMods: d.files.wins.length, loses: sum(d.files.loses, "files"), loseMods: d.files.loses.length };
  for (const p of d.plugins) {
    c.problems += p.problems.length;
    c.over += sum(p.overwrites, "records"); c.overPlugins += p.overwrites.length;
    c.under += sum(p.overwritten_by, "records"); c.underPlugins += p.overwritten_by.length;
  }
  return c;
}
function scanNote(name, d, error) {
  const box = $("scan-note");
  if (error || !d) { box.hidden = true; return; }
  const c = scanCounts(d);
  const bits = [];
  if (d.plugins.length) bits.push(c.problems ? plural(c.problems, "problem") + " with its plugins' place: " + d.plugins.flatMap((p) => p.problems.map((x) => p.name + ": " + x)).slice(0, 2).join("; ")
    : (d.plugins.length === 1 ? "its plugin stands" : "its " + d.plugins.length + " plugins stand") + " safely in the load order");
  if (c.over) bits.push("overwrites " + plural(c.over, "record") + " that " + plural(c.overPlugins, "other plugin") + " changed");
  if (c.under) bits.push(plural(c.under, "record") + " of its own " + (c.under === 1 ? "is" : "are") + " overwritten by " + plural(c.underPlugins, "later plugin"));
  if (c.wins) bits.push("overwrites " + plural(c.wins, "file") + " of " + plural(c.winMods, "mod"));
  if (c.loses) bits.push(plural(c.loses, "file") + " of its own " + (c.loses === 1 ? "is" : "are") + " overwritten by " + plural(c.loseMods, "mod"));
  if (!c.over && !c.under && !c.wins && !c.loses) bits.push("it overwrites nothing, and nothing overwrites it");
  const show = el("button", { type: "button", class: "primary", text: "Show the details" });
  show.addEventListener("click", () => { box.hidden = true; showInList(name); });
  const close = el("button", { type: "button", text: "Close" });
  close.addEventListener("click", () => { box.hidden = true; });
  box.className = "scannote" + (c.problems ? " bad" : "");
  box.replaceChildren(el("b", { text: "Scan of “" + name + "”: " }), bits.join("; ") + "." + (d.cut || d.files.cut ? " (The look was cut short: there may be more.)" : ""), el("div", { class: "actions" }, show, close));
  box.hidden = false;
}
// What the scan found of one plugin, as parts for a card or a pane: its place and whether it stands safely, the
// records it changes, the plugins whose change it overwrites and the ones that overwrite its own.
function scanPluginParts(p, titled) {
  const out = [];
  const kinds = (k) => Object.entries(k).map(([a, b]) => (KIND_WORDS[a] || a) + ": " + b).join(", ");
  const many = (list, line) => el("ul", { class: "small" }, ...list.slice(0, 12).map(line), list.length > 12 ? el("li", { class: "dim", text: "and " + (list.length - 12) + " more" }) : null);
  if (titled) {
      out.push(el("h3", {}, p.name + " ", el("span", { class: "tag", text: p.kind || "?" }), " ",
        el("span", { class: "tag " + (p.problems.length ? "bad" : "good"), text: p.problems.length ? "not safe" : "stands safely" }),
        p.position != null ? el("span", { class: "dim small", text: "  place " + p.position + " of " + p.of + " in the load order" }) : null));
  }
    if (p.problems.length) out.push(el("ul", { class: "findings" }, ...p.problems.map((x) => el("li", { class: "bad", text: x }))));
    if (p.notes.length) out.push(el("ul", { class: "findings" }, ...p.notes.map((x) => el("li", { class: "warn", text: x }))));
    if (p.records) out.push(el("p", { class: "small", text: plural(p.records, "record") + ": " + p.own + " of its own" + (p.masters.length ? "; it changes " + p.masters.map((x) => plural(x.records, "record") + " of " + x.name + " (" + kinds(x.kinds) + ")").join(", ") : "; it changes none of its masters'") + "." }));
    if (p.overwrites.length) out.push(el("p", { class: "small" }, el("b", { text: "It overwrites what " + plural(p.overwrites.length, "plugin") + " before it changed in the same records:" })),
      many(p.overwrites, (x) => el("li", {}, pluginLink(x.plugin), " (" + x.mod + "): " + plural(x.records, "record") + " · " + kinds(x.kinds))));
    if (p.overwritten_by.length) out.push(el("p", { class: "small" }, el("b", { text: plural(p.overwritten_by.length, "plugin") + " after it overwrite" + (p.overwritten_by.length === 1 ? "s" : "") + " what it changes in the same records:" })),
      many(p.overwritten_by, (x) => el("li", {}, pluginLink(x.plugin), " (" + x.mod + "): " + plural(x.records, "record") + " · " + kinds(x.kinds))));
    if (p.records && !p.overwrites.length && !p.overwritten_by.length && p.masters.length) out.push(el("p", { class: "dim small", text: "No other active plugin changes the same records." }));
    if (p.cut) out.push(el("p", { class: "dim small", text: "The look through the load order was cut short: there may be more." }));
  return out;
}
// The scan's findings in full, for the mod's card.
function scanView(name) {
  const sc = state.scan && state.scan.mod === name ? state.scan : null;
  if (!sc) return null;
  if (sc.going) return el("div", { class: "scan" }, el("p", { class: "dim" }, el("span", { class: "spinner small" }), " Looking through the load order for what this mod overwrites…"));
  if (sc.error || !sc.data) return el("div", { class: "scan" }, el("p", { class: "would-needs", text: "The scan did not run: " + (sc.error || "no answer") }));
  const d = sc.data, out = [];
  const kinds = (k) => Object.entries(k).map(([a, b]) => (KIND_WORDS[a] || a) + ": " + b).join(", ");
  const many = (list, line) => el("ul", { class: "small" }, ...list.slice(0, 12).map(line), list.length > 12 ? el("li", { class: "dim", text: "and " + (list.length - 12) + " more" }) : null);
  if (!d.enabled) {
    out.push(el("h3", { text: "The mod is disabled. Enabling it would do this:" }));
    out.push(d.plan && findings(d.plan) || el("p", { class: "dim", text: "Nothing in the load order: it brings no plugin of its own." }));
  }
  for (const p of d.plugins) out.push(...scanPluginParts(p, true));
  const f = d.files;
  const fileLine = (x) => el("li", {}, modLink(x.mod), ": " + plural(x.files, "file") + " (" + Object.entries(x.kinds).map(([k, v]) => v + " " + k).join(", ") + ")",
    x.notable.length ? el("span", { class: "tag warn", text: x.notable.join(", ") }) : null, x.output ? el("span", { class: "tag", title: x.output, text: "a tool's output" }) : null);
  out.push(el("h3", { text: "Its files" + (d.enabled ? "" : ", at the priority it has") }));
  out.push(el("p", { class: "small", text: f.wins.length ? "It overwrites " + plural(f.wins.reduce((a, x) => a + x.files, 0), "file") + " of " + plural(f.wins.length, "mod") + " below it:" : "It overwrites no file of another mod." }));
  if (f.wins.length) out.push(many(f.wins, fileLine));
  out.push(el("p", { class: "small", text: f.loses.length ? plural(f.loses.reduce((a, x) => a + x.files, 0), "file") + " of its own " + (f.loses.reduce((a, x) => a + x.files, 0) === 1 ? "is" : "are") + " overwritten by " + plural(f.loses.length, "mod") + " above it:" : "No mod above it overwrites a file of its own." }));
  if (f.loses.length) out.push(many(f.loses, fileLine));
  if (f.cut) out.push(el("p", { class: "dim small", text: "The look through the mods' folders was cut short: there may be more." }));
  return el("div", { class: "scan" }, ...out.filter(Boolean));
}

// --- a mod's file dropped on the Modlist page's list, at a place (MT57) -----------------------------------------------
// While a file is dragged over the rows of Modlist › Mods, the line of "Manual placement" shows where the mod would go
// and follows the pointer. Let go there, the place is the mod's: ModTrap takes the archive in, unpacks it, reads
// what it needs and what it overwrites at that place, installs it there and checks the result, all shown in a box
// on this page. The Installer tool has the mod too, with the place, and shows what it always shows.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function chosenPlace() {
  const p = state.addPlace;
  if (!p) return null;
  if (!p.ids.length || !p.ids.every((id) => (state.staged || []).includes(id))) { state.addPlace = null; return null; }
  return p;
}
// The place under a dragged file, or null where there is none: not on this tab, not over a row, the list not in
// MO2's order, or ModTrap not started to change anything. Shows the line, or takes it away.
function fileOver(ev) {
  let at = null;
  const types = ev && ev.dataTransfer ? Array.from(ev.dataTransfer.types || []) : [];
  if (ev && types.includes("Files") && onMods() && state.status === "ready" && state.changes && !state.placing && !state.dropRun
      && state.grouped && !modSort().desc && !document.querySelector(".modal-back")) {
    if (!state.fileListed || state.fileListed.gen !== state.loaded) state.fileListed = { gen: state.loaded, names: listedNames() };
    at = exactPlace(placeAt(ev), state.fileListed.names);
  }
  placeLine(at ? at.tr : null, at && at.below);
  document.body.classList.toggle("dropping-at", !!at);
  if (document.body.classList.contains("dragging") && state.status === "ready") $("drop-words").textContent = at ? "Let go to install the mod " + at.words
    : "Drop a mod's archive here to add it, or another modlist's folder to open that";
  return at;
}

const DROP_STAGES = [["take", "Taken in"], ["unpack", "Unpacked"], ["read", "Read"], ["install", "Installed"], ["check", "Checked"]];
function dropAtPlace(ev, at) {
  const files = Array.from((ev.dataTransfer && ev.dataTransfer.files) || []).filter((f) => ARCHIVE_NAME.test(f.name)).slice(0, 10);
  if (!files.length) { toast("Dropped on the list, a mod's archive (.zip, .7z or .rar) is installed at that place. This is none: nothing was done."); return; }
  const run = state.dropRun = { files, label: files.map((f) => f.name).join(", "), before: at.before, words: at.words, ids: [], names: [],
    stage: { take: "going", unpack: "waiting", read: "waiting", install: "waiting", check: "waiting" }, note: {}, state: "going", d: null, done: null, job: "", why: "" };
  run.back = el("div", { class: "modal-back" }, el("div", { class: "modal wide dropbox", role: "dialog", "aria-modal": "true" }));
  document.body.append(run.back);
  renderDropBox();
  dropRun(run).catch((e) => dropStop(run, "failed", e.message)).finally(() => renderDropBox());
}
function dropStop(run, how, why) {
  if (run.state !== "going") return;
  run.state = how;
  run.why = why || "";
  for (const k of Object.keys(run.stage)) if (run.stage[k] === "going") run.stage[k] = how === "yours" ? "yours" : how === "stopped" ? "skipped" : "failed";
}
async function dropRun(run) {
  const step = (k, st, note) => { run.stage[k] = st; if (note !== undefined) run.note[k] = note; renderDropBox(); };
  const body = () => ({ mods: [], staged: run.ids.slice(), before: run.before });
  // 1. Taken in: the archive goes to ModTrap's work folder (or is used from MO2's downloads folder, where it lies there).
  const got = await api("/api/add/resolve", { items: run.files.map((f) => ({ name: f.name })) });
  for (let i = 0; i < run.files.length; i++) {
    const it = got.items[i], file = run.files[i];
    if ((state.staged || []).length + (state.adding || []).length >= 20) return dropStop(run, "failed", "Twenty mods at a time is the most the Installer tool holds. Take some off its list first.");
    step("take", "going", run.files.length > 1 ? file.name : "");
    let rec = it.downloaded ? await api("/api/add/take", { name: it.name, size: file.size }).catch(() => sendArchive(file)) : await sendArchive(file);
    if (!(rec.already || []).length && it.mods.length)            // MO2 has a mod installed from this very file
      rec.already = it.mods.map((n) => { const f = findMod(n) || {}; return { mod: n, version: rec.version || "", enabled: !!f.enabled, priority: f.priority === undefined ? -1 : f.priority, how: "installed from this very file", newer: 0, same: true }; });
    if ((rec.already || []).length) {
      // The mod is in the modlist already (MT65): said, with both versions, before anything is installed.
      const answer = await new Promise((resolve) => { run.ask = { rec, resolve }; renderDropBox(); });
      run.ask = null;
      if (answer !== "second") for (let k = 0; k < 120; k++) {          // off the Installer tool's list again, once it is unpacked
        try { await api("/api/add/forget", { id: rec.id }); break; } catch (e) { if (!/still being unpacked/.test(e.message)) break; await sleep(500); }
      }
      if (answer === "cancel") return dropStop(run, "stopped", "Nothing was installed: “" + rec.already[0].mod + "” is in the modlist already, and stays as it is.");
      if (answer === "update") {
        run.updates = rec.already[0].mod;
        run.words = "in the place of “" + run.updates + "”, as its newer version";
        rec = await sendArchive(file, run.updates);
      }
      renderDropBox();
    }
    run.ids.push(rec.id);
    run.names.push(rec.name);
    state.staged = (state.staged || []).concat(rec.id);
    state.stagedInfo = Object.assign({}, state.stagedInfo, { [rec.id]: rec });
    state.addPlace = { ids: run.ids.slice(), before: run.before, words: run.words };        // the Installer tool knows the place too
    renderAddPicked();
    saveUi();
  }
  step("take", "done", "in ModTrap's work folder");
  // 2. Unpacked, 3. Read: what it needs, what it overwrites at this place, the tools that have to do with it.
  step("unpack", "going");
  let d;
  for (let i = 0; ; i++) {
    if (run.state !== "going") return;
    if (i > 3600) return dropStop(run, "failed", "It took too long to get ready. The mod is on the Installer tool's list, with its place.");
    d = await api("/api/add", body());
    const recs = (d.staged || []).filter((r) => run.ids.includes(r.id));
    if ((d.gone || []).some((id) => run.ids.includes(id)) || recs.length < run.ids.length) return dropStop(run, "failed", "The archive could not be unpacked.");
    const bad = recs.find((r) => r.state === "failed");
    if (bad) return dropStop(run, "failed", bad.note || "The archive could not be read.");
    if (recs.some((r) => r.state === "copying" || r.state === "unpacking")) { await sleep(400); continue; }
    if (recs.some((r) => r.state !== "ready")) {
      step("unpack", "done");
      step("read", "going");
      return dropStop(run, "yours", "This mod asks which parts to install. Answer its questions on the Installer tool: “Install mod” there then puts it at the place you chose.");
    }
    run.names = recs.map((r) => r.name);
    step("unpack", "done", plural(recs.reduce((a, r) => a + (r.files || 0), 0), "file"));
    step("read", "going");
    if (!d.looking && !d.unpacking) break;
    await sleep(400);
  }
  if (d.failed) return dropStop(run, "failed", d.failed);
  run.d = d;
  const needs = (d.steps || []).find((x) => x.key === "needs");
  if (needs && needs.state !== "done") return dropStop(run, "yours", "Something the mod needs is not there yet: " + needs.items.map((x) => x.text).slice(0, 3).join(" ") + " It is on the Installer tool's list, with its place.");
  if (probeReason()) return dropStop(run, "failed", "Not yet: " + probeReason() + ".");
  step("read", "done", "what it needs is there");
  // 4. Installed at the place; 5. Checked: the add job reads the lists back itself, and puts everything back if they are not as planned.
  step("install", "going");
  let r;
  for (let i = 0; ; i++) {
    if (run.state !== "going") return;
    try { r = await api("/api/add/run", body()); break; }
    catch (e) {
      if (i < 240 && /try again in a moment|still reading/.test(e.message)) { run.note.install = "waiting: " + (atWork() || "ModTrap is reading"); renderDropBox(); await sleep(500); continue; }
      throw e;
    }
  }
  run.done = r.done;
  run.job = r.job;
  state.addPlace = null;
  for (const n of run.names) if (!(state.adding || []).includes(n)) state.adding.push(n);
  saveUi();
  const first = (r.done.mods || [])[0];
  step("install", "done", first ? "priority " + first.priority : "");
  step("check", "done", "the lists read back as planned");
  run.state = "done";
  state.addText = "";
  state.gen = (state.gen || 0) + 1;
  tick();
  dropEvaluate(run, first ? first.name : run.names[0]);
}
// The installed mod, weighed at its place (MT65), once the list has been read anew with it in.
async function dropEvaluate(run, name) {
  run.evalGoing = true;
  renderDropBox();
  for (let i = 0; i < 240 && state.dropRun === run; i++) {
    await sleep(500);
    if (state.status !== "ready") continue;
    try { run.eval = await api("/api/mod/evaluate", { mod: name }); break; }
    catch (e) { if (i > 20 && !/still being read|still reading|try again/.test(e.message)) { run.evalError = e.message; break; } }
  }
  run.evalGoing = false;
  if (state.dropRun === run) renderDropBox();
}
function dropClose() {
  const run = state.dropRun;
  if (!run) return;
  run.back.remove();
  state.dropRun = null;
}
function renderDropBox() {
  const run = state.dropRun;
  if (!run) return;
  const box = run.back.firstChild;
  const WORD = { going: "going on", yours: "waits for you", done: "done", failed: "stopped", stopped: "stopped by you" };
  const kids = [el("div", { class: "uprun-head" }, el("b", { text: "Installing “" + (run.names.length ? run.names.join(", ") : run.label) + "” " + run.words }),
    el("span", { class: "tag " + ({ done: "good", failed: "bad", going: "warn" }[run.state] || ""), text: WORD[run.state] }))];
  kids.push(el("div", { class: "miniflow" }, ...DROP_STAGES.map(([k, title], i) => {
    const st = run.stage[k];
    return el("div", { class: "stage s-" + st }, el("div", { class: "stage-head" }, el("span", { class: "n", text: String(i + 1) }), el("b", { text: title }),
      el("span", { class: "ico t-" + st, "aria-hidden": "true", text: TASK_ICON[st] || "○" })),
      el("p", { class: "stage-note", text: run.note[k] || (st === "going" ? "…" : st === "waiting" ? "to come" : "") }));
  })));
  if (run.why) kids.push(el("p", { class: run.state === "failed" ? "would-needs" : "", text: run.why }));
  if (run.ask) {
    const rec = run.ask.rec, a = rec.already[0];
    const said = a.same ? "the very file it was installed from" : a.newer > 0 ? "newer" : a.newer < 0 ? "older" : rec.version && a.version ? "the same version" : "";
    const answer = (label, what, cls, title) => { const b = el("button", { type: "button", text: label, class: cls || "", title: title || "" }); b.addEventListener("click", () => run.ask.resolve(what)); return b; };
    kids.push(el("div", { class: "finding f-warn dupask" },
      el("p", { class: "f-head" }, el("span", { class: "tag warn", text: "already in the modlist" }), el("b", { text: "This mod is installed already" })),
      el("p", {}, "The modlist has “" + a.mod + "”: " + (a.version ? "version " + a.version : "of a version ModTrap cannot tell") + ", " + (a.enabled ? "enabled" : "disabled") + ", priority " + a.priority + " (" + a.how + ")."
        + (rec.already.length > 1 ? " And " + plural(rec.already.length - 1, "more copy", "more copies") + ": " + rec.already.slice(1).map((x) => "“" + x.mod + "”" + (x.version ? " " + x.version : "")).join(", ") + "." : "")),
      el("p", {}, "The file you dropped is " + (rec.version ? "version " + rec.version : "of a version its name does not tell") + (said ? ": " + said + "." : ".")
        + (a.newer > 0 ? " An update puts it in the place of the one that is there, which is kept, disabled." : a.newer < 0 ? " The modlist's is the newer one: installing this over it would be a step back."
          : a.same ? " To give the mod another place, drag its row in the list. Installed as a second mod it would be named “" + rec.name + "” and overwrite the first, file for file."
            : " Installed as a second mod it would be named “" + rec.name + "” and overwrite the first, file for file.")),
      el("div", { class: "actions" },
        answer("Update “" + a.mod + "” with it", "update", a.newer > 0 || (a.newer === 0 && !a.same && !(rec.version && a.version)) ? "primary" : "", "The file goes in as the newer version of the mod that is there, at that mod's place; the older one is kept, disabled (as “Manual update…” does)"),
        answer("Install it as a second mod", "second", "", "Both stand in the modlist; this one is named “" + rec.name + "”"),
        answer("Cancel", "cancel", a.newer < 0 || a.same || (a.newer === 0 && rec.version && a.version) ? "primary" : "", "Nothing is installed"))));
  }
  if (run.done) {
    const where = (run.done.mods || []).map((x) => "“" + x.name + "” is enabled at priority " + x.priority).join("; ");
    const plugs = (run.done.plugins || []).map((x) => x.name + " at place " + x.position).join(", ");
    kids.push(el("p", {}, el("b", { text: "Installed. " }), where + "." + (plugs ? " Active in the load order: " + plugs + "." : " It brings no plugin.")));
  }
  if (run.d) {
    const tools = (run.d.steps || []).find((x) => x.key === "tools");
    const details = [...placeLines(run.d)];
    if (tools) details.push(el("p", {}, el("b", { text: tools.items && tools.items.length ? "Tools that have to do with it:" : "No tool of the modlist has to run again for it." })),
      tools.items && tools.items.length ? moreList(tools.items.map((x) => el("li", { text: x.text })), 10, 0, "drop-tools") : null);
    // Two tabs (MT65): what is overwritten, and what that comes to.
    const ev = run.eval;
    const tab = (key, label, tag) => { const b = el("button", { type: "button", class: "minitab" + ((run.tab || "over") === key ? " on" : ""), "aria-pressed": (run.tab || "over") === key ? "true" : "false" }, label, tag); b.addEventListener("click", () => { run.tab = key; renderDropBox(); }); return b; };
    const mark = ev ? el("span", { class: "tag " + { problem: "bad", look: "warn", clean: "good" }[ev.verdict], text: { problem: "needs your attention", look: "worth a look", clean: "clean" }[ev.verdict] })
      : run.evalGoing ? el("span", { class: "spinner small" }) : null;
    kids.push(el("div", { class: "minitabs" }, tab("over", "Overwrites"), tab("eval", "Evaluation", mark)));
    const pane = (run.tab || "over") === "over" ? details.filter(Boolean)
      : ev ? evalNodes(ev, "drop-eval")
        : run.evalError ? [el("p", { class: "would-needs", text: "The evaluation could not be made: " + run.evalError })]
          : run.done ? [el("p", { class: "dim" }, el("span", { class: "spinner small" }), " Looking at the mod's own files and at every file it shares with another mod…")]
            : [el("p", { class: "dim", text: "Once the mod is installed, ModTrap weighs what it does at its place: which overwrites change nothing, which are what a patch or a retexture is for, and which are the usual ways a modlist breaks." })];
    const scrolled = (box.querySelector(".dropdetails") || {}).scrollTop || 0;
    kids.push(el("div", { class: "dropdetails" }, ...pane));
    run.scrolled = (run.shownTab === (run.tab || "over")) ? scrolled : 0;
    run.shownTab = run.tab || "over";
  }
  const acts = [];
  const act = (label, run2, cls, title) => { const b = el("button", { type: "button", text: label, class: cls || "", title: title || "" }); b.addEventListener("click", run2); acts.push(b); };
  const toTool = () => { dropClose(); showTab("add"); state.addText = ""; pollAdd(true); };
  if (run.ask) { /* the question's own buttons answer it */ }
  else if (run.state === "going") {
    if (run.stage.install === "waiting") act("Stop", () => { dropStop(run, "stopped", "Stopped. Nothing of the modlist was changed. The mod is on the Installer tool's list, with its place."); renderDropBox(); }, "", "Nothing of the modlist is changed before the install itself");
  } else {
    if (run.state === "done" && run.job) {
      act("Uninstall", async () => { if (await uninstallJob(run.job, run.names.map((n) => "“" + n + "”").join(", "))) dropClose(); }, "", "Puts MO2's lists back as they were and takes ModTrap's copy of the mod out again");
      act("Show it in the list", () => { const n = run.names[0]; dropClose(); if (findMod(n)) { showInList(n); } }, "");
    }
    act(run.state === "yours" ? "Go to the Installer tool" : "Open the Installer tool", toTool, run.state === "yours" ? "primary" : "", "The mod is there too, with everything the Installer tool shows");
    act("Close", dropClose, run.state === "yours" ? "" : "primary");
  }
  kids.push(el("div", { class: "actions" }, ...acts));
  box.replaceChildren(...kids.filter(Boolean));
  const details = box.querySelector(".dropdetails");
  if (details && run.scrolled) details.scrollTop = run.scrolled;
  const stop = box.querySelector(".actions button.primary") || box.querySelector(".actions button");
  if (stop && run.state !== "going" && !box.contains(document.activeElement)) stop.focus();
}
document.addEventListener("keydown", (ev) => {
  const run = state.dropRun;
  if (!run || ev.key !== "Escape" || document.querySelectorAll(".modal-back").length > 1) return;
  ev.preventDefault();
  if (run.state !== "going") dropClose();
}, true);

// --- one mod and its web (MT62, DESIGN§23) ----------------------------------------------------------------------------
// A click on a mod's name opens a box with the mod in the middle and, around it, every mod it has to do with: on the
// left the mods it needs, on the right the mods built on it (those that need it, patches made for it, what a tool
// made from it), above it the mods that win over it and below it the mods it wins over (files overwritten, records
// both change). A box has the colour of its kind; a line joins it to the middle, its arrow pointing at the one that
// is needed or overwritten. The server reads all of it and changes nothing: first what the plugins' headers say,
// which is there at once, then the files and the records, which takes seconds on a large modlist.
const WEB_KINDS = {
  needs: ["It needs", "A plugin of this mod names one of its plugins as a master: without it, this mod's plugin cannot load"],
  needed: ["Needs it", "One of its plugins names a plugin of this mod as a master"],
  patch: ["A patch for it", "Every plugin in it needs this mod, and it is named a patch (or a fix, a tweak, an add-on): made for this mod, often to make it work with another"],
  output: ["A tool's output", "What a tool of the modlist made, with a plugin of this mod among its masters: made anew when the tool runs again"],
  overwritten: ["Overwrites its files", "It has files of the same name and a higher priority: the game loads its files in place of this mod's"],
  overwrites: ["Files it overwrites", "This mod has files of the same name and the higher priority: the game loads this mod's files in place of its"],
  conflict: ["Conflict", "Plugins of both change the same records and neither knows the other (neither is the other's master): the later one's change wins whole, the other's is lost unseen"],
  settled: ["Conflict, settled", "Plugins of both change the same records without knowing each other, and an active third plugin has both as masters: a patch that can carry both changes"],
  loses: ["Changes its records", "A plugin made with this mod in view (one is the other's master) changes records this mod changes too, and loads later: its change is the one the game takes, as a patch means it to be"],
  wins: ["Records it changes", "A plugin of this mod changes records that a mod it knows changes too (one is the other's master), and loads later: this mod's change is the one the game takes"],
};
const WEB_LEGEND = ["needs", "needed", "patch", "output", "overwritten", "overwrites", "conflict", "settled", "loses", "wins"];
const WEB_FIRST = ["conflict", "patch", "output", "needs", "needed", "settled", "overwritten", "overwrites", "loses", "wins"];    // which kind names a box that has several
const WEB_DEEP = new Set(["overwritten", "overwrites", "conflict", "settled", "loses", "wins"]);
const WEB_SIDE = { needs: "left", needed: "right", patch: "right", output: "right", overwritten: "top", loses: "top", overwrites: "bottom", wins: "bottom" };
const WEB_HEAD = { left: "It needs", right: "Built on it", top: "Win over it", bottom: "It wins over" };
const WEB_CAP = { left: 9, right: 9, top: 8, bottom: 8 };
const WEB_W = 1000, WEB_H = 640;
const WEB_MID = { x: 378, y: 280, w: 244, h: 80 };
const SVG_NS = new DOMParser().parseFromString("<svg></svg>", "text/html").body.firstChild.namespaceURI;
const svgEl = (tag, attrs) => { const e = document.createElementNS(SVG_NS, tag); for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, v); return e; };
const webCache = new Map();                       // the modlist as it stands + the mod -> { near, deep }
const webPics = new Map();                        // the mod -> { type, data }, { none } or { going }
const webKey = (name) => (state.loaded || "") + "\n" + (state.gen || 0) + "\n" + name;
const webRank = (k) => WEB_FIRST.indexOf(k);

function webClose() {
  const w = state.web;
  if (!w) return;
  state.web = null;
  w.back.remove();
  if (w.before && w.before.focus && document.contains(w.before)) w.before.focus();
}

async function webOpen(name, opts) {
  const o = opts || {};
  let w = state.web;
  if (!w) {
    const box = el("div", { class: "modal webbox", role: "dialog", "aria-modal": "true", "aria-label": "A mod and the mods it has to do with" });
    const back = el("div", { class: "modal-back" }, box);
    back.addEventListener("mousedown", (ev) => { if (ev.target === back) webClose(); });
    w = state.web = { back, box, trail: [], hidden: new Set(), before: document.activeElement };
    document.body.append(back);
  } else if (!o.back && w.name && w.name !== name) w.trail.push(w.name);
  Object.assign(w, { name, sel: null, more: null, error: "", going: false, data: null });
  const key = webKey(name);
  const here = () => state.web === w && w.name === name;
  let kept = webCache.get(key);
  if (kept) w.data = kept.deep || kept.near;
  webRender();
  try {
    if (!kept) {
      const near = await api("/api/mod/web", { mod: name });
      kept = { near };
      webCache.set(key, kept);
      if (webCache.size > 40) webCache.delete(webCache.keys().next().value);
      if (!here()) return;
      w.data = near;
      webRender();
    }
    webPicture(w, name);
    if (!kept.deep) {
      w.going = true;
      webRender();
      kept.deep = await api("/api/mod/web", { mod: name, deep: true });
      if (!here()) return;
      w.data = kept.deep;
    }
  } catch (e) { if (here()) w.error = e.message; }
  if (here()) { w.going = false; webRender(); }
}

// The one picture the mod's page opens with (MT62): asked of the server, which fetches it from the mod's site once
// and keeps it; shown as it comes, and the box stays as it is where there is none.
async function webPicture(w, name) {
  const origin = w.data && w.data.source;
  if (!origin || !origin.picture || webPics.has(name)) return;
  webPics.set(name, { going: true });
  if (state.web === w && w.name === name) webRender();
  let got;
  try { got = await api("/api/mod/picture", { mod: name }); } catch (e) { got = { none: e.message }; }
  webPics.set(name, got);
  if (state.web === w && w.name === name) webRender();
}

// The mods around the one in the middle: one box for each, however many things tie the two; the weightiest kind
// names the box and gives it its side.
function webNodes(d, hidden) {
  const by = new Map();
  for (const x of d.links) {
    if (hidden.has(x.kind)) continue;
    let n = by.get(x.mod);
    if (!n) by.set(x.mod, n = { mod: x.mod, shown: x.shown, priority: x.priority, enabled: x.enabled, links: [] });
    n.links.push(x);
  }
  const sides = { left: [], right: [], top: [], bottom: [] };
  for (const n of by.values()) {
    n.links.sort((a, b) => webRank(a.kind) - webRank(b.kind));
    const p = n.links[0];
    n.kind = p.kind;
    n.side = WEB_SIDE[p.kind] || ((p.loses || 0) >= (p.wins || 0) ? "top" : "bottom");
    sides[n.side].push(n);
  }
  for (const list of Object.values(sides)) list.sort((a, b) => webRank(a.kind) - webRank(b.kind) || b.links[0].weight - a.links[0].weight || naturally(a.shown, b.shown));
  return sides;
}

// Where each box stands, on a sheet of 1000 by 640: a column on either side, two rows above and two below. A side
// with more mods than it has room for ends in one box that stands for the rest.
function webPlace(sides) {
  const placed = [];
  for (const side of ["left", "right", "top", "bottom"]) {
    const all = sides[side], cap = WEB_CAP[side];
    const items = (all.length > cap ? all.slice(0, cap - 1) : all).map((n) => ({ n }));
    if (all.length > cap) items.push({ more: all.slice(cap - 1) });
    items.forEach((it, i) => {
      it.side = side;
      it.h = 40;
      if (side === "left" || side === "right") {
        it.w = 232;
        it.x = side === "left" ? 8 : WEB_W - 8 - it.w;
        it.y = WEB_H / 2 + (i - (items.length - 1) / 2) * 46 - it.h / 2;
      } else {
        const row = Math.floor(i / 4), inRow = Math.min(4, items.length - row * 4);
        it.w = 238;
        it.x = WEB_W / 2 - (inRow * 248 - 10) / 2 + (i % 4) * 248;
        it.y = side === "top" ? (row ? 4 : 50) : (row ? WEB_H - 44 : WEB_H - 90);
      }
      placed.push(it);
    });
  }
  return placed;
}

// The line from a box to the middle, bent, and which way its arrow points: at the one that is needed, or the one
// whose files or changes are overwritten. Both ways where each wins somewhere.
function webEdge(it) {
  const m = WEB_MID, cx = it.x + it.w / 2, cy = it.y + it.h / 2;
  let a, b, bend;
  if (it.side === "left" || it.side === "right") {
    a = [it.side === "left" ? it.x + it.w : it.x, cy];
    b = [it.side === "left" ? m.x : m.x + m.w, WEB_H / 2 + (cy - WEB_H / 2) * 0.13];
    const mx = (a[0] + b[0]) / 2;
    bend = [[mx, a[1]], [mx, b[1]]];
  } else {
    a = [cx, it.side === "top" ? it.y + it.h : it.y];
    b = [WEB_W / 2 + (cx - WEB_W / 2) * 0.24, it.side === "top" ? m.y : m.y + m.h];
    const my = (a[1] + b[1]) / 2;
    bend = [[a[0], my], [b[0], my]];
  }
  const p = it.n ? it.n.links[0] : null;
  const kind = p ? p.kind : "";
  const toMid = ["needed", "patch", "output", "overwritten", "loses"].includes(kind) || ((kind === "conflict" || kind === "settled") && (p.loses || 0) >= (p.wins || 0));
  const both = (kind === "conflict" || kind === "settled") && p.loses > 0 && p.wins > 0;
  const pts = toMid ? [a, bend[0], bend[1], b] : [b, bend[1], bend[0], a];
  const f = (q) => q[0].toFixed(1) + " " + q[1].toFixed(1);
  return { d: "M" + f(pts[0]) + " C" + f(pts[1]) + ", " + f(pts[2]) + ", " + f(pts[3]), both };
}

// The second line of a box: its kind and how much of it, in few words. The whole of it is in the box's details.
function webShort(x) {
  const n = x.weight;
  const much = { needs: plural(n, "master"), needed: plural(n, "plugin"), output: plural(n, "plugin"), overwritten: plural(n, "file"), overwrites: plural(n, "file"),
    conflict: plural(n, "record"), settled: plural(n, "record"), loses: plural(n, "record"), wins: plural(n, "record"),
    patch: x.between && x.between.length ? "with " + x.between[0] + (x.between.length > 1 ? " and more" : "") : plural(n, "plugin") }[x.kind];
  return WEB_KINDS[x.kind][0] + " · " + much;
}

function webSelect(w, mod, more) {
  w.sel = mod || null;
  w.more = more || null;
  for (const [name, b] of w.nodes) {
    b.node.classList.toggle("sel", name === w.sel);
    b.path.classList.toggle("sel", name === w.sel);
  }
  if (w.moreEls) for (const [side, b] of w.moreEls) b.classList.toggle("sel", !!w.more && w.more.side === side);
  w.side.replaceChildren(...webSide(w));
}

function webMap(w) {
  const d = w.data;
  const map = el("div", { class: "webmap" });
  const svg = svgEl("svg", { viewBox: "0 0 " + WEB_W + " " + WEB_H, "aria-hidden": "true" });
  const defs = svgEl("defs");
  for (const k of WEB_LEGEND) {
    const mk = svgEl("marker", { id: "web-arrow-" + k, viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse" });
    mk.append(svgEl("path", { d: "M0 1 L10 5 L0 9 z", class: "wk-" + k }));
    defs.append(mk);
  }
  svg.append(defs);
  const put = (node, x, y, wd, h) => {
    node.style.left = (x / WEB_W * 100) + "%"; node.style.top = (y / WEB_H * 100) + "%";
    node.style.width = (wd / WEB_W * 100) + "%"; if (h) node.style.height = (h / WEB_H * 100) + "%";
    return node;
  };
  const sides = webNodes(d, w.hidden);
  const placed = webPlace(sides);
  w.nodes = new Map();
  w.moreEls = new Map();
  const kids = [svg];
  const hot = (path, on) => { path.classList.toggle("hot", on); map.classList.toggle("hover", on); };
  for (const it of placed) {
    const edge = webEdge(it);
    if (it.more) {
      const path = svgEl("path", { d: edge.d, class: "webline more" });
      svg.append(path);
      const b = put(el("button", { type: "button", class: "webnode more" + (w.more && w.more.side === it.side ? " sel" : ""), title: "The mods of this side that have no room here: listed on the right" },
        el("span", { class: "wn-name", text: "+ " + it.more.length.toLocaleString("en-GB") + " more" }), el("span", { class: "wn-what", text: "show them as a list" })), it.x, it.y, it.w, it.h);
      b.dataset.k = "more:" + it.side;
      b.addEventListener("click", () => webSelect(w, null, { side: it.side, mods: it.more }));
      w.moreEls.set(it.side, b);
      kids.push(b);
      continue;
    }
    const n = it.n, p = n.links[0];
    const path = svgEl("path", { d: edge.d, class: "webline wk-" + n.kind + (w.sel === n.mod ? " sel" : ""), "marker-end": "url(#web-arrow-" + n.kind + ")" });
    if (edge.both) path.setAttribute("marker-start", "url(#web-arrow-" + n.kind + ")");
    path.setAttribute("stroke-width", (1.4 + Math.min(2.2, Math.log10(1 + p.weight))).toFixed(1));
    svg.append(path);
    const b = put(el("button", { type: "button", class: "webnode wk-" + n.kind + (n.enabled ? "" : " off") + (w.sel === n.mod ? " sel" : ""),
      title: n.shown + (n.enabled ? "" : " (disabled)") + "\n" + n.links.map((x) => WEB_KINDS[x.kind][0] + ": " + x.text).join("\n") + "\n\nClick for what lies between the two; double-click to put this mod in the middle." },
      el("span", { class: "wn-name", text: n.shown }),
      el("span", { class: "wn-what", text: webShort(p) }),
      n.links.length > 1 ? el("span", { class: "wn-dots" }, ...n.links.slice(1, 6).map((x) => el("i", { class: "wk-" + x.kind }))) : null), it.x, it.y, it.w, it.h);
    b.dataset.k = "mod:" + n.mod;
    b.addEventListener("click", () => webSelect(w, n.mod));
    b.addEventListener("dblclick", () => webOpen(n.mod));
    b.addEventListener("mouseenter", () => hot(path, true));
    b.addEventListener("mouseleave", () => hot(path, false));
    b.addEventListener("focus", () => hot(path, true));
    b.addEventListener("blur", () => hot(path, false));
    w.nodes.set(n.mod, { node: b, path });
    kids.push(b);
  }
  for (const side of ["left", "right", "top", "bottom"]) {
    const mine = placed.filter((it) => it.side === side);
    if (!mine.length) continue;
    const total = sides[side].length;
    const lab = el("span", { class: "weblabel " + side, text: WEB_HEAD[side] + " · " + total.toLocaleString("en-GB") });
    if (side === "left" || side === "right") put(lab, mine[0].x, mine[0].y - 22, mine[0].w);
    else put(lab, WEB_MID.x, side === "top" ? 98 : WEB_H - 98 - 18, WEB_MID.w);
    kids.push(lab);
  }
  const me = d.mod;
  const mid = put(el("div", { class: "webmid" + (me.enabled ? "" : " off") },
    el("span", { class: "wn-name", text: me.shown, title: me.shown }),
    el("span", { class: "wn-what", text: (me.priority >= 0 ? "priority " + me.priority + " · " : "") + (me.enabled ? "enabled" : "disabled") + " · " + plural(me.plugins.length, "plugin") })), WEB_MID.x, WEB_MID.y, WEB_MID.w, WEB_MID.h);
  kids.push(mid);
  if (!placed.length) kids.push(put(el("span", { class: "weblabel none", text: w.going ? "Nothing in the plugins' headers ties it to another mod. Its files and records are being looked through…"
    : w.hidden.size ? "Nothing of the kinds that are switched on. Switch a kind on again in the list on the right." : "No other mod has to do with it: it needs none, none needs it, and nothing is overwritten either way." }), 250, 150, 500));
  map.append(...kids);
  return map;
}

function webLinkBlock(x) {
  return el("div", { class: "weblink-block wk-" + x.kind },
    el("p", {}, el("b", { class: "wkw", text: WEB_KINDS[x.kind][0], title: WEB_KINDS[x.kind][1] }), " " + x.text),
    x.lines && x.lines.length ? el("ul", { class: "small" }, ...x.lines.map((t) => el("li", { text: t })), x.more ? el("li", { class: "dim", text: "… and " + plural(x.more, "more line") }) : null) : null,
    x.settled_by && x.settled_by.length && x.kind === "settled" ? el("p", { class: "small dim", text: "Has both as masters: " + x.settled_by.join(", ") }) : null,
    x.between && x.between.length ? el("p", { class: "small dim", text: "It also needs: " + x.between.join(", ") }) : null,
    x.kind === "conflict" ? el("p", { class: "small dim", text: "The game takes a record whole from the plugin that loads last, so what the earlier plugin changed in these records is not in the game, unless the later one happens to hold the same. ModTrap reads which records each plugin changes, not what is changed inside them: look at these in xEdit to see what is lost, and whether a patch is called for." }) : null,
    x.kind === "settled" ? el("p", { class: "small dim", text: "Whether that plugin does carry both changes, for these very records, is for xEdit to show: ModTrap reads which records each plugin changes, not what is changed inside them." }) : null);
}

function webSide(w) {
  const d = w.data;
  const kids = [];
  // The kinds and their colours; a press takes a kind out of the picture or puts it back.
  kids.push(el("div", { class: "weblegend" }, ...WEB_LEGEND.map((k) => {
    const n = d.counts[k] || 0;
    const pending = !d.deep && WEB_DEEP.has(k);
    const b = el("button", { type: "button", class: "wl wk-" + k + (w.hidden.has(k) ? " out" : "") + (n ? "" : " none"), title: WEB_KINDS[k][1] + (n ? "\n\nPress to take this kind out of the picture, or to put it back." : ""), "aria-pressed": w.hidden.has(k) ? "false" : "true" },
      el("i", {}), el("span", { text: WEB_KINDS[k][0] }), el("b", { text: pending ? "…" : n.toLocaleString("en-GB") }));
    b.dataset.k = "kind:" + k;
    b.disabled = !n;
    b.addEventListener("click", () => { if (w.hidden.has(k)) w.hidden.delete(k); else w.hidden.add(k); webRender(); });
    return b;
  })));
  const go = (label, run, title, cls) => { const b = el("button", { type: "button", text: label, title: title || "", class: cls || "" }); b.addEventListener("click", run); return b; };
  const pick = (n) => { const b = el("button", { type: "button", class: "webrow wk-" + n.kind, title: n.links.map((x) => WEB_KINDS[x.kind][0] + ": " + x.text).join("\n") },
    el("i", {}), el("span", { class: "wn-name", text: n.shown }), el("span", { class: "dim", text: WEB_KINDS[n.kind][0] })); b.addEventListener("click", () => webSelect(w, n.mod)); b.addEventListener("dblclick", () => webOpen(n.mod)); return b; };
  if (w.sel) {
    const links = d.links.filter((x) => x.mod === w.sel).sort((a, b) => webRank(a.kind) - webRank(b.kind));
    const first = links[0];
    const inList = !!findMod(w.sel);
    kids.push(el("div", { class: "webdetail" },
      el("h3", {}, first.shown, first.enabled ? null : el("span", { class: "tag", text: "disabled" }), first.priority != null && first.priority >= 0 ? el("span", { class: "tag", text: "priority " + first.priority }) : null),
      el("p", { class: "dim small", text: "Between it and “" + d.mod.shown + "”:" }),
      ...links.map(webLinkBlock),
      el("div", { class: "actions" }, inList && first.mod !== "<game>" ? go("Put it in the middle", () => webOpen(w.sel), "Shows this mod's own web; “Back” brings this one again") : null,
        inList ? go("Show it in the list", () => { const n = w.sel; webClose(); showInList(n); }) : null,
        go("Back to the overview", () => webSelect(w, null)))));
  } else if (w.more) {
    kids.push(el("div", { class: "webdetail" }, el("h3", { text: WEB_HEAD[w.more.side] + ": " + plural(w.more.mods.length, "more mod") }),
      el("p", { class: "dim small", text: "The mods that have no room in the picture. Press one for what lies between the two." }),
      el("div", { class: "webrows" }, ...w.more.mods.slice(0, 400).map(pick)), w.more.mods.length > 400 ? el("p", { class: "dim small", text: "… and " + plural(w.more.mods.length - 400, "more mod") }) : null,
      el("div", { class: "actions" }, go("Back to the overview", () => webSelect(w, null)))));
  } else {
    const mods = new Set(d.links.map((x) => x.mod)).size;
    const said = [];
    said.push(el("p", { text: mods ? plural(mods, "mod has", "mods have") + " to do with it" + (d.deep ? "." : " by the plugins' headers; its files and records are being looked through.") : d.deep ? "No other mod has to do with it." : "Nothing ties it to another mod by the plugins' headers; its files and records are being looked through." }));
    for (const t of d.lacks || []) said.push(el("p", { class: "would-needs", text: t }));
    const worst = d.links.filter((x) => x.kind === "conflict").sort((a, b) => b.weight - a.weight).slice(0, 6);
    if (worst.length) said.push(el("p", {}, el("b", { class: "wkw wk-conflict", text: "Conflicts: " }), "records that two plugins change without knowing each other. The later plugin's change is the one in the game."),
      el("div", { class: "webrows" }, ...worst.map((x) => { const b = el("button", { type: "button", class: "webrow wk-conflict" }, el("i", {}), el("span", { class: "wn-name", text: x.shown }), el("span", { class: "dim", text: plural(x.weight, "record") })); b.addEventListener("click", () => webSelect(w, x.mod)); return b; })));
    if (d.deep && d.files !== undefined) said.push(el("p", { class: "dim small", text: "Looked through: " + plural(d.files, "file") + " of this mod against every other mod's, and the records of its " + plural(d.mod.plugins.length, "plugin") + " against the load order." }));
    if (d.cut) said.push(el("p", { class: "small would-needs", text: "The look was cut short, so that it does not hold you up: on a mod this large there may be more than is shown." }));
    said.push(el("p", { class: "dim small", text: "A box is a mod, in the colour of what ties it to this one. Click a box for what lies between the two: which plugin needs which, which kind of files is overwritten, which records. Double-click it to put that mod in the middle. An arrow points at the mod that is needed, or the one that is overwritten." }));
    kids.push(el("div", { class: "webdetail" }, ...said));
  }
  return kids;
}

function webRender() {
  const w = state.web;
  if (!w) return;
  const d = w.data;
  const had = w.box.contains(document.activeElement) ? document.activeElement.dataset.k : null;
  const scrolled = w.side ? w.side.scrollTop : 0;
  const close = el("button", { type: "button", class: "webclose", text: "✕", title: "Close (Esc)", "aria-label": "Close" });
  close.dataset.k = "close";
  close.addEventListener("click", webClose);
  const trail = w.trail.length ? el("button", { type: "button", class: "linkish webback", text: "← Back to “" + w.trail[w.trail.length - 1] + "”" }) : null;
  if (trail) { trail.dataset.k = "back"; trail.addEventListener("click", () => webOpen(w.trail.pop(), { back: true })); }
  if (!d) {
    w.side = null;
    w.box.replaceChildren(el("div", { class: "web-head" }, el("div", { class: "web-title" }, trail, el("h2", { text: w.name })), close),
      el("p", { class: w.error ? "would-needs" : "dim", text: w.error || "Reading what this mod has to do with the others…" }));
    close.focus();
    return;
  }
  const me = d.mod, origin = d.source;
  // The mod's page: where it came from, as a link that opens a new tab, and the picture its page opens with.
  let source;
  if (origin && /^https?:\/\//i.test(origin.page || "")) {
    const word = { nexus: "Nexus", github: "GitHub", loverslab: "LoversLab" }[origin.host] || origin.host;
    source = el("p", { class: "websource" }, "From ", el("a", { class: "weblink", href: origin.page, target: "_blank", rel: "noopener noreferrer", text: word + " ↗", title: "Opens the mod's page in a new tab:\n" + origin.page }),
      el("span", { class: "dim small", text: " " + origin.page.replace(/^https?:\/\/(www\.)?/i, "") + (origin.version ? " · version " + origin.version : "") }));
  } else if (me.kind === "mod") {
    const add = el("button", { type: "button", class: "linkish", text: "Add a source link…" });
    add.addEventListener("click", async () => { await sourceLink(me.name, ""); webCache.delete(webKey(me.name)); if (state.web === w && w.name === me.name) webOpen(me.name, { back: true }); });
    source = el("p", { class: "websource dim" }, "Where it came from is not known. ", add);
  }
  const pic = webPics.get(me.name);
  let picture = null;
  if (pic && pic.data && /^image\/(png|jpeg|webp|gif)$/.test(pic.type || "")) {
    picture = el("img", { class: "webpic", alt: "The picture of the mod's page", src: "data:" + pic.type + ";base64," + pic.data });
    if (origin && origin.page) { picture.title = "From the mod's page. Click to open the page in a new tab."; picture.addEventListener("click", () => openTab(origin.page)); }
  } else if (pic && pic.going) picture = el("div", { class: "webpic wait", text: "its picture…" });
  const plugins = me.plugins.slice(0, 8).map((p, i) => {
    const b = el("button", { type: "button", class: "linkish mono", text: p.name, title: (p.active ? "Active" : "Not active") + (p.position != null && p.position >= 0 ? ", place " + p.position : "") + ". Click to show it on the Plugins tab." });
    b.addEventListener("click", () => { webClose(); gotoPlugin(p.name); });
    return i ? [", ", b] : [b];
  }).flat();
  const head = el("div", { class: "web-head" }, picture, el("div", { class: "web-title" }, trail,
    el("h2", {}, me.shown, el("span", { class: "tag " + (me.enabled ? "good" : ""), text: me.enabled ? "enabled" : "disabled" }), me.priority >= 0 ? el("span", { class: "tag", text: "priority " + me.priority }) : null),
    el("p", { class: "dim" }, me.plugins.length ? "Plugins: " : "It has no plugin.", ...plugins, me.plugins.length > 8 ? " … +" + (me.plugins.length - 8) : ""),
    source), close);
  w.side = el("div", { class: "webside" }, ...webSide(w));
  const body = el("div", { class: "web-body" }, el("div", { class: "webmap-wrap" }, webMap(w)), w.side);
  const acts = [];
  const act = (label, run, cls) => { const b = el("button", { type: "button", text: label, class: cls || "" }); b.addEventListener("click", run); b.dataset.k = "act:" + label; acts.push(b); };
  if (findMod(me.name)) act("Show it in the list", () => { webClose(); showInList(me.name); });
  act("Close", webClose, "primary");
  const status = w.error ? el("span", { class: "would-needs", text: w.error })
    : w.going ? el("span", { class: "webstatus going" }, el("span", { class: "spinner small" }), "Looking through its files and its records…")
      : el("span", { class: "webstatus dim", text: d.deep ? "Read from the modlist as it stands now. Nothing is changed." : "" });
  w.box.replaceChildren(head, body, el("div", { class: "web-foot" }, status, el("div", { class: "actions" }, ...acts)));
  w.side.scrollTop = scrolled;
  const again = had ? [...w.box.querySelectorAll("[data-k]")].find((e) => e.dataset.k === had) : null;
  (again || (w.box.contains(document.activeElement) ? null : close) || { focus() {} }).focus();
}
document.addEventListener("keydown", (ev) => {
  const w = state.web;
  if (!w || document.querySelectorAll(".modal-back").length > 1 || state.menu) return;
  if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); if (w.sel || w.more) webSelect(w, null); else webClose(); return; }
  if (ev.key !== "Tab") return;                    // the box keeps the keyboard while it is open
  const stops = [...w.box.querySelectorAll("button:not([disabled]), a[href], [tabindex='0']")].filter((e) => e.offsetParent !== null);
  if (!stops.length) return;
  const i = stops.indexOf(document.activeElement);
  if (i === -1 || (ev.shiftKey && i === 0) || (!ev.shiftKey && i === stops.length - 1)) { ev.preventDefault(); stops[ev.shiftKey ? stops.length - 1 : 0].focus(); }
}, true);

// --- ModTrap updates itself (MT58) -------------------------------------------------------------------------------------
// The version at the top is a button. It opens a box with a drop zone and "Add file": a ModTrap release file
// (ModTrap-<version>-win64.zip) given there is read by ModTrap's program, which says what version it is; one press
// then puts it in place and starts ModTrap again, and this page loads itself anew.
const SELF_NAME = /^ModTrap-\d[\d.]*-win64.*\.zip$/i;
async function selfUpdateBox(file) {
  if (state.selfBox) { if (file) selfTake(file); return; }
  let st = { version: state.version, can: false, why: "", name: "ModTrap-<version>-win64.zip" };
  try { st = await api("/api/selfupdate"); } catch (e) { st.why = e.message; }
  const pick = el("input", { type: "file", accept: ".zip" });
  const add = el("button", { type: "button", class: "primary", text: "Add file", disabled: !st.can });
  add.addEventListener("click", () => pick.click());
  pick.addEventListener("change", () => { if (pick.files && pick.files[0]) selfTake(pick.files[0]); pick.value = ""; });
  const zone = el("div", { class: "selfdrop" + (st.can ? "" : " off") }, el("b", { text: "Drop a ModTrap release file here" }),
    el("span", { class: "dim", text: st.name }), add, pick);
  const said = el("div", { class: "selfsaid" });
  const close = el("button", { type: "button", text: "Close" });
  const box = el("div", { class: "modal selfbox", role: "dialog", "aria-modal": "true" },
    el("p", {}, el("b", { text: "Update ModTrap" })),
    el("p", { text: "This is ModTrap " + st.version + ". Give it a newer release file and it puts that in place itself: the version in use is copied aside first, the new one is tried, and ModTrap starts again. Your sessions and settings stay as they are." }),
    zone, said, el("div", { class: "actions" }, close));
  const back = el("div", { class: "modal-back" }, box);
  const done = () => { if (state.selfBox && state.selfBox.busy) return; document.removeEventListener("keydown", key, true); back.remove(); state.selfBox = null; };
  const key = (ev) => { if (ev.key === "Escape" && document.querySelectorAll(".modal-back").length === 1) { ev.preventDefault(); ev.stopPropagation(); done(); } };
  close.addEventListener("click", done);
  back.addEventListener("mousedown", (ev) => { if (ev.target === back) done(); });
  document.addEventListener("keydown", key, true);
  document.body.append(back);
  state.selfBox = { said, zone, add, close, busy: false, st };
  if (!st.can) said.replaceChildren(el("p", { class: "would-needs", text: st.why || "This ModTrap cannot update itself." }));
  (st.can ? add : close).focus();
  if (file) selfTake(file);
}
function selfTake(file) {
  const b = state.selfBox;
  if (!b || b.busy) return;
  if (!b.st.can) return;
  b.busy = true;
  b.add.disabled = true;
  b.said.replaceChildren(el("p", { class: "dim" }, el("span", { class: "spinner small" }), " Reading “" + file.name + "”…"));
  const x = new XMLHttpRequest();
  x.open("POST", "/api/selfupdate/upload?name=" + encodeURIComponent(file.name));
  x.setRequestHeader("X-ModTrap-Token", TOKEN);
  x.setRequestHeader("Content-Type", "application/octet-stream");
  const fail = (text) => { b.busy = false; b.add.disabled = false; b.said.replaceChildren(el("p", { class: "would-needs", text })); };
  x.onerror = () => fail("The file did not reach ModTrap.");
  x.onload = () => {
    let d = {};
    try { d = JSON.parse(x.responseText); } catch (e) { /* no answer to read */ }
    if (x.status !== 200) return fail(d.error || (x.status === 413 ? "That file is larger than a ModTrap release file can be." : "The file was not accepted (" + x.status + ")."));
    b.busy = false;
    b.add.disabled = false;
    const go = el("button", { type: "button", class: "primary", text: d.order > 0 ? "Update to " + d.version : d.order < 0 ? "Go back to " + d.version : "Put " + d.version + " in place again" });
    go.addEventListener("click", () => selfApply(d, go));
    b.said.replaceChildren(el("p", {}, el("b", { text: "This file is ModTrap " + d.version + ". " }),
      d.order > 0 ? "It is newer than the one in use (" + d.current + ")." : d.order < 0 ? "It is older than the one in use (" + d.current + ")." : "That is the version in use.",
      d.python ? " It has a Python of its own inside; the Python ModTrap runs on now is kept." : ""),
      el("div", { class: "actions" }, go));
    go.focus();
  };
  x.send(file);
}
async function selfApply(d, go) {
  const b = state.selfBox;
  if (!b || b.busy) return;
  b.busy = true;
  go.disabled = b.add.disabled = b.close.disabled = true;
  b.said.replaceChildren(el("p", { class: "dim" }, el("span", { class: "spinner small" }), " Putting ModTrap " + d.version + " in place: copying the version in use aside, writing the new files, trying the new version…"));
  let done;
  try { done = await call("/api/selfupdate/apply", { id: d.id }); }
  catch (e) {
    b.busy = false;
    b.add.disabled = b.close.disabled = false;
    b.said.replaceChildren(el("p", { class: "would-needs", text: e.message }));
    return;
  }
  // The new ModTrap is starting and takes over from this one. This page waits for it, then loads itself anew.
  state.selfRestart = true;
  b.said.replaceChildren(el("p", {}, el("span", { class: "spinner small" }), " ModTrap " + done.version + " is in place and starting. This page loads itself anew as soon as it answers…"));
  for (let i = 0; i < 120; i++) {
    await sleep(1000);
    try {
      const r = await fetch("/", { cache: "no-store" });
      const m = r.ok ? /data-token="([^"]+)"/.exec(await r.text()) : null;
      if (m && m[1] !== TOKEN) { window.removeEventListener("beforeunload", siteGuard); location.reload(); return; }
    } catch (e) { /* between the two: nobody answers yet */ }
  }
  b.busy = false;
  b.close.disabled = false;
  b.said.replaceChildren(el("p", { class: "would-needs", text: "ModTrap " + done.version + " is in place but has not answered. Start ModTrap.exe again; if it does not start, the version before is kept in ModTrap's own folder, under updates." }));
}
$("version").addEventListener("click", () => selfUpdateBox());

// --- the split view (MT59): the mods and the plugins side by side ---------------------------------------------------
// One tab of the Modlist section shows both lists at once, each as it is on its own tab: the same rows, ticks,
// drags and menus. The line between them is dragged sideways to give one side more room. As in MO2's two panes, a
// mod looked at marks its plugins on the other side, and a plugin looked at marks its mod.
const onMods = () => state.tab === "mods" || state.tab === "split";
const onPlugins = () => state.tab === "plugins" || state.tab === "split";
function splitSet(pct) {
  const left = $("tab-mods");
  if (state.tab !== "split") { left.style.flex = ""; return; }
  state.splitAt = Math.max(15, Math.min(85, Math.round(pct * 10) / 10));
  left.style.flex = "0 0 calc(" + state.splitAt + "% - 5px)";
  $("split-bar").setAttribute("aria-valuenow", String(Math.round(state.splitAt)));
}
function linkPlugins(mod, scroll) {
  let first = null;
  for (const p of state.plugins || []) {
    if (!p.row) continue;
    const on = state.tab === "split" && !!mod && p.mod === mod;
    p.row.classList.toggle("linked", on);
    if (on && !first && !p.row.hidden) first = p.row;
  }
  if (first && scroll) first.scrollIntoView({ block: "nearest" });
}
function linkMod(plugin, scroll) {
  const p = plugin ? (state.plugins || []).find((x) => x.name === plugin) : null;
  const want = state.tab === "split" && p ? p.mod : "";
  let row = null;
  for (const g of state.groups || []) for (const m of g.mods) if (m.row) { const on = !!want && m.name === want; m.row.classList.toggle("linked", on); if (on && !m.row.hidden) row = m.row; }
  if (row && scroll) row.scrollIntoView({ block: "nearest" });
}
$("split-bar").addEventListener("mousedown", (ev) => {
  if (ev.button !== 0) return;
  ev.preventDefault();
  state.splitting = true;
  document.body.classList.add("splitting");
});
document.addEventListener("mousemove", (ev) => {
  if (!state.splitting) return;
  const r = $("split-bar").parentNode.getBoundingClientRect();
  if (r.width > 0) { const fromLeft = 100 * (ev.clientX - r.left) / r.width; splitSet(state.splitSwap ? 100 - fromLeft : fromLeft); }      // the share kept is the mods' side's
});
document.addEventListener("mouseup", () => {
  if (!state.splitting) return;
  state.splitting = false;
  document.body.classList.remove("splitting");
  saveUi();
});
$("split-bar").addEventListener("dblclick", () => { splitSet(50); saveUi(); });
// "Swap sides": the plugins to the left and the mods to the right, or back. Each list keeps the room it had, so the
// line moves to the mirrored place. Kept with the session, as the line's place is.
function swapSet(on) {
  state.splitSwap = !!on;
  const b = $("split-swap"), split = state.tab === "split";
  b.hidden = !split;
  b.setAttribute("aria-pressed", state.splitSwap ? "true" : "false");
  b.title = "Swaps the two sides of the split view. Now: " + (state.splitSwap ? "plugins on the left, mods on the right" : "mods on the left, plugins on the right") + ".";
  $("split-bar").parentNode.classList.toggle("swapped", split && state.splitSwap);
}
$("split-swap").addEventListener("click", () => { swapSet(!state.splitSwap); saveUi(); });
$("split-bar").addEventListener("keydown", (ev) => {
  if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") return;
  ev.preventDefault();
  splitSet((state.splitAt || 50) + ((ev.key === "ArrowLeft") !== !!state.splitSwap ? -2 : 2));        // the line goes where the arrow points
  saveUi();
});

// --- columns the owner sets: their widths and their order (MT61, MT62) --------------------------------------------
// Every table with a heading row has a thin line at the right edge of each heading, the last one too, and the same
// thin lines between the columns down its rows. A line held and moved sideways sets the width of the column on its
// left, exactly as far as the pointer goes: the columns to its right keep their widths and move along. While it is
// held, the line glows from the heading down through the rows. A heading held and moved sideways takes its whole
// column to another place; the first columns of a table (the tick, the priority or position, the name) stay.
// A double-click on a line gives the table its own widths and order back. All of it is kept with the session, for
// each kind of table.
const COL_MIN = 28;
const COL_FIXED = { "mods-table": 3, "plugins-table": 4 };          // the columns that keep their place; any other table: 2
function colKey(table) {
  return table.id || "t:" + [...table.tHead.rows[0].cells].map((th) => th.childNodes[0] && th.childNodes[0].nodeType === 3 ? th.childNodes[0].textContent.trim() : th.textContent.trim()).join("|").slice(0, 120);
}
const colOf = (cell) => Number(cell.dataset.c);
const colShown = (th) => getComputedStyle(th).display !== "none";
// Each cell is marked with the column it was drawn in (its number, and a class "k" + number): a column that was
// moved is still known for what it is, to the sorting, to the widths, and to the split view, which leaves some out.
function colTag(table) {
  const head = table.tHead.rows[0], n = head.cells.length;
  if (!head.dataset.o) { [...head.cells].forEach((th, i) => { th.dataset.c = String(i); th.classList.add("k" + i); }); head.dataset.o = "1"; }
  for (const body of table.tBodies) for (const row of body.rows) {
    if (row.dataset.o || row.cells.length !== n) continue;
    for (let i = 0; i < n; i++) { const td = row.cells[i]; td.dataset.c = String(i); td.classList.add("k" + i); }
    row.dataset.o = "1";
  }
}
function colSaved(table) { return (state.cols || {})[table.dataset.colKey] || null; }
function colOrderOf(table) {
  const n = table.tHead.rows[0].cells.length, fixed = Math.min(n, COL_FIXED[table.id] || 2);
  const saved = colSaved(table), order = saved && Array.isArray(saved.order) ? saved.order.map(Number) : null;
  const own = [...Array(n).keys()];
  if (!order || order.length !== n || [...order].sort((x, y) => x - y).some((v, i) => v !== i) || order.slice(0, fixed).some((v, i) => v !== i)) return own;
  return order;
}
function colOrder(table) {
  const order = colOrderOf(table), n = order.length;
  const rows = [table.tHead.rows[0]];
  for (const body of table.tBodies) for (const row of body.rows) if (row.dataset.o && row.cells.length === n) rows.push(row);
  for (const row of rows) {
    let same = true;
    for (let j = 0; j < n; j++) if (colOf(row.cells[j]) !== order[j]) { same = false; break; }
    if (same) continue;
    const by = {};
    for (const cell of row.cells) by[colOf(cell)] = cell;
    for (let j = 0; j < n; j++) row.append(by[order[j]]);
  }
}
function colWidths(table) {
  const saved = colSaved(table), ths = [...table.tHead.rows[0].cells];
  const sized = !!saved && ths.some((th) => Number.isFinite(Number(saved[colOf(th)])));
  if (!sized) {
    if (table.classList.contains("colfixed")) { table.classList.remove("colfixed"); table.style.width = ""; for (const th of ths) th.style.width = ""; }
    return;
  }
  let sum = 0;
  for (const th of ths) {
    const w = Math.max(COL_MIN, Number(saved[colOf(th)]) || (colOf(th) === ths.length - 1 && Number(saved.rest)) || 120);     // a column not seen when the widths were set
    th.style.width = w + "px";
    if (colShown(th)) sum += w;
  }
  table.classList.add("colfixed");
  table.style.width = sum + "px";                           // the table is as wide as its columns: no column takes "the rest"
}
function colApply(table) { colTag(table); colOrder(table); colWidths(table); }
function colSetup(table) {
  if (!table.tHead || !table.tHead.rows[0] || table.tHead.rows[0].cells.length < 2) return;
  table.dataset.colKey = colKey(table);
  table.classList.add("cols");
  colTag(table);
  for (const th of table.tHead.rows[0].cells) {
    if (th.querySelector(":scope > .colgrip")) continue;
    const grip = el("span", { class: "colgrip", role: "separator", "aria-orientation": "vertical", title: "Hold and move sideways to set this column's width; double-click to give the table its own widths and order back" });
    grip.addEventListener("mousedown", (ev) => {
      if (ev.button !== 0) return;
      ev.preventDefault();
      ev.stopPropagation();
      const key = table.dataset.colKey;
      const saved = Object.assign({}, (state.cols || {})[key]);
      const all = [...table.tHead.rows[0].cells];
      if (!all.some((x) => Number.isFinite(Number(saved[colOf(x)])))) {     // the widths as they are now are fixed first: only this column changes
        for (const x of all) saved[colOf(x)] = colShown(x) ? Math.round(x.getBoundingClientRect().width) : 120;
        state.cols = Object.assign({}, state.cols, { [key]: saved });
        colWidths(table);
      }
      state.colDrag = { key, c: colOf(th), x: ev.clientX, w: th.getBoundingClientRect().width };
      document.body.classList.add("colsizing");
      colGuide(table, colOf(th));
    });
    grip.addEventListener("click", (ev) => ev.stopPropagation());          // a press on the line is not a press on the heading (which sorts)
    grip.addEventListener("dblclick", (ev) => {
      ev.stopPropagation();
      if (state.cols) delete state.cols[table.dataset.colKey];
      colApply(table);
      saveUi();
    });
    th.append(grip);
    th.addEventListener("mousedown", (ev) => {              // a heading held and moved takes its column along (MT62)
      if (ev.button !== 0 || ev.target.closest(".colgrip")) return;
      const n = table.tHead.rows[0].cells.length, fixed = Math.min(n, COL_FIXED[table.id] || 2);
      if (colOf(th) < fixed || n - fixed < 2) return;
      state.colMove = { table, key: table.dataset.colKey, c: colOf(th), x: ev.clientX, y: ev.clientY, going: false, to: null, label: (th.childNodes[0] && th.childNodes[0].textContent || "").trim() || "this column" };
    });
  }
  colApply(table);
}
function colSetupAll(again) {
  for (const t of document.querySelectorAll("main table")) if (t.tHead && (again || !t.dataset.colKey || t.tHead.querySelectorAll(".colgrip").length === 0 || !t.tHead.rows[0].dataset.o)) colSetup(t);
  else if (t.tHead && t.dataset.colKey) colApply(t);         // rows drawn anew in a table that stayed: marked, and put in the kept order
  if (state.colDrag) for (const t of document.querySelectorAll("main table")) if (t.dataset.colKey === state.colDrag.key && t.offsetParent !== null) colGuide(t, state.colDrag.c);
}
// The glowing line of a column being set, or of the place a moved column would take: from the heading down
// through the rows that are shown.
function colGuide(table, c, x) {
  let g = state.colGuideEl;
  if (!table) { if (g) g.remove(); state.colGuideEl = null; return; }
  if (!g) { g = state.colGuideEl = el("div", { class: "colguide" }); document.body.append(g); }
  const th = [...table.tHead.rows[0].cells].find((h) => colOf(h) === c), r = th.getBoundingClientRect();
  const pane = table.closest(".scroll"), pr = pane ? pane.getBoundingClientRect() : { top: 0, bottom: window.innerHeight, left: 0, right: window.innerWidth };
  const tr = table.getBoundingClientRect();
  const left = x === undefined ? r.right - 1 : x;
  g.hidden = left < pr.left - 1 || left > pr.right + 1;
  g.style.left = left + "px";
  g.style.top = Math.max(r.top, pr.top) + "px";
  g.style.height = Math.max(0, Math.min(tr.bottom, pr.bottom, window.innerHeight) - Math.max(r.top, pr.top)) + "px";
}
// The widths are kept by the kind of table, not by the table: a list that is drawn anew while a line is held
// (the Updater list does that as answers come in) goes on from the kept widths.
document.addEventListener("mousemove", (ev) => {
  const d = state.colDrag;
  if (d) {
    const saved = Object.assign({}, (state.cols || {})[d.key]);
    saved[d.c] = Math.max(COL_MIN, Math.round(d.w + ev.clientX - d.x));
    state.cols = Object.assign({}, state.cols, { [d.key]: saved });
    for (const t of document.querySelectorAll("main table")) if (t.dataset.colKey === d.key) { colWidths(t); if (t.offsetParent !== null) colGuide(t, d.c); }
    return;
  }
  const m = state.colMove;
  if (!m) return;
  if (!m.going) {
    if (Math.abs(ev.clientX - m.x) < 8) return;
    if (!m.table.isConnected) { state.colMove = null; return; }
    m.going = true;
    m.ghost = el("div", { class: "dragghost", text: m.label });
    document.body.append(m.ghost);
    document.body.classList.add("dragging-mod");
  }
  ev.preventDefault();
  m.ghost.style.left = (ev.clientX + 14) + "px";
  m.ghost.style.top = (ev.clientY + 12) + "px";
  // Where it would go: before the heading under the pointer's left half, after it under its right half; never
  // among the columns that keep their place.
  const heads = [...m.table.tHead.rows[0].cells].filter(colShown);
  const fixed = Math.min(m.table.tHead.rows[0].cells.length, COL_FIXED[m.table.id] || 2);
  let to = null;
  for (const h of heads) {
    const r = h.getBoundingClientRect();
    if (ev.clientX < r.left || ev.clientX > r.right || colOf(h) < fixed && !(colOf(h) === fixed - 1)) continue;
    const after = ev.clientX > r.left + r.width / 2 || colOf(h) < fixed;
    to = { c: colOf(h), after, x: after ? r.right - 1 : r.left };
  }
  const last = heads[heads.length - 1].getBoundingClientRect();
  if (!to && ev.clientX > last.right) to = { c: colOf(heads[heads.length - 1]), after: true, x: last.right - 1 };
  m.to = to && to.c !== m.c ? to : null;
  if (m.to) colGuide(m.table, m.to.c, m.to.x); else colGuide(null);
});
document.addEventListener("mouseup", () => {
  const d = state.colDrag, m = state.colMove;
  state.colDrag = state.colMove = null;
  if (d) {
    colGuide(null);
    document.body.classList.remove("colsizing");
    saveUi();
  }
  if (!m || !m.going) return;
  m.ghost.remove();
  document.body.classList.remove("dragging-mod");
  colGuide(null);
  state.dragged = Date.now();                              // the press that ends the move is not a press on the heading
  if (!m.to || !m.table.isConnected) return;
  const order = colOrderOf(m.table).filter((c) => c !== m.c);
  order.splice(order.indexOf(m.to.c) + (m.to.after ? 1 : 0), 0, m.c);
  state.cols = Object.assign({}, state.cols, { [m.key]: Object.assign({}, (state.cols || {})[m.key], { order }) });
  for (const t of document.querySelectorAll("main table")) if (t.dataset.colKey === m.key) colApply(t);
  saveUi();
});
document.addEventListener("keydown", (ev) => {
  if (ev.key !== "Escape" || !state.colMove) return;
  if (state.colMove.ghost) state.colMove.ghost.remove();
  document.body.classList.remove("dragging-mod");
  colGuide(null);
  state.colMove = null;
});
// Tables are drawn anew as the lists change: each new one gets its lines, its kept widths and its kept order.
{
  let wait = 0;
  new MutationObserver(() => { clearTimeout(wait); wait = setTimeout(() => colSetupAll(false), 60); }).observe(document.querySelector("main"), { childList: true, subtree: true });
}

// --- the Plugins tab -------------------------------------------------------------------------------------------------

// The Plugins tab as MO2's own list (MT58): the box is the plugin's state, a row is moved by dragging it, and what is
// wrong with a plugin, or what it overwrites, shows as a symbol on its row; a press on the symbol tells it in the pane.
function pluginIssues(p) {
  const out = [];
  if (!p.active) return out;                       // the game does not load it: nothing of it can go wrong
  if (p.unreadable) out.push(p.mod ? "it could not be read: " + p.unreadable : "it is active, but no enabled mod holds its file");
  for (const x of p.missing || []) out.push("its master " + x + " is missing");
  for (const x of p.inactive || []) out.push("its master " + x + " is not active");
  for (const x of p.early || []) out.push("it loads before its master " + x);
  return out;
}
function pluginMarks(p) {
  const cell = p.marks;
  if (!cell) return;
  const kids = [];
  const mark = (cls, text, title) => { const b = el("button", { type: "button", class: "rowmark " + cls, text, title, "aria-label": title }); b.addEventListener("click", (ev) => { ev.stopPropagation(); showPlugin(p.name, p.row); }); kids.push(b); };
  if (p.issues.length) mark("bad", "⚠", plural(p.issues.length, "issue") + ": " + p.issues.join("; ") + ". Press for the details.");
  const sc = (state.pscan || {})[p.name];
  if (sc && sc.going) kids.push(el("span", { class: "spinner small", title: "Looking through the load order for what it overwrites…" }));
  else if (sc && sc.data) {
    const sum = (list) => list.reduce((a, x) => a + x.records, 0);
    const over = sc.data.overwrites, under = sc.data.overwritten_by;
    if (over.length || under.length) mark("warn", "⇄", [over.length ? "it overwrites what " + plural(over.length, "plugin") + " before it changed (" + plural(sum(over), "record") + ")" : "",
      under.length ? plural(under.length, "plugin") + " after it overwrite" + (under.length === 1 ? "s" : "") + " what it changes (" + plural(sum(under), "record") + ")" : ""].filter(Boolean).join("; ") + ". Press for the details.");
    else if (!sc.data.problems.length) mark("good", "✓", "Scanned: no other active plugin changes the same records.");
  }
  cell.replaceChildren(...kids);
}
function renderPlugins() {
  const body = $("plugins-table").tBodies[0];
  const frag = document.createDocumentFragment();
  for (const p of state.plugins) {
    const name = el("td", {}, p.name);
    if (!p.active) name.append(el("span", { class: "tag", text: "not active" }));
    if (p.primary) name.append(el("span", { class: "tag", text: "game" }));
    if (p.unreadable) name.append(el("span", { class: "tag " + (p.active ? "bad" : ""), text: p.mod ? "unreadable" : "no file" }));
    p.issues = pluginIssues(p);
    const can = state.changes && !p.primary && (p.active || !!p.mod);
    const on = el("input", { type: "checkbox", disabled: !can, checked: !!p.active, "aria-label": "Activate " + p.name,
      title: p.primary ? "One of the game's own plugins: always active" : !state.changes ? NO_CHANGES : !p.mod && !p.active ? "No enabled mod holds its file: enable its mod first"
        : p.active ? "Active. Untick to deactivate the plugin" : "Not active. Tick to activate the plugin" });
    on.addEventListener("change", () => pluginSet([p.name], on.checked, on));
    on.addEventListener("click", (ev) => ev.stopPropagation());
    p.marks = el("td", { class: "c-mark" });
    const mod = p.mod === "<game>" ? "the game" : p.mod === "<overwrite>" ? "Overwrite" : p.mod;
    const tr = el("tr", { class: "clickable" + (p.active ? "" : " off") },
      el("td", { class: "c-tick" }, on), el("td", { class: "c-num", text: p.position == null ? "" : p.position }), p.marks, name, el("td", { text: p.kind }),
      el("td", { text: mod }), el("td", { class: "c-num", text: p.mod_priority == null || p.mod_priority < 0 ? "" : p.mod_priority }),
      el("td", { class: "c-num", text: p.masters }), el("td", { class: "c-num" + (p.dependants ? " badnum" : ""), text: p.dependants }));
    tr.addEventListener("click", () => { showPlugin(p.name, tr); linkMod(p.name, true); });
    tr.dataset.plugin = p.name;
    p.row = tr;
    p.hay = fold(p.name + " " + p.mod);
    pluginMarks(p);
    frag.append(tr);
  }
  body.replaceChildren(frag);
  colSetup($("plugins-table"));
  filterPlugins();
}

// Activates or deactivates plugins, as their tick in MO2 does. Nothing is asked: what follows is told, and shows on the rows.
function pluginSet(names, on, box) {
  const put = (v) => { if (box) box.checked = v; };
  if (!state.changes) { put(!on); toast(NO_CHANGES); return; }
  listDo(async () => {
    try {
      if (!await mo2Closed()) { put(!on); return; }
      const got = await api("/api/list/plugins/set", { plugins: names, on });
      if (got.nothing) return;
      listChanged(got.text + "." + (got.lacking ? " " + plural(got.lacking, "active plugin") + " now lack" + (got.lacking === 1 ? "s" : "") + " a master (" + got.lack.slice(0, 3).join(", ") + (got.lacking > 3 ? ", …" : "") + "): see ⚠ on their rows." : ""));
      if (on && names.length === 1 && (state.settings || {}).scan_on_enable !== false) state.scanTimer = setTimeout(() => scanPlugin(names[0]), 1200);
    } catch (e) { put(!on); toast(e.message); }
  });
}
// What one plugin overwrites, for its row's symbol and its pane. Asked for in the pane, and by itself after a plugin
// is moved or activated.
async function scanPlugin(name) {
  state.pscan = state.pscan || {};
  const mine = state.pscan[name] = { going: true };
  const paint = () => { const p = state.plugins.find((x) => x.name === name); if (p) pluginMarks(p); if (state.plugin === name && onPlugins()) showPlugin(name, p && p.row); };
  paint();
  for (let i = 0; i < 300; i++) {
    let s;
    try { s = await api("/api/state"); } catch (e) { break; }
    if (s.status !== "reading") break;
    await sleep(200);
  }
  let d = null, error = "";
  try { d = await api("/api/list/scan", { plugin: name }); } catch (e) { error = e.message; }
  if ((state.pscan || {})[name] !== mine) return;          // the order changed meanwhile: this answer is of the old one
  state.pscan[name] = d && d.plugins[0] ? { data: Object.assign(d.plugins[0], { cut: d.plugins[0].cut || d.cut }) } : { error: error || "no answer" };
  paint();
}

// Dragging a plugin to another place in the load order. MO2's own limits are kept by ModTrap's program: a plugin
// let go where it may not stand comes to stand at the nearest place it may, and the page says why.
let pdrag = null;
function pdragEnd() {
  if (!pdrag) return;
  clearInterval(pdrag.timer);
  if (pdrag.ghost) pdrag.ghost.remove();
  pdrag.tr.classList.remove("drag-src");
  document.body.classList.remove("dragging-mod");
  placeLine(null);
  pdrag = null;
}
$("plugins-table").addEventListener("mousedown", (ev) => {
  if (ev.button !== 0 || !state.changes || ev.target.closest("input, button")) return;
  const tr = ev.target.closest("#plugins-table tbody tr");
  const p = tr ? state.plugins.find((x) => x.name === tr.dataset.plugin) : null;
  if (p && p.position != null && !p.primary) pdrag = { tr, name: p.name, x: ev.clientX, y: ev.clientY, going: false, at: null,
    listed: state.plugins.filter((x) => x.position != null).map((x) => x.name) };
});
document.addEventListener("mousemove", (ev) => {
  if (!pdrag) return;
  if (!pdrag.going) {
    if (Math.abs(ev.clientX - pdrag.x) + Math.abs(ev.clientY - pdrag.y) < 7) return;
    pdrag.going = true;
    pdrag.ghost = el("div", { class: "dragghost", text: pdrag.name });
    document.body.append(pdrag.ghost);
    document.body.classList.add("dragging-mod");
    pdrag.tr.classList.add("drag-src");
    const sel = window.getSelection && window.getSelection();
    if (sel) sel.removeAllRanges();
    const pane = $("plugins-table").closest(".scroll");
    pdrag.timer = setInterval(() => {
      if (!pdrag || !pane || pdrag.py == null) return;
      const r = pane.getBoundingClientRect();
      const d = pdrag.py < r.top + 36 ? -1 : pdrag.py > r.bottom - 36 ? 1 : 0;
      if (d) pane.scrollTop += d * 26;
    }, 40);
  }
  ev.preventDefault();
  pdrag.py = ev.clientY;
  pdrag.ghost.style.left = (ev.clientX + 14) + "px";
  pdrag.ghost.style.top = (ev.clientY + 12) + "px";
  const tr = ev.target.closest ? ev.target.closest("#plugins-table tbody tr") : null;
  let at = null;
  if (tr && !tr.hidden) {
    const r = tr.getBoundingClientRect(), below = ev.clientY > r.top + r.height / 2;
    const i = pdrag.listed.indexOf(tr.dataset.plugin);
    if (i >= 0) {                                          // below a row: right after it in the load order, whatever is filtered away
      const before = below ? (i + 1 < pdrag.listed.length ? pdrag.listed[i + 1] : "") : pdrag.listed[i];
      const mine = pdrag.listed.indexOf(pdrag.name);
      if (before !== pdrag.name && before !== (mine + 1 < pdrag.listed.length ? pdrag.listed[mine + 1] : "")) at = { tr, below, before };
    }
  }
  pdrag.at = at;
  placeLine(at ? at.tr : null, at && at.below);
});
document.addEventListener("mouseup", () => {
  if (!pdrag) return;
  const d = pdrag, went = pdrag.going;
  pdragEnd();
  if (!went) return;
  state.dragged = Date.now();
  if (!d.at) return;
  listDo(async () => {
    try {
      const got = await api("/api/list/plugins/move", { plugin: d.name, before: d.at.before });
      if (got.nothing) { toast(got.why ? d.name + " stays where it is: " + got.why + "." : d.name + " is there already."); return; }
      listChanged(got.text + "." + (got.why ? " Not where you let go: " + got.why + "." : ""));
      if ((state.settings || {}).scan_on_enable !== false) state.scanTimer = setTimeout(() => scanPlugin(d.name), 1200);
    } catch (e) { toast(e.message); }
  });
});
document.addEventListener("keydown", (ev) => { if (pdrag && ev.key === "Escape") pdragEnd(); });
window.addEventListener("blur", pdragEnd);
$("plugins-undo").addEventListener("click", listUndo);

function filterPlugins() {
  const typed = $("plugins-search").value.trim();
  const star = starNumber(typed);                        // *138: the plugin at position 138 of the load order (MT60)
  const q = star === null ? fold(typed) : "";
  const pr = $("p-problems").checked, dp = $("p-deps").checked;
  let shown = 0, target = null;
  const found = [];
  for (const p of state.plugins) {
    const ok = (!q || p.hay.includes(q)) && (!pr || p.issues.length || p.unreadable) && (!dp || p.dependants > 0);
    p.row.hidden = !ok;
    if (ok) shown++;
    if (ok && q) found.push(p.row);
    if (Number.isFinite(star) && p.position === star) target = p;
  }
  $("plugins-shown").textContent = (q || pr || dp) ? shown + " of " + state.plugins.length + " shown" : state.plugins.length + " plugins";
  $("plugins-empty").hidden = shown > 0;
  const there = target && !target.row.hidden ? target.row : null;
  markFound("plugins", found, there, "*" + star);
  if (star !== null) $("plugins-shown").textContent = !Number.isFinite(star) ? "a star and a number, like *138, goes to that position"
    : there ? "position " + star + ": " + target.name : target ? "position " + star + " (" + target.name + ") is not shown: the filters hide it" : "no plugin is at position " + star;
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
  if (!onPlugins()) showTab("plugins");
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
    ...pluginPane(name),
    ...list("Masters", p.masters, p), ...list("Needed by", p.dependants)].filter(Boolean));
}

// A plugin's pane, the part of MT58: what is wrong with it (the row's ⚠), and what it overwrites (the row's ⇄).
function pluginPane(name) {
  const row = state.plugins.find((x) => x.name === name);
  const out = [];
  if (row && row.issues.length) out.push(el("h3", { text: plural(row.issues.length, "issue") }), el("ul", { class: "findings" }, ...row.issues.map((x) => el("li", { class: "bad", text: x }))));
  const sc = (state.pscan || {})[name];
  const scan = el("button", { type: "button", text: sc && sc.data ? "Scan again" : "Scan what it overwrites", disabled: !!(sc && sc.going) || !row || row.position == null,
    title: "Looks through the load order for the plugins that change the same records: the ones before it, whose change it overwrites, and the ones after it, which overwrite its own. It only reads." });
  scan.addEventListener("click", () => scanPlugin(name));
  out.push(el("div", { class: "actions" }, scan));
  if (sc && sc.going) out.push(el("p", { class: "dim" }, el("span", { class: "spinner small" }), " Looking through the load order…"));
  else if (sc && sc.error) out.push(el("p", { class: "would-needs", text: "The scan did not run: " + sc.error }));
  else if (sc && sc.data) out.push(el("div", { class: "scan" }, ...scanPluginParts(sc.data, false).filter(Boolean)));
  return out;
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
    const go = el("button", { type: "button", text: "Go to Pick mods" });
    go.addEventListener("click", () => showTab("pick"));
    box.replaceChildren(el("div", { class: "card" }, el("h2", { text: "Nothing is ticked yet" }),
      el("p", { class: "dim", text: "Tick the mods you want to take out on Pick mods. This tab then shows every plugin that depends on them, and from here you start the dry run. Tip: “Has dependants” there shows the mods that cannot simply be disabled." }), go));
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
      el("p", { class: "dim", text: "Tick the mods you want to take out on Pick mods. This tab then lists every step that takes: what ModTrap does, what is yours to do, and which steps the modlist's own files already show as done." })));
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

// --- the Install mods tab (MT21, DESIGN§16) ------------------------------------------------------------------------------

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

function sendArchive(file, updates) {
  const up = { name: file.name, pct: 0 };
  state.uploads = (state.uploads || []).concat(up);
  renderAddPicked();
  return new Promise((resolve, reject) => {
    const x = new XMLHttpRequest();
    x.open("POST", "/api/add/upload?name=" + encodeURIComponent(file.name) + (updates ? "&updates=" + encodeURIComponent(updates) : ""));
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
        // A dropped mod is installed by itself as soon as it is unpacked and read (MT54; a setting, on).
        state.autoInstall = { ids: ((state.autoInstall || {}).ids || []).concat(rec.id), since: Date.now() };
        added++;
        renderAddPicked();
        saveUi();
      } catch (e) { notes.push({ name: it.name, bad: true, text: "Not taken in: " + e.message + "." }); }
    }
    state.addNotes = notes;
    state.addText = "";
    if (added) toast(state.autoInstall && (state.settings || {}).install_on_drop && state.changes
      ? ((state.settings || {}).manual_placement ? "Taken in. ModTrap unpacks it, then takes you to the Mods tab to choose its place." : "Taken in. ModTrap unpacks it and installs it by itself.")
      : plural(added, "mod") + " put on the list."); else if (!notes.length) toast("Already on the list.");
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
  const where = x.updates ? "right after “" + x.updates + "”, the version it is newer than, in MO2's list" + (x.updates_enabled ? "; “" + x.updates + "” is disabled when this one is added, not deleted, and enabled again by Revert" : " (which is disabled already)")
    : place.before ? "directly before “" + place.before + "” in MO2's list" : "last in MO2's list (the highest priority)";
  const plugs = x.plugins.map((p) => {
    if (p.unreadable) return el("div", { class: "plug" }, el("p", {}, el("span", { class: "mono", text: p.name }), el("span", { class: "tag bad", text: "could not be read" })), el("p", { class: "dim", text: p.unreadable }));
    const pr = p.proposed;
    const bad = p.masters.filter((m) => m.state !== "active" && m.state !== "comes along");
    return el("div", { class: "plug" },
      el("p", {}, p.active ? pluginLink(p.name) : el("span", { class: "mono", text: p.name }), el("span", { class: "tag", text: p.kind }),
        el("span", { class: "tag " + (p.active || p.keeps ? "good" : ""), text: p.active ? "active, position " + p.position : p.keeps ? "keeps the older version's place, position " + p.keeps.position + (p.keeps.active ? "" : " (not active there)") : "not active yet" })),
      p.active || p.keeps ? null : el("p", {}, "Goes " + (pr.before ? "directly before " : "at the end of the load order"), pr.before ? pluginLink(pr.before) : null,
        el("span", { class: "dim", text: "  (" + pr.why + ")" })),
      el("p", { class: "dim" }, "Masters: " + (p.masters.length ? p.masters.map((m) => m.name).join(", ") : "none"),
        bad.length ? el("span", { class: "tag bad", text: plural(bad.length, "master") + " not ready" }) : p.masters.length ? el("span", { class: "tag good", text: "all there" }) : null),
      ...bad.map((m) => el("p", { class: "would-needs", text: m.name + ": " + (m.state === "missing" ? "no mod in this MO2 has it" : m.state === "inactive" ? "in the modlist, not active" : "in a disabled mod: " + m.mods.join(" or ")) })),
      p.replaces && p.replaces.mod !== x.updates ? el("p", { class: "would-needs" }, "Another mod has a plugin of this name: ", modLink(p.replaces.mod), ". This mod's copy would be the one used; " + plural(p.replaces.dependants, "plugin") + " name it as a master.") : null,
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

// "Install mod" (DESIGN§16.8): the plan first, then the go-ahead; and the adds already carried out, with Revert.
const addBody = () => ({ mods: (state.adding || []).slice(), staged: (state.staged || []).slice() });

async function askAddPlan() {
  try { state.addPlan = await api("/api/add/plan", addBody()); state.addPlanError = ""; }
  catch (e) { state.addPlan = null; state.addPlanError = e.message; }
  state.addText = "";
  pollAdd(true);
}

// A dropped mod installs by itself (MT54): once it is unpacked and read, and nothing in it is the owner's to answer,
// ModTrap goes on as "Install mod" would; with "Always place a new mod by hand" it goes to the choosing of the place.
// It waits while an installer's questions are open, and gives up, saying why, where something the mod needs is missing.
function autoInstallStep(d) {
  const a = state.autoInstall;
  if (!a || state.addBusy || state.placing) return;
  const stop = (why) => { state.autoInstall = null; if (why) toast("Not installed by itself: " + why + ". “Install mod”, at the top, installs it once that is settled."); };
  if (!(state.settings || {}).install_on_drop || !state.changes) return stop("");
  if (Date.now() - a.since > 30 * 60 * 1000) return stop("it took too long to get ready");
  if ((d.gone || []).some((id) => a.ids.includes(id))) return stop("the archive could not be unpacked");
  const recs = (d.staged || []).filter((r) => a.ids.includes(r.id));
  if (recs.length < a.ids.length || d.looking || d.unpacking || recs.some((r) => r.state === "copying" || r.state === "unpacking")) return;      // not ready yet
  const bad = recs.find((r) => r.state === "failed");
  if (bad) return stop(bad.note || "the archive could not be read");
  if (recs.some((r) => r.state !== "ready")) {            // an installer asks which parts to install: ModTrap waits for the answers
    if (!a.told) { a.told = true; toast("This mod asks which parts to install. Answer its questions below: ModTrap installs it as soon as you have."); }
    return;
  }
  if (!(d.mods || []).length) return;
  const needs = (d.steps || []).find((s) => s.key === "needs");
  if (needs && needs.state !== "done") return stop("something the mod needs is not there yet (see “Get what the mod needs”)");
  if (probeReason()) return stop(probeReason());
  if (!settled()) return;                                 // ModTrap is still reading or scanning
  state.autoInstall = null;
  if (chosenPlace()) installNow(chosenPlace().before); else if ((state.settings || {}).manual_placement && !d.update) startPlacement(); else installNow("");
}

// "Install mod" (MT53): one press copies the mod in, puts it in its place, enables it, activates its plugins and checks
// the result, as "Demaster Selected" does its work. `before`: a place the owner chose by hand ("Manual placement").
async function installNow(before) {
  const body = Object.assign(addBody(), before ? { before } : {});
  state.addBusy = true;
  state.addText = "";
  pollAdd(true);
  try {
    await api("/api/add/run", body);
    const names = Object.values(state.stagedInfo || {}).filter((r) => (state.staged || []).includes(r.id) && r.state === "ready").map((r) => r.name);
    toast("Installed. ModTrap is reading the modlist again.");
    state.addPlace = null;
    for (const n of names) if (!(state.adding || []).includes(n)) state.adding.push(n);
    state.addPlanError = "";
    saveUi();
  } catch (e) { state.addPlanError = e.message; }
  state.addBusy = false;
  state.addText = "";
  state.gen = (state.gen || 0) + 1;
  tick();
}
async function uninstallJob(job, what) {
  if (!await confirmBox("Uninstall " + what + "? ModTrap puts MO2's mod list and load order back as they were before this install and takes its copy of the mod out of MO2's mods folder. MO2 must be closed.")) return false;
  try {
    const r = await api("/api/add/revert", { job });
    for (const x of r.restored || []) {                // a dropped mod is back in ModTrap's work folder only
      state.adding = (state.adding || []).filter((n) => n !== x.name);
      if (!(state.staged || []).includes(x.id)) state.staged = (state.staged || []).concat(x.id);
    }
    renderAddPicked();
    saveUi();
    toast(r.left.length ? "Uninstalled. Left in place, because it changed since: " + r.left.join(", ") : "Uninstalled: the modlist is as it was before.");
    state.addPlanError = "";
  } catch (e) { state.addPlanError = e.message; toast(e.message); }
  state.addText = "";
  state.gen = (state.gen || 0) + 1;
  tick();
  return true;
}
function addActionCard(d) {
  const st = (k) => (d.steps || []).find((x) => x.key === k) || { state: "done" };
  const todo = ["install", "enable", "activate", "update"].some((k) => (d.steps || []).some((x) => x.key === k && x.state !== "done"));
  const kids = [];
  const manual = !!(state.settings || {}).manual_placement && !d.update;
  const blocked = !state.changes || !todo || st("needs").state !== "done" || d.looking || !!probeReason() || !!state.addBusy;
  const why = probeReason() ? "Not yet: " + probeReason() + "." : !state.changes ? "Switched off. ModTrap changes a modlist only when it is started with its switch for changes." :
    st("needs").state !== "done" ? "First get what the mod needs: see step “Get what the mod needs”." : !todo ? "There is nothing left for ModTrap to do here." : "";
  const b = el("button", { type: "button", class: "primary", text: state.addBusy ? "Installing…" : d.update ? "Update mod" : "Install mod", disabled: blocked });
  b.title = why || (manual ? "Your setting: you choose its place on the Mods tab first" : "One press: ModTrap copies the mod in, puts it in its place, enables it, activates its plugins and checks the result");
  const chosen = chosenPlace();
  b.addEventListener("click", () => { if (chosenPlace()) installNow(chosenPlace().before); else if (manual) startPlacement(); else installNow(""); });
  if (chosen) b.title = why || "One press: ModTrap installs the mod at the place you dropped it on the Modlist page";
  const place = el("button", { type: "button", text: "Manual placement…", disabled: blocked || !!d.update,
    title: d.update ? "An update takes the older version's place" : "Choose its place yourself: on the Mods tab, move over the list and click between two mods" });
  place.addEventListener("click", startPlacement);
  kids.push(el("div", { class: "actions" }, b, d.update ? null : place, probeButton(), el("span", { class: probeReason() ? "would-needs" : "dim", text: probeReason() ? "Not yet: " + probeReason() + "." : !state.changes ?
    "Switched off: ModTrap installs a mod only when it is started with its switch for changes." :
    d.update ? "An update of a mod you have: one press copies the newer version in, puts it right after the older one, disables the older one (it is not deleted) and checks the result. The plugins keep their places."
      : manual ? "Your setting: you choose the mod's place yourself. One press takes you to the Mods tab; a click between two mods there is the place."
      : "One press: ModTrap copies the mod in, puts it last (before what the modlist's tools made), enables it, activates its plugins and checks the result. What it overwrites there, and the tools that have to do with it, are told below. “Manual placement” puts it anywhere else." })),
    state.addPlanError ? el("p", { class: "would-needs", text: state.addPlanError }) : null);
  if (chosen) {
    // The place the mod was dropped at on the Modlist page (MT57): "Install mod" puts it there.
    const forget = el("button", { type: "button", text: "Forget this place", title: "“Install mod” then places the mod as it does without a chosen place" });
    forget.addEventListener("click", () => { state.addPlace = null; state.addText = ""; pollAdd(true); });
    kids.push(el("p", {}, el("span", { class: "tag good", text: "place chosen" }), " You dropped it on the Modlist page " + chosen.words + ": “Install mod” puts it there.  ", forget));
  }
  for (const j of (d.added || []).filter((x) => x.state === "added").slice(0, 12)) {
    const undo = el("button", { type: "button", text: "Uninstall" });
    undo.addEventListener("click", () => uninstallJob(j.job, j.mods.map((n) => "“" + n + "”").join(", ")));
    kids.push(el("p", {}, el("span", { class: "tag good", text: "installed by ModTrap" }),
      " " + j.when.replace("T", " ") + ": " + j.mods.join(", ") + (j.plugins.length ? "  (" + j.plugins.join(", ") + ")" : "") + "  ", state.changes ? undo : null));
  }
  return el("div", { class: "card" }, ...kids.filter(Boolean));
}

// --- Manual placement (MT53) ---------------------------------------------------------------------------------------
// The owner chooses the new mod's place on the Mods tab: a line shows between two rows as the pointer moves, a click
// is the place. ModTrap then says what the mod overwrites there and what overwrites it, and installs it there on OK.
function startPlacement() {
  const names = Object.values(state.stagedInfo || {}).filter((r) => (state.staged || []).includes(r.id)).map((r) => r.name).concat(state.adding || []);
  state.placing = { body: addBody(), label: names.join(", ") || "the mod" };
  $("mods-order").value = "mo2";
  $("mods-search").value = "";
  for (const id of ["f-enabled", "f-plugins", "f-deps"]) $(id).checked = false;
  state.collapsed = new Set();
  showTab("mods");
  layoutMods();
  const cancel = el("button", { type: "button", text: "Cancel" });
  cancel.addEventListener("click", () => { endPlacement(); showTab("add"); });
  const last = el("button", { type: "button", text: "Put it last of all" });
  last.addEventListener("click", () => placementChosen("*last*", "last of all in MO2's list, after what the tools made too"));
  const banner = $("place-banner");
  banner.replaceChildren(el("b", { text: "Placing “" + state.placing.label + "”. " }),
    el("span", { text: "Move the pointer over the list: the line shows where the mod would go. Click to choose that place; ModTrap then tells you what it overwrites there, and asks before installing. Esc cancels.  " }), last, " ", cancel);
  banner.hidden = false;
  document.body.classList.add("placing");
}
function endPlacement() {
  state.placing = null;
  $("place-banner").hidden = true;
  document.body.classList.remove("placing");
  placeLine(null);
}
function placeLine(tr, below) {
  for (const x of document.querySelectorAll("tr.place-above, tr.place-below")) x.classList.remove("place-above", "place-below");
  if (tr) tr.classList.add(below ? "place-below" : "place-above");
}
// The row under the pointer and whether the line is above or below it; and what the new mod would then stand before.
function placeAt(ev) {
  const tr = ev.target.closest ? ev.target.closest("#mods-table tbody tr") : null;
  if (!tr || tr.hidden) return null;
  const r = tr.getBoundingClientRect();
  const nameOf = (row) => row ? (row.dataset.sep || row.dataset.name || "") : "";
  const here = findMod(nameOf(tr));
  const below = ev.clientY > r.top + r.height / 2 || !!(here && here.kind === "game");      // nothing goes above the game's own files
  let target = tr;
  if (below) { target = tr.nextElementSibling; while (target && target.hidden) target = target.nextElementSibling; }
  const m = target ? findMod(nameOf(target)) : null;
  const before = !target || (m && !["mod", "separator", "foreign"].includes(m.kind)) ? "*last*" : nameOf(target);
  return { tr, below, before, after: nameOf(below ? tr : tr.previousElementSibling) };
}
// What the mods of an analysis overwrite at their place, and what overwrites them there, as lines for a box.
function placeLines(d) {
  const lines = [];
  for (const x of d.mods || []) {
    const lead = (d.mods || []).length > 1 ? x.name + ": " : "";
    const say = (wins, list) => {
      const n = list.reduce((a, c) => a + c.files, 0);
      lines.push(el("p", {}, el("b", { text: lead + (wins ? (n ? "There it overwrites " + plural(n, "file") + " of " + plural(list.length, "mod") + ":" : "There it overwrites nothing.")
        : (n ? "There " + plural(n, "file") + " of its own " + (n === 1 ? "is" : "are") + " overwritten, by " + plural(list.length, "mod") + ":" : "There nothing overwrites it.")) })));
      if (n) lines.push(moreList(list.map((c) => el("li", { title: (c.examples || []).join("\n") }, c.mod + ": " + plural(c.files, "file") + " (" + Object.entries(c.kinds).map(([k, v]) => v + " " + k).join(", ") + ")",
        c.notable.length ? el("span", { class: "tag warn", text: c.notable.join(", ") }) : null)), 14, 0, "place:" + x.name + ":" + (wins ? "w" : "l")));
    };
    say(true, x.wins);
    say(false, x.loses);
    for (const pl of x.plugins) lines.push(el("p", { class: "dim small", text: pl.name + (pl.active ? ": active already" : pl.proposed ? ": goes " + (pl.proposed.before ? "directly before " + pl.proposed.before : "at the end of the load order") + " (" + pl.proposed.why + ")" : "") }));
  }
  return lines;
}
async function placementChosen(before, words) {
  const p = state.placing;
  if (!p || p.asking) return;
  p.asking = true;
  const body = Object.assign({}, p.body, { before });
  let d;
  try {
    for (let i = 0; i < 240; i++) {                       // the same analysis as the Installer tool's, for this place
      d = await api("/api/add", body);
      if (!d.looking && !d.unpacking) break;
      await new Promise((r) => setTimeout(r, 400));
    }
  } catch (e) { p.asking = false; toast(e.message); return; }
  p.asking = false;
  if (!state.placing) return;
  const needs = (d.steps || []).find((x) => x.key === "needs");
  const lines = placeLines(d);
  const ok = el("button", { type: "button", class: "primary", text: "OK, install it there", disabled: !!(needs && needs.state !== "done") });
  const cancel = el("button", { type: "button", text: "Cancel" });
  const box = el("div", { class: "modal wide", role: "dialog", "aria-modal": "true" },
    el("p", {}, el("b", { text: "“" + p.label + "”: " + words })),
    needs && needs.state !== "done" ? el("p", { class: "would-needs", text: "Something the mod needs is not there yet: " + needs.items.map((i) => i.text).slice(0, 3).join(" ") }) : null,
    ...lines,
    el("p", { class: "dim small", text: "OK installs the mod at this place, whatever is listed above. Cancel lets you choose another place." }),
    el("div", { class: "actions" }, cancel, ok));
  const back = el("div", { class: "modal-back" }, box);
  const done = () => { document.removeEventListener("keydown", key, true); back.remove(); };
  const key = (ev) => { if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); done(); } };
  cancel.addEventListener("click", done);
  ok.addEventListener("click", () => { done(); endPlacement(); showTab("add"); installNow(before); });
  document.addEventListener("keydown", key, true);
  document.body.append(back);
  ok.focus();
}
$("mods-table").addEventListener("mousemove", (ev) => { if (!state.placing) return; const at = placeAt(ev); placeLine(at ? at.tr : null, at && at.below); });
$("mods-table").addEventListener("mouseleave", () => { if (state.placing) placeLine(null); });
$("mods-table").addEventListener("click", (ev) => {
  if (!state.placing) return;
  ev.preventDefault();
  ev.stopPropagation();
  const at = placeAt(ev);
  if (!at) return;
  placementChosen(at.before, at.before === "*last*" ? "last of all in MO2's list" : "right before “" + at.before.replace(/_separator$/i, "") + "”" + (at.after ? ", after “" + at.after.replace(/_separator$/i, "") + "”" : ""));
}, true);
document.addEventListener("keydown", (ev) => { if (state.placing && ev.key === "Escape" && !document.querySelector(".modal-back")) { endPlacement(); showTab("add"); } });

// --- Installed mods (MT53) -------------------------------------------------------------------------------------------
// The mods installed through ModTrap, laid out as the modlist's rows are: priority, mod, source, version, how it was
// installed, its update, and "Uninstall".
async function loadInstalled() {
  if (state.status !== "ready") return;
  let d;
  try {
    d = await api("/api/installed");
    if (!state.updates || state.updatesFor !== state.loaded) { state.updates = await api("/api/updates"); state.updatesFor = state.loaded; }
  } catch (e) { toast(e.message); return; }
  state.installed = d;
  const count = $("installed-count");
  count.hidden = !d.rows.length;
  count.textContent = String(d.rows.length);
  const up = new Map(((state.updates || {}).rows || []).map((r) => [r.mod, r]));
  $("installed-head").replaceChildren(el("div", { class: "card" }, el("h3", { text: "Installed mods" }),
    el("p", { class: "dim", text: "The mods ModTrap installed into this modlist that still stand, by priority (click a column's title to sort by it): new mods, and newer versions put in by the Updater. “Uninstall” puts MO2's lists back as they were before that install and takes ModTrap's copy of the mod out again; for a newer version, the older one is enabled as before." })));
  if (!d.rows.length) { $("installed-list").replaceChildren(el("div", { class: "card" }, el("p", { class: "dim", text: "ModTrap has installed nothing into this modlist yet. Drop a mod's archive on the Installer tool, or update a mod on the Updater list." }))); return; }
  const isort = state.instSort || { key: "priority", desc: false };
  const rank = { update: 0, maybe: 1, replaced: 2, current: 3, "not asked": 4, none: 5, gone: 6 };
  const of = (x) => up.get(x.mod) || {};
  const iby = { priority: (a, b) => (a.priority === null ? 1e9 : a.priority) - (b.priority === null ? 1e9 : b.priority), mod: (a, b) => naturally(a.mod, b.mod),
    from: (a, b) => naturally((of(a).host || "~") + " " + String(of(a).id || ""), (of(b).host || "~") + " " + String(of(b).id || "")),
    version: (a, b) => naturally(of(a).version || "", of(b).version || ""), when: (a, b) => naturally(a.when, b.when),
    update: (a, b) => (rank[of(a).state] === undefined ? 9 : rank[of(a).state]) - (rank[of(b).state] === undefined ? 9 : rank[of(b).state]) }[isort.key];
  const rows = [...d.rows].sort((a, b) => (isort.desc ? -iby(a, b) : iby(a, b)) || naturally(a.mod, b.mod));
  const table = el("table", { class: "grid uptable", id: "installed-table" },
    el("thead", {}, el("tr", {}, ...["Priority", "Mod", "From", "Version", "Installed", "Update", "", "What is known", ""].map((h) => el("th", { text: h })))),
    el("tbody", {}, ...rows.map((x) => {
      const r = up.get(x.mod);
      const un = el("button", { type: "button", text: "Uninstall", disabled: !d.changes, title: x.with.length ? "Installed together with " + x.with.join(", ") + ": they are uninstalled together" : "Puts the modlist back as it was before this install" });
      un.addEventListener("click", async () => { if (await uninstallJob(x.job, "“" + x.mod + "”" + (x.with.length ? " and " + x.with.map((n) => "“" + n + "”").join(", ") : ""))) setTimeout(loadInstalled, 1500); });
      const tr = el("tr", {},
        el("td", { class: "num", text: x.priority === null ? "" : String(x.priority) }),
        el("td", { class: "modname" }, r && r.fav ? el("span", { class: "upfav", title: "A favourite of yours", text: "★ " }) : null, /_separator$/i.test(x.mod) ? el("span", { text: x.mod.replace(/_separator$/i, "") }) : x.there ? modLink(x.mod) : el("span", { text: x.mod }),
          /_separator$/i.test(x.mod) ? el("span", { class: "tag", text: "separator" }) : x.there ? (x.enabled ? null : el("span", { class: "tag", text: "disabled" })) : el("span", { class: "tag warn", text: "no longer in the modlist" }),
          x.updates ? el("div", { class: "dim small", text: "a newer version of “" + x.updates + "”" }) : null,
          x.plugins.length ? el("div", { class: "dim small mono", text: x.plugins.slice(0, 4).join(", ") + (x.plugins.length > 4 ? " …" : "") }) : null),
        el("td", {}, r ? (UP_HOST[r.host] || "not known") + (r.id ? " " + r.id : "") : "", r && r.page ? el("div", {}, el("a", { href: r.page, target: "_blank", rel: "noopener noreferrer", text: "its page" })) : null),
        el("td", { text: r ? r.version || "" : "" }),
        el("td", { class: "small" }, x.when.replace("T", " "), x.archive ? el("div", { class: "dim mono", text: x.archive }) : null),
        el("td", { class: "upstate" }, r ? el("span", { class: "tag " + UP_STATE[r.state][1], text: UP_STATE[r.state][0] }) : null, r && r.newest ? el("div", { class: "small", text: r.newest + (r.when ? " · " + r.when : "") }) : null),
        el("td", { class: "c-get" }, r ? upGetButton(r) : null),
        el("td", { class: "small", text: r ? r.text : "" }),
        el("td", {}, un));
      tr.dataset.mod = x.mod;
      tr.addEventListener("contextmenu", (ev) => modMenu(ev, x.mod));
      return tr;
    })));
  sortHeads(table, ["priority", "mod", "from", "version", "when", "update", null, null, null], isort, (key) => { state.instSort = nextSort(isort, key); loadInstalled(); });
  $("installed-list").replaceChildren(el("div", { class: "card" }, table));
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
  // What ModTrap does itself is never shown as something "to do": it is ModTrap's, done when the mod is installed.
  const auto = !isDone && st.who === "ModTrap" && !!state.changes && !st.manual;
  const [word, cls] = ticked ? ["ticked off by you", "good"] : auto ? [state.addBusy ? "ModTrap is doing this…" : "ModTrap does this", state.addBusy ? "warn" : ""] : STEP_STATE[st.state] || [st.state, ""];
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
  state.addData = d;
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
  const mine = d.steps.filter((st) => st.who !== "ModTrap" && !["done", "not needed"].includes(st.state)).length;       // what is the owner's
  const ready = ["install", "enable", "activate", "update"].some((k) => d.steps.some((x) => x.key === k && x.state !== "done"));
  $("add-summary").textContent = state.addBusy ? "Installing…" : state.autoInstall ? "Installing by itself…" : mine ? plural(mine, "thing") + " for you to settle first"
    : ready ? (state.changes ? "Ready to install" : plural(open, "step") + " to go") : open ? plural(open, "step") + " to go" : "Installed: every step is done";
  const go = $("add-go");
  go.hidden = !(ready && state.changes) || !!state.addBusy;
  go.disabled = !!mine || !!d.looking || !!probeReason() || !!state.autoInstall;
  go.textContent = d.update ? "Update mod" : "Install mod";
  const s = d.slots;
  const room = el("p", { class: s.full.after > s.full.limit || s.light.after > s.light.limit ? "would-needs" : "dim",
    text: "Room in the load order: full plugins " + s.full.now + (s.full.after !== s.full.now ? " → " + s.full.after : "") + " of " + s.full.limit +
      ", light plugins " + s.light.now + (s.light.after !== s.light.now ? " → " + s.light.after : "") + " of " + s.light.limit + "." });
  box.replaceChildren(...[noteCard,
    el("div", { class: "card" }, el("p", { text: d.update ? "An update: a newer version of a mod you have. It takes the older one's place and nothing else of the modlist is judged anew; a new mod gets the full list of steps."
      : "What ModTrap can tell from the files; what is inside the plugins' records is read through xEdit in its own step. ModTrap checks every step against the modlist's files each time the modlist is read." }), room,
      d.cut ? el("p", { class: "would-needs", text: "The search for shared files was cut short: there may be more than is listed." }) : null,
      d.unknown && d.unknown.length ? el("p", { class: "would-needs", text: "No longer in MO2: " + d.unknown.join(", ") }) : null),
    toolCard(), addActionCard(d),
    ...askCards,
    ...d.mods.map((x) => addModCard(x, d.place, (d.staged || []).find((r) => r.installer && r.state === "ready" && r.name === x.name))),
    el("h2", { text: ready && state.changes ? "What ModTrap does when it installs the mod, in order" : "What was done, in order" }), ...cards].filter(Boolean));
}

async function autoAddStep(d) {
  const a = state.autoAdd;
  if (!a || state.autoAddBusy) return;
  const stop = (why) => { state.autoAdd = null; if (why) toast("“" + a.mod + "”: its newer version is on the Install mods list and waits for you: " + why + "."); };
  if (Date.now() - a.since > 15 * 60 * 1000) return stop("it took too long to get ready");
  if ((state.adding || []).length || (state.staged || []).length !== 1 || state.staged[0] !== a.staged) return stop("more than this one mod is on the list");
  const rec = (d.staged || []).find((r) => r.id === a.staged);
  if (d.gone && d.gone.includes(a.staged)) return stop("the file could not be unpacked");
  if (!rec || d.looking || d.unpacking || rec.state === "copying" || rec.state === "unpacking") return;      // not ready yet
  if (rec.state !== "ready") return stop(rec.note || "the archive could not be read");
  if (rec.installer) return stop("its installer asks questions");
  const x = (d.mods || []).find((m) => m.name === rec.name);
  if (!x) return;
  if (!x.updates) return stop("the mod it is a newer version of is no longer there");
  const needs = (d.steps || []).find((s) => s.key === "needs");
  if (needs && needs.state !== "done") return stop("something it needs is not there yet");
  if (!settled()) return;                                                 // ModTrap is still reading or scanning
  state.autoAddBusy = true;
  try {
    const p = await api("/api/add/plan", addBody());
    if (p.nothing) { stop("there is nothing to add"); return; }
    await api("/api/add/run", addBody());
    state.autoAdd = null;
    state.addPlan = null;
    toast("“" + rec.name + "” is added as the newer version of “" + a.mod + "”" + (x.updates_enabled ? ", and “" + a.mod + "” is disabled" : "") + ". Revert, on the Install mods tab, undoes it.");
    if (!(state.adding || []).includes(rec.name)) state.adding.push(rec.name);
    saveUi();
    state.addText = ""; state.upSig = "";
    state.gen = (state.gen || 0) + 1;
    tick();
  } catch (e) { stop(e.message); state.addPlanError = e.message; }
  finally { state.autoAddBusy = false; }
}

async function pollAdd(force) {
  if (state.status !== "ready") return;
  const mods = (state.adding || []).slice();
  const staged = (state.staged || []).slice();
  const key = mods.join("|") + "#" + staged.join("|") + "#" + state.loaded;
  if (!force && key === state.addKeySeen && !state.addLooking && !state.recGoing && !state.autoAdd) return;
  try {
    const d = mods.length || staged.length ? await api("/api/add", { mods: mods, staged: staged }) : { looking: false, mods: [], steps: [] };
    state.addKeySeen = key;
    state.addLooking = d.looking || d.unpacking;
    if (state.autoAdd) autoAddStep(d);
    autoInstallStep(d);
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
      + JSON.stringify(state.addPlan || 0) + (state.addPlanError || "") + state.changes + probeReason() + JSON.stringify(chosenPlace() || 0);
    if (text !== state.addText) { state.addText = text; renderAdd(d); }
  } catch (e) { /* the next round tries again */ }
}

// --- tabs, the log, and the loop -------------------------------------------------------------------------------------

// A list keeps its place (WHY§122). A list that is hidden forgets how far it was scrolled, and every list is hidden
// while its tab is not shown and while ModTrap reads the modlist again. So each list's place is noted as it is
// scrolled, while it is shown, and given back when it is shown again: after a change, a rescan, or a look at another tab.
const scrollTops = new Map();
document.addEventListener("scroll", (ev) => {
  const t = ev.target;
  if (!t || !t.classList || !t.classList.contains("scroll") || !t.querySelector("table") || t.offsetParent === null) return;
  if (state.status !== "ready" || state.restoring) return;
  scrollTops.set(t, t.scrollTop);
}, true);
function restoreScroll() {
  state.restoring = true;
  for (const [pane, top] of scrollTops) if (pane.offsetParent !== null && pane.scrollTop !== top) pane.scrollTop = top;
  state.restoring = false;
}

function showTab(name) {
  // Two rows (DESIGN§4): the section the tab belongs to, and that section's tabs.
  const mine = document.querySelector('#tabs button[data-tab="' + name + '"]');
  const group = mine ? mine.dataset.group : "modlist";
  state.groupTab = state.groupTab || {};
  state.groupTab[group] = name;
  let shown = 0;
  document.querySelectorAll("#tabs button[data-tab]").forEach((b) => {
    b.classList.toggle("on", b.dataset.tab === name);
    b.hidden = b.dataset.group !== group;
    if (!b.hidden) shown++;
  });
  $("tabs").classList.toggle("single", shown < 2);
  document.querySelectorAll("#groups button[data-group]").forEach((b) => b.classList.toggle("on", b.dataset.group === group));
  const pane = name === "pick" ? "mods" : name;                  // the mods' table serves two tabs (MT56)
  const split = name === "split";                                // and stands beside the plugins' in the split view (MT59)
  const panes = split ? ["tab-mods", "tab-plugins"] : ["tab-" + pane];
  document.querySelectorAll(".tab").forEach((t) => { t.hidden = !panes.includes(t.id); });
  $("split-bar").hidden = !split;
  $("split-bar").parentNode.classList.toggle("sidebyside", split);
  state.tab = name;
  swapSet(!!state.splitSwap);
  splitSet(state.splitAt || 50);
  if (!split) for (const r of document.querySelectorAll("tr.linked")) r.classList.remove("linked");
  else { linkPlugins(state.focus || "", false); linkMod(state.plugin || "", false); }
  restoreScroll();
  colSetupAll(true);                                             // the split view hides some columns: the widths are fitted again
  if (pane === "mods" || split) modsMode();
  updateTray();
  saveUi();
  if (name === "history") { state.historyText = ""; pollHistory(); }
  if (name === "updates") loadUpdates();
  if (name === "updater") pollUpdater(true);
  if (name === "installed") loadInstalled();
  if (name !== "mods" && state.placing) endPlacement();
  if (pane !== "mods" && !split) dragEnd();
  if (name === "downloads") loadDownloads();
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
  if (fresh) scrollTops.clear();                  // another session's lists begin at their top
  applyUi(fresh ? (s.session && s.session.ui) || {} : keep);
  restoreScroll();
  loadListState();
}

async function tick() {
  if (state.quit || state.selfRestart) return;
  let s;
  try { s = await api("/api/state"); state.unanswered = 0; } catch (e) {
    showMessage("ModTrap is not answering: " + e.message, true);
    // ModTrap has closed (with a page it took for gone, MT64): asked for anew, the page ModTrap's worker kept shows, and starts it.
    state.unanswered = e instanceof TypeError ? (state.unanswered || 0) + 1 : 0;
    if (state.unanswered >= 4 && navigator.serviceWorker && navigator.serviceWorker.controller) location.replace("/");
    return;
  }
  const was = state.status;
  state.status = s.status;
  state.changes = !!s.changes;
  state.mo2 = s.mo2 || null;
  renderMo2();
  state.settings = s.settings || {};
  renderSettings();
  if (s.status === "ready" && state.updater === undefined && !state.updaterBusy) pollUpdater(true);     // updates begun before the page was opened
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
document.addEventListener("dragover", (e) => {
  e.preventDefault();
  if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
  fileOver(e);                                             // over the Modlist page's rows: the line of the place
});
document.addEventListener("dragleave", () => { dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) { dragOn(false); fileOver(null); } });
document.addEventListener("drop", (e) => {
  e.preventDefault();
  if (state.selfBox) {                                     // the box for ModTrap's own update is open: the file is for it
    dragDepth = 0; dragOn(false);
    const f = Array.from((e.dataTransfer && e.dataTransfer.files) || [])[0];
    if (f) selfTake(f);
    return;
  }
  const own = Array.from((e.dataTransfer && e.dataTransfer.files) || []);
  if (own.length === 1 && SELF_NAME.test(own[0].name)) {   // a ModTrap release file, dropped anywhere on the page
    dragDepth = 0; dragOn(false); fileOver(null);
    selfUpdateBox(own[0]);
    return;
  }
  const at = fileOver(e);                                  // before the header folds again: that moves the rows
  dragDepth = 0; dragOn(false);
  fileOver(null);
  if (at) dropAtPlace(e, at);
  else if (state.tab === "updates" && state.status === "ready") updatesDropped(e); else dropped(e);
});

$("profile").addEventListener("change", () => $("open-form").requestSubmit());
$("rescan").addEventListener("click", async () => {
  try { state.gen = (state.gen || 0) + 1; await api("/api/rescan", {}); state.status = "reading"; } catch (e) { problem(e.message); }
  tick();
});
document.querySelectorAll("#tabs button[data-tab]").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
const GROUP_FIRST = { modlist: "mods", demaster: "pick", add: "add", update: "updates", downloads: "downloads", record: "history", settings: "settings" };
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
$("scan-list").addEventListener("click", () => { showTab("health"); listScan(true); });
$("s-scan").addEventListener("click", () => showTab("health"));
$("add-rescan").addEventListener("click", () => $("rescan").click());
$("add-go").addEventListener("click", () => { if (chosenPlace()) installNow(chosenPlace().before); else if ((state.settings || {}).manual_placement && !((state.addData || {}).update)) startPlacement(); else installNow(""); });
$("updater-clear").addEventListener("click", async () => { try { await api("/api/updater/clear", {}); } catch (e) { toast(e.message); } pollUpdater(true); });
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
  const box = state.tab === "plugins" ? $("plugins-search") : state.tab === "mods" || state.tab === "pick" || state.tab === "split" ? $("mods-search") : null;
  if ((ev.ctrlKey || ev.metaKey) && !ev.shiftKey && ev.key.toLowerCase() === "z" && !typing && (onMods() || onPlugins()) && !document.querySelector(".modal-back")) { ev.preventDefault(); listUndo(); return; }
  if (ev.key === "/" && !typing && box && !$("tabs").hidden) { ev.preventDefault(); box.focus(); box.select(); }
  if (ev.key === "Escape" && !$("picker").hidden) { pickerClose(); return; }
  if (ev.key === "Escape" && !$("session-panel").hidden) { $("session-panel").hidden = true; $("session-btn").setAttribute("aria-expanded", "false"); $("session-btn").focus(); }
  if (ev.key === "Escape" && document.activeElement === box && box.value) { box.value = ""; (state.tab === "plugins" ? filterPlugins : filterMods)(); }
});
const later = (fn) => { let timer; return () => { clearTimeout(timer); timer = setTimeout(fn, 120); }; };      // each box its own wait: the split view shows two
$("mods-search").addEventListener("input", later(filterMods));
$("plugins-search").addEventListener("input", later(filterPlugins));
// Enter in a search box goes to its star-number again, after the list was scrolled away from it.
$("mods-search").addEventListener("keydown", (ev) => { if (ev.key === "Enter") { (state.jumped || {}).mods = ""; filterMods(); } });
$("plugins-search").addEventListener("keydown", (ev) => { if (ev.key === "Enter") { (state.jumped || {}).plugins = ""; filterPlugins(); } });
for (const id of ["f-enabled", "f-plugins", "f-deps"]) $(id).addEventListener("change", filterMods);
for (const id of ["p-problems", "p-deps"]) $(id).addEventListener("change", filterPlugins);
paneWatch("log"); paneWatch("job-log");
loop();
