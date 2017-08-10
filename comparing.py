import filecmp
from os.path import getsize, basename


class Comparer(object):

    def __init__(self, dest_files):
        self.destination_files = dest_files

    @classmethod
    def name(cls):
        return cls.__name__.lower().replace('comparer', '')

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

AVAILABLE_COMPARER_TYPES = [BinaryComparer.name(), NameComparer.name(), SizeComparer.name(), CompositionComparer.name()]
COMPARER_INITIALIZERS = {
    BinaryComparer.name(): BinaryComparer,
    NameComparer.name(): NameComparer,
    SizeComparer.name(): SizeComparer,
    CompositionComparer.name(): CompositionComparer
}


def get_comparer(comparer):
    ''' Compare methods factory'''
    ret_val = None
    if isinstance(comparer, list):
        compare_methods = []
        for _type in comparer:
            compare_methods.append(get_comparer(_type))
        ret_val = COMPARER_INITIALIZERS[CompositionComparer.name](compare_methods)
    else:
        if comparer not in AVAILABLE_COMPARER_TYPES:
            raise ValueError('Incompatible comparer type {}'.format(comparer))
        ret_val = COMPARER_INITIALIZERS[comparer]()

    return ret_val
