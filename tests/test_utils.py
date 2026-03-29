from __future__ import annotations

import os
import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import utils


class TestLoadDbFiles:

    def test_load_existing_db(self, tmp_path) -> None:
        db_data = {'src/photo.jpg': 'dst/20200101_120000_000.jpg'}
        db_file = tmp_path / 'files.txt'
        db_file.write_text(json.dumps(db_data))
        result = utils.load_db_files(str(tmp_path))
        assert result == db_data

    def test_load_nonexistent_db_returns_empty(self, tmp_path) -> None:
        result = utils.load_db_files(str(tmp_path))
        assert result == {}

    def test_load_custom_db_name(self, tmp_path) -> None:
        db_data = {'a': 'b'}
        db_file = tmp_path / 'custom.json'
        db_file.write_text(json.dumps(db_data))
        result = utils.load_db_files(str(tmp_path), db_name='custom.json')
        assert result == db_data


class TestSaveDbFiles:

    def test_save_creates_file(self, tmp_path) -> None:
        data = {'src/img.jpg': 'dst/20200101_000000_000.jpg'}
        utils.save_db_files(data, str(tmp_path))
        db_file = tmp_path / 'files.txt'
        assert db_file.exists()
        loaded = json.loads(db_file.read_text())
        assert loaded == data

    def test_save_overwrites_existing(self, tmp_path) -> None:
        old_data = {'old': 'data'}
        new_data = {'new': 'data'}
        utils.save_db_files(old_data, str(tmp_path))
        utils.save_db_files(new_data, str(tmp_path))
        db_file = tmp_path / 'files.txt'
        loaded = json.loads(db_file.read_text())
        assert loaded == new_data


class TestIsOldDbFormat:

    def test_old_format_detected(self) -> None:
        old_db = {'C:/src/IMG_001.jpg': 'C:/dst/20200315_143022_000.jpg'}
        assert utils.is_old_db_format(old_db) is True

    def test_new_format_detected(self) -> None:
        new_db = {'20200315_143022_000.jpg': {'source_name': 'IMG_001.jpg', 'size': 100}}
        assert utils.is_old_db_format(new_db) is False

    def test_empty_db_returns_false(self) -> None:
        assert utils.is_old_db_format({}) is False


class TestConvertDb:

    def test_converts_old_to_new_format(self, tmp_path) -> None:
        dst_file = tmp_path / '20200315_143022_000.jpg'
        dst_file.write_text('photo data')
        old_db = {'C:/src/IMG_001.jpg': str(dst_file)}
        (tmp_path / 'files.txt').write_text(json.dumps(old_db))
        logs: list[str] = []
        result = utils.convert_db(str(tmp_path), dry_run=False, logger_func=logs.append)
        assert '20200315_143022_000.jpg' in result
        entry = result['20200315_143022_000.jpg']
        assert entry['source_name'] == 'IMG_001.jpg'
        assert entry['size'] == len('photo data')
        # Verify file was saved
        reloaded = json.loads((tmp_path / 'files.txt').read_text())
        assert reloaded == result

    def test_dry_run_does_not_save(self, tmp_path) -> None:
        dst_file = tmp_path / '20200315_143022_000.jpg'
        dst_file.write_text('photo data')
        old_db = {'C:/src/IMG_001.jpg': str(dst_file)}
        (tmp_path / 'files.txt').write_text(json.dumps(old_db))
        original_text = (tmp_path / 'files.txt').read_text()
        utils.convert_db(str(tmp_path), dry_run=True, logger_func=lambda x: None)
        assert (tmp_path / 'files.txt').read_text() == original_text

    def test_already_new_format_returns_as_is(self, tmp_path) -> None:
        new_db = {'20200315_143022_000.jpg': {'source_name': 'IMG_001.jpg', 'size': 100}}
        (tmp_path / 'files.txt').write_text(json.dumps(new_db))
        logs: list[str] = []
        result = utils.convert_db(str(tmp_path), dry_run=True, logger_func=logs.append)
        assert result == new_db
        assert any('already in new format' in log for log in logs)

    def test_empty_db_returns_empty(self, tmp_path) -> None:
        (tmp_path / 'files.txt').write_text('{}')
        logs: list[str] = []
        result = utils.convert_db(str(tmp_path), dry_run=True, logger_func=logs.append)
        assert result == {}
        assert any('empty' in log for log in logs)

    def test_nonexistent_folder_returns_empty(self, tmp_path) -> None:
        logs: list[str] = []
        result = utils.convert_db(str(tmp_path / 'nope'), dry_run=True, logger_func=logs.append)
        assert result == {}
        assert any('does not exist' in log for log in logs)

    def test_missing_file_sets_size_zero(self, tmp_path) -> None:
        old_db = {'C:/src/IMG_001.jpg': 'C:/nonexistent/20200315_143022_000.jpg'}
        (tmp_path / 'files.txt').write_text(json.dumps(old_db))
        logs: list[str] = []
        result = utils.convert_db(str(tmp_path), dry_run=False, logger_func=logs.append)
        assert result['20200315_143022_000.jpg']['size'] == 0
        assert any('not found' in log for log in logs)

    def test_duplicate_source_names_both_kept(self, tmp_path) -> None:
        dst1 = tmp_path / 'dst1.jpg'
        dst2 = tmp_path / 'dst2.jpg'
        dst1.write_text('a')
        dst2.write_text('b')
        old_db = {
            'C:/folder1/photo.jpg': str(dst1),
            'C:/folder2/photo.jpg': str(dst2),
        }
        (tmp_path / 'files.txt').write_text(json.dumps(old_db))
        logs: list[str] = []
        result = utils.convert_db(str(tmp_path), dry_run=False, logger_func=logs.append)
        # Both entries kept since dest names (keys) are unique
        assert 'dst1.jpg' in result
        assert 'dst2.jpg' in result
        assert result['dst1.jpg']['source_name'] == 'photo.jpg'
        assert result['dst2.jpg']['source_name'] == 'photo.jpg'

    def test_finds_file_by_rglob_when_full_path_missing(self, tmp_path) -> None:
        sub = tmp_path / '2020'
        sub.mkdir()
        actual_file = sub / '20200315_143022_000.jpg'
        actual_file.write_text('found by rglob')
        old_db = {'C:/src/IMG.jpg': 'C:/gone/path/20200315_143022_000.jpg'}
        (tmp_path / 'files.txt').write_text(json.dumps(old_db))
        result = utils.convert_db(str(tmp_path), dry_run=False, logger_func=lambda x: None)
        assert result['20200315_143022_000.jpg']['size'] == len('found by rglob')


class TestSyncFolderAndDb:

    def test_dry_run_does_not_modify_db(self, tmp_path) -> None:
        db_data = {'missing.jpg': {'source_name': 'photo_src.jpg', 'size': 100}}
        db_file = tmp_path / 'files.txt'
        db_file.write_text(json.dumps(db_data))
        logs: list[str] = []
        utils.sync_folder_and_db(str(tmp_path), dry_run=True, logger_func=logs.append)
        reloaded = json.loads(db_file.read_text())
        assert reloaded == db_data

    def test_non_dry_run_removes_missing_from_db(self, tmp_path) -> None:
        present_file = tmp_path / 'present.jpg'
        present_file.write_text('data')
        db_data = {
            'present.jpg': {'source_name': 'present_src.jpg', 'size': 4},
            'gone.jpg': {'source_name': 'gone_src.jpg', 'size': 100},
        }
        db_file = tmp_path / 'files.txt'
        db_file.write_text(json.dumps(db_data))
        logs: list[str] = []
        utils.sync_folder_and_db(str(tmp_path), dry_run=False, logger_func=logs.append)
        reloaded = json.loads(db_file.read_text())
        assert 'gone.jpg' not in reloaded
        assert 'present.jpg' in reloaded

    def test_finds_files_in_subdirectories(self, tmp_path) -> None:
        sub = tmp_path / 'subdir'
        sub.mkdir()
        sub_file = sub / 'deep_photo.jpg'
        sub_file.write_text('deep data')
        db_data = {'deep_photo.jpg': {'source_name': 'deep_photo_src.jpg', 'size': 9}}
        db_file = tmp_path / 'files.txt'
        db_file.write_text(json.dumps(db_data))
        logs: list[str] = []
        utils.sync_folder_and_db(str(tmp_path), dry_run=False, logger_func=logs.append)
        reloaded = json.loads(db_file.read_text())
        assert 'deep_photo.jpg' in reloaded


class TestOrganizeByYear:

    def test_dry_run_does_not_move_files(self, tmp_path) -> None:
        f1 = tmp_path / '20200315_143022_000.jpg'
        f1.write_text('photo data')
        logs: list[str] = []
        utils.organize_by_year(str(tmp_path), dry_run=True, logger_func=logs.append)
        assert f1.exists()
        assert not (tmp_path / '2020').exists()
        assert any('[DRY RUN]' in log for log in logs)

    def test_moves_files_into_year_folders(self, tmp_path) -> None:
        f1 = tmp_path / '20200315_143022_000.jpg'
        f2 = tmp_path / '20210601_080000_000.jpg'
        f1.write_text('photo 2020')
        f2.write_text('photo 2021')
        logs: list[str] = []
        utils.organize_by_year(str(tmp_path), dry_run=False, logger_func=logs.append)
        assert not f1.exists()
        assert not f2.exists()
        assert (tmp_path / '2020' / '20200315_143022_000.jpg').exists()
        assert (tmp_path / '2021' / '20210601_080000_000.jpg').exists()

    def test_db_unchanged_after_organize(self, tmp_path) -> None:
        f1 = tmp_path / '20200315_143022_000.jpg'
        f1.write_text('photo data')
        db_data = {'20200315_143022_000.jpg': {'source_name': 'IMG_001.jpg', 'size': 10}}
        (tmp_path / 'files.txt').write_text(json.dumps(db_data))
        utils.organize_by_year(str(tmp_path), dry_run=False, logger_func=lambda x: None)
        reloaded = json.loads((tmp_path / 'files.txt').read_text())
        assert reloaded == db_data

    def test_skips_non_matching_files(self, tmp_path) -> None:
        f1 = tmp_path / 'random_notes.txt'
        f1.write_text('not a photo')
        logs: list[str] = []
        utils.organize_by_year(str(tmp_path), dry_run=False, logger_func=logs.append)
        assert f1.exists()
        assert any('0 files' in log for log in logs)

    def test_skips_if_already_exists_in_year_folder(self, tmp_path) -> None:
        year_dir = tmp_path / '2020'
        year_dir.mkdir()
        existing = year_dir / '20200315_143022_000.jpg'
        existing.write_text('already here')
        duplicate = tmp_path / '20200315_143022_000.jpg'
        duplicate.write_text('duplicate')
        logs: list[str] = []
        utils.organize_by_year(str(tmp_path), dry_run=False, logger_func=logs.append)
        assert duplicate.exists()
        assert any('Skipping' in log for log in logs)


class TestOrganizeByMonth:

    def test_moves_files_into_year_month_folders(self, tmp_path) -> None:
        f1 = tmp_path / '20200315_143022_000.jpg'
        f2 = tmp_path / '20200601_080000_000.jpg'
        f1.write_text('march photo')
        f2.write_text('june photo')
        logs: list[str] = []
        utils.organize_by_year(str(tmp_path), dry_run=False, by_month=True, logger_func=logs.append)
        assert not f1.exists()
        assert not f2.exists()
        assert (tmp_path / '2020' / '03' / '20200315_143022_000.jpg').exists()
        assert (tmp_path / '2020' / '06' / '20200601_080000_000.jpg').exists()

    def test_dry_run_does_not_create_month_folders(self, tmp_path) -> None:
        f1 = tmp_path / '20200315_143022_000.jpg'
        f1.write_text('photo')
        logs: list[str] = []
        utils.organize_by_year(str(tmp_path), dry_run=True, by_month=True, logger_func=logs.append)
        assert f1.exists()
        assert not (tmp_path / '2020' / '03').exists()
        assert any('[DRY RUN]' in log for log in logs)

    def test_upgrades_year_only_to_year_month(self, tmp_path) -> None:
        year_dir = tmp_path / '2020'
        year_dir.mkdir()
        f1 = year_dir / '20200315_143022_000.jpg'
        f1.write_text('photo in year folder')
        logs: list[str] = []
        utils.organize_by_year(str(tmp_path), dry_run=False, by_month=True, logger_func=logs.append)
        assert not f1.exists()
        assert (tmp_path / '2020' / '03' / '20200315_143022_000.jpg').exists()

    def test_db_unchanged_after_month_organize(self, tmp_path) -> None:
        f1 = tmp_path / '20200315_143022_000.jpg'
        f1.write_text('photo')
        db_data = {'20200315_143022_000.jpg': {'source_name': 'IMG_001.jpg', 'size': 5}}
        (tmp_path / 'files.txt').write_text(json.dumps(db_data))
        utils.organize_by_year(str(tmp_path), dry_run=False, by_month=True, logger_func=lambda x: None)
        reloaded = json.loads((tmp_path / 'files.txt').read_text())
        assert reloaded == db_data


class TestGenerateDuplicateReport:

    def test_finds_duplicate_files(self, tmp_path) -> None:
        f1 = tmp_path / 'photo1.jpg'
        f2 = tmp_path / 'photo2.jpg'
        f1.write_text('identical content here')
        f2.write_text('identical content here')
        logs: list[str] = []
        groups = utils.generate_duplicate_report(str(tmp_path), logger_func=logs.append)
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_no_duplicates_returns_empty(self, tmp_path) -> None:
        f1 = tmp_path / 'photo1.jpg'
        f2 = tmp_path / 'photo2.jpg'
        f1.write_text('content A')
        f2.write_text('different content B')
        logs: list[str] = []
        groups = utils.generate_duplicate_report(str(tmp_path), logger_func=logs.append)
        assert len(groups) == 0

    def test_generates_html_report(self, tmp_path) -> None:
        f1 = tmp_path / 'photo1.jpg'
        f2 = tmp_path / 'photo2.jpg'
        f1.write_text('same data')
        f2.write_text('same data')
        report_path = str(tmp_path / 'report.html')
        utils.generate_duplicate_report(str(tmp_path), output_path=report_path, logger_func=lambda x: None)
        report = (tmp_path / 'report.html')
        assert report.exists()
        content = report.read_text()
        assert 'Duplicate Files Report' in content
        assert 'Group 1' in content
        assert '1 duplicate groups' in content or '1</strong> duplicate groups' in content

    def test_default_report_path_in_folder(self, tmp_path) -> None:
        f1 = tmp_path / 'a.jpg'
        f2 = tmp_path / 'b.jpg'
        f1.write_text('dup')
        f2.write_text('dup')
        utils.generate_duplicate_report(str(tmp_path), logger_func=lambda x: None)
        assert (tmp_path / 'duplicate_report.html').exists()

    def test_finds_duplicates_in_subfolders(self, tmp_path) -> None:
        sub1 = tmp_path / 'sub1'
        sub2 = tmp_path / 'sub2'
        sub1.mkdir()
        sub2.mkdir()
        (sub1 / 'photo.jpg').write_text('same bytes')
        (sub2 / 'photo_copy.jpg').write_text('same bytes')
        groups = utils.generate_duplicate_report(str(tmp_path), logger_func=lambda x: None)
        assert len(groups) == 1

    def test_nonexistent_folder_returns_empty(self, tmp_path) -> None:
        logs: list[str] = []
        groups = utils.generate_duplicate_report(str(tmp_path / 'nope'), logger_func=logs.append)
        assert groups == []
        assert any('does not exist' in log for log in logs)


class TestFindDuplicates:

    def test_dry_run_finds_but_does_not_delete(self, tmp_path) -> None:
        f1 = tmp_path / 'photo1.jpg'
        f2 = tmp_path / 'photo2.jpg'
        f1.write_bytes(b'\xff\xd8\xff identical image data here')
        f2.write_bytes(b'\xff\xd8\xff identical image data here')
        logs: list[str] = []
        groups = utils.find_duplicates(str(tmp_path), delete=False, logger_func=logs.append)
        assert len(groups) == 1
        assert len(groups[0]) == 2
        assert f1.exists()
        assert f2.exists()
        assert any('[DRY RUN]' in log for log in logs)

    def test_delete_removes_duplicates(self, tmp_path) -> None:
        f1 = tmp_path / 'photo1.jpg'
        f2 = tmp_path / 'photo2.jpg'
        f3 = tmp_path / 'photo3.jpg'
        f1.write_bytes(b'\xff\xd8\xff same content bytes')
        f2.write_bytes(b'\xff\xd8\xff same content bytes')
        f3.write_bytes(b'\xff\xd8\xff same content bytes')
        logs: list[str] = []
        groups = utils.find_duplicates(str(tmp_path), delete=True, logger_func=logs.append)
        assert len(groups) == 1
        # First file kept, others deleted
        remaining = [f for f in [f1, f2, f3] if f.exists()]
        assert len(remaining) == 1
        assert any('Deleted' in log for log in logs)

    def test_ignores_non_media_files(self, tmp_path) -> None:
        f1 = tmp_path / 'notes1.txt'
        f2 = tmp_path / 'notes2.txt'
        f1.write_text('same text content')
        f2.write_text('same text content')
        logs: list[str] = []
        groups = utils.find_duplicates(str(tmp_path), delete=False, logger_func=logs.append)
        assert len(groups) == 0
        assert f1.exists()
        assert f2.exists()

    def test_finds_duplicates_in_subfolders(self, tmp_path) -> None:
        sub1 = tmp_path / 'sub1'
        sub2 = tmp_path / 'sub2'
        sub1.mkdir()
        sub2.mkdir()
        (sub1 / 'photo.jpg').write_bytes(b'\xff\xd8\xff dupe across folders')
        (sub2 / 'photo_copy.jpg').write_bytes(b'\xff\xd8\xff dupe across folders')
        groups = utils.find_duplicates(str(tmp_path), delete=False, logger_func=lambda x: None)
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_no_duplicates_returns_empty(self, tmp_path) -> None:
        (tmp_path / 'a.jpg').write_bytes(b'\xff\xd8\xff unique A')
        (tmp_path / 'b.png').write_bytes(b'\x89PNG unique B')
        logs: list[str] = []
        groups = utils.find_duplicates(str(tmp_path), delete=False, logger_func=logs.append)
        assert len(groups) == 0

    def test_nonexistent_folder_returns_empty(self, tmp_path) -> None:
        logs: list[str] = []
        groups = utils.find_duplicates(str(tmp_path / 'missing'), logger_func=logs.append)
        assert groups == []
        assert any('does not exist' in log for log in logs)

    def test_handles_video_duplicates(self, tmp_path) -> None:
        f1 = tmp_path / 'clip1.mp4'
        f2 = tmp_path / 'clip2.mp4'
        f1.write_bytes(b'\x00\x00\x00 same video data')
        f2.write_bytes(b'\x00\x00\x00 same video data')
        groups = utils.find_duplicates(str(tmp_path), delete=False, logger_func=lambda x: None)
        assert len(groups) == 1

    def test_mixed_media_and_non_media(self, tmp_path) -> None:
        (tmp_path / 'photo1.jpg').write_bytes(b'\xff\xd8\xff same')
        (tmp_path / 'photo2.jpg').write_bytes(b'\xff\xd8\xff same')
        (tmp_path / 'doc1.pdf').write_bytes(b'\xff\xd8\xff same')
        groups = utils.find_duplicates(str(tmp_path), delete=False, logger_func=lambda x: None)
        assert len(groups) == 1
        # Only jpg files in the group, not pdf
        all_files_in_groups = [f for g in groups for f in g]
        assert all(f.endswith('.jpg') for f in all_files_in_groups)


class TestKeepStrategies:

    def test_folder_priority_keeps_preferred_folder(self, tmp_path) -> None:
        preferred = tmp_path / 'keep_here'
        other = tmp_path / 'other'
        preferred.mkdir()
        other.mkdir()
        (preferred / 'photo.jpg').write_bytes(b'\xff\xd8\xff same data')
        (other / 'photo_copy.jpg').write_bytes(b'\xff\xd8\xff same data')
        groups = utils.find_duplicates(str(tmp_path), delete=True,
                                       keep_strategy='folder_priority',
                                       keep_folder=str(preferred),
                                       logger_func=lambda x: None)
        assert len(groups) == 1
        assert (preferred / 'photo.jpg').exists()
        assert not (other / 'photo_copy.jpg').exists()

    def test_folder_priority_no_match_keeps_first(self, tmp_path) -> None:
        sub1 = tmp_path / 'sub1'
        sub2 = tmp_path / 'sub2'
        sub1.mkdir()
        sub2.mkdir()
        (sub1 / 'a.jpg').write_bytes(b'\xff\xd8\xff same')
        (sub2 / 'b.jpg').write_bytes(b'\xff\xd8\xff same')
        groups = utils.find_duplicates(str(tmp_path), delete=False,
                                       keep_strategy='folder_priority',
                                       keep_folder=str(tmp_path / 'nonexistent'),
                                       logger_func=lambda x: None)
        assert len(groups) == 1
        # Both still exist (dry run), group order unchanged since no match
        assert (sub1 / 'a.jpg').exists()
        assert (sub2 / 'b.jpg').exists()

    def test_shortest_path_keeps_shallowest(self, tmp_path) -> None:
        deep = tmp_path / 'a' / 'b' / 'c'
        deep.mkdir(parents=True)
        (tmp_path / 'photo.jpg').write_bytes(b'\xff\xd8\xff same data here')
        (deep / 'photo_deep.jpg').write_bytes(b'\xff\xd8\xff same data here')
        groups = utils.find_duplicates(str(tmp_path), delete=True,
                                       keep_strategy='shortest_path',
                                       logger_func=lambda x: None)
        assert len(groups) == 1
        assert (tmp_path / 'photo.jpg').exists()
        assert not (deep / 'photo_deep.jpg').exists()

    def test_oldest_keeps_oldest_file(self, tmp_path) -> None:
        import time
        old_file = tmp_path / 'old.jpg'
        old_file.write_bytes(b'\xff\xd8\xff same content')
        import os
        os.utime(str(old_file), (1000000, 1000000))
        time.sleep(0.05)
        new_file = tmp_path / 'new.jpg'
        new_file.write_bytes(b'\xff\xd8\xff same content')
        groups = utils.find_duplicates(str(tmp_path), delete=True,
                                       keep_strategy='oldest',
                                       logger_func=lambda x: None)
        assert len(groups) == 1
        assert old_file.exists()
        assert not new_file.exists()

    def test_unknown_strategy_returns_empty(self, tmp_path) -> None:
        (tmp_path / 'a.jpg').write_bytes(b'\xff\xd8\xff same')
        (tmp_path / 'b.jpg').write_bytes(b'\xff\xd8\xff same')
        logs: list[str] = []
        groups = utils.find_duplicates(str(tmp_path), delete=False,
                                       keep_strategy='bogus',
                                       logger_func=logs.append)
        assert groups == []
        assert any('Unknown keep strategy' in log for log in logs)

    def test_folder_priority_without_keep_folder_returns_empty(self, tmp_path) -> None:
        (tmp_path / 'a.jpg').write_bytes(b'\xff\xd8\xff same')
        (tmp_path / 'b.jpg').write_bytes(b'\xff\xd8\xff same')
        logs: list[str] = []
        groups = utils.find_duplicates(str(tmp_path), delete=False,
                                       keep_strategy='folder_priority',
                                       keep_folder=None,
                                       logger_func=logs.append)
        assert groups == []
        assert any('--keep-folder is required' in log for log in logs)

    def test_no_strategy_keeps_default_order(self, tmp_path) -> None:
        (tmp_path / 'a.jpg').write_bytes(b'\xff\xd8\xff same')
        (tmp_path / 'b.jpg').write_bytes(b'\xff\xd8\xff same')
        groups = utils.find_duplicates(str(tmp_path), delete=False,
                                       keep_strategy=None,
                                       logger_func=lambda x: None)
        assert len(groups) == 1
        assert len(groups[0]) == 2


class TestCompareFolders:

    def test_identical_folders(self, tmp_path) -> None:
        a = tmp_path / 'a'
        b = tmp_path / 'b'
        a.mkdir()
        b.mkdir()
        (a / 'photo.jpg').write_text('same')
        (b / 'photo.jpg').write_text('same')
        logs: list[str] = []
        result = utils.compare_folders(str(a), str(b), logger_func=logs.append)
        assert result['only_in_a'] == []
        assert result['only_in_b'] == []

    def test_files_only_in_a(self, tmp_path) -> None:
        a = tmp_path / 'a'
        b = tmp_path / 'b'
        a.mkdir()
        b.mkdir()
        (a / 'unique.jpg').write_text('only in a')
        (a / 'common.jpg').write_text('shared')
        (b / 'common.jpg').write_text('shared')
        result = utils.compare_folders(str(a), str(b), logger_func=lambda x: None)
        assert 'unique.jpg' in result['only_in_a']
        assert result['only_in_b'] == []

    def test_files_only_in_b(self, tmp_path) -> None:
        a = tmp_path / 'a'
        b = tmp_path / 'b'
        a.mkdir()
        b.mkdir()
        (a / 'common.jpg').write_text('shared')
        (b / 'common.jpg').write_text('shared')
        (b / 'extra.png').write_text('only in b')
        result = utils.compare_folders(str(a), str(b), logger_func=lambda x: None)
        assert result['only_in_a'] == []
        assert 'extra.png' in result['only_in_b']

    def test_both_have_unique_files(self, tmp_path) -> None:
        a = tmp_path / 'a'
        b = tmp_path / 'b'
        a.mkdir()
        b.mkdir()
        (a / 'only_a.jpg').write_text('a')
        (b / 'only_b.jpg').write_text('b')
        result = utils.compare_folders(str(a), str(b), logger_func=lambda x: None)
        assert 'only_a.jpg' in result['only_in_a']
        assert 'only_b.jpg' in result['only_in_b']

    def test_compare_content_detects_differences(self, tmp_path) -> None:
        a = tmp_path / 'a'
        b = tmp_path / 'b'
        a.mkdir()
        b.mkdir()
        (a / 'photo.jpg').write_text('version 1')
        (b / 'photo.jpg').write_text('version 2')
        result = utils.compare_folders(str(a), str(b), compare_content=True,
                                       logger_func=lambda x: None)
        assert 'photo.jpg' in result['different_content']

    def test_compare_content_false_skips_content_check(self, tmp_path) -> None:
        a = tmp_path / 'a'
        b = tmp_path / 'b'
        a.mkdir()
        b.mkdir()
        (a / 'photo.jpg').write_text('version 1')
        (b / 'photo.jpg').write_text('version 2')
        result = utils.compare_folders(str(a), str(b), compare_content=False,
                                       logger_func=lambda x: None)
        assert result['different_content'] == []

    def test_recursive_subfolder_comparison(self, tmp_path) -> None:
        a = tmp_path / 'a'
        b = tmp_path / 'b'
        (a / 'sub').mkdir(parents=True)
        (b / 'sub').mkdir(parents=True)
        (a / 'sub' / 'deep.jpg').write_text('deep')
        (b / 'root.jpg').write_text('root')
        result = utils.compare_folders(str(a), str(b), logger_func=lambda x: None)
        only_a = result['only_in_a']
        only_b = result['only_in_b']
        assert any('deep.jpg' in f for f in only_a)
        assert 'root.jpg' in only_b

    def test_writes_output_file(self, tmp_path) -> None:
        a = tmp_path / 'a'
        b = tmp_path / 'b'
        a.mkdir()
        b.mkdir()
        (a / 'only_a.txt').write_text('a')
        (b / 'only_b.txt').write_text('b')
        report = str(tmp_path / 'report.txt')
        utils.compare_folders(str(a), str(b), output_file=report, logger_func=lambda x: None)
        assert Path(report).exists()
        content = Path(report).read_text()
        assert 'only_a.txt' in content
        assert 'only_b.txt' in content
        assert 'Folder Comparison Report' in content

    def test_nonexistent_folder_returns_empty(self, tmp_path) -> None:
        a = tmp_path / 'a'
        a.mkdir()
        logs: list[str] = []
        result = utils.compare_folders(str(a), str(tmp_path / 'nope'), logger_func=logs.append)
        assert result == {'only_in_a': [], 'only_in_b': [], 'different_content': []}
        assert any('does not exist' in log for log in logs)

    def test_empty_folders(self, tmp_path) -> None:
        a = tmp_path / 'a'
        b = tmp_path / 'b'
        a.mkdir()
        b.mkdir()
        result = utils.compare_folders(str(a), str(b), logger_func=lambda x: None)
        assert result['only_in_a'] == []
        assert result['only_in_b'] == []
        assert result['different_content'] == []


class TestIncrementFilenameSuffix:

    def test_increments_standard_suffix(self) -> None:
        result = utils._increment_filename_suffix('20200315_143022_000.jpg', set())
        assert result == '20200315_143022_001.jpg'

    def test_skips_existing_names(self) -> None:
        existing = {'20200315_143022_001.jpg', '20200315_143022_002.jpg'}
        result = utils._increment_filename_suffix('20200315_143022_000.jpg', existing)
        assert result == '20200315_143022_003.jpg'

    def test_handles_non_standard_filename(self) -> None:
        result = utils._increment_filename_suffix('photo.jpg', set())
        assert result == 'photo_001.jpg'

    def test_preserves_suffix_width(self) -> None:
        result = utils._increment_filename_suffix('20200315_143022_0000.png', set())
        assert result == '20200315_143022_0001.png'


class TestMergeDbs:

    def test_merge_no_conflicts(self, tmp_path) -> None:
        db_a = {'20200315_143022_000.jpg': {'source_name': 'IMG_001.jpg', 'size': 100}}
        db_b = {'20210601_080000_000.jpg': {'source_name': 'IMG_002.jpg', 'size': 200}}
        (tmp_path / 'files.txt').write_text(json.dumps(db_a))
        db_b_path = tmp_path / 'db_b.txt'
        db_b_path.write_text(json.dumps(db_b))
        logs: list[str] = []
        result = utils.merge_dbs(str(tmp_path), str(db_b_path), dry_run=False, logger_func=logs.append)
        assert '20200315_143022_000.jpg' in result
        assert '20210601_080000_000.jpg' in result
        assert len(result) == 2
        assert any('Merged directly: 1' in log for log in logs)

    def test_duplicate_same_key_same_size(self, tmp_path) -> None:
        entry = {'source_name': 'IMG_001.jpg', 'size': 100}
        db_a = {'20200315_143022_000.jpg': dict(entry)}
        db_b = {'20200315_143022_000.jpg': dict(entry)}
        (tmp_path / 'files.txt').write_text(json.dumps(db_a))
        (tmp_path / '20200315_143022_000.jpg').write_bytes(b'x' * 100)
        db_b_path = tmp_path / 'db_b.txt'
        db_b_path.write_text(json.dumps(db_b))
        logs: list[str] = []
        result = utils.merge_dbs(str(tmp_path), str(db_b_path), dry_run=True, logger_func=logs.append)
        assert len(result) == 1
        assert any('Duplicate' in log for log in logs)

    def test_conflict_different_size_renames_key(self, tmp_path) -> None:
        db_a = {'20200315_143022_000.jpg': {'source_name': 'IMG_A.jpg', 'size': 100}}
        db_b = {'20200315_143022_000.jpg': {'source_name': 'IMG_B.jpg', 'size': 200}}
        (tmp_path / 'files.txt').write_text(json.dumps(db_a))
        db_b_path = tmp_path / 'db_b.txt'
        db_b_path.write_text(json.dumps(db_b))
        logs: list[str] = []
        result = utils.merge_dbs(str(tmp_path), str(db_b_path), dry_run=True, logger_func=logs.append)
        assert '20200315_143022_000.jpg' in result
        assert '20200315_143022_001.jpg' in result
        assert result['20200315_143022_001.jpg']['source_name'] == 'IMG_B.jpg'
        assert any('Conflict' in log for log in logs)
        assert any('renaming' in log for log in logs)

    def test_conflict_renames_file_on_disk(self, tmp_path) -> None:
        db_a = {'20200315_143022_000.jpg': {'source_name': 'A.jpg', 'size': 5}}
        db_b = {'20200315_143022_000.jpg': {'source_name': 'B.jpg', 'size': 7}}
        (tmp_path / 'files.txt').write_text(json.dumps(db_a))
        (tmp_path / '20200315_143022_000.jpg').write_text('aaaaa')
        # Simulate B's file already in folder with a different name (OS renamed on copy)
        (tmp_path / 'b_copy.jpg').write_text('bbbbbbb')
        db_b_path = tmp_path / 'db_b.txt'
        db_b_path.write_text(json.dumps(db_b))
        result = utils.merge_dbs(str(tmp_path), str(db_b_path), dry_run=False, logger_func=lambda x: None)
        assert '20200315_143022_001.jpg' in result
        # The file should have been renamed on disk
        assert (tmp_path / '20200315_143022_001.jpg').exists()

    def test_dry_run_does_not_modify(self, tmp_path) -> None:
        db_a = {'20200315_143022_000.jpg': {'source_name': 'A.jpg', 'size': 100}}
        db_b = {'20210601_080000_000.jpg': {'source_name': 'B.jpg', 'size': 200}}
        (tmp_path / 'files.txt').write_text(json.dumps(db_a))
        original_text = (tmp_path / 'files.txt').read_text()
        db_b_path = tmp_path / 'db_b.txt'
        db_b_path.write_text(json.dumps(db_b))
        utils.merge_dbs(str(tmp_path), str(db_b_path), dry_run=True, logger_func=lambda x: None)
        assert (tmp_path / 'files.txt').read_text() == original_text

    def test_empty_db_b_returns_db_a(self, tmp_path) -> None:
        db_a = {'20200315_143022_000.jpg': {'source_name': 'IMG.jpg', 'size': 100}}
        (tmp_path / 'files.txt').write_text(json.dumps(db_a))
        db_b_path = tmp_path / 'db_b.txt'
        db_b_path.write_text('{}')
        logs: list[str] = []
        result = utils.merge_dbs(str(tmp_path), str(db_b_path), dry_run=True, logger_func=logs.append)
        assert result == db_a
        assert any('empty' in log for log in logs)

    def test_nonexistent_folder_returns_empty(self, tmp_path) -> None:
        db_b_path = tmp_path / 'db_b.txt'
        db_b_path.write_text('{}')
        logs: list[str] = []
        result = utils.merge_dbs(str(tmp_path / 'nope'), str(db_b_path), logger_func=logs.append)
        assert result == {}

    def test_nonexistent_db_b_returns_empty(self, tmp_path) -> None:
        (tmp_path / 'files.txt').write_text('{}')
        logs: list[str] = []
        result = utils.merge_dbs(str(tmp_path), str(tmp_path / 'nope.txt'), logger_func=logs.append)
        assert result == {}

    def test_multiple_conflicts_increment_suffix(self, tmp_path) -> None:
        db_a = {
            '20200315_143022_000.jpg': {'source_name': 'A.jpg', 'size': 100},
            '20200315_143022_001.jpg': {'source_name': 'B.jpg', 'size': 150},
        }
        db_b = {
            '20200315_143022_000.jpg': {'source_name': 'C.jpg', 'size': 200},
        }
        (tmp_path / 'files.txt').write_text(json.dumps(db_a))
        db_b_path = tmp_path / 'db_b.txt'
        db_b_path.write_text(json.dumps(db_b))
        result = utils.merge_dbs(str(tmp_path), str(db_b_path), dry_run=True, logger_func=lambda x: None)
        # _001 already taken by db_a, so B's conflict should go to _002
        assert '20200315_143022_002.jpg' in result
        assert result['20200315_143022_002.jpg']['source_name'] == 'C.jpg'

    def test_duplicate_deletes_file_on_disk(self, tmp_path) -> None:
        db_a = {'20200315_143022_000.jpg': {'source_name': 'IMG.jpg', 'size': 10}}
        db_b = {'20200315_143022_000.jpg': {'source_name': 'IMG.jpg', 'size': 10}}
        (tmp_path / 'files.txt').write_text(json.dumps(db_a))
        (tmp_path / '20200315_143022_000.jpg').write_bytes(b'0123456789')
        # Simulate a second identical copy the user moved in
        sub = tmp_path / 'sub'
        sub.mkdir()
        (sub / 'dup_copy.jpg').write_bytes(b'0123456789')
        db_b_path = tmp_path / 'db_b.txt'
        db_b_path.write_text(json.dumps(db_b))
        result = utils.merge_dbs(str(tmp_path), str(db_b_path), dry_run=False, logger_func=lambda x: None)
        assert len(result) == 1
        # The duplicate file should be deleted
        assert not (sub / 'dup_copy.jpg').exists()
