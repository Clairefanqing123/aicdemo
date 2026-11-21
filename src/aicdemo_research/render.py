from __future__ import annotations

import html
import shutil
import subprocess
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import REPORTS, TEMPLATES, TEX_BIN
from .narrative import Section, money, pct


TITLE = "Apple vs. Microsoft: A Five-Year Comparative Fundamental Analysis"
LATEST_HEADERS = ["Company", "FY End", "Revenue", "Growth", "Gross Margin", "Op. Margin", "Net Margin", "FCF"]
CORE_HEADERS = ["Company", "FY End", "Revenue", "Growth", "Gross Margin", "Op. Margin", "Net Income", "Net Margin", "OCF", "Capex", "FCF", "EPS"]


def tex_escape(value: Any) -> str:
    replacements = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
        "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in str(value))


def _html_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{html.escape(x)}</th>" for x in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def latest_rows(rows: list[dict[str, Any]]) -> list[list[str]]:
    output: list[list[str]] = []
    for ticker in ("AAPL", "MSFT"):
        row = max((r for r in rows if r["ticker"] == ticker), key=lambda r: r["fiscal_year_end"])
        output.append([
            ticker, row["fiscal_year_end"], money(row["revenue_usd"]), pct(row["revenue_growth_pct"]),
            pct(row["gross_margin_pct"]), pct(row["operating_margin_pct"]), pct(row["net_margin_pct"]),
            money(row["free_cash_flow_usd"]),
        ])
    return output


def core_rows(rows: list[dict[str, Any]]) -> list[list[str]]:
    output: list[list[str]] = []
    for row in sorted(rows, key=lambda x: (x["ticker"], x["fiscal_year_end"])):
        output.append([
            row["ticker"], row["fiscal_year_end"], money(row["revenue_usd"]), pct(row["revenue_growth_pct"]),
            pct(row["gross_margin_pct"]), pct(row["operating_margin_pct"]), money(row["net_income_usd"]),
            pct(row["net_margin_pct"]), money(row["operating_cash_flow_usd"]), money(row["capital_expenditures_usd"]),
            money(row["free_cash_flow_usd"]), f"${row['diluted_eps_usd_per_share']:.2f}",
        ])
    return output


def render_html(
    sections: list[Section], rows: list[dict[str, Any]], references: list[dict[str, str]], generated_at: str,
    verification_count: int,
) -> Path:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))
    figures = {
        3: [
            {"src": "../figures/revenue_comparison.png", "caption": "Figure 1. Five-Year Revenue Comparison"},
            {"src": "../figures/revenue_growth.png", "caption": "Figure 2. Revenue Growth Comparison"},
        ],
        4: [
            {"src": "../figures/gross_margin.png", "caption": "Figure 3. Gross Margin Comparison"},
            {"src": "../figures/operating_margin.png", "caption": "Figure 4. Operating Margin Comparison"},
            {"src": "../figures/net_margin.png", "caption": "Figure 5. Net Margin Comparison"},
            {"src": "../figures/net_income.png", "caption": "Figure 6. Net Income Comparison"},
        ],
        5: [{"src": "../figures/cash_flow_capex.png", "caption": "Figure 7. Operating Cash Flow and Capital Expenditures Comparison"}],
    }
    document = env.get_template("report.html.j2").render(
        title=TITLE, generated_at=generated_at, sections=sections, figures_by_section=figures,
        latest_table=_html_table(LATEST_HEADERS, latest_rows(rows)),
        core_table=_html_table(CORE_HEADERS, core_rows(rows)), references=references,
        verification_count=verification_count,
    )
    path = REPORTS / "apple_vs_microsoft_report.html"
    path.write_text(document, encoding="utf-8")
    return path


def _tex_paragraphs(section: Section, indices: list[int] | None = None) -> str:
    paragraphs = section.paragraphs if indices is None else tuple(section.paragraphs[i] for i in indices)
    return "\n".join(r"\noindent " + tex_escape(paragraph) + r"\par" for paragraph in paragraphs)


def _tex_latest_table(rows: list[dict[str, Any]]) -> str:
    lines = [" & ".join(tex_escape(x) for x in row) + r" \\" for row in latest_rows(rows)]
    header = r"\rowcolor{navy}\color{white}\bfseries Company & \color{white}\bfseries FY End & \color{white}\bfseries Revenue & \color{white}\bfseries Growth & \color{white}\bfseries Gross M. & \color{white}\bfseries Op. M. & \color{white}\bfseries Net M. & \color{white}\bfseries FCF \\"
    return r"\par\noindent\scriptsize\rowcolors{2}{white}{pale}\begin{tabularx}{\linewidth}{l l *{6}{>{\raggedleft\arraybackslash}X}}" + "\n" + header + "\n" + "\n".join(lines) + "\n" + r"\end{tabularx}\par"


def _tex_core_table(rows: list[dict[str, Any]]) -> str:
    lines = [" & ".join(tex_escape(x) for x in row) + r" \\" for row in core_rows(rows)]
    header = r"\toprule Company & FY End & Revenue & Growth & Gross M. & Op. M. & Net Inc. & Net M. & OCF & Capex & FCF & EPS \\ \midrule\endhead"
    return r"\fontsize{7.2}{9.2}\selectfont\setlength{\tabcolsep}{1.9pt}\renewcommand{\arraystretch}{1.55}\rowcolors{2}{white}{pale}\begin{longtable}{l l r r r r r r r r r r}" + "\n" + header + "\n" + "\n".join(lines) + "\n" + r"\bottomrule\end{longtable}"


def _figure(name: str, width: str = r"0.93\linewidth") -> str:
    return rf"\begin{{center}}\includegraphics[width={width}]{{../figures/{name}.png}}\end{{center}}"


def render_tex(
    sections: list[Section], rows: list[dict[str, Any]], references: list[dict[str, str]], generated_at: str,
    verification_count: int,
) -> Path:
    executive = sections[0]
    pages = [
        r"{\scriptsize\color{blue}\bfseries FUNDAMENTAL EQUITY RESEARCH | HISTORICAL ANALYSIS}\par\vspace{5pt}"
        + rf"\reporttitle{{{tex_escape(TITLE)}}}\par\vspace{{5pt}}"
        + rf"{{\small\color{{muted}} Apple Inc. (AAPL) and Microsoft Corporation (MSFT) | FY2022--FY2026 | Generated {tex_escape(generated_at)}}}\par\vspace{{10pt}}"
        + r"{\color{navy}\rule{\linewidth}{2pt}}\par\vspace{5pt}"
        + r"\colorbox{pale}{\parbox{0.965\linewidth}{\textbf{Core conclusion.} " + tex_escape(executive.paragraphs[0]) + r"}}\par\vspace{4pt}"
        + _tex_paragraphs(executive, [1, 2]) + r"\vspace{8pt}\sectiontitle{Latest Fiscal Year Scorecard}" + _tex_latest_table(rows),
        r"\sectiontitle{2. Business Model and Revenue Drivers}" + _tex_paragraphs(sections[1]),
        r"\sectiontitle{3. Revenue and Growth Analysis}" + _tex_paragraphs(sections[2]) + _figure("revenue_comparison", r"0.72\linewidth") + _figure("revenue_growth", r"0.72\linewidth"),
        r"\sectiontitle{4. Profitability Analysis}" + _tex_paragraphs(sections[3], [0, 1])
        + _figure("gross_margin", r"0.78\linewidth") + _figure("operating_margin", r"0.78\linewidth"),
        r"\sectiontitle{4. Profitability Analysis (continued)}" + _tex_paragraphs(sections[3], [2])
        + _figure("net_margin", r"0.86\linewidth") + _figure("net_income", r"0.86\linewidth")
        + r"\vspace{8pt}\sourcefoot{Absolute EPS is retained in Appendix A for within-company trend analysis only.}",
        r"\sectiontitle{5. Cash Flow and Capital Investment}" + _tex_paragraphs(sections[4]) + _figure("cash_flow_capex", r"0.96\linewidth"),
        r"\sectiontitle{6. Comparative Assessment and Key Risks}" + _tex_paragraphs(sections[5]),
    ]
    body = ("\n\\newpage\n").join(pages)
    body += "\n\\newpage\n" + r"\sectiontitle{Appendix A. Methodology}" + _tex_paragraphs(sections[6])
    body += "\n\\newpage\n" + r"\sectiontitle{Appendix B. Five-Year Core Financial Data}" + _tex_core_table(rows)
    body += "\n\\newpage\n" + rf"\sectiontitle{{Appendix C. Data Lineage and Verification}}All {verification_count} raw observations were matched to consolidated, non-dimensional inline XBRL contexts in the corresponding original Form 10-K. Derived metrics were recalculated from unrounded values.\par\vspace{{8pt}}\textbf{{Formulas}}\par Revenue growth = Revenue / prior-year Revenue - 1. Gross, operating and net margins divide the corresponding GAAP profit by Revenue. Free cash flow = Operating Cash Flow - cash purchases of property and equipment. Capex intensity = cash Capital Expenditures / Revenue."
    body += "\n\\newpage\n" + r"\sectiontitle{References}\small\begin{enumerate}" + "\n".join(rf"\item {ref['tex']}" for ref in references) + r"\end{enumerate}"
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=False, variable_start_string="<<", variable_end_string=">>")
    path = REPORTS / "apple_vs_microsoft_report.tex"
    path.write_text(env.get_template("report.tex.j2").render(body=body), encoding="utf-8")
    return path


def compile_pdf(tex_path: Path) -> dict[str, Any]:
    latexmk = TEX_BIN / "latexmk.exe"
    if not latexmk.exists():
        found = shutil.which("latexmk")
        if not found:
            raise RuntimeError(f"TeX compiler not found at {latexmk}")
        latexmk = Path(found)
    result = subprocess.run(
        [str(latexmk), "-xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
        cwd=tex_path.parent, capture_output=True, text=True, timeout=240,
    )
    if result.returncode != 0:
        raise RuntimeError(f"LaTeX failed:\n{result.stdout[-6000:]}\n{result.stderr[-2000:]}")
    pdf = tex_path.with_suffix(".pdf")
    if not pdf.exists():
        raise RuntimeError("LaTeX reported success but PDF was not created")
    return {"compiler": str(latexmk), "returncode": result.returncode, "pdf": str(pdf), "log_tail": result.stdout[-1500:]}
