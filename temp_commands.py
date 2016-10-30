import os
import os.path
import json
import re
import regex_patterns
from collections import defaultdict
import shutil

DB_NAME = 'files.txt'


def sync_folder_and_db(folder):
    db_path = os.path.join(folder, 'files.txt')
    with open(db_path, 'r') as f:
        files_in_db = json.load(f)

    files_in_folder = [os.path.join(folder, _f) for _f in os.listdir(folder) if
                       os.path.isfile(os.path.join(folder, _f))
                       and re.match(regex_patterns.DESTINATION_REGEX, _f)]

    missing_in_folder = set(files_in_db.values()) - set(files_in_folder)
    missing_in_db = set(files_in_folder) - set(files_in_db.values())
    num_files_in_db_before = len(files_in_db)
    print 'missing_in_folder length {}'.format(len(missing_in_folder))
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
