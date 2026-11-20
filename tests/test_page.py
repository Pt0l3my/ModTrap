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

    def test_every_tab_button_has_its_section(self):
        tabs = re.findall(r'<button data-tab="([^"]+)"', self.html)
        for t in tabs:
            self.assertIn('id="tab-%s"' % t, self.html)


if __name__ == "__main__":
    unittest.main()
