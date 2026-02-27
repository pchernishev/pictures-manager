from __future__ import annotations

import os
import tempfile
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import comparing


class TestComparerFactory:

    def test_get_binary_comparer(self) -> None:
        comparer = comparing.get_comparer('binary')
        assert isinstance(comparer, comparing.BinaryComparer)

    def test_get_name_comparer(self) -> None:
        comparer = comparing.get_comparer('name')
        assert isinstance(comparer, comparing.NameComparer)

    def test_get_size_comparer(self) -> None:
        comparer = comparing.get_comparer('size')
        assert isinstance(comparer, comparing.SizeComparer)

    def test_get_invalid_comparer_raises(self) -> None:
        with pytest.raises(ValueError, match='Incompatible compare parameter'):
            comparing.get_comparer('nonexistent')

    def test_available_comparers_keys(self) -> None:
        assert 'binary' in comparing.AVAILABLE_COMPARERS
        assert 'name' in comparing.AVAILABLE_COMPARERS
        assert 'size' in comparing.AVAILABLE_COMPARERS


class TestBinaryComparer:

    def test_identical_files_fail_compare(self, tmp_path: str) -> None:
        f1 = tmp_path / 'file1.txt'
        f2 = tmp_path / 'file2.txt'
        f1.write_text('identical content')
        f2.write_text('identical content')
        comparer = comparing.BinaryComparer()
        assert comparer.pass_compare(str(f1), str(f2)) is False

    def test_different_files_pass_compare(self, tmp_path: str) -> None:
        f1 = tmp_path / 'file1.txt'
        f2 = tmp_path / 'file2.txt'
        f1.write_text('content A')
        f2.write_text('content B')
        comparer = comparing.BinaryComparer()
        assert comparer.pass_compare(str(f1), str(f2)) is True


class TestNameComparer:

    def test_same_name_fail_compare(self, tmp_path: str) -> None:
        f1 = tmp_path / 'sub1' / 'photo.jpg'
        f2 = tmp_path / 'sub2' / 'photo.jpg'
        f1.parent.mkdir()
        f2.parent.mkdir()
        f1.write_text('a')
        f2.write_text('b')
        comparer = comparing.NameComparer()
        assert comparer.pass_compare(str(f1), str(f2)) is False

    def test_different_name_pass_compare(self, tmp_path: str) -> None:
        f1 = tmp_path / 'photo1.jpg'
        f2 = tmp_path / 'photo2.jpg'
        f1.write_text('a')
        f2.write_text('b')
        comparer = comparing.NameComparer()
        assert comparer.pass_compare(str(f1), str(f2)) is True


class TestSizeComparer:

    def test_same_size_fail_compare(self, tmp_path: str) -> None:
        f1 = tmp_path / 'file1.txt'
        f2 = tmp_path / 'file2.txt'
        f1.write_text('abcd')
        f2.write_text('efgh')
        comparer = comparing.SizeComparer()
        assert comparer.pass_compare(str(f1), str(f2)) is False

    def test_different_size_pass_compare(self, tmp_path: str) -> None:
        f1 = tmp_path / 'file1.txt'
        f2 = tmp_path / 'file2.txt'
        f1.write_text('short')
        f2.write_text('much longer content here')
        comparer = comparing.SizeComparer()
        assert comparer.pass_compare(str(f1), str(f2)) is True
