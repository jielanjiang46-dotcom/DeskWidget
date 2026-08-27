from dataclasses import asdict, dataclass
from datetime import datetime
from uuid import uuid4


@dataclass
class PlanItem:
    id: str
    title: str
    due_at: str | None = None
    completed: bool = False
    created_at: str = ""
    pomodoros: int = 0
    repeat_weekly: bool = False

    @classmethod
    def create(
        cls, title: str, due_at: str | None = None, repeat_weekly: bool = False
    ) -> "PlanItem":
        return cls(
            uuid4().hex, title.strip(), due_at, False,
            datetime.now().isoformat(), 0, repeat_weekly,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "PlanItem":
        return cls(
            str(data.get("id") or uuid4().hex),
            str(data.get("title", "")),
            data.get("due_at"),
            bool(data.get("completed", False)),
            str(data.get("created_at", "")),
            int(data.get("pomodoros", 0)),
            bool(data.get("repeat_weekly", False)),
        )

    def to_dict(self) -> dict:
        return asdict(self)
