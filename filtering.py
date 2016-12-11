import filecmp
from os.path import getsize, basename


class Compare(object):
    name = ''

    def initialize(self, dest_files):
        self.destination_files = dest_files

    def pass_compare(self, file1, file2):
        raise NotImplementedError()


class BinaryCompare(Compare):
    name = 'binary'

    def initialize(self):
        raise NotImplementedError()

    def pass_compare(self, file_path1, file_path2):
        return not filecmp.cmp(file_path1, file_path2, shallow=False)


class NameCompare(Compare):
    name = 'name'

    def initialize(self):
        raise NotImplementedError()

    def pass_compare(self, file_path1, file_path2):
        return basename(file_path1) != basename(file_path2)


class SizeCompare(Compare):
    name = 'size'

    def initialize(self):
        raise NotImplementedError()

    def pass_compare(self, file_path1, file_path2):
        return getsize(file_path1) != getsize(file_path2)


class CompositionCompare(Compare):
    name = 'multiple'

    def __init__(self, compare_methods):
        # super(CompositionCompare, self).__init__(dest_files)
        self.compare_methods = compare_methods

    def initialize(self):
        for _compare in self.compare_methods:
            _compare.initialize()

    def pass_compare(self, file_path1, file_path2):
        for _compare in self.compare_methods:
            if not _compare.pass_compare():
                return False
        return True

available_compare_types = [BinaryCompare.name, NameCompare.name, SizeCompare.name, CompositionCompare.name]
compare_initializers = {
    BinaryCompare.name: BinaryCompare,
    NameCompare.name: NameCompare,
    SizeCompare.name: SizeCompare,
    CompositionCompare.name: CompositionCompare
}


def get_compare():
    ''' Compare methods factory'''
    ret_val = None
    if isinstance(compare_type, list):
        compare_methods = []
        for _type in compare_type:
            compare_methods.append(get_compare(_type))
        ret_val = compare_initializers[CompositionCompare.name](compare_methods)
    else:
        if compare_type not in available_compare_types:
            raise ValueError('Incompatible compare type {}'.format(compare_type))
        ret_val = compare_initializers[compare_type]()

    return ret_val
