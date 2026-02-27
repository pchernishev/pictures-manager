from __future__ import annotations

import filecmp
from pathlib import Path
import sys
import inspect


class Comparer:

    def __init__(self) -> None:
        pass

    def pass_compare(self, file1: str, file2: str) -> bool:
        raise NotImplementedError()


class BinaryComparer(Comparer):

    def pass_compare(self, file_path1: str, file_path2: str) -> bool:
        return not filecmp.cmp(file_path1, file_path2, shallow=False)


class NameComparer(Comparer):

    def initialize(self) -> None:
        raise NotImplementedError()

    def pass_compare(self, file_path1: str, file_path2: str) -> bool:
        return Path(file_path1).name != Path(file_path2).name


class SizeComparer(Comparer):

    def pass_compare(self, file_path1: str, file_path2: str) -> bool:
        return Path(file_path1).stat().st_size != Path(file_path2).stat().st_size


AVAILABLE_COMPARERS: dict[str, type[Comparer]] = {
    m[0].replace(Comparer.__name__, '').lower(): m[1]
    for m in inspect.getmembers(sys.modules[__name__], inspect.isclass)
    if issubclass(m[1], Comparer) and m[1] != Comparer
}


def get_comparer(comparer: str) -> Comparer:
    ''' Compare methods factory'''
    if comparer not in AVAILABLE_COMPARERS:
        raise ValueError(f'Incompatible compare parameter {comparer} passed')
    return AVAILABLE_COMPARERS[comparer]()
