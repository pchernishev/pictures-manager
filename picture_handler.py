#!/usr/bin/python

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
import logging
import regex_patterns
import comparing
import utils

DATE_TIME_ORIGINAL_KEY = 36867


def main():
    parser = create_parser()
    args = parser.parse_args()

    logging.getLogger("PIL.TiffImagePlugin").setLevel(logging.INFO)

    logger.info('Handling started')
    handler = PicturesHandler(args.src, args.dst, comparers=args.compare, ignore_regexs=args.ignore,
                              dry_run=args.dry_run, recursive=args.recursive, accept_regexs=args.accept)
    if args.sync:
        utils.sync_folder_and_db(handler.dst, handler.recursive, handler.dry_run, logger.info);
        return

    handler.handle()
    handler.output()
    logger.info('Handling finished\n')


def create_parser():
    parser = ArgumentParser(description="Pictures Handler parameters")
    parser.add_argument("--src", '-s', dest="src", type=str, help="Folder to parse")
    parser.add_argument("--dst", '-d', dest="dst", type=str, help="Folder copy pictures to")
    parser.add_argument('--compare', '-c', dest='compare', type=str, nargs='+',
                        help='Methods for comparing pictures, separated by whitespace.\n'
                        'Already handled picture will be ignored.\n'
                        'Possible Compare methods: {}'.format(comparing.AVAILABLE_COMPARERS.keys()))
    parser.add_argument('--ignore', '-i', dest='ignore', type=str, nargs='+',
                        help='Regexs surrounded by " for picture names to ignore, separated by whitespace')
    parser.add_argument('--accept', '-a', dest='accept', type=str, nargs='+',
                        help='Regexs surrounded by " for picture names to accept, separated by whitespace.\n'
                        'In case parameter not specified all files accepted.\n'
                        'preset "default" "camera" "mobile" regex can be specified')
    # '{}'.format(regex_patterns.ACCEPTABLE_REGEXS))
    parser.add_argument('--not-recursive', '--nr', dest='recursive', action='store_true', default=True)
    parser.add_argument('--dry-run', '--dr', dest='dry_run', action='store_true', default=False)
    parser.add_argument('--sync-folder-and-db', '--sync', dest='sync', action='store_true', default=False)
    return parser


class PicturesHandler(object):

    def __init__(self, src, dst, comparers=None, ignore_regexs=None, dry_run=False, recursive=False,
                 accept_regexs=None, sync=False, db_path='files.txt'):
        if not src or not dst:
            raise ValueError('Manadatory parameter source folder or destination folder is missing')
        if comparers:
            self.comparers = dict((c, comparing.get_comparer(c)) for c in comparers)

        self.src = str(src) # unicode(src)
        self.dst = str(dst) # unicode(dst)
        self.db_path = db_path
        self.recursive = recursive
        self.dry_run = dry_run
        self.ignore_regexs = [re.compile(r'{}'.format(regex)) for regex in ignore_regexs] if ignore_regexs else []
        self.sync_folder_and_db = sync

        if accept_regexs:
            if 'default' in accept_regexs:
                accept_regexs.remove('default')
                accept_regexs += regex_patterns.ACCEPTABLE_REGEXS
            if 'mobile' in accept_regexs:
                accept_regexs.remove('mobile')
                accept_regexs.append(regex_patterns.ACCEPTABLE_REGEXS[0])
            if 'camera' in accept_regexs:
                accept_regexs.remove('camera')
                accept_regexs.append(regex_patterns.ACCEPTABLE_REGEXS[1])

        self.acceptable_regexs = [re.compile(r'{}'.format(regex)) for regex in accept_regexs] if accept_regexs else []

        self.db_files = {}
        self.all_handled_names = []
        self.ignored = []
        self.sizes_files = defaultdict(list)
        self.matched = defaultdict(list)
        self.matched_regex = []
        self.unmatched = []
        self.not_passed_comparison = []
        self.destination_formats = defaultdict(list)
        self.destination_not_matched = []
        self.ready_to_add = defaultdict(list)
        self.added_files = []
        self.moved = {}
        self.unmoved = {}
        self.not_deleted = []
        self.min_date_taken = []
        self.unsupported = []
        self.num_of_dst_files = 0

    def output(self):

        # logger.info(u'*****Following files were found at destination directory {}'.format(self.dst))
        # counter = 0
        # for key, matches in self.destination_files.items():
            # if len(matches) > 1:
            #     logger.info('***Dest group: {}'.format(key))
            # for match in matches:
            #     counter += 1
                # logger.info('{}Dest: {file} '.format('\t' if len(matches) > 1 else '', **match))
        logger.info('*****Total {} files found at destination directory {}\n'.format(
            self.num_of_dst_files, self.dst))
        logger.info(u'*****Total {} formats found at destination directory'.format(
           len(self.destination_formats)))
        logger.info(u'*****Total {} files found and matched at destination directory {}'.format(
            sum([len(val) for val in self.destination_formats.values()]), self.dst))
        logger.info('*****Total {} files found but not matched at destination directory\n'.format(
            len(self.destination_not_matched)))
        for item in self.destination_not_matched:
            logger.info(u'Destination Not Matched: {}'.format(item))

        logger.info('\n')
        # logger.info('*****Following files wern\'t matched')
        logger.info('*****Total {} files wern\'t matched\n'.format(len(self.unmatched)))
        for item in self.unmatched:
            logger.info(u'Unmatched  {}'.format(item))

        # logger.info('******Following files matched but not pass comparison')
        logger.info('*****Total {} files matched not pass comparison\n'.format(len(self.not_passed_comparison)))
        for item in self.not_passed_comparison:
            logger.info(u'Not passed compare {}'.format(item[1]))

        # logger.info('******Following files matched regex')
        # logger.info('*****Total {} files matched regex\n'.format(len(self.matched_regex)))
        # for item in self.matched_regex:
        #     logger.info(u'{}'.format(item))

        # logger.info('****Following files were ignored')
        logger.info('*****Total {} files were ignored\n'.format(len(self.ignored)))
        for item in self.ignored:
            logger.info(u'{}'.format(item))

        # logger.info('*****Following files new name created by taken min date')
        # for name, props in self.min_date_taken:
        #     logger.info(u'{}. Props{}'.format(name, props))
        logger.info('*****Total {} files new name created by taken min date\n'.format(len(self.min_date_taken)))

        # logger.info('*****Following files are of unsupported type')
        logger.info('*****Total {} files are of unsupported type\n'.format(len(self.unsupported)))
        for item in self.unsupported:
            logger.info(u'{}'.format(item))

        counter = 0
        # logger.info('*****Following files were matched')
        for key, matches in self.matched.items():
            # if len(matches) > 1:
            #     logger.info(u'*****Matched Group: {}'.format(key))
            for match in matches:
                counter += 1
                # logger.info(u'{}Matched: {file} Folder: {folder}'.format('\t' if len(matches) > 1 else '', **match))
        logger.info('*****Total {} files matched\n'.format(counter))

        logger.info('*****Following files are ready to be added')
        counter = 0
        for key, matches in self.ready_to_add.items():
            if len(matches) > 1:
                logger.info(u'***Ready group: {}'.format(key))
            for match in matches:
                counter += 1
                logger.info(u'{}Ready File: {file}, New File Name: {new_file_name}'.format(
                    '\t' if len(matches) > 1 else '', **match))
        logger.info('*****Total {} files ready to be added\n'.format(counter))
        
        if not self.dry_run:
            logger.info('*****Total {} files failed to be moved\n'.format(len(self.unmoved)))
            if len(self.unmoved) > 0:
                logger.info('*****Following files failed to be moved')
                for item, reason in self.unmoved.items():
                    logger.info(u'Unmoved. {}. {}'.format(item, reason))

            logger.info('*****Total {} files wern\'t deleted\n'.format(len(self.not_deleted)))
            if len(self.not_deleted) > 0:
                logger.info('*****Following files failed to be deleted')
                for f in self.not_deleted:
                    logger.info(u'Not deleted {}. Reason: {}'.format(f[0], f[1]))

            logger.info(u'*****Total {} files were moved to {}\n'.format(len(self.moved), self.dst))
            logger.info('******Moved files dict')
            logger.info(json.dumps(self.moved, indent=4))

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
        for src, dst in self.db_files.items():
            self.all_handled_names += [basename(src), basename(dst)]

    def _delete_not_added(self):
        for f in self.not_passed_comparison:
            try:
                remove(f[0])
            except Exception as e:
                self.not_deleted.append((f[0], 'Error {} {}'.format(e.__class__.__name__,str(e))))

    def _update_db(self):
        self.db_files.update(self.moved)
        utils.save_db_files(self.db_files, self.dst, 'files.txt')

    def _prepare_new_files_for_copy(self):
        def get_new_filename():
            return regex_patterns.NEW_FILE_FORMAT.format(
                regex_patterns.DESTINATION_FORMAT_NO_SUFFIX_NO_EXTENSION.format(**match).replace(
                    'None', '00'), suffix, **match)

        def get_new_suffix(file_props_list):
            return regex_patterns.NEW_SUFFIX_FORMAT.format(
                max([int(props['suffix']) for props in file_props_list]) + 1)

        for key, matched in self.matched.items():
            for match in matched:
                logger.info('match {}'.format(str(match)))
                file_format = regex_patterns.DESTINATION_FORMAT_NO_SUFFIX.format(**match).replace('None', '00')
                if file_format not in list(self.destination_formats) + list(self.ready_to_add):
                    suffix = '000'
                elif file_format in self.ready_to_add:
                    suffix = get_new_suffix(self.ready_to_add[file_format])
                else:  # file_format in self.destination_files
                    suffix = get_new_suffix(self.destination_formats[file_format])
                    # sizes = [(join(prop['folder'], prop['file']), prop['size']) for prop
                    #          in self.ready_to_add[file_format] + self.destination_files[file_format]]
                    # if match['size'] in [size[1] for size in sizes]:
                    #     filename, size = next(size for size in sizes if size[1] == match['size'])
                    #     self.not_passed_comparing.append((join(match['folder'], match['file']),
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
        properties['extension'] = splitext(full_path)[1].lstrip('.').lower()
        return properties

    def _handle_destination_folder(self, folder, recursive=False):
        if not exists(folder):
            mkdir(folder)

        if recursive:
            dirs = [join(folder, d) for d in listdir(folder) if isdir(join(folder, d)) and
                    join(folder, d).lower() != self.src.lower()]
            for d in dirs:
                self._handle_destination_folder(d)
        files = [f for f in listdir(folder) if isfile(join(folder, f))]
        self.num_of_dst_files = len(files)
        counter_of_matched = 0
        for f in files:
            match = re.match(regex_patterns.DESTINATION_REGEX, f)
            if not match:
                self.destination_not_matched.append(f)
                continue
            else:
                counter_of_matched =+ 1

            properties = self._update_common_file_props(f, folder)
            properties.update(match.groupdict())
            # Create key with no suffix
            key = regex_patterns.DESTINATION_FORMAT_NO_SUFFIX.format(**properties)
            self.destination_formats[key].append(properties)
            self.sizes_files[properties['size']].append(properties['fullpath'])
        self.num_of_dst_matched_files = counter_of_matched

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

            if self.acceptable_regexs and not any(re.match(_regex, f) for _regex in self.acceptable_regexs):
                self.unmatched.append(join(folder, f))
                continue

            properties = self._update_common_file_props(f, folder)
            full_path = properties['fullpath']
            size = properties['size']
            # Photo file
            if imghdr.what(full_path):
                date_taken = None
                img = None
                try:
                    img = Image.open(full_path)
                except IOError:
                    pass
                if img:
                    if hasattr(img, '_getexif'):
                        _getexif = img._getexif()
                        if _getexif and DATE_TIME_ORIGINAL_KEY in _getexif:
                            date_taken = _getexif[DATE_TIME_ORIGINAL_KEY]
                    if not date_taken and hasattr(img, 'tag'):
                        logger.info('tag exists {}'.format(f))
                        date_taken = img.tag._tagdata[DATE_TIME_ORIGINAL_KEY]
                if date_taken:
                    match = re.match(regex_patterns.DATE_TAKEN_REGEX, date_taken)
                    if match:
                        properties.update(match.groupdict())
                    else:
                        logger.info(format('date_taken case {} full_path: {}'.format(str(date_taken), full_path)))
                        self.unsupported.append(full_path)
                else:
                    properties.update(self._retrieve_min_date(f, full_path))
            elif properties['extension'] in regex_patterns.VIDEO_FILE_EXTENSIONS:
                properties.update(self._retrieve_min_date(f, full_path))
            else:
                self.unsupported.append(full_path)
                continue

            passed_comparison = True
            errors = []
            # Name Filter
            if 'name' in self.comparers:
                if f in self.all_handled_names:
                    errors.append(u'NAME: {}'.format(f))
                    passed_comparison = False

            if 'size' in self.comparers:
                pass

            # binary Comparer
            if passed_comparison and 'binary' in self.comparers:
                if size in self.sizes_files:
                    for _f in self.sizes_files[size]:
                        if filecmp.cmp(_f, full_path, shallow=False):
                            errors.append(u'BINARY: {} same as {} {}'.format(full_path, _f, size))
                            passed_comparison = False
                            break

            if passed_comparison:
                self.matched[f].append(properties)
                self.sizes_files[size].append(full_path)
            else:
                self.not_passed_comparison.append((full_path, '; '.join(errors)))

    def _retrieve_min_date(self, f, full_path):
        min_date = min([getatime(full_path), getmtime(full_path), getctime(full_path)])
        dt = datetime.fromtimestamp(min_date)
        match = re.match(regex_patterns.ACCEPTABLE_REGEXS[0], f)
        if match:
            group_dict = match.groupdict()
            group_dict = dict([(key, int(value if value else '0')) for key, value in match.groupdict().items()
                              if key in ['year', 'month', 'day', 'hour', 'minute', 'second']])
            dt_from_name = datetime(group_dict['year'], group_dict['month'], group_dict['day'], group_dict['hour'],
                                    group_dict['minute'], group_dict['second'])
            dt = min(dt, dt_from_name)

        def format_func(num):
            return '{:0=2d}'.format(num)
        date_props = {
            'year': str(dt.year), 'month': format_func(dt.month),
            'day': format_func(dt.day), 'hour': format_func(dt.hour),
            'minute': format_func(dt.minute), 'second': format_func(dt.second)
            }
        self.min_date_taken.append((f, date_props))
        return date_props

    def _move_prepared_files(self):
        for fg, files in self.ready_to_add.items():
            for f in files:
                new_file_path = join(self.dst, f['new_file_name'])
                full_path = join(f['folder'], f['file'])
                try:
                    if exists(new_file_path):
                        self.unmoved[full_path] = u'Exists {}'.format(new_file_path)
                        continue
                    move(full_path, new_file_path)
                    self.moved[full_path] = new_file_path
                except Exception as e:
                    msg = 'Error {} {}'.format(e.__class__.__name__, str(e))
                    self.unmoved[full_path] = msg


if __name__ == "__main__":
    main()
