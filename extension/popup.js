let activeTabId = null;
let courses = [];
let settings = null;

function setStatus(message) {
  document.getElementById("status").textContent = message;
}

function getSelectedCourseIds() {
  return Array.from(document.querySelectorAll(".course-checkbox:checked"))
    .map((el) => el.value);
}

function summarizeSettings(s) {
  return [
    `University: ${s.universityLabel || "n/a"}`,
    `Host: ${s.preferredHost || "auto"}`,
    `Preset: ${s.exportPreset}`,
    `ZIP: ${s.zipBundling ? "on" : "off"}`,
    `Incremental: ${s.incrementalMode ? "on" : "off"}`,
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

  return list.filter((course) => {
    const statusOk =
      (course.status === "active" && showActive) ||
      (course.status === "past" && showPast) ||
      (!course.status && showActive);
    if (!statusOk) {
      return false;
    }
    if (!query) {
      return true;
    }
    const haystack = `${course.name} ${course.term} ${course.id}`.toLowerCase();
    return haystack.includes(query);
  });
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
      row.innerHTML = `
        <input class="course-checkbox" type="checkbox" value="${c.id}" checked />
        <div>
          <div class="course-name">${c.name}</div>
          <div class="course-meta">${c.id} | ${c.status || "active"}</div>
        </div>
      `;
      container.appendChild(row);
    }
  }
}

async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

async function discoverCoursesFromPage(tabId) {
  const resp = await chrome.tabs.sendMessage(tabId, { type: "discover-courses" });
  if (!resp || !resp.ok) {
    return [];
  }
  return resp.courses || [];
}

async function loadSettings() {
  const resp = await chrome.runtime.sendMessage({ type: "get-settings" });
  if (!resp || !resp.ok) {
    throw new Error(resp && resp.error ? resp.error : "Could not load settings");
  }
  settings = resp.settings;
  document.getElementById("settings-summary").textContent = summarizeSettings(settings);
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

  try {
    courses = await discoverCoursesFromPage(activeTabId);
    renderCourseList();
    setStatus(`Detected ${courses.length} course(s).`);
  } catch (err) {
    setStatus(`Could not discover courses on this page: ${String(err)}`);
  }
}

async function downloadSelected() {
  const selectedIds = new Set(getSelectedCourseIds());
  const selectedCourses = courses.filter((c) => selectedIds.has(c.id));

  if (selectedCourses.length === 0) {
    setStatus("Select at least one course.");
    return;
  }

  setStatus(`Starting download for ${selectedCourses.length} course(s)...`);

  const resp = await chrome.runtime.sendMessage({
    type: "download-courses",
    payload: {
      tabId: activeTabId,
      courses: selectedCourses
    }
  });

  if (!resp || !resp.ok) {
    setStatus(`Error: ${resp && resp.error ? resp.error : "Unknown"}`);
    return;
  }

  const lines = ["Done:"];
  for (const s of resp.result.summaries || []) {
    lines.push(
      `- ${s.courseName}: pages=${s.crawledPages}, resources=${s.foundResources}, downloaded=${s.downloaded}, skipped=${s.skipped}`
    );
  }
  setStatus(lines.join("\n"));
}

function selectAll(checked) {
  for (const el of document.querySelectorAll(".course-checkbox")) {
    el.checked = checked;
  }
}

document.getElementById("download-selected").addEventListener("click", () => {
  downloadSelected().catch((err) => setStatus(`Error: ${String(err)}`));
});

document.getElementById("select-all").addEventListener("click", () => selectAll(true));
document.getElementById("clear-all").addEventListener("click", () => selectAll(false));
document.getElementById("search").addEventListener("input", renderCourseList);
document.getElementById("show-active").addEventListener("change", renderCourseList);
document.getElementById("show-past").addEventListener("change", renderCourseList);
document.getElementById("open-settings").addEventListener("click", () => chrome.runtime.openOptionsPage());

init().catch((err) => setStatus(`Init error: ${String(err)}`));
