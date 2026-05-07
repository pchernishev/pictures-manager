# Pictures Manager

A CLI-based photo/video organizer written in Python.
It scans a source folder for media files, extracts date metadata, renames them into a standardized format (`YYYYMMDD_HHMMSS_NNN.ext`), and moves them to a destination folder — with duplicate detection and a JSON-based tracking database.

## Requirements

- Python 3.10+
- `Pillow>=10.0.0`
- `tqdm>=4.60.0`

Install dependencies:
```bash
pip install -r requirements.txt
```

## Basic Usage

```bash
python picture_handler.py --src /path/to/source --dst /path/to/destination
```

This scans the source folder, matches media files against known filename patterns, extracts dates, renames them, and moves them to the destination.

## CLI Arguments

### Core Options

| Flag | Short | Description |
|------|-------|-------------|
| `--src` | `-s` | Source folder to scan |
| `--dst` | `-d` | Destination folder for organized files |
| `--compare` | `-c` | Duplicate detection methods: `name`, `binary`, `size` (space-separated) |
| `--ignore` | `-i` | Regex patterns for filenames to skip |
| `--accept` | `-a` | Regex patterns for filenames to include (presets: `default`, `mobile`, `camera`) |
| `--not-recursive` | `--nr` | Disable recursive scanning (default is recursive) |
| `--dry-run` | `--dr` | Preview all operations without moving or modifying any files |
| `--by-month` | `--bm` | Organize files into month subfolders within year folders (e.g. `dst/2020/03/`) |

### Folder Organization

| Flag | Short | Description |
|------|-------|-------------|
| `--organize-by-year` | `--oby` | Move existing destination files into year subfolders (e.g. `dst/2020/`, `dst/2021/`) |
| `--by-month` | `--bm` | When combined with `--organize-by-year`, creates month subfolders (e.g. `dst/2020/03/`) |

### DB Sync & Migration

| Flag | Short | Description |
|------|-------|-------------|
| `--sync-folder-and-db` | `--sync` | Reconcile the DB with folder contents — removes DB entries for missing files, reports files not in DB |
| `--convert-db` | `--cdb` | Migrate DB from old format (full paths) to new format (filenames + size) |
| `--merge-db DB_FILE` | `--mdb` | Merge a second DB file into the destination DB (see [Merging DBs](#merging-dbs)) |

### Duplicate Detection & Cleanup

| Flag | Short | Description |
|------|-------|-------------|
| `--duplicate-report` | `--dupes` | Generate an HTML report of duplicate files in the destination folder |
| `--find-duplicates` | `--fd` | Scan destination for duplicate media files (dry run by default) |
| `--delete-duplicates` | `--dd` | Actually delete duplicates found by `--find-duplicates` (keeps one copy) |
| `--keep-strategy` | `--ks` | Strategy for choosing which duplicate to keep: `folder_priority`, `shortest_path`, `oldest` |
| `--keep-folder` | `--kf` | Preferred folder path for the `folder_priority` strategy |

**Keep strategies:**
- **folder_priority** — Keep the copy in the folder specified by `--keep-folder`, delete others
- **shortest_path** — Keep the file with the shallowest path (fewest directory levels)
- **oldest** — Keep the file with the earliest modification timestamp

### Folder Comparison

| Flag | Short | Description |
|------|-------|-------------|
| `--compare-folders FOLDER_A FOLDER_B` | `--cf` | Compare two folders and report files only in A, only in B, and optionally files with different content |
| `--compare-content` | `--cc` | Also compare file content (binary) for files present in both folders |
| `--compare-output FILE` | `--co` | Write the comparison report to a file |

## Date Extraction Strategy

The tool extracts dates from media files using a priority chain:

1. **EXIF** — For image files, reads `DateTimeOriginal` (tag 36867) via PIL
2. **Filename regex** — Falls back to parsing date/time from the filename using known patterns (mobile, camera, etc.)
3. **File system timestamps** — Uses the minimum of `atime`, `mtime`, `ctime`

The earliest date found is used to generate the standardized filename: `YYYYMMDD_HHMMSS_NNN.ext`

## Database Format

The tracking database (`files.txt`) is a JSON file stored in the destination folder.

```json
{
    "20200315_143022_000.jpg": {"source_name": "IMG_001.jpg", "size": 12345},
    "20210601_080000_000.jpg": {"source_name": "DSC_1234.jpg", "size": 67890}
}
```

- **Key** — Destination filename (guaranteed unique by the `YYYYMMDD_HHMMSS_NNN` naming scheme)
- **source_name** — Original filename from the source folder
- **size** — File size in bytes

### Merging DBs

When consolidating two destination folders into one:

1. Move all files from folder B into folder A
2. Run: `python picture_handler.py -s /any -d /folderA --merge-db /folderB/files.txt`

The merge handles three scenarios:
- **No conflict** (key only in one DB) — merged directly
- **Same key + same size** — binary comparison; if identical, keeps one entry and deletes the duplicate file
- **Same key + different size** (or different content) — keeps both; renames the conflicting entry by incrementing the filename suffix (`_000` → `_001` → `_002`, etc.) and renames the file on disk accordingly

Use `--dry-run` to preview all conflicts and duplicates before committing changes.

## Supported Media Types

- **Photos:** jpg, jpeg, png, nef, gif, dng
- **Videos:** mp4, mov, avi, mkv, wmv, flv, webm, and [300+ additional formats](regex_patterns.py)
