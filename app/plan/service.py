from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
from uuid import uuid4

from .models import PlanItem
from .repository import PlanRepository


class PlanService:
    def __init__(self, repository: PlanRepository | None = None) -> None:
        self.repository = repository or PlanRepository()
        self.items = self.repository.load()
        self._listeners: list[callable] = []

    def subscribe(self, listener) -> None:
        self._listeners.append(listener)

    def add(
        self, title: str, due_at: str | None = None, repeat_weekly: bool = False
    ) -> PlanItem | None:
        if not title.strip():
            return None
        item = PlanItem.create(title, due_at, repeat_weekly)
        self.items.append(item)
        self._changed()
        return item

    def set_completed(self, item_id: str, completed: bool) -> None:
        for item in self.items:
            if item.id == item_id:
                item.completed = completed
                self._changed()
                return

    def update(
        self, item_id: str, title: str, due_at: str | None,
        repeat_weekly: bool = False,
    ) -> None:
        if not title.strip():
            return
        for item in self.items:
            if item.id == item_id:
                item.title = title.strip()
                item.due_at = due_at
                item.repeat_weekly = repeat_weekly
                self._changed()
                return

    def occurs_on(self, item: PlanItem, day: date) -> bool:
        if not item.due_at:
            return False
        try:
            due = datetime.fromisoformat(item.due_at)
        except ValueError:
            return False
        if not item.repeat_weekly:
            return due.date() == day
        return day >= due.date() and day.weekday() == due.weekday()

    def items_on(self, day: date) -> list[PlanItem]:
        return [item for item in self.items if self.occurs_on(item, day)]

    def occurs_between(self, item: PlanItem, start: date, end: date) -> bool:
        day = start
        while day <= end:
            if self.occurs_on(item, day):
                return True
            day += timedelta(days=1)
        return False

    def import_file(self, path: Path) -> tuple[int, int]:
        imported = (
            self._import_ics(path) if path.suffix.lower() == ".ics"
            else self._import_json(path)
        )
        existing = {
            (item.title, item.due_at or "", item.repeat_weekly)
            for item in self.items
        }
        existing_ids = {item.id for item in self.items}
        added = []
        skipped = 0
        for item in imported:
            signature = (item.title, item.due_at or "", item.repeat_weekly)
            if signature in existing:
                skipped += 1
                continue
            if item.id in existing_ids:
                item.id = uuid4().hex
            existing.add(signature)
            existing_ids.add(item.id)
            added.append(item)
        if added:
            self.items.extend(added)
            self._changed()
        return len(added), skipped

    def export_file(self, path: Path) -> int:
        if path.suffix.lower() == ".ics":
            content = self._export_ics()
            count = content.count("BEGIN:VEVENT")
        else:
            content = json.dumps(
                {"format": "DeskWidget plans", "version": 1,
                 "items": [item.to_dict() for item in self.items]},
                ensure_ascii=False, indent=2,
            )
            count = len(self.items)
        path.write_text(content, encoding="utf-8")
        return count

    @staticmethod
    def _import_json(path: Path) -> list[PlanItem]:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        items = data.get("items", []) if isinstance(data, dict) else data
        if not isinstance(items, list):
            raise ValueError("日程 JSON 中没有有效的 items 列表。")
        return [PlanItem.from_dict(item) for item in items if isinstance(item, dict)]

    @staticmethod
    def _import_ics(path: Path) -> list[PlanItem]:
        text = path.read_text(encoding="utf-8-sig")
        unfolded = re.sub(r"\r?\n[ \t]", "", text)
        items = []
        for block in unfolded.split("BEGIN:VEVENT")[1:]:
            event = block.split("END:VEVENT", 1)[0]
            summary = PlanService._ics_value(event, "SUMMARY")
            start = PlanService._ics_value(event, "DTSTART")
            if not summary or not start:
                continue
            due = PlanService._parse_ics_datetime(start)
            repeat = "FREQ=WEEKLY" in PlanService._ics_value(event, "RRULE")
            item = PlanItem.create(PlanService._ics_unescape(summary), due, repeat)
            item.completed = (
                PlanService._ics_value(event, "STATUS").upper() == "COMPLETED"
            )
            items.append(item)
        return items

    def _export_ics(self) -> str:
        lines = [
            "BEGIN:VCALENDAR", "VERSION:2.0",
            "PRODID:-//DeskWidget//Plans//ZH", "CALSCALE:GREGORIAN",
        ]
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        for item in self.items:
            if not item.due_at:
                continue
            try:
                due = datetime.fromisoformat(item.due_at)
            except ValueError:
                continue
            lines.extend([
                "BEGIN:VEVENT", f"UID:{item.id}@deskwidget",
                f"DTSTAMP:{stamp}", f"DTSTART:{due:%Y%m%dT%H%M%S}",
                f"SUMMARY:{self._ics_escape(item.title)}",
            ])
            if item.repeat_weekly:
                lines.append("RRULE:FREQ=WEEKLY")
            if item.completed:
                lines.append("STATUS:COMPLETED")
            lines.append("END:VEVENT")
        lines.append("END:VCALENDAR")
        return "\r\n".join(lines) + "\r\n"

    @staticmethod
    def _ics_value(event: str, name: str) -> str:
        match = re.search(rf"(?m)^{re.escape(name)}(?:;[^:]*)?:(.*)$", event)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _parse_ics_datetime(value: str) -> str:
        normalized = value.rstrip("Z")
        for pattern in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
            try:
                return datetime.strptime(normalized, pattern).isoformat()
            except ValueError:
                continue
        raise ValueError(f"无法识别日历时间“{value}”。")

    @staticmethod
    def _ics_escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")

    @staticmethod
    def _ics_unescape(value: str) -> str:
        return value.replace("\\n", "\n").replace("\\;", ";").replace("\\,", ",").replace("\\\\", "\\")

    def delete(self, item_id: str) -> None:
        self.items = [item for item in self.items if item.id != item_id]
        self._changed()

    def add_pomodoro(self, item_id: str) -> None:
        for item in self.items:
            if item.id == item_id:
                item.pomodoros += 1
                self._changed()
                return

    def _changed(self) -> None:
        self.repository.save(self.items)
        for listener in tuple(self._listeners):
            listener()
