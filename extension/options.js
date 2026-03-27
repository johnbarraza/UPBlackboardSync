const PRESETS = {
  full_archive: {
    filesFolders: true,
    pages: true,
    assignments: true,
    discussions: true,
    announcements: true,
    modules: true,
    syllabus: true,
    gradesCsv: true,
    linkedExtracted: true,
    text: true
  },
  files_only: {
    filesFolders: true,
    pages: false,
    assignments: false,
    discussions: false,
    announcements: false,
    modules: false,
    syllabus: false,
    gradesCsv: false,
    linkedExtracted: true,
    text: false
  },
  text_only: {
    filesFolders: false,
    pages: true,
    assignments: true,
    discussions: true,
    announcements: true,
    modules: true,
    syllabus: true,
    gradesCsv: true,
    linkedExtracted: false,
    text: true
  },
  linked_only: {
    filesFolders: false,
    pages: false,
    assignments: false,
    discussions: false,
    announcements: false,
    modules: false,
    syllabus: false,
    gradesCsv: false,
    linkedExtracted: true,
    text: false
  }
};

const DEFAULT_SETTINGS = {
  exportPreset: "full_archive",
  contentTypes: { ...PRESETS.full_archive },
  conflictHandling: "uniquify",
  delayMs: 250,
  folderPrefix: "",
  zipBundling: true,
  incrementalMode: true,
  excludeVideo: false,
  maxFileSizeMb: 0,
  maxPagesPerCourse: 60
};

function setStatus(msg) {
  document.getElementById("status").textContent = msg;
}

function readForm() {
  const exportPreset = document.getElementById("export-preset").value;
  return {
    exportPreset,
    contentTypes: {
      filesFolders: document.getElementById("ct-files-folders").checked,
      pages: document.getElementById("ct-pages").checked,
      assignments: document.getElementById("ct-assignments").checked,
      discussions: document.getElementById("ct-discussions").checked,
      announcements: document.getElementById("ct-announcements").checked,
      modules: document.getElementById("ct-modules").checked,
      syllabus: document.getElementById("ct-syllabus").checked,
      gradesCsv: document.getElementById("ct-grades").checked,
      linkedExtracted: document.getElementById("ct-linked").checked,
      text: document.getElementById("ct-text").checked
    },
    conflictHandling: document.getElementById("conflict-handling").value,
    delayMs: Number(document.getElementById("delay-ms").value || 0),
    folderPrefix: document.getElementById("folder-prefix").value || "",
    zipBundling: document.getElementById("zip-bundling").checked,
    incrementalMode: document.getElementById("incremental-mode").checked,
    excludeVideo: document.getElementById("exclude-video").checked,
    maxFileSizeMb: Number(document.getElementById("max-file-size").value || 0),
    maxPagesPerCourse: Number(document.getElementById("max-pages").value || 60)
  };
}

function fillForm(settings) {
  document.getElementById("export-preset").value = settings.exportPreset || "custom";
  document.getElementById("ct-files-folders").checked = !!settings.contentTypes.filesFolders;
  document.getElementById("ct-pages").checked = !!settings.contentTypes.pages;
  document.getElementById("ct-assignments").checked = !!settings.contentTypes.assignments;
  document.getElementById("ct-discussions").checked = !!settings.contentTypes.discussions;
  document.getElementById("ct-announcements").checked = !!settings.contentTypes.announcements;
  document.getElementById("ct-modules").checked = !!settings.contentTypes.modules;
  document.getElementById("ct-syllabus").checked = !!settings.contentTypes.syllabus;
  document.getElementById("ct-grades").checked = !!settings.contentTypes.gradesCsv;
  document.getElementById("ct-linked").checked = !!settings.contentTypes.linkedExtracted;
  document.getElementById("ct-text").checked = !!settings.contentTypes.text;
  document.getElementById("conflict-handling").value = settings.conflictHandling || "uniquify";
  document.getElementById("delay-ms").value = settings.delayMs ?? 250;
  document.getElementById("folder-prefix").value = settings.folderPrefix || "";
  document.getElementById("zip-bundling").checked = !!settings.zipBundling;
  document.getElementById("incremental-mode").checked = !!settings.incrementalMode;
  document.getElementById("exclude-video").checked = !!settings.excludeVideo;
  document.getElementById("max-file-size").value = settings.maxFileSizeMb ?? 0;
  document.getElementById("max-pages").value = settings.maxPagesPerCourse ?? 60;
}

function applyPresetToForm(presetKey) {
  const preset = PRESETS[presetKey];
  if (!preset) {
    return;
  }
  document.getElementById("ct-files-folders").checked = preset.filesFolders;
  document.getElementById("ct-pages").checked = preset.pages;
  document.getElementById("ct-assignments").checked = preset.assignments;
  document.getElementById("ct-discussions").checked = preset.discussions;
  document.getElementById("ct-announcements").checked = preset.announcements;
  document.getElementById("ct-modules").checked = preset.modules;
  document.getElementById("ct-syllabus").checked = preset.syllabus;
  document.getElementById("ct-grades").checked = preset.gradesCsv;
  document.getElementById("ct-linked").checked = preset.linkedExtracted;
  document.getElementById("ct-text").checked = preset.text;
}

async function loadSettings() {
  const resp = await chrome.runtime.sendMessage({ type: "get-settings" });
  if (!resp || !resp.ok) {
    throw new Error(resp && resp.error ? resp.error : "Could not load settings");
  }
  fillForm(resp.settings);
}

async function saveSettings() {
  const payload = readForm();
  const resp = await chrome.runtime.sendMessage({
    type: "save-settings",
    settings: payload
  });
  if (!resp || !resp.ok) {
    throw new Error(resp && resp.error ? resp.error : "Could not save settings");
  }
  fillForm(resp.settings);
  setStatus("Settings saved.");
}

document.getElementById("export-preset").addEventListener("change", (e) => {
  const value = e.target.value;
  if (value !== "custom") {
    applyPresetToForm(value);
  }
});

document.getElementById("save").addEventListener("click", () => {
  saveSettings().catch((err) => setStatus(`Error: ${String(err)}`));
});

document.getElementById("reset").addEventListener("click", () => {
  fillForm(DEFAULT_SETTINGS);
  setStatus("Defaults loaded. Click Save settings to persist.");
});

loadSettings()
  .then(() => setStatus("Loaded."))
  .catch((err) => setStatus(`Error: ${String(err)}`));
