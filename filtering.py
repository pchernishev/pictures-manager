import filecmp
from os.path import getsize, basename


class Filter:
    name = ''

    def pass_filter(self, file1, file2):
        raise NotImplementedError()


class BinaryFilter(Filter):
    name = 'binary'

    def pass_filter(self, file_path1, file_path2):
        return not filecmp.cmp(file_path1, file_path2, shallow=False)


class NameFilter(Filter):
    name = 'name'

    def pass_filter(self, file_path1, file_path2):
        return basename(file_path1) != basename(file_path2)


class SizeFilter(Filter):
    name = 'size'

    def pass_filter(self, file_path1, file_path2):
        return getsize(file_path1) != getsize(file_path2)


class CompositionFilter(Filter):
    name = 'multiple'

    def __init__(self, filters=None):
        self.filters = filters

    def pass_filter(self, file_path1, file_path2):
        for _filter in self.filters:
            if not _filter.pass_filter():
                return False
        return True

available_filter_types = [BinaryFilter.name, NameFilter.name, SizeFilter.name]
filter_initializers = {
    BinaryFilter.name: BinaryFilter,
    NameFilter.name: NameFilter,
    SizeFilter.name: SizeFilter,
    CompositionFilter.name: CompositionFilter
}


def get_filter(filter_type):
    ''' Filters factory method'''
    ret_val = None
    if isinstance(filter_type, list):
        filters = []
        for _type in filter_type:
            filters.append(get_filter(_type))
        ret_val = filter_initializers[CompositionFilter.name](filters)
    else:
        if filter_type not in available_filter_types:
            raise ValueError('Incompatible filter type {}'.format(filter_type))
        ret_val = filter_initializers[filter_type]()

    return ret_val