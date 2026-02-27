from __future__ import annotations

import os
import json
import re
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import picture_handler
from picture_handler import PicturesHandler, create_parser
import regex_patterns


class TestCreateParser:

    def test_defaults(self) -> None:
        parser = create_parser()
        args = parser.parse_args(['--src', '/src', '--dst', '/dst'])
        assert args.src == '/src'
        assert args.dst == '/dst'
        assert args.recursive is True
        assert args.dry_run is False
        assert args.sync is False
        assert args.compare is None
        assert args.ignore is None
        assert args.accept is None

    def test_not_recursive_flag_keeps_recursive_true(self) -> None:
        parser = create_parser()
        args = parser.parse_args(['--src', '/s', '--dst', '/d', '--not-recursive'])
        assert args.recursive is True

    def test_dry_run_flag(self) -> None:
        parser = create_parser()
        args = parser.parse_args(['--src', '/s', '--dst', '/d', '--dry-run'])
        assert args.dry_run is True

    def test_compare_args(self) -> None:
        parser = create_parser()
        args = parser.parse_args(['--src', '/s', '--dst', '/d', '-c', 'name', 'binary'])
        assert args.compare == ['name', 'binary']


class TestPicturesHandlerInit:

    def test_missing_src_raises(self, tmp_path) -> None:
        with pytest.raises(ValueError, match='Mandatory parameter'):
            PicturesHandler(None, str(tmp_path))

    def test_missing_dst_raises(self, tmp_path) -> None:
        with pytest.raises(ValueError, match='Mandatory parameter'):
            PicturesHandler(str(tmp_path), None)

    def test_nonexistent_src_raises(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError, match='Source folder does not exist'):
            PicturesHandler(str(tmp_path / 'nonexistent'), str(tmp_path))

    def test_src_is_file_raises(self, tmp_path) -> None:
        f = tmp_path / 'file.txt'
        f.write_text('x')
        with pytest.raises(NotADirectoryError, match='Source path is not a directory'):
            PicturesHandler(str(f), str(tmp_path))

    def test_valid_init(self, tmp_path) -> None:
        src = tmp_path / 'src'
        src.mkdir()
        dst = tmp_path / 'dst'
        handler = PicturesHandler(str(src), str(dst))
        assert handler.src == src
        assert handler.dst == dst
        assert handler.comparers == {}
        assert handler.dry_run is False
        assert handler.recursive is False

    def test_comparers_initialized(self, tmp_path) -> None:
        src = tmp_path / 'src'
        src.mkdir()
        handler = PicturesHandler(str(src), str(tmp_path), comparers=['name', 'binary'])
        assert 'name' in handler.comparers
        assert 'binary' in handler.comparers

    def test_accept_default_preset(self, tmp_path) -> None:
        src = tmp_path / 'src'
        src.mkdir()
        handler = PicturesHandler(str(src), str(tmp_path), accept_regexs=['default'])
        assert len(handler.acceptable_regexs) == len(regex_patterns.ACCEPTABLE_REGEXS)


class TestHandleDestinationFolder:

    def test_creates_dst_if_not_exists(self, tmp_path) -> None:
        src = tmp_path / 'src'
        src.mkdir()
        dst = tmp_path / 'dst'
        handler = PicturesHandler(str(src), str(dst), dry_run=True)
        handler._handle_destination_folder(dst)
        assert dst.exists()

    def test_counts_files_in_destination(self, tmp_path) -> None:
        src = tmp_path / 'src'
        src.mkdir()
        dst = tmp_path / 'dst'
        dst.mkdir()
        (dst / 'some_file.txt').write_text('x')
        (dst / 'another.jpg').write_text('x')
        handler = PicturesHandler(str(src), str(dst), dry_run=True)
        handler._handle_destination_folder(dst)
        assert handler.num_of_dst_files == 2


class TestHandleSourceFolder:

    def test_ignores_files_matching_ignore_regex(self, tmp_path) -> None:
        src = tmp_path / 'src'
        src.mkdir()
        dst = tmp_path / 'dst'
        (src / 'thumbs.db').write_text('x')
        (src / '.DS_Store').write_text('x')
        handler = PicturesHandler(str(src), str(dst), dry_run=True,
                                  ignore_regexs=[r'thumbs\.db', r'\.DS_Store'])
        handler._handle_source_folder(src, recursive=False)
        assert len(handler.ignored) == 2

    def test_unsupported_extension_skipped(self, tmp_path) -> None:
        src = tmp_path / 'src'
        src.mkdir()
        dst = tmp_path / 'dst'
        (src / 'readme.txt').write_text('not an image')
        handler = PicturesHandler(str(src), str(dst), dry_run=True)
        handler._handle_source_folder(src, recursive=False)
        assert len(handler.unsupported) == 1


class TestRetrieveMinDate:

    def test_returns_date_props_from_file_stats(self, tmp_path) -> None:
        src = tmp_path / 'src'
        src.mkdir()
        dst = tmp_path / 'dst'
        test_file = src / 'test.jpg'
        test_file.write_text('x')
        handler = PicturesHandler(str(src), str(dst), dry_run=True)
        result = handler._retrieve_min_date('test.jpg', str(test_file))
        assert 'year' in result
        assert 'month' in result
        assert 'day' in result
        assert 'hour' in result
        assert 'minute' in result
        assert 'second' in result
        assert len(result['month']) == 2
        assert len(result['day']) == 2


class TestMoveFlow:

    def _create_test_image(self, path: Path) -> None:
        img = Image.new('RGB', (10, 10), color='red')
        img.save(str(path))

    def test_dry_run_does_not_move(self, tmp_path) -> None:
        src = tmp_path / 'src'
        src.mkdir()
        dst = tmp_path / 'dst'
        dst.mkdir()
        img_file = src / 'IMG_0001.jpg'
        self._create_test_image(img_file)
        handler = PicturesHandler(str(src), str(dst), dry_run=True)
        handler.handle()
        assert img_file.exists()
        assert len(handler.moved) == 0

    def test_full_move_with_comparers(self, tmp_path) -> None:
        src = tmp_path / 'src'
        src.mkdir()
        dst = tmp_path / 'dst'
        dst.mkdir()
        img_file = src / 'IMG_0001.jpg'
        self._create_test_image(img_file)
        handler = PicturesHandler(str(src), str(dst), comparers=['name'], dry_run=False)
        handler.handle()
        assert not img_file.exists()
        assert len(handler.moved) == 1
        moved_dst = list(handler.moved.values())[0]
        assert Path(moved_dst).exists()

    def test_move_places_file_in_year_subfolder(self, tmp_path) -> None:
        src = tmp_path / 'src'
        src.mkdir()
        dst = tmp_path / 'dst'
        dst.mkdir()
        img_file = src / 'IMG_0001.jpg'
        self._create_test_image(img_file)
        handler = PicturesHandler(str(src), str(dst), dry_run=False)
        handler.handle()
        assert len(handler.moved) == 1
        moved_dst = list(handler.moved.values())[0]
        moved_path = Path(moved_dst)
        assert moved_path.exists()
        # File should be in a year subfolder (4-digit parent dir name)
        assert re.match(r'^\d{4}$', moved_path.parent.name)


class TestHandleDestinationWithYearFolders:

    def test_scans_year_subfolders(self, tmp_path) -> None:
        src = tmp_path / 'src'
        src.mkdir()
        dst = tmp_path / 'dst'
        dst.mkdir()
        year_dir = dst / '2020'
        year_dir.mkdir()
        (year_dir / '20200315_143022_000.jpg').write_text('x')
        (year_dir / '20200601_080000_000.jpg').write_text('x')
        handler = PicturesHandler(str(src), str(dst), dry_run=True)
        handler._handle_destination_folder(dst)
        assert handler.num_of_dst_files == 2
        assert len(handler.destination_formats) == 2

    def test_scans_mixed_root_and_year_files(self, tmp_path) -> None:
        src = tmp_path / 'src'
        src.mkdir()
        dst = tmp_path / 'dst'
        dst.mkdir()
        (dst / '20190101_120000_000.jpg').write_text('x')
        year_dir = dst / '2020'
        year_dir.mkdir()
        (year_dir / '20200315_143022_000.jpg').write_text('x')
        handler = PicturesHandler(str(src), str(dst), dry_run=True)
        handler._handle_destination_folder(dst)
        assert handler.num_of_dst_files == 2
        assert len(handler.destination_formats) == 2


class TestCreateParserOrganizeByYear:

    def test_organize_by_year_flag_default_false(self) -> None:
        parser = create_parser()
        args = parser.parse_args(['--src', '/s', '--dst', '/d'])
        assert args.organize_by_year is False

    def test_organize_by_year_flag_set(self) -> None:
        parser = create_parser()
        args = parser.parse_args(['--src', '/s', '--dst', '/d', '--organize-by-year'])
        assert args.organize_by_year is True

    def test_by_month_flag_default_false(self) -> None:
        parser = create_parser()
        args = parser.parse_args(['--src', '/s', '--dst', '/d'])
        assert args.by_month is False

    def test_by_month_flag_set(self) -> None:
        parser = create_parser()
        args = parser.parse_args(['--src', '/s', '--dst', '/d', '--by-month'])
        assert args.by_month is True

    def test_duplicate_report_flag_default_false(self) -> None:
        parser = create_parser()
        args = parser.parse_args(['--src', '/s', '--dst', '/d'])
        assert args.duplicate_report is False

    def test_duplicate_report_flag_set(self) -> None:
        parser = create_parser()
        args = parser.parse_args(['--src', '/s', '--dst', '/d', '--duplicate-report'])
        assert args.duplicate_report is True

    def test_find_duplicates_flag_default_false(self) -> None:
        parser = create_parser()
        args = parser.parse_args(['--src', '/s', '--dst', '/d'])
        assert args.find_duplicates is False

    def test_find_duplicates_flag_set(self) -> None:
        parser = create_parser()
        args = parser.parse_args(['--src', '/s', '--dst', '/d', '--find-duplicates'])
        assert args.find_duplicates is True

    def test_delete_duplicates_flag_default_false(self) -> None:
        parser = create_parser()
        args = parser.parse_args(['--src', '/s', '--dst', '/d'])
        assert args.delete_duplicates is False

    def test_delete_duplicates_flag_set(self) -> None:
        parser = create_parser()
        args = parser.parse_args(['--src', '/s', '--dst', '/d', '--find-duplicates', '--delete-duplicates'])
        assert args.delete_duplicates is True


class TestMoveByMonth:

    def _create_test_image(self, path: Path) -> None:
        img = Image.new('RGB', (10, 10), color='blue')
        img.save(str(path))

    def test_move_places_file_in_year_month_subfolder(self, tmp_path) -> None:
        src = tmp_path / 'src'
        src.mkdir()
        dst = tmp_path / 'dst'
        dst.mkdir()
        img_file = src / 'IMG_0001.jpg'
        self._create_test_image(img_file)
        handler = PicturesHandler(str(src), str(dst), dry_run=False, by_month=True)
        handler.handle()
        assert len(handler.moved) == 1
        moved_dst = list(handler.moved.values())[0]
        moved_path = Path(moved_dst)
        assert moved_path.exists()
        # Parent should be a 2-digit month folder, grandparent a 4-digit year folder
        assert re.match(r'^\d{2}$', moved_path.parent.name)
        assert re.match(r'^\d{4}$', moved_path.parent.parent.name)

    def test_by_month_false_uses_year_only(self, tmp_path) -> None:
        src = tmp_path / 'src'
        src.mkdir()
        dst = tmp_path / 'dst'
        dst.mkdir()
        img_file = src / 'IMG_0001.jpg'
        self._create_test_image(img_file)
        handler = PicturesHandler(str(src), str(dst), dry_run=False, by_month=False)
        handler.handle()
        assert len(handler.moved) == 1
        moved_path = Path(list(handler.moved.values())[0])
        assert re.match(r'^\d{4}$', moved_path.parent.name)


class TestHandleDestinationWithMonthFolders:

    def test_scans_month_subfolders_inside_year(self, tmp_path) -> None:
        src = tmp_path / 'src'
        src.mkdir()
        dst = tmp_path / 'dst'
        dst.mkdir()
        month_dir = dst / '2020' / '03'
        month_dir.mkdir(parents=True)
        (month_dir / '20200315_143022_000.jpg').write_text('x')
        handler = PicturesHandler(str(src), str(dst), dry_run=True)
        handler._handle_destination_folder(dst)
        assert handler.num_of_dst_files == 1
        assert len(handler.destination_formats) == 1
