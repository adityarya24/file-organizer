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
        if watch_cfg.target_base in file_path.parents or file_path.parent == watch_cfg.target_base:
            # If the file is directly or indirectly inside the organized output tree
            rel = file_path.relative_to(watch_cfg.path)
            # If relative path has more than 1 part and first part is a known category or "Organized"
            if len(rel.parts) > 1 and (rel.parts[0] in config.categories or rel.parts[0] == "Organized"):
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
    """
    if not file_path.is_file():
        return False

    # Check 1: File size stability
    try:
        initial_size = file_path.stat().st_size
    except OSError:
        return False

    # Brief delay if file was just created
    time.sleep(min(settle_delay, 1.0))

    try:
        current_size = file_path.stat().st_size
        if initial_size != current_size:
            return False
    except OSError:
        return False

    # Check 2: Try to open the file exclusively in append mode to confirm lock release
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
