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
        tabs = re.findall(r'<button data-tab="([^"]+)"', self.html)
        for t in tabs:
            self.assertIn('id="tab-%s"' % t, self.html)


if __name__ == "__main__":
    unittest.main()
