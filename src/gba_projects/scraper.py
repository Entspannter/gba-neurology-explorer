from __future__ import annotations

import argparse
import csv
import json
import re
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://innovationsfonds.g-ba.de"
LIST_URL = f"{BASE_URL}/projekte/"
LIST_PARAMS = {
    "direction": "asc",
    "sort": "projekt.akronym",
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
LISTING_CACHE_DIR = CACHE_DIR / "listings"
PROJECT_CACHE_DIR = CACHE_DIR / "projects"

ALL_PROJECTS_JSON = DATA_DIR / "projects_all.json"
ALL_PROJECTS_CSV = DATA_DIR / "projects_all.csv"
NEUROLOGY_PROJECTS_JSON = DATA_DIR / "projects_neurology.json"

WHITESPACE_RE = re.compile(r"\s+")
PAGE_COUNT_RE = re.compile(r"Seite\s+\d+\s+von\s+(\d+)", re.IGNORECASE)
POSTAL_CITY_RE = re.compile(r"^(?P<postal_code>\d{4,5})\s+(?P<city>.+)$")
DATE_RANGE_RE = re.compile(
    r"(?P<start_month>\d{2})/(?P<start_year>\d{4})\s*[–-]\s*(?P<end_month>\d{2})/(?P<end_year>\d{4})"
)


@dataclass(slots=True)
class ScrapeConfig:
    force: bool = False
    delay: float = 0.05
    limit: int | None = None


def ensure_directories() -> None:
    for path in [DATA_DIR, LISTING_CACHE_DIR, PROJECT_CACHE_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return WHITESPACE_RE.sub(" ", value).strip()


def slugify_label(label: str) -> str:
    normalized = unicodedata.normalize("NFKD", label)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")


def split_values(value: str) -> list[str]:
    if not value:
        return []
    parts = re.split(r"\s*[,;]\s*", value)
    cleaned = [clean_text(part) for part in parts if clean_text(part)]
    return list(dict.fromkeys(cleaned))


def parse_money_eur(value: str) -> int | None:
    if not value:
        return None

    normalized = value.casefold().replace("ca.", "").replace("euro", "").strip()
    normalized = normalized.replace(" ", "")

    if "mio" in normalized:
        number = normalized.replace("mio.", "").replace("mio", "")
        number = number.replace(".", "").replace(",", ".")
        try:
            return round(float(number) * 1_000_000)
        except ValueError:
            return None

    number = normalized.replace(".", "").replace(",", ".")
    try:
        return round(float(number))
    except ValueError:
        return None


def parse_duration_range(value: str) -> tuple[str | None, str | None]:
    match = DATE_RANGE_RE.search(value)
    if not match:
        return None, None
    start = f"{match.group('start_year')}-{match.group('start_month')}"
    end = f"{match.group('end_year')}-{match.group('end_month')}"
    return start, end


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (compatible; gba-neurology-explorer/1.0; "
                "+https://innovationsfonds.g-ba.de/projekte/)"
            )
        }
    )
    return session


def cache_path_for_listing(page: int) -> Path:
    return LISTING_CACHE_DIR / f"page-{page}.html"


def cache_path_for_project(url: str) -> Path:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    safe_slug = re.sub(r"[^A-Za-z0-9._-]+", "_", slug)
    return PROJECT_CACHE_DIR / f"{safe_slug}.html"


def fetch_html(
    session: requests.Session,
    *,
    url: str,
    params: dict[str, Any] | None = None,
    cache_path: Path,
    force: bool,
) -> str:
    if cache_path.exists() and not force:
        return cache_path.read_text(encoding="utf-8")

    response = session.get(url, params=params, timeout=60)
    response.raise_for_status()
    html = response.text
    cache_path.write_text(html, encoding="utf-8")
    return html


def get_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def parse_last_page(list_soup: BeautifulSoup) -> int:
    status = list_soup.select_one(".gba-pagination-status")
    if status:
        match = PAGE_COUNT_RE.search(clean_text(status.get_text(" ", strip=True)))
        if match:
            return int(match.group(1))

    pages: list[int] = []
    for link in list_soup.select("a[href*='page=']"):
        href = link.get("href", "")
        match = re.search(r"[?&]page=(\d+)", href)
        if match:
            pages.append(int(match.group(1)))
    return max(pages) if pages else 1


def extract_project_links(list_soup: BeautifulSoup) -> list[str]:
    links: list[str] = []
    for link in list_soup.select("td[data-label='Projektname'] a[href^='/projekte/']"):
        href = link.get("href", "")
        absolute_url = urljoin(BASE_URL, href)
        links.append(absolute_url)
    return list(dict.fromkeys(links))


def parse_kv_list(root: Tag | None) -> dict[str, str]:
    data: dict[str, str] = {}
    if root is None:
        return data

    for item in root.select("li"):
        label_node = item.find("b")
        if label_node is None:
            continue
        label = clean_text(label_node.get_text(" ", strip=True)).rstrip(":")
        raw_text = clean_text(item.get_text(" ", strip=True))
        value = raw_text.replace(clean_text(label_node.get_text(" ", strip=True)), "", 1)
        value = clean_text(value).lstrip(":").strip()
        if label and value:
            data[label] = value
    return data


def section_by_id(soup: BeautifulSoup, section_id: str) -> Tag | None:
    section = soup.select_one(f"section#{section_id}")
    if section:
        return section
    return soup.select_one(f"div#{section_id}-mobile")


def parse_contact_block(block: Tag | None) -> dict[str, Any]:
    if block is None:
        return {}

    lines = [clean_text(text) for text in block.stripped_strings]
    if not lines:
        return {}

    info: dict[str, Any] = {
        "raw_lines": lines,
        "display": " | ".join(lines),
        "name": lines[0],
    }

    email = next((line for line in lines if "@" in line), None)
    phone = next((line for line in lines if line.startswith("+")), None)
    city_line = next((line for line in lines if POSTAL_CITY_RE.match(line)), None)
    city_match = POSTAL_CITY_RE.match(city_line) if city_line else None

    info["email"] = email
    info["phone"] = phone
    if city_match:
        info["postal_code"] = city_match.group("postal_code")
        info["city"] = clean_text(city_match.group("city"))

    organization_lines: list[str] = []
    for line in lines[1:]:
        if line == email or line == phone:
            continue
        if city_line and line == city_line:
            continue
        if re.search(r"\d", line):
            continue
        organization_lines.append(line)
    if organization_lines:
        info["organization"] = organization_lines[0]
        if len(organization_lines) > 1:
            info["department"] = " | ".join(organization_lines[1:])

    address_lines: list[str] = []
    seen_city = False
    for line in lines[1:]:
        if line == email or line == phone:
            continue
        if city_line and line == city_line:
            seen_city = True
            continue
        if not seen_city and re.search(r"\d", line):
            address_lines.append(line)
    if address_lines:
        info["street"] = address_lines[0]

    return info


def parse_project_team(section: Tag | None) -> tuple[dict[str, Any], list[str]]:
    if section is None:
        return {}, []

    lead_block: Tag | None = None
    partner_block: Tag | None = None
    for heading in section.select("h2.h3"):
        heading_text = clean_text(heading.get_text(" ", strip=True)).casefold()
        paragraph = heading.find_next_sibling("p")
        if paragraph is None:
            continue
        if "projektleitung" in heading_text and lead_block is None:
            lead_block = paragraph
        if "konsortialpartner" in heading_text and partner_block is None:
            partner_block = paragraph

    partners = split_values(clean_text(partner_block.get_text(" ", strip=True)) if partner_block else "")
    return parse_contact_block(lead_block), partners


def parse_documents(section: Tag | None) -> list[dict[str, str]]:
    documents: list[dict[str, str]] = []
    if section is None:
        return documents

    for anchor in section.select(".gba-download-list a[href]"):
        title_node = anchor.select_one(".gba-download__text")
        info_node = anchor.select_one(".gba-download__dateiinfo")
        title = clean_text(title_node.get_text(" ", strip=True) if title_node else anchor.get_text(" ", strip=True))
        info = clean_text(info_node.get_text(" ", strip=True) if info_node else "")
        href = urljoin(BASE_URL, anchor.get("href", ""))
        if title and href:
            documents.append({"title": title, "meta": info, "url": href})
    return documents


def parse_decision_date(section: Tag | None) -> str | None:
    if section is None:
        return None

    label = section.find(string=re.compile("Beschlussdatum", re.IGNORECASE))
    if not label:
        return None

    parent = label.parent if isinstance(label.parent, Tag) else None
    value_node = parent.find_next("span", class_="wert") if parent else None
    if value_node:
        return clean_text(value_node.get_text(" ", strip=True))
    return None


def parse_project_description(soup: BeautifulSoup) -> str:
    content = soup.select_one(".gba-page__content")
    if content is None:
        return ""

    disclosure = content.select_one(".gba-ausklappbarer-abschnitt")
    if disclosure is None:
        return clean_text(content.get_text(" ", strip=True))

    paragraphs: list[str] = []
    for paragraph in disclosure.select(".gba-ausklappbarer-abschnitt__teaser p, .gba-ausklappbarer-abschnitt__panel p"):
        text = clean_text(paragraph.get_text(" ", strip=True))
        if text and text not in paragraphs:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def parse_project_websites(soup: BeautifulSoup) -> list[str]:
    urls: list[str] = []
    for anchor in soup.select(".projekt-detail__projekt-website a[href]"):
        href = anchor.get("href", "")
        if href:
            urls.append(href)
    return list(dict.fromkeys(urls))


def parse_essential_elements(project_meta_root: Tag | None) -> dict[str, list[str]]:
    if project_meta_root is None:
        return {}

    result: dict[str, list[str]] = {}
    for box in project_meta_root.select(".gba-box"):
        title = clean_text(box.select_one(".gba-box__titel").get_text(" ", strip=True) if box.select_one(".gba-box__titel") else "")
        if title.casefold() != "wesentliche projektelemente":
            continue
        for row in box.select(".gba-box__body > div"):
            label_node = row.find("b")
            if label_node is None:
                continue
            label = clean_text(label_node.get_text(" ", strip=True)).rstrip(":")
            values = [clean_text(anchor.get_text(" ", strip=True)) for anchor in row.select("a")]
            if label and values:
                result[label] = values
        break
    return result


def project_id_from_url(url: str) -> int | None:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    match = re.search(r"\.(\d+)$", slug)
    return int(match.group(1)) if match else None


def acronym_from_title(title: str, slug: str) -> str:
    parts = re.split(r"\s+[–-]\s+", title, maxsplit=1)
    candidate = clean_text(parts[0])
    if candidate and len(candidate) <= 40:
        return candidate
    return slug.split(".", 1)[0].upper()


def parse_project_page(soup: BeautifulSoup, url: str) -> dict[str, Any]:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    title_node = soup.select_one("h1.h1--reduziert")
    title = clean_text(title_node.get_text(" ", strip=True) if title_node else slug)
    funding_category = clean_text(
        soup.select_one(".projekt-detail__titel .gba-stack").get_text(" ", strip=True)
        if soup.select_one(".projekt-detail__titel .gba-stack")
        else ""
    )

    meta_root = soup.select_one(".padding.border.margin-top")
    project_data = parse_kv_list(meta_root)
    essential_elements = parse_essential_elements(meta_root)
    funding_info = parse_kv_list(section_by_id(soup, "foerderangaben"))

    team_section = section_by_id(soup, "projektleitung-und-konsortialpartner")
    project_lead, partners = parse_project_team(team_section)

    results_section = section_by_id(soup, "ergebnisse-und-beschluss")
    other_info_section = section_by_id(soup, "weitere-informationen")

    themenschwerpunkte = split_values(project_data.get("Themenschwerpunkte", ""))
    target_groups = split_values(project_data.get("Zielgruppen", ""))
    states = split_values(project_data.get("Bundesland", ""))
    duration_raw = project_data.get("Laufzeit", "")
    start_date, end_date = parse_duration_range(duration_raw)

    funding_sum_label = funding_info.get("Fördersumme", "")
    transfer_recommendation = project_data.get("Transferempfehlung", "")

    return {
        "project_id": project_id_from_url(url),
        "slug": slug,
        "url": url,
        "title": title,
        "acronym": acronym_from_title(title, slug),
        "funding_category": funding_category,
        "project_data": project_data,
        "funding_info": funding_info,
        "thematic_focuses": themenschwerpunkte,
        "target_groups": target_groups,
        "states": states,
        "care_setting": project_data.get("Versorgungsbereich", ""),
        "status": project_data.get("Status", ""),
        "duration_raw": duration_raw,
        "start_date": start_date,
        "end_date": end_date,
        "transfer_recommendation": transfer_recommendation,
        "funding_sum_label": funding_sum_label,
        "funding_sum_eur": parse_money_eur(funding_sum_label),
        "funding_reference": project_data.get("Förderkennzeichen", ""),
        "themenfeld": funding_info.get("Themenfeld", ""),
        "funding_process": funding_info.get("Förderverfahren", ""),
        "funding_area": funding_info.get("Förderbereich", ""),
        "call_date": funding_info.get("Förderbekanntmachung", ""),
        "description": parse_project_description(soup),
        "project_websites": parse_project_websites(soup),
        "project_lead": project_lead,
        "project_lead_city": project_lead.get("city"),
        "consortium_partners": partners,
        "essential_elements": essential_elements,
        "decision_date": parse_decision_date(results_section),
        "result_documents": parse_documents(results_section),
        "additional_documents": parse_documents(other_info_section),
        "is_neurology": any(focus.casefold() == "neurologische erkrankungen" for focus in themenschwerpunkte),
    }


def flatten_record(project: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": project.get("project_id"),
        "acronym": project.get("acronym"),
        "title": project.get("title"),
        "url": project.get("url"),
        "is_neurology": project.get("is_neurology"),
        "funding_category": project.get("funding_category"),
        "funding_area": project.get("funding_area"),
        "funding_process": project.get("funding_process"),
        "status": project.get("status"),
        "transfer_recommendation": project.get("transfer_recommendation"),
        "states": " | ".join(project.get("states", [])),
        "thematic_focuses": " | ".join(project.get("thematic_focuses", [])),
        "target_groups": " | ".join(project.get("target_groups", [])),
        "care_setting": project.get("care_setting"),
        "funding_reference": project.get("funding_reference"),
        "duration_raw": project.get("duration_raw"),
        "start_date": project.get("start_date"),
        "end_date": project.get("end_date"),
        "funding_sum_label": project.get("funding_sum_label"),
        "funding_sum_eur": project.get("funding_sum_eur"),
        "project_lead_name": project.get("project_lead", {}).get("name"),
        "project_lead_organization": project.get("project_lead", {}).get("organization"),
        "project_lead_city": project.get("project_lead_city"),
        "consortium_partners": " | ".join(project.get("consortium_partners", [])),
        "decision_date": project.get("decision_date"),
        "description": project.get("description"),
        "project_websites": " | ".join(project.get("project_websites", [])),
    }


def write_outputs(projects: list[dict[str, Any]]) -> None:
    ALL_PROJECTS_JSON.write_text(
        json.dumps(projects, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    flattened_rows = [flatten_record(project) for project in projects]
    if flattened_rows:
        with ALL_PROJECTS_CSV.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(flattened_rows[0].keys()))
            writer.writeheader()
            writer.writerows(flattened_rows)
    else:
        ALL_PROJECTS_CSV.write_text("", encoding="utf-8")

    neurology_projects = [project for project in projects if project.get("is_neurology")]
    NEUROLOGY_PROJECTS_JSON.write_text(
        json.dumps(neurology_projects, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def scrape_projects(config: ScrapeConfig) -> list[dict[str, Any]]:
    ensure_directories()
    session = make_session()

    first_page_html = fetch_html(
        session,
        url=LIST_URL,
        params={**LIST_PARAMS, "page": 1},
        cache_path=cache_path_for_listing(1),
        force=config.force,
    )
    first_page_soup = get_soup(first_page_html)
    last_page = parse_last_page(first_page_soup)

    all_urls: list[str] = []
    for page in range(1, last_page + 1):
        html = first_page_html if page == 1 else fetch_html(
            session,
            url=LIST_URL,
            params={**LIST_PARAMS, "page": page},
            cache_path=cache_path_for_listing(page),
            force=config.force,
        )
        soup = first_page_soup if page == 1 else get_soup(html)
        page_urls = extract_project_links(soup)
        all_urls.extend(page_urls)
        print(f"Collected {len(page_urls):>2} links from list page {page}/{last_page}")
        if config.delay:
            time.sleep(config.delay)

    deduped_urls = list(dict.fromkeys(all_urls))
    if config.limit is not None:
        deduped_urls = deduped_urls[: config.limit]

    print(f"Scraping {len(deduped_urls)} project detail pages")

    projects: list[dict[str, Any]] = []
    for index, project_url in enumerate(deduped_urls, start=1):
        cache_path = cache_path_for_project(project_url)
        try:
            html = fetch_html(
                session,
                url=project_url,
                cache_path=cache_path,
                force=config.force,
            )
            soup = get_soup(html)
            projects.append(parse_project_page(soup, project_url))
        except Exception as exc:  # pragma: no cover - defensive in live scrape
            projects.append(
                {
                    "project_id": project_id_from_url(project_url),
                    "slug": urlparse(project_url).path.rstrip("/").split("/")[-1],
                    "url": project_url,
                    "error": str(exc),
                    "is_neurology": False,
                }
            )
        print(f"Parsed {index}/{len(deduped_urls)}: {project_url}")
        if config.delay:
            time.sleep(config.delay)

    write_outputs(projects)
    return projects


def parse_args(argv: list[str] | None = None) -> ScrapeConfig:
    parser = argparse.ArgumentParser(description="Scrape the G-BA Innovationsfonds projects index.")
    parser.add_argument("--force", action="store_true", help="Ignore cached HTML and refetch from the source site.")
    parser.add_argument("--delay", type=float, default=0.05, help="Delay between HTTP requests in seconds.")
    parser.add_argument("--limit", type=int, default=None, help="Only scrape the first N project detail pages.")
    args = parser.parse_args(argv)
    return ScrapeConfig(force=args.force, delay=args.delay, limit=args.limit)


def main(argv: list[str] | None = None) -> None:
    config = parse_args(argv)
    started = time.perf_counter()
    projects = scrape_projects(config)
    elapsed = time.perf_counter() - started
    neurology_count = sum(1 for project in projects if project.get("is_neurology"))
    print(
        f"Wrote {ALL_PROJECTS_JSON.name}, {ALL_PROJECTS_CSV.name}, and "
        f"{NEUROLOGY_PROJECTS_JSON.name} in {elapsed:.1f}s "
        f"({neurology_count} neurology projects)"
    )


if __name__ == "__main__":
    main()

