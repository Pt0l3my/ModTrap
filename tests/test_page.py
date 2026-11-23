import re
import unittest
from pathlib import Path

from modtrap import server

PAGE = Path(server.PAGE_DIR)


class PageTests(unittest.TestCase):
    def setUp(self):
        self.html = (PAGE / "index.html").read_text(encoding="utf-8")
        self.js = "\n".join((PAGE / n).read_text(encoding="utf-8") for n in server.PAGE_JS)
        self.css = "\n".join((PAGE / n).read_text(encoding="utf-8") for n in server.PAGE_CSS)

    def test_every_element_the_script_asks_for_is_on_the_page(self):
        ids = set(re.findall(r'id="([^"]+)"', self.html))
        wanted = set(re.findall(r'\$\("([^"]+)"\)', self.js))
        self.assertEqual(sorted(wanted - ids), [])

    def test_nothing_is_loaded_from_outside_and_nothing_runs_inline(self):
        page = server.assemble("nonce", "token").decode("utf-8")
        self.assertEqual(re.findall(r'(?:src|href)\s*=', page), [])               # no outside file at all
        self.assertEqual(re.findall(r'https?://(?!127\.0\.0\.1)', page), [])
        self.assertEqual(re.findall(r'\son[a-z]+\s*=\s*"', self.html), [])          # no inline handlers (the policy)
        self.assertNotIn(' style="', self.html)                                     # no inline styles either
        self.assertEqual(page.count('nonce="nonce"'), 2)

    def test_every_fixed_button_that_starts_something_is_greyed_while_modtrap_works(self):
        """WHY§92, WHY§100: a button that changes the modlist or starts a program is gated, by its words. The ones
        the script makes get the mark as they are made; the page's fixed ones must carry it too."""
        words = re.search(r"const GATED = /\^\((.+?)\)/;", self.js).group(1).split("|")
        fixed = re.findall(r"<button\b([^>]*)>([^<]*)", self.html)
        named = [(attrs, text.strip()) for attrs, text in fixed if any(text.strip().startswith(w) for w in words)]
        self.assertTrue(any('id="process-go"' in a for a, _t in named))
        self.assertTrue(any('id="demaster"' in a for a, _t in named))
        for attrs, text in named:
            self.assertRegex(attrs, r'class="[^"]*\bgated\b', text)
        self.assertIn('document.querySelectorAll("button").forEach((b) => { if (GATED.test(b.textContent.trim())) b.classList.add("gated"); });', self.js)

    def test_every_tab_button_has_its_section(self):
        tabs = re.findall(r'<button data-group="[^"]+" data-tab="([^"]+)"', self.html)
        self.assertGreater(len(tabs), 12)
        for t in tabs:
            # "Pick mods" shows the mods' table too: one table serves it and the Modlist section's Mods tab (MT56).
            self.assertIn('id="tab-%s"' % ("mods" if t in ("pick", "split") else t), self.html)   # the split view shows two sections (MT59)

    def test_the_mods_list_is_modlists_own_tab_and_the_demasters_first(self):
        """MT56: Modlist › Mods is MO2's own list; the demaster's ticks are Demaster's first tab, on the same table."""
        tabs = re.findall(r'<button data-group="([^"]+)" data-tab="([^"]+)"', self.html)
        self.assertEqual([t for g, t in tabs if g == "modlist"][0], "mods")
        self.assertEqual([t for g, t in tabs if g == "demaster"][:2], ["pick", "selection"])
        self.assertIn('demaster: "pick"', self.js)
        self.assertIn('const pane = name === "pick" ? "mods" : name;', self.js)
        self.assertIn("#mods-table.picking .onbox, #mods-table:not(.picking) .pickbox { display: none; }", self.css)
        for path in ("/api/list/set", "/api/list/move", "/api/list/rename", "/api/list/undo", "/api/list/scan"):
            self.assertIn('"%s"' % path, self.js)
        # What changes MO2's lists is begun only with MO2 closed.
        closed = re.search(r"const NEEDS_MO2_CLOSED = new Set\(\[(.+?)\]\);", self.js, re.S).group(1)
        for path in ("/api/list/move", "/api/list/rename", "/api/list/undo", "/api/separator/add"):
            self.assertIn('"%s"' % path, closed)

    def test_a_file_dropped_on_the_list_is_installed_at_its_place_and_a_list_keeps_its_place(self):
        """MT57: the drop's place is read before the header folds back (WHY§122); the run asks with its own
        archives and its place; a list's place is noted while it is shown and given back when it is shown again."""
        drop = re.search(r'document\.addEventListener\("drop", \(e\) => \{(.+?)\n\}\);', self.js, re.S).group(1)
        self.assertLess(drop.index("const at = fileOver(e)"), drop.rindex("dragOn(false)"))
        self.assertIn("if (at) dropAtPlace(e, at);", drop)
        self.assertIn('const body = () => ({ mods: [], staged: run.ids.slice(), before: run.before });', self.js)
        self.assertIn('api("/api/add/run", body())', self.js)
        self.assertIn("if (chosenPlace()) installNow(chosenPlace().before);", self.js)
        self.assertIn("scrollTops.set(t, t.scrollTop);", self.js)
        show = self.js[self.js.index("function showTab(name) {"):]
        self.assertLess(show.index("state.tab = name;"), show.index("restoreScroll();"))          # given back as the tab is shown
        self.assertNotIn("if (pane && !fresh) pane.scrollTop = top;", self.js)       # read after the list was hidden: always 0


    def test_the_plugins_tab_changes_the_load_order_and_the_version_is_a_button(self):
        """MT58: the Plugins tab's box, drag and row symbols; ModTrap's own update behind the version."""
        self.assertIn('<button id="version" type="button"', self.html)
        self.assertIn('$("version").addEventListener("click", () => selfUpdateBox());', self.js)
        for path in ("/api/list/plugins/set", "/api/list/plugins/move", "/api/selfupdate/upload", "/api/selfupdate/apply"):
            self.assertIn(path, self.js)
        self.assertIn('if (p.issues.length) mark("bad", "⚠"', self.js)
        self.assertIn('mark("warn", "⇄"', self.js)
        for needle in ('id="plugins-undo"', 'class="c-mark"'):
            self.assertIn(needle, self.html)
        # A plugin's tick asks nothing: no question box in its function.
        body = re.search(r"function pluginSet\(names, on, box\) \{(.+?)\n\}\n", self.js, re.S).group(1)
        self.assertNotIn("modalBox", body)


    def test_the_split_view_shows_both_lists_with_a_line_to_drag(self):
        """MT59: a tab of the Modlist section with the mods' and the plugins' sections side by side."""
        tabs = re.findall(r'<button data-group="([^"]+)" data-tab="([^"]+)"', self.html)
        self.assertEqual([t for g, t in tabs if g == "modlist"][:3], ["mods", "plugins", "split"])
        # The line stands between the two sections it parts.
        self.assertRegex(self.html, r'(?s)<section id="tab-mods".+?</section>\s*<div id="split-bar" class="splitbar"[^>]*hidden></div>\s*<section id="tab-plugins"')
        self.assertIn('const panes = split ? ["tab-mods", "tab-plugins"] : ["tab-" + pane];', self.js)
        self.assertIn("split: state.splitAt || 50", self.js)
        self.assertIn(".splitbar { flex: 0 0 9px; position: relative; cursor: col-resize;", self.css)
        # "Swap sides" (MT59, note): a button of the tab row, shown on the split view alone; it is no tab.
        self.assertRegex(self.html, r'<button id="split-swap" type="button" class="tabtool"[^>]*hidden>')
        self.assertIn("main.sidebyside.swapped { flex-direction: row-reverse; }", self.css)
        self.assertIn('document.querySelectorAll("#tabs button[data-tab]").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));', self.js)
        self.assertIn("swap: !!state.splitSwap", self.js)


if __name__ == "__main__":
    unittest.main()
