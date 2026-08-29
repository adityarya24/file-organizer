"""History and undo manager for File Organizer."""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

HISTORY_FILE = Path(__file__).parent / "history.jsonl"


@dataclass
class MoveRecord:
    session_id: str
    timestamp: str
    src: str
    dest: str
    category: str
    size_bytes: int


class HistoryManager:
    """Manages transaction logs and undo rollback operations."""

    def __init__(self, history_file: Path | None = None) -> None:
        self.history_file = history_file or HISTORY_FILE

    def log_move(
        self,
        *,
        session_id: str,
        src: Path,
        dest: Path,
        category: str,
        size_bytes: int = 0
    ) -> None:
        """Append a move operation to history."""
        record = MoveRecord(
            session_id=session_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            src=str(src.resolve()),
            dest=str(dest.resolve()),
            category=category,
            size_bytes=size_bytes,
        )
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    def get_recent_records(self, limit: int = 50) -> list[MoveRecord]:
        """Fetch the most recent move records."""
        if not self.history_file.is_file():
            return []
        records: list[MoveRecord] = []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            records.append(MoveRecord(**data))
                        except Exception:
                            continue
        except Exception:
            return []
        return records[-limit:]

    def undo_last_moves(self, count: int = 1) -> list[tuple[str, str, bool, str]]:
        """
        Undo the last N moves.
        Returns list of (dest_path, original_src_path, success, message).
        """
        records = self.get_recent_records(limit=1000)
        if not records:
            return []

        to_undo = records[-count:]
        results: list[tuple[str, str, bool, str]] = []

        # Process in reverse order
        for rec in reversed(to_undo):
            current_path = Path(rec.dest)
            original_path = Path(rec.src)

            if not current_path.exists():
                results.append((rec.dest, rec.src, False, "File does not exist at current destination"))
                continue

            try:
                # Ensure destination directory exists
                original_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Check collision at original location
                final_dest = original_path
                if final_dest.exists() and final_dest != current_path:
                    stem = original_path.stem
                    suffix = original_path.suffix
                    final_dest = original_path.parent / f"{stem}_restored{suffix}"

                shutil.move(str(current_path), str(final_dest))
                results.append((str(current_path), str(final_dest), True, "Restored successfully"))
            except Exception as exc:
                results.append((str(current_path), str(original_path), False, str(exc)))

        # Rewrite history file without the successfully undone records
        undone_dests = {r[0] for r in results if r[2]}
        remaining = [r for r in records if r.dest not in undone_dests]
        with open(self.history_file, "w", encoding="utf-8") as f:
            for r in remaining:
                f.write(json.dumps(asdict(r)) + "\n")

        return results
