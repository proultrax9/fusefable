from __future__ import annotations
from typing import Protocol
from fusefable.models import Completion


class Provider(Protocol):
    async def complete(self, model: str, prompt: str) -> Completion:
        """ยิง 1 โมเดล คืน Completion. โยน exception ได้เมื่อ HTTP error."""
        ...
