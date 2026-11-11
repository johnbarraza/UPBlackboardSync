"""Offline HTML dashboard of the download folder.

Regenerated after every sync as ``BlackboardSync.html`` in the download
location. Self-contained (no network), links open the local files.
"""

import re
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DASHBOARD_NAME = "BlackboardSync.html"
_SKIP_FILES = {DASHBOARD_NAME, "recent.md"}
_SPECIAL_DIRS = {"Announcements", "Roster"}
_RECENT_LIMIT = 80


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _tree(folder: Path, root: Path, files_out: list[dict]) -> dict:
    """Nested {name, dirs, files} for folder; also appends every file to files_out."""
    node: dict = {"name": folder.name, "dirs": [], "files": []}
    try:
        entries = sorted(folder.iterdir(), key=lambda e: e.name.lower())
    except OSError:
        return node
    for e in entries:
        if e.name.startswith(".") or e.name in _SKIP_FILES:
            continue
        try:
            is_dir = e.is_dir()
        except OSError:  # e.g. WinError 1920 on WSL/broken links
            continue
        if is_dir:
            if e.name in _SPECIAL_DIRS:
                continue
            node["dirs"].append(_tree(e, root, files_out))
        else:
            try:
                st = e.stat()
            except OSError:
                continue
            # mtime = posted in Blackboard (set by the writers);
            # creation time = when it was downloaded here.
            born = getattr(st, "st_birthtime", st.st_ctime)
            f = {"name": e.name, "path": e.relative_to(root).as_posix(),
                 "size": st.st_size, "mtime": _iso(st.st_mtime),
                 "downloaded": _iso(born)}
            node["files"].append(f)
            files_out.append(f)
    return node


def _announcements(folder: Path, root: Path) -> list[dict]:
    out: list[dict] = []
    if not folder.is_dir():
        return out
    for f in folder.glob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        lines = text.splitlines()
        title = lines[0].lstrip("# ").strip() if lines else f.stem
        body = text.split("\n---\n", 1)[1].strip() if "\n---\n" in text else text
        # '**Date:** 2026-11-10 15:00 UTC' written by Announcement.write
        m = re.search(r"\*\*Date:\*\* (\d{4}-\d\d-\d\d) (\d\d:\d\d) UTC", text)
        date = f"{m[1]}T{m[2]}:00+00:00" if m else f.name[:10]
        out.append({"title": title, "date": date, "body": body,
                    "path": f.relative_to(root).as_posix()})
    return out


def build_index(root: Path) -> dict:
    """Scan root/<year>/<course>/... into the data the dashboard shows."""
    courses, recent, announcements = [], [], []
    for year_dir in sorted((d for d in root.iterdir() if d.is_dir()
                            and not d.name.startswith(".")),
                           key=lambda d: d.name, reverse=True):
        for course_dir in sorted(d for d in year_dir.iterdir() if d.is_dir()):
            files: list[dict] = []
            tree = _tree(course_dir, root, files)
            anns = _announcements(course_dir / "Announcements", root)
            for f in files:
                recent.append({**f, "course": course_dir.name})
            for a in anns:
                announcements.append({**a, "course": course_dir.name})
            courses.append({
                "name": course_dir.name, "year": year_dir.name,
                "file_count": len(files),
                "size": sum(f["size"] for f in files),
                "last_modified": max((f["mtime"] for f in files), default=None),
                "announcement_count": len(anns),
                "tree": tree,
            })
    recent.sort(key=lambda f: f["mtime"], reverse=True)
    announcements.sort(key=lambda a: a["date"], reverse=True)
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "courses": courses,
        "recent": recent[:_RECENT_LIMIT],
        "announcements": announcements,
    }


def write_dashboard(root: Path) -> Path | None:
    """(Re)generate the dashboard HTML. Never raises."""
    try:
        data = json.dumps(build_index(root), ensure_ascii=False)
        data = data.replace("</", "<\\/")  # keep </script> out of the JSON blob
        out = root / DASHBOARD_NAME
        out.write_text(_TEMPLATE.replace("__DATA__", data), encoding="utf-8")
        return out
    except Exception:
        logger.warning("Could not write dashboard", exc_info=True)
        return None


_TEMPLATE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BlackboardSync</title>
<style>
:root{
  --bg:#f6f5f2;--panel:#ffffff;--ink:#1d1c1a;--muted:#6f6b64;--line:#e4e1da;
  --accent:#0f6b5c;--accent-soft:#e2f0ec;--new:#c2410c;--new-soft:#fdeee4;
  --shadow:0 1px 2px rgba(0,0,0,.04),0 4px 16px rgba(0,0,0,.04);
}
@media (prefers-color-scheme:dark){:root{
  --bg:#141413;--panel:#1d1c1a;--ink:#ecebe7;--muted:#9a968e;--line:#2e2c29;
  --accent:#4cc2a8;--accent-soft:#1b302b;--new:#fb923c;--new-soft:#33231a;
  --shadow:none;
}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.5 "Segoe UI",system-ui,-apple-system,sans-serif}
a{color:inherit;text-decoration:none}
.app{display:grid;grid-template-columns:290px minmax(0,1fr);min-height:100vh}
aside{border-right:1px solid var(--line);padding:20px 14px;position:sticky;top:0;
  height:100vh;overflow:auto;background:var(--panel)}
.brand{font-weight:700;font-size:17px;padding:0 8px 4px}
.sub{color:var(--muted);font-size:12px;padding:0 8px 14px}
input[type=search]{width:100%;padding:9px 12px;border:1px solid var(--line);
  border-radius:10px;background:var(--bg);color:var(--ink);font:inherit;margin-bottom:12px}
.nav{display:block;width:100%;text-align:left;border:0;background:none;color:inherit;
  font:inherit;padding:8px 10px;border-radius:8px;cursor:pointer;display:flex;
  justify-content:space-between;gap:8px;align-items:center}
.nav:hover{background:var(--bg)}
.nav.on{background:var(--accent-soft);color:var(--accent);font-weight:600}
.nav .n{color:var(--muted);font-size:12px;font-variant-numeric:tabular-nums;
  white-space:nowrap;flex:none}
.nav .name{min-width:0}
.year{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);
  padding:14px 10px 4px}
main{padding:28px clamp(16px,4vw,48px);max-width:1100px;width:100%}
h1{font-size:26px;margin:0 0 4px}
h2{font-size:15px;margin:28px 0 10px;color:var(--muted);font-weight:600;
  text-transform:uppercase;letter-spacing:.06em}
.stats{display:grid;gap:12px;margin:16px 0 4px;
  grid-template-columns:repeat(auto-fit,minmax(120px,1fr))}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:12px 16px;box-shadow:var(--shadow)}
.stat b{display:block;font-size:22px;font-variant-numeric:tabular-nums}
.stat span{color:var(--muted);font-size:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  box-shadow:var(--shadow);overflow:hidden}
.row{display:flex;gap:12px;align-items:center;padding:10px 14px;
  border-top:1px solid var(--line)}
.row:first-child{border-top:0}
a.row:hover{background:var(--bg)}
.ico{width:34px;height:34px;flex:none;border-radius:8px;display:grid;place-items:center;
  font-size:10px;font-weight:700;background:var(--accent-soft);color:var(--accent)}
.grow{flex:1;min-width:0}
.name{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.meta{color:var(--muted);font-size:12px}
.badge{font-size:11px;font-weight:700;padding:2px 7px;border-radius:99px;
  background:var(--new-soft);color:var(--new);flex:none}
.ann{padding:14px 16px;border-top:1px solid var(--line)}
.ann:first-child{border-top:0}
.ann summary{cursor:pointer;list-style:none;display:flex;flex-wrap:wrap;gap:4px 10px;
  align-items:baseline}
.ann summary::-webkit-details-marker{display:none}
.ann .t{font-weight:600;flex:1 1 200px}
.ann pre{white-space:pre-wrap;font:inherit;color:var(--ink);margin:10px 0 0;
  padding:12px;background:var(--bg);border-radius:8px}
.tree details{padding-left:14px}
.tree>details{padding-left:0}
.tree summary{cursor:pointer;padding:6px 8px;border-radius:6px;font-weight:600}
.tree summary:hover{background:var(--bg)}
.tree .row{border:0;padding:6px 8px 6px 22px;border-radius:6px}
.tree .ico{width:26px;height:26px;font-size:9px}
.empty{padding:18px;color:var(--muted)}
.group{margin-bottom:14px}
.ghead{display:flex;justify-content:space-between;align-items:baseline;width:100%;
  border:0;background:none;color:var(--accent);font:inherit;font-weight:600;
  padding:4px 2px 8px;cursor:pointer;text-align:left}
.ghead:hover{text-decoration:underline}
@media (max-width:760px){
  .app{grid-template-columns:minmax(0,1fr)}
  aside{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line)}
  #courses{max-height:40vh;overflow:auto}
}
</style>
</head>
<body>
<div class="app">
  <aside>
    <div class="brand">BlackboardSync</div>
    <div class="sub" id="gen"></div>
    <input type="search" id="q" placeholder="Buscar archivo o anuncio…">
    <button class="nav on" data-view="home">Novedades <span class="n" id="newcount"></span></button>
    <div id="courses"></div>
  </aside>
  <main id="main"></main>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const href = p => p.split('/').map(encodeURIComponent).join('/');
const DAY = 864e5, now = Date.now();
const isNew = iso => now - new Date(iso) < 3 * DAY;
const fmtSize = b => b < 1024 ? b + ' B' : b < 1048576 ? (b/1024).toFixed(0) + ' KB' : (b/1048576).toFixed(1) + ' MB';
const pad = n => String(n).padStart(2, '0');
// dd/mm/aaaa h:mm AM/PM (date-only 'YYYY-MM-DD' -> just dd/mm/aaaa)
const fmtDate = iso => {
  if (!iso) return '';
  if (iso.length === 10) return iso.split('-').reverse().join('/');
  const d = new Date(iso), h = d.getHours();
  const time = `${h % 12 || 12}:${pad(d.getMinutes())} ${h < 12 ? 'AM' : 'PM'}`;
  // calendar days: 'hoy' / 'ayer', otherwise dd/mm/aaaa
  const day = x => new Date(x).setHours(0, 0, 0, 0);
  const diff = Math.round((day(now) - day(d)) / DAY);
  if (diff === 0) return 'hoy ' + time;
  if (diff === 1) return 'ayer ' + time;
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${time}`;
};
// UP-style section/term suffix: 'Curso-A-PRE-PRE2026_IIPER-130613' -> 'Curso'
const short = n => n.replace(/-[A-Z]{1,2}-[A-Z]+-.*$/, '');
const ext = n => (n.includes('.') ? n.split('.').pop() : '•').slice(0, 4).toUpperCase();

const fileRow = (f, course) => `<a class="row" href="${href(f.path)}" target="_blank">
  <div class="ico">${esc(ext(f.name))}</div>
  <div class="grow"><div class="name">${esc(f.name)}</div>
  <div class="meta">${course ? esc(short(course)) + ' · ' : ''}${fmtSize(f.size)} · publicado ${fmtDate(f.mtime)}${
    Math.abs(new Date(f.downloaded) - new Date(f.mtime)) > DAY ? ' · descargado ' + fmtDate(f.downloaded) : ''}</div></div>
  ${isNew(f.mtime) ? '<span class="badge">NUEVO</span>' : ''}</a>`;

const annRow = (a, showCourse) => `<details class="ann"><summary>
  <span class="t">${esc(a.title)}</span>
  ${isNew(a.date) ? '<span class="badge">NUEVO</span>' : ''}
  <span class="meta">${showCourse ? esc(short(a.course)) + ' · ' : ''}${fmtDate(a.date)}</span></summary>
  <pre>${esc(a.body)}</pre></details>`;

const list = (items, fn, empty) => `<div class="card">${items.length ? items.map(fn).join('') : `<div class="empty">${empty}</div>`}</div>`;

const treeHtml = (node, open) => {
  const inner = node.dirs.map(d => treeHtml(d, false)).join('') + node.files.map(f => fileRow(f)).join('');
  return `<details ${open ? 'open' : ''}><summary>📁 ${esc(node.name)} <span class="meta">${countFiles(node)}</span></summary>${inner || '<div class="empty">Vacío</div>'}</details>`;
};
const countFiles = n => n.files.length + n.dirs.reduce((s, d) => s + countFiles(d), 0);

let view = 'home';
function renderNav() {
  let html = '', year = null;
  D.courses.forEach((c, i) => {
    if (c.year !== year) { year = c.year; html += `<div class="year">${esc(year)}</div>`; }
    const fresh = c.last_modified && isNew(c.last_modified);
    html += `<button class="nav ${view == i ? 'on' : ''}" data-view="${i}" title="${esc(c.name)}">
      <span class="name">${esc(short(c.name))}</span>
      <span class="n">${fresh ? '<span class="badge">●</span> ' : ''}${c.file_count}</span></button>`;
  });
  $('#courses').innerHTML = html || '<div class="empty">Sin cursos todavía</div>';
  document.querySelectorAll('.nav').forEach(b => b.classList.toggle('on', b.dataset.view == String(view)));
}

function renderHome(q) {
  const m = s => !q || s.toLowerCase().includes(q);
  const files = D.recent.filter(f => m(f.name) || m(f.course));
  const anns = D.announcements.filter(a => m(a.title) || m(a.body) || m(a.course));
  const groups = new Map();  // insertion order = newest announcement first
  anns.forEach(a => groups.has(a.course) ? groups.get(a.course).push(a) : groups.set(a.course, [a]));
  const annHtml = groups.size ? [...groups].map(([course, items]) => {
    const i = D.courses.findIndex(c => c.name === course);
    return `<div class="group"><button class="ghead" data-view="${i}">${esc(short(course))}
      <span class="meta">${items.length} anuncio${items.length > 1 ? 's' : ''} ›</span></button>
      ${list(items.slice(0, 3), a => annRow(a, false), '')}</div>`;
  }).join('') : list([], null, 'Sin anuncios');
  const total = D.courses.reduce((s, c) => s + c.file_count, 0);
  const size = D.courses.reduce((s, c) => s + c.size, 0);
  $('#main').innerHTML = `<h1>Novedades</h1>
    <div class="stats">
      <div class="stat"><b>${D.courses.length}</b><span>cursos</span></div>
      <div class="stat"><b>${total}</b><span>archivos · ${fmtSize(size)}</span></div>
      <div class="stat"><b>${D.recent.filter(f => isNew(f.mtime)).length}</b><span>publicados (3 días)</span></div>
      <div class="stat"><b>${D.announcements.length}</b><span>anuncios</span></div>
    </div>
    <h2>Últimos anuncios por curso</h2>${annHtml}
    <h2>Último material</h2>${list(files, f => fileRow(f, f.course), 'Sin archivos')}`;
}

function renderCourse(c, q) {
  const m = s => !q || s.toLowerCase().includes(q);
  const anns = D.announcements.filter(a => a.course === c.name && (m(a.title) || m(a.body)));
  const every = []; (function walk(n){ every.push(...n.files); n.dirs.forEach(walk); })(c.tree);
  const files = [...every].sort((a, b) => b.mtime.localeCompare(a.mtime));
  let body;
  if (q) {
    const all = every.filter(f => m(f.name));
    body = `<h2>Archivos que coinciden</h2>${list(all, f => fileRow(f), 'Nada encontrado')}`;
  } else {
    body = `<h2>Carpetas y materiales</h2><div class="card tree" style="padding:8px">${treeHtml({...c.tree, name: short(c.name)}, true)}</div>`;
  }
  $('#main').innerHTML = `<h1>${esc(short(c.name))}</h1>
    <div class="meta">${esc(c.name)} · ${esc(c.year)} · ${c.file_count} archivos · ${fmtSize(c.size)}${c.last_modified ? ' · actualizado ' + fmtDate(c.last_modified) : ''}</div>
    ${files.length ? `<h2>Último publicado</h2>${list(files.slice(0, 5), f => fileRow(f))}` : ''}
    ${body}
    <h2>Anuncios</h2>${list(anns, a => annRow(a, false), 'Sin anuncios')}`;
}

function render() {
  const q = $('#q').value.trim().toLowerCase();
  renderNav();
  view === 'home' ? renderHome(q) : renderCourse(D.courses[view], q);
}

document.addEventListener('click', e => {
  const b = e.target.closest('[data-view]'); if (!b) return;
  view = b.dataset.view === 'home' ? 'home' : +b.dataset.view;
  render(); window.scrollTo(0, 0);
});
$('#q').addEventListener('input', render);
$('#gen').textContent = 'Actualizado ' + fmtDate(D.generated);
$('#newcount').textContent = D.recent.filter(f => isNew(f.mtime)).length || '';
render();
</script>
</body>
</html>
"""
