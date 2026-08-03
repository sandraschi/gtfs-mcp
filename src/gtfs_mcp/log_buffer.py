"""In-memory ring-buffer activity log for the webapp Logging page."""

import threading
import time
from collections import deque


class ActivityLog:
    """Thread-safe ring buffer with query/stats/export support."""

    def __init__(self, max_entries: int = 500):
        self._entries: deque[dict] = deque(maxlen=max_entries)
        self._lock = threading.Lock()
        self._counter = 0

    def info(self, kind: str, message: str) -> None:
        self._append("INFO", kind, message)

    def warning(self, kind: str, message: str) -> None:
        self._append("WARNING", kind, message)

    def error(self, kind: str, message: str) -> None:
        self._append("ERROR", kind, message)

    def _append(self, level: str, kind: str, message: str) -> None:
        with self._lock:
            self._counter += 1
            self._entries.append(
                {
                    "id": str(self._counter),
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "level": level,
                    "kind": kind,
                    "message": str(message),
                }
            )

    def query(self, limit=50, offset=0, level=None, search=None, sort="desc"):
        with self._lock:
            entries = list(self._entries)
        if level:
            entries = [e for e in entries if e["level"] == level.upper()]
        if search:
            entries = [e for e in entries if search.lower() in e["message"].lower()]
        if sort == "asc":
            entries = list(reversed(entries))
        total = len(entries)
        return {
            "entries": entries[offset : offset + limit],
            "total": total,
            "limit": limit,
            "offset": offset,
            "max_entries": self._entries.maxlen,
            "sort": sort,
        }

    def stats(self):
        with self._lock:
            entries = list(self._entries)
        levels: dict[str, int] = {}
        kinds: dict[str, int] = {}
        for e in entries:
            levels[e["level"]] = levels.get(e["level"], 0) + 1
            kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
        return {"total": len(entries), "max_entries": self._entries.maxlen, "levels": levels, "kinds": kinds}

    def export(self, level=None, search=None, sort="desc"):
        result = self.query(limit=5000, level=level, search=search, sort=sort)
        lines = [f"[{e['timestamp']}] {e['level']} {e['kind']}: {e['message']}" for e in result["entries"]]
        return "\n".join(lines)

    def clear(self) -> int:
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
        return count


activity_log = ActivityLog()
