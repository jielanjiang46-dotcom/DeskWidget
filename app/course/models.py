from dataclasses import asdict, dataclass, field
from datetime import date
from uuid import uuid4


@dataclass
class CourseItem:
    id: str
    name: str
    weekday: int
    start_time: str
    end_time: str
    location: str = ""
    teacher: str = ""
    start_date: str = ""
    end_date: str = ""
    dates: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls, name: str, weekday: int, start_time: str, end_time: str,
        location: str = "", teacher: str = "", start_date: str = "",
        end_date: str = "",
    ) -> "CourseItem":
        return cls(
            uuid4().hex, name.strip(), weekday, start_time, end_time,
            location.strip(), teacher.strip(), start_date, end_date,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "CourseItem":
        return cls(
            str(data.get("id") or uuid4().hex), str(data.get("name", "")),
            int(data.get("weekday", 0)), str(data.get("start_time", "")),
            str(data.get("end_time", "")), str(data.get("location", "")),
            str(data.get("teacher", "")), str(data.get("start_date", "")),
            str(data.get("end_date", "")),
            [str(value) for value in data.get("dates", []) if value],
        )

    def occurs_on(self, day: date) -> bool:
        if day.weekday() != self.weekday:
            return False
        if self.dates:
            return day.isoformat() in self.dates
        if self.start_date and day < date.fromisoformat(self.start_date):
            return False
        if self.end_date and day > date.fromisoformat(self.end_date):
            return False
        return True

    def to_dict(self) -> dict:
        return asdict(self)
