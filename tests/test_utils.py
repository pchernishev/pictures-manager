from __future__ import annotations

import os
import json
import pytest
import sys

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


class TestSyncFolderAndDb:

    def test_dry_run_does_not_modify_db(self, tmp_path) -> None:
        db_data = {'old/photo.jpg': str(tmp_path / 'missing.jpg')}
        db_file = tmp_path / 'files.txt'
        db_file.write_text(json.dumps(db_data))
        logs: list[str] = []
        utils.sync_folder_and_db(str(tmp_path), dry_run=True, logger_func=logs.append)
        reloaded = json.loads(db_file.read_text())
        assert reloaded == db_data

    def test_non_dry_run_removes_missing_from_db(self, tmp_path) -> None:
        present_file = tmp_path / 'present.jpg'
        present_file.write_text('data')
        old_dir = tmp_path / 'old'
        present_src_key = str(old_dir / 'present_src.jpg')
        gone_src_key = str(old_dir / 'gone_src.jpg')
        db_data = {
            present_src_key: str(tmp_path / 'present.jpg'),
            gone_src_key: str(tmp_path / 'gone.jpg'),
        }
        db_file = tmp_path / 'files.txt'
        db_file.write_text(json.dumps(db_data))
        logs: list[str] = []
        utils.sync_folder_and_db(str(tmp_path), dry_run=False, logger_func=logs.append)
        reloaded = json.loads(db_file.read_text())
        assert gone_src_key not in reloaded
        assert present_src_key in reloaded

    def test_finds_files_in_subdirectories(self, tmp_path) -> None:
        sub = tmp_path / 'subdir'
        sub.mkdir()
        sub_file = sub / 'deep_photo.jpg'
        sub_file.write_text('deep data')
        src_key = str(tmp_path / 'orig' / 'deep_photo_src.jpg')
        db_data = {src_key: str(sub_file)}
        db_file = tmp_path / 'files.txt'
        db_file.write_text(json.dumps(db_data))
        logs: list[str] = []
        utils.sync_folder_and_db(str(tmp_path), dry_run=False, logger_func=logs.append)
        reloaded = json.loads(db_file.read_text())
        assert src_key in reloaded


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

    def test_updates_db_after_move(self, tmp_path) -> None:
        f1 = tmp_path / '20200315_143022_000.jpg'
        f1.write_text('photo data')
        src_key = str(tmp_path / 'old' / 'IMG_001.jpg')
        db_data = {src_key: str(f1)}
        (tmp_path / 'files.txt').write_text(json.dumps(db_data))
        utils.organize_by_year(str(tmp_path), dry_run=False, logger_func=lambda x: None)
        reloaded = json.loads((tmp_path / 'files.txt').read_text())
        new_dst = reloaded[src_key]
        assert '2020' in new_dst
        assert new_dst.endswith('20200315_143022_000.jpg')

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

    def test_updates_db_with_month_path(self, tmp_path) -> None:
        f1 = tmp_path / '20200315_143022_000.jpg'
        f1.write_text('photo')
        src_key = str(tmp_path / 'old' / 'IMG_001.jpg')
        db_data = {src_key: str(f1)}
        (tmp_path / 'files.txt').write_text(json.dumps(db_data))
        utils.organize_by_year(str(tmp_path), dry_run=False, by_month=True, logger_func=lambda x: None)
        reloaded = json.loads((tmp_path / 'files.txt').read_text())
        new_dst = reloaded[src_key]
        assert '2020' in new_dst
        assert '03' in new_dst
        assert new_dst.endswith('20200315_143022_000.jpg')


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
