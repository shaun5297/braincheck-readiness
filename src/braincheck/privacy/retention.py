from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class RetentionPolicy:
    raw_days: int = 30
    result_days: int = 365

    def raw_expires_at(self, created_at: datetime) -> datetime:
        value = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
        return value + timedelta(days=self.raw_days)

