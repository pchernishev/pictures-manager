#!/usr/bin/python

from __future__ import annotations

import re
import filecmp
from pathlib import Path
from argparse import ArgumentParser, Namespace
from collections import defaultdict
from shutil import move
import json
from PIL import Image
from datetime import datetime
from logger import logger
import logging
import regex_patterns
import comparing
import utils

DATE_TIME_ORIGINAL_KEY = 36867


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    logging.getLogger("PIL.TiffImagePlugin").setLevel(logging.INFO)

    logger.info('Handling started')
    handler = PicturesHandler(args.src, args.dst, comparers=args.compare, ignore_regexs=args.ignore,
                              dry_run=args.dry_run, recursive=args.recursive, accept_regexs=args.accept,
                              by_month=args.by_month)
    if args.sync:
        utils.sync_folder_and_db(str(handler.dst), handler.recursive, handler.dry_run, logger.info)
        return

    if args.organize_by_year:
        utils.organize_by_year(str(handler.dst), dry_run=args.dry_run, by_month=args.by_month,
                               logger_func=logger.info)
        return

    if args.duplicate_report:
        utils.generate_duplicate_report(str(handler.dst), logger_func=logger.info)
        return

    if args.find_duplicates:
        utils.find_duplicates(str(handler.dst), delete=args.delete_duplicates, logger_func=logger.info)
        return

    handler.handle()
    handler.output()
    logger.info('Handling finished\n')


def create_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Pictures Handler parameters")
    parser.add_argument("--src", '-s', dest="src", type=str, help="Folder to parse")
    parser.add_argument("--dst", '-d', dest="dst", type=str, help="Folder copy pictures to")
    parser.add_argument('--compare', '-c', dest='compare', type=str, nargs='+',
                        help=f'Methods for comparing pictures, separated by whitespace.\n'
                        f'Already handled picture will be ignored.\n'
                        f'Possible Compare methods: {comparing.AVAILABLE_COMPARERS.keys()}')
    parser.add_argument('--ignore', '-i', dest='ignore', type=str, nargs='+',
                        help='Regexs surrounded by " for picture names to ignore, separated by whitespace')
    parser.add_argument('--accept', '-a', dest='accept', type=str, nargs='+',
                        help='Regexs surrounded by " for picture names to accept, separated by whitespace.\n'
                        'In case parameter not specified all files accepted.\n'
                        'preset "default" "camera" "mobile" regex can be specified')
    parser.add_argument('--not-recursive', '--nr', dest='recursive', action='store_true', default=True)
    parser.add_argument('--dry-run', '--dr', dest='dry_run', action='store_true', default=False)
    parser.add_argument('--sync-folder-and-db', '--sync', dest='sync', action='store_true', default=False)
    parser.add_argument('--organize-by-year', '--oby', dest='organize_by_year', action='store_true', default=False,
                        help='Reorganize existing destination files into year subfolders (e.g. dst/2020/, dst/2021/)')
    parser.add_argument('--by-month', '--bm', dest='by_month', action='store_true', default=False,
                        help='Organize files into month subfolders within year folders (e.g. dst/2020/03/)')
    parser.add_argument('--duplicate-report', '--dupes', dest='duplicate_report', action='store_true', default=False,
                        help='Generate an HTML report of duplicate files in the destination folder')
    parser.add_argument('--find-duplicates', '--fd', dest='find_duplicates', action='store_true', default=False,
                        help='Scan destination folder and subfolders for duplicate media files (dry run by default)')
    parser.add_argument('--delete-duplicates', '--dd', dest='delete_duplicates', action='store_true', default=False,
                        help='Actually delete duplicate media files found by --find-duplicates (keeps one copy)')
    return parser


class PicturesHandler:

    def __init__(self, src: str, dst: str, comparers: list[str] | None = None,
                 ignore_regexs: list[str] | None = None, dry_run: bool = False,
                 recursive: bool = False, accept_regexs: list[str] | None = None,
                 sync: bool = False, db_path: str = 'files.txt',
                 by_month: bool = False) -> None:
        if not src or not dst:
            raise ValueError('Mandatory parameter source folder or destination folder is missing')
        src_path = Path(src)
        if not src_path.exists():
            raise FileNotFoundError(f'Source folder does not exist: {src_path}')
        if not src_path.is_dir():
            raise NotADirectoryError(f'Source path is not a directory: {src_path}')
        self.comparers: dict[str, comparing.Comparer] = {}
        if comparers:
            self.comparers = {c: comparing.get_comparer(c) for c in comparers}

        self.src = src_path
        self.dst = Path(dst)
        self.db_path = db_path
        self.recursive = recursive
        self.dry_run = dry_run
        self.ignore_regexs = [re.compile(rf'{regex}') for regex in ignore_regexs] if ignore_regexs else []
        self.sync_folder_and_db = sync
        self.by_month = by_month

        if accept_regexs:
            if 'default' in accept_regexs:
                accept_regexs.remove('default')
                accept_regexs += regex_patterns.ACCEPTABLE_REGEXS
            if 'mobile' in accept_regexs:
                accept_regexs.remove('mobile')
                accept_regexs.append(regex_patterns.ACCEPTABLE_REGEXS[0])
            if 'camera' in accept_regexs:
                accept_regexs.remove('camera')
                accept_regexs.append(regex_patterns.ACCEPTABLE_REGEXS[1])

        self.acceptable_regexs = [re.compile(rf'{regex}') for regex in accept_regexs] if accept_regexs else []

        self.db_files: dict[str, str] = {}
        self.all_handled_names: list[str] = []
        self.ignored: list[str] = []
        self.sizes_files: defaultdict[int, list[str]] = defaultdict(list)
        self.matched: defaultdict[str, list[dict]] = defaultdict(list)
        self.matched_regex: list[str] = []
        self.unmatched: list[str] = []
        self.not_passed_comparison: list[tuple[str, str]] = []
        self.destination_formats: defaultdict[str, list[dict]] = defaultdict(list)
        self.destination_not_matched: list[str] = []
        self.ready_to_add: defaultdict[str, list[dict]] = defaultdict(list)
        self.added_files: list[str] = []
        self.moved: dict[str, str] = {}
        self.unmoved: dict[str, str] = {}
        self.not_deleted: list[tuple[str, str]] = []
        self.min_date_taken: list[tuple[str, dict]] = []
        self.unsupported: list[str] = []
        self.num_of_dst_files: int = 0

    def output(self) -> None:
        logger.info(f'*****Total {self.num_of_dst_files} files found at destination directory {self.dst}\n')
        logger.info(f'*****Total {len(self.destination_formats)} formats found at destination directory')
        logger.info(f'*****Total {sum(len(val) for val in self.destination_formats.values())} '
                    f'files found and matched at destination directory {self.dst}')
        logger.info(f'*****Total {len(self.destination_not_matched)} '
                    f'files found but not matched at destination directory\n')
        for item in self.destination_not_matched:
            logger.info(f'Destination Not Matched: {item}')

        logger.info('\n')
        logger.info(f'*****Total {len(self.unmatched)} files weren\'t matched\n')
        for item in self.unmatched:
            logger.info(f'Unmatched  {item}')

        logger.info(f'*****Total {len(self.not_passed_comparison)} files matched not pass comparison\n')
        for item in self.not_passed_comparison:
            logger.info(f'Not passed compare {item[1]}')

        logger.info(f'*****Total {len(self.ignored)} files were ignored\n')
        for item in self.ignored:
            logger.info(f'{item}')

        logger.info(f'*****Total {len(self.min_date_taken)} files new name created by taken min date\n')

        logger.info(f'*****Total {len(self.unsupported)} files are of unsupported type\n')
        for item in self.unsupported:
            logger.info(f'{item}')

        counter = 0
        for key, matches in self.matched.items():
            for match in matches:
                counter += 1
        logger.info(f'*****Total {counter} files matched\n')

        logger.info('*****Following files are ready to be added')
        counter = 0
        for key, matches in self.ready_to_add.items():
            if len(matches) > 1:
                logger.info(f'***Ready group: {key}')
            for match in matches:
                counter += 1
                indent = '\t' if len(matches) > 1 else ''
                logger.info(f'{indent}Ready File: {match["file"]}, New File Name: {match["new_file_name"]}')
        logger.info(f'*****Total {counter} files ready to be added\n')

        if not self.dry_run:
            logger.info(f'*****Total {len(self.unmoved)} files failed to be moved\n')
            if len(self.unmoved) > 0:
                logger.info('*****Following files failed to be moved')
                for item, reason in self.unmoved.items():
                    logger.info(f'Unmoved. {item}. {reason}')

            logger.info(f'*****Total {len(self.not_deleted)} files weren\'t deleted\n')
            if len(self.not_deleted) > 0:
                logger.info('*****Following files failed to be deleted')
                for f in self.not_deleted:
                    logger.info(f'Not deleted {f[0]}. Reason: {f[1]}')

            logger.info(f'*****Total {len(self.moved)} files were moved to {self.dst}\n')
            logger.info('******Moved files dict')
            logger.info(json.dumps(self.moved, indent=4))

    def handle(self) -> None:
        self._load_db()
        self._handle_destination_folder(self.dst)
        self._handle_source_folder(self.src, self.recursive)
        self._prepare_new_files_for_copy()
        if not self.dry_run:
            self._move_prepared_files()
            self._update_db()
            self._delete_not_added()

    def _load_db(self) -> None:
        self.db_files = utils.load_db_files(str(self.dst))
        for src, dst in self.db_files.items():
            self.all_handled_names += [Path(src).name, Path(dst).name]

    def _delete_not_added(self) -> None:
        for f in self.not_passed_comparison:
            try:
                Path(f[0]).unlink()
            except OSError as e:
                self.not_deleted.append((f[0], f'Error {e.__class__.__name__} {e}'))

    def _update_db(self) -> None:
        self.db_files.update(self.moved)
        utils.save_db_files(self.db_files, str(self.dst), 'files.txt')

    def _prepare_new_files_for_copy(self) -> None:
        def get_new_filename() -> str:
            return regex_patterns.NEW_FILE_FORMAT.format(
                regex_patterns.DESTINATION_FORMAT_NO_SUFFIX_NO_EXTENSION.format(**match).replace(
                    'None', '00'), suffix, **match)

        def get_new_suffix(file_props_list: list[dict]) -> str:
            return regex_patterns.NEW_SUFFIX_FORMAT.format(
                max(int(props['suffix']) for props in file_props_list) + 1)

        for key, matched in self.matched.items():
            for match in matched:
                logger.info(f'match {match}')
                file_format = regex_patterns.DESTINATION_FORMAT_NO_SUFFIX.format(**match).replace('None', '00')
                if file_format not in list(self.destination_formats) + list(self.ready_to_add):
                    suffix = '000'
                elif file_format in self.ready_to_add:
                    suffix = get_new_suffix(self.ready_to_add[file_format])
                else:  # file_format in self.destination_formats
                    suffix = get_new_suffix(self.destination_formats[file_format])
                match['suffix'] = suffix
                match['new_file_name'] = get_new_filename()
                self.ready_to_add[file_format].append(match)

    def _update_common_file_props(self, file: str, folder: str | Path) -> dict:
        full_path = Path(folder) / file
        return {
            'fullpath': str(full_path),
            'folder': str(folder),
            'size': full_path.stat().st_size,
            'file': file,
            'extension': full_path.suffix.lstrip('.').lower(),
        }

    def _handle_destination_folder(self, folder: str | Path, recursive: bool = False) -> None:
        folder_path = Path(folder)
        if not folder_path.exists():
            folder_path.mkdir(parents=True)

        # Always scan year subfolders (4-digit) and month subfolders (2-digit)
        date_dirs = [d for d in folder_path.iterdir() if d.is_dir() and
                     re.match(r'^\d{2,4}$', d.name)]
        for d in date_dirs:
            self._handle_destination_folder(d)

        if recursive:
            other_dirs = [d for d in folder_path.iterdir() if d.is_dir() and
                          not re.match(r'^\d{4}$', d.name) and
                          str(d).lower() != str(self.src).lower()]
            for d in other_dirs:
                self._handle_destination_folder(d)

        files = [f.name for f in folder_path.iterdir() if f.is_file()]
        self.num_of_dst_files += len(files)
        counter_of_matched = 0
        for f in files:
            match = re.match(regex_patterns.DESTINATION_REGEX, f)
            if not match:
                self.destination_not_matched.append(f)
                continue
            else:
                counter_of_matched += 1

            properties = self._update_common_file_props(f, folder_path)
            properties.update(match.groupdict())
            # Create key with no suffix
            key = regex_patterns.DESTINATION_FORMAT_NO_SUFFIX.format(**properties)
            self.destination_formats[key].append(properties)
            self.sizes_files[properties['size']].append(properties['fullpath'])
        self.num_of_dst_matched_files = counter_of_matched

    @staticmethod
    def _is_image(file_path: str) -> bool:
        try:
            with Image.open(file_path) as img:
                img.verify()
            return True
        except Exception:
            return False

    def _handle_source_folder(self, folder: str | Path, recursive: bool) -> None:
        folder_path = Path(folder)
        if recursive:
            dirs = [d for d in folder_path.iterdir() if d.is_dir() and
                    str(d).lower() != str(self.dst).lower()]
            for d in dirs:
                self._handle_source_folder(d, recursive)
        files = [f.name for f in folder_path.iterdir() if f.is_file()]

        try:
            from tqdm import tqdm
            file_iter = tqdm(files, desc=f'Scanning {folder_path.name}', unit='file')
        except ImportError:
            file_iter = files

        for f in file_iter:
            if any(regex.match(f) for regex in self.ignore_regexs):
                self.ignored.append(f'{f}. Folder: {folder_path}')
                continue

            if self.acceptable_regexs and not any(re.match(_regex, f) for _regex in self.acceptable_regexs):
                self.unmatched.append(str(folder_path / f))
                continue

            properties = self._update_common_file_props(f, folder_path)
            full_path = properties['fullpath']
            size = properties['size']
            # Photo file
            if self._is_image(full_path):
                date_taken = None
                img = None
                try:
                    img = Image.open(full_path)
                except OSError as e:
                    logger.warning(f'Failed to open image {full_path}: {e}')
                if img:
                    try:
                        if hasattr(img, '_getexif'):
                            _getexif = img._getexif()
                            if _getexif and DATE_TIME_ORIGINAL_KEY in _getexif:
                                date_taken = _getexif[DATE_TIME_ORIGINAL_KEY]
                        if not date_taken and hasattr(img, 'tag'):
                            logger.info(f'tag exists {f}')
                            date_taken = img.tag._tagdata[DATE_TIME_ORIGINAL_KEY]
                    except Exception as e:
                        logger.warning(f'Failed to read EXIF data from {full_path}: {e}')
                if date_taken:
                    match = re.match(regex_patterns.DATE_TAKEN_REGEX, date_taken)
                    if match:
                        properties.update(match.groupdict())
                    else:
                        logger.info(f'date_taken case {date_taken} full_path: {full_path}')
                        self.unsupported.append(full_path)
                else:
                    properties.update(self._retrieve_min_date(f, full_path))
            elif properties['extension'] in regex_patterns.VIDEO_FILE_EXTENSIONS:
                properties.update(self._retrieve_min_date(f, full_path))
            else:
                self.unsupported.append(full_path)
                continue

            passed_comparison = True
            errors: list[str] = []
            # Name Filter
            if 'name' in self.comparers:
                if f in self.all_handled_names:
                    errors.append(f'NAME: {f}')
                    passed_comparison = False

            if 'size' in self.comparers:
                pass

            # binary Comparer
            if passed_comparison and 'binary' in self.comparers:
                if size in self.sizes_files:
                    for _f in self.sizes_files[size]:
                        if filecmp.cmp(_f, full_path, shallow=False):
                            errors.append(f'BINARY: {full_path} same as {_f} {size}')
                            passed_comparison = False
                            break

            if passed_comparison:
                self.matched[f].append(properties)
                self.sizes_files[size].append(full_path)
            else:
                self.not_passed_comparison.append((full_path, '; '.join(errors)))

    def _retrieve_min_date(self, f: str, full_path: str) -> dict[str, str]:
        p = Path(full_path)
        stat = p.stat()
        min_date = min(stat.st_atime, stat.st_mtime, stat.st_ctime)
        dt = datetime.fromtimestamp(min_date)
        match = re.match(regex_patterns.ACCEPTABLE_REGEXS[0], f)
        if match:
            group_dict = {key: int(value if value else '0') for key, value in match.groupdict().items()
                          if key in ['year', 'month', 'day', 'hour', 'minute', 'second']}
            dt_from_name = datetime(group_dict['year'], group_dict['month'], group_dict['day'], group_dict['hour'],
                                    group_dict['minute'], group_dict['second'])
            dt = min(dt, dt_from_name)

        date_props = {
            'year': str(dt.year), 'month': f'{dt.month:02d}',
            'day': f'{dt.day:02d}', 'hour': f'{dt.hour:02d}',
            'minute': f'{dt.minute:02d}', 'second': f'{dt.second:02d}'
            }
        self.min_date_taken.append((f, date_props))
        return date_props

    def _move_prepared_files(self) -> None:
        all_files = [(fg, f) for fg, files in self.ready_to_add.items() for f in files]

        try:
            from tqdm import tqdm
            file_iter = tqdm(all_files, desc='Moving files', unit='file')
        except ImportError:
            file_iter = all_files

        for fg, f in file_iter:
            year = f.get('year', '')
            month = f.get('month', '')
            if year and self.by_month and month:
                target_folder = self.dst / year / month
            elif year:
                target_folder = self.dst / year
            else:
                target_folder = self.dst
            target_folder.mkdir(parents=True, exist_ok=True)
            new_file_path = target_folder / f['new_file_name']
            full_path = Path(f['folder']) / f['file']
            try:
                if new_file_path.exists():
                    self.unmoved[str(full_path)] = f'Exists {new_file_path}'
                    continue
                move(str(full_path), str(new_file_path))
                self.moved[str(full_path)] = str(new_file_path)
            except OSError as e:
                self.unmoved[str(full_path)] = f'Error {e.__class__.__name__} {e}'


if __name__ == "__main__":
    main()
