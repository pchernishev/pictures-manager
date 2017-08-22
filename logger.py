import logging


def init_logger():
    _format = '%(asctime)s - %(levelname)s - %(filename)s:%(funcName)s:%(lineno)d - %(message)s'
    date_format = '%d/%m/%Y %H:%M:%S'
    logging.basicConfig(filename='logger.log', level=logging.DEBUG, format=_format,
                        datefmt=date_format)
    logger = logging.getLogger('logger')
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter(_format, date_format)
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)
    return logger


logger = init_logger()
