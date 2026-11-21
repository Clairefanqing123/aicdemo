from __future__ import annotations

import json
import shutil
from datetime import date, datetime
from typing import Any

from .charts import generate_charts
from .config import COMPANIES, DATA_PROCESSED, LEGACY, REPORTS, ROOT, TABLES, ensure_directories
from .metrics import build_company_rows, build_long_rows, save_context, summaries, write_dict_csv, write_wide_csv
from .narrative import build_sections
from .render import compile_pdf, render_html, render_tex
from .sec_data import cache_filing, load_company_sources
from .verification import assert_verification, verify_filing


LEGACY_FILES = ["comparison.csv", "verification.json", "equity_research_memo.html", "equity_research_memo.tex", "build_status.json"]


def preserve_legacy() -> None:
    for name in LEGACY_FILES:
        source, target = ROOT / name, LEGACY / name
        if source.exists() and not target.exists():
            shutil.copy2(source, target)


def build_references(rows: list[dict[str, Any]], accessed: str) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for row in sorted(rows, key=lambda item: (item["ticker"], item["fiscal_year"])):
        label = (
            f"{row['company']}. Form 10-K for fiscal year ended {row['fiscal_year_end']}. "
            f"{row['primary_document']}; filed {row['filing_date']}. Accessed {accessed}."
        )
        refs.append({
            "html": f'{label} <a href="{row["filing_source"]}">{row["filing_source"]}</a>',
            "tex": f"{label} \\url{{{row['filing_source']}}}",
        })
    for ticker in ("AAPL", "MSFT"):
        row = next(item for item in rows if item["ticker"] == ticker)
        filename = f"{ticker.lower()}_companyfacts.json"
        label = f"U.S. Securities and Exchange Commission. {row['company']} Company Facts ({filename}). Accessed {accessed}."
        refs.append({
            "html": f'{label} <a href="{row["company_facts_source"]}">{row["company_facts_source"]}</a>',
            "tex": f"{label} \\url{{{row['company_facts_source']}}}",
        })
    return refs


def latest_table_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [max((r for r in rows if r["ticker"] == ticker), key=lambda r: r["fiscal_year_end"]) for ticker in ("AAPL", "MSFT")]


def run(*, refresh: bool = False, offline: bool = False, skip_pdf: bool = False) -> dict[str, Any]:
    ensure_directories()
    preserve_legacy()
    all_rows: list[dict[str, Any]] = []
    selected_by_company: dict[str, dict[str, dict[str, Any]]] = {}
    for ticker in COMPANIES:
        facts, submissions = load_company_sources(ticker, refresh=refresh, offline=offline)
        rows, selected = build_company_rows(ticker, facts, submissions)
        all_rows.extend(rows)
        selected_by_company[ticker] = selected
    all_rows.sort(key=lambda item: (item["ticker"], item["fiscal_year_end"]))
    if len(all_rows) != 10:
        raise RuntimeError(f"Expected 10 company-year rows, found {len(all_rows)}")

    verification_records: list[dict[str, Any]] = []
    for row in all_rows:
        filing_path = cache_filing(
            row["ticker"], row["fiscal_year"], row["accession_number"], row["primary_document"], row["filing_source"],
            refresh=refresh, offline=offline,
        )
        verification_records.extend(verify_filing(
            row["ticker"], row["fiscal_year"], filing_path, row["filing_source"],
            selected_by_company[row["ticker"]][row["fiscal_year_end"]],
        ))
    assert_verification(verification_records)
    if len(verification_records) != 70:
        raise RuntimeError(f"Expected 70 verification records, found {len(verification_records)}")

    wide_path = DATA_PROCESSED / "comparison.csv"
    long_path = DATA_PROCESSED / "metrics_long.csv"
    manifest_path = DATA_PROCESSED / "source_manifest.csv"
    verification_path = DATA_PROCESSED / "verification.json"
    write_wide_csv(all_rows, wide_path)
    long_rows = build_long_rows(all_rows, selected_by_company)
    write_dict_csv(long_rows, long_path)
    matched = {(x["ticker"], x["fiscal_year"], x["concept"]): x["matched"] for x in verification_records}
    write_dict_csv(
        [dict(item, verified=matched[(item["ticker"], item["fiscal_year"], item["concept"])]) for item in long_rows],
        manifest_path,
    )
    verification_path.write_text(json.dumps(verification_records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_wide_csv(all_rows, TABLES / "five_year_core_financials.csv")
    write_wide_csv(latest_table_rows(all_rows), TABLES / "latest_fiscal_year_comparison.csv")

    chart_paths = generate_charts(all_rows)
    summary = summaries(all_rows)
    sections = build_sections(summary)
    accessed = date.today().isoformat()
    refs = build_references(all_rows, accessed)
    html_path = render_html(sections, all_rows, refs, accessed, len(verification_records))
    tex_path = render_tex(sections, all_rows, refs, accessed, len(verification_records))
    pdf_result = None if skip_pdf else compile_pdf(tex_path)

    context = {
        "title": "Apple vs. Microsoft: A Five-Year Comparative Fundamental Analysis",
        "generated_at": datetime.now().astimezone().isoformat(), "as_of_date": accessed,
        "rows": all_rows, "summaries": summary, "figures": chart_paths, "references": refs,
        "verification_count": len(verification_records),
        "verification_passed": all(x["matched"] for x in verification_records),
        "outputs": {"html": str(html_path), "tex": str(tex_path), "pdf": pdf_result["pdf"] if pdf_result else None},
    }
    save_context(context)
    status = {
        "generated_at": context["generated_at"], "rows": len(all_rows), "companies": list(COMPANIES),
        "raw_metrics_verified": len(verification_records), "verification_passed": context["verification_passed"],
        "figures": len(chart_paths), "references": len(refs), "pdf": pdf_result,
    }
    (REPORTS / "build_status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return status
