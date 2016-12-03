NEW_FILE_FORMAT = '{}_{}.{extension}'
NEW_SUFFIX_FORMAT = '{:0=3d}'
DELIMITER = '[-|_| |\.|~]?'
EXTENSIONS = ['jpg', 'jpeg', 'png', 'mp4', 'mov', 'nef', 'gif']
REGEX_PARTS = {
        'extension': '\.(?P<extension>{})'.format('|'.join(EXTENSIONS + [ext.upper() for ext in EXTENSIONS])),
        'date': '((?P<year>[1-2][9|0]\d{2})' + DELIMITER + '(?P<month>[0-1]\d)' + DELIMITER + '(?P<day>[0-3]\d))',
        'time_no_milli': '(?P<hour>[0-2]\d)' + DELIMITER + '(?P<minute>\d{2})' + DELIMITER + '(?P<second>\d{2})',
        'time': '((?P<hour>[0-2]\d)' + DELIMITER + '(?P<minute>\d{2})' + DELIMITER + '(?P<second>\d{2})' +
                DELIMITER + '(?P<millisecond>\d{3})?)',
        'prefix': '(?P<prefix>IMG|VID|Screenshot|C360|MPC|DSC|RKP|MVI)',
        'suffix': '(?P<suffix>\d{1,4}|\(\d\)|\w{1,10}|Burst\d{2}|WA\d{4})',
        'delimiter': DELIMITER,
    }
DATE_TAKEN_REGEX = '(?P<year>20[0-1]\d):(?P<month>[0-1]\d):(?P<day>[0-3]\d)[ ]' \
                   '(?P<hour>[0-2]\d):(?P<minute>\d{2}):(?P<second>\d{2})'
ACCEPTABLE_REGEX_DICT = '^{prefix}?{delimiter}{date}?{delimiter}{time}?{delimiter}{suffix}?{extension}$'.format(
    **REGEX_PARTS)
# '^{prefix}{delimiter}{suffix}{extension}$'.format(**REGEX_PARTS),
DESTINATION_REGEX = '^{date}_{time_no_milli}_{suffix}{extension}'.format(**REGEX_PARTS)
DESTINATION_FORMAT_NO_SUFFIX_NO_EXTENSION = '{year}{month}{day}_{hour}{minute}{second}'
DESTINATION_FORMAT_NO_SUFFIX = DESTINATION_FORMAT_NO_SUFFIX_NO_EXTENSION + '.{extension}'
DESTINATION_FORMAT = DESTINATION_FORMAT_NO_SUFFIX_NO_EXTENSION + '{suffix}' + '{extension}'
