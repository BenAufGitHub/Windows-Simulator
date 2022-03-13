import os, sys, logging
from datetime import date


class ErrorLog(object):
    def write(self, data):
        if len(data.strip()) >= 3:
            logging.error(" "+data.strip())


def config_logging():
    sys.stderr = ErrorLog()
    filename = _get_logging_path()
    logging.basicConfig(filename=filename, encoding='utf-8', level=logging.DEBUG)


def _get_date():
    return date.today()


def _get_logging_path() -> str:
    path = f".\\logs\\{_get_date()}"
    if os.path.isdir(path):
        length = len(os.listdir(path))
        return _create_session_name(path, length)
    os.mkdir(path)
    return _create_session_name(path, 0)


# creates session name as name for log file
def _create_session_name(path: str, index: int) -> str:
    return f"{path}\\{index+1}.txt"