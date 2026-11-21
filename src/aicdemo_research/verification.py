from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from .config import RAW_LABELS
from .sec_data import AnnualFact


def _numeric_value(tag: Any) -> float | None:
    raw = tag.get_text("", strip=True)
    cleaned = re.sub(r"[^0-9.()\-]", "", raw)
    if cleaned in {"", "-", "--"}:
        return None
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    scale = int(tag.attrs.get("scale", "0") or "0")
    sign = -1 if tag.attrs.get("sign") == "-" or negative else 1
    return sign * value * (10**scale)


def verify_filing(
    ticker: str,
    fiscal_year: int,
    filing_path: Path,
    filing_url: str,
    facts: dict[str, AnnualFact],
) -> list[dict[str, Any]]:
    soup = BeautifulSoup(filing_path.read_bytes(), "lxml")
    contexts: dict[str, dict[str, Any]] = {}
    for tag in soup.find_all(lambda node: node.name and node.name.lower().endswith("context")):
        context_id = tag.attrs.get("id")
        if not context_id:
            continue
        start = tag.find(lambda node: node.name and node.name.lower().endswith("startdate"))
        end = tag.find(lambda node: node.name and node.name.lower().endswith("enddate"))
        dimensions = tag.find_all(
            lambda node: node.name and node.name.lower().endswith(("explicitmember", "typedmember"))
        )
        contexts[context_id] = {
            "start": start.get_text(strip=True) if start else None,
            "end": end.get_text(strip=True) if end else None,
            "has_dimensions": bool(dimensions),
        }

    records: list[dict[str, Any]] = []
    for metric, expected in facts.items():
        candidates: list[float] = []
        for tag in soup.find_all(
            lambda node: node.name
            and node.name.lower().endswith("nonfraction")
            and str(node.attrs.get("name", "")).split(":")[-1].lower() == expected.concept.lower()
        ):
            context_ref = tag.attrs.get("contextref") or tag.attrs.get("contextRef")
            context = contexts.get(context_ref, {})
            if context.get("has_dimensions"):
                continue
            if context.get("start") != expected.start or context.get("end") != expected.end:
                continue
            value = _numeric_value(tag)
            if value is not None:
                candidates.append(value)
        tolerance = max(1.0e-4 if expected.unit == "USD/shares" else 1.0, abs(expected.value) * 1e-9)
        match = next((value for value in candidates if math.isclose(value, expected.value, abs_tol=tolerance)), None)
        records.append(
            {
                "ticker": ticker,
                "fiscal_year": fiscal_year,
                "metric": RAW_LABELS[metric],
                "concept": expected.concept,
                "unit": expected.unit,
                "period_start": expected.start,
                "period_end": expected.end,
                "company_facts_value": expected.value,
                "ten_k_value": match,
                "matched": match is not None,
                "candidate_count": len(candidates),
                "accession_number": expected.accession,
                "filing_source": filing_url,
                "cached_file": str(filing_path),
            }
        )
    return records


def assert_verification(records: list[dict[str, Any]]) -> None:
    failures = [item for item in records if not item["matched"]]
    if failures:
        sample = ", ".join(
            f"{item['ticker']} FY{item['fiscal_year']} {item['metric']}"
            for item in failures[:8]
        )
        raise RuntimeError(f"10-K cross-check failed for {len(failures)} facts: {sample}")
