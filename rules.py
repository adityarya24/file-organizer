"""File classification, safety checks, and destination routing rules."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from config import OrganizerConfig, WatchFolderConfig


def should_ignore_file(
    file_path: Path,
    config: OrganizerConfig,
    watch_cfg: WatchFolderConfig
) -> bool:
    """Determine whether a file should be ignored from processing."""
    name = file_path.name
    suffix = file_path.suffix.lower()

    # 1. Ignored exact names (desktop.ini, Thumbs.db, etc.)
    if name in config.ignored_names or name.startswith("."):
        return True

    # 2. In-progress download extensions (.crdownload, .tmp, .part, etc.)
    if suffix in config.temporary_extensions:
        return True

    # 3. Watcher-specific ignored extensions (e.g. .lnk, .url on Desktop)
    if suffix in watch_cfg.ignore_extensions:
        return True

    # 4. Check if inside target destination directory (avoid recursive loops)
    try:
        rel = file_path.relative_to(watch_cfg.path)
        # If relative path is inside a category subfolder or "Organized"
        if len(rel.parts) > 1:
            first_dir = rel.parts[0]
            if first_dir in config.categories or first_dir == "Organized" or first_dir == "Others":
                return True
    except ValueError:
        pass

    return False


def classify_file(
    file_path: Path,
    config: OrganizerConfig
) -> str:
    """Return the category name for a given file based on its extension."""
    suffix = file_path.suffix.lower()
    if not suffix:
        return "Others"
    return config.extension_map.get(suffix, "Others")


def is_file_ready_for_move(
    file_path: Path,
    settle_delay: float = 2.0
) -> bool:
    """
    Check if the file has finished writing/downloading and is not locked by another process.
    Fast-paths settled older files; only delays freshly modified files.
    """
    if not file_path.is_file():
        return False

    try:
        st = file_path.stat()
        file_age = time.time() - st.st_mtime
    except OSError:
        return False

    # If file was modified within the last 5 seconds, verify size stability
    if file_age < 5.0:
        initial_size = st.st_size
        time.sleep(min(settle_delay, 1.0))
        try:
            current_size = file_path.stat().st_size
            if initial_size != current_size:
                return False
        except OSError:
            return False

    # Non-exclusive open check to confirm no lock
    try:
        with open(file_path, "r+b"):
            pass
        return True
    except (PermissionError, OSError):
        # File is locked by browser/downloader
        return False


def get_unique_destination(target_dir: Path, original_filename: str) -> Path:
    """
    Generate collision-safe target path:
    If `report.pdf` exists, returns `report (1).pdf`, `report (2).pdf`, etc.
    """
    dest_path = target_dir / original_filename
    if not dest_path.exists():
        return dest_path

    p = Path(original_filename)
    stem = p.stem
    suffix = p.suffix

    counter = 1
    while True:
        candidate_name = f"{stem} ({counter}){suffix}"
        candidate_path = target_dir / candidate_name
        if not candidate_path.exists():
            return candidate_path
        counter += 1
