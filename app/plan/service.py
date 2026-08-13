from .models import PlanItem
from .repository import PlanRepository


class PlanService:
    def __init__(self, repository: PlanRepository | None = None) -> None:
        self.repository = repository or PlanRepository()
        self.items = self.repository.load()
        self._listeners: list[callable] = []

    def subscribe(self, listener) -> None:
        self._listeners.append(listener)

    def add(self, title: str, due_at: str | None = None) -> PlanItem | None:
        if not title.strip():
            return None
        item = PlanItem.create(title, due_at)
        self.items.append(item)
        self._changed()
        return item

    def set_completed(self, item_id: str, completed: bool) -> None:
        for item in self.items:
            if item.id == item_id:
                item.completed = completed
                self._changed()
                return

    def update(self, item_id: str, title: str, due_at: str | None) -> None:
        if not title.strip():
            return
        for item in self.items:
            if item.id == item_id:
                item.title = title.strip()
                item.due_at = due_at
                self._changed()
                return

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
