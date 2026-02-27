from __future__ import annotations

import os
from pathlib import Path
import json
import shutil
import re
from collections import defaultdict
from typing import Callable

from logger import logger

DB_NAME = 'files.txt'


def load_db_files(folder: str, db_name: str = DB_NAME) -> dict[str, str]:
    db_path = Path(folder) / db_name
    if not db_path.exists():
        return {}

    with open(db_path, 'r') as f:
        files_in_db = json.load(f)
    return files_in_db


def save_db_files(files: dict[str, str], folder: str, db_name: str = DB_NAME) -> None:
    db_path = Path(folder) / db_name
    with open(db_path, 'w') as f:
        json.dump(files, f, indent=4)


def sync_folder_and_db(folder: str, recursive: bool = True, dry_run: bool = True,
                       logger_func: Callable[..., None] | None = None) -> None:
    if not logger_func:
        logger_func = print
    files_in_db = load_db_files(folder)
    files_in_folder: defaultdict[str, dict] = defaultdict(dict)
    files_in_db_modified: defaultdict[str, dict] = defaultdict(dict)
    sizes: defaultdict[int, list[str]] = defaultdict(list)
    folder_path = Path(folder)
    for path, subdirs, files in os.walk(folder_path):
        for name in files:
            full_path = Path(path) / name
            size = full_path.stat().st_size
            files_in_folder[name] = {
                'path': folder,
                'size': size
                }
            sizes[size].append(str(full_path))
    logger_func(f'files in folder: {len(files_in_folder)}, sizes: {len(sizes)}')
    logger_func(f'files in DB: {len(files_in_db)}')

    for key, value in files_in_db.items():
        key_path = Path(key)
        value_path = Path(value)
        files_in_db_modified[value_path.name] = {'old_path': str(key_path.parent),
                                                  'old_name': key_path.name,
                                                  'new_path': str(value_path.parent),
                                                  'new_name': value_path.name
                                                  }
    def get_missing_in_folder() -> set[str]:
        return set(files_in_db_modified.keys()) - set(files_in_folder.keys())

    def get_missing_in_db() -> set[str]:
        return set(files_in_folder.keys()) - set(files_in_db_modified.keys())

    missing_in_folder = get_missing_in_folder()
    missing_in_db = get_missing_in_db()

    def output_missing_files() -> None:
        logger_func(f'Number of missing_in_folder: {len(missing_in_folder)}')
        logger_func('The following DB files are missing in folder')
        logger_func(f'List of files missing in folder\n{chr(10).join(missing_in_folder)}\n')

        logger_func(f'Number of files missing in DB: {len(missing_in_db)}')
        logger_func('The following DB files are missing in DB')
        logger_func(f'List of files missing in DB\n{chr(10).join(missing_in_db)}\n')

    output_missing_files()

    if dry_run:
        return

    for f in missing_in_folder:
        key_to_delete = files_in_db_modified[f]
        del files_in_db[str(Path(key_to_delete['old_path']) / key_to_delete['old_name'])]

    save_db_files(files_in_db, folder)


def organize_by_year(folder: str, dry_run: bool = True, by_month: bool = False,
                     logger_func: Callable[..., None] | None = None) -> None:
    import regex_patterns

    if not logger_func:
        logger_func = print
    folder_path = Path(folder)
    if not folder_path.exists():
        logger_func(f'Folder does not exist: {folder}')
        return

    db_files = load_db_files(folder)
    moved_count = 0
    skipped_count = 0

    # Collect files from root and from existing year (and month) subfolders
    files_to_process: list[Path] = []
    for f in folder_path.iterdir():
        if f.is_file() and f.name != DB_NAME:
            files_to_process.append(f)
    # Also scan existing year subfolders when upgrading to by_month
    if by_month:
        for year_dir in folder_path.iterdir():
            if year_dir.is_dir() and re.match(r'^\d{4}$', year_dir.name):
                for f in year_dir.iterdir():
                    if f.is_file():
                        files_to_process.append(f)

    try:
        from tqdm import tqdm
        file_iter = tqdm(files_to_process, desc='Organizing files', unit='file')
    except ImportError:
        file_iter = files_to_process

    for file_path_item in file_iter:
        match = re.match(regex_patterns.DESTINATION_REGEX, file_path_item.name)
        if not match:
            continue

        year = match.group('year')
        month = match.group('month')
        if by_month:
            target_folder = folder_path / year / month
        else:
            target_folder = folder_path / year
        new_path = target_folder / file_path_item.name

        if file_path_item == new_path:
            continue

        rel_target = new_path.relative_to(folder_path)

        if not dry_run:
            target_folder.mkdir(parents=True, exist_ok=True)
            if new_path.exists():
                logger_func(f'Skipping {file_path_item.name}, already exists in {target_folder}')
                skipped_count += 1
                continue
            shutil.move(str(file_path_item), str(new_path))

            for src_key, dst_value in list(db_files.items()):
                if Path(dst_value) == file_path_item:
                    db_files[src_key] = str(new_path)

        moved_count += 1
        logger_func(f'{"[DRY RUN] " if dry_run else ""}Moved {file_path_item.name} -> {rel_target}')

    if not dry_run and moved_count > 0:
        save_db_files(db_files, folder)

    mode = 'year/month' if by_month else 'year'
    logger_func(f'Organize by {mode}: {moved_count} files {"would be " if dry_run else ""}moved, '
                f'{skipped_count} skipped')


def generate_duplicate_report(folder: str, output_path: str | None = None,
                              dry_run: bool = True,
                              logger_func: Callable[..., None] | None = None) -> list[list[str]]:
    import filecmp

    if not logger_func:
        logger_func = print
    folder_path = Path(folder)
    if not folder_path.exists():
        logger_func(f'Folder does not exist: {folder}')
        return []

    logger_func('Scanning for duplicates...')
    sizes: defaultdict[int, list[Path]] = defaultdict(list)
    all_files = list(folder_path.rglob('*'))
    file_list = [f for f in all_files if f.is_file() and f.name != DB_NAME]

    try:
        from tqdm import tqdm
        file_iter = tqdm(file_list, desc='Indexing files by size', unit='file')
    except ImportError:
        file_iter = file_list

    for file_path_item in file_iter:
        try:
            size = file_path_item.stat().st_size
            sizes[size].append(file_path_item)
        except OSError:
            continue

    duplicate_groups: list[list[str]] = []
    size_groups = [(s, paths) for s, paths in sizes.items() if len(paths) > 1]

    try:
        from tqdm import tqdm
        group_iter = tqdm(size_groups, desc='Comparing files', unit='group')
    except ImportError:
        group_iter = size_groups

    for size, paths in group_iter:
        compared: list[list[Path]] = []
        for path_a in paths:
            placed = False
            for group in compared:
                try:
                    if filecmp.cmp(str(group[0]), str(path_a), shallow=False):
                        group.append(path_a)
                        placed = True
                        break
                except OSError:
                    continue
            if not placed:
                compared.append([path_a])
        for group in compared:
            if len(group) > 1:
                duplicate_groups.append([str(p) for p in group])

    logger_func(f'Found {len(duplicate_groups)} duplicate groups '
                f'({sum(len(g) - 1 for g in duplicate_groups)} redundant files)')

    if not output_path:
        output_path = str(Path(folder) / 'duplicate_report.html')

    _write_duplicate_report_html(duplicate_groups, output_path)
    logger_func(f'Report written to {output_path}')

    return duplicate_groups


def _write_duplicate_report_html(groups: list[list[str]], output_path: str) -> None:
    html_parts: list[str] = [
        '<!DOCTYPE html><html><head><meta charset="utf-8">',
        '<title>Duplicate Files Report</title>',
        '<style>',
        'body { font-family: sans-serif; margin: 2rem; background: #f5f5f5; }',
        'h1 { color: #333; }',
        '.summary { background: #fff; padding: 1rem; border-radius: 8px; margin-bottom: 2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }',
        '.group { background: #fff; padding: 1rem; margin-bottom: 1rem; border-radius: 8px; border-left: 4px solid #e74c3c; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }',
        '.group h3 { margin-top: 0; color: #e74c3c; }',
        '.file { font-family: monospace; padding: 0.3rem 0; font-size: 0.9rem; }',
        '.file:first-child { color: #27ae60; font-weight: bold; }',
        '.stats { color: #666; font-size: 0.85rem; margin-top: 0.5rem; }',
        '</style></head><body>',
        '<h1>Duplicate Files Report</h1>',
    ]
    total_redundant = sum(len(g) - 1 for g in groups)
    total_wasted = 0
    for g in groups:
        try:
            total_wasted += Path(g[0]).stat().st_size * (len(g) - 1)
        except OSError:
            pass
    wasted_mb = total_wasted / (1024 * 1024)
    html_parts.append(f'<div class="summary"><strong>{len(groups)}</strong> duplicate groups, '
                       f'<strong>{total_redundant}</strong> redundant files, '
                       f'<strong>{wasted_mb:.1f} MB</strong> wasted</div>')

    for i, group in enumerate(groups, 1):
        try:
            size = Path(group[0]).stat().st_size
            size_str = f'{size / 1024:.1f} KB' if size < 1024 * 1024 else f'{size / (1024 * 1024):.1f} MB'
        except OSError:
            size_str = 'unknown'
        html_parts.append(f'<div class="group"><h3>Group {i} ({len(group)} files, {size_str} each)</h3>')
        for f in group:
            html_parts.append(f'<div class="file">{f}</div>')
        html_parts.append('</div>')

    html_parts.append('</body></html>')
    Path(output_path).write_text('\n'.join(html_parts), encoding='utf-8')


def find_duplicates(folder: str, delete: bool = False,
                    logger_func: Callable[..., None] | None = None) -> list[list[str]]:
    import filecmp
    import regex_patterns

    if not logger_func:
        logger_func = print
    folder_path = Path(folder)
    if not folder_path.exists():
        logger_func(f'Folder does not exist: {folder}')
        return []

    media_extensions = set(regex_patterns.PHOTO_FILE_EXTENSIONS + regex_patterns.VIDEO_FILE_EXTENSIONS)

    logger_func('Scanning for duplicate media files...')
    all_files = list(folder_path.rglob('*'))
    media_files = [f for f in all_files if f.is_file()
                   and f.suffix.lstrip('.').lower() in media_extensions]
    logger_func(f'Found {len(media_files)} media files')

    sizes: defaultdict[int, list[Path]] = defaultdict(list)

    try:
        from tqdm import tqdm
        file_iter = tqdm(media_files, desc='Indexing by size', unit='file')
    except ImportError:
        file_iter = media_files

    for file_path_item in file_iter:
        try:
            size = file_path_item.stat().st_size
            sizes[size].append(file_path_item)
        except OSError:
            continue

    duplicate_groups: list[list[str]] = []
    size_groups = [(s, paths) for s, paths in sizes.items() if len(paths) > 1]

    try:
        from tqdm import tqdm
        group_iter = tqdm(size_groups, desc='Comparing files', unit='group')
    except ImportError:
        group_iter = size_groups

    for size, paths in group_iter:
        compared: list[list[Path]] = []
        for path_a in paths:
            placed = False
            for group in compared:
                try:
                    if filecmp.cmp(str(group[0]), str(path_a), shallow=False):
                        group.append(path_a)
                        placed = True
                        break
                except OSError:
                    continue
            if not placed:
                compared.append([path_a])
        for group in compared:
            if len(group) > 1:
                duplicate_groups.append([str(p) for p in group])

    total_redundant = sum(len(g) - 1 for g in duplicate_groups)
    total_wasted = 0
    for g in duplicate_groups:
        try:
            total_wasted += Path(g[0]).stat().st_size * (len(g) - 1)
        except OSError:
            pass
    wasted_mb = total_wasted / (1024 * 1024)

    logger_func(f'Found {len(duplicate_groups)} duplicate groups '
                f'({total_redundant} redundant files, {wasted_mb:.1f} MB wasted)')

    deleted_count = 0
    for i, group in enumerate(duplicate_groups, 1):
        kept = group[0]
        duplicates = group[1:]
        logger_func(f'{"[DRY RUN] " if not delete else ""}Group {i}: keeping {kept}')
        for dup in duplicates:
            logger_func(f'  {"[DRY RUN] would delete" if not delete else "Deleting"}: {dup}')
            if delete:
                try:
                    Path(dup).unlink()
                    deleted_count += 1
                except OSError as e:
                    logger_func(f'  Failed to delete {dup}: {e}')

    if delete:
        logger_func(f'Deleted {deleted_count} duplicate files, freed ~{wasted_mb:.1f} MB')
    else:
        logger_func(f'[DRY RUN] {total_redundant} files would be deleted, '
                    f'~{wasted_mb:.1f} MB would be freed')

    return duplicate_groups


def move_files(folder: str, new_folder: str, regex_pattern: str = r'.*\.\w{2,4}',
               create_subfolder: bool = True, dry_run: bool = True) -> None:
    db_files = load_db_files(folder)
    new_folder_db_files: dict[str, str] = {}
    old_folder_db_files = dict(db_files)
    folder_path = Path(folder)
    dest_folder = folder_path / new_folder if create_subfolder else Path(new_folder)
    if not dest_folder.exists():
        dest_folder.mkdir(parents=True)

    print(regex_pattern)
    regex = re.compile(regex_pattern)
    for source_name, current_name in db_files.items():
        old_basename = Path(source_name).name
        new_basename = Path(current_name).name
        if regex.match(old_basename):
            new_name = str(dest_folder / new_basename)
            new_folder_db_files[source_name] = new_name
            del old_folder_db_files[source_name]
            if not dry_run:
                shutil.move(current_name, new_name)

    logger.info(json.dumps(new_folder_db_files, indent=4))
    logger.info(f'handled files names {len(new_folder_db_files)}')
    if not dry_run:
        save_db_files(old_folder_db_files, folder)
        save_db_files(new_folder_db_files, str(dest_folder))
