(function () {
  const FILE_EXT_RE = /\.(pdf|docx?|pptx?|xlsx?|zip|rar|txt|csv|rtf|odt|ods|odp|png|jpe?g|gif|svg|webp|mp4|mov|avi|mkv|webm|wmv|flv|m4v)$/i;

  function sanitizeName(input) {
    return String(input || "")
      .replace(/[<>:"/\\|?*\u0000-\u001F]/g, "_")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, 180) || "item";
  }

  function toAbsolute(url, baseUrl) {
    try {
      return new URL(url, baseUrl || location.href).toString();
    } catch (_err) {
      return "";
    }
  }

  function parseCourseId(url) {
    if (!url) {
      return "";
    }
    const ultra = url.match(/\/courses\/([^/?#]+)/i);
    if (ultra && ultra[1]) {
      return decodeURIComponent(ultra[1]);
    }
    const query = url.match(/[?&]course_id=([^&#]+)/i);
    if (query && query[1]) {
      return decodeURIComponent(query[1]);
    }
    const queryAlt = url.match(/[?&]courseId=([^&#]+)/i);
    if (queryAlt && queryAlt[1]) {
      return decodeURIComponent(queryAlt[1]);
    }
    const idPattern = String(url).match(/(_\d+_1)/);
    if (idPattern && idPattern[1]) {
      return idPattern[1];
    }
    return "";
  }

  function parseTermFromText(text) {
    const clean = String(text || "");
    const m = clean.match(/\(([^)]+)\)\s*$/);
    if (m && m[1]) {
      return m[1].trim();
    }
    return "No term";
  }

  function inferStatus(term, courseName) {
    const lower = `${term} ${courseName}`.toLowerCase();
    if (lower.includes("past") || lower.includes("pasado") || lower.includes("previous")) {
      return "past";
    }
    const y = lower.match(/(20\d{2})/);
    if (y && Number(y[1]) < new Date().getFullYear()) {
      return "past";
    }
    return "active";
  }

  function cleanCourseName(raw) {
    let value = sanitizeName(String(raw || "").replace(/\s+/g, " "));
    value = value.replace(/^Skip to main content\s*/i, "").trim();
    value = value.replace(/\s*\|\s*(active|past)\s*$/i, "").trim();
    if (/^_\d+_1$/i.test(value)) {
      return "";
    }
    return value;
  }

  function inferCourseNameFromNode(node, url) {
    const titleNode =
      node.querySelector("[data-qa='course-title']") ||
      node.querySelector("[data-testid*='course-title']") ||
      node.querySelector("h1,h2,h3,h4");

    const title =
      node.getAttribute("data-course-title") ||
      node.getAttribute("title") ||
      node.getAttribute("aria-label") ||
      (titleNode && titleNode.textContent) ||
      node.textContent ||
      document.title ||
      parseCourseId(url);

    return cleanCourseName(title) || parseCourseId(url);
  }

  function getCurrentCourseTitle(courseId) {
    const selectors = [
      "[data-qa='course-title']",
      "[data-testid*='course-title']",
      "main h1",
      "header h1",
      "h1",
      ".course-title",
      "[class*='courseTitle']"
    ];

    for (const sel of selectors) {
      const node = document.querySelector(sel);
      if (!node || !node.textContent) {
        continue;
      }
      const name = cleanCourseName(node.textContent);
      if (name && name !== courseId) {
        return name;
      }
    }

    const title = cleanCourseName(document.title);
    if (title && title !== courseId) {
      return title;
    }

    return courseId;
  }

  function discoverCoursesFromDom() {
    const found = new Map();
    const candidates = [
      ...Array.from(document.querySelectorAll("a[href]")),
      ...Array.from(
        document.querySelectorAll(
          "[data-course-id],[data-courseid],[course-id]"
        )
      )
    ];

    for (const node of candidates) {
      const href =
        node.getAttribute("href") ||
        (node.closest("a[href]") && node.closest("a[href]").getAttribute("href"));
      const url = toAbsolute(href, location.href);

      let courseId = parseCourseId(url);
      if (!courseId) {
        const attrs = [
          node.getAttribute("data-course-id"),
          node.getAttribute("data-courseid"),
          node.getAttribute("course-id"),
          node.getAttribute("id"),
          node.getAttribute("aria-controls"),
          node.getAttribute("aria-label")
        ];
        for (const value of attrs) {
          const id = parseCourseId(value || "");
          if (id) {
            courseId = id;
            break;
          }
        }
      }

      if (!courseId) {
        continue;
      }

      const fallbackUrl =
        url || `${location.origin}/ultra/courses/${encodeURIComponent(courseId)}/outline`;
      const name = inferCourseNameFromNode(node, fallbackUrl);
      const term = parseTermFromText(name);
      const status = inferStatus(term, name);

      if (!found.has(courseId)) {
        found.set(courseId, {
          id: courseId,
          name,
          url: fallbackUrl,
          term,
          status
        });
        continue;
      }

      const current = found.get(courseId);
      if (current && current.name === courseId && name !== courseId) {
        current.name = name;
      }
      if (current && (!current.url || current.url === location.href)) {
        current.url = fallbackUrl;
      }
    }

    const currentId = parseCourseId(location.href);
    if (currentId && !found.has(currentId)) {
      const currentName = getCurrentCourseTitle(currentId);
      found.set(currentId, {
        id: currentId,
        name: currentName,
        url: location.href,
        term: parseTermFromText(currentName),
        status: inferStatus(parseTermFromText(currentName), currentName)
      });
    }

    return Array.from(found.values());
  }

  function filenameFromUrl(rawUrl) {
    try {
      const url = new URL(rawUrl, location.href);
      const qp = new URLSearchParams(url.search);
      const fromQuery = qp.get("filename") || qp.get("file") || qp.get("name");
      if (fromQuery) {
        return sanitizeName(fromQuery);
      }
      const last = decodeURIComponent(url.pathname.split("/").filter(Boolean).pop() || "");
      if (last && !last.toLowerCase().startsWith("xid-")) {
        return sanitizeName(last);
      }
    } catch (_err) {
      // ignored
    }
    return "resource";
  }

  function classifyPage(url) {
    const lower = String(url || "").toLowerCase();
    if (lower.includes("discussion")) {
      return "discussions";
    }
    if (lower.includes("announcement")) {
      return "announcements";
    }
    if (lower.includes("assignment") || lower.includes("assess")) {
      return "assignments";
    }
    if (lower.includes("module") || lower.includes("outline")) {
      return "modules";
    }
    if (lower.includes("syllabus")) {
      return "syllabus";
    }
    return "pages";
  }

  function shouldFollowLink(url, courseId) {
    if (!url || !/^https?:\/\//i.test(url)) {
      return false;
    }
    if (url.startsWith("javascript:") || url.startsWith("mailto:")) {
      return false;
    }
    if (!url.includes(location.host)) {
      return false;
    }
    if (FILE_EXT_RE.test(url)) {
      return false;
    }
    const idFromUrl = parseCourseId(url);
    if (!idFromUrl) {
      return false;
    }
    return idFromUrl === courseId;
  }

  function isLikelyDownloadable(url) {
    if (!url) {
      return false;
    }
    return /bbcswebdav|xythos-download|render=inline|download/i.test(url) ||
      FILE_EXT_RE.test(url);
  }

  function collectGradeRows(doc) {
    const rows = [];
    const tables = Array.from(doc.querySelectorAll("table"));
    for (const table of tables) {
      const headers = Array.from(table.querySelectorAll("thead th, tr th"))
        .map((h) => h.textContent.trim().toLowerCase());
      const gradeLike = headers.some((h) =>
        ["assignment", "due", "points", "score", "grade"].some((w) => h.includes(w))
      );
      if (!gradeLike) {
        continue;
      }
      const bodyRows = Array.from(table.querySelectorAll("tbody tr"));
      for (const row of bodyRows) {
        const cells = Array.from(row.querySelectorAll("td")).map((c) => c.textContent.trim());
        if (cells.length >= 2) {
          rows.push(cells.slice(0, 6));
        }
      }
    }
    return rows;
  }

  async function fetchText(url) {
    const response = await fetch(url, {
      credentials: "include",
      redirect: "follow"
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} for ${url}`);
    }
    return response.text();
  }

  function collectLinksFromPage(doc) {
    return [
      ...Array.from(doc.querySelectorAll("a[href]")),
      ...Array.from(doc.querySelectorAll("iframe[src]")),
      ...Array.from(doc.querySelectorAll("img[src]")),
      ...Array.from(doc.querySelectorAll("source[src]")),
      ...Array.from(doc.querySelectorAll("[aria-controls^='file-preview-']"))
    ];
  }

  function extractResourceUrl(node, pageUrl) {
    let raw =
      node.getAttribute("href") ||
      node.getAttribute("src") ||
      node.getAttribute("data-href") ||
      node.getAttribute("data-resource-url");

    if (!raw) {
      const controls = node.getAttribute("aria-controls") || "";
      if (controls.startsWith("file-preview-")) {
        raw = controls.slice("file-preview-".length);
      }
    }

    return toAbsolute(raw, pageUrl);
  }

  function extractResourceLabel(node, absoluteUrl) {
    const aria = node.getAttribute("aria-label") || "";
    const ariaMatch = aria.match(/(?:File|Archivo)\s+(.+)$/i);
    const label = sanitizeName(
      node.getAttribute("title") ||
      (ariaMatch && ariaMatch[1]) ||
      aria ||
      node.textContent ||
      filenameFromUrl(absoluteUrl)
    );
    return label || filenameFromUrl(absoluteUrl);
  }

  function parsePageContent(
    doc,
    pageUrl,
    html,
    course,
    settings,
    queue,
    seenPages,
    seenResources,
    resources,
    textFiles,
    gradeRows
  ) {
    const pageTitle = sanitizeName(
      (doc.querySelector("title") && doc.querySelector("title").textContent) ||
      pageUrl
    );
    const pageType = classifyPage(pageUrl);

    if (settings.contentTypes.text && settings.contentTypes[pageType] !== false) {
      textFiles.push({
        path: `${pageType}/${pageTitle}.html`,
        body: html
      });
    }

    if (settings.contentTypes.gradesCsv) {
      gradeRows.push(...collectGradeRows(doc));
    }

    for (const node of collectLinksFromPage(doc)) {
      const absolute = extractResourceUrl(node, pageUrl);
      if (!absolute) {
        continue;
      }

      const label = extractResourceLabel(node, absolute);

      if (isLikelyDownloadable(absolute) || /^https?:\/\//i.test(absolute)) {
        const key = `${absolute}::${label}`;
        if (!seenResources.has(key)) {
          resources.push({
            url: absolute,
            title: label,
            folder: pageType,
            sourcePage: pageUrl
          });
          seenResources.add(key);
        }
      }

      if (shouldFollowLink(absolute, course.id)) {
        if (!seenPages.has(absolute) && !queue.includes(absolute)) {
          queue.push(absolute);
        }
      }
    }
  }

  async function crawlCourse(course, settings) {
    const maxPages = Number(settings.maxPagesPerCourse || 60);
    const queue = [toAbsolute(course.url, location.href)];
    const seenPages = new Set();
    const seenResources = new Set();
    const resources = [];
    const textFiles = [];
    const gradeRows = [];

    const currentCourseId = parseCourseId(location.href);
    if (currentCourseId && currentCourseId === course.id) {
      const liveHtml = document.documentElement
        ? document.documentElement.outerHTML
        : document.body.innerHTML;
      const liveUrl = toAbsolute(location.href, location.href);
      seenPages.add(liveUrl);
      parsePageContent(
        document,
        liveUrl,
        liveHtml,
        course,
        settings,
        queue,
        seenPages,
        seenResources,
        resources,
        textFiles,
        gradeRows
      );
    }

    while (queue.length > 0 && seenPages.size < maxPages) {
      const pageUrl = queue.shift();
      if (!pageUrl || seenPages.has(pageUrl)) {
        continue;
      }
      seenPages.add(pageUrl);

      let html;
      try {
        html = await fetchText(pageUrl);
      } catch (_err) {
        continue;
      }

      const doc = new DOMParser().parseFromString(html, "text/html");
      parsePageContent(
        doc,
        pageUrl,
        html,
        course,
        settings,
        queue,
        seenPages,
        seenResources,
        resources,
        textFiles,
        gradeRows
      );
    }

    return {
      course,
      crawledPages: seenPages.size,
      resources,
      textFiles,
      gradeRows
    };
  }

  function collectCurrentPageResources() {
    const links = [];
    const seen = new Set();
    for (const node of document.querySelectorAll("a[href],iframe[src],img[src],source[src]")) {
      const raw = node.getAttribute("href") || node.getAttribute("src");
      const absolute = toAbsolute(raw, location.href);
      if (!absolute || seen.has(absolute)) {
        continue;
      }
      if (!isLikelyDownloadable(absolute) && !/^https?:\/\//i.test(absolute)) {
        continue;
      }
      seen.add(absolute);
      links.push({
        url: absolute,
        title: sanitizeName(
          node.getAttribute("title") ||
          node.getAttribute("aria-label") ||
          node.textContent ||
          filenameFromUrl(absolute)
        ),
        folder: classifyPage(location.href),
        sourcePage: location.href
      });
    }

    return {
      pageUrl: location.href,
      courseId: parseCourseId(location.href),
      courseTitle: sanitizeName(document.title || "Blackboard Course"),
      links
    };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (!msg || !msg.type) {
      return false;
    }

    if (msg.type === "discover-courses") {
      sendResponse({
        ok: true,
        courses: discoverCoursesFromDom(),
        currentPage: location.href,
        currentCourseId: parseCourseId(location.href)
      });
      return true;
    }

    if (msg.type === "collect-page-resources") {
      sendResponse({ ok: true, data: collectCurrentPageResources() });
      return true;
    }

    if (msg.type === "crawl-course") {
      crawlCourse(msg.course, msg.settings || {})
        .then((data) => sendResponse({ ok: true, data }))
        .catch((err) => sendResponse({ ok: false, error: String(err) }));
      return true;
    }

    return false;
  });
})();
