from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Mem:
    max_items: int = 30
    items: list[str] = field(default_factory=list)

    def add(self, s: str) -> None:
        self.items.append(s.strip())
        if len(self.items) > self.max_items:
            self.items = self.items[-self.max_items :]

    def view(self) -> str:
        return "\n".join(self.items)

