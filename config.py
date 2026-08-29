"""Configuration manager for File Organizer."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.json"


def get_windows_shell_folder(folder_name: str, fallback_name: str) -> Path:
    """Dynamically resolve Windows Shell Folder paths (supporting OneDrive redirection)."""
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            )
            raw_path, _ = winreg.QueryValueEx(key, folder_name)
            expanded = os.path.expandvars(raw_path)
            if os.path.isdir(expanded):
                return Path(expanded).resolve()
        except Exception:
            pass
    fallback = Path.home() / fallback_name
    return fallback.resolve()


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
        ".sql", ".db", ".sqlite", ".pine", ".c", ".cpp", ".h", ".hpp", ".rs", ".go", ".java", ".kt", ".swift",
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
        ext_map: dict[str, str] = {}
        for category, exts in self.categories.items():
            for ext in exts:
                cleaned = ext.strip().lower()
                if not cleaned.startswith("."):
                    cleaned = f".{cleaned}"
                ext_map[cleaned] = category
        self.extension_map = ext_map


def load_config(config_path: Path | None = None) -> OrganizerConfig:
    """Load configuration from JSON or use dynamically detected Windows folders."""
    target_path = config_path or DEFAULT_CONFIG_PATH
    real_desktop = get_windows_shell_folder("Desktop", "Desktop")
    real_downloads = get_windows_shell_folder("{374DE290-123F-4565-9164-39C4925E467B}", "Downloads")
    default_desktop = Path.home() / "Desktop"

    if target_path.is_file():
        try:
            with open(target_path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except Exception:
            raw = {}
    else:
        raw = {}

    watch_dirs_raw = raw.get("watch_dirs")
    if not watch_dirs_raw:
        # Dynamically build default directories
        watch_dirs = [
            WatchFolderConfig(
                path=real_downloads,
                mode="categorized_subfolders",
                target_base=real_downloads,
                enabled=True,
                ignore_extensions=[]
            ),
            WatchFolderConfig(
                path=real_desktop,
                mode="desktop_cleanup",
                target_base=real_desktop / "Organized",
                enabled=True,
                ignore_extensions=[".lnk", ".url", ".ini"]
            )
        ]
        # Also watch standard Desktop if different from redirected one
        if default_desktop.is_dir() and default_desktop.resolve() != real_desktop:
            watch_dirs.append(
                WatchFolderConfig(
                    path=default_desktop.resolve(),
                    mode="desktop_cleanup",
                    target_base=default_desktop.resolve() / "Organized",
                    enabled=True,
                    ignore_extensions=[".lnk", ".url", ".ini"]
                )
            )
    else:
        watch_dirs = []
        for entry in watch_dirs_raw:
            if not entry.get("enabled", True):
                continue
            raw_p = entry["path"]
            # Auto-substitute Desktop with real active desktop if configured as standard desktop
            p = Path(os.path.expandvars(raw_p)).resolve()
            if p == default_desktop.resolve() and real_desktop != default_desktop.resolve():
                p = real_desktop

            raw_t = entry.get("target_base", entry["path"])
            t = Path(os.path.expandvars(raw_t)).resolve()
            if t == (default_desktop / "Organized").resolve() and real_desktop != default_desktop.resolve():
                t = real_desktop / "Organized"

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

    return OrganizerConfig(
        watch_dirs=watch_dirs,
        categories=categories,
        temporary_extensions=temporary_extensions,
        ignored_names=ignored_names,
        settle_delay_seconds=settle_delay,
        poll_interval_seconds=poll_interval,
    )


def save_default_config(target_path: Path | None = None) -> Path:
    """Write default configuration file to disk with resolved active paths."""
    dest = target_path or DEFAULT_CONFIG_PATH
    real_desktop = get_windows_shell_folder("Desktop", "Desktop")
    real_downloads = get_windows_shell_folder("{374DE290-123F-4565-9164-39C4925E467B}", "Downloads")

    default_payload = {
        "watch_dirs": [
            {
                "path": str(real_downloads),
                "mode": "categorized_subfolders",
                "target_base": str(real_downloads),
                "enabled": True,
                "ignore_extensions": []
            },
            {
                "path": str(real_desktop),
                "mode": "desktop_cleanup",
                "target_base": str(real_desktop / "Organized"),
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
        json.dump(default_payload, f, indent=2, ensure_ascii=False)
    return dest
