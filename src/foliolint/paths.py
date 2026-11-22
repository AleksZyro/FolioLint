"""Classify scan entries without following links or Windows reparse points."""

import stat
from pathlib import Path


def entry_mode(path: Path) -> int:
    try:
        info = path.lstat()
    except OSError:
        return 0
    if getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        return 0
    return info.st_mode


def regular_file(path: Path) -> bool:
    return stat.S_ISREG(entry_mode(path))


def directory(path: Path) -> bool:
    return stat.S_ISDIR(entry_mode(path))
