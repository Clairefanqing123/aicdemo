from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .config import FIGURES


COLORS = {"AAPL": "#2F6B9A", "MSFT": "#D9862C"}


def _group(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["ticker"]].append(row)
    for values in grouped.values():
        values.sort(key=lambda row: row["fiscal_year"])
    return grouped


def _style(ax: Any, title: str, ylabel: str) -> None:
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color="#16324F", pad=12)
    ax.set_ylabel(ylabel, fontsize=9, color="#44546A")
    ax.grid(axis="y", color="#D9E1E8", linewidth=0.7)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="both", labelsize=8, colors="#44546A")
    ax.text(
        0,
        -0.22,
        "Source: SEC EDGAR Company Facts and Forms 10-K. Fiscal years use each issuer's own year-end.",
        transform=ax.transAxes,
        fontsize=6.8,
        color="#667085",
    )


def _line_chart(
    rows: list[dict[str, Any]], field: str, title: str, ylabel: str, filename: str, scale: float = 1.0
) -> Path:
    grouped = _group(rows)
    fig, ax = plt.subplots(figsize=(7.2, 3.25), dpi=180)
    years = [f"FY{x}" for x in range(2022, 2027)]
    for ticker in ("AAPL", "MSFT"):
        values = [row[field] / scale for row in grouped[ticker]]
        ax.plot(years, values, marker="o", linewidth=2.2, label=ticker, color=COLORS[ticker])
        for x, value in zip(years, values):
            ax.annotate(f"{value:.1f}", (x, value), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=7)
    _style(ax, title, ylabel)
    ax.legend(frameon=False, ncol=2, loc="upper left", fontsize=8)
    fig.tight_layout()
    path = FIGURES / filename
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def cash_flow_chart(rows: list[dict[str, Any]]) -> Path:
    grouped = _group(rows)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.35), dpi=180, sharey=True)
    years = np.arange(5)
    labels = [f"FY{x}" for x in range(2022, 2027)]
    width = 0.25
    for ax, ticker in zip(axes, ("AAPL", "MSFT")):
        values = grouped[ticker]
        ocf = [x["operating_cash_flow_usd"] / 1e9 for x in values]
        capex = [x["capital_expenditures_usd"] / 1e9 for x in values]
        fcf = [x["free_cash_flow_usd"] / 1e9 for x in values]
        ax.bar(years - width, ocf, width, color="#2F6B9A", label="OCF")
        ax.bar(years, capex, width, color="#D9862C", label="Cash capex")
        ax.bar(years + width, fcf, width, color="#5A9A6E", label="FCF")
        ax.set_title(ticker, fontsize=10, fontweight="bold", color="#16324F")
        ax.set_xticks(years, labels, fontsize=7)
        ax.grid(axis="y", color="#D9E1E8", linewidth=0.7)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", labelsize=7)
    axes[0].set_ylabel("USD billions", fontsize=9)
    axes[0].legend(frameon=False, fontsize=7, ncol=3, loc="upper left")
    fig.suptitle(
        "Operating Cash Flow, Cash Capital Expenditures and Free Cash Flow",
        x=0.06,
        ha="left",
        fontsize=12,
        fontweight="bold",
        color="#16324F",
    )
    fig.text(
        0.06,
        0.01,
        "Source: SEC EDGAR Company Facts and Forms 10-K. FCF = OCF - cash purchases of property and equipment.",
        fontsize=6.8,
        color="#667085",
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    path = FIGURES / "cash_flow_capex.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def generate_charts(rows: list[dict[str, Any]]) -> dict[str, str]:
    specs = [
        ("revenue_usd", "Five-Year Revenue Comparison", "USD billions", "revenue_comparison.png", 1e9),
        ("revenue_growth_pct", "Revenue Growth Comparison", "Year-over-year growth (%)", "revenue_growth.png", 1),
        ("gross_margin_pct", "Gross Margin Comparison", "Gross margin (%)", "gross_margin.png", 1),
        ("operating_margin_pct", "Operating Margin Comparison", "Operating margin (%)", "operating_margin.png", 1),
        ("net_margin_pct", "Net Margin Comparison", "Net margin (%)", "net_margin.png", 1),
        ("net_income_usd", "Net Income Comparison", "USD billions", "net_income.png", 1e9),
    ]
    paths = {
        filename.removesuffix(".png"): str(_line_chart(rows, field, title, ylabel, filename, scale))
        for field, title, ylabel, filename, scale in specs
    }
    paths["cash_flow_capex"] = str(cash_flow_chart(rows))
    return paths
