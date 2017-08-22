import filecmp
from os.path import getsize, basename
import sys
import inspect


class Comparer(object):

    def __init__(self):
        pass

    def pass_compare(self, file1, file2):
        raise NotImplementedError()


class BinaryComparer(Comparer):

    def pass_compare(self, file_path1, file_path2):
        return not filecmp.cmp(file_path1, file_path2, shallow=False)


class NameComparer(Comparer):

    def initialize(self):
        raise NotImplementedError()

    def pass_compare(self, file_path1, file_path2):
        return basename(file_path1) != basename(file_path2)


class SizeComparer(Comparer):

    def pass_compare(self, file_path1, file_path2):
        return getsize(file_path1) != getsize(file_path2)


AVAILABLE_COMPARERS = dict([(m[0].replace(Comparer.__name__, '').lower(), m[1])
                            for m in inspect.getmembers(sys.modules[__name__], inspect.isclass)
                            if issubclass(m[1], Comparer) and m[1] != Comparer])


def get_comparer(comparer):
    ''' Compare methods factory'''
    if comparer not in AVAILABLE_COMPARERS:
        raise ValueError('Incompatible compare parameter {} passed'.format(comparer))
    return AVAILABLE_COMPARERS[comparer]()
