"""refresh.py — one-command SiteDocs export + warehouse ingest + dashboard serve.

Mirrors the QuickBooks refresh pipeline but for SiteDocs HSE data.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("refresh")

ROOT = Path(__file__).resolve().parent


def run(args: list[str]) -> None:
    logger.info("$ %s", " ".join(args))
    subprocess.check_call(args, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="SiteDocs data refresh pipeline")
    parser.add_argument("--no-export", action="store_true", help="Skip the QuickBooks pull")
    parser.add_argument("--no-serve", action="store_true", help="Don't start the dashboard")
    args = parser.parse_args()

    # 1. Ensure the Postgres warehouse is running
    logger.info("═══ Step 1: warehouse ═══")
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", "ews-warehouse"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or result.stdout.strip() != "true":
        logger.info("Starting warehouse container…")
        run(["docker", "start", "ews-warehouse"])
    else:
        logger.info("Warehouse already running ✓")

    # 2. Export SiteDocs data to CSVs
    if not args.no_export:
        logger.info("\n═══ Step 2: SiteDocs export ═══")
        run([sys.executable, "-m", "src.main"])

    # 3. Ingest CSVs into the warehouse
    logger.info("\n═══ Step 3: warehouse ingest ═══")
    run([sys.executable, "database/ingest.py"])

    # 4. Serve the dashboard
    if not args.no_serve:
        logger.info("\n═══ Step 4: dashboard ═══")
        port = 5001
        logger.info("Starting dashboard on http://localhost:%s", port)
        run([sys.executable, "visualize_fasthtml/app.py"])


if __name__ == "__main__":
    main()
