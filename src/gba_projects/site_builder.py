from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .scraper import ALL_PROJECTS_CSV, ALL_PROJECTS_JSON, DATA_DIR, LIST_URL, NEUROLOGY_PROJECTS_JSON, PROJECT_ROOT

SITE_DIR = PROJECT_ROOT / "site"
PAGES_DIR = PROJECT_ROOT / "docs"
SITE_DATA_JS = SITE_DIR / "data.js"
UI_PAYLOAD_JSON = DATA_DIR / "neurology_ui_payload.json"
SITE_DOWNLOADS_DIR = SITE_DIR / "downloads"
PAGES_DOWNLOADS_DIR = PAGES_DIR / "downloads"
STATIC_FILES = ["index.html", "styles.css", "app.js", "data.js", "favicon.svg"]

DOWNLOAD_SPECS = [
    {
        "source": ALL_PROJECTS_JSON,
        "href": "./downloads/projects_all.json",
        "label": "Alle Projekte",
        "format": "JSON",
    },
    {
        "source": ALL_PROJECTS_CSV,
        "href": "./downloads/projects_all.csv",
        "label": "Alle Projekte",
        "format": "CSV",
    },
    {
        "source": NEUROLOGY_PROJECTS_JSON,
        "href": "./downloads/projects_neurology.json",
        "label": "Neurologie-Subset",
        "format": "JSON",
    },
]

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


def format_file_size(path: Path) -> str:
    size = path.stat().st_size
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            decimals = 0 if unit == "B" else 1
            return f"{value:.{decimals}f} {unit}"
        value /= 1024


def download_entries() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for spec in DOWNLOAD_SPECS:
        source = spec["source"]
        entries.append(
            {
                "href": spec["href"],
                "filename": source.name,
                "label": spec["label"],
                "format": spec["format"],
                "size": format_file_size(source),
            }
        )
    return entries


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
        "neurologySourceMatch": project.get("matches_neurology_online_filter", False),
        "neurologyExplicitFocus": project.get("has_explicit_neurology_focus", False),
        "neurologyFocusScope": project.get("neurology_focus_scope", "none"),
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
    neurology_projects = [
        compact_project(project)
        for project in valid_projects
        if project.get("matches_neurology_online_filter")
    ]
    neurology_projects.sort(key=lambda project: clean_text(project["title"]).casefold())

    state_counter: Counter[str] = Counter()
    for project in neurology_projects:
        for state in project.get("states", []):
            state_counter[state] += 1

    status_counter: Counter[str] = Counter(project.get("status", "") for project in neurology_projects)
    total_funding = sum(project.get("fundingSumEur") or 0 for project in neurology_projects)
    states_for_ui = ordered_states(state_counter)
    exclusive_count = sum(1 for project in neurology_projects if project.get("neurologyFocusScope") == "exclusive")
    multiple_count = sum(1 for project in neurology_projects if project.get("neurologyFocusScope") == "multiple")
    online_only_count = sum(1 for project in neurology_projects if project.get("neurologyFocusScope") == "online_filter_only")
    explicit_count = sum(1 for project in neurology_projects if project.get("neurologyExplicitFocus"))

    payload = {
        "generatedAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "source": {
            "listUrl": LIST_URL,
            "projectCount": len(valid_projects),
            "neurologyCount": len(neurology_projects),
            "neurologyFilterUrl": (
                "https://innovationsfonds.g-ba.de/projekte/"
                "?projektname=&themenschwerpunkt=neurologische+Erkrankungen&zielgruppe="
                "&projektelemente%5BprojektelementGruppe%5D=&projektelemente%5Bprojektelement%5D="
                "&foerderbereich%5Bfoerderbereich%5D=&foerderbereich%5Bfoerderverfahren%5D="
                "&versorgungsbereich=&bundesland=&status%5Bstatus%5D=&status%5Btransferempfehlung%5D="
                "&sort=projekt.akronym&direction=asc"
            ),
        },
        "overview": {
            "totalProjectsScraped": len(valid_projects),
            "neurologyProjects": len(neurology_projects),
            "onlineFilterNeurologyProjects": len(neurology_projects),
            "explicitNeurologyProjects": explicit_count,
            "exclusiveNeurologyProjects": exclusive_count,
            "multiFocusNeurologyProjects": multiple_count,
            "onlineFilterOnlyProjects": online_only_count,
            "activeNeurologyProjects": sum(1 for project in neurology_projects if project.get("status") != "beendet"),
            "completedNeurologyProjects": status_counter.get("beendet", 0),
            "statesWithNeurologyProjects": sum(1 for state in STATE_ORDER if state_counter.get(state, 0)),
            "totalFundingEur": total_funding,
        },
        "classification": {
            "onlineFilterCount": len(neurology_projects),
            "explicitCount": explicit_count,
            "exclusiveCount": exclusive_count,
            "multiFocusCount": multiple_count,
            "onlineFilterOnlyCount": online_only_count,
            "note": (
                "Die Standardansicht folgt der öffentlichen G-BA-Online-Maske für "
                "„neurologische Erkrankungen“. Ein Teil der Projekte führt Neurologie "
                "als einen von mehreren Themenschwerpunkten."
            ),
        },
        "downloads": download_entries(),
        "filters": {
            "statuses": sorted({project.get("status", "") for project in neurology_projects if project.get("status")}),
            "fundingCategories": sorted(
                {project.get("fundingCategory", "") for project in neurology_projects if project.get("fundingCategory")}
            ),
            "states": [state for state in states_for_ui if state_counter.get(state, 0)],
            "focusScopes": [
                {
                    "value": "all",
                    "label": "Alle Treffer aus dem Online-Filter",
                    "count": len(neurology_projects),
                },
                {
                    "value": "exclusive",
                    "label": "Nur neurologischer Schwerpunkt",
                    "count": exclusive_count,
                },
                {
                    "value": "multiple",
                    "label": "Neurologie unter mehreren Schwerpunkten",
                    "count": multiple_count,
                },
                {
                    "value": "online_filter_only",
                    "label": "Im Online-Filter, aber ohne sichtbare Schwerpunktangabe",
                    "count": online_only_count,
                },
            ],
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
    SITE_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    for filename in STATIC_FILES:
        shutil.copy2(SITE_DIR / filename, PAGES_DIR / filename)
    for spec in DOWNLOAD_SPECS:
        source = spec["source"]
        shutil.copy2(source, SITE_DOWNLOADS_DIR / source.name)
        shutil.copy2(source, PAGES_DOWNLOADS_DIR / source.name)
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
