from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .scraper import ALL_PROJECTS_CSV, ALL_PROJECTS_JSON, NEUROLOGY_PROJECTS_JSON, PROJECT_ROOT
from .site_builder import PAGES_DIR, SITE_DIR, UI_PAYLOAD_JSON

DOWNLOAD_SOURCES = [
    ALL_PROJECTS_JSON,
    ALL_PROJECTS_CSV,
    NEUROLOGY_PROJECTS_JSON,
]
STATIC_FILES = [
    "index.html",
    "styles.css",
    "app.js",
    "data.js",
    "favicon.svg",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def duplicate_values(values: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    duplicates: set[Any] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates, key=str)


def validate_outputs() -> list[str]:
    errors: list[str] = []
    required_paths = [
        ALL_PROJECTS_JSON,
        ALL_PROJECTS_CSV,
        NEUROLOGY_PROJECTS_JSON,
        UI_PAYLOAD_JSON,
    ]
    for path in required_paths:
        if not path.is_file():
            errors.append(f"Missing required output: {path.relative_to(PROJECT_ROOT)}")

    if errors:
        return errors

    all_projects = load_json(ALL_PROJECTS_JSON)
    neurology_projects = load_json(NEUROLOGY_PROJECTS_JSON)
    payload = load_json(UI_PAYLOAD_JSON)

    if not isinstance(all_projects, list):
        return ["data/projects_all.json must contain a JSON array"]
    if not isinstance(neurology_projects, list):
        return ["data/projects_neurology.json must contain a JSON array"]
    if not isinstance(payload, dict):
        return ["data/neurology_ui_payload.json must contain a JSON object"]

    all_ids = [project.get("project_id") for project in all_projects]
    all_urls = [project.get("url") for project in all_projects]
    duplicate_ids = duplicate_values(all_ids)
    duplicate_urls = duplicate_values(all_urls)
    if duplicate_ids:
        errors.append(f"Duplicate project IDs: {duplicate_ids[:10]}")
    if duplicate_urls:
        errors.append(f"Duplicate project URLs: {duplicate_urls[:10]}")

    for field in ["project_id", "title", "url"]:
        missing = sum(not project.get(field) for project in all_projects)
        if missing:
            errors.append(f"{missing} project rows are missing {field}")

    scrape_errors = [project for project in all_projects if project.get("error")]
    if scrape_errors:
        errors.append(f"{len(scrape_errors)} project rows contain scrape errors")

    expected_neurology_ids = {
        project.get("project_id")
        for project in all_projects
        if project.get("matches_neurology_online_filter")
    }
    neurology_ids = {project.get("project_id") for project in neurology_projects}
    payload_ids = {project.get("project_id") for project in payload.get("projects", [])}
    if neurology_ids != expected_neurology_ids:
        errors.append("Neurology subset does not match the online-filter flags in projects_all.json")
    if payload_ids != neurology_ids:
        errors.append("UI payload project IDs do not match projects_neurology.json")

    overview = payload.get("overview", {})
    expected_counts = {
        "totalProjectsScraped": len(all_projects) - len(scrape_errors),
        "neurologyProjects": len(neurology_projects),
        "exclusiveNeurologyProjects": sum(
            project.get("neurology_focus_scope") == "exclusive"
            for project in neurology_projects
        ),
        "multiFocusNeurologyProjects": sum(
            project.get("neurology_focus_scope") == "multiple"
            for project in neurology_projects
        ),
    }
    for key, expected in expected_counts.items():
        if overview.get(key) != expected:
            errors.append(
                f"UI payload {key} is {overview.get(key)!r}; expected {expected}"
            )

    for source in DOWNLOAD_SOURCES:
        source_bytes = source.read_bytes()
        for root in [SITE_DIR, PAGES_DIR]:
            target = root / "downloads" / source.name
            if not target.is_file():
                errors.append(f"Missing download mirror: {target.relative_to(PROJECT_ROOT)}")
            elif target.read_bytes() != source_bytes:
                errors.append(f"Stale download mirror: {target.relative_to(PROJECT_ROOT)}")

    for filename in STATIC_FILES:
        source = SITE_DIR / filename
        target = PAGES_DIR / filename
        if not source.is_file():
            errors.append(f"Missing site asset: {source.relative_to(PROJECT_ROOT)}")
        elif not target.is_file():
            errors.append(f"Missing Pages asset: {target.relative_to(PROJECT_ROOT)}")
        elif source.read_bytes() != target.read_bytes():
            errors.append(f"Pages asset is stale: {target.relative_to(PROJECT_ROOT)}")

    if not (PAGES_DIR / ".nojekyll").is_file():
        errors.append("Missing docs/.nojekyll")

    return errors


def main() -> None:
    errors = validate_outputs()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Validated datasets, UI payload, download mirrors, and Pages assets")


if __name__ == "__main__":
    main()
