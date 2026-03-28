let activeTabId = null;
let courses = [];
let settings = null;
let selectedCourseIds = new Set();
let hasSelectionState = false;
let detectedByCourse = new Map();
let selectedMaterialKeys = new Set();

function setStatus(message) {
  document.getElementById("status").textContent = message;
}

function normalizeUrl(value) {
  try {
    return new URL(value).toString();
  } catch (_err) {
    return "";
  }
}

function materialKey(courseId, url) {
  return `${courseId}::${normalizeUrl(url)}`;
}

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase()
    .replace(/\s+/g, " ")
    .trim();
}

function getTermToken(term) {
  const raw = String(term || "").trim();
  if (!raw || /^no term$/i.test(raw)) {
    return null;
  }

  const norm = normalizeText(raw);
  const yearMatch = norm.match(/\b(19\d{2}|20\d{2})\b/);
  if (!yearMatch) {
    return `text:${norm}`;
  }

  const year = Number(yearMatch[1]);
  const full = ` ${norm} `;
  let period = 0;

  if (/\b(SEMESTER|SEMESTRE|TERM|TRIMESTRE|QUARTER|Q)\s*([1-6])\b/.test(full)) {
    period = Number(full.match(/\b(SEMESTER|SEMESTRE|TERM|TRIMESTRE|QUARTER|Q)\s*([1-6])\b/)[2]);
  } else if (/\b(IV|III|II|I)\b/.test(full)) {
    const roman = full.match(/\b(IV|III|II|I)\b/)[1];
    period = { I: 1, II: 2, III: 3, IV: 4 }[roman] || 0;
  } else if (/\b(FALL|OTONO|AUTUMN)\b/.test(full)) {
    period = 3;
  } else if (/\b(SUMMER|VERANO)\b/.test(full)) {
    period = 2;
  } else if (/\b(SPRING|PRIMAVERA)\b/.test(full)) {
    period = 1;
  } else if (/\b(WINTER|INVIERNO)\b/.test(full)) {
    period = 0;
  } else {
    const afterYear = norm.slice(norm.indexOf(yearMatch[1]) + 4);
    const numberMatch = afterYear.match(/[\/\-_ ](0?[1-9]|1[0-2])(?:\b|[\/\-_ ])/);
    if (numberMatch) {
      period = Number(numberMatch[1]);
    }
  }

  return `rank:${year * 100 + period}`;
}

function detectCurrentCycle(list) {
  let current = null;
  for (const course of list || []) {
    const token = getTermToken(course.term);
    if (!token || !token.startsWith("rank:")) {
      continue;
    }
    const score = Number(token.slice("rank:".length));
    if (!Number.isFinite(score)) {
      continue;
    }
    const isActiveHint = String(course.status || "").toLowerCase() === "active";
    if (!current) {
      current = { token, score, isActiveHint };
      continue;
    }
    if (isActiveHint && !current.isActiveHint) {
      current = { token, score, isActiveHint };
      continue;
    }
    if (isActiveHint === current.isActiveHint && score > current.score) {
      current = { token, score, isActiveHint };
    }
  }
  return current ? current.token : null;
}

function getSelectedCourseIds() {
  return Array.from(selectedCourseIds);
}

function getSelectedCourses() {
  const selectedIds = new Set(getSelectedCourseIds());
  return courses.filter((c) => selectedIds.has(c.id));
}

function summarizeSettings(s) {
  return [
    `University: ${s.universityLabel || "n/a"}`,
    `Host: ${s.preferredHost || "auto"}`,
    `Preset: ${s.exportPreset}`,
    `ZIP: ${s.zipBundling ? "on" : "off"}`,
    `Incremental: ${s.incrementalMode ? "on" : "off"}`,
    `Debug: ${s.debugMode ? "on" : "off"}`,
    `Delay: ${s.delayMs} ms`,
    `Conflict: ${s.conflictHandling}`,
    `Max size: ${s.maxFileSizeMb || "none"} MB`,
    `Exclude video: ${s.excludeVideo ? "yes" : "no"}`
  ].join(" | ");
}

function groupByTerm(list) {
  const map = new Map();
  for (const c of list) {
    const term = c.term || "No term";
    if (!map.has(term)) {
      map.set(term, []);
    }
    map.get(term).push(c);
  }
  return map;
}

function filterCourses(list) {
  const query = document.getElementById("search").value.trim().toLowerCase();
  const showActive = document.getElementById("show-active").checked;
  const showPast = document.getElementById("show-past").checked;
  const cycleFilter = document.getElementById("cycle-filter").value;
  const currentCycleToken = detectCurrentCycle(list);

  return list.filter((course) => {
    const statusOk =
      (course.status === "active" && showActive) ||
      (course.status === "past" && showPast) ||
      (!course.status && showActive);
    if (!statusOk) {
      return false;
    }

    const termToken = getTermToken(course.term);
    if (cycleFilter === "__none__" && termToken !== null) {
      return false;
    }
    if (cycleFilter === "__current__" && currentCycleToken && termToken !== currentCycleToken) {
      return false;
    }
    if (cycleFilter !== "__all__" && cycleFilter !== "__current__" && cycleFilter !== "__none__") {
      if (termToken !== cycleFilter) {
        return false;
      }
    }

    if (!query) {
      return true;
    }
    const haystack = `${course.name} ${course.term} ${course.id}`.toLowerCase();
    return haystack.includes(query);
  });
}

function renderCycleFilterOptions() {
  const select = document.getElementById("cycle-filter");
  const previous = select.value || "__current__";
  const seen = new Map();

  for (const c of courses) {
    const token = getTermToken(c.term);
    if (!token) {
      continue;
    }
    if (!seen.has(token)) {
      seen.set(token, String(c.term || "").trim());
    }
  }

  const ranked = [];
  const textOnly = [];
  for (const [token, label] of seen.entries()) {
    if (token.startsWith("rank:")) {
      ranked.push({ token, label, score: Number(token.slice("rank:".length)) });
    } else {
      textOnly.push({ token, label });
    }
  }
  ranked.sort((a, b) => b.score - a.score);
  textOnly.sort((a, b) => a.label.localeCompare(b.label));

  select.innerHTML = "";
  const baseOptions = [
    { value: "__current__", text: "Current (auto)" },
    { value: "__all__", text: "All cycles" },
    { value: "__none__", text: "No cycle" }
  ];
  for (const optionData of baseOptions) {
    const option = document.createElement("option");
    option.value = optionData.value;
    option.textContent = optionData.text;
    select.appendChild(option);
  }

  for (const item of [...ranked, ...textOnly]) {
    const option = document.createElement("option");
    option.value = item.token;
    option.textContent = item.label;
    select.appendChild(option);
  }

  const validValues = new Set(Array.from(select.options).map((o) => o.value));
  select.value = validValues.has(previous) ? previous : "__current__";
}

function renderCourseList() {
  const container = document.getElementById("course-list");
  container.innerHTML = "";

  const filtered = filterCourses(courses);
  if (filtered.length === 0) {
    container.innerHTML = "<div class='muted'>No courses found. Open Blackboard dashboard and retry.</div>";
    return;
  }

  const grouped = groupByTerm(filtered);
  for (const [term, items] of grouped.entries()) {
    const termEl = document.createElement("div");
    termEl.className = "term";
    termEl.textContent = term;
    container.appendChild(termEl);

    for (const c of items) {
      const row = document.createElement("label");
      row.className = "course-item";
      const checked = selectedCourseIds.has(c.id) ? "checked" : "";
      row.innerHTML = `
        <input class="course-checkbox" type="checkbox" value="${c.id}" ${checked} />
        <div>
          <div class="course-name">${c.name}</div>
          <div class="course-meta">${c.id} | ${c.status || "active"}</div>
        </div>
      `;
      container.appendChild(row);
    }
  }
}

function clearMaterialPreview() {
  detectedByCourse = new Map();
  selectedMaterialKeys = new Set();
  renderMaterialList();
}

function setAllDetectedMaterials(checked) {
  if (checked) {
    for (const [courseId, data] of detectedByCourse.entries()) {
      for (const item of data.items || []) {
        selectedMaterialKeys.add(materialKey(courseId, item.url));
      }
    }
  } else {
    selectedMaterialKeys = new Set();
  }
  renderMaterialList();
}

function renderMaterialList() {
  const summary = document.getElementById("material-summary");
  const container = document.getElementById("material-list");
  container.innerHTML = "";

  if (detectedByCourse.size === 0) {
    summary.textContent = "No preview yet.";
    container.innerHTML = "<div class='muted'>Run Preview materials to inspect detected files/folders.</div>";
    return;
  }

  let total = 0;
  let selected = 0;

  for (const [courseId, data] of detectedByCourse.entries()) {
    const section = document.createElement("div");
    section.className = "material-course";

    const title = document.createElement("div");
    title.className = "material-course-title";
    const itemCount = (data.items || []).length;
    title.textContent = `${data.course.name} (${itemCount})`;
    section.appendChild(title);

    const grouped = new Map();
    const sorted = [...(data.items || [])].sort((a, b) => {
      const fa = String(a.folder || "");
      const fb = String(b.folder || "");
      if (fa !== fb) {
        return fa.localeCompare(fb);
      }
      return String(a.title || "").localeCompare(String(b.title || ""));
    });

    for (const item of sorted) {
      const folder = item.folder || "files";
      if (!grouped.has(folder)) {
        grouped.set(folder, []);
      }
      grouped.get(folder).push(item);
    }

    for (const [folder, items] of grouped.entries()) {
      const folderTitle = document.createElement("div");
      folderTitle.className = "material-folder-title";
      folderTitle.textContent = folder;
      section.appendChild(folderTitle);

      for (const item of items) {
        const key = materialKey(courseId, item.url);
        const checked = selectedMaterialKeys.has(key);
        total += 1;
        if (checked) {
          selected += 1;
        }

        const row = document.createElement("label");
        row.className = "material-item";

        const input = document.createElement("input");
        input.type = "checkbox";
        input.className = "material-checkbox";
        input.dataset.courseId = courseId;
        input.dataset.url = item.url;
        input.checked = checked;

        const textWrap = document.createElement("div");

        const name = document.createElement("div");
        name.className = "material-name";
        name.textContent = item.title || "resource";

        const url = document.createElement("div");
        url.className = "material-url";
        url.textContent = item.url || "";

        textWrap.appendChild(name);
        textWrap.appendChild(url);

        row.appendChild(input);
        row.appendChild(textWrap);
        section.appendChild(row);
      }
    }

    container.appendChild(section);
  }

  summary.textContent = `Detected ${total} material(s). Selected ${selected}.`;
}

async function previewSelectedMaterials() {
  const selectedCourses = getSelectedCourses();
  if (selectedCourses.length === 0) {
    setStatus("Select at least one course.");
    return;
  }

  setStatus(`Previewing materials for ${selectedCourses.length} course(s)...`);
  detectedByCourse = new Map();
  selectedMaterialKeys = new Set();

  for (const course of selectedCourses) {
    try {
      const resp = await chrome.tabs.sendMessage(activeTabId, {
        type: "crawl-course",
        course,
        settings
      });
      if (!resp || !resp.ok || !resp.data) {
        detectedByCourse.set(course.id, { course, items: [] });
        continue;
      }

      const unique = new Map();
      for (const item of resp.data.resources || []) {
        const url = normalizeUrl(item.url);
        if (!url || unique.has(url)) {
          continue;
        }
        unique.set(url, {
          url,
          title: item.title || "resource",
          folder: item.folder || "files",
          sourcePage: item.sourcePage || ""
        });
      }

      const items = Array.from(unique.values());
      detectedByCourse.set(course.id, { course, items });
      for (const item of items) {
        selectedMaterialKeys.add(materialKey(course.id, item.url));
      }
    } catch (_err) {
      detectedByCourse.set(course.id, { course, items: [] });
    }
  }

  renderMaterialList();
  setStatus("Preview completed. Review detected items and run download.");
}

async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

async function discoverCoursesFromPage(tabId) {
  try {
    const resp = await chrome.tabs.sendMessage(tabId, { type: "discover-courses" });
    if (!resp || !resp.ok) {
      return [];
    }
    return resp.courses || [];
  } catch (_err) {
    throw new Error("Could not read courses from page. Open a Blackboard page and retry.");
  }
}

async function loadSettings() {
  const resp = await chrome.runtime.sendMessage({ type: "get-settings" });
  if (!resp || !resp.ok) {
    throw new Error(resp && resp.error ? resp.error : "Could not load settings");
  }
  settings = resp.settings;
  document.getElementById("settings-summary").textContent = summarizeSettings(settings);
  document.getElementById("debug-mode-toggle").checked = !!settings.debugMode;
}

async function init() {
  setStatus("Detecting courses from current Blackboard page...");

  const activeTab = await getActiveTab();
  if (!activeTab || typeof activeTab.id !== "number") {
    setStatus("No active tab detected.");
    return;
  }
  activeTabId = activeTab.id;

  try {
    await loadSettings();
  } catch (err) {
    setStatus(`Error loading settings: ${String(err)}`);
    return;
  }

  await refreshCourses(false);
}

function applyCourseSet(nextCourses, preserveSelection) {
  const previous = new Set(selectedCourseIds);
  courses = Array.isArray(nextCourses) ? nextCourses : [];

  if (!preserveSelection || !hasSelectionState) {
    selectedCourseIds = new Set(courses.map((c) => c.id));
    hasSelectionState = true;
    return;
  }

  const available = new Set(courses.map((c) => c.id));
  const kept = new Set();
  for (const id of previous) {
    if (available.has(id)) {
      kept.add(id);
    }
  }
  selectedCourseIds = kept;
}

async function refreshCourses(preserveSelection = true) {
  if (typeof activeTabId !== "number") {
    setStatus("No active tab detected.");
    return;
  }

  setStatus("Refreshing courses from current page...");
  const nextCourses = await discoverCoursesFromPage(activeTabId);
  applyCourseSet(nextCourses, preserveSelection);
  renderCycleFilterOptions();
  renderCourseList();
  clearMaterialPreview();
  setStatus(`Detected ${courses.length} course(s).`);
}

async function downloadSelected() {
  const selectedCourses = getSelectedCourses();

  if (selectedCourses.length === 0) {
    setStatus("Select at least one course.");
    return;
  }

  setStatus(`Starting download for ${selectedCourses.length} course(s)...`);
  const payload = {
    tabId: activeTabId,
    courses: selectedCourses
  };

  if (detectedByCourse.size > 0) {
    for (const course of selectedCourses) {
      if (!detectedByCourse.has(course.id)) {
        setStatus("Preview is stale. Run Preview materials again.");
        return;
      }
    }

    const selectedResourceUrlsByCourse = {};
    let totalSelected = 0;

    for (const course of selectedCourses) {
      const data = detectedByCourse.get(course.id) || { items: [] };
      const urls = [];
      for (const item of data.items || []) {
        const key = materialKey(course.id, item.url);
        if (selectedMaterialKeys.has(key)) {
          urls.push(item.url);
        }
      }
      if (urls.length > 0) {
        selectedResourceUrlsByCourse[course.id] = urls;
        totalSelected += urls.length;
      }
    }

    if (totalSelected === 0) {
      setStatus("No detected materials selected. Use Preview materials first.");
      return;
    }

    payload.selectedResourceUrlsByCourse = selectedResourceUrlsByCourse;
  }

  const resp = await chrome.runtime.sendMessage({
    type: "download-courses",
    payload
  });

  if (!resp || !resp.ok) {
    setStatus(`Error: ${resp && resp.error ? resp.error : "Unknown"}`);
    return;
  }

  const lines = ["Done:"];
  for (const s of resp.result.summaries || []) {
    const reasonEntries = Object.entries(s.skippedByReason || {});
    const reasonSummary = reasonEntries.length
      ? ` | reasons=${reasonEntries.map(([k, v]) => `${k}:${v}`).join(", ")}`
      : "";
    const debugSummary = typeof s.debugEntries === "number" ? ` | debugEntries=${s.debugEntries}` : "";
    lines.push(
      `- ${s.courseName}: pages=${s.crawledPages}, resources=${s.foundResources}, downloaded=${s.downloaded}, skipped=${s.skipped}${reasonSummary}${debugSummary}`
    );
  }
  setStatus(lines.join("\n"));
}

function selectAll(checked) {
  if (checked) {
    selectedCourseIds = new Set(courses.map((c) => c.id));
  } else {
    selectedCourseIds.clear();
  }
  renderCourseList();
}

document.getElementById("download-selected").addEventListener("click", () => {
  downloadSelected().catch((err) => setStatus(`Error: ${String(err)}`));
});

document.getElementById("refresh-courses").addEventListener("click", () => {
  refreshCourses(true).catch((err) => setStatus(`Error: ${String(err)}`));
});
document.getElementById("select-all").addEventListener("click", () => selectAll(true));
document.getElementById("clear-all").addEventListener("click", () => selectAll(false));
document.getElementById("search").addEventListener("input", renderCourseList);
document.getElementById("show-active").addEventListener("change", renderCourseList);
document.getElementById("show-past").addEventListener("change", renderCourseList);
document.getElementById("cycle-filter").addEventListener("change", renderCourseList);
document.getElementById("open-settings").addEventListener("click", () => chrome.runtime.openOptionsPage());
document.getElementById("preview-selected").addEventListener("click", () => {
  previewSelectedMaterials().catch((err) => setStatus(`Error: ${String(err)}`));
});
document.getElementById("select-all-materials").addEventListener("click", () => setAllDetectedMaterials(true));
document.getElementById("clear-all-materials").addEventListener("click", () => setAllDetectedMaterials(false));
document.getElementById("course-list").addEventListener("change", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) {
    return;
  }
  if (!target.classList.contains("course-checkbox")) {
    return;
  }

  if (target.checked) {
    selectedCourseIds.add(target.value);
  } else {
    selectedCourseIds.delete(target.value);
  }
});

document.getElementById("material-list").addEventListener("change", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) {
    return;
  }
  if (!target.classList.contains("material-checkbox")) {
    return;
  }

  const courseId = target.dataset.courseId || "";
  const url = target.dataset.url || "";
  const key = materialKey(courseId, url);
  if (!key.includes("::")) {
    return;
  }

  if (target.checked) {
    selectedMaterialKeys.add(key);
  } else {
    selectedMaterialKeys.delete(key);
  }
  renderMaterialList();
});

document.getElementById("debug-mode-toggle").addEventListener("change", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) {
    return;
  }
  const wanted = !!target.checked;
  const previous = !!(settings && settings.debugMode);
  if (wanted === previous) {
    return;
  }

  try {
    const resp = await chrome.runtime.sendMessage({
      type: "save-settings",
      settings: { ...(settings || {}), debugMode: wanted }
    });
    if (!resp || !resp.ok) {
      throw new Error(resp && resp.error ? resp.error : "Could not save settings");
    }
    settings = resp.settings;
    document.getElementById("settings-summary").textContent = summarizeSettings(settings);
    target.checked = !!settings.debugMode;
    setStatus(`Debug mode ${settings.debugMode ? "enabled" : "disabled"}.`);
  } catch (err) {
    target.checked = previous;
    setStatus(`Error: ${String(err)}`);
  }
});

init().catch((err) => setStatus(`Init error: ${String(err)}`));
