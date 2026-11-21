# AI Coding in Finance: Apple vs Microsoft

## Research task

Build a reproducible comparison of Apple Inc. (AAPL) and Microsoft Corporation
(MSFT) using their five most recent complete fiscal years. Analyze revenue,
revenue growth, net income, net margin, operating margin, and diluted EPS, then
produce a concise English equity research memo.

## Data sources

- SEC EDGAR XBRL Company Facts API only for calculated financial data:
  - Apple CIK 0000320193: `https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json`
  - Microsoft CIK 0000789019: `https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json`
- SEC EDGAR submissions API for 10-K accession numbers and primary-document links.
- Original SEC 10-K inline XBRL documents for an independent latest-year revenue
  cross-check for each company.

Raw SEC responses and filing documents are cached under `data/sec/` so the
process is auditable and repeatable.

## Method

1. Request SEC JSON with a descriptive User-Agent and cache the responses.
2. Use only `us-gaap` facts reported on Form 10-K with fiscal-period marker `FY`.
3. Keep annual durations of 300-380 days and require the fact fiscal year to
   match the year of its period end, preventing quarterly and comparative-period
   duplicates from entering the series.
4. Use `RevenueFromContractWithCustomerExcludingAssessedTax`, `NetIncomeLoss`,
   `OperatingIncomeLoss`, and `EarningsPerShareDiluted` in USD or USD/share.
5. Select the latest five common complete fiscal-year ends. Revenue growth for
   the earliest displayed year is calculated from the immediately preceding
   annual revenue fact, so six revenue observations are fetched when available.
6. Calculate net margin and operating margin from SEC facts without mixing the
   companies' different fiscal calendars.
7. Cross-check the latest displayed revenue against the same tagged fact in the
   corresponding original SEC 10-K inline XBRL document. Save the audit result
   in `verification.json`.

## Delivery standard

- `comparison.csv` contains five annual rows per company, explicit dates, units,
  filing metadata, and SEC source URLs.
- `equity_research_memo.tex` and `equity_research_memo.html` contain consistent,
  data-driven English conclusions and a professional one-page layout.
- The LaTeX source is compiled to `equity_research_memo.pdf` when a supported
  compiler is installed. No data may be fabricated if SEC access fails.
- The build exits non-zero on missing facts, failed 10-K verification, non-finite
  calculations, or an unexpected row count.

