from pathlib import Path
from datetime import datetime

from bs4 import BeautifulSoup
from pathvalidate import sanitize_filename


class Announcement:
    def __init__(self, data: dict):
        self.title = data.get("title") or "Untitled"
        self.body_html = data.get("body") or ""
        created_str = data.get("created")
        modified_str = data.get("modified")
        self.created = self._parse_dt(created_str)
        self.modified = self._parse_dt(modified_str)

    @staticmethod
    def _parse_dt(s: str | None) -> datetime | None:
        if not s:
            return None
        return datetime.fromisoformat(s.replace("Z", "+00:00"))

    def write(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)

        date_str = self.created.strftime("%Y-%m-%d") if self.created else "No-Date"
        safe_title = sanitize_filename(self.title, replacement_text="_") or "Untitled"
        filename = f"{date_str} - {safe_title}.md"
        filepath = folder / filename

        if filepath.exists():
            return

        body_text = (
            BeautifulSoup(self.body_html, "lxml").get_text(separator="\n").strip()
            if self.body_html
            else ""
        )

        timestamp = self.created.strftime("%Y-%m-%d %H:%M UTC") if self.created else "Unknown"
        content = f"# {self.title}\n\n**Date:** {timestamp}\n\n---\n\n{body_text}\n"

        filepath.write_text(content, encoding="utf-8")
