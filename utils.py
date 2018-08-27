from __future__ import print_function
import os
from os.path import exists, join, basename, dirname
import json
import shutil
import re
from collections import defaultdict

from logger import logger

DB_NAME = 'files.txt'


def load_db_files(folder, db_name=DB_NAME):
    db_path = join(folder, db_name)
    if not exists(db_path):
        return {}

    with open(db_path, 'r') as f:
        files_in_db = json.load(f)
    return files_in_db


def save_db_files(files, folder, db_name=DB_NAME):
    db_path = join(folder, db_name)
    with open(db_path, 'w') as f:
        json.dump(files, f, indent=4)


def sync_folder_and_db(folder, recursive=True, dry_run=True, logger_func=None):
    if not logger_func:
        logger_func = print
    files_in_db = load_db_files(folder)
    files_in_folder = defaultdict(dict)
    files_in_db_modified = defaultdict(dict)
    print('%s' % files_in_db)
    for path, subdirs, files in os.walk(folder):
        for name in files:
            files_in_folder['name'] = {'path': folder}
    for key, value in files_in_db:
        files_in_db_modified[basename(value)] = {'old_path': dirname(key), 'old_name': basename(key), 'new_path': dirname(value)}

    # files_in_folder = [join(folder, _f) for _f in os.listdir(folder) if
    #                    isfile(join(folder, _f))
    #                    and re.match(regex_patterns.DESTINATION_REGEX, _f)]

    def get_missing_in_folder():
        return set(files_in_db_modified.keys()) - set(files_in_folder.keys())

    def get_missing_in_db():
        return set(files_in_folder.keys()) - set(files_in_db_modified.keys())

    missing_in_folder = get_missing_in_folder()
    missing_in_db = get_missing_in_db()

    def output():
        logger_func('Number of missing_in_folder {}'.format(len(missing_in_folder)))
        logger_func('Number of missing_in_db {}'.format(len(missing_in_db)))
        if dry_run:
            logger_func('List of missing_in_db\n{}\n'.format('\n'.join(missing_in_db)))
            logger_func('List of missing_in_folder\n{}\n'.format('\n'.join(missing_in_folder)))

    if dry_run:
        output()
        return

    # files_in_db_value_key_changed = {}
    # for key, value in files_in_db_modified.iteritems():
    #     files_in_db_value_key_changed[value] = key

    # for f in missing_in_folder:
    #     del files_in_db[files_in_db_value_key_changed[f]]
    # # for f in missing_in_db:
    # #     files_in_db[]

    # output()
    # missing_in_folder = get_missing_in_folder()
    # missing_in_db = get_missing_in_db()
    # output()
    # save_db_files(files_in_db, folder)


def move_files(folder, new_folder, regex_pattern='.*\.\w{2,4}', create_subfolder=True, dry_run=True):
    db_files = load_db_files(folder)
    new_folder_db_files = {}
    old_folder_db_files = dict(db_files)
    dest_folder = join(folder, new_folder) if create_subfolder else new_folder
    if not exists(dest_folder):
        os.mkdir(dest_folder)

    print(regex_pattern)
    regex = re.compile(regex_pattern)
    for source_name, current_name in db_files.iteritems():
        old_basename = basename(source_name)
        new_basename = basename(current_name)
        if regex.match(old_basename):
            new_name = join(dest_folder, basename(new_basename))
            new_folder_db_files[source_name] = new_name
            del old_folder_db_files[source_name]
            if not dry_run:
                shutil.move(current_name, new_name)

    logger.info(json.dumps(new_folder_db_files, indent=4))
    logger.info('handled files names {}'.format(len(new_folder_db_files)))
    if not dry_run:
        save_db_files(old_folder_db_files, folder)
        save_db_files(new_folder_db_files, dest_folder)
