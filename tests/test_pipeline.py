from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class GeneratedReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        context_path = ROOT / "data" / "processed" / "report_context.json"
        if not context_path.exists():
            raise unittest.SkipTest("Run build_research.py before generated-output tests")
        cls.context = json.loads(context_path.read_text(encoding="utf-8"))
        cls.rows = cls.context["rows"]

    def test_complete_company_year_panel(self) -> None:
        self.assertEqual(len(self.rows), 10)
        self.assertEqual({row["ticker"] for row in self.rows}, {"AAPL", "MSFT"})
        for ticker in ("AAPL", "MSFT"):
            values = [row for row in self.rows if row["ticker"] == ticker]
            self.assertEqual(len(values), 5)
            self.assertEqual({row["fiscal_year"] for row in values}, set(range(2022, 2027)))

    def test_derived_metrics(self) -> None:
        for row in self.rows:
            self.assertAlmostEqual(row["gross_margin_pct"], row["gross_profit_usd"] / row["revenue_usd"] * 100, places=7)
            self.assertAlmostEqual(row["operating_margin_pct"], row["operating_income_usd"] / row["revenue_usd"] * 100, places=7)
            self.assertAlmostEqual(row["net_margin_pct"], row["net_income_usd"] / row["revenue_usd"] * 100, places=7)
            self.assertEqual(row["free_cash_flow_usd"], row["operating_cash_flow_usd"] - row["capital_expenditures_usd"])
            self.assertTrue(all(math.isfinite(float(value)) for key, value in row.items() if key.endswith(("_usd", "_pct", "_share"))))

    def test_sources_and_verification(self) -> None:
        self.assertTrue(self.context["verification_passed"])
        self.assertEqual(self.context["verification_count"], 70)
        self.assertEqual(len(self.context["references"]), 12)

    def test_expected_outputs(self) -> None:
        for path in (
            ROOT / "output" / "reports" / "apple_vs_microsoft_report.html",
            ROOT / "output" / "reports" / "apple_vs_microsoft_report.tex",
            ROOT / "output" / "reports" / "apple_vs_microsoft_report.pdf",
        ):
            self.assertTrue(path.exists(), str(path))
            self.assertGreater(path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
