from __future__ import print_function
import os
import os.path
import json
import shutil

from logger import logger

DB_NAME = 'files.txt'


def load_db_files(folder, db_name=DB_NAME):
    db_path = os.path.join(folder, db_name)
    if not os.path.exists(db_path):
        return {}

    with open(db_path, 'r') as f:
        files_in_db = json.load(f)
    return files_in_db


def save_db_files(files, folder, db_name=DB_NAME):
    db_path = os.path.join(folder, db_name)
    with open(db_path, 'w') as f:
        json.dump(files, f, indent=4)


def sync_folder_and_db(folder, recursive=True, dry_run=True, logger_func=None):
    if not logger_func:
        logger_func = print
    files_in_db = load_db_files(folder)
    files_in_folder = []
    for path, subdirs, files in os.walk(folder):
        for name in files:
            files_in_folder.append(os.path.join(path, name))
    # files_in_folder = [os.path.join(folder, _f) for _f in os.listdir(folder) if
    #                    os.path.isfile(os.path.join(folder, _f))
    #                    and re.match(regex_patterns.DESTINATION_REGEX, _f)]

    def get_missing_in_folder():
        return set(files_in_db.values()) - set(files_in_folder)

    def get_missing_in_db():
        return set(files_in_folder) - set(files_in_db.values())
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

    files_in_db_value_key_changed = {}
    for f in files_in_db:
        files_in_db_value_key_changed[files_in_db[f]] = f

    for f in missing_in_folder:
        del files_in_db[files_in_db_value_key_changed[f]]

    output()
    missing_in_folder = get_missing_in_folder()
    missing_in_db = get_missing_in_db()
    output()
    save_db_files(files_in_db, folder)


def move_files(folder, new_folder, source_file_pattern, create_subfolder=True):
    db_files = load_db_files(folder)
    moved_files = {}
    dest_folder = os.path.join(folder, new_folder) if create_subfolder else new_folder
    if not os.path.exists(dest_folder):
        os.mkdir(dest_folder)

    for source_name, current_name in db_files.iteritems():
        if source_file_pattern in source_name:
            new_name = os.path.join(dest_folder, os.path.basename(current_name))
            shutil.move(current_name, new_name)
            moved_files[source_name] = new_name
            db_files[source_name] = new_name

    logger.info(json.dumps(moved_files, indent=4))
    logger.info('len {}'.format(len(moved_files)))
    save_db_files(db_files, folder)
