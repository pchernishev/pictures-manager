import os
import os.path
import json
import re
import regex_patterns
import shutil

from logger import logger

DB_NAME = 'files.txt'


def load_db_files(folder, db_name=DB_NAME):
    db_path = os.path.join(folder, db_name)
    files_in_db = None
    with open(db_path, 'r') as f:
        files_in_db = json.load(f)
    return files_in_db


def save_db_files(files, folder, db_name=DB_NAME):
    db_path = os.path.join(folder, db_name)
    with open(db_path, 'w') as f:
        json.dump(files, f, indent=4)


def sync_folder_and_db(folder):
    files_in_db = load_db_files(folder)
    files_in_folder = [os.path.join(folder, _f) for _f in os.listdir(folder) if
                       os.path.isfile(os.path.join(folder, _f))
                       and re.match(regex_patterns.DESTINATION_REGEX, _f)]

    # missing_in_folder = set(files_in_db.values()) - set(files_in_folder)
    missing_in_db = set(files_in_folder) - set(files_in_db.values())
    num_files_in_db_before = len(files_in_db)
    print 'missing_in_db length {}'.format(len(missing_in_db))

    new_files = {}
    source_folder = 'C:\Users\Pavel Chernishev\Desktop\Pics'
    for f in missing_in_db:
        basename = os.path.basename(f)
        name, ext = os.path.splitext(basename)
        splits = name.split('_')
        key = os.path.join(source_folder, splits[0], '{}_{}{}'.format(splits[0], splits[1], ext))
        if key in new_files:
            print('Key exists {}'.format(key))
            print('Existing file {}'.format(new_files[key]))
            print('New file {}'.format(f))
        new_files[key] = f
        files_in_db[key] = f
    msg = ['num new_files: {}'.format(len(new_files)),
           'num files_in_db before: {}'.format(num_files_in_db_before),
           'num files_in_db after: {}'.format(len(files_in_db)),
           'difference: {}'.format(len(files_in_db) - num_files_in_db_before)]
    print('\n'.join(msg))
    missing_basenames = [os.path.basename(f) for f in missing_in_db]
    added_basenames = [os.path.basename(f) for f in new_files.values()]
    diff = set(missing_basenames) - set(added_basenames)
    print('diff: {}'.format(diff))

    db_path = os.path.join(folder, 'files_1.txt')
    with open(db_path, 'w') as f:
        files_in_db = json.dump(files_in_db, f, indent=4)


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
