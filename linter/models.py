from __future__ import annotations

from dataclasses import asdict, dataclass

ERROR = "error"
WARNING = "warning"
INFO = "info"


@dataclass(frozen=True)
class Issue:
    level: str
    path: str
    message: str

    def to_dict(self) -> dict:
        return asdict(self)
