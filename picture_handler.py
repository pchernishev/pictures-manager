import re
import filecmp
from os import listdir, remove, mkdir
from os.path import isfile, join, isdir, getsize, exists, getmtime, getctime, getatime, basename, splitext
from argparse import ArgumentParser
from collections import defaultdict
from shutil import move
import json
from PIL import Image
from datetime import datetime
import imghdr

from logger import logger
import regex_patterns
import filtering
import utils

DATE_TIME_ORIGINAL_KEY = 36867


def main():
    parser = create_parser()
    args = parser.parse_args()
    logger.info('Handling started')
    handler = PicturesHandler(args.src, args.dst, args.filter, args.ignore, args.dry_run, args.recursive)
    handler.handle()
    handler.output()
    logger.info('Handling finished\n')


def create_parser():
    parser = ArgumentParser(description="Pictures Handler parameters")
    parser.add_argument("--src", '-s', dest="src", type=str, help="Folder to parse")
    parser.add_argument("--dst", '-d', dest="dst", type=str, help="Folder copy pictures to")
    parser.add_argument('--filter', '-f', dest='filter', type=str, nargs='+',
                        help="Methods for pictures fitering before copy, separated by whitespace")
    parser.add_argument('--ignore', '-i', dest='ignore', type=str, nargs='+',
                        help="Regexs surrounded by \" for pictures names to ignore, separated by whitespace")
    parser.add_argument('--not-recursive', '--nr', dest='recursive', action='store_true', default=True)
    parser.add_argument('--dry-run', '--dr', dest='dry_run', action='store_true', default=False)
    return parser


class PicturesHandler:
    def __init__(self, src, dst, filters=None, ignore_regexs=None,
                 dry_run=False, recursive=True, db_path='files.txt'):
        if not src or not dst:
            raise ValueError('Manadatory parameter source folder or destination folder is missing')
        if filters:
            invalid_filters = set(filters) - set(filtering.available_filter_types)
            if invalid_filters:
                raise ValueError('Invalid filters passed {}. Expected no filters or one of the following {}'.format(
                    invalid_filters, filtering.available_filter_types))
            self.filter = filtering.get_filter(filters)

        self.src = unicode(src)
        self.dst = unicode(dst)
        self.db_path = db_path
        self.recursive = recursive
        self.dry_run = dry_run
        self.ignore_regexs = [re.compile(r'{}'.format(regex)) for regex in ignore_regexs] if ignore_regexs else []

        self.db_files = {}
        self.all_handled_names = []
        self.ignored = []
        self.sizes_files = defaultdict(list)
        self.matched = defaultdict(list)
        self.unmatched = []
        self.not_passed_filters = []
        self.destination_formats = defaultdict(list)
        self.destination_not_matched = []
        self.ready_to_add = defaultdict(list)
        self.added_files = []
        self.moved = {}
        self.unmoved = {}
        self.not_deleted = []
        self.min_date_taken = []

    def output(self):
        logger.info('\n\n*****Following files wern\'t matched')
        for item in self.unmatched:
            logger.info(u'Unmatched  {}'.format(item))
        logger.info('*****Total {} files wern\'t matched'.format(len(self.unmatched)))

        counter = 0
        logger.info('\n\n*****Following files were matched')
        for key, matches in self.matched.iteritems():
            if len(matches) > 1:
                logger.info(u'*****Matched Group: {}'.format(key))
            for match in matches:
                counter += 1
                logger.info(u'{}Matched: {file} Folder: {folder}'.format('\t' if len(matches) > 1 else '', **match))
        logger.info('*****Total {} files matched'.format(counter))

        logger.info(u'\n\n*****Following files were found at destination directory {}'.format(self.dst))
        # counter = 0
        # for key, matches in self.destination_files.iteritems():
        #     if len(matches) > 1:
        #         logger.info('***Dest group: {}'.format(key))
        #     for match in matches:
        #         counter += 1
        #         logger.info('{}Dest: {file} '.format('\t' if len(matches) > 1 else '', **match))
        logger.info(u'*****Total {} formats found at destination directory {}'.format(
            len(self.destination_formats), self.dst))
        logger.info(u'*****Total {} files found and matched at destination directory {}'.format(
            sum([len(val) for val in self.destination_formats.values()]), self.dst))

        logger.info(u'\n\n******Following files found but not matched at destination directory {}'.format(self.dst))
        for item in self.destination_not_matched:
            logger.info(u'Dest Not Matched. {}'.format(item))
        logger.info('*****Total {} files found but not matched at destination directory '.format(
            len(self.destination_not_matched)))
        logger.info('\n\n******Following files matched but not pass filters')
        for item in self.not_passed_filters:
            logger.info(u'Not Added. {}'.format(item[1]))
        logger.info('*****Total {} files matched but not added '.format(len(self.not_passed_filters)))

        logger.info('\n\n*****Following files are ready to be added')
        counter = 0
        for key, matches in self.ready_to_add.iteritems():
            if len(matches) > 1:
                logger.info(u'***Ready group: {}'.format(key))
            for match in matches:
                counter += 1
                logger.info(u'{}Ready File: {file}, New File Name: {new_file_name}'.format(
                    '\t' if len(matches) > 1 else '', **match))
        logger.info('*****Total {} files ready to be added'.format(counter))

        logger.info('\n\n*****Following files were ignored')
        for item in self.ignored:
            logger.info(u'{}'.format(item))
        logger.info('*****Total {} files were ignored'.format(len(self.ignored)))

        logger.info('\n\n*****Following files new name created by taken min date')
        for name, props in self.min_date_taken:
            logger.info(u'{}. Props{}'.format(name, props))
        logger.info('*****Total {} files new name created by taken min date'.format(len(self.min_date_taken)))

        if not self.dry_run:
            logger.info('\n\n*****Following files failed to be moved')
            for item, reason in self.unmoved.iteritems():
                logger.info(u'Unmoved. {}. {}'.format(item, reason))
            logger.info('*****Total {} files failed to be moved'.format(len(self.unmoved)))

            logger.info('******Moved files dict')
            logger.info(json.dumps(self.moved, indent=4))
            logger.info(u'*****Total {} files were moved to {}'.format(len(self.moved), self.dst))

            logger.info('\n\n*****Following files failed to be deleted')
            for f in self.not_deleted:
                logger.info(u'Not deleted {}. Reason: {}'.format(f[0], f[1]))
            logger.info('*****Total {} files wern\'t deleted'.format(len(self.not_deleted)))

    def handle(self):
        self._load_db()
        self._handle_destination_folder(self.dst)
        self._handle_source_folder(self.src, self.recursive)
        self._prepare_new_files_for_copy()
        if not self.dry_run:
            self._move_prepared_files()
            self._update_db()
            self._delete_not_added()

    def _load_db(self):
        self.db_files = utils.load_db_files(self.dst)
        for src, dst in self.db_files.iteritems():
            self.all_handled_names += [basename(src), basename(dst)]

    def _delete_not_added(self):
        for f in self.not_passed_filters:
            try:
                remove(f[0])
            except Exception, e:
                self.not_deleted.append((f[0], 'Error {} {}'.format(e.__class__.__name__, e.message)))

    def _update_db(self):
        self.db_files.update(self.moved)
        utils.save_db_files(self.db_files, self.dst, 'files_1.txt')

    def _prepare_new_files_for_copy(self):
        def get_new_filename():
            return regex_patterns.NEW_FILE_FORMAT.format(
                regex_patterns.DESTINATION_FORMAT_NO_SUFFIX_NO_EXTENSION.format(**match).replace(
                    'None', '00'), suffix, **match)

        def get_new_suffix(file_props_list):
            return regex_patterns.NEW_SUFFIX_FORMAT.format(
                max([int(props['suffix']) for props in file_props_list]) + 1)

        for key, matches in self.matched.iteritems():
            for match in matches:
                file_format = regex_patterns.DESTINATION_FORMAT_NO_SUFFIX.format(**match).replace('None', '00')
                if file_format not in self.destination_formats.keys() + self.ready_to_add.keys():
                    suffix = '000'
                elif file_format in self.ready_to_add:
                    suffix = get_new_suffix(self.ready_to_add[file_format])
                else:  # file_format in self.destination_files
                    suffix = get_new_suffix(self.destination_formats[file_format])
                    # sizes = [(join(prop['folder'], prop['file']), prop['size']) for prop
                    #          in self.ready_to_add[file_format] + self.destination_files[file_format]]
                    # if match['size'] in [size[1] for size in sizes]:
                    #     filename, size = next(size for size in sizes if size[1] == match['size'])
                    #     self.not_passed_filters.append((join(match['folder'], match['file']),
                    #                                    'File {} has the same name and size {}'.format(
                    # filename, size)))
                    #     continue
                match['suffix'] = suffix
                match['new_file_name'] = get_new_filename()
                self.ready_to_add[file_format].append(match)

    def _update_common_file_props(self, file, folder):
        properties = {}
        full_path = join(folder, file)
        size = getsize(full_path)
        properties['fullpath'] = full_path
        properties['folder'] = folder
        properties['size'] = size
        properties['file'] = file
        properties['extension'] = splitext(full_path)[1].lstrip('.')
        return properties

    def _handle_destination_folder(self, folder, recursive=True):
        if not exists(folder):
            mkdir(folder)

        if recursive:
            dirs = [join(folder, d) for d in listdir(folder) if isdir(join(folder, d)) and
                    join(folder, d).lower() != self.src.lower()]
            for d in dirs:
                self._handle_destination_folder(d)
        files = [f for f in listdir(folder) if isfile(join(folder, f))]
        for f in files:
            match = re.match(regex_patterns.DESTINATION_REGEX, f)
            if not match:
                self.destination_not_matched.append(f)
                continue
            properties = self._update_common_file_props(f, folder)
            properties.update(match.groupdict())
            # Create key with no suffix
            key = regex_patterns.DESTINATION_FORMAT_NO_SUFFIX.format(**properties)
            self.destination_formats[key].append(properties)
            self.sizes_files[properties['size']].append(properties['fullpath'])

    def _handle_source_folder(self, folder, recursive):
        if recursive:
            dirs = [join(folder, d) for d in listdir(folder) if isdir(join(folder, d)) and
                    join(folder, d).lower() != self.dst.lower()]
            for d in dirs:
                self._handle_source_folder(d, recursive)
        files = [f for f in listdir(folder) if isfile(join(folder, f))]
        for f in files:
            if any(regex.match(f) for regex in self.ignore_regexs):
                self.ignored.append(u'{}. Folder: {}'.format(f, folder))
                continue

            match = re.match(regex_patterns.ACCEPTABLE_REGEX_DICT, f)
            if not match:
                self.unmatched.append(join(folder, f))
                continue

            properties = self._update_common_file_props(f, folder)
            full_path = properties['fullpath']
            size = properties['size']
            logger.info('TYPE {}. File {}'.format(imghdr.what(full_path), f))
            try:
                date_taken = None
                img = Image.open(full_path)
                if hasattr(img, '_getexif'):
                    _getexif = img._getexif()
                    if _getexif and DATE_TIME_ORIGINAL_KEY in _getexif:
                        date_taken = _getexif[DATE_TIME_ORIGINAL_KEY]
                if not date_taken and hasattr(img, 'tag'):
                    logger.info('tag exists {}'.format(f))
                    date_taken = img.tag._tagdata[DATE_TIME_ORIGINAL_KEY]
                if date_taken:
                    properties.update(re.match(regex_patterns.DATE_TAKEN_REGEX, date_taken).groupdict())
            except (KeyError, IOError) as e:
                logger.error(u'KeyError, IOError {}. Reason: {}'.format(f, e.message))
                if isinstance(e, IOError) and 'cannot identify image file' not in e.message \
                        or isinstance(e, KeyError) and e.message != DATE_TIME_ORIGINAL_KEY:
                    raise
            except Exception as e:
                logger.error(u'Exception {}. Reason: {}'.format(f, e.message))

            if not date_taken:
                properties.update(match.groupdict())
                if not all(properties.get(key, None) for key in ['year', 'month', 'day']):
                    min_date = min([getatime(full_path), getmtime(full_path), getctime(full_path)])
                    dt = datetime.fromtimestamp(min_date)

                    def format_func(num):
                        return '{:0=2d}'.format(num)
                    update_dict = {
                        'year': str(dt.year), 'month': format_func(dt.month),
                        'day': format_func(dt.day), 'hour': format_func(dt.hour),
                        'minute': format_func(dt.minute), 'second': format_func(dt.second)
                    }
                    properties.update(update_dict)
                    self.min_date_taken.append((f, update_dict))

            filters = [_filter.name for _filter in self.filter.filters]
            passed_filter = True
            errors = []
            # Name Filets
            if filtering.NameFilter.name in filters:
                if f in self.all_handled_names:
                    errors.append(u'NAME: {}'.format(f))
                    passed_filter = False

            # Size Filter
            if passed_filter and filtering.BinaryFilter.name in filters:
                if size in self.sizes_files:
                    for _f in self.sizes_files[size]:
                        if filecmp.cmp(_f, full_path, shallow=False):
                            errors.append(u'BINARY: {} same as {} {}'.format(full_path, _f, size))
                            passed_filter = False
                            break

            if passed_filter:
                self.matched[f].append(properties)
                self.sizes_files[size].append(full_path)
            else:
                self.not_passed_filters.append((full_path, '; '.join(errors)))

    def _move_prepared_files(self):
        for fg, files in self.ready_to_add.iteritems():
            for f in files:
                new_file_path = join(self.dst, f['new_file_name'])
                full_path = join(f['folder'], f['file'])
                try:
                    if exists(new_file_path):
                        self.unmoved[full_path] = u'Exists {}'.format(new_file_path)
                        continue
                    move(full_path, new_file_path)
                    self.moved[full_path] = new_file_path
                except Exception, e:
                    msg = 'Error {} {}'.format(e.__class__.__name__, e.message)
                    self.unmoved[full_path] = msg

if __name__ == "__main__":
    main()
