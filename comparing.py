import filecmp
from os.path import getsize, basename
import sys
import inspect


class Comparer(object):

    def __init__(self, dest_files):
        self.destination_files = dest_files

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


class CompositionComparer(Comparer):

    def __init__(self, comparers):
        # super(CompositionComparer, self).__init__(dest_files)
        self.comparers = comparers

    # def initialize(self):
    #     for _compare in self.comparers:
    #         _compare.initialize()

    def pass_compare(self, file_path1, file_path2):
        for _compare in self.comparers:
            if not _compare.pass_compare():
                return False
        return True


AVAILABLE_COMPARERS = dict([(m[0].lower().replace(Comparer.__name__, ''), m[1])
                            for m in inspect.getmembers(sys.modules[__name__], inspect.isclass)
                            if issubclass(m[1], Comparer) and m[1] != Comparer])


def get_comparer(comparer):
    ''' Compare methods factory'''
    ret_val = None
    if isinstance(comparer, list):
        compare_methods = []
        for _type in comparer:
            compare_methods.append(get_comparer(_type))
        ret_val = AVAILABLE_COMPARERS[CompositionComparer.__name__](compare_methods)
    else:
        if comparer not in AVAILABLE_COMPARERS:
            raise ValueError('Incompatible compare parameter {} passed'.format(comparer))
        ret_val = AVAILABLE_COMPARERS[comparer]()

    return ret_val
