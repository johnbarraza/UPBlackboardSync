(function () {
  const FILE_EXT_RE = /\.(pdf|docx?|pptx?|xlsx?|zip|rar|txt|csv|rtf|odt|ods|odp|png|jpe?g|gif|svg|webp|mp4|mov|avi|mkv|webm|wmv|flv|m4v)$/i;
  const BLACKBOARD_FILE_ROUTE_RE = /\/ultra\/courses\/[^/]+\/outline\/file\/[^/?#]+/i;
  const MOJIBAKE_RE = /(?:\u00C3|\u00C2|\u00E2|\uFFFD)/;
  const ERROR_PAGE_HINTS = [
    "request[/announcement]",
    "does not contain handler parameter named 'method'",
    "whitespace in the label text",
    "for reference, the error id is",
    "whitelabel error page",
    "oops! something went wrong",
    "an error has occurred"
  ];
  const STATIC_ASSET_HOST_RE = /(^|\.)blackboardcdn\.com$/i;
  const COURSE_CONTENT_ANALYTICS_RE = /content\.item\.course\.outline\.coursecontent\.link/i;

  function mojibakeScore(value) {
    return (String(value || "").match(/[\u00C2\u00C3\u00E2\uFFFD]/g) || []).length;
  }

  function decodeLatin1AsUtf8(value) {
    const bytes = new Uint8Array(Array.from(String(value || ""), (ch) => ch.charCodeAt(0) & 0xff));
    return new TextDecoder("utf-8", { fatal: false }).decode(bytes);
  }

  function fixMojibake(input) {
    const raw = String(input || "");
    if (!MOJIBAKE_RE.test(raw)) {
      return raw;
    }

    let best = raw;
    let bestScore = mojibakeScore(raw);
    let current = raw;

    // Some Blackboard strings come double-encoded (e.g. "PerÃƒÂº").
    // Run a few decoding passes and keep the least-garbled candidate.
    for (let i = 0; i < 3; i += 1) {
      try {
        const decoded = decodeLatin1AsUtf8(current);
        if (!decoded || decoded === current) {
          break;
        }
        const score = mojibakeScore(decoded);
        if (score < bestScore) {
          best = decoded;
          bestScore = score;
        }
        current = decoded;
      } catch (_err) {
        break;
      }
    }

    return bestScore < mojibakeScore(raw) ? best : raw;
  }

  function sanitizeName(input) {
    return fixMojibake(String(input || ""))
      .normalize("NFC")
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

  function normalizeUrl(url) {
    try {
      return new URL(url, location.href).toString();
    } catch (_err) {
      return "";
    }
  }

  function normalizeResourceUrl(rawUrl, baseUrl) {
    try {
      const u = new URL(rawUrl, baseUrl || location.href);
      const path = u.pathname.toLowerCase();
      if (path.includes("/bbcswebdav/")) {
        u.searchParams.set("xythos-download", "true");
        u.searchParams.delete("render");
        u.searchParams.delete("isInlineRender");
      }
      return u.toString();
    } catch (_err) {
      return "";
    }
  }

  function parseCourseId(url) {
    if (!url) {
      return "";
    }
    const raw = String(url).trim();
    const fromCourseIdAttr = raw.match(/course-id-(_\d+_1)/i);
    if (fromCourseIdAttr && fromCourseIdAttr[1]) {
      return fromCourseIdAttr[1];
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
    return "";
  }

  const PAST_KEYWORDS_RE = /\b(past|pasado|previous|closed|inactive|ended|completed|archive|archived|finalizado|cerrado)\b/i;
  const ACTIVE_KEYWORDS_RE = /\b(active|current|ongoing|actual|en curso|vigente|open|abierto)\b/i;
  const TERM_HINT_RE = /\b(19\d{2}|20\d{2}|semester|semestre|term|ciclo|periodo|period|quarter|trimestre|spring|summer|fall|autumn|winter|primavera|verano|otono|invierno)\b/i;

  function normalizeText(input) {
    return String(input || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function cleanTermLabel(value) {
    return String(value || "")
      .replace(/^[\s\-:|,;]+/, "")
      .replace(/[\s\-:|,;]+$/, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function extractYearToken(value) {
    const normalized = normalizeText(value).toUpperCase();
    let match = normalized.match(/\b(19\d{2}|20\d{2})\b/);
    if (!match) {
      // Accept packed formats such as PRE2026_IPER...
      match = normalized.match(/(?:^|[^0-9])(19\d{2}|20\d{2})(?:[^0-9]|$)/);
    }
    return match && match[1] ? match[1] : "";
  }

  function rankedTerm(term) {
    const raw = cleanTermLabel(term);
    if (!raw || /^no term$/i.test(raw)) {
      return null;
    }

    const normalized = normalizeText(raw).toUpperCase();
    const yearToken = extractYearToken(normalized);
    if (!yearToken) {
      return null;
    }

    const year = Number(yearToken);
    const full = ` ${normalized} `;
    let period = 0;

    const semesterMatch = full.match(/\b(SEMESTER|SEMESTRE|TERM|TRIMESTRE|QUARTER|Q|CICLO)\s*([1-6])\b/);
    if (semesterMatch) {
      period = Number(semesterMatch[2]);
    } else {
      const romanMatch = full.match(/\b(IV|III|II|I)\b/);
      if (romanMatch) {
        period = { I: 1, II: 2, III: 3, IV: 4 }[romanMatch[1]] || 0;
      } else if (/\b(FALL|AUTUMN|OTONO)\b/.test(full)) {
        period = 3;
      } else if (/\b(SUMMER|VERANO)\b/.test(full)) {
        period = 2;
      } else if (/\b(SPRING|PRIMAVERA)\b/.test(full)) {
        period = 1;
      } else if (/\b(WINTER|INVIERNO)\b/.test(full)) {
        period = 0;
      } else {
        const yearIndex = normalized.indexOf(yearToken);
        const afterYear = yearIndex >= 0 ? normalized.slice(yearIndex + 4) : "";
        const numberMatch = afterYear.match(/[\/\-_ ](0?[1-9]|1[0-2])(?:\b|[\/\-_ ])/);
        if (numberMatch) {
          period = Number(numberMatch[1]);
        }
      }
    }

    return {
      score: year * 100 + period,
      token: `rank:${year * 100 + period}`
    };
  }

  function parseTermFromText(text) {
    const clean = String(text || "").replace(/\s+/g, " ").trim();
    if (!clean) {
      return "No term";
    }

    const candidates = [];
    for (const match of clean.matchAll(/\(([^)]+)\)/g)) {
      if (match[1]) {
        candidates.push(match[1]);
      }
    }

    const patterns = [
      /((?:19|20)\d{2}\s*[-/_ ]\s*(?:0?[1-9]|1[0-2]|I{1,3}|IV|V|A|B|C|D|SPRING|SUMMER|FALL|AUTUMN|WINTER|PRIMAVERA|VERANO|OTONO|INVIERNO))/ig,
      /((?:SEMESTER|SEMESTRE|TERM|CICLO|PERIODO|QUARTER|TRIMESTRE)\s*[A-Z0-9IVX]+)/ig,
      /((?:19|20)\d{2}\s*(?:SPRING|SUMMER|FALL|AUTUMN|WINTER|PRIMAVERA|VERANO|OTONO|INVIERNO))/ig,
      /((?:PRE|POST|CICLO|TERM|SEMESTRE)?\s*(?:19|20)\d{2}(?:[_\- ](?:0?[1-9]|1[0-2]|I{1,3}|IV|V|PRE|POST))?)/ig
    ];
    for (const pattern of patterns) {
      for (const match of clean.matchAll(pattern)) {
        if (match[1]) {
          candidates.push(match[1]);
        }
      }
    }

    for (const candidate of candidates) {
      if (!TERM_HINT_RE.test(candidate)) {
        continue;
      }
      const label = cleanTermLabel(candidate);
      if (!label) {
        continue;
      }
      return label;
    }

    const yearToken = extractYearToken(clean);
    if (yearToken) {
      return yearToken;
    }

    return "No term";
  }

  function inferStatus(term, courseName) {
    const lower = normalizeText(`${term} ${courseName}`).toLowerCase();
    if (PAST_KEYWORDS_RE.test(lower)) {
      return { status: "past", source: "keyword-past" };
    }
    if (ACTIVE_KEYWORDS_RE.test(lower)) {
      return { status: "active", source: "keyword-active" };
    }

    const rank = rankedTerm(term);
    if (rank) {
      const year = Math.floor(rank.score / 100);
      if (year < new Date().getFullYear()) {
        return { status: "past", source: "year" };
      }
    }

    return { status: "active", source: "default" };
  }

  function cleanCourseName(raw) {
    let value = String(raw || "").replace(/\s+/g, " ").trim();
    const nameCodeTerm = value.match(/^(.+?)\s*-\s*\d{4,}\s*-\s*[A-Za-z0-9]+\s*(?:\(|$)/);
    if (nameCodeTerm && nameCodeTerm[1]) {
      value = nameCodeTerm[1].trim();
    }
    const sectionName = value.match(/^(.+?)\s*-\s*SECCION\b/i);
    if (sectionName && sectionName[1]) {
      value = sectionName[1].trim();
    }
    value = sanitizeName(value);
    value = value.replace(/^Skip to course information\s*/i, "").trim();
    value = value.replace(/^Skip to main content\s*/i, "").trim();
    value = value.replace(/\s*\|\s*(active|past)\s*$/i, "").trim();
    if (value.includes("|")) {
      const parts = value
        .split("|")
        .map((p) => p.trim())
        .filter(Boolean);
      const good = parts.find(
        (p) => !/^(active|past)$/i.test(p) && !/^_\d+_1$/i.test(p)
      );
      if (good) {
        value = good;
      }
    }
    if (/^Skip to /i.test(value)) {
      return "";
    }
    if (/^_\d+_1$/i.test(value)) {
      return "";
    }
    if (/^(item|course|untitled|archivo|file)$/i.test(value)) {
      return "";
    }
    return value;
  }

  function isWeakCourseName(name, courseId) {
    const n = String(name || "").trim();
    if (!n) {
      return true;
    }
    if (n === courseId) {
      return true;
    }
    if (/^skip to /i.test(n)) {
      return true;
    }
    if (/^_\d+_1$/i.test(n)) {
      return true;
    }
    if (/^(item|course|untitled|archivo|file)$/i.test(n)) {
      return true;
    }
    if (n.length < 3) {
      return true;
    }
    return false;
  }

  function hasStrongCourseSignal(text) {
    const value = normalizeText(text).toUpperCase();
    return (
      /\b\d{4,}\s*-\s*[A-Za-z0-9]+\s*\((?:19|20)\d{2}/.test(value) ||
      /\((?:19|20)\d{2}\s*[-_/ ]/.test(value) ||
      /-\s*SECCION\b/.test(value)
    );
  }

  function inferTermFromNode(node, courseName) {
    const card = node.closest(
      "[data-course-id],[data-courseid],[class*='course-card'],[class*='courseCard'],li,article,div"
    );

    const sources = [
      courseName,
      node.getAttribute("data-term"),
      node.getAttribute("data-term-name"),
      node.getAttribute("data-period"),
      node.getAttribute("data-semester"),
      node.getAttribute("aria-label"),
      node.getAttribute("title"),
      card && card.getAttribute("data-term"),
      card && card.getAttribute("data-term-name"),
      card && card.getAttribute("data-period"),
      card && card.getAttribute("data-semester"),
      card && card.getAttribute("aria-label"),
      card && card.getAttribute("title"),
      card && card.textContent,
      node.textContent
    ];

    for (const source of sources) {
      const term = parseTermFromText(source || "");
      if (term !== "No term") {
        return term;
      }
    }
    return "No term";
  }

  function inferCourseNameFromNode(node, url) {
    const courseId = parseCourseId(url);
    const card = node.closest(
      "[data-course-id],[data-courseid],[class*='course-card'],[class*='courseCard'],li,article,div"
    );
    const titleNode =
      node.querySelector("[data-qa='course-title']") ||
      node.querySelector("[data-testid*='course-title']") ||
      node.querySelector("h1,h2,h3,h4");

    const cardTitleNode = card
      ? card.querySelector(
        "[data-qa='course-title'],[data-testid*='course-title'],h1,h2,h3,h4,[class*='course-title'],[class*='courseTitle']"
      )
      : null;

    const candidates = [
      node.getAttribute("data-course-title") ||
      node.getAttribute("title") ||
      node.getAttribute("aria-label") ||
      (titleNode && titleNode.textContent) ||
      "",
      card && card.getAttribute("title"),
      card && card.getAttribute("aria-label"),
      cardTitleNode && cardTitleNode.textContent,
      node.textContent,
      card && card.textContent,
      document.title
    ];

    for (const candidate of candidates) {
      const name = cleanCourseName(candidate);
      if (!isWeakCourseName(name, courseId)) {
        return name;
      }
    }

    return courseId;
  }

  function getCurrentCourseTitle(courseId) {
    let courseCodeLabel = "";
    const courseIdNode = document.getElementById(`course-id-${courseId}`);
    if (courseIdNode && courseIdNode.textContent) {
      const displayIdName = cleanCourseName(courseIdNode.textContent);
      if (!isWeakCourseName(displayIdName, courseId)) {
        courseCodeLabel = displayIdName;
      }
    }

    const courseHeader = document.querySelector("div[class*='courseTitle']");
    if (courseHeader) {
      const spanCandidates = Array.from(courseHeader.querySelectorAll("span"));
      for (const span of spanCandidates) {
        const cls = span.getAttribute("class") || "";
        if (/courseId/i.test(cls)) {
          continue;
        }
        const name = cleanCourseName(span.textContent || "");
        if (name && !isWeakCourseName(name, courseId)) {
          return name;
        }
      }
      const headerText = cleanCourseName(courseHeader.textContent || "");
      if (headerText && !isWeakCourseName(headerText, courseId)) {
        return headerText;
      }
    }

    const selectors = [
      "course-banner h1",
      "course-banner [class*='courseTitle']",
      "[class*='titleContainer'] h1",
      "h1[class*='courseTitle']",
      "div[class*='courseTitle']",
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
      if (name && !isWeakCourseName(name, courseId)) {
        return name;
      }
    }

    const title = cleanCourseName(document.title);
    if (title && !isWeakCourseName(title, courseId)) {
      return title;
    }

    if (courseCodeLabel) {
      return courseCodeLabel;
    }

    return courseId;
  }

  function reconcileCourseStatuses(coursesList) {
    const enriched = coursesList.map((course) => {
      const rank = rankedTerm(course.term);
      return {
        ...course,
        termRank: rank ? rank.score : null,
        termToken: rank ? rank.token : null
      };
    });

    let currentScore = null;
    for (const course of enriched) {
      if (typeof course.termRank !== "number") {
        continue;
      }
      if (course.status === "active" && (currentScore === null || course.termRank > currentScore)) {
        currentScore = course.termRank;
      }
    }
    if (currentScore === null) {
      for (const course of enriched) {
        if (typeof course.termRank !== "number") {
          continue;
        }
        if (currentScore === null || course.termRank > currentScore) {
          currentScore = course.termRank;
        }
      }
    }

    for (const course of enriched) {
      if (course.statusSource === "keyword-past") {
        course.status = "past";
        continue;
      }
      if (typeof course.termRank === "number" && currentScore !== null) {
        course.status = course.termRank < currentScore ? "past" : "active";
      } else if (!course.status) {
        course.status = "active";
      }
    }

    return enriched.map((course) => ({
      id: course.id,
      name: course.name,
      url: course.url,
      term: course.term,
      status: course.status,
      termRank: course.termRank
    }));
  }

  function discoverCoursesFromDom() {
    const currentId = parseCourseId(location.href);
    if (currentId) {
      const currentName = getCurrentCourseTitle(currentId);
      const currentTerm = parseTermFromText(
        `${currentName} ${(document.body && document.body.textContent) || ""}`
      );
      const currentStatusInfo = inferStatus(currentTerm, currentName);
      const currentCourse = {
        id: currentId,
        name: currentName,
        url: location.href,
        term: currentTerm,
        status: currentStatusInfo.status,
        statusSource: currentStatusInfo.source,
        nameStrength: true
      };
      return reconcileCourseStatuses([currentCourse]);
    }

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
      const term = inferTermFromNode(node, name);
      const statusInfo = inferStatus(term, name);
      const signalText = `${node.textContent || ""} ${node.getAttribute("aria-label") || ""}`;
      const nameStrength = hasStrongCourseSignal(signalText) || hasStrongCourseSignal(name);

      if (!found.has(courseId)) {
        found.set(courseId, {
          id: courseId,
          name,
          url: fallbackUrl,
          term,
          status: statusInfo.status,
          statusSource: statusInfo.source,
          nameStrength
        });
        continue;
      }

      const current = found.get(courseId);
      if (current && isWeakCourseName(current.name, courseId)) {
        if (!isWeakCourseName(name, courseId)) {
          current.name = name;
          current.nameStrength = nameStrength;
        }
      } else if (current && !current.nameStrength && nameStrength && !isWeakCourseName(name, courseId)) {
        current.name = name;
        current.nameStrength = true;
      }
      if (current && (current.term === "No term")) {
        const betterTerm = inferTermFromNode(node, name);
        if (betterTerm !== "No term") {
          current.term = betterTerm;
        }
      }
      if (current && current.status === "active") {
        const currentStatusInfo = inferStatus(current.term, current.name);
        current.status = currentStatusInfo.status;
        current.statusSource = currentStatusInfo.source;
      }
      if (current && current.name === courseId && name !== courseId) {
        current.name = name;
      }
      if (current && (!current.url || current.url === location.href)) {
        current.url = fallbackUrl;
      }
    }

    return reconcileCourseStatuses(Array.from(found.values()));
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
      BLACKBOARD_FILE_ROUTE_RE.test(url) ||
      FILE_EXT_RE.test(url);
  }

  function addUrlToQueue(queue, seenPages, rawUrl) {
    const normalized = normalizeUrl(rawUrl);
    if (!normalized) {
      return;
    }
    if (seenPages.has(normalized)) {
      return;
    }
    if (queue.includes(normalized)) {
      return;
    }
    queue.push(normalized);
  }

  function buildCourseSeedUrls(courseId, pageOrCourseUrl) {
    if (!courseId) {
      return [];
    }

    let origin = location.origin;
    try {
      const parsed = new URL(pageOrCourseUrl || location.href);
      origin = parsed.origin;
    } catch (_err) {
      // keep default origin
    }

    const encoded = encodeURIComponent(courseId);
    return [
      `${origin}/ultra/courses/${encoded}/outline`,
      `${origin}/ultra/courses/${encoded}/announcements`
    ];
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
    const scope = doc.querySelector(".js-content-outline, .course-outline-content-list") || doc;
    return [
      ...Array.from(scope.querySelectorAll("a[href]")),
      ...Array.from(scope.querySelectorAll("button[data-analytics-id*='course.content.navigation.item.content-link']")),
      ...Array.from(scope.querySelectorAll("iframe[src]")),
      ...Array.from(scope.querySelectorAll("img[src]")),
      ...Array.from(scope.querySelectorAll("source[src]")),
      ...Array.from(scope.querySelectorAll("[aria-controls^='file-preview-']"))
    ];
  }

  function collectAnnouncementItems(doc) {
    const rows = Array.from(doc.querySelectorAll("tr.announcement-item-row"));
    const items = [];

    for (const row of rows) {
      const anchor =
        row.querySelector(".announcement-title-detail a") ||
        row.querySelector("a[id^='list-item-title-']");
      const title = sanitizeName((anchor && anchor.textContent) || "Announcement");
      if (!title) {
        continue;
      }

      const bodyNode = row.querySelector(".list-item-body");
      const body = fixMojibake((bodyNode && bodyNode.textContent) || "").trim();
      const posted = fixMojibake(
        ((row.querySelector(".list-item-date-sent") && row.querySelector(".list-item-date-sent").textContent) ||
          "")
      ).trim();
      const rowId = ((anchor && anchor.id) || row.getAttribute("id") || "").trim();
      const stableId = rowId || `${title}::${posted}`;

      const lines = [`Title: ${title}`];
      if (posted) {
        lines.push(`Posted: ${posted}`);
      }
      if (body) {
        lines.push("");
        lines.push(body);
      }

      items.push({
        id: stableId,
        title,
        posted,
        body: `${lines.join("\n").trim()}\n`
      });
    }

    return items;
  }

  function inferUltraResourceUrlFromNode(node, pageUrl, courseId) {
    const contentNode = node.closest("[data-content-id]");
    const contentId = contentNode && contentNode.getAttribute("data-content-id");
    if (!contentId || !courseId) {
      return "";
    }

    let origin = location.origin;
    try {
      origin = new URL(pageUrl || location.href).origin;
    } catch (_err) {
      // keep location origin
    }

    const iconLabel = (
      (contentNode.querySelector("svg[aria-label]") &&
        contentNode.querySelector("svg[aria-label]").getAttribute("aria-label")) ||
      ""
    ).toLowerCase();

    const encodedCourse = encodeURIComponent(courseId);
    if (iconLabel.includes("pdf") || iconLabel.includes("file") || iconLabel.includes("archivo")) {
      return `${origin}/ultra/courses/${encodedCourse}/outline/file/${encodeURIComponent(contentId)}`;
    }

    if (iconLabel.includes("text document") || iconLabel.includes("document") || iconLabel.includes("documento")) {
      return `${origin}/ultra/courses/${encodedCourse}/outline/edit/document/${encodeURIComponent(contentId)}?courseId=${encodeURIComponent(courseId)}&view=content&state=view`;
    }

    return "";
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

    return normalizeResourceUrl(raw, pageUrl);
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

  function isStaticUiAssetUrl(url) {
    try {
      const parsed = new URL(url, location.href);
      const host = parsed.hostname.toLowerCase();
      const path = parsed.pathname.toLowerCase();
      if (path.includes("default_profile_avatar.svg")) {
        return true;
      }
      if (STATIC_ASSET_HOST_RE.test(host) && /\/images\//.test(path)) {
        return true;
      }
      return false;
    } catch (_err) {
      return false;
    }
  }

  function nodeHasCourseContentSignal(node) {
    if (!node) {
      return false;
    }
    const analytics = node.getAttribute("data-analytics-id") || "";
    if (COURSE_CONTENT_ANALYTICS_RE.test(analytics)) {
      return true;
    }
    if (node.closest("[data-content-id]")) {
      return true;
    }
    if (node.closest(".js-content-outline, .course-outline-content-list")) {
      return true;
    }
    return false;
  }

  function shouldIncludeDetectedResource(node, absoluteUrl, courseId) {
    if (!absoluteUrl || isStaticUiAssetUrl(absoluteUrl)) {
      return false;
    }

    let parsed;
    try {
      parsed = new URL(absoluteUrl, location.href);
    } catch (_err) {
      return false;
    }

    // Ultra "document" routes are HTML pages, not binary materials.
    // We still follow them as pages elsewhere, but don't treat them as direct resources.
    if (/\/ultra\/courses\/[^/]+\/outline\/edit\/document\/[^/?#]+/i.test(parsed.pathname)) {
      return false;
    }

    if (nodeHasCourseContentSignal(node)) {
      return true;
    }

    const lower = absoluteUrl.toLowerCase();
    const sameHost = parsed.host === location.host;
    if (!sameHost) {
      return /drive\.google\.com|docs\.google\.com|onedrive\.live\.com|dropbox\.com/i.test(parsed.host);
    }

    if (courseId && lower.includes(String(courseId).toLowerCase())) {
      return true;
    }
    if (/bbcswebdav|xythos-download|\/outline\/file\//i.test(lower)) {
      return true;
    }
    return false;
  }

  function addUniquePathSegment(segments, seen, value) {
    const label = sanitizeName(value);
    if (!label) {
      return;
    }
    const key = label.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    segments.unshift(label);
  }

  function extractFolderPath(node, doc, pageType) {
    const segments = [];
    const seen = new Set();

    const addById = (id) => {
      if (!id) {
        return;
      }
      const titleNode = doc.getElementById(id);
      if (!titleNode) {
        return;
      }
      addUniquePathSegment(
        segments,
        seen,
        titleNode.textContent || titleNode.getAttribute("title") || ""
      );
    };

    let current = node;
    let depth = 0;
    while (current && depth < 20) {
      if (current.id && current.id.startsWith("folder-contents-")) {
        addById(`folder-title-${current.id.slice("folder-contents-".length)}`);
      }
      if (current.id && current.id.startsWith("learning-module-contents-")) {
        addById(`learning-module-title-${current.id.slice("learning-module-contents-".length)}`);
      }

      const labelledBy = current.getAttribute("aria-labelledby") || "";
      for (const id of labelledBy.split(/\s+/).filter(Boolean)) {
        if (id.startsWith("folder-title-") || id.startsWith("learning-module-title-")) {
          addById(id);
        }
      }

      const controls = current.getAttribute("aria-controls") || "";
      if (controls.startsWith("folder-contents-")) {
        addById(`folder-title-${controls.slice("folder-contents-".length)}`);
      }
      if (controls.startsWith("learning-module-contents-")) {
        addById(`learning-module-title-${controls.slice("learning-module-contents-".length)}`);
      }

      current = current.parentElement;
      depth += 1;
    }

    if (segments.length === 0) {
      return pageType === "modules" ? "files" : pageType;
    }

    // In modules view, keep the Blackboard folder/module names directly
    // instead of adding an artificial "modules/" prefix.
    if (pageType === "modules") {
      return segments.join("/");
    }
    return `${pageType}/${segments.join("/")}`;
  }

  function isBlackboardErrorPage(doc, html, pageUrl) {
    const title = (doc.querySelector("title") && doc.querySelector("title").textContent) || "";
    const bodyText = (doc.body && doc.body.textContent) || String(html || "");
    const sample = `${title}\n${bodyText}\n${pageUrl}`.toLowerCase();
    if (/^\s*error\b/i.test(title)) {
      return true;
    }
    if (/\berror\s*[–-]/i.test(title)) {
      return true;
    }
    return ERROR_PAGE_HINTS.some((hint) => sample.includes(hint));
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function collectCollapsedContentToggles(doc) {
    const scope = doc.querySelector(".js-content-outline, .course-outline-content-list") || doc;
    const selectors = [
      "button[id^='learning-module-title-'][aria-expanded='false']",
      "button[id^='folder-title-'][aria-expanded='false']",
      "button[data-analytics-id='course.learning.module.base.item.toggleLm.button'][aria-expanded='false']",
      "button[data-analytics-id='content.item.folder.toggleFolder.button'][aria-expanded='false']",
      "button[aria-controls^='learning-module-contents-'][aria-expanded='false']",
      "button[aria-controls^='folder-contents-'][aria-expanded='false']"
    ];
    const out = [];
    const seen = new Set();
    for (const selector of selectors) {
      for (const btn of scope.querySelectorAll(selector)) {
        if (!(btn instanceof HTMLButtonElement) || btn.disabled) {
          continue;
        }
        const key = btn.id || `${btn.getAttribute("aria-controls") || ""}::${btn.textContent || ""}`;
        if (seen.has(key)) {
          continue;
        }
        seen.add(key);
        out.push(btn);
      }
    }
    return out;
  }

  async function expandAllCourseContent(doc) {
    // Blackboard Ultra lazily renders children only after expand.
    for (let round = 0; round < 6; round += 1) {
      const collapsed = collectCollapsedContentToggles(doc);
      if (collapsed.length === 0) {
        return;
      }
      for (const button of collapsed) {
        try {
          button.click();
        } catch (_err) {
          // ignore UI interaction issues
        }
        await sleep(90);
      }
      await sleep(280);
    }
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
    gradeRows,
    seenAnnouncementItems
  ) {
    const isErrorPage = isBlackboardErrorPage(doc, html, pageUrl);
    const pageTitle = sanitizeName(
      (doc.querySelector("title") && doc.querySelector("title").textContent) ||
      pageUrl
    );
    const pageType = classifyPage(pageUrl);

    if (!isErrorPage && settings.contentTypes.text && settings.contentTypes[pageType] !== false) {
      textFiles.push({
        path: `${pageType}/${pageTitle}.html`,
        body: html
      });
    }

    if (settings.contentTypes.gradesCsv) {
      gradeRows.push(...collectGradeRows(doc));
    }

    for (const node of collectLinksFromPage(doc)) {
      const absolute =
        extractResourceUrl(node, pageUrl) ||
        inferUltraResourceUrlFromNode(node, pageUrl, course.id);
      if (!absolute) {
        continue;
      }
      if (!shouldIncludeDetectedResource(node, absolute, course.id)) {
        continue;
      }

      const label = extractResourceLabel(node, absolute);

      if (isLikelyDownloadable(absolute)) {
        const key = `${absolute}::${label}`;
        if (!seenResources.has(key)) {
          const folderPath = extractFolderPath(node, doc, pageType);
          resources.push({
            url: absolute,
            title: label,
            folder: folderPath,
            sourcePage: pageUrl
          });
          seenResources.add(key);
        }
      }

      if (shouldFollowLink(absolute, course.id)) {
        addUrlToQueue(queue, seenPages, absolute);
      }
    }

    const hasAnnouncementSignal = !isErrorPage && (
      pageType === "announcements" ||
      !!doc.querySelector("span[data-title='Announcements']") ||
      !!doc.querySelector("caption#announcement-table-caption") ||
      !!doc.querySelector("table.table-content.sortable-table")
    );

    if (hasAnnouncementSignal) {
      if (settings.contentTypes.text && settings.contentTypes.announcements !== false) {
        const items = collectAnnouncementItems(doc);
        for (const item of items) {
          const dedupeKey = `${course.id}::${item.id}`;
          if (seenAnnouncementItems.has(dedupeKey)) {
            continue;
          }
          seenAnnouncementItems.add(dedupeKey);
          const postedPrefix = item.posted ? `${sanitizeName(item.posted)} - ` : "";
          textFiles.push({
            path: `announcements/${postedPrefix}${item.title}.txt`,
            body: item.body
          });
        }
      }
      for (const seed of buildCourseSeedUrls(course.id, pageUrl)) {
        addUrlToQueue(queue, seenPages, seed);
      }
    }
  }

  async function crawlCourse(course, settings) {
    const maxPages = Number(settings.maxPagesPerCourse || 60);
    const queue = [];
    const seenPages = new Set();
    const seenResources = new Set();
    const seenAnnouncementItems = new Set();
    const resources = [];
    const textFiles = [];
    const gradeRows = [];

    addUrlToQueue(queue, seenPages, toAbsolute(course.url, location.href));
    for (const seed of buildCourseSeedUrls(course.id, course.url || location.href)) {
      addUrlToQueue(queue, seenPages, seed);
    }

    const currentCourseId = parseCourseId(location.href);
    if (currentCourseId && currentCourseId === course.id) {
      await expandAllCourseContent(document);
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
        gradeRows,
        seenAnnouncementItems
      );

      for (const seed of buildCourseSeedUrls(course.id, liveUrl)) {
        addUrlToQueue(queue, seenPages, seed);
      }
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
        gradeRows,
        seenAnnouncementItems
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
    for (const node of document.querySelectorAll("a[href],button[data-analytics-id*='course.content.navigation.item.content-link'],iframe[src],img[src],source[src]")) {
      const raw = node.getAttribute("href") || node.getAttribute("src");
      const absolute =
        toAbsolute(raw, location.href) ||
        inferUltraResourceUrlFromNode(node, location.href, parseCourseId(location.href));
      if (!absolute || seen.has(absolute)) {
        continue;
      }
      if (!shouldIncludeDetectedResource(node, absolute, parseCourseId(location.href))) {
        continue;
      }
      if (!isLikelyDownloadable(absolute)) {
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
        folder: extractFolderPath(node, document, classifyPage(location.href)),
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
