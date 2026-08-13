import json

from ..constants import PLANS_FILE
from .models import PlanItem


class PlanRepository:
    def load(self) -> list[PlanItem]:
        if not PLANS_FILE.exists():
            return []
        try:
            data = json.loads(PLANS_FILE.read_text(encoding="utf-8"))
            return [PlanItem.from_dict(item) for item in data.get("items", [])]
        except (OSError, json.JSONDecodeError, AttributeError):
            return []

    def save(self, items: list[PlanItem]) -> None:
        try:
            PLANS_FILE.write_text(
                json.dumps({"items": [item.to_dict() for item in items]}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

