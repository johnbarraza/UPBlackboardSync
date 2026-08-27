from datetime import datetime, timezone
from pathlib import Path


class Roster:
    def __init__(self, course_id: str, members: list[dict]):
        self.course_id = course_id
        self.members = members

    @classmethod
    def fetch(cls, session, course_id: str) -> "Roster":
        try:
            result = session.fetch_course_memberships(course_id=course_id)
            if isinstance(result, dict):
                items = result.get("results", [result])
            elif isinstance(result, list):
                items = result
            else:
                items = []
        except Exception:
            items = []
        return cls(course_id, items)

    def write(self, folder: Path) -> None:
        if not self.members:
            return

        folder.mkdir(parents=True, exist_ok=True)
        filepath = folder / "roster.md"

        updated = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            "# Roster",
            "",
            f"**Last updated:** {updated}  ",
            f"**Members found:** {len(self.members)}",
            "",
            "| # | User ID | Role | Available |",
            "|---|---------|------|-----------|",
        ]

        for i, m in enumerate(self.members, 1):
            uid = m.get("userId", "—")
            role = m.get("courseRoleId", "—")
            avail = m.get("availability", {})
            if isinstance(avail, dict):
                avail = avail.get("available", "—")

            # Some Blackboard instances include nested user details
            user = m.get("user", {}) or {}
            name_obj = user.get("name", {}) or {}
            given = name_obj.get("given", "")
            family = name_obj.get("family", "")
            username = user.get("userName", "")
            display = f"{given} {family}".strip() or username or uid

            lines.append(f"| {i} | {display} | {role} | {avail} |")

        lines.append("")
        filepath.write_text("\n".join(lines), encoding="utf-8")
