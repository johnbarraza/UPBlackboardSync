const PRESETS = {
  essentials: {
    contentTypes: {
      filesFolders: true,
      pages: false,
      assignments: false,
      discussions: false,
      announcements: true,
      modules: false,
      syllabus: false,
      gradesCsv: false,
      linkedExtracted: true,
      text: true
    }
  },
  full_archive: {
    contentTypes: {
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
    }
  },
  files_only: {
    contentTypes: {
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
    }
  },
  text_only: {
    contentTypes: {
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
    }
  },
  linked_only: {
    contentTypes: {
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
  }
};

const DEFAULT_SETTINGS = {
  universityLabel: "",
  preferredHost: "",
  exportPreset: "essentials",
  contentTypes: {
    filesFolders: true,
    pages: false,
    assignments: false,
    discussions: false,
    announcements: true,
    modules: false,
    syllabus: false,
    gradesCsv: false,
    linkedExtracted: true,
    text: true
  },
  conflictHandling: "uniquify",
  delayMs: 250,
  folderPrefix: "",
  zipBundling: true,
  incrementalMode: true,
  debugMode: false,
  excludeVideo: false,
  maxFileSizeMb: 0,
  maxPagesPerCourse: 60
};

const VIDEO_EXT_RE = /\.(mp4|mov|avi|mkv|webm|wmv|flv|m4v)$/i;
const FILE_EXT_RE = /\.[A-Za-z0-9]{2,8}$/;
const BLACKBOARD_FILE_ROUTE_RE = /\/ultra\/courses\/[^/]+\/outline\/file\/[^/?#]+(?:\/download)?/i;
const BLACKBOARD_DOCUMENT_ROUTE_RE = /\/ultra\/courses\/[^/]+\/outline\/edit\/document\/[^/?#]+(?:\/download)?/i;
const DOWNLOAD_HINT_RE = /(bbcswebdav|xythos-download|\/download\b|[?&]download=)/i;
const MOJIBAKE_RE = /(?:\u00C3|\u00C2|\u00E2|\uFFFD)/;

function fixMojibake(input) {
  const raw = String(input || "");
  if (!MOJIBAKE_RE.test(raw)) {
    return raw;
  }
  try {
    const bytes = new Uint8Array(Array.from(raw, (ch) => ch.charCodeAt(0) & 0xff));
    const decoded = new TextDecoder("utf-8", { fatal: false }).decode(bytes);
    const badRaw = (raw.match(/[\u00C2\u00C3\u00E2\uFFFD]/g) || []).length;
    const badDecoded = (decoded.match(/[\u00C2\u00C3\u00E2\uFFFD]/g) || []).length;
    if (badDecoded < badRaw) {
      return decoded;
    }
  } catch (_err) {
    // keep original text
  }
  return raw;
}

function sanitizeName(input) {
  return fixMojibake(String(input || ""))
    .replace(/[<>:"/\\|?*\u0000-\u001F]/g, "_")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 180) || "item";
}

function mergeSettings(raw) {
  const data = raw || {};
  const merged = {
    ...DEFAULT_SETTINGS,
    ...data,
    contentTypes: {
      ...DEFAULT_SETTINGS.contentTypes,
      ...(data.contentTypes || {})
    }
  };

  if (merged.exportPreset && PRESETS[merged.exportPreset]) {
    merged.contentTypes = {
      ...merged.contentTypes,
      ...PRESETS[merged.exportPreset].contentTypes
    };
  }

  merged.delayMs = Math.max(0, Number(merged.delayMs || 0));
  merged.maxFileSizeMb = Math.max(0, Number(merged.maxFileSizeMb || 0));
  merged.maxPagesPerCourse = Math.max(1, Number(merged.maxPagesPerCourse || 60));
  merged.folderPrefix = String(merged.folderPrefix || "").trim();
  merged.universityLabel = String(merged.universityLabel || "").trim();
  merged.preferredHost = String(merged.preferredHost || "")
    .replace(/^https?:\/\//i, "")
    .replace(/\/+$/, "")
    .trim();

  return merged;
}

async function getSettings() {
  const data = await chrome.storage.local.get(["settings"]);
  return mergeSettings(data.settings);
}

async function saveSettings(settings) {
  const normalized = mergeSettings(settings);
  await chrome.storage.local.set({ settings: normalized });
  return normalized;
}

function csvEscape(value) {
  const text = String(value || "").replace(/\r?\n/g, " ");
  if (/[",]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function buildGradesCsv(rows) {
  const header = [
    "Assignment",
    "Due Date",
    "Points",
    "Score",
    "Letter Grade",
    "Notes"
  ];
  const lines = [header.join(",")];
  for (const row of rows || []) {
    const cols = [...row];
    while (cols.length < 6) {
      cols.push("");
    }
    lines.push(cols.slice(0, 6).map(csvEscape).join(","));
  }
  return lines.join("\n") + "\n";
}

function uint8ToDataUrl(bytes, mime) {
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    const view = bytes.subarray(i, i + chunk);
    binary += String.fromCharCode(...view);
  }
  return `data:${mime};base64,${btoa(binary)}`;
}

function toUtf8Bytes(text) {
  return new TextEncoder().encode(String(text || ""));
}

function crc32(bytes) {
  let crc = -1;
  for (let i = 0; i < bytes.length; i += 1) {
    crc ^= bytes[i];
    for (let j = 0; j < 8; j += 1) {
      const mask = -(crc & 1);
      crc = (crc >>> 1) ^ (0xedb88320 & mask);
    }
  }
  return (crc ^ -1) >>> 0;
}

function writeU16(arr, value) {
  arr.push(value & 0xff, (value >>> 8) & 0xff);
}

function writeU32(arr, value) {
  arr.push(value & 0xff, (value >>> 8) & 0xff, (value >>> 16) & 0xff, (value >>> 24) & 0xff);
}

function zipStored(files) {
  const enc = new TextEncoder();
  const local = [];
  const central = [];
  let offset = 0;

  for (const file of files) {
    const nameBytes = enc.encode(file.name);
    const data = file.bytes;
    const c = crc32(data);

    const localHeader = [];
    writeU32(localHeader, 0x04034b50);
    writeU16(localHeader, 20);
    writeU16(localHeader, 0);
    writeU16(localHeader, 0);
    writeU16(localHeader, 0);
    writeU16(localHeader, 0);
    writeU32(localHeader, c);
    writeU32(localHeader, data.length);
    writeU32(localHeader, data.length);
    writeU16(localHeader, nameBytes.length);
    writeU16(localHeader, 0);

    local.push(new Uint8Array(localHeader), nameBytes, data);

    const centralHeader = [];
    writeU32(centralHeader, 0x02014b50);
    writeU16(centralHeader, 20);
    writeU16(centralHeader, 20);
    writeU16(centralHeader, 0);
    writeU16(centralHeader, 0);
    writeU16(centralHeader, 0);
    writeU16(centralHeader, 0);
    writeU32(centralHeader, c);
    writeU32(centralHeader, data.length);
    writeU32(centralHeader, data.length);
    writeU16(centralHeader, nameBytes.length);
    writeU16(centralHeader, 0);
    writeU16(centralHeader, 0);
    writeU16(centralHeader, 0);
    writeU16(centralHeader, 0);
    writeU32(centralHeader, 0);
    writeU32(centralHeader, offset);

    central.push(new Uint8Array(centralHeader), nameBytes);

    offset += localHeader.length + nameBytes.length + data.length;
  }

  const centralSize = central.reduce((acc, part) => acc + part.length, 0);
  const end = [];
  writeU32(end, 0x06054b50);
  writeU16(end, 0);
  writeU16(end, 0);
  writeU16(end, files.length);
  writeU16(end, files.length);
  writeU32(end, centralSize);
  writeU32(end, offset);
  writeU16(end, 0);

  const parts = [...local, ...central, new Uint8Array(end)];
  const total = parts.reduce((acc, p) => acc + p.length, 0);
  const out = new Uint8Array(total);
  let ptr = 0;
  for (const part of parts) {
    out.set(part, ptr);
    ptr += part.length;
  }
  return out;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function normalizeUrl(url) {
  try {
    return new URL(url).toString();
  } catch (_err) {
    return "";
  }
}

function ensureFileName(base, url, contentType) {
  const cleaned = sanitizeName(base);
  if (FILE_EXT_RE.test(cleaned)) {
    return cleaned;
  }
  try {
    const u = new URL(url);
    const last = decodeURIComponent(u.pathname.split("/").filter(Boolean).pop() || "");
    if (FILE_EXT_RE.test(last)) {
      return sanitizeName(last);
    }
  } catch (_err) {
    // ignore
  }
  if ((contentType || "").includes("pdf")) {
    return `${cleaned}.pdf`;
  }
  if ((contentType || "").includes("html")) {
    return `${cleaned}.html`;
  }
  return `${cleaned}.bin`;
}

function removeExtension(filename) {
  return String(filename || "").replace(/\.[A-Za-z0-9]{1,10}$/, "");
}

function looksLikeHtml(bytes) {
  try {
    const head = new TextDecoder("utf-8")
      .decode(bytes.subarray(0, 512))
      .toLowerCase();
    return head.includes("<html") || head.includes("<!doctype html");
  } catch (_err) {
    return false;
  }
}

function looksLikePdf(bytes) {
  if (!(bytes instanceof Uint8Array) || bytes.length < 5) {
    return false;
  }
  return (
    bytes[0] === 0x25 && // %
    bytes[1] === 0x50 && // P
    bytes[2] === 0x44 && // D
    bytes[3] === 0x46 && // F
    bytes[4] === 0x2d // -
  );
}

function isHtmlPayload(bytes, meta) {
  const contentType = String((meta && meta.contentType) || "").toLowerCase();
  return contentType.includes("text/html") || looksLikeHtml(bytes);
}

function seemsPdfTarget(filename, url, meta) {
  const lowerName = String(filename || "").toLowerCase();
  const lowerUrl = String(url || "").toLowerCase();
  const contentType = String((meta && meta.contentType) || "").toLowerCase();
  return (
    lowerName.endsWith(".pdf") ||
    /\.pdf(?:$|[?#])/.test(lowerUrl) ||
    contentType.includes("application/pdf")
  );
}

function normalizeDownloadedFilename(filename, meta, bytes) {
  const lower = String(filename || "").toLowerCase();
  if (isHtmlPayload(bytes, meta)) {
    if (!lower.endsWith(".html") && !lower.endsWith(".htm")) {
      return `${removeExtension(filename)}.html`;
    }
  }
  return filename;
}

function validateDownloadedPayload(filename, url, meta, bytes) {
  if (isHtmlPayload(bytes, meta)) {
    return { keep: false, reason: "html-response" };
  }

  if (seemsPdfTarget(filename, url, meta) && !looksLikePdf(bytes)) {
    return { keep: false, reason: "invalid-pdf" };
  }

  return { keep: true };
}

function isVideoResource(url, contentType) {
  return VIDEO_EXT_RE.test(url || "") || (contentType || "").toLowerCase().includes("video");
}

function makeSignature(url, meta) {
  return `${url}::${meta.lastModified || ""}::${meta.contentLength || ""}`;
}

async function getHistory() {
  const data = await chrome.storage.local.get(["downloadHistory"]);
  return data.downloadHistory || {};
}

async function setHistory(history) {
  await chrome.storage.local.set({ downloadHistory: history });
}

async function sendToTab(tabId, message) {
  return chrome.tabs.sendMessage(tabId, message);
}

async function fetchResource(url) {
  const response = await fetch(url, {
    credentials: "include",
    redirect: "follow"
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} for ${url}`);
  }

  const contentType = response.headers.get("content-type") || "application/octet-stream";
  const contentLength = Number(response.headers.get("content-length") || "0") || 0;
  const lastModified = response.headers.get("last-modified") || "";
  const buffer = await response.arrayBuffer();

  return {
    bytes: new Uint8Array(buffer),
    meta: {
      contentType,
      contentLength: contentLength || buffer.byteLength,
      lastModified
    }
  };
}

function decodeBytesAsText(bytes) {
  try {
    return new TextDecoder("utf-8").decode(bytes);
  } catch (_err) {
    return "";
  }
}

function isLikelyBinaryUrl(url) {
  const lower = String(url || "").toLowerCase();
  return (
    DOWNLOAD_HINT_RE.test(lower) ||
    BLACKBOARD_FILE_ROUTE_RE.test(lower) ||
    /\/bbcswebdav\//i.test(lower) ||
    FILE_EXT_RE.test(lower)
  );
}

function buildFetchCandidates(rawUrl) {
  const source = normalizeUrl(rawUrl);
  if (!source) {
    return [];
  }

  const out = new Set([source]);
  let parsed;
  try {
    parsed = new URL(source);
  } catch (_err) {
    return Array.from(out);
  }

  const fileMatch = parsed.pathname.match(/^\/ultra\/courses\/([^/]+)\/outline\/file\/([^/?#]+)/i);
  if (fileMatch) {
    out.add(`${parsed.origin}/ultra/courses/${fileMatch[1]}/outline/file/${fileMatch[2]}/download`);
    out.add(`${parsed.origin}/ultra/courses/${fileMatch[1]}/outline/file/${fileMatch[2]}?download=true`);
  }

  const docMatch = parsed.pathname.match(/^\/ultra\/courses\/([^/]+)\/outline\/edit\/document\/([^/?#]+)/i);
  if (docMatch) {
    out.add(`${parsed.origin}/ultra/courses/${docMatch[1]}/outline/edit/document/${docMatch[2]}/download`);
  }

  return Array.from(out);
}

function extractDownloadCandidatesFromHtml(html, baseUrl) {
  const out = new Set();
  const source = String(html || "");
  const unescaped = source.replace(/\\\//g, "/");

  const addCandidate = (raw) => {
    const normalized = normalizeUrl(raw ? new URL(raw, baseUrl).toString() : "");
    if (!normalized) {
      return;
    }
    if (!isLikelyBinaryUrl(normalized)) {
      return;
    }
    out.add(normalized);
  };

  const attrRe = /(?:href|src)\s*=\s*["']([^"']+)["']/gi;
  for (const match of unescaped.matchAll(attrRe)) {
    if (match[1]) {
      try {
        addCandidate(match[1]);
      } catch (_err) {
        // ignore malformed URLs
      }
    }
  }

  const urlRe = /https?:\/\/[^"'\\\s<>]+|\/[^"'\\\s<>]+/gi;
  for (const match of unescaped.matchAll(urlRe)) {
    const candidate = match[0];
    if (!candidate) {
      continue;
    }
    try {
      addCandidate(candidate);
    } catch (_err) {
      // ignore malformed URLs
    }
  }

  return Array.from(out).slice(0, 15);
}

async function fetchResourceWithFallback(url) {
  const candidates = buildFetchCandidates(url);
  const tried = new Set();
  let htmlFallback = null;
  let lastError = null;

  const tryCandidate = async (candidateUrl) => {
    if (!candidateUrl || tried.has(candidateUrl)) {
      return null;
    }
    tried.add(candidateUrl);
    const fetched = await fetchResource(candidateUrl);
    const htmlLike = (fetched.meta.contentType || "").toLowerCase().includes("html") || looksLikeHtml(fetched.bytes);
    if (!htmlLike) {
      return { ...fetched, resolvedUrl: candidateUrl };
    }
    if (!htmlFallback) {
      htmlFallback = { ...fetched, resolvedUrl: candidateUrl };
    }
    const html = decodeBytesAsText(fetched.bytes);
    const embedded = extractDownloadCandidatesFromHtml(html, candidateUrl);
    for (const embeddedUrl of embedded) {
      try {
        const nested = await tryCandidate(embeddedUrl);
        if (nested) {
          return nested;
        }
      } catch (_err) {
        // continue trying other candidates
      }
    }
    return null;
  };

  for (const candidate of candidates) {
    try {
      const resolved = await tryCandidate(candidate);
      if (resolved) {
        return resolved;
      }
    } catch (err) {
      lastError = err;
    }
  }

  if (htmlFallback) {
    return htmlFallback;
  }
  if (lastError) {
    throw lastError;
  }
  throw new Error(`Could not fetch resource: ${url}`);
}

function applyResourceFilters(url, meta, settings) {
  if (settings.excludeVideo && isVideoResource(url, meta.contentType)) {
    return { keep: false, reason: "video" };
  }
  if (settings.maxFileSizeMb > 0) {
    const maxBytes = settings.maxFileSizeMb * 1024 * 1024;
    if ((meta.contentLength || 0) > maxBytes) {
      return { keep: false, reason: "max-size" };
    }
  }
  return { keep: true };
}

function dedupeResources(resources) {
  const map = new Map();
  for (const item of resources || []) {
    const url = normalizeUrl(item.url);
    if (!url) {
      continue;
    }
    if (!map.has(url)) {
      map.set(url, { ...item, url });
    }
  }
  return Array.from(map.values());
}

async function downloadDataFile(filename, mime, textOrBytes, conflictAction) {
  const bytes = textOrBytes instanceof Uint8Array ? textOrBytes : toUtf8Bytes(textOrBytes);
  const url = uint8ToDataUrl(bytes, mime);
  await chrome.downloads.download({
    url,
    filename,
    conflictAction,
    saveAs: false
  });
}

async function processCourse(tabId, course, settings, historyRoot, selectedResourceUrls) {
  const debugEnabled = !!settings.debugMode;
  const debugEntries = [];
  const fallbackUrl = settings.preferredHost
    ? `https://${settings.preferredHost}/ultra/courses/${encodeURIComponent(course.id)}/outline`
    : "";
  const resolvedUrl = normalizeUrl(course.url) || fallbackUrl;
  const resolvedCourse = {
    ...course,
    url: resolvedUrl || course.url
  };

  const crawlResp = await sendToTab(tabId, {
    type: "crawl-course",
    course: resolvedCourse,
    settings
  });

  if (!crawlResp || !crawlResp.ok) {
    throw new Error(crawlResp && crawlResp.error ? crawlResp.error : "Could not crawl course");
  }

  const data = crawlResp.data;
  let resources = dedupeResources(data.resources);
  if (Array.isArray(selectedResourceUrls)) {
    const allowed = new Set(
      selectedResourceUrls
        .map((url) => normalizeUrl(url))
        .filter(Boolean)
    );
    resources = resources.filter((item) => allowed.has(normalizeUrl(item.url)));
  }
  const textFiles = data.textFiles || [];
  const gradeRows = data.gradeRows || [];
  const downloaded = [];
  const skipped = [];

  const host = resolvedUrl ? new URL(resolvedUrl).host : "unknown-host";
  const hostRoot = historyRoot[host] || {};
  const courseRoot = hostRoot[course.id] || {};

  const prefix = settings.folderPrefix ? `${sanitizeName(settings.folderPrefix)}/` : "";
  const courseFolder = `${prefix}${sanitizeName(course.name || course.id)}`;

  if (settings.zipBundling) {
    const filesForZip = [];

    for (const textFile of textFiles) {
      filesForZip.push({
        name: `${courseFolder}/${textFile.path}`,
        bytes: toUtf8Bytes(textFile.body)
      });
    }

    for (const resource of resources) {
      try {
        const fetched = await fetchResourceWithFallback(resource.url);
        const resolvedUrl = fetched.resolvedUrl || resource.url;
        const contentType = fetched.meta.contentType || "";
        const contentLength = fetched.meta.contentLength || fetched.bytes.length || 0;
        const verdict = applyResourceFilters(resolvedUrl, fetched.meta, settings);
        if (!verdict.keep) {
          skipped.push({ url: resource.url, reason: verdict.reason });
          if (debugEnabled) {
            debugEntries.push({
              requestedUrl: resource.url,
              resolvedUrl,
              title: resource.title || "",
              folder: resource.folder || "files",
              sourcePage: resource.sourcePage || "",
              contentType,
              contentLength,
              outcome: "skipped",
              reason: verdict.reason
            });
          }
          continue;
        }

        const signature = makeSignature(resolvedUrl, fetched.meta);
        if (settings.incrementalMode && courseRoot[signature]) {
          skipped.push({ url: resource.url, reason: "incremental" });
          if (debugEnabled) {
            debugEntries.push({
              requestedUrl: resource.url,
              resolvedUrl,
              title: resource.title || "",
              folder: resource.folder || "files",
              sourcePage: resource.sourcePage || "",
              contentType,
              contentLength,
              outcome: "skipped",
              reason: "incremental"
            });
          }
          continue;
        }

        const filename = normalizeDownloadedFilename(
          ensureFileName(resource.title, resolvedUrl, fetched.meta.contentType),
          fetched.meta,
          fetched.bytes
        );
        const payloadVerdict = validateDownloadedPayload(
          filename,
          resolvedUrl,
          fetched.meta,
          fetched.bytes
        );
        if (!payloadVerdict.keep) {
          skipped.push({ url: resource.url, reason: payloadVerdict.reason });
          if (debugEnabled) {
            debugEntries.push({
              requestedUrl: resource.url,
              resolvedUrl,
              title: resource.title || "",
              folder: resource.folder || "files",
              sourcePage: resource.sourcePage || "",
              contentType,
              contentLength,
              filename,
              outcome: "skipped",
              reason: payloadVerdict.reason
            });
          }
          continue;
        }
        const folder = sanitizeName(resource.folder || "files");
        const zipPath = `${courseFolder}/${folder}/${filename}`;
        filesForZip.push({ name: zipPath, bytes: fetched.bytes });
        courseRoot[signature] = true;
        downloaded.push(resource.url);
        if (debugEnabled) {
          debugEntries.push({
            requestedUrl: resource.url,
            resolvedUrl,
            title: resource.title || "",
            folder: resource.folder || "files",
            sourcePage: resource.sourcePage || "",
            contentType,
            contentLength,
            filename,
            outcome: "downloaded"
          });
        }
      } catch (_err) {
        skipped.push({ url: resource.url, reason: "fetch-failed" });
        if (debugEnabled) {
          debugEntries.push({
            requestedUrl: resource.url,
            resolvedUrl: "",
            title: resource.title || "",
            folder: resource.folder || "files",
            sourcePage: resource.sourcePage || "",
            outcome: "skipped",
            reason: "fetch-failed",
            error: String(_err)
          });
        }
      }
    }

    if (settings.contentTypes.gradesCsv && gradeRows.length > 0) {
      filesForZip.push({
        name: `${courseFolder}/grades.csv`,
        bytes: toUtf8Bytes(buildGradesCsv(gradeRows))
      });
    }

    if (debugEnabled) {
      const report = {
        generatedAt: new Date().toISOString(),
        courseId: course.id,
        courseName: course.name,
        crawledPages: data.crawledPages,
        foundResources: resources.length,
        downloaded: downloaded.length,
        skipped: skipped.length,
        entries: debugEntries
      };
      filesForZip.push({
        name: `${courseFolder}/debug/debug_report.json`,
        bytes: toUtf8Bytes(JSON.stringify(report, null, 2))
      });
    }

    if (filesForZip.length > 0) {
      const zip = zipStored(filesForZip);
      const zipName = `${courseFolder}.zip`;
      await downloadDataFile(zipName, "application/zip", zip, settings.conflictHandling);
    }
  } else {
    for (const textFile of textFiles) {
      const filename = `${courseFolder}/${textFile.path}`;
      await downloadDataFile(filename, "text/html", textFile.body, settings.conflictHandling);
      if (settings.delayMs > 0) {
        await sleep(settings.delayMs);
      }
    }

    for (const resource of resources) {
      try {
        const fetched = await fetchResourceWithFallback(resource.url);
        const resolvedUrl = fetched.resolvedUrl || resource.url;
        const meta = fetched.meta;
        const contentType = meta.contentType || "";
        const contentLength = meta.contentLength || fetched.bytes.length || 0;
        const verdict = applyResourceFilters(resolvedUrl, meta, settings);
        if (!verdict.keep) {
          skipped.push({ url: resource.url, reason: verdict.reason });
          if (debugEnabled) {
            debugEntries.push({
              requestedUrl: resource.url,
              resolvedUrl,
              title: resource.title || "",
              folder: resource.folder || "files",
              sourcePage: resource.sourcePage || "",
              contentType,
              contentLength,
              outcome: "skipped",
              reason: verdict.reason
            });
          }
          continue;
        }

        const signature = makeSignature(resolvedUrl, meta);
        if (settings.incrementalMode && courseRoot[signature]) {
          skipped.push({ url: resource.url, reason: "incremental" });
          if (debugEnabled) {
            debugEntries.push({
              requestedUrl: resource.url,
              resolvedUrl,
              title: resource.title || "",
              folder: resource.folder || "files",
              sourcePage: resource.sourcePage || "",
              contentType,
              contentLength,
              outcome: "skipped",
              reason: "incremental"
            });
          }
          continue;
        }

        const filename = normalizeDownloadedFilename(
          ensureFileName(resource.title, resolvedUrl, meta.contentType || ""),
          meta,
          fetched.bytes
        );
        const payloadVerdict = validateDownloadedPayload(
          filename,
          resolvedUrl,
          meta,
          fetched.bytes
        );
        if (!payloadVerdict.keep) {
          skipped.push({ url: resource.url, reason: payloadVerdict.reason });
          if (debugEnabled) {
            debugEntries.push({
              requestedUrl: resource.url,
              resolvedUrl,
              title: resource.title || "",
              folder: resource.folder || "files",
              sourcePage: resource.sourcePage || "",
              contentType,
              contentLength,
              filename,
              outcome: "skipped",
              reason: payloadVerdict.reason
            });
          }
          continue;
        }
        const folder = sanitizeName(resource.folder || "files");
        await downloadDataFile(
          `${courseFolder}/${folder}/${filename}`,
          meta.contentType || "application/octet-stream",
          fetched.bytes,
          settings.conflictHandling
        );
        courseRoot[signature] = true;
        downloaded.push(resource.url);
        if (debugEnabled) {
          debugEntries.push({
            requestedUrl: resource.url,
            resolvedUrl,
            title: resource.title || "",
            folder: resource.folder || "files",
            sourcePage: resource.sourcePage || "",
            contentType,
            contentLength,
            filename,
            outcome: "downloaded"
          });
        }
        if (settings.delayMs > 0) {
          await sleep(settings.delayMs);
        }
      } catch (_err) {
        skipped.push({ url: resource.url, reason: "download-failed" });
        if (debugEnabled) {
          debugEntries.push({
            requestedUrl: resource.url,
            resolvedUrl: "",
            title: resource.title || "",
            folder: resource.folder || "files",
            sourcePage: resource.sourcePage || "",
            outcome: "skipped",
            reason: "download-failed",
            error: String(_err)
          });
        }
      }
    }

    if (settings.contentTypes.gradesCsv && gradeRows.length > 0) {
      await downloadDataFile(
        `${courseFolder}/grades.csv`,
        "text/csv",
        buildGradesCsv(gradeRows),
        settings.conflictHandling
      );
    }

    if (debugEnabled) {
      const report = {
        generatedAt: new Date().toISOString(),
        courseId: course.id,
        courseName: course.name,
        crawledPages: data.crawledPages,
        foundResources: resources.length,
        downloaded: downloaded.length,
        skipped: skipped.length,
        entries: debugEntries
      };
      await downloadDataFile(
        `${courseFolder}/debug/debug_report.json`,
        "application/json",
        JSON.stringify(report, null, 2),
        settings.conflictHandling
      );
    }
  }

  hostRoot[course.id] = courseRoot;
  historyRoot[host] = hostRoot;

  return {
    courseId: course.id,
    courseName: course.name,
    crawledPages: data.crawledPages,
    foundResources: resources.length,
    downloaded: downloaded.length,
    skipped: skipped.length,
    skippedByReason: skipped.reduce((acc, item) => {
      const key = String((item && item.reason) || "unknown");
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {}),
    debugEntries: debugEnabled ? debugEntries.length : 0
  };
}

async function startDownloads(payload) {
  const settings = await getSettings();
  const tabId = Number(payload && payload.tabId);
  const courses = (payload && payload.courses) || [];
  const selectedByCourse = (payload && payload.selectedResourceUrlsByCourse) || {};

  if (!tabId || courses.length === 0) {
    throw new Error("No courses selected or tab unavailable.");
  }

  const history = await getHistory();
  const summaries = [];

  for (const course of courses) {
    const selectedResourceUrls = Array.isArray(selectedByCourse[course.id])
      ? selectedByCourse[course.id]
      : null;
    const summary = await processCourse(tabId, course, settings, history, selectedResourceUrls);
    summaries.push(summary);
  }

  await setHistory(history);
  return { ok: true, summaries, settings };
}

async function quickDownloadFromActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || typeof tab.id !== "number") {
    return;
  }

  const discovery = await sendToTab(tab.id, { type: "discover-courses" });
  const courses = (discovery && discovery.courses) || [];
  if (courses.length === 0) {
    const current = await sendToTab(tab.id, { type: "collect-page-resources" });
    if (current && current.ok) {
      const pseudoCourse = {
        id: current.data.courseId || "current",
        name: current.data.courseTitle || "Current Page",
        url: current.data.pageUrl
      };
      await startDownloads({ tabId: tab.id, courses: [pseudoCourse] });
    }
    return;
  }

  await startDownloads({ tabId: tab.id, courses: [courses[0]] });
}

chrome.commands.onCommand.addListener(async (command) => {
  if (command === "quick-download-current") {
    try {
      await quickDownloadFromActiveTab();
    } catch (_err) {
      // Silent for shortcut path
    }
  }
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg || !msg.type) {
    return false;
  }

  if (msg.type === "get-settings") {
    getSettings()
      .then((settings) => sendResponse({ ok: true, settings }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }

  if (msg.type === "save-settings") {
    saveSettings(msg.settings)
      .then((settings) => sendResponse({ ok: true, settings }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }

  if (msg.type === "download-courses") {
    startDownloads(msg.payload)
      .then((result) => sendResponse({ ok: true, result }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }

  return false;
});
