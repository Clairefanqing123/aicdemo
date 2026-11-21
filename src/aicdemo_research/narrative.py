from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def money(value: float) -> str:
    return f"${value / 1e9:,.1f}bn"


def pct(value: float) -> str:
    return f"{value:.1f}%"


@dataclass(frozen=True)
class Section:
    title: str
    paragraphs: tuple[str, ...]


def build_sections(summary: dict[str, Any]) -> list[Section]:
    a = summary["AAPL"]
    m = summary["MSFT"]
    al, ml = a["latest"], m["latest"]
    return [
        Section(
            "Executive Summary",
            (
                f"Apple remains the larger revenue platform, with FY2026 revenue of {money(al['revenue_usd'])} "
                f"versus Microsoft's {money(ml['revenue_usd'])}. Microsoft, however, delivered the stronger "
                f"five-year growth profile: revenue compounded at {pct(m['revenue_cagr_pct'])} from FY2022 to "
                f"FY2026, compared with {pct(a['revenue_cagr_pct'])} for Apple. The result is a clear split between "
                "Apple's greater current scale and Microsoft's faster expansion. [1]-[10]",
                f"Profitability strengthens the case for Microsoft's operating model. Its FY2026 operating margin "
                f"of {pct(ml['operating_margin_pct'])} exceeded Apple's {pct(al['operating_margin_pct'])}, while "
                f"net income of {money(ml['net_income_usd'])} was slightly above Apple's {money(al['net_income_usd'])} "
                "despite materially lower revenue. The comparison points to the economic advantage of a business "
                "mix weighted toward cloud infrastructure and software subscriptions. [5][10]",
                f"Cash generation presents the counterweight. Apple produced {money(al['free_cash_flow_usd'])} of "
                f"derived free cash flow in FY2026 on cash capital expenditures of {money(al['capital_expenditures_usd'])}. "
                f"Microsoft generated {money(ml['free_cash_flow_usd'])} after capital expenditures rose to "
                f"{money(ml['capital_expenditures_usd'])}. Microsoft therefore offers the stronger growth and margin "
                "profile, while Apple currently converts revenue into post-capex cash with far lower owned-asset "
                "intensity. This report evaluates operating fundamentals and does not provide a valuation or rating. [5][10]",
            ),
        ),
        Section(
            "Business Model and Revenue Drivers",
            (
                "Apple combines a global installed base of devices with a growing set of services distributed through "
                "the same ecosystem. Hardware remains central to revenue and exposes reported growth to replacement "
                "cycles, launch timing, component availability and consumer demand. Services add recurring and higher-"
                "margin activity, helping explain why gross margin expanded over the period even when aggregate revenue "
                "growth was uneven. Apple's filing identifies products and services as distinct economic streams, so the "
                "margin progression is better read as a mix outcome than as a simple pricing effect. [5]",
                "Microsoft's revenue base is more heavily tied to cloud consumption, enterprise software subscriptions "
                "and long-duration customer relationships. Azure and related cloud services expand the addressable market "
                "and support recurring revenue, while Office, Windows, security, gaming and professional-network products "
                "diversify the platform. This structure is consistent with faster consolidated growth and substantially "
                "higher margins, but it increasingly requires Microsoft to fund servers, data centers and other AI-related "
                "infrastructure before the associated revenue is fully realized. [10]",
                "The difference is not a simple contrast between hardware and software. Apple outsources much of its "
                "manufacturing footprint but invests heavily in product development and ecosystem control; Microsoft owns "
                "a growing portion of the infrastructure needed to deliver cloud and AI services. The financial statements "
                "therefore show Apple as the less capital-intensive cash generator and Microsoft as the faster-growing, "
                "higher-margin operator with a rising infrastructure burden. [5][10]",
            ),
        ),
        Section(
            "Revenue and Growth Analysis",
            (
                f"Apple's revenue increased from {money(a['first']['revenue_usd'])} in FY2022 to "
                f"{money(al['revenue_usd'])} in FY2026, a {pct(a['revenue_cagr_pct'])} CAGR. The path was not linear: "
                "revenue declined in FY2023 and grew only modestly in FY2024 before accelerating in FY2025 and FY2026. "
                "That pattern is consistent with a mature, product-cycle-sensitive platform whose installed base and "
                "services activity can support growth but do not remove annual hardware volatility. [1]-[5]",
                f"Microsoft expanded from {money(m['first']['revenue_usd'])} to {money(ml['revenue_usd'])} over the same "
                f"fiscal-year labels, producing a {pct(m['revenue_cagr_pct'])} CAGR. After growth slowed in FY2023, the "
                "company returned to mid-teens expansion for the next three years. The steadier acceleration indicates "
                "that cloud consumption and subscription revenue provided a broader and more persistent growth engine than "
                "Apple's predominantly device-led model. [6]-[10]",
                "The fiscal calendars are not concurrent: Microsoft's year ends on June 30, while Apple's closes in late "
                "September. FY labels are retained because they reflect the audited reporting periods used by each issuer, "
                "but a difference between same-labelled years should not be interpreted as a comparison of identical "
                "calendar months. The conclusions emphasize multi-year direction rather than short-term timing differences. [11][12]",
            ),
        ),
        Section(
            "Profitability Analysis",
            (
                f"Microsoft sustained a structural profitability advantage. FY2026 gross, operating and net margins were "
                f"{pct(ml['gross_margin_pct'])}, {pct(ml['operating_margin_pct'])} and {pct(ml['net_margin_pct'])}, "
                f"respectively, compared with Apple's {pct(al['gross_margin_pct'])}, "
                f"{pct(al['operating_margin_pct'])} and {pct(al['net_margin_pct'])}. Software licensing, subscriptions "
                "and cloud scale allow a larger share of incremental revenue to reach operating income even as Microsoft "
                "funds a substantial engineering and infrastructure base. [5][10]",
                f"Apple nevertheless improved gross margin from {pct(a['first']['gross_margin_pct'])} in FY2022 to "
                f"{pct(al['gross_margin_pct'])} in FY2026, and operating margin rose from "
                f"{pct(a['first']['operating_margin_pct'])} to {pct(al['operating_margin_pct'])}. The movement indicates "
                "that mix and operating discipline strengthened unit economics despite a slower revenue CAGR. Net margin "
                "was more variable because below-operating-line items and taxes can obscure the underlying operating trend. [1]-[5]",
                "Absolute diluted EPS is not comparable across the two companies because share counts and repurchase "
                "programs differ. Within each company, however, EPS remains useful for assessing whether profit growth and "
                "capital returns translated into per-share results. The report therefore includes EPS in the data appendix "
                "but bases the cross-company profitability judgment on margins and aggregate income. [1]-[10]",
            ),
        ),
        Section(
            "Cash Flow and Capital Investment",
            (
                f"Apple generated {money(al['operating_cash_flow_usd'])} of operating cash flow in FY2026 and spent "
                f"{money(al['capital_expenditures_usd'])} on property and equipment, leaving derived free cash flow of "
                f"{money(al['free_cash_flow_usd'])}. Capex represented only {pct(al['capex_intensity_pct'])} of revenue. "
                "This low cash capital intensity reflects a model in which Apple controls design, software and ecosystem "
                "economics without owning the full manufacturing chain. [5]",
                f"Microsoft produced higher FY2026 operating cash flow of {money(ml['operating_cash_flow_usd'])}, but cash "
                f"capital expenditures reached {money(ml['capital_expenditures_usd'])}, or "
                f"{pct(ml['capex_intensity_pct'])} of revenue. As a result, free cash flow was "
                f"{money(ml['free_cash_flow_usd'])}, only modestly above its FY2022 level despite the large increase in "
                "revenue and operating cash flow. The financial trade-off is direct: AI and cloud capacity can sustain future "
                "growth, but near-term cash conversion depends on utilization and monetization catching up with investment. [6][10]",
                "Free cash flow is calculated here as operating cash flow less cash purchases of property and equipment. "
                "It is not a GAAP subtotal and does not capture all contractual commitments, finance leases or acquisition "
                "spending. The measure is used consistently for both issuers because it isolates the cash cost of sustaining "
                "and expanding owned productive assets. [11][12]",
            ),
        ),
        Section(
            "Comparative Assessment and Key Risks",
            (
                "Microsoft ranks higher on growth persistence and operating profitability, while Apple ranks higher on "
                "current revenue scale and post-capex cash efficiency. Neither advantage is unconditional. Microsoft's "
                "capital program raises the amount of demand, pricing and utilization required to earn attractive incremental "
                "returns. Apple's low capital intensity supports cash generation, but its mature revenue base places more "
                "weight on product innovation, installed-base monetization and services mix. [5][10]",
                "For Apple, the key variables are device replacement cycles, services growth and regulation, supply-chain "
                "and geographic concentration, and the ability to sustain recent margin gains. For Microsoft, the key "
                "variables are Azure and AI revenue growth, data-center utilization, depreciation pressure, energy and chip "
                "availability, cybersecurity execution and cloud competition. These risks affect operating outcomes; they "
                "do not by themselves establish whether either stock is attractively valued. [5][10]",
                "The preferred monitoring framework is therefore asymmetric. Apple should be evaluated on whether ecosystem "
                "monetization can lift growth without sacrificing its exceptional cash profile. Microsoft should be evaluated "
                "on whether AI-driven revenue and gross profit scale rapidly enough to absorb the step-up in invested capital. "
                "A valuation conclusion would require market prices, forecasts, cost of capital and scenario analysis that are "
                "outside this report's historical-fundamentals scope.",
            ),
        ),
        Section(
            "Methodology",
            (
                "The analysis uses SEC EDGAR Company Facts for standardized GAAP observations and each issuer's original "
                "Form 10-K for filing metadata, qualitative interpretation and cross-checking. Eligible facts must be annual "
                "10-K observations marked FY, span 300 to 380 days, match the fiscal year of the period end and use the "
                "specified USD or USD-per-share unit. All seven raw metrics are reconciled to non-dimensional consolidated "
                "inline XBRL contexts in the corresponding original filing. [1]-[12]",
                "Revenue growth uses the immediately preceding annual revenue observation. Margins divide the relevant GAAP "
                "profit measure by revenue. Free cash flow equals operating cash flow less cash purchases of property and "
                "equipment, while capex intensity divides that cash expenditure by revenue. The five-year CAGR spans four "
                "annual intervals. Figures are displayed in billions and percentages, but calculations use unrounded values.",
                "Apple and Microsoft retain their own fiscal calendars. The approach avoids fabricating calendar-year "
                "alignment and explicitly discloses each fiscal year-end. Later amendments or issuer reclassifications can "
                "change Company Facts; the cached source files, accession numbers and verification records preserve the exact "
                "evidence used for this build. Access dates appear in the references.",
            ),
        ),
    ]
