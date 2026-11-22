import json

from blackboard_sync.dashboard import DASHBOARD_NAME, build_index, write_dashboard


def test_dashboard_indexes_courses_files_and_announcements(tmp_path):
    course = tmp_path / "2026" / "Cálculo"
    (course / "Semana 1").mkdir(parents=True)
    (course / "Semana 1" / "clase.pdf").write_bytes(b"x" * 10)
    (course / "Announcements").mkdir()
    (course / "Announcements" / "2026-11-10 - Examen.md").write_text(
        "# Examen\n\n**Date:** 2026-11-10 10:00 UTC\n\n---\n\nEl lunes </script>.\n",
        encoding="utf-8")
    (course / "Roster").mkdir()
    (course / "Roster" / "roster.md").write_text("x", encoding="utf-8")
    (tmp_path / "recent.md").write_text("x", encoding="utf-8")

    data = build_index(tmp_path)
    [c] = data["courses"]
    assert c["year"] == "2026" and c["file_count"] == 1
    assert c["tree"]["dirs"][0]["files"][0]["path"] == "2026/Cálculo/Semana 1/clase.pdf"
    assert [f["name"] for f in data["recent"]] == ["clase.pdf"]
    [a] = data["announcements"]
    assert (a["title"], a["date"], a["body"]) == ("Examen", "2026-11-10T10:00:00+00:00", "El lunes </script>.")

    html = write_dashboard(tmp_path).read_text(encoding="utf-8")
    assert (tmp_path / DASHBOARD_NAME).exists()
    blob = html.split('type="application/json">', 1)[1].split("</script>", 1)[0]
    assert json.loads(blob)["announcements"][0]["body"] == "El lunes </script>."


def test_dashboard_embeds_connection_status(tmp_path):
    from datetime import datetime, timezone
    since = datetime(2026, 11, 21, 7, 24, tzinfo=timezone.utc)

    def status(html):
        blob = html.split('type="application/json">', 1)[1].split("</script>", 1)[0]
        return json.loads(blob)["status"]

    ok = write_dashboard(tmp_path).read_text(encoding="utf-8")
    assert status(ok) == {"state": "ok", "since": None}
    auth = write_dashboard(tmp_path, "auth", since).read_text(encoding="utf-8")
    assert status(auth) == {"state": "auth", "since": since.isoformat()}
    assert 'id="conn"' in auth
