(function () {
  function textOrFallback(value, fallback) {
    if (!value) {
      return fallback;
    }
    const clean = String(value).trim();
    return clean || fallback;
  }

  function sanitizeName(input) {
    return String(input || "")
      .replace(/[<>:"/\\|?*\u0000-\u001F]/g, "_")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, 180) || "resource";
  }

  function filenameFromUrl(rawUrl) {
    try {
      const url = new URL(rawUrl, location.href);
      const qp = new URLSearchParams(url.search);
      const fromQuery = qp.get("filename") || qp.get("file") || qp.get("name");
      if (fromQuery) {
        return sanitizeName(fromQuery);
      }
      const lastSegment = decodeURIComponent(url.pathname.split("/").filter(Boolean).pop() || "");
      if (lastSegment && !lastSegment.toLowerCase().startsWith("xid-")) {
        return sanitizeName(lastSegment);
      }
    } catch (_err) {
      // ignore parsing errors and fallback.
    }
    return "resource";
  }

  function detectCourseTitle() {
    const titleCandidate = document.querySelector("h1, [data-analytics-id*='course'], .course-title");
    const pageTitle = document.title || "Blackboard Course";
    return sanitizeName(textOrFallback(titleCandidate && titleCandidate.textContent, pageTitle));
  }

  function collectResourceLinks() {
    const seen = new Set();
    const links = [];
    const selectors = ["a[href]", "iframe[src]"];

    selectors.forEach((selector) => {
      document.querySelectorAll(selector).forEach((node) => {
        const raw = node.getAttribute("href") || node.getAttribute("src");
        if (!raw) {
          return;
        }

        const absolute = new URL(raw, location.href).toString();
        if (seen.has(absolute)) {
          return;
        }

        const isLikelyFile =
          /bbcswebdav|xythos-download|render=inline|download/i.test(absolute) ||
          /\.(pdf|docx?|pptx?|xlsx?|zip|rar|txt|csv)$/i.test(absolute);

        const isLikelyExternal = selector === "a[href]" && /^https?:\/\//i.test(absolute);

        if (!isLikelyFile && !isLikelyExternal) {
          return;
        }

        const title =
          node.getAttribute("title") ||
          node.getAttribute("aria-label") ||
          node.textContent ||
          filenameFromUrl(absolute);

        links.push({
          url: absolute,
          title: sanitizeName(textOrFallback(title, filenameFromUrl(absolute)))
        });
        seen.add(absolute);
      });
    });

    return {
      pageUrl: location.href,
      courseTitle: detectCourseTitle(),
      links
    };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg && msg.type === "collect-links") {
      sendResponse({ ok: true, data: collectResourceLinks() });
      return true;
    }
    return false;
  });
})();
