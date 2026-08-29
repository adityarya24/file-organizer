"""Core File Organizer Engine and CLI."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Any

# Ensure Windows stdout handles any unicode / emojis in filenames safely
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

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

        print(f"\n==================================================")
        print(f"  {'[DRY-RUN] ' if dry_run else ''}Organizing Files (Session: {session_id})")
        print(f"==================================================")

        for watch_cfg in self.config.watch_dirs:
            if not watch_cfg.path.exists():
                print(f"[-] Directory not found: {watch_cfg.path}")
                continue

            print(f"\n[*] Scanning: {watch_cfg.path} (Mode: {watch_cfg.mode})")
            entries = []
            try:
                with os.scandir(watch_cfg.path) as it:
                    for entry in it:
                        if entry.is_file():
                            entries.append(Path(entry.path))
            except Exception as exc:
                print(f"[-] Error scanning {watch_cfg.path}: {exc}")
                continue

            moved_in_dir = 0
            for file_path in entries:
                success, category, msg = self.process_file(
                    file_path, watch_cfg, session_id, dry_run=dry_run
                )
                if success:
                    moved_in_dir += 1
                    results["moved_count"] += 1
                    print(f"  [+] {file_path.name} -> [{category}]")
                    results["details"].append({"file": file_path.name, "category": category, "msg": msg})
                else:
                    results["skipped_count"] += 1

            if moved_in_dir == 0:
                print("  (No loose files needed organizing)")

        print(f"\n--------------------------------------------------")
        print(f"Summary: {results['moved_count']} files organized, {results['skipped_count']} skipped.")
        print(f"==================================================\n")
        return results

    def watch(self) -> None:
        """Continuous live watcher monitoring downloads and desktop."""
        print(f"\n==================================================")
        print(f"  Live Smart File Organizer (Background Watcher)")
        print(f"==================================================")
        print(f"Polling interval: {self.config.poll_interval_seconds}s | Settle delay: {self.config.settle_delay_seconds}s")
        print(f"Watching folders:")
        for w in self.config.watch_dirs:
            print(f"  - {w.path} -> {w.target_base} ({w.mode})")
        print(f"\nPress Ctrl+C to stop.\n")

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

                                # Check readiness
                                if is_file_ready_for_move(file_path, settle_delay=self.config.settle_delay_seconds):
                                    success, category, msg = self.process_file(
                                        file_path, watch_cfg, session_id=session_id, dry_run=False
                                    )
                                    if success:
                                        timestamp = time.strftime("%H:%M:%S")
                                        print(f"[{timestamp}] [+] {file_path.name} -> [{category}]")
                    except Exception as exc:
                        print(f"[-] Watch error: {exc}")

                time.sleep(self.config.poll_interval_seconds)
        except KeyboardInterrupt:
            print("\nWatcher stopped by user.")

    def undo(self, count: int = 10) -> None:
        """Undo the last N moves from history."""
        print(f"\n[*] Reverting last {count} file movements...")
        results = self.history.undo_last_moves(count=count)
        if not results:
            print("[-] No moves recorded in history to revert.")
            return

        reverted = 0
        for dest, orig, success, msg in results:
            if success:
                reverted += 1
                print(f"  [+] Restored: {Path(dest).name} -> {orig}")
            else:
                print(f"  [-] Failed: {Path(dest).name} ({msg})")

        print(f"\n[OK] Undone {reverted}/{len(results)} operations.\n")

    def status(self) -> None:
        """Show current configuration and recent history status."""
        print(f"\n==================================================")
        print(f"  File Organizer Status & Statistics")
        print(f"==================================================")
        print(f"Configured Watch Folders:")
        for w in self.config.watch_dirs:
            print(f"  - Path: {w.path}")
            print(f"    Mode: {w.mode} | Target: {w.target_base}")
            if w.ignore_extensions:
                print(f"    Ignored Exts: {', '.join(w.ignore_extensions)}")

        print(f"\nRegistered Categories ({len(self.config.categories)}):")
        for cat, exts in self.config.categories.items():
            print(f"  - {cat:16}: {', '.join(exts[:6])}{'...' if len(exts) > 6 else ''}")

        recent = self.history.get_recent_records(limit=10)
        print(f"\nRecent Move History (Last {len(recent)}):")
        if not recent:
            print("  (No recent moves logged)")
        else:
            for r in recent:
                t = r.timestamp.split("T")[1][:8] if "T" in r.timestamp else r.timestamp
                print(f"  - [{t}] {Path(r.src).name} -> [{r.category}]")
        print(f"==================================================\n")


def install_windows_startup() -> bool:
    """Create a Windows Startup VBS shortcut to launch the watcher on boot."""
    startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    if not startup_dir.is_dir():
        print(f"[-] Could not locate Windows Startup directory: {startup_dir}")
        return False

    startup_link = startup_dir / "FileOrganizerWatcher.vbs"
    script_path = Path(__file__).resolve()
    
    # Try pythonw in Python installation dir
    py_dir = Path(sys.executable).parent
    pyw_candidate = py_dir / "pythonw.exe"
    pyw_exec = str(pyw_candidate) if pyw_candidate.exists() else "pythonw.exe"

    content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "\"{pyw_exec}\" \"{script_path}\" --watch", 0, False
'''
    try:
        startup_link.write_text(content, encoding="utf-8")
        print(f"[OK] Successfully installed to Windows Startup:")
        print(f"     {startup_link}")
        print(f"     Watcher will now run automatically in the background on PC login.")
        return True
    except Exception as exc:
        print(f"[-] Failed to install startup script: {exc}")
        return False


def uninstall_windows_startup() -> bool:
    """Remove File Organizer from Windows Startup."""
    startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup_link = startup_dir / "FileOrganizerWatcher.vbs"
    if startup_link.exists():
        startup_link.unlink()
        print(f"[OK] Removed File Organizer from Windows Startup ({startup_link})")
        return True
    else:
        print("[-] File Organizer was not in Windows Startup.")
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
        print(f"[OK] Default configuration saved to: {cfg_file}")
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
        print("Use --dry-run to preview organization, --organize to run, or --watch to monitor live.")


if __name__ == "__main__":
    main()
