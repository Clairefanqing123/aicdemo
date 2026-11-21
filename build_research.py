from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from aicdemo_research.pipeline import run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Apple vs. Microsoft equity research report")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--refresh", action="store_true", help="Refresh cached SEC source files")
    mode.add_argument("--offline", action="store_true", help="Forbid network access and require a complete cache")
    parser.add_argument("--skip-pdf", action="store_true", help="Generate data, charts, HTML and TeX without compiling PDF")
    args = parser.parse_args()
    status = run(refresh=args.refresh, offline=args.offline, skip_pdf=args.skip_pdf)
    print(
        f"Built {status['rows']} company-year rows, verified {status['raw_metrics_verified']} raw facts, "
        f"generated {status['figures']} figures and {status['references']} references."
    )
    if status["pdf"]:
        print(f"PDF: {status['pdf']['pdf']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
