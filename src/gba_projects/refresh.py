from __future__ import annotations

import argparse
import time

from .scraper import ScrapeConfig, scrape_projects
from .site_builder import build_payload, write_payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape the live dataset and rebuild the neurology explorer.")
    parser.add_argument("--force", action="store_true", help="Ignore cached HTML and refetch from the source site.")
    parser.add_argument("--delay", type=float, default=0.05, help="Delay between HTTP requests in seconds.")
    parser.add_argument("--limit", type=int, default=None, help="Only scrape the first N detail pages.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    started = time.perf_counter()
    projects = scrape_projects(ScrapeConfig(force=args.force, delay=args.delay, limit=args.limit))
    payload = build_payload(projects)
    write_payload(payload)
    elapsed = time.perf_counter() - started
    print(
        f"Refresh complete in {elapsed:.1f}s "
        f"({payload['overview']['totalProjectsScraped']} projects, "
        f"{payload['overview']['neurologyProjects']} neurology)"
    )


if __name__ == "__main__":
    main()

