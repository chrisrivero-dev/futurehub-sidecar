"""
cli_rollup.py
CLI entrypoint for generating weekly rollups.

Usage:
    python cli_rollup.py                    # Default: last 7 days
    python cli_rollup.py --start 2025-01-01 --end 2025-01-08
"""

import argparse
import json
import sys

from audit.rollup import compute_weekly_rollup


def main():
    parser = argparse.ArgumentParser(description="Generate weekly audit rollup")
    parser.add_argument("--start", help="Start date (ISO format)", default=None)
    parser.add_argument("--end", help="End date (ISO format)", default=None)
    args = parser.parse_args()

    print("Computing weekly rollup...")
    metrics = compute_weekly_rollup(start_date=args.start, end_date=args.end)
    print(json.dumps(metrics, indent=2))
    print("\nRollup persisted to SQLite.")


if __name__ == "__main__":
    main()
