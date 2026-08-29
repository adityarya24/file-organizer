"""Core File Organizer Engine and CLI."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
import traceback
import uuid
from pathlib import Path
from typing import Any

# Ensure script directory is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

LOG_FILE = SCRIPT_DIR / "watcher.log"

def safe_log(msg: str, console_only: bool = False) -> None:
    """Safe logging that never crashes on detached Windows standard handles."""
    try:
        if sys.stdout is not None:
            print(msg, flush=True)
    except Exception:
        pass

    if not console_only:
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {msg}\n")
        except Exception:
            pass

# Ensure Windows stdout handles any unicode safely if present
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)
except Exception:
    pass

from config import OrganizerConfig, WatchFolderConfig, load_config, save_default_config
from history import HistoryManager
from rules import (
    classify_file,
    get_unique_destination,
    is_file_ready_for_move,
    should_ignore_file,
)


class FileOrganizer:
    """Core organizer orchestrating scans, moves, watchers, and undo operations."""

    def __init__(self, config: OrganizerConfig | None = None) -> None:
        self.config = config or load_config()
        self.history = HistoryManager()

    def process_file(
        self,
        file_path: Path,
        watch_cfg: WatchFolderConfig,
        session_id: str,
        dry_run: bool = False
    ) -> tuple[bool, str, str]:
        """
        Process an individual file: classify, resolve destination, check lock, move, and log.
        Returns: (success, category, message)
        """
        if not file_path.is_file():
            return False, "", "Not a regular file"

        if should_ignore_file(file_path, self.config, watch_cfg):
            return False, "", "Ignored by filter rules"

        category = classify_file(file_path, self.config)

        # Determine target folder
        if watch_cfg.mode == "desktop_cleanup":
            # Clean into Desktop/Organized/<Category>
            target_dir = watch_cfg.target_base / category
        else:
            # Downloads/<Category>
            target_dir = watch_cfg.target_base / category

        if not dry_run and not is_file_ready_for_move(file_path, self.config.settle_delay_seconds):
            return False, category, "File is still downloading or locked"

        dest_path = get_unique_destination(target_dir, file_path.name)

        if dry_run:
            return True, category, f"[DRY-RUN] Would move -> {dest_path}"

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            file_size = file_path.stat().st_size
            shutil.move(str(file_path), str(dest_path))
            self.history.log_move(
                session_id=session_id,
                src=file_path,
                dest=dest_path,
                category=category,
                size_bytes=file_size,
            )
            return True, category, f"Moved -> {dest_path.name} in [{category}]"
        except Exception as exc:
            return False, category, f"Failed to move: {exc}"

    def organize_all(self, dry_run: bool = False) -> dict[str, Any]:
        """Run a full scan and organization pass across all configured watch folders."""
        session_id = str(uuid.uuid4())[:8]
        results: dict[str, Any] = {
            "session_id": session_id,
            "dry_run": dry_run,
            "moved_count": 0,
            "skipped_count": 0,
            "details": []
        }

        safe_log(f"\n==================================================", console_only=True)
        safe_log(f"  {'[DRY-RUN] ' if dry_run else ''}Organizing Files (Session: {session_id})", console_only=True)
        safe_log(f"==================================================", console_only=True)

        for watch_cfg in self.config.watch_dirs:
            if not watch_cfg.path.exists():
                safe_log(f"[-] Directory not found: {watch_cfg.path}", console_only=True)
                continue

            safe_log(f"\n[*] Scanning: {watch_cfg.path} (Mode: {watch_cfg.mode})", console_only=True)
            entries = []
            try:
                with os.scandir(watch_cfg.path) as it:
                    for entry in it:
                        if entry.is_file():
                            entries.append(Path(entry.path))
            except Exception as exc:
                safe_log(f"[-] Error scanning {watch_cfg.path}: {exc}", console_only=True)
                continue

            moved_in_dir = 0
            for file_path in entries:
                success, category, msg = self.process_file(
                    file_path, watch_cfg, session_id, dry_run=dry_run
                )
                if success:
                    moved_in_dir += 1
                    results["moved_count"] += 1
                    safe_log(f"  [+] {file_path.name} -> [{category}]")
                    results["details"].append({"file": file_path.name, "category": category, "msg": msg})
                else:
                    results["skipped_count"] += 1

            if moved_in_dir == 0:
                safe_log("  (No loose files needed organizing)", console_only=True)

        safe_log(f"\n--------------------------------------------------", console_only=True)
        safe_log(f"Summary: {results['moved_count']} files organized, {results['skipped_count']} skipped.", console_only=True)
        safe_log(f"==================================================\n", console_only=True)
        return results

    def watch(self) -> None:
        """Continuous live watcher monitoring downloads and desktop."""
        safe_log("==================================================")
        safe_log("  Live Smart File Organizer (Background Watcher Started)")
        safe_log("==================================================")
        safe_log(f"Polling interval: {self.config.poll_interval_seconds}s | Settle delay: {self.config.settle_delay_seconds}s")
        for w in self.config.watch_dirs:
            safe_log(f"  - Watching: {w.path} -> {w.target_base} ({w.mode})")

        try:
            while True:
                session_id = f"watch_{int(time.time())}"
                for watch_cfg in self.config.watch_dirs:
                    if not watch_cfg.path.exists():
                        continue

                    try:
                        with os.scandir(watch_cfg.path) as it:
                            for entry in it:
                                if not entry.is_file():
                                    continue
                                file_path = Path(entry.path)
                                if should_ignore_file(file_path, self.config, watch_cfg):
                                    continue

                                # Check readiness & process
                                success, category, msg = self.process_file(
                                    file_path, watch_cfg, session_id=session_id, dry_run=False
                                )
                                if success:
                                    safe_log(f"[+] {file_path.name} -> [{category}]")
                    except Exception as exc:
                        safe_log(f"[-] Watch error: {exc}")

                time.sleep(self.config.poll_interval_seconds)
        except KeyboardInterrupt:
            safe_log("Watcher stopped by user.")
        except BaseException as fatal_exc:
            safe_log(f"Fatal watcher exception: {type(fatal_exc).__name__}: {fatal_exc}\n{traceback.format_exc()}")

    def undo(self, count: int = 10) -> None:
        """Undo the last N moves from history."""
        safe_log(f"\n[*] Reverting last {count} file movements...", console_only=True)
        results = self.history.undo_last_moves(count=count)
        if not results:
            safe_log("[-] No moves recorded in history to revert.", console_only=True)
            return

        reverted = 0
        for dest, orig, success, msg in results:
            if success:
                reverted += 1
                safe_log(f"  [+] Restored: {Path(dest).name} -> {orig}", console_only=True)
            else:
                safe_log(f"  [-] Failed: {Path(dest).name} ({msg})", console_only=True)

        safe_log(f"\n[OK] Undone {reverted}/{len(results)} operations.\n", console_only=True)

    def status(self) -> None:
        """Show current configuration and recent history status."""
        safe_log(f"\n==================================================", console_only=True)
        safe_log(f"  File Organizer Status & Statistics", console_only=True)
        safe_log(f"==================================================", console_only=True)
        safe_log(f"Configured Watch Folders:", console_only=True)
        for w in self.config.watch_dirs:
            safe_log(f"  - Path: {w.path}", console_only=True)
            safe_log(f"    Mode: {w.mode} | Target: {w.target_base}", console_only=True)
            if w.ignore_extensions:
                safe_log(f"    Ignored Exts: {', '.join(w.ignore_extensions)}", console_only=True)

        safe_log(f"\nRegistered Categories ({len(self.config.categories)}):", console_only=True)
        for cat, exts in self.config.categories.items():
            safe_log(f"  - {cat:16}: {', '.join(exts[:6])}{'...' if len(exts) > 6 else ''}", console_only=True)

        recent = self.history.get_recent_records(limit=10)
        safe_log(f"\nRecent Move History (Last {len(recent)}):", console_only=True)
        if not recent:
            safe_log("  (No recent moves logged)", console_only=True)
        else:
            for r in recent:
                t = r.timestamp.split("T")[1][:8] if "T" in r.timestamp else r.timestamp
                safe_log(f"  - [{t}] {Path(r.src).name} -> [{r.category}]", console_only=True)
        safe_log(f"==================================================\n", console_only=True)


def install_windows_startup() -> bool:
    """Create a Windows Startup VBS shortcut to launch the watcher on boot."""
    startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    if not startup_dir.is_dir():
        safe_log(f"[-] Could not locate Windows Startup directory: {startup_dir}", console_only=True)
        return False

    startup_link = startup_dir / "FileOrganizerWatcher.vbs"
    script_path = Path(__file__).resolve()
    py_exec = sys.executable

    content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "{py_exec}" & chr(34) & " " & chr(34) & "{script_path}" & chr(34) & " --watch", 0, False
'''
    try:
        startup_link.write_text(content, encoding="utf-8")
        safe_log(f"[OK] Successfully installed to Windows Startup:", console_only=True)
        safe_log(f"     {startup_link}", console_only=True)
        safe_log(f"     Watcher will now run automatically in the background on PC login.", console_only=True)
        return True
    except Exception as exc:
        safe_log(f"[-] Failed to install startup script: {exc}", console_only=True)
        return False


def uninstall_windows_startup() -> bool:
    """Remove File Organizer from Windows Startup."""
    startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup_link = startup_dir / "FileOrganizerWatcher.vbs"
    if startup_link.exists():
        startup_link.unlink()
        safe_log(f"[OK] Removed File Organizer from Windows Startup ({startup_link})", console_only=True)
        return True
    else:
        safe_log("[-] File Organizer was not in Windows Startup.", console_only=True)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smart File Organizer for Downloads & Desktop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--organize", action="store_true", help="Run a one-time clean-up across all folders"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate organization without moving any files"
    )
    parser.add_argument(
        "--watch", action="store_true", help="Run background watcher for new downloads and files"
    )
    parser.add_argument(
        "--undo", type=int, nargs="?", const=10, help="Undo the last N moves (default: 10)"
    )
    parser.add_argument(
        "--status", action="store_true", help="Show current rules and recent move history"
    )
    parser.add_argument(
        "--init-config", action="store_true", help="Generate or reset config.json"
    )
    parser.add_argument(
        "--install-startup", action="store_true", help="Enable auto-start with Windows"
    )
    parser.add_argument(
        "--uninstall-startup", action="store_true", help="Disable auto-start with Windows"
    )

    args = parser.parse_args()

    if args.init_config:
        cfg_file = save_default_config()
        safe_log(f"[OK] Default configuration saved to: {cfg_file}", console_only=True)
        return

    if args.install_startup:
        install_windows_startup()
        return

    if args.uninstall_startup:
        uninstall_windows_startup()
        return

    organizer = FileOrganizer()

    if args.undo is not None:
        organizer.undo(count=args.undo)
    elif args.status:
        organizer.status()
    elif args.watch:
        organizer.watch()
    elif args.organize or args.dry_run:
        organizer.organize_all(dry_run=args.dry_run)
    else:
        organizer.status()
        safe_log("Use --dry-run to preview organization, --organize to run, or --watch to monitor live.", console_only=True)


if __name__ == "__main__":
    main()
