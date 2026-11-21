# aicdemo

Reproducible SEC-based comparison of Apple Inc. and Microsoft Corporation for their five most recent complete fiscal years. The pipeline produces a professional English equity research report in HTML, LaTeX and PDF, together with verified datasets, charts and a complete source manifest.

## Build

```powershell
python build_research.py
python build_research.py --offline
python build_research.py --refresh
```

The default build is cache-first and fetches only missing SEC files. `--offline` requires a complete local cache. `--refresh` replaces cached SEC responses. Set `SEC_USER_AGENT` to a descriptive SEC-compliant identity when refreshing.

PDF compilation uses the existing TeX Live installation at `D:\texlive\2026\bin\windows`. No TeX installation is performed by the project.

## Data and methodology

- Raw SEC Company Facts, submissions metadata and original 10-K documents are stored under `data/raw/sec/`.
- Processed wide and long datasets, source lineage and the 70-record XBRL cross-check are stored under `data/processed/`.
- Revenue, gross profit, operating income, net income, diluted EPS, operating cash flow and cash purchases of property and equipment are GAAP facts.
- Revenue growth and margins are calculated from unrounded facts.
- Free cash flow is a non-GAAP derived measure: operating cash flow less cash purchases of property and equipment.
- Apple and Microsoft retain their own fiscal calendars; the report does not fabricate calendar-year alignment.

## Outputs

- `output/figures/`: seven Python-generated charts.
- `output/tables/`: five-year core financial data and latest-year comparison.
- `output/reports/`: HTML, LaTeX, compiled PDF and build status.
- `output/legacy/`: preserved copies of the original one-page memo artifacts.

The build fails on missing facts, mixed accessions, incomplete annual series, non-finite calculations, failed inline-XBRL verification, an unexpected row count or a LaTeX compilation error.
