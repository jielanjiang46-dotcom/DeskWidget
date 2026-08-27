import json

from ..constants import COURSES_FILE
from .models import CourseItem


class CourseRepository:
    def load(self) -> tuple[list[CourseItem], bool]:
        if not COURSES_FILE.exists():
            return [], True
        try:
            data = json.loads(COURSES_FILE.read_text(encoding="utf-8"))
            items = [CourseItem.from_dict(item) for item in data.get("items", [])]
            return items, bool(data.get("show_in_calendar", True))
        except (OSError, ValueError, TypeError, AttributeError):
            return [], True

    def save(self, items: list[CourseItem], show_in_calendar: bool) -> None:
        try:
            COURSES_FILE.write_text(
                json.dumps(
                    {"show_in_calendar": show_in_calendar,
                     "items": [item.to_dict() for item in items]},
                    ensure_ascii=False, indent=2,
                ),
                encoding="utf-8",
            )
        except OSError:
            pass
