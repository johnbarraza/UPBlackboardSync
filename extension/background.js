function sanitizeName(input) {
  return String(input || "")
    .replace(/[<>:"/\\|?*\u0000-\u001F]/g, "_")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 180) || "resource";
}

function ensureExtension(name, url) {
  if (/\.[A-Za-z0-9]{2,6}$/.test(name)) {
    return name;
  }
  try {
    const parsed = new URL(url);
    const part = parsed.pathname.split("/").filter(Boolean).pop() || "";
    if (/\.[A-Za-z0-9]{2,6}$/.test(part)) {
      return sanitizeName(part);
    }
  } catch (_err) {
    // fallback below
  }
  return `${name}.html`;
}

async function queueDownloads(payload) {
  const course = sanitizeName(payload.courseTitle || "Blackboard Course");
  let count = 0;
  for (const item of payload.links || []) {
    const safeBase = sanitizeName(item.title || "resource");
    const filename = `${course}/${ensureExtension(safeBase, item.url)}`;
    await chrome.downloads.download({
      url: item.url,
      filename,
      conflictAction: "uniquify",
      saveAs: false
    });
    count += 1;
  }
  return count;
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "download-links") {
    queueDownloads(msg.payload)
      .then((count) => sendResponse({ ok: true, count }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }
  return false;
});
