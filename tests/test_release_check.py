"""Tests for scripts/release_check.py on a generated repo layout.

Run: python3 -m unittest discover -s tests
"""

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "release_check", ROOT / "scripts" / "release_check.py"
)
release_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_check)


def repo(
    tmp,
    changelog="## v2.1.0 — 2026-12-01",
    provides="2026/12/01 v2.1.0",
    pkg="2.1.0 2026-12-01",
    doc="2.1.0",
):
    root = Path(tmp)
    (root / "tex").mkdir()
    (root / "ctan").mkdir()
    (root / "docs").mkdir()
    (root / "CHANGELOG.md").write_text(
        f"# Зміни\n\n{changelog}\n\nТекст.\n\n## v2.0.0 — 2026-11-17\n"
    )
    (root / "tex/kpi-thesis.cls").write_text(
        f"\\ProvidesClass{{kpi-thesis}}[{provides} KPI]\n"
    )
    (root / "tex/kpi-thesis-where.sty").write_text(
        f"\\ProvidesPackage{{kpi-thesis-where}}[{provides} where]\n"
    )
    (root / "ctan/kpi-thesis.pkg").write_text(
        f"\\pkg{{kpi-thesis}}\n\\version{{{pkg}}}\n"
    )
    (root / "docs/kpi-thesis-doc.tex").write_text(f"Версія {doc}, 1 грудня 2026 р.\n")
    return root


class ReleaseCheckTest(unittest.TestCase):
    def test_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(release_check.check(repo(tmp), "v2.1.0"), [])

    def test_unreleased_changelog(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors = release_check.check(repo(tmp, changelog="## v2.1.0 — не випущено"))
            self.assertIn("без дати", errors[0])

    def test_stale_provides_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors = release_check.check(repo(tmp, provides="2026/11/17 v2.1.0"))
            self.assertEqual(len(errors), 2)
            self.assertIn("датовано 2026/11/17", errors[0])

    def test_short_provides_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors = release_check.check(repo(tmp, provides="2026/12/01 v2.1"))
            self.assertEqual(len(errors), 2)
            self.assertIn("має v2.1, а реліз — v2.1.0", errors[0])

    def test_pkg_version_without_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors = release_check.check(repo(tmp, pkg="2.1.0"))
            self.assertEqual(len(errors), 1)
            self.assertIn("2.1.0 2026-12-01", errors[0])

    def test_version_mismatches(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors = release_check.check(repo(tmp, pkg="2.0.0 2026-12-01", doc="2.0.0"), "v2.0.0")
            text = "\n".join(errors)
            self.assertIn("ctan/kpi-thesis.pkg", text)
            self.assertIn("docs/kpi-thesis-doc.tex", text)
            self.assertIn("тег v2.0.0", text)


if __name__ == "__main__":
    unittest.main()
