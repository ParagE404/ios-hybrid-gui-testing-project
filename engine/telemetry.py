"""Append-only JSONL telemetry.

Origin: original, 

One line per event. Every line carries the run context (run_id, scenario, condition,
configuration, repetition) so the analysis scripts can work from raw logs alone.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class Telemetry:
    def __init__(self, path: str | Path | None, **context: Any):
        self.path = Path(path) if path else None
        self.context = context
        self.records: list[dict] = []
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def bind(self, **extra: Any) -> "Telemetry":
        t = Telemetry(None, **{**self.context, **extra})
        t.path, t.records = self.path, self.records
        return t

    def emit(self, event: str, **data: Any) -> dict:
        rec = {"ts": time.time(), "event": event, **self.context, **data}
        self.records.append(rec)
        if self.path:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, default=str) + "\n")
        return rec
