"""Configuration manager for File Organizer."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULT_CATEGORIES: dict[str, list[str]] = {
    "Documents": [
        ".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".epub", ".pages", ".md", ".tex", ".wpd"
    ],
    "Spreadsheets": [
        ".xlsx", ".xls", ".csv", ".tsv", ".ods", ".numbers"
    ],
    "Presentations": [
        ".ppt", ".pptx", ".key", ".odp"
    ],
    "Images": [
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".tiff", ".ico", ".heic", ".psd", ".ai", ".raw", ".cr2", ".nef"
    ],
    "Videos": [
        ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v", ".3gp", ".ts"
    ],
    "Audio": [
        ".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma", ".opus", ".mid", ".midi"
    ],
    "Archives": [
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".dmg", ".tgz"
    ],
    "Installers": [
        ".exe", ".msi", ".bat", ".cmd", ".ps1", ".apk", ".appx", ".msix", ".pkg", ".deb", ".rpm"
    ],
    "Code_and_Data": [
        ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss", ".json", ".xml", ".yaml", ".yml",
        ".sql", ".db", ".sqlite", ".c", ".cpp", ".h", ".hpp", ".rs", ".go", ".java", ".kt", ".swift",
        ".sh", ".ipynb", ".parquet"
    ],
    "Torrents": [
        ".torrent"
    ]
}

DEFAULT_TEMPORARY_EXTENSIONS: list[str] = [
    ".crdownload", ".tmp", ".partial", ".part", ".~tmp", ".download", ".aria2", ".lock"
]

DEFAULT_IGNORED_NAMES: list[str] = [
    "desktop.ini", "Thumbs.db", ".DS_Store", "Organized", "history.jsonl"
]


@dataclass
class WatchFolderConfig:
    path: Path
    mode: str  # "categorized_subfolders" or "desktop_cleanup"
    target_base: Path
    enabled: bool = True
    ignore_extensions: list[str] = field(default_factory=list)


@dataclass
class OrganizerConfig:
    watch_dirs: list[WatchFolderConfig]
    categories: dict[str, list[str]]
    temporary_extensions: list[str]
    ignored_names: list[str]
    settle_delay_seconds: float = 3.0
    poll_interval_seconds: float = 2.0
    extension_map: dict[str, str] = field(init=False)

    def __post_init__(self) -> None:
        # Build fast lookup map: extension -> category
        ext_map: dict[str, str] = {}
        for category, exts in self.categories.items():
            for ext in exts:
                cleaned = ext.strip().lower()
                if not cleaned.startswith("."):
                    cleaned = f".{cleaned}"
                ext_map[cleaned] = category
        self.extension_map = ext_map


def load_config(config_path: Path | None = None) -> OrganizerConfig:
    """Load configuration from JSON or use sensible Windows defaults."""
    target_path = config_path or DEFAULT_CONFIG_PATH
    user_home = Path.home()
    default_downloads = user_home / "Downloads"
    default_desktop = user_home / "Desktop"

    if target_path.is_file():
        try:
            with open(target_path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except Exception:
            raw = {}
    else:
        raw = {}

    watch_dirs_raw = raw.get("watch_dirs", [
        {
            "path": str(default_downloads),
            "mode": "categorized_subfolders",
            "target_base": str(default_downloads),
            "enabled": True,
            "ignore_extensions": []
        },
        {
            "path": str(default_desktop),
            "mode": "desktop_cleanup",
            "target_base": str(default_desktop / "Organized"),
            "enabled": True,
            "ignore_extensions": [".lnk", ".url", ".ini"]
        }
    ])

    watch_dirs: list[WatchFolderConfig] = []
    for entry in watch_dirs_raw:
        if not entry.get("enabled", True):
            continue
        p = Path(os.path.expandvars(entry["path"])).resolve()
        t = Path(os.path.expandvars(entry.get("target_base", entry["path"]))).resolve()
        watch_dirs.append(WatchFolderConfig(
            path=p,
            mode=entry.get("mode", "categorized_subfolders"),
            target_base=t,
            enabled=True,
            ignore_extensions=[ext.lower() for ext in entry.get("ignore_extensions", [])]
        ))

    categories = raw.get("categories", DEFAULT_CATEGORIES)
    temporary_extensions = [e.lower() for e in raw.get("temporary_extensions", DEFAULT_TEMPORARY_EXTENSIONS)]
    ignored_names = raw.get("ignored_names", DEFAULT_IGNORED_NAMES)
    settle_delay = float(raw.get("settle_delay_seconds", 3.0))
    poll_interval = float(raw.get("poll_interval_seconds", 2.0))

    cfg = OrganizerConfig(
        watch_dirs=watch_dirs,
        categories=categories,
        temporary_extensions=temporary_extensions,
        ignored_names=ignored_names,
        settle_delay_seconds=settle_delay,
        poll_interval_seconds=poll_interval,
    )
    return cfg


def save_default_config(target_path: Path | None = None) -> Path:
    """Write default configuration file to disk."""
    dest = target_path or DEFAULT_CONFIG_PATH
    user_home = str(Path.home())
    default_payload = {
        "watch_dirs": [
            {
                "path": str(Path.home() / "Downloads"),
                "mode": "categorized_subfolders",
                "target_base": str(Path.home() / "Downloads"),
                "enabled": True,
                "ignore_extensions": []
            },
            {
                "path": str(Path.home() / "Desktop"),
                "mode": "desktop_cleanup",
                "target_base": str(Path.home() / "Desktop" / "Organized"),
                "enabled": True,
                "ignore_extensions": [".lnk", ".url", ".ini"]
            }
        ],
        "categories": DEFAULT_CATEGORIES,
        "temporary_extensions": DEFAULT_TEMPORARY_EXTENSIONS,
        "ignored_names": DEFAULT_IGNORED_NAMES,
        "settle_delay_seconds": 3.0,
        "poll_interval_seconds": 2.0
    }
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(default_payload, f, indent=2)
    return dest
