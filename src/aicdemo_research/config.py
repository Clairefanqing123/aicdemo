from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw" / "sec"
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "output"
FIGURES = OUTPUT / "figures"
TABLES = OUTPUT / "tables"
REPORTS = OUTPUT / "reports"
LEGACY = OUTPUT / "legacy"
TMP_PDFS = ROOT / "tmp" / "pdfs"
TEMPLATES = Path(__file__).resolve().parent / "templates"

TEX_BIN = Path(r"D:\texlive\2026\bin\windows")
USER_AGENT = os.environ.get(
    "SEC_USER_AGENT",
    "AI-Coding-Finance-Classroom-Demo/2.0 contact=research@example.edu",
)

COMPANIES = {
    "AAPL": {"name": "Apple", "legal_name": "Apple Inc.", "cik": "0000320193"},
    "MSFT": {
        "name": "Microsoft",
        "legal_name": "Microsoft Corporation",
        "cik": "0000789019",
    },
}

CONCEPTS = {
    "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax", "USD"),
    "gross_profit": ("GrossProfit", "USD"),
    "operating_income": ("OperatingIncomeLoss", "USD"),
    "net_income": ("NetIncomeLoss", "USD"),
    "diluted_eps": ("EarningsPerShareDiluted", "USD/shares"),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities", "USD"),
    "capital_expenditures": ("PaymentsToAcquirePropertyPlantAndEquipment", "USD"),
}

RAW_LABELS = {
    "revenue": "Revenue",
    "gross_profit": "Gross Profit",
    "operating_income": "Operating Income",
    "net_income": "Net Income",
    "diluted_eps": "Diluted EPS",
    "operating_cash_flow": "Operating Cash Flow",
    "capital_expenditures": "Capital Expenditures",
}


def ensure_directories() -> None:
    for path in (
        DATA_RAW / "companyfacts",
        DATA_RAW / "submissions",
        DATA_RAW / "filings",
        DATA_PROCESSED,
        FIGURES,
        TABLES,
        REPORTS,
        LEGACY,
        TMP_PDFS,
    ):
        path.mkdir(parents=True, exist_ok=True)
