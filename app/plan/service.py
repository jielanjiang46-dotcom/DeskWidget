from datetime import date, datetime, timedelta

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
