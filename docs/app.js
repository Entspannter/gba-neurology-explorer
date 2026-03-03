const BASE_STATE_LAYOUT = [
  { name: "bundesweit", label: "Bundesweit", code: "DE", x: 2, y: 8, w: 15, h: 18 },
  { name: "Ohne Zuordnung", label: "Ohne Bundesland", code: "NA", x: 2, y: 30, w: 17, h: 14 },
  { name: "Schleswig-Holstein", code: "SH", x: 36, y: 5, w: 17, h: 10 },
  { name: "Hamburg", code: "HH", x: 41, y: 18, w: 12, h: 9 },
  { name: "Mecklenburg-Vorpommern", code: "MV", x: 67, y: 7, w: 23, h: 12 },
  { name: "Bremen", code: "HB", x: 27, y: 29, w: 11, h: 10 },
  { name: "Niedersachsen", code: "NI", x: 39, y: 28, w: 28, h: 15 },
  { name: "Berlin", code: "BE", x: 70, y: 30, w: 10, h: 10 },
  { name: "Brandenburg", code: "BB", x: 81, y: 27, w: 15, h: 16 },
  { name: "Nordrhein-Westfalen", code: "NW", x: 16, y: 46, w: 20, h: 15 },
  { name: "Sachsen-Anhalt", code: "ST", x: 59, y: 45, w: 16, h: 13 },
  { name: "Hessen", code: "HE", x: 42, y: 51, w: 16, h: 13 },
  { name: "Thüringen", code: "TH", x: 60, y: 58, w: 14, h: 12 },
  { name: "Sachsen", code: "SN", x: 76, y: 57, w: 17, h: 13 },
  { name: "Rheinland-Pfalz", code: "RP", x: 28, y: 64, w: 14, h: 14 },
  { name: "Saarland", code: "SL", x: 17, y: 78, w: 11, h: 9 },
  { name: "Baden-Württemberg", code: "BW", x: 40, y: 72, w: 21, h: 17 },
  { name: "Bayern", code: "BY", x: 63, y: 73, w: 28, h: 18 },
];
const AUXILIARY_MAP_NODES = new Set(["bundesweit", "Ohne Zuordnung"]);

const appState = {
  search: "",
  focusScope: "all",
  status: "all",
  funding: "all",
  target: "all",
  state: null,
  sort: "title",
  projectId: null,
};

const elements = {
  heroStats: document.querySelector("#hero-stats"),
  classificationNote: document.querySelector("#classification-note"),
  heroFocusBreakdown: document.querySelector("#hero-focus-breakdown"),
  sourceLink: document.querySelector("#source-link"),
  generatedAt: document.querySelector("#generated-at"),
  searchInput: document.querySelector("#search-input"),
  focusScopeFilter: document.querySelector("#focus-scope-filter"),
  statusFilter: document.querySelector("#status-filter"),
  fundingFilter: document.querySelector("#funding-filter"),
  targetFilter: document.querySelector("#target-filter"),
  sortFilter: document.querySelector("#sort-filter"),
  resetFilters: document.querySelector("#reset-filters"),
  selectionSummary: document.querySelector("#selection-summary"),
  stateMap: document.querySelector("#state-map"),
  mapActiveLabel: document.querySelector("#map-active-label"),
  mapActiveCount: document.querySelector("#map-active-count"),
  mapTopStates: document.querySelector("#map-top-states"),
  resultsTitle: document.querySelector("#results-title"),
  resultsCount: document.querySelector("#results-count"),
  projectList: document.querySelector("#project-list"),
  detailTitle: document.querySelector("#detail-title"),
  detailBody: document.querySelector("#detail-body"),
};

const data = window.GBA_NEUROLOGY_DATA;

if (!data) {
  document.body.innerHTML =
    "<p style='padding:24px;font-family:Arial,sans-serif'>Die Datendatei fehlt. Führen Sie zuerst <code>gba-refresh</code> aus.</p>";
  throw new Error("Missing site payload.");
}

const projectsById = new Map(data.projects.map((project) => [project.project_id, project]));
const stateLayout = (() => {
  const known = new Set(BASE_STATE_LAYOUT.map((entry) => entry.name));
  const extras = data.stateSummary
    .map((entry) => entry.name)
    .filter((name) => !known.has(name))
    .map((name, index) => ({
      name,
      label: name,
      code: "EX",
      x: 3 + (index % 2) * 20,
      y: 82 + Math.floor(index / 2) * 11,
      w: 18,
      h: 10,
    }));
  return [...BASE_STATE_LAYOUT, ...extras];
})();

const stateLabelByName = new Map(stateLayout.map((entry) => [entry.name, entry.label || entry.name]));

function stateLabel(name) {
  return stateLabelByName.get(name) || name;
}

function isAuxiliaryMapNode(name) {
  return AUXILIARY_MAP_NODES.has(name);
}

function formatNumber(value) {
  return new Intl.NumberFormat("de-DE").format(value);
}

function formatCurrency(value) {
  if (!value) return "k. A.";
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDate(isoString) {
  if (!isoString) return "k. A.";
  const value = new Date(isoString);
  if (Number.isNaN(value.getTime())) return isoString;
  return new Intl.DateTimeFormat("de-DE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(value);
}

function formatProjectCount(value) {
  return `${formatNumber(value)} ${value === 1 ? "Projekt" : "Projekte"}`;
}

function normalize(value) {
  return (value || "")
    .toString()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

function focusScopeLabel(value) {
  const option = data.filters.focusScopes.find((item) => item.value === value);
  return option ? option.label : value;
}

function focusScopeBadge(project) {
  if (project.neurologyFocusScope === "exclusive") {
    return { label: "nur Neurologie", className: "scope-exclusive" };
  }
  if (project.neurologyFocusScope === "multiple") {
    return { label: "mehrere Schwerpunkte", className: "scope-multiple" };
  }
  if (project.neurologyFocusScope === "online_filter_only") {
    return { label: "im Online-Filter", className: "scope-online-only" };
  }
  return { label: "neurologisch", className: "scope-default" };
}

function setSelectOptions(select, options, label, formatter = (value) => value) {
  const values = ["all", ...options];
  select.innerHTML = values
    .map((value) => {
      const optionLabel = value === "all" ? `Alle ${label}` : formatter(value);
      return `<option value="${value}">${optionLabel}</option>`;
    })
    .join("");
}

function fillFocusScopeOptions() {
  const options = data.filters.focusScopes.filter((option) => option.value === "all" || option.count > 0);
  elements.focusScopeFilter.innerHTML = options
    .map(
      (option) =>
        `<option value="${option.value}">${option.label} (${formatNumber(option.count)})</option>`
    )
    .join("");
}

function renderHero() {
  elements.sourceLink.href = data.source.neurologyFilterUrl || data.source.listUrl;
  elements.generatedAt.textContent = formatDate(data.generatedAt);

  const breakdownParts = [
    `${formatNumber(data.overview.onlineFilterNeurologyProjects)} Treffer in der Online-Maske`,
    `${formatNumber(data.overview.exclusiveNeurologyProjects)} nur neurologisch`,
    `${formatNumber(data.overview.multiFocusNeurologyProjects)} mit weiteren Schwerpunkten`,
  ];
  if (data.overview.onlineFilterOnlyProjects) {
    breakdownParts.push(
      `${formatNumber(data.overview.onlineFilterOnlyProjects)} ohne sichtbare Schwerpunktangabe`
    );
  }
  elements.heroFocusBreakdown.textContent = breakdownParts.join(" · ");

  elements.classificationNote.innerHTML = `
    <p>
      <strong>Abgleich mit der öffentlichen G-BA-Maske:</strong>
      <a href="${data.source.neurologyFilterUrl}" target="_blank" rel="noreferrer">
        ${formatNumber(data.classification.onlineFilterCount)} Treffer
      </a>
      am Online-Filter für neurologische Erkrankungen. Davon haben
      ${formatNumber(data.classification.exclusiveCount)} Projekte ausschließlich Neurologie als
      Schwerpunkt, ${formatNumber(data.classification.multiFocusCount)} führen Neurologie als einen
      von mehreren Schwerpunkten.
      ${
        data.classification.onlineFilterOnlyCount
          ? ` ${formatNumber(data.classification.onlineFilterOnlyCount)} Projekte erscheinen im Online-Filter, ohne dass auf der Detailseite ein Schwerpunktfeld sichtbar ist.`
          : ""
      }
    </p>
  `;

  elements.heroStats.innerHTML = [
    { label: "Online-Filter-Treffer", value: data.overview.onlineFilterNeurologyProjects },
    { label: "nur Neurologie", value: data.overview.exclusiveNeurologyProjects },
    { label: "mehrere Schwerpunkte", value: data.overview.multiFocusNeurologyProjects },
    { label: "Fördervolumen", value: formatCurrency(data.overview.totalFundingEur) },
  ]
    .map(
      (item) => `
        <div class="stat-chip">
          <strong>${item.value}</strong>
          <span>${item.label}</span>
        </div>
      `
    )
    .join("");
}

function fillFilters() {
  fillFocusScopeOptions();
  setSelectOptions(elements.statusFilter, data.filters.statuses, "Status");
  setSelectOptions(elements.fundingFilter, data.filters.fundingCategories, "Förderkategorien");
  setSelectOptions(elements.targetFilter, data.filters.targetGroups, "Zielgruppen");
  elements.sortFilter.value = appState.sort;
}

function projectMatches(project, options = {}) {
  const ignoreState = options.ignoreState === true;

  if (appState.focusScope !== "all" && project.neurologyFocusScope !== appState.focusScope) return false;
  if (appState.status !== "all" && project.status !== appState.status) return false;
  if (appState.funding !== "all" && project.fundingCategory !== appState.funding) return false;
  if (appState.target !== "all" && !project.targetGroups.includes(appState.target)) return false;
  if (!ignoreState && appState.state && !project.states.includes(appState.state)) return false;

  if (!appState.search) return true;

  const haystack = normalize(
    [
      project.title,
      project.acronym,
      project.summary,
      project.description,
      project.projectLead?.display,
      project.projectLeadCity,
      project.partners.join(" "),
      project.states.join(" "),
      project.thematicFocuses.join(" "),
    ].join(" ")
  );
  return haystack.includes(normalize(appState.search));
}

function sortProjects(projects) {
  const sorted = [...projects];
  sorted.sort((left, right) => {
    if (appState.sort === "funding") {
      return (right.fundingSumEur || 0) - (left.fundingSumEur || 0);
    }
    if (appState.sort === "recent") {
      return (right.startDate || "").localeCompare(left.startDate || "");
    }
    if (appState.sort === "status") {
      return (left.status || "").localeCompare(right.status || "", "de");
    }
    return left.title.localeCompare(right.title, "de");
  });
  return sorted;
}

function getFilteredProjects(options = {}) {
  return sortProjects(data.projects.filter((project) => projectMatches(project, options)));
}

function buildSelectionSummary(filteredProjects) {
  const pills = [
    `${formatNumber(filteredProjects.length)} Treffer`,
    appState.focusScope !== "all" ? focusScopeLabel(appState.focusScope) : null,
    appState.state ? `Bundesland: ${stateLabel(appState.state)}` : null,
    appState.status !== "all" ? `Status: ${appState.status}` : null,
    appState.funding !== "all" ? `Förderkategorie: ${appState.funding}` : null,
    appState.target !== "all" ? `Zielgruppe: ${appState.target}` : null,
    appState.search ? `Suche: ${appState.search}` : null,
  ].filter(Boolean);

  elements.selectionSummary.innerHTML = pills.map((pill) => `<span class="pill">${pill}</span>`).join("");
}

function mapTileAppearance(count, maxCount) {
  if (!count) {
    return {
      background: "linear-gradient(180deg, rgba(255,255,255,0.88), rgba(240,244,249,0.92))",
      textColor: "var(--muted)",
      borderColor: "rgba(32, 58, 102, 0.10)",
      shadow: "0 12px 22px rgba(13, 31, 66, 0.05)",
    };
  }

  const intensity = count / maxCount;
  return {
    background: `linear-gradient(180deg, rgba(255,255,255,0.98), rgba(0, 168, 223, ${0.12 + intensity * 0.22}), rgba(28, 47, 105, ${0.08 + intensity * 0.22}))`,
    textColor: "var(--ink)",
    borderColor: `rgba(0, 168, 223, ${0.18 + intensity * 0.32})`,
    shadow: `0 18px 32px rgba(28, 47, 105, ${0.08 + intensity * 0.14})`,
  };
}

function renderMapSummary(counts, totalProjects) {
  const activeLabel = appState.state ? stateLabel(appState.state) : "Alle Bundesländer";
  const activeCount = appState.state ? counts.get(appState.state) || 0 : totalProjects;

  elements.mapActiveLabel.textContent = activeLabel;
  elements.mapActiveCount.textContent = formatProjectCount(activeCount);

  const topStates = [...counts.entries()]
    .filter(([name, count]) => count > 0 && !isAuxiliaryMapNode(name))
    .sort((left, right) => right[1] - left[1] || stateLabel(left[0]).localeCompare(stateLabel(right[0]), "de"))
    .slice(0, 5);

  if (!topStates.length) {
    elements.mapTopStates.innerHTML = "<p class='map-side-copy'>Keine Bundesländer passen zu den aktuellen Filtern.</p>";
    return;
  }

  elements.mapTopStates.innerHTML = topStates
    .map(
      ([name, count], index) => `
        <button
          type="button"
          class="map-top-state ${appState.state === name ? "active" : ""}"
          data-state-select="${name}"
        >
          <span class="map-top-rank">0${index + 1}</span>
          <span class="map-top-copy">
            <strong>${stateLabel(name)}</strong>
            <small>${formatProjectCount(count)}</small>
          </span>
        </button>
      `
    )
    .join("");

  elements.mapTopStates.querySelectorAll("[data-state-select]").forEach((button) => {
    button.addEventListener("click", () => {
      const selectedState = button.dataset.stateSelect;
      appState.state = appState.state === selectedState ? null : selectedState;
      rerender();
    });
  });
}

function renderMap(mapProjects) {
  const counts = new Map();
  mapProjects.forEach((project) => {
    project.states.forEach((state) => {
      counts.set(state, (counts.get(state) || 0) + 1);
    });
  });

  const maxCount = Math.max(1, ...counts.values());
  const visibleLayout = stateLayout.filter((state) => !isAuxiliaryMapNode(state.name) || (counts.get(state.name) || 0) > 0);

  elements.stateMap.innerHTML = visibleLayout
    .map((state) => {
      const count = counts.get(state.name) || 0;
      const appearance = mapTileAppearance(count, maxCount);
      const activeClass = appState.state === state.name ? "active" : "";
      const emptyClass = count === 0 ? "empty" : "";
      const tileLabel = count ? formatProjectCount(count) : "Keine Treffer";

      return `
        <button
          type="button"
          class="state-tile ${activeClass} ${emptyClass}"
          data-state="${state.name}"
          title="${stateLabel(state.name)}: ${tileLabel}"
          aria-label="${stateLabel(state.name)}: ${tileLabel}"
          aria-pressed="${appState.state === state.name}"
          style="
            left:${state.x}%;
            top:${state.y}%;
            width:${state.w}%;
            height:${state.h}%;
            background:${appearance.background};
            border-color:${appearance.borderColor};
            box-shadow:${appearance.shadow};
            color:${appearance.textColor};
          "
        >
          <div class="state-code">${state.code}</div>
          <div class="state-copy">
            <span class="state-name">${state.label || state.name}</span>
            <span class="state-count">${tileLabel}</span>
          </div>
        </button>
      `;
    })
    .join("");

  elements.stateMap.querySelectorAll("[data-state]").forEach((button) => {
    button.addEventListener("click", () => {
      const selectedState = button.dataset.state;
      appState.state = appState.state === selectedState ? null : selectedState;
      rerender();
    });
  });

  renderMapSummary(counts, mapProjects.length);
}

function renderProjectList(filteredProjects) {
  const focusLabel = appState.focusScope !== "all" ? focusScopeLabel(appState.focusScope) : "Neurologie-Projekte";
  elements.resultsTitle.textContent = appState.state
    ? `${focusLabel} in ${stateLabel(appState.state)}`
    : focusLabel;
  elements.resultsCount.textContent = `${formatNumber(filteredProjects.length)} angezeigt`;

  if (!filteredProjects.length) {
    appState.projectId = null;
    elements.projectList.innerHTML = `
      <p class="empty-results">
        Keine Projekte passen zu der aktuellen Kombination aus Suche, Neurologie-Definition und Filtern.
      </p>
    `;
    return;
  }

  if (!appState.projectId || !filteredProjects.some((project) => project.project_id === appState.projectId)) {
    appState.projectId = filteredProjects[0].project_id;
  }

  elements.projectList.innerHTML = filteredProjects
    .map((project) => {
      const activeClass = appState.projectId === project.project_id ? "active" : "";
      const scopeBadge = focusScopeBadge(project);
      return `
        <article class="project-card ${activeClass}" data-project-id="${project.project_id}">
          <h3>${project.title}</h3>
          <div class="project-meta">
            <span class="meta-pill meta-pill-strong">${project.status || "Status offen"}</span>
            <span class="meta-pill">${project.states.join(", ") || "ohne Bundesland"}</span>
            <span class="meta-pill ${scopeBadge.className}">${scopeBadge.label}</span>
          </div>
          <p>${project.summary || "Keine Kurzbeschreibung verfügbar."}</p>
        </article>
      `;
    })
    .join("");

  elements.projectList.querySelectorAll("[data-project-id]").forEach((card) => {
    card.addEventListener("click", () => {
      appState.projectId = Number(card.dataset.projectId);
      renderDetail(projectsById.get(appState.projectId));
      elements.projectList.querySelectorAll(".project-card").forEach((node) => node.classList.remove("active"));
      card.classList.add("active");
    });
  });
}

function renderDetail(project) {
  if (!project) {
    elements.detailTitle.textContent = "Projekt wählen";
    elements.detailBody.innerHTML = `
      <p class="empty-state">
        Wählen Sie ein Projekt aus der Liste oder klicken Sie auf ein Bundesland in der Karte.
      </p>
    `;
    return;
  }

  const scopeBadge = focusScopeBadge(project);
  elements.detailTitle.textContent = project.acronym || project.title;

  const websites = project.projectWebsites.length
    ? project.projectWebsites.map((url) => `<a href="${url}" target="_blank" rel="noreferrer">${url}</a>`).join("")
    : "<span>Keine Projektwebsite hinterlegt.</span>";

  const documents = project.documents.length
    ? project.documents
        .map(
          (document) => `
            <a href="${document.url}" target="_blank" rel="noreferrer">
              ${document.title}${document.meta ? ` <small>${document.meta}</small>` : ""}
            </a>
          `
        )
        .join("")
    : "<span>Keine Dokumente in der Detailansicht gefunden.</span>";

  const essentialEntries = Object.entries(project.essentialElements || {});
  const essentialMarkup = essentialEntries.length
    ? `
      <ul class="detail-list">
        ${essentialEntries
          .map(([label, values]) => `<li><strong>${label}:</strong> ${values.join(", ")}</li>`)
          .join("")}
      </ul>
    `
    : "<p>Keine wesentlichen Projektelemente veröffentlicht.</p>";

  elements.detailBody.innerHTML = `
    <div class="detail-block">
      <div class="detail-meta">
        <span class="meta-pill meta-pill-strong">${project.status || "Status k. A."}</span>
        <span class="meta-pill">${project.states.join(", ") || "Bundesland k. A."}</span>
        <span class="meta-pill ${scopeBadge.className}">${scopeBadge.label}</span>
      </div>
      <p>${project.description || "Keine ausführliche Projektbeschreibung verfügbar."}</p>
    </div>

    <div class="detail-block detail-kv">
      <div class="detail-kv-row">
        <strong>Neurologie-Einordnung</strong>
        <span>${scopeBadge.label}</span>
      </div>
      <div class="detail-kv-row">
        <strong>Themenschwerpunkte</strong>
        <span>${project.thematicFocuses.length ? project.thematicFocuses.join(", ") : "nicht sichtbar ausgewiesen"}</span>
      </div>
      <div class="detail-kv-row">
        <strong>Laufzeit</strong>
        <span>${project.duration || "k. A."}</span>
      </div>
      <div class="detail-kv-row">
        <strong>Fördersumme</strong>
        <span>${project.fundingSumLabel || formatCurrency(project.fundingSumEur)}</span>
      </div>
      <div class="detail-kv-row">
        <strong>Projektleitung</strong>
        <span>${project.projectLead?.display || "k. A."}</span>
      </div>
      <div class="detail-kv-row">
        <strong>Transferempfehlung</strong>
        <span>${project.transferRecommendation || "k. A."}</span>
      </div>
      <div class="detail-kv-row">
        <strong>Zielgruppen</strong>
        <span>${project.targetGroups.join(", ") || "k. A."}</span>
      </div>
      <div class="detail-kv-row">
        <strong>Versorgungsbereich</strong>
        <span>${project.careSetting || "k. A."}</span>
      </div>
      <div class="detail-kv-row">
        <strong>Beschlussdatum</strong>
        <span>${project.decisionDate || "k. A."}</span>
      </div>
      <div class="detail-kv-row">
        <strong>Originalseite</strong>
        <a href="${project.url}" target="_blank" rel="noreferrer">Projekt beim Innovationsfonds öffnen</a>
      </div>
    </div>

    <div class="detail-block">
      <h3>Partner</h3>
      <p>${project.partners.length ? project.partners.join("; ") : "Keine Konsortialpartner gelistet."}</p>
    </div>

    <div class="detail-block">
      <h3>Projektwebsite</h3>
      <div class="detail-links">${websites}</div>
    </div>

    <div class="detail-block">
      <h3>Wesentliche Projektelemente</h3>
      ${essentialMarkup}
    </div>

    <div class="detail-block">
      <h3>Dokumente</h3>
      <div class="detail-links">${documents}</div>
    </div>
  `;
}

function rerender() {
  const filteredProjects = getFilteredProjects();
  const mapProjects = getFilteredProjects({ ignoreState: true });
  buildSelectionSummary(filteredProjects);
  renderMap(mapProjects);
  renderProjectList(filteredProjects);
  renderDetail(projectsById.get(appState.projectId));
}

function wireEvents() {
  elements.searchInput.addEventListener("input", (event) => {
    appState.search = event.target.value.trim();
    rerender();
  });

  elements.focusScopeFilter.addEventListener("change", (event) => {
    appState.focusScope = event.target.value;
    rerender();
  });

  elements.statusFilter.addEventListener("change", (event) => {
    appState.status = event.target.value;
    rerender();
  });

  elements.fundingFilter.addEventListener("change", (event) => {
    appState.funding = event.target.value;
    rerender();
  });

  elements.targetFilter.addEventListener("change", (event) => {
    appState.target = event.target.value;
    rerender();
  });

  elements.sortFilter.addEventListener("change", (event) => {
    appState.sort = event.target.value;
    rerender();
  });

  elements.resetFilters.addEventListener("click", () => {
    appState.search = "";
    appState.focusScope = "all";
    appState.status = "all";
    appState.funding = "all";
    appState.target = "all";
    appState.state = null;
    appState.sort = "title";
    elements.searchInput.value = "";
    elements.focusScopeFilter.value = "all";
    elements.statusFilter.value = "all";
    elements.fundingFilter.value = "all";
    elements.targetFilter.value = "all";
    elements.sortFilter.value = "title";
    rerender();
  });
}

renderHero();
fillFilters();
wireEvents();
rerender();
