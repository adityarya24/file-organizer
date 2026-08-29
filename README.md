<div align="center">

# 📁 Smart File Organizer

**A lightweight, zero-dependency, background-capable file organizer for Downloads & Desktop.**  
*Auto-categorize downloads, reduce desktop clutter, protect active downloads, and rollback any change with instant undo.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows / macOS / Linux](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero-green.svg)]()

</div>

---

## ✨ Features

- 🚀 **Zero Dependencies**: Pure Python standard library (`pathlib`, `shutil`, `winreg`, `os.scandir`). No heavy frameworks or complex wheels.
- 📂 **Multi-Directory Management**:
  - **Downloads**: Categorizes incoming files into organized subfolders (`Documents`, `Images`, `Spreadsheets`, `Installers`, `Archives`, `Videos`, `Audio`, `Code_and_Data`, etc.).
  - **Desktop Clutter Cleanup**: Cleans loose desktop files into `Desktop/Organized/<Category>` while keeping your desktop app shortcuts (`.lnk`), URLs (`.url`), and system files (`desktop.ini`) **safe and untouched**.
- ☁️ **Windows OneDrive Redirection Aware**: Automatically resolves dynamic Windows Shell Folders and redirected OneDrive Desktop paths directly from the Windows Registry.
- 🛡️ **Active Download Protection**:
  - Automatically ignores in-progress browser downloads (`.crdownload`, `.part`, `.partial`, `.tmp`, `.~tmp`, `.download`, `.aria2`, `.lock`).
  - Verifies file size stability and lock release before executing any file movement.
- 🔄 **Collision-Safe (No Overwrites)**:
  - If `statement.pdf` already exists in destination, automatically generates `statement (1).pdf`, `statement (2).pdf` instead of overwriting.
- ⏪ **Transaction Logs & Instant Undo**:
  - Every single file movement is logged to `history.jsonl` with timestamps and byte sizes.
  - Run `--undo` at any time to rollback any number of operations to their exact original locations.
- 👁️ **Dry-Run Mode**:
  - Preview exactly what files will be moved where with `--dry-run` before applying changes.
- 🔕 **Silent Background Watcher & Windows Startup**:
  - Runs in the background with minimal CPU usage (~0%).
  - One-command integration with Windows Startup (`--install-startup`) for automatic background launch on PC boot.

---

## ⚡ Quick Start

### 1. Clone & Run
```bash
git clone https://github.com/adityarya24/file-organizer.git
cd file-organizer
```

### 2. Basic Commands
```bash
# 1. Preview changes safely without moving anything
python organizer.py --dry-run

# 2. Run a one-time clean-up across Downloads and Desktop
python organizer.py --organize

# 3. Start the live background watcher
python organizer.py --watch

# 4. Undo the last 10 file movements
python organizer.py --undo 10

# 5. Check status, watched directories, and recent move history
python organizer.py --status
```

---

## 🖥️ Windows Startup Integration (Silent Background Service)

Enable the organizer to run quietly in the background on system boot:

```powershell
# Install auto-start to Windows Startup folder
python organizer.py --install-startup

# Remove auto-start from Windows Startup folder
python organizer.py --uninstall-startup
```

---

## ⚙️ Configuration (`config.json`)

The organizer automatically creates and maintains a `config.json` file. You can customize paths, categories, extensions, and polling frequencies without modifying code:

```json
{
  "watch_dirs": [
    {
      "path": "AUTO:DOWNLOADS",
      "mode": "categorized_subfolders",
      "target_base": "AUTO:DOWNLOADS",
      "enabled": true,
      "ignore_extensions": []
    },
    {
      "path": "AUTO:DESKTOP",
      "mode": "desktop_cleanup",
      "target_base": "AUTO:DESKTOP",
      "enabled": true,
      "ignore_extensions": [".lnk", ".url", ".ini"]
    }
  ],
  "categories": {
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".epub", ".pages", ".md", ".tex"],
    "Spreadsheets": [".xlsx", ".xls", ".csv", ".tsv", ".ods", ".numbers"],
    "Presentations": [".ppt", ".pptx", ".key", ".odp"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".tiff", ".ico", ".heic", ".psd"],
    "Videos": [".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v", ".ts"],
    "Audio": [".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma", ".opus"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".dmg"],
    "Installers": [".exe", ".msi", ".bat", ".cmd", ".ps1", ".apk", ".appx", ".msix", ".deb", ".rpm"],
    "Code_and_Data": [".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".sql", ".db", ".sqlite", ".pine", ".c", ".cpp", ".rs", ".go", ".java", ".ipynb"],
    "Torrents": [".torrent"]
  },
  "temporary_extensions": [
    ".crdownload", ".tmp", ".partial", ".part", ".~tmp", ".download", ".aria2", ".lock"
  ],
  "ignored_names": [
    "desktop.ini", "Thumbs.db", ".DS_Store", "Organized", "history.jsonl"
  ],
  "settle_delay_seconds": 3.0,
  "poll_interval_seconds": 2.0
}
```

---

## 🛠️ CLI Reference

| Flag | Description |
| :--- | :--- |
| `--organize` | Execute a one-time clean-up pass across all watched folders. |
| `--dry-run` | Simulate file organization and print actions without moving files. |
| `--watch` | Start continuous real-time directory watcher. |
| `--undo [N]` | Rollback the last `N` operations (default: 10). |
| `--status` | Show active directories, category counts, and recent transactions. |
| `--init-config` | Reset or generate default `config.json`. |
| `--install-startup` | Register silent watcher in Windows Startup. |
| `--uninstall-startup` | Remove watcher from Windows Startup. |

---

## 📄 License

Distributed under the [MIT License](LICENSE). Free for personal and commercial use.
