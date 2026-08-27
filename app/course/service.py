import csv
import io
import re
from datetime import date, datetime
from pathlib import Path

from .models import CourseItem
from .repository import CourseRepository


WEEKDAYS = {
    "1": 0, "周一": 0, "星期一": 0, "monday": 0, "mon": 0,
    "2": 1, "周二": 1, "星期二": 1, "tuesday": 1, "tue": 1,
    "3": 2, "周三": 2, "星期三": 2, "wednesday": 2, "wed": 2,
    "4": 3, "周四": 3, "星期四": 3, "thursday": 3, "thu": 3,
    "5": 4, "周五": 4, "星期五": 4, "friday": 4, "fri": 4,
    "6": 5, "周六": 5, "星期六": 5, "saturday": 5, "sat": 5,
    "7": 6, "周日": 6, "星期日": 6, "星期天": 6, "sunday": 6, "sun": 6,
}


class CourseService:
    def __init__(self, repository: CourseRepository | None = None) -> None:
        self.repository = repository or CourseRepository()
        self.items, self.show_in_calendar = self.repository.load()
        self._listeners: list[callable] = []

    def subscribe(self, listener) -> None:
        self._listeners.append(listener)

    def courses_on(self, day: date) -> list[CourseItem]:
        return sorted(
            (item for item in self.items if item.occurs_on(day)),
            key=lambda item: item.start_time,
        )

    def set_show_in_calendar(self, enabled: bool) -> None:
        self.show_in_calendar = enabled
        self._changed()

    def delete(self, item_id: str) -> None:
        self.items = [item for item in self.items if item.id != item_id]
        self._changed()

    def clear(self) -> None:
        self.items.clear()
        self._changed()

    def import_csv(self, path: Path) -> tuple[int, list[str]]:
        aliases = {
            "name": ("课程", "课程名", "课程名称", "name", "course"),
            "weekday": ("星期", "周几", "weekday", "day"),
            "start_time": ("开始时间", "上课时间", "start_time", "start"),
            "end_time": ("结束时间", "下课时间", "end_time", "end"),
            "location": ("地点", "教室", "location", "room"),
            "teacher": ("教师", "老师", "teacher"),
            "start_date": ("开始日期", "start_date"),
            "end_date": ("结束日期", "end_date"),
        }
        imported: list[CourseItem] = []
        errors: list[str] = []
        content = self._decode(path)
        with io.StringIO(content, newline="") as source:
            reader = csv.DictReader(source)
            if not reader.fieldnames:
                raise ValueError("CSV 文件没有表头。")
            fields = {name.strip().lower(): name for name in reader.fieldnames}

            def value(row, key: str) -> str:
                for alias in aliases[key]:
                    original = fields.get(alias.lower())
                    if original is not None:
                        return str(row.get(original, "") or "").strip()
                return ""

            for line, row in enumerate(reader, 2):
                try:
                    name = value(row, "name")
                    weekday_text = value(row, "weekday").lower()
                    if not name or weekday_text not in WEEKDAYS:
                        raise ValueError("课程名或星期无效")
                    start = self._time(value(row, "start_time"))
                    end = self._time(value(row, "end_time"))
                    if not start or not end or start >= end:
                        raise ValueError("开始/结束时间无效")
                    start_date = self._date(value(row, "start_date"))
                    end_date = self._date(value(row, "end_date"))
                    imported.append(CourseItem.create(
                        name, WEEKDAYS[weekday_text], start, end,
                        value(row, "location"), value(row, "teacher"),
                        start_date, end_date,
                    ))
                except ValueError as error:
                    errors.append(f"第 {line} 行：{error}")
        self.items.extend(imported)
        if imported:
            self._changed()
        return len(imported), errors

    def import_ics(self, path: Path) -> tuple[int, list[str]]:
        content = self._decode(path)
        # RFC 5545 folds long properties onto continuation lines.
        unfolded = re.sub(r"\r?\n[ \t]", "", content)
        groups: dict[tuple, set[str]] = {}
        errors: list[str] = []
        for index, block in enumerate(unfolded.split("BEGIN:VEVENT")[1:], 1):
            event = block.split("END:VEVENT", 1)[0]
            try:
                name = self._ics_unescape(self._ics_value(event, "SUMMARY"))
                start = self._ics_datetime(self._ics_value(event, "DTSTART"))
                end = self._ics_datetime(self._ics_value(event, "DTEND"))
                if not name or end <= start:
                    raise ValueError("课程名称或时间无效")
                location = self._ics_unescape(
                    self._ics_value(event, "LOCATION", required=False)
                )
                description = self._ics_unescape(
                    self._ics_value(event, "DESCRIPTION", required=False)
                )
                teacher_match = re.search(
                    r"(?:Teacher|Instructor|Lecturer|教师|老师)\s*:\s*([^\n]+)",
                    description, re.IGNORECASE,
                )
                teacher = teacher_match.group(1).strip() if teacher_match else ""
                key = (
                    name, start.weekday(), start.strftime("%H:%M"),
                    end.strftime("%H:%M"), location, teacher,
                )
                groups.setdefault(key, set()).add(start.date().isoformat())
            except ValueError as error:
                errors.append(f"第 {index} 个日历事件：{error}")

        imported: list[CourseItem] = []
        for key, dates in groups.items():
            name, weekday, start_time, end_time, location, teacher = key
            ordered = sorted(dates)
            course = CourseItem.create(
                name, weekday, start_time, end_time, location, teacher,
                ordered[0], ordered[-1],
            )
            course.dates = ordered
            imported.append(course)
        self.items.extend(imported)
        if imported:
            self._changed()
        return len(imported), errors

    def import_file(self, path: Path) -> tuple[int, list[str]]:
        if path.suffix.lower() == ".ics":
            return self.import_ics(path)
        return self.import_csv(path)

    @staticmethod
    def _decode(path: Path) -> str:
        raw = path.read_bytes()
        try:
            return raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return raw.decode("gb18030")

    @staticmethod
    def _ics_value(event: str, name: str, required: bool = True) -> str:
        match = re.search(rf"(?m)^{re.escape(name)}(?:;[^:]*)?:(.*)$", event)
        if match is not None:
            return match.group(1).strip()
        if required:
            raise ValueError(f"缺少 {name} 字段")
        return ""

    @staticmethod
    def _ics_datetime(value: str) -> datetime:
        normalized = value.rstrip("Z")
        for pattern in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
            try:
                return datetime.strptime(normalized, pattern)
            except ValueError:
                continue
        raise ValueError(f"无法识别日历时间“{value}”")

    @staticmethod
    def _ics_unescape(value: str) -> str:
        return (
            value.replace("\\n", "\n").replace("\\N", "\n")
            .replace("\\,", ",").replace("\\;", ";")
            .replace("\\\\", "\\")
        )

    @staticmethod
    def _time(value: str) -> str:
        if not value:
            return ""
        for pattern in ("%H:%M", "%H:%M:%S"):
            try:
                return datetime.strptime(value, pattern).strftime("%H:%M")
            except ValueError:
                continue
        raise ValueError(f"无法识别时间“{value}”")

    @staticmethod
    def _date(value: str) -> str:
        if not value:
            return ""
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as error:
            raise ValueError(f"无法识别日期“{value}”") from error

    def _changed(self) -> None:
        self.repository.save(self.items, self.show_in_calendar)
        for listener in tuple(self._listeners):
            listener()
