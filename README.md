# 📁 Smart File Organizer for Windows (Downloads & Desktop)

A robust, background-capable, zero-dependency Python tool that automatically organizes files by type in `Downloads` and cleans clutter from `Desktop`.

---

## ⚡ Quick Commands

Run from command prompt or PowerShell in `C:\Users\ADITYA\tools\file-organizer`:

```powershell
# 1. Preview changes without touching files (Simulate)
python organizer.py --dry-run

# 2. Organize all loose files right now
python organizer.py --organize

# 3. Start live background watcher (auto-organizes new downloads as they finish)
python organizer.py --watch

# 4. Undo last moves (e.g. undo last 20 moves)
python organizer.py --undo 20

# 5. Check status, categories, and recent history
python organizer.py --status

# 6. Enable auto-start on Windows Boot (silent background service)
python organizer.py --install-startup

# 7. Disable auto-start on Windows Boot
python organizer.py --uninstall-startup
```

---

## 🛡️ Safety & Core Features

1. **Active Download Protection**:
   - Never touches files currently downloading (`.crdownload`, `.tmp`, `.partial`, `.part`, `.~tmp`, `.download`).
   - Checks file size stability and locks before moving.

2. **No Overwrites / Safe Collisions**:
   - If `report.pdf` already exists in `Downloads/Documents/`, it renames automatically to `report (1).pdf`, `report (2).pdf`.

3. **Desktop Shortcut Protection**:
   - Preserves all `.lnk` (app shortcuts), `.url` (browser links), and system files (`desktop.ini`).
   - Cleans loose files safely into `Desktop\Organized\<Category>`.

4. **Complete Rollback / Undo**:
   - Every single file movement is logged to `history.jsonl`.
   - Run `--undo` at any time to restore files to their exact original locations.

5. **Silent Background Execution on Windows**:
   - `start_background.vbs` can run the watcher without opening any console window.
   - `--install-startup` adds it to your Windows Startup folder seamlessly.

---

## 📂 Category Mappings (`config.json`)

* **Documents**: `.pdf`, `.doc`, `.docx`, `.txt`, `.rtf`, `.odt`, `.epub`, `.pages`, `.md`, `.tex`
* **Spreadsheets**: `.xlsx`, `.xls`, `.csv`, `.tsv`, `.ods`, `.numbers`
* **Presentations**: `.ppt`, `.pptx`, `.key`, `.odp`
* **Images**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`, `.bmp`, `.tiff`, `.ico`, `.heic`, `.psd`, `.ai`
* **Videos**: `.mp4`, `.mkv`, `.mov`, `.avi`, `.webm`, `.flv`, `.wmv`, `.m4v`, `.ts`
* **Audio**: `.mp3`, `.wav`, `.m4a`, `.flac`, `.aac`, `.ogg`, `.wma`, `.opus`
* **Archives**: `.zip`, `.rar`, `.7z`, `.tar`, `.gz`, `.bz2`, `.xz`, `.iso`, `.dmg`
* **Installers**: `.exe`, `.msi`, `.bat`, `.cmd`, `.ps1`, `.apk`, `.appx`, `.msix`
* **Code & Data**: `.py`, `.js`, `.ts`, `.html`, `.css`, `.json`, `.sql`, `.db`, `.sqlite`, `.c`, `.cpp`, `.rs`, `.go`, `.java`, `.ipynb`
* **Torrents**: `.torrent`
* **Others**: Any unmatched extension.
