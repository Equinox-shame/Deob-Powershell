# coding=utf-8
import sys
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    NONE = 4


__log_level = LogLevel.DEBUG
__log_fd = sys.stdout


def set_log_level(level):
    global __log_level
    __log_level = level


def set_log_file(filename):
    global __log_fd
    try:
        __log_fd = open(filename, "wb")
    except IOError:
        __log_fd = sys.stdout
        log_warn("Unable to create %s, using standard ouput")


def shrink(s, max_length=150):
    return s if len(s) <= max_length else s[:max_length] + "..."


def log_debug(s):
    global __log_level
    if __log_level.value < LogLevel.INFO.value:
        __log_fd.write(
            '\u001b[36m[{:<19}]'.format(datetime.now().strftime("%Y-%d-%m %H:%M:%S")) + ' {:<8}'.format("[DEBUG]") + shrink(
                s) + "\u001b[0m\n")
        sys.stdout.flush()


def log_info(s):
    global __log_level
    if __log_level.value <= LogLevel.WARNING.value:
        __log_fd.write(
            '[{:<19}]'.format(datetime.now().strftime("%Y-%d-%m %H:%M:%S")) + ' {:<8}'.format("[INFO]") + shrink(
                s) + "\n")
        sys.stdout.flush()


def log_warn(s):
    global __log_level
    if __log_level.value <= LogLevel.ERROR.value:
        __log_fd.write(
            '\u001b[33m[{:<19}]'.format(datetime.now().strftime("%Y-%d-%m %H:%M:%S")) + ' {:<8}'.format("[WARN]") + shrink(
                s) + "\u001b[0m\n")
        sys.stdout.flush()


def log_err(s):
    global __log_level
    if __log_level.value <= LogLevel.NONE.value:
        __log_fd.write(
            '\u001b[31m[{:<19}]'.format(datetime.now().strftime("%Y-%d-%m %H:%M:%S")) + ' {:<8}'.format("[ERROR]") + shrink(
                s) + "\u001b[0m\n")
        sys.stdout.flush()

if __name__ == "__main__":
    # 测试
    log_debug("This is a debug message")
    log_info("This is an info message")
    log_warn("This is a warning message")
    log_err("This is an error message")
