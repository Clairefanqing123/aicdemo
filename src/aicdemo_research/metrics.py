from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import COMPANIES, CONCEPTS, DATA_PROCESSED, ROOT
from .sec_data import AnnualFact, annual_facts, filing_url, find_filing


RAW_METRIC_FIELDS = {
    "revenue": "revenue_usd",
    "gross_profit": "gross_profit_usd",
    "operating_income": "operating_income_usd",
    "net_income": "net_income_usd",
    "diluted_eps": "diluted_eps_usd_per_share",
    "operating_cash_flow": "operating_cash_flow_usd",
    "capital_expenditures": "capital_expenditures_usd",
}


def build_company_rows(
    ticker: str,
    company_facts: dict[str, Any],
    submissions: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, AnnualFact]]]:
    series: dict[str, list[AnnualFact]] = {}
    by_end: dict[str, dict[str, AnnualFact]] = {}
    for metric, (concept, unit) in CONCEPTS.items():
        series[metric] = annual_facts(company_facts, concept, unit)
        by_end[metric] = {fact.end: fact for fact in series[metric]}

    common_ends = set.intersection(*(set(values) for values in by_end.values()))
    selected_ends = sorted(common_ends)[-5:]
    if len(selected_ends) != 5:
        raise RuntimeError(f"{ticker} has only {len(selected_ends)} complete fiscal years")

    revenue_ends = [fact.end for fact in series["revenue"]]
    rows: list[dict[str, Any]] = []
    selected: dict[str, dict[str, AnnualFact]] = {}
    company = COMPANIES[ticker]
    for end in selected_ends:
        facts = {metric: by_end[metric][end] for metric in CONCEPTS}
        accessions = {fact.accession for fact in facts.values()}
        if len(accessions) != 1:
            raise RuntimeError(f"{ticker} {end} metrics span accessions: {sorted(accessions)}")
        revenue = facts["revenue"]
        revenue_index = revenue_ends.index(end)
        if revenue_index == 0:
            raise RuntimeError(f"{ticker} lacks prior-year revenue for {end}")
        prior_revenue = series["revenue"][revenue_index - 1].value
        filing = find_filing(submissions, end, revenue.accession)
        source = filing_url(company["cik"], filing["accession"], filing["primary_document"])
        rev = facts["revenue"].value
        capex = facts["capital_expenditures"].value
        ocf = facts["operating_cash_flow"].value
        row: dict[str, Any] = {
            "company": company["legal_name"],
            "ticker": ticker,
            "fiscal_year": revenue.fiscal_year,
            "fiscal_year_end": end,
            "revenue_usd": int(round(rev)),
            "revenue_growth_pct": (rev / prior_revenue - 1) * 100,
            "gross_profit_usd": int(round(facts["gross_profit"].value)),
            "gross_margin_pct": facts["gross_profit"].value / rev * 100,
            "operating_income_usd": int(round(facts["operating_income"].value)),
            "operating_margin_pct": facts["operating_income"].value / rev * 100,
            "net_income_usd": int(round(facts["net_income"].value)),
            "net_margin_pct": facts["net_income"].value / rev * 100,
            "diluted_eps_usd_per_share": facts["diluted_eps"].value,
            "operating_cash_flow_usd": int(round(ocf)),
            "capital_expenditures_usd": int(round(capex)),
            "free_cash_flow_usd": int(round(ocf - capex)),
            "capex_intensity_pct": capex / rev * 100,
            "form": "10-K",
            "filing_date": filing["filing_date"],
            "accession_number": filing["accession"],
            "primary_document": filing["primary_document"],
            "company_facts_source": (
                f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company['cik']}.json"
            ),
            "filing_source": source,
        }
        numeric = [value for key, value in row.items() if key.endswith(("_usd", "_pct", "_share"))]
        if not all(math.isfinite(float(value)) for value in numeric):
            raise RuntimeError(f"Non-finite calculation for {ticker} {end}")
        rows.append(row)
        selected[end] = facts
    return rows, selected


def _format_csv(row: dict[str, Any]) -> dict[str, Any]:
    output = dict(row)
    for key in output:
        if key.endswith("_pct"):
            output[key] = f"{float(output[key]):.2f}"
    output["diluted_eps_usd_per_share"] = f"{float(output['diluted_eps_usd_per_share']):.2f}"
    return output


def write_wide_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(_format_csv(row) for row in rows)


def build_long_rows(
    rows: list[dict[str, Any]], selected: dict[str, dict[str, dict[str, AnnualFact]]]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    by_key = {(row["ticker"], row["fiscal_year_end"]): row for row in rows}
    for ticker, years in selected.items():
        for end, facts in years.items():
            row = by_key[(ticker, end)]
            for metric, fact in facts.items():
                output.append(
                    {
                        "ticker": ticker,
                        "fiscal_year": row["fiscal_year"],
                        "fiscal_year_end": end,
                        "metric": metric,
                        "concept": fact.concept,
                        "unit": fact.unit,
                        "value": fact.value,
                        "period_start": fact.start,
                        "period_end": fact.end,
                        "accession_number": fact.accession,
                        "filing_date": fact.filed,
                        "company_facts_source": row["company_facts_source"],
                        "filing_source": row["filing_source"],
                    }
                )
    return output


def write_dict_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summaries(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["ticker"]].append(row)
    result: dict[str, Any] = {}
    for ticker, values in grouped.items():
        values.sort(key=lambda item: item["fiscal_year_end"])
        first, latest = values[0], values[-1]
        result[ticker] = {
            "first": first,
            "latest": latest,
            "revenue_cagr_pct": ((latest["revenue_usd"] / first["revenue_usd"]) ** 0.25 - 1) * 100,
            "capex_cagr_pct": (
                (latest["capital_expenditures_usd"] / first["capital_expenditures_usd"]) ** 0.25 - 1
            ) * 100,
            "average_operating_margin_pct": sum(x["operating_margin_pct"] for x in values) / 5,
            "average_net_margin_pct": sum(x["net_margin_pct"] for x in values) / 5,
        }
    return result


def save_context(context: dict[str, Any]) -> None:
    (DATA_PROCESSED / "report_context.json").write_text(
        json.dumps(context, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
