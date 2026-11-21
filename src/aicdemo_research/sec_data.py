from __future__ import annotations

import json
import shutil
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .config import COMPANIES, DATA_RAW, ROOT, USER_AGENT


@dataclass(frozen=True)
class AnnualFact:
    concept: str
    start: str
    end: str
    value: float
    unit: str
    accession: str
    filed: str
    fiscal_year: int


def request_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Unable to fetch {url}")


def load_or_fetch(
    url: str,
    path: Path,
    *,
    refresh: bool,
    offline: bool,
    legacy_path: Path | None = None,
) -> bytes:
    if path.exists() and not refresh:
        return path.read_bytes()
    if legacy_path and legacy_path.exists() and not refresh:
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_path, path)
        return path.read_bytes()
    if offline:
        raise RuntimeError(f"Offline cache is missing: {path}")
    payload = request_bytes(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def load_json(
    url: str,
    path: Path,
    *,
    refresh: bool,
    offline: bool,
    legacy_path: Path | None = None,
) -> dict[str, Any]:
    return json.loads(
        load_or_fetch(
            url,
            path,
            refresh=refresh,
            offline=offline,
            legacy_path=legacy_path,
        ).decode("utf-8")
    )


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def annual_facts(company_facts: dict[str, Any], concept: str, unit: str) -> list[AnnualFact]:
    try:
        records = company_facts["facts"]["us-gaap"][concept]["units"][unit]
    except KeyError as exc:
        raise RuntimeError(f"Missing SEC concept/unit: {concept} ({unit})") from exc

    candidates: dict[str, AnnualFact] = {}
    for record in records:
        if record.get("form") not in {"10-K", "10-K/A"} or record.get("fp") != "FY":
            continue
        if not all(record.get(key) for key in ("start", "end", "filed", "accn", "fy")):
            continue
        start = parse_date(record["start"])
        end = parse_date(record["end"])
        duration = (end - start).days
        if not 300 <= duration <= 380 or int(record["fy"]) != end.year:
            continue
        fact = AnnualFact(
            concept=concept,
            start=record["start"],
            end=record["end"],
            value=float(record["val"]),
            unit=unit,
            accession=record["accn"],
            filed=record["filed"],
            fiscal_year=int(record["fy"]),
        )
        previous = candidates.get(fact.end)
        if previous is None or (fact.filed, fact.accession) > (previous.filed, previous.accession):
            candidates[fact.end] = fact
    facts = sorted(candidates.values(), key=lambda item: item.end)
    if len(facts) < 6 and concept == "RevenueFromContractWithCustomerExcludingAssessedTax":
        raise RuntimeError(f"Only {len(facts)} usable annual revenue observations")
    if len(facts) < 5:
        raise RuntimeError(f"Only {len(facts)} usable annual observations for {concept}")
    return facts


def find_filing(submissions: dict[str, Any], end: str, accession: str) -> dict[str, str]:
    recent = submissions["filings"]["recent"]
    for index, candidate in enumerate(recent["accessionNumber"]):
        if candidate == accession:
            return {
                "accession": candidate,
                "filing_date": recent["filingDate"][index],
                "report_date": recent["reportDate"][index],
                "primary_document": recent["primaryDocument"][index],
            }
    for index, report_date in enumerate(recent["reportDate"]):
        if report_date == end and recent["form"][index] in {"10-K", "10-K/A"}:
            return {
                "accession": recent["accessionNumber"][index],
                "filing_date": recent["filingDate"][index],
                "report_date": report_date,
                "primary_document": recent["primaryDocument"][index],
            }
    raise RuntimeError(f"No matching 10-K submission metadata for fiscal end {end}")


def filing_url(cik: str, accession: str, primary_document: str) -> str:
    return (
        f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
        f"{accession.replace('-', '')}/{primary_document}"
    )


def load_company_sources(ticker: str, *, refresh: bool, offline: bool) -> tuple[dict, dict]:
    company = COMPANIES[ticker]
    facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company['cik']}.json"
    submissions_url = f"https://data.sec.gov/submissions/CIK{company['cik']}.json"
    facts = load_json(
        facts_url,
        DATA_RAW / "companyfacts" / f"{ticker.lower()}_companyfacts.json",
        refresh=refresh,
        offline=offline,
        legacy_path=ROOT / "data" / "sec" / f"{ticker.lower()}_companyfacts.json",
    )
    submissions = load_json(
        submissions_url,
        DATA_RAW / "submissions" / f"{ticker.lower()}_submissions.json",
        refresh=refresh,
        offline=offline,
        legacy_path=ROOT / "data" / "sec" / f"{ticker.lower()}_submissions.json",
    )
    return facts, submissions


def cache_filing(
    ticker: str,
    fiscal_year: int,
    accession: str,
    primary_document: str,
    url: str,
    *,
    refresh: bool,
    offline: bool,
) -> Path:
    target = DATA_RAW / "filings" / ticker / str(fiscal_year) / primary_document
    legacy = ROOT / "data" / "sec" / f"{ticker.lower()}_{accession}.html"
    load_or_fetch(
        url,
        target,
        refresh=refresh,
        offline=offline,
        legacy_path=legacy,
    )
    return target
