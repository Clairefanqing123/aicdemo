from __future__ import annotations

import csv
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "sec"
USER_AGENT = os.environ.get(
    "SEC_USER_AGENT",
    "AI-Coding-Finance-Classroom-Demo/1.0 contact=research@example.edu",
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
    "net_income": ("NetIncomeLoss", "USD"),
    "operating_income": ("OperatingIncomeLoss", "USD"),
    "diluted_eps": ("EarningsPerShareDiluted", "USD/shares"),
}


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


class InlineFactParser(HTMLParser):
    def __init__(self, concept: str) -> None:
        super().__init__()
        self.concept = concept.lower()
        self.active: dict[str, str] | None = None
        self.fragments: list[str] = []
        self.values: list[float] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() not in {"ix:nonfraction", "nonfraction"}:
            return
        attributes = {key.lower(): value or "" for key, value in attrs}
        fact_name = attributes.get("name", "").lower().split(":")[-1]
        if fact_name == self.concept.lower():
            self.active = attributes
            self.fragments = []

    def handle_data(self, data: str) -> None:
        if self.active is not None:
            self.fragments.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.active is None or tag.lower() not in {"ix:nonfraction", "nonfraction"}:
            return
        raw = "".join(self.fragments).strip()
        cleaned = re.sub(r"[^0-9.()\-]", "", raw)
        if cleaned not in {"", "-", "--"}:
            negative = cleaned.startswith("(") and cleaned.endswith(")")
            cleaned = cleaned.strip("()")
            try:
                value = float(cleaned)
                scale = int(self.active.get("scale", "0") or "0")
                sign = -1 if self.active.get("sign") == "-" or negative else 1
                self.values.append(sign * value * (10**scale))
            except ValueError:
                pass
        self.active = None
        self.fragments = []


def request_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Host": urllib.parse.urlparse(url).netloc,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"SEC request failed for {url}: {exc}") from exc
    time.sleep(0.12)
    return payload


def load_or_fetch(url: str, path: Path, refresh: bool) -> bytes:
    if path.exists() and not refresh:
        return path.read_bytes()
    payload = request_bytes(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def load_json(url: str, path: Path, refresh: bool) -> dict[str, Any]:
    return json.loads(load_or_fetch(url, path, refresh).decode("utf-8"))


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


def verify_revenue(
    ticker: str,
    company: dict[str, str],
    latest_revenue: AnnualFact,
    submissions: dict[str, Any],
    refresh: bool,
) -> dict[str, Any]:
    filing = find_filing(submissions, latest_revenue.end, latest_revenue.accession)
    url = filing_url(company["cik"], filing["accession"], filing["primary_document"])
    cache_path = DATA_DIR / f"{ticker.lower()}_{filing['accession']}.html"
    document = load_or_fetch(url, cache_path, refresh).decode("utf-8", errors="replace")
    parser = InlineFactParser(latest_revenue.concept)
    parser.feed(document)
    tolerance = max(1.0, abs(latest_revenue.value) * 1e-9)
    matched_value = next(
        (value for value in parser.values if abs(value - latest_revenue.value) <= tolerance),
        None,
    )
    if matched_value is None:
        raise RuntimeError(
            f"{ticker} 10-K verification failed: expected revenue {latest_revenue.value:.0f}; "
            f"found {len(parser.values)} tagged revenue values"
        )
    return {
        "ticker": ticker,
        "metric": "Revenue",
        "concept": latest_revenue.concept,
        "fiscal_year_end": latest_revenue.end,
        "company_facts_value_usd": int(round(latest_revenue.value)),
        "ten_k_tagged_value_usd": int(round(matched_value)),
        "matched": True,
        "accession_number": filing["accession"],
        "filing_date": filing["filing_date"],
        "source": url,
    }


def build_company_rows(
    ticker: str,
    company: dict[str, str],
    company_facts: dict[str, Any],
    submissions: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, AnnualFact]]:
    series: dict[str, list[AnnualFact]] = {}
    by_end: dict[str, dict[str, AnnualFact]] = {}
    for metric, (concept, unit) in CONCEPTS.items():
        series[metric] = annual_facts(company_facts, concept, unit)
        by_end[metric] = {fact.end: fact for fact in series[metric]}

    common_ends = set.intersection(*(set(values) for values in by_end.values()))
    selected_ends = sorted(common_ends)[-5:]
    if len(selected_ends) != 5:
        raise RuntimeError(f"{ticker} has only {len(selected_ends)} common complete fiscal years")

    revenue_by_end = by_end["revenue"]
    all_revenue_ends = [fact.end for fact in series["revenue"]]
    rows: list[dict[str, Any]] = []
    selected_facts: dict[str, AnnualFact] = {}
    for end in selected_ends:
        revenue = revenue_by_end[end]
        revenue_index = all_revenue_ends.index(end)
        if revenue_index == 0:
            raise RuntimeError(f"{ticker} lacks prior-year revenue for growth at {end}")
        prior_revenue = series["revenue"][revenue_index - 1].value
        net_income = by_end["net_income"][end]
        operating_income = by_end["operating_income"][end]
        diluted_eps = by_end["diluted_eps"][end]
        filing = find_filing(submissions, end, revenue.accession)
        source = filing_url(company["cik"], filing["accession"], filing["primary_document"])
        row = {
            "company": company["legal_name"],
            "ticker": ticker,
            "fiscal_year": revenue.fiscal_year,
            "fiscal_year_end": end,
            "revenue_usd": int(round(revenue.value)),
            "revenue_growth_pct": (revenue.value / prior_revenue - 1) * 100,
            "net_income_usd": int(round(net_income.value)),
            "net_margin_pct": net_income.value / revenue.value * 100,
            "operating_income_usd": int(round(operating_income.value)),
            "operating_margin_pct": operating_income.value / revenue.value * 100,
            "diluted_eps_usd_per_share": diluted_eps.value,
            "form": "10-K",
            "filing_date": filing["filing_date"],
            "accession_number": filing["accession"],
            "company_facts_source": (
                f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company['cik']}.json"
            ),
            "filing_source": source,
        }
        if not all(math.isfinite(float(row[key])) for key in (
            "revenue_usd",
            "revenue_growth_pct",
            "net_income_usd",
            "net_margin_pct",
            "operating_income_usd",
            "operating_margin_pct",
            "diluted_eps_usd_per_share",
        )):
            raise RuntimeError(f"Non-finite calculation for {ticker} at {end}")
        rows.append(row)
        selected_facts[end] = revenue
    return rows, selected_facts


def write_csv(rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0])
    with (ROOT / "comparison.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            formatted = dict(row)
            for key in ("revenue_growth_pct", "net_margin_pct", "operating_margin_pct"):
                formatted[key] = f"{row[key]:.2f}"
            formatted["diluted_eps_usd_per_share"] = f"{row['diluted_eps_usd_per_share']:.2f}"
            writer.writerow(formatted)


def money_billions(value: float) -> str:
    return f"${value / 1_000_000_000:,.1f}B"


def pct(value: float) -> str:
    return f"{value:.1f}%"


def company_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: row["fiscal_year_end"])
    first, latest = ordered[0], ordered[-1]
    years = len(ordered) - 1
    return {
        "first": first,
        "latest": latest,
        "revenue_cagr": ((latest["revenue_usd"] / first["revenue_usd"]) ** (1 / years) - 1) * 100,
        "average_net_margin": sum(row["net_margin_pct"] for row in ordered) / len(ordered),
        "average_operating_margin": (
            sum(row["operating_margin_pct"] for row in ordered) / len(ordered)
        ),
    }


def narrative(rows: list[dict[str, Any]]) -> dict[str, str]:
    grouped = {ticker: [row for row in rows if row["ticker"] == ticker] for ticker in COMPANIES}
    apple = company_summary(grouped["AAPL"])
    microsoft = company_summary(grouped["MSFT"])
    a_latest, m_latest = apple["latest"], microsoft["latest"]
    larger = "Apple" if a_latest["revenue_usd"] > m_latest["revenue_usd"] else "Microsoft"
    smaller = "Microsoft" if larger == "Apple" else "Apple"
    larger_value = max(a_latest["revenue_usd"], m_latest["revenue_usd"])
    smaller_value = min(a_latest["revenue_usd"], m_latest["revenue_usd"])
    faster = "Apple" if apple["revenue_cagr"] > microsoft["revenue_cagr"] else "Microsoft"
    faster_cagr = max(apple["revenue_cagr"], microsoft["revenue_cagr"])
    slower = "Microsoft" if faster == "Apple" else "Apple"
    slower_cagr = min(apple["revenue_cagr"], microsoft["revenue_cagr"])
    return {
        "summary": (
            f"Apple remains the larger revenue platform at {money_billions(a_latest['revenue_usd'])}, "
            f"while Microsoft produces materially higher margins: its latest operating margin was "
            f"{pct(m_latest['operating_margin_pct'])} versus Apple's {pct(a_latest['operating_margin_pct'])}. "
            f"The comparison uses each issuer's own fiscal year and therefore avoids calendar-period mixing."
        ),
        "size": (
            f"{larger}'s latest annual revenue of {money_billions(larger_value)} exceeded {smaller}'s "
            f"{money_billions(smaller_value)}. Apple reports through {a_latest['fiscal_year_end']}; "
            f"Microsoft reports through {m_latest['fiscal_year_end']}, so the endpoints are not concurrent."
        ),
        "growth": (
            f"Across the five displayed fiscal years, {faster} delivered a {pct(faster_cagr)} revenue CAGR "
            f"versus {pct(slower_cagr)} for {slower}. Latest-year growth was "
            f"{pct(a_latest['revenue_growth_pct'])} for Apple and {pct(m_latest['revenue_growth_pct'])} "
            f"for Microsoft."
        ),
        "profitability": (
            f"Microsoft's latest net and operating margins were {pct(m_latest['net_margin_pct'])} and "
            f"{pct(m_latest['operating_margin_pct'])}, above Apple's {pct(a_latest['net_margin_pct'])} and "
            f"{pct(a_latest['operating_margin_pct'])}. The gap is consistent with Microsoft's more "
            f"software- and cloud-oriented economics versus Apple's hardware-heavy revenue base."
        ),
        "risks": (
            "Key interpretation risks are non-aligned fiscal calendars, product-cycle and supply-chain "
            "exposure at Apple, cloud/AI capital intensity and competition at Microsoft, and the possibility "
            "of later XBRL amendments or reclassifications. This memo is historical analysis, not a valuation "
            "or investment recommendation."
        ),
    }


def compact_table_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    output = []
    for row in sorted(rows, key=lambda item: (item["ticker"], item["fiscal_year_end"])):
        output.append({
            "company": row["ticker"],
            "fy_end": row["fiscal_year_end"],
            "revenue": money_billions(row["revenue_usd"]),
            "growth": pct(row["revenue_growth_pct"]),
            "net_income": money_billions(row["net_income_usd"]),
            "net_margin": pct(row["net_margin_pct"]),
            "operating_margin": pct(row["operating_margin_pct"]),
            "eps": f"${row['diluted_eps_usd_per_share']:.2f}",
        })
    return output


def write_html(rows: list[dict[str, Any]], verifications: list[dict[str, Any]]) -> None:
    text = narrative(rows)
    table_rows = compact_table_rows(rows)
    table = "\n".join(
        "<tr>" + "".join(f"<td>{html.escape(item[key])}</td>" for key in (
            "company", "fy_end", "revenue", "growth", "net_income", "net_margin", "operating_margin", "eps"
        )) + "</tr>"
        for item in table_rows
    )
    verification_note = " ".join(
        f"{item['ticker']} {item['fiscal_year_end']} revenue {money_billions(item['company_facts_value_usd'])} "
        f"matched the tagged value in the original 10-K ({item['accession_number']})."
        for item in verifications
    )
    source_links = "".join(
        f'<li><a href="{html.escape(item["source"])}">{item["ticker"]} Form 10-K</a> - '
        f'{item["filing_date"]}; revenue cross-check passed.</li>'
        for item in verifications
    )
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Apple vs Microsoft Equity Research Memo</title>
<style>
@page {{ size: Letter landscape; margin: 0.42in; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; color: #172033; background: #eef2f7; font-family: Arial, Helvetica, sans-serif; }}
.page {{ width: 10.16in; min-height: 7.66in; margin: 20px auto; padding: 0.36in 0.42in;
  background: white; box-shadow: 0 8px 30px #24324a22; }}
header {{ display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 3px solid #173f73;
  padding-bottom: 9px; margin-bottom: 10px; }}
h1 {{ font-size: 22px; margin: 0; letter-spacing: -0.4px; color: #102a4d; }}
.kicker {{ color: #2c6e9f; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.1px; }}
.date {{ font-size: 9px; color: #5d6879; text-align: right; }}
.summary {{ font-size: 10px; line-height: 1.35; background: #edf4fa; border-left: 4px solid #2c6e9f;
  padding: 8px 10px; margin-bottom: 9px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 8.2px; font-variant-numeric: tabular-nums; }}
th {{ background: #173f73; color: white; padding: 4px 5px; text-align: right; }}
th:first-child, th:nth-child(2), td:first-child, td:nth-child(2) {{ text-align: left; }}
td {{ padding: 3.5px 5px; border-bottom: 1px solid #dce3ec; text-align: right; }}
tr:nth-child(5n+1) td {{ border-top: 2px solid #91a9c1; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 9px; margin-top: 10px; }}
.section {{ border-top: 2px solid #2c6e9f; padding-top: 5px; }}
.section h2 {{ margin: 0 0 3px; color: #173f73; font-size: 10px; text-transform: uppercase; letter-spacing: .5px; }}
.section p {{ margin: 0; font-size: 8.4px; line-height: 1.35; }}
footer {{ margin-top: 9px; padding-top: 6px; border-top: 1px solid #aeb9c7; display: grid;
  grid-template-columns: 1.2fr 1fr; gap: 14px; font-size: 7.2px; line-height: 1.3; color: #4b5667; }}
footer ul {{ margin: 2px 0 0 13px; padding: 0; }}
a {{ color: #245f91; text-decoration: none; }}
@media print {{ body {{ background: white; }} .page {{ margin: 0; box-shadow: none; width: auto; min-height: auto; }} }}
</style>
</head>
<body><main class="page">
<header><div><div class="kicker">AI Coding in Finance | Equity Research</div>
<h1>Apple vs Microsoft: Scale, Growth &amp; Profitability</h1></div>
<div class="date">Historical fundamentals memo<br>Generated {date.today().isoformat()} | USD unless stated</div></header>
<div class="summary"><strong>Executive summary.</strong> {html.escape(text['summary'])}</div>
<table><thead><tr><th>Company</th><th>Fiscal year end</th><th>Revenue</th><th>YoY growth</th>
<th>Net income</th><th>Net margin</th><th>Operating margin</th><th>Diluted EPS</th></tr></thead>
<tbody>{table}</tbody></table>
<div class="grid">
<section class="section"><h2>Size</h2><p>{html.escape(text['size'])}</p></section>
<section class="section"><h2>Growth</h2><p>{html.escape(text['growth'])}</p></section>
<section class="section"><h2>Profitability</h2><p>{html.escape(text['profitability'])}</p></section>
</div>
<div class="grid">
<section class="section"><h2>Risks</h2><p>{html.escape(text['risks'])}</p></section>
<section class="section"><h2>10-K Cross-check</h2><p>{html.escape(verification_note)}</p></section>
<section class="section"><h2>Method</h2><p>Annual 10-K XBRL facts only; 300-380 day durations; five latest common fiscal ends per issuer. Growth uses the preceding annual revenue observation. Fiscal calendars remain separate.</p></section>
</div>
<footer><div><strong>Sources.</strong><ul>{source_links}</ul></div>
<div>SEC EDGAR XBRL Company Facts API for all table values and calculations. Original 10-K inline XBRL used only for the stated revenue checks. See <code>comparison.csv</code> for URLs, filing dates, accession numbers, full-dollar units and audit trail.</div></footer>
</main></body></html>"""
    (ROOT / "equity_research_memo.html").write_text(document, encoding="utf-8")


def latex_escape(value: str) -> str:
    replacements = {
        "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
        "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in value)


def write_tex(rows: list[dict[str, Any]], verifications: list[dict[str, Any]]) -> None:
    text = narrative(rows)
    table_lines = []
    for item in compact_table_rows(rows):
        table_lines.append(
            " & ".join(latex_escape(item[key]) for key in (
                "company", "fy_end", "revenue", "growth", "net_income", "net_margin", "operating_margin", "eps"
            )) + r" \\" 
        )
    verification_text = " ".join(
        f"{item['ticker']} {item['fiscal_year_end']} revenue {money_billions(item['company_facts_value_usd'])} "
        f"matched original 10-K accession {item['accession_number']}."
        for item in verifications
    )
    sources = " ".join(
        rf"\href{{{item['source']}}}{{{item['ticker']} 10-K ({item['filing_date']})}};"
        for item in verifications
    )
    tex = rf"""\documentclass[9pt]{{article}}
\usepackage[letterpaper,landscape,margin=0.42in]{{geometry}}
\usepackage{{array,booktabs,tabularx,xcolor,hyperref,microtype,helvet}}
\renewcommand{{\familydefault}}{{\sfdefault}}
\definecolor{{navy}}{{HTML}}{{173F73}}
\definecolor{{blue}}{{HTML}}{{2C6E9F}}
\definecolor{{pale}}{{HTML}}{{EDF4FA}}
\hypersetup{{colorlinks=true,urlcolor=blue}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{0pt}}
\pagestyle{{empty}}
\newcommand{{\sectionbox}}[2]{{\textcolor{{navy}}{{\bfseries\MakeUppercase{{#1}}}}\\[-1pt]
  {{\color{{blue}}\rule{{\linewidth}}{{0.8pt}}}}\\[-2pt]{{\footnotesize #2}}}}
\begin{{document}}
\begin{{minipage}}[b]{{0.72\linewidth}}
{{\scriptsize\color{{blue}}\bfseries AI CODING IN FINANCE $\mid$ EQUITY RESEARCH}}\\[2pt]
{{\LARGE\color{{navy}}\bfseries Apple vs Microsoft: Scale, Growth \& Profitability}}
\end{{minipage}}\hfill
\begin{{minipage}}[b]{{0.26\linewidth}}\raggedleft\scriptsize
Historical fundamentals memo\\Generated {date.today().isoformat()} $\mid$ USD unless stated
\end{{minipage}}\\[-1pt]
{{\color{{navy}}\rule{{\linewidth}}{{2.2pt}}}}\\[4pt]
\colorbox{{pale}}{{\parbox{{0.975\linewidth}}{{\footnotesize\textbf{{Executive summary.}} {latex_escape(text['summary'])}}}}}\\[5pt]
\scriptsize
\rowcolors{{2}}{{white}}{{pale}}
\begin{{tabularx}}{{\linewidth}}{{l l *{{6}}{{>{{\raggedleft\arraybackslash}}X}}}}
\rowcolor{{navy}}\color{{white}}\bfseries Company & \color{{white}}\bfseries FY end &
\color{{white}}\bfseries Revenue & \color{{white}}\bfseries YoY growth & \color{{white}}\bfseries Net income &
\color{{white}}\bfseries Net margin & \color{{white}}\bfseries Op. margin & \color{{white}}\bfseries Diluted EPS \\
{chr(10).join(table_lines)}
\end{{tabularx}}\\[6pt]
\begin{{minipage}}[t]{{0.32\linewidth}}\sectionbox{{Size}}{{{latex_escape(text['size'])}}}\end{{minipage}}\hfill
\begin{{minipage}}[t]{{0.32\linewidth}}\sectionbox{{Growth}}{{{latex_escape(text['growth'])}}}\end{{minipage}}\hfill
\begin{{minipage}}[t]{{0.32\linewidth}}\sectionbox{{Profitability}}{{{latex_escape(text['profitability'])}}}\end{{minipage}}\\[6pt]
\begin{{minipage}}[t]{{0.32\linewidth}}\sectionbox{{Risks}}{{{latex_escape(text['risks'])}}}\end{{minipage}}\hfill
\begin{{minipage}}[t]{{0.32\linewidth}}\sectionbox{{10-K Cross-check}}{{{latex_escape(verification_text)}}}\end{{minipage}}\hfill
\begin{{minipage}}[t]{{0.32\linewidth}}\sectionbox{{Method}}{{Annual 10-K XBRL facts only; 300--380 day durations; five latest common fiscal ends per issuer. Growth uses the preceding annual revenue observation.}}\end{{minipage}}\\[6pt]
{{\color{{navy}}\rule{{\linewidth}}{{0.5pt}}}}\\[2pt]
{{\tiny\textbf{{Sources.}} SEC EDGAR XBRL Company Facts API for all table values and calculations. {sources}
Original inline XBRL used for revenue checks. See comparison.csv for full-dollar units and audit trail.}}
\end{{document}}
"""
    (ROOT / "equity_research_memo.tex").write_text(tex, encoding="utf-8")


def compile_tex() -> dict[str, Any]:
    for command in ("latexmk", "pdflatex", "xelatex", "lualatex"):
        executable = shutil.which(command)
        if not executable:
            continue
        if command == "latexmk":
            arguments = [executable, "-pdf", "-interaction=nonstopmode", "-halt-on-error", "equity_research_memo.tex"]
        else:
            arguments = [executable, "-interaction=nonstopmode", "-halt-on-error", "equity_research_memo.tex"]
        result = subprocess.run(arguments, cwd=ROOT, capture_output=True, text=True, timeout=120)
        return {"attempted": True, "compiler": command, "returncode": result.returncode, "output": result.stdout[-4000:]}
    return {
        "attempted": False,
        "compiler": None,
        "returncode": None,
        "output": "No LaTeX compiler found. Run: pdflatex equity_research_memo.tex",
    }


def main() -> int:
    refresh = "--refresh" in sys.argv
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, Any]] = []
    company_payloads: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, AnnualFact]]] = {}
    for ticker, company in COMPANIES.items():
        facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company['cik']}.json"
        submissions_url = f"https://data.sec.gov/submissions/CIK{company['cik']}.json"
        company_facts = load_json(facts_url, DATA_DIR / f"{ticker.lower()}_companyfacts.json", refresh)
        submissions = load_json(submissions_url, DATA_DIR / f"{ticker.lower()}_submissions.json", refresh)
        rows, selected = build_company_rows(ticker, company, company_facts, submissions)
        all_rows.extend(rows)
        company_payloads[ticker] = (company_facts, submissions, selected)

    if len(all_rows) != 10:
        raise RuntimeError(f"Expected 10 output rows, found {len(all_rows)}")

    verifications = []
    for ticker, company in COMPANIES.items():
        _, submissions, selected = company_payloads[ticker]
        latest_end = max(selected)
        verifications.append(
            verify_revenue(ticker, company, selected[latest_end], submissions, refresh)
        )

    write_csv(all_rows)
    (ROOT / "verification.json").write_text(
        json.dumps(verifications, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_html(all_rows, verifications)
    write_tex(all_rows, verifications)
    compile_result = compile_tex()
    (ROOT / "build_status.json").write_text(
        json.dumps(
            {
                "generated_at": datetime.now().astimezone().isoformat(),
                "sec_user_agent": USER_AGENT,
                "rows": len(all_rows),
                "companies": list(COMPANIES),
                "verification_passed": all(item["matched"] for item in verifications),
                "latex": compile_result,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"Created comparison.csv with {len(all_rows)} rows")
    for item in verifications:
        print(
            f"Verified {item['ticker']} revenue {item['company_facts_value_usd']:,} USD "
            f"against 10-K {item['accession_number']}"
        )
    if compile_result["attempted"] and compile_result["returncode"] == 0:
        print(f"Compiled equity_research_memo.pdf with {compile_result['compiler']}")
    elif compile_result["attempted"]:
        raise RuntimeError(
            f"LaTeX compilation failed with {compile_result['compiler']}:\n{compile_result['output']}"
        )
    else:
        print(compile_result["output"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)



