NEW_FILE_FORMAT = '{}_{}.{extension}'
NEW_SUFFIX_FORMAT = '{:0=3d}'
DELIMITER = '[-|_| |\.|~]?'
PHOTO_FILE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'nef', 'gif', 'dng']
VIDEO_FILE_EXTENSIONS = [
    '264', '3g2', '3gp', '3gp2', '3gpp', '3gpp2', '3mm', '3p2', '60d', '787', '89', 'aaf', 'aec', 'aep', 'aepx',
    'aet', 'aetx', 'ajp', 'ale', 'am', 'amc', 'amv', 'amx', 'anim', 'aqt', 'arcut', 'arf', 'asf', 'asx', 'avb',
    'avc', 'avd', 'avi', 'avp', 'avs', 'avs', 'avv', 'axm', 'bdm', 'bdmv', 'bdt2', 'bdt3', 'bik', 'bin', 'bix',
    'bmk', 'bnp', 'box', 'bs4', 'bsf', 'bvr', 'byu', 'camproj', 'camrec', 'camv', 'ced', 'cel', 'cine', 'cip',
    'clpi', 'cmmp', 'cmmtpl', 'cmproj', 'cmrec', 'cpi', 'cst', 'cvc', 'cx3', 'd2v', 'd3v', 'dat', 'dav', 'dce',
    'dck', 'dcr', 'dcr', 'ddat', 'dif', 'dir', 'divx', 'dlx', 'dmb', 'dmsd', 'dmsd3d', 'dmsm', 'dmsm3d', 'dmss',
    'dmx', 'dnc', 'dpa', 'dpg', 'dream', 'dsy', 'dv', 'dv-avi', 'dv4', 'dvdmedia', 'dvr', 'dvr-ms', 'dvx', 'dxr',
    'dzm', 'dzp', 'dzt', 'edl', 'evo', 'eye', 'ezt', 'f4p', 'f4v', 'fbr', 'fbr', 'fbz', 'fcp', 'fcproject',
    'ffd', 'flc', 'flh', 'fli', 'flv', 'flx', 'gfp', 'gl', 'gom', 'grasp', 'gts', 'gvi', 'gvp', 'h264', 'hdmov',
    'hkm', 'ifo', 'imovieproj', 'imovieproject', 'ircp', 'irf', 'ism', 'ismc', 'ismv', 'iva', 'ivf', 'ivr', 'ivs',
    'izz', 'izzy', 'jss', 'jts', 'jtv', 'k3g', 'kmv', 'ktn', 'lrec', 'lsf', 'lsx', 'm15', 'm1pg', 'm1v', 'm21',
    'm21', 'm2a', 'm2p', 'm2t', 'm2ts', 'm2v', 'm4e', 'm4u', 'm4v', 'm75', 'mani', 'meta', 'mgv', 'mj2', 'mjp',
    'mjpg', 'mk3d', 'mkv', 'mmv', 'mnv', 'mob', 'mod', 'modd', 'moff', 'moi', 'moov', 'mov', 'movie', 'mp21',
    'mp21', 'mp2v', 'mp4', 'mp4v', 'mpe', 'mpeg', 'mpeg1', 'mpeg4', 'mpf', 'mpg', 'mpg2', 'mpgindex', 'mpl',
    'mpl', 'mpls', 'mpsub', 'mpv', 'mpv2', 'mqv', 'msdvd', 'mse', 'msh', 'mswmm', 'mts', 'mtv', 'mvb', 'mvc',
    'mvd', 'mve', 'mvex', 'mvp', 'mvp', 'mvy', 'mxf', 'mxv', 'mys', 'ncor', 'nsv', 'nut', 'nuv', 'nvc', 'ogm',
    'ogv', 'ogx', 'osp', 'otrkey', 'pac', 'par', 'pds', 'pgi', 'photoshow', 'piv', 'pjs', 'playlist', 'plproj',
    'pmf', 'pmv', 'pns', 'ppj', 'prel', 'pro', 'prproj', 'prtl', 'psb', 'psh', 'pssd', 'pva', 'pvr', 'pxv',
    'qt', 'qtch', 'qtindex', 'qtl', 'qtm', 'qtz', 'r3d', 'rcd', 'rcproject', 'rdb', 'rec', 'rm', 'rmd', 'rmd',
    'rmp', 'rms', 'rmv', 'rmvb', 'roq', 'rp', 'rsx', 'rts', 'rts', 'rum', 'rv', 'rvid', 'rvl', 'sbk', 'sbt',
    'scc', 'scm', 'scm', 'scn', 'screenflow', 'sec', 'sedprj', 'seq', 'sfd', 'sfvidcap', 'siv', 'smi', 'smi',
    'smil', 'smk', 'sml', 'smv', 'spl', 'sqz', 'srt', 'ssf', 'ssm', 'stl', 'str', 'stx', 'svi', 'swf', 'swi',
    'swt', 'tda3mt', 'tdx', 'thp', 'tivo', 'tix', 'tod', 'tp', 'tp0', 'tpd', 'tpr', 'trp', 'ts', 'tsp', 'ttxt',
    'tvs', 'usf', 'usm', 'vc1', 'vcpf', 'vcr', 'vcv', 'vdo', 'vdr', 'vdx', 'veg', 'vem', 'vep', 'vf', 'vft',
    'vfw', 'vfz', 'vgz', 'vid', 'video', 'viewlet', 'viv', 'vivo', 'vlab', 'vob', 'vp3', 'vp6', 'vp7', 'vpj',
    'vro', 'vs4', 'vse', 'vsp', 'w32', 'wcp', 'webm', 'wlmp', 'wm', 'wmd', 'wmmp', 'wmv', 'wmx', 'wot', 'wp3',
    'wpl', 'wtv', 'wve', 'wvx', 'xej', 'xel', 'xesc', 'xfl', 'xlmv', 'xmv', 'xvid', 'y4m', 'yog', 'yuv', 'zeg',
    'zm1', 'zm2', 'zm3', 'zmv']
EXTENSIONS = PHOTO_FILE_EXTENSIONS + VIDEO_FILE_EXTENSIONS
REGEX_PARTS = {
        'extension': '\.(?P<extension>{})'.format('|'.join(EXTENSIONS + [ext.upper() for ext in EXTENSIONS])),
        'date': '((?P<year>[1-2][9|0]\d{2})' + DELIMITER + '(?P<month>[0-1]\d)' + DELIMITER + '(?P<day>[0-3]\d))',
        'time_no_milli': '(?P<hour>[0-2]\d)' + DELIMITER + '(?P<minute>\d{2})' + DELIMITER + '(?P<second>\d{2})',
        'time': '((?P<hour>[0-2]\d)' + DELIMITER + '(?P<minute>\d{2})' + DELIMITER + '(?P<second>\d{2})' +
                DELIMITER + '(?P<millisecond>\d{3})?)',
        'prefix': '(?P<prefix>IMG|VID|Screenshot|[a-zA-Z|\d]{4})',
        'suffix': '(?P<suffix>(\d|\w){1,4}|\(\d\)|Burst\d{2}|WA\d{4})',
        'delimiter': DELIMITER,
        'delimiter_once': DELIMITER.replace('?', ''),
    }
DATE_TAKEN_REGEX = '(?P<year>20[0-1]\d):(?P<month>[0-1]\d):(?P<day>[0-3]\d)[ ]' \
                   '(?P<hour>[0-2]\d):(?P<minute>\d{2}):(?P<second>\d{2})'
ACCEPTABLE_REGEXS = [
    '^{prefix}?{delimiter}{date}{delimiter}{time}?{delimiter}{suffix}?{extension}$'.format(**REGEX_PARTS),
    '^{prefix}{delimiter_once}{suffix}{extension}$'.format(**REGEX_PARTS)
]
DESTINATION_REGEX = '^{date}_{time_no_milli}_{suffix}{extension}'.format(**REGEX_PARTS)
DESTINATION_FORMAT_NO_SUFFIX_NO_EXTENSION = '{year}{month}{day}_{hour}{minute}{second}'
DESTINATION_FORMAT_NO_SUFFIX = DESTINATION_FORMAT_NO_SUFFIX_NO_EXTENSION + '.{extension}'
DESTINATION_FORMAT = DESTINATION_FORMAT_NO_SUFFIX_NO_EXTENSION + '{suffix}' + '{extension}'
