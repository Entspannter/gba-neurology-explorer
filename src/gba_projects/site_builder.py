from __future__ import annotations

import argparse
import shutil
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .scraper import ALL_PROJECTS_JSON, DATA_DIR, LIST_URL, PROJECT_ROOT

SITE_DIR = PROJECT_ROOT / "site"
PAGES_DIR = PROJECT_ROOT / "docs"
SITE_DATA_JS = SITE_DIR / "data.js"
UI_PAYLOAD_JSON = DATA_DIR / "neurology_ui_payload.json"

STATE_ORDER = [
    "Schleswig-Holstein",
    "Hamburg",
    "Mecklenburg-Vorpommern",
    "Bremen",
    "Niedersachsen",
    "Berlin",
    "Brandenburg",
    "Nordrhein-Westfalen",
    "Sachsen-Anhalt",
    "Hessen",
    "Thüringen",
    "Sachsen",
    "Rheinland-Pfalz",
    "Saarland",
    "Baden-Württemberg",
    "Bayern",
]


def clean_text(value: str | None) -> str:
    return " ".join((value or "").split()).strip()


def ordered_states(state_counter: Counter[str]) -> list[str]:
    seen = set(STATE_ORDER)
    extras = sorted((state for state in state_counter if state not in seen), key=str.casefold)
    return [*STATE_ORDER, *extras]


def sentence_summary(text: str, max_chars: int = 240) -> str:
    cleaned = clean_text(text)
    if len(cleaned) <= max_chars:
        return cleaned
    cut = cleaned[: max_chars + 1]
    if ". " in cut:
        return cut.rsplit(". ", 1)[0].strip() + "."
    return cut.rsplit(" ", 1)[0].strip() + " ..."


def load_projects(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Input dataset not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def compact_project(project: dict[str, Any]) -> dict[str, Any]:
    lead = project.get("project_lead") or {}
    states = project.get("states") or ["Ohne Zuordnung"]
    documents = []
    for key in ["result_documents", "additional_documents"]:
        for document in project.get(key, []):
            documents.append(document)

    return {
        "project_id": project.get("project_id"),
        "slug": project.get("slug"),
        "title": project.get("title"),
        "acronym": project.get("acronym"),
        "url": project.get("url"),
        "summary": sentence_summary(project.get("description", "")),
        "description": project.get("description", ""),
        "status": project.get("status", ""),
        "states": states,
        "thematicFocuses": project.get("thematic_focuses", []),
        "targetGroups": project.get("target_groups", []),
        "careSetting": project.get("care_setting", ""),
        "fundingCategory": project.get("funding_category", ""),
        "fundingArea": project.get("funding_area", ""),
        "fundingProcess": project.get("funding_process", ""),
        "fundingSumLabel": project.get("funding_sum_label", ""),
        "fundingSumEur": project.get("funding_sum_eur"),
        "duration": project.get("duration_raw", ""),
        "startDate": project.get("start_date"),
        "endDate": project.get("end_date"),
        "transferRecommendation": project.get("transfer_recommendation", ""),
        "projectLead": lead,
        "projectLeadCity": project.get("project_lead_city"),
        "partners": project.get("consortium_partners", []),
        "projectWebsites": project.get("project_websites", []),
        "decisionDate": project.get("decision_date"),
        "documents": documents,
        "essentialElements": project.get("essential_elements", {}),
    }


def build_payload(projects: list[dict[str, Any]]) -> dict[str, Any]:
    valid_projects = [project for project in projects if not project.get("error")]
    neurology_projects = [compact_project(project) for project in valid_projects if project.get("is_neurology")]
    neurology_projects.sort(key=lambda project: clean_text(project["title"]).casefold())

    state_counter: Counter[str] = Counter()
    for project in neurology_projects:
        for state in project.get("states", []):
            state_counter[state] += 1

    status_counter: Counter[str] = Counter(project.get("status", "") for project in neurology_projects)
    total_funding = sum(project.get("fundingSumEur") or 0 for project in neurology_projects)
    states_for_ui = ordered_states(state_counter)

    payload = {
        "generatedAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "source": {
            "listUrl": LIST_URL,
            "projectCount": len(valid_projects),
            "neurologyCount": len(neurology_projects),
        },
        "overview": {
            "totalProjectsScraped": len(valid_projects),
            "neurologyProjects": len(neurology_projects),
            "activeNeurologyProjects": sum(1 for project in neurology_projects if project.get("status") != "beendet"),
            "completedNeurologyProjects": status_counter.get("beendet", 0),
            "statesWithNeurologyProjects": sum(1 for state in STATE_ORDER if state_counter.get(state, 0)),
            "totalFundingEur": total_funding,
        },
        "filters": {
            "statuses": sorted({project.get("status", "") for project in neurology_projects if project.get("status")}),
            "fundingCategories": sorted(
                {project.get("fundingCategory", "") for project in neurology_projects if project.get("fundingCategory")}
            ),
            "states": [state for state in states_for_ui if state_counter.get(state, 0)],
            "targetGroups": sorted(
                {
                    target
                    for project in neurology_projects
                    for target in project.get("targetGroups", [])
                    if target
                }
            ),
        },
        "stateSummary": [
            {
                "name": state,
                "count": state_counter.get(state, 0),
                "projectIds": [
                    project["project_id"]
                    for project in neurology_projects
                    if state in project.get("states", [])
                ],
            }
            for state in states_for_ui
        ],
        "projects": neurology_projects,
    }
    return payload


def write_payload(payload: dict[str, Any]) -> None:
    UI_PAYLOAD_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    SITE_DATA_JS.write_text(
        "window.GBA_NEUROLOGY_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )


def mirror_site_for_pages() -> None:
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    for filename in ["index.html", "styles.css", "app.js", "data.js"]:
        shutil.copy2(SITE_DIR / filename, PAGES_DIR / filename)
    (PAGES_DIR / ".nojekyll").write_text("", encoding="utf-8")


def build_site(input_path: Path) -> dict[str, Any]:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    projects = load_projects(input_path)
    payload = build_payload(projects)
    write_payload(payload)
    mirror_site_for_pages()
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the static neurology explorer payload.")
    parser.add_argument(
        "--input",
        type=Path,
        default=ALL_PROJECTS_JSON,
        help="Path to the full JSON dataset produced by gba-scrape.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    payload = build_site(args.input)
    print(
        f"Wrote {UI_PAYLOAD_JSON.name} and {SITE_DATA_JS.name} "
        f"for {payload['overview']['neurologyProjects']} neurology projects"
    )


if __name__ == "__main__":
    main()
