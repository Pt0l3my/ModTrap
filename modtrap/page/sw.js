// ModTrap's worker in the browser (MT64, DESIGN§26). It does one thing: when ModTrap's page is asked for and ModTrap
// is not running, it answers with the small page it kept, which offers to start ModTrap again. Every other request
// goes to ModTrap untouched, and nothing of ModTrap's own page is ever kept or answered from here.
const KEPT = "modtrap-__VERSION__";
const SHELL = "/offline";
self.addEventListener("install", (ev) => {
  ev.waitUntil(caches.open(KEPT).then((c) => c.add(new Request(SHELL, { cache: "reload" }))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (ev) => {
  ev.waitUntil(caches.keys().then((names) => Promise.all(names.filter((n) => n !== KEPT).map((n) => caches.delete(n)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (ev) => {
  if (ev.request.mode !== "navigate") return;
  ev.respondWith(fetch(ev.request).catch(() => caches.match(SHELL).then((kept) => kept || Response.error())));
});
