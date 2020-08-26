import logging
import sys
import typing
import inspect

LOGGER_NAME = 'EmojiManiac'
_initialized_loggers = []
_is_debug = False


def _initialize_logger(logger: logging.Logger):
    level = logging.DEBUG if _is_debug else logging.INFO
    logger.setLevel(level)
    logger.handlers.clear()

    stderr_h = logging.StreamHandler(sys.stderr)
    stderr_h.setLevel(level)
    stderr_h.addFilter(above_warning_filter)
    stderr_h.setFormatter(base_formatter_instance)

    stdout_h = logging.StreamHandler(sys.stdout)
    stdout_h.setLevel(level)
    stdout_h.addFilter(below_warning_filter)
    stdout_h.setFormatter(base_formatter_instance)

    logger.handlers = [stdout_h, stderr_h]
    logger.propagate = False

    logger.debug(f'Logger {logger.name} is ready')
    return logger


def set_debug(debug: bool):
    global _is_debug
    _is_debug = debug


def get_logger(name: typing.Union[str, type] = None):
    logger = logging.getLogger(LOGGER_NAME)
    if name is not None:
        if inspect.isclass(name):
            name = name.__name__
        logger = logger.getChild(name)

    if logger not in _initialized_loggers:
        _initialize_logger(logger)

    return logger


class LoggingRecordLevelFilter(logging.Filter):
    filter_func: typing.Callable[[int], bool]

    def __init__(self, filter_func: typing.Callable[[int], bool]):
        super(LoggingRecordLevelFilter, self).__init__()
        self.filter_func = filter_func

    def filter(self, record: logging.LogRecord):
        return self.filter_func(record.levelno)


below_warning_filter = LoggingRecordLevelFilter(lambda level: level < logging.WARNING)
above_warning_filter = LoggingRecordLevelFilter(lambda level: level >= logging.WARNING)


class BaseFormatter(logging.Formatter):
    def __init__(self):
        super(BaseFormatter, self).__init__('%(asctime)s %(processName)-10s %(name)s %(levelname)-8s %(message)s')


base_formatter_instance = BaseFormatter()