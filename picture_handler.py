import logging
import re
import filecmp
from os import listdir, remove
from os.path import isfile, join, isdir, getsize, exists, getmtime, getctime, getatime, basename
from optparse import OptionParser
from collections import defaultdict
from shutil import move
import json
from PIL import Image
from datetime import datetime

import regex_patterns

logger = None
DATE_TIME_ORIGINAL_KEY = 36867


def main():
    init_logger()
    parser = create_parser()
    options, args = parser.parse_args()
    logger.info('Handling started')
    handler = PicturesHandler(options.src, options.dst, options.mode,
                              options.filter.replace(' ', '').split(' ') if options.filter else [],
                              options.filter.replace(' ', '').strip('"').split('" "') if options.ignore else [],
                              options.dry_run)
    handler.handle()
    handler.output()
    logger.info('Handling finished')


def create_parser():
    parser = OptionParser()
    parser.add_option("--src", '-s', dest="src", type="string", help="Folder to parse")
    parser.add_option("--dst", '-d', dest="dst", type="string", help="Folder copy pictures to")
    parser.add_option('--mode', '-m', dest='mode', type="string", help="Whether to handle phone or camera pictures")
    parser.add_option('--filter', '-f', dest='filter', type="string",
                      help="Methods for pictures fitering before copy separated by whitespace")
    parser.add_option('--ignore', '-i', dest='ignore', type="string",
                      help="Regexs surrounded by \" for pictures names to ignore separated by whitespace")
    parser.add_option('--dry-run', '--dr', dest='dry_run', action='store_true')
    parser.set_defaults(dry_run=False)
    return parser


def init_logger():
    logging.basicConfig(filename='logger.log', level=logging.DEBUG, format='%(asctime)s %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S')
    global logger
    logger = logging.getLogger('logger')
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)


class Mode:
    camera = 'camera'
    phone = 'phone'
    available_modes = [camera, phone]


class PicturesHandler:
    def __init__(self, src, dst, mode=Mode.phone, filters=None, ignore_regexs=None, dry_run=False):
        if not src or not dst or not mode:
            raise ValueError('Manadatory parameter is missing')

        self.src = unicode(src)
        self.dst = unicode(dst)
        self.mode = mode
        self.filters = get_filter()
        self.dry_run = dry_run

        if self.mode not in Mode.available_modes:
            raise ValueError('Invalid mode passed {}. Expected one of the following {}'.format(
                self.moved, Mode.available_modes))

        self.sizes_files = defaultdict(list)
        self.matched = defaultdict(list)
        self.unmatched = []
        self.matched_not_added = []
        self.destination_formats = defaultdict(list)
        self.destination_not_matched = []
        self.ready_to_add = defaultdict(list)
        self.added_files = []
        self.moved = {}
        self.unmoved = {}
        self.not_deleted = []

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
        counter = 0
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
        logger.info('\n\n******Following files matched but was not added')
        for item in self.matched_not_added:
            logger.info(u'Not Added. {}'.format(item[1]))
        logger.info('*****Total {} files matched but not added '.format(len(self.matched_not_added)))

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
        self._handle_destination_folder()
        self._handle_source_folder(self.src)
        self._prepare_new_files_for_copy()
        if not self.dry_run:
            self._move_prepared_files()
            self._delete_not_added()

    def _delete_not_added(self):
        for f in self.matched_not_added:
            try:
                remove(f[0])
            except Exception, e:
                self.not_deleted.append((f[0], 'Error {} {}'.format(e.__class__.__name__, e.message)))

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
                    #     self.matched_not_added.append((join(match['folder'], match['file']),
                    #                                    'File {} has the same name and size {}'.format(
                    # filename, size)))
                    #     continue
                match['suffix'] = suffix
                match['new_file_name'] = get_new_filename()
                self.ready_to_add[file_format].append(match)

    def _handle_destination_folder(self):
        files = [f for f in listdir(self.dst) if isfile(join(self.dst, f))]
        for _f in files:
            match = re.match(regex_patterns.DESTINATION_REGEX, _f)
            if not match:
                self.destination_not_matched.append(_f)
                continue
            properties = match.groupdict()
            properties['folder'] = self.dst
            full_path = join(self.dst, _f)
            size = getsize(full_path)
            properties['size'] = size
            properties['file'] = _f

            # Create key with no suffix
            key = regex_patterns.DESTINATION_FORMAT_NO_SUFFIX.format(**properties)
            self.destination_formats[key].append(properties)
            self.sizes_files[size].append(full_path)

    def _handle_source_folder(self, folder, recursive=True):
        if recursive:
            dirs = [join(folder, d) for d in listdir(folder) if isdir(join(folder, d)) and
                    join(folder, d).lower() != self.dst.lower]
            for d in dirs:
                self._handle_source_folder(d)
        files = [_f for _f in listdir(folder) if isfile(join(folder, _f))]
        for f in files:
            match = re.match(regex_patterns.ACCEPTABLE_REGEX_DICT[self.mode], f)
            if match:
                full_path = (join(folder, f))
                properties = match.groupdict()
                properties['folder'] = folder
                size = getsize(full_path)
                properties['size'] = size
                properties['file'] = f
                if self.mode == Mode.camera:
                    try:
                        img = Image.open(full_path)
                        if hasattr(img, '_getexif'):
                            date_taken = img._getexif()[DATE_TIME_ORIGINAL_KEY]
                        elif hasattr(img, 'tag'):
                            date_taken = img.tag._tagdata[DATE_TIME_ORIGINAL_KEY]
                        date_taken_dict = re.match(regex_patterns.DATE_TAKEN_REGEX, date_taken).groupdict()
                        properties.update(date_taken_dict)
                    except (KeyError, IOError) as e:
                        if isinstance(e, IOError) and 'cannot identify image file' not in e.message \
                                or isinstance(e, KeyError) and e.message != 36867:
                            raise
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
                    except Exception as e:
                        logger.info('Error {}'.format(_f))

                if size not in self.sizes_files:
                    self.matched[f].append(properties)
                    self.sizes_files[size].append(full_path)
                else:
                    for _f in self.sizes_files[size]:
                        if filecmp.cmp(_f, full_path, shallow=False):
                            self.matched_not_added.append((full_path, u'{} same as {} and {} size {}'.format(
                                full_path, _f, len(self.sizes_files[size][1:]), size)))
                            break
                    else:
                        self.matched[f].append(properties)
                        self.sizes_files[size].append(full_path)
            else:
                self.unmatched.append(join(folder, f))

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
