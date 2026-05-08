"""
Shared logging utility for ALDA placement optimizer scripts.

Usage in every script:
    from lib.log_setup import get_logger
    DEBUG = False          # flip to True to see debug output in stderr
    logger = get_logger(__name__, DEBUG)

Log files land in  <WorkDir>/logs/<script_name>.log
"""

import logging
import sys
from pathlib import Path

_LOG_DIR = Path(__file__).parent.parent.parent / "logs"
_FMT = logging.Formatter("%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
                          datefmt="%H:%M:%S")


def get_logger(name: str, debug: bool = False) -> logging.Logger:
    """
    Return a logger that always writes DEBUG+ to a file and optionally
    mirrors DEBUG+ to stderr when debug=True (WARNING+ otherwise).
    stdout is never touched — it belongs to the n8n JSON protocol.
    """
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    stem = name.replace(".", "_").replace("\\", "_").replace("/", "_")
    if stem == "__main__":
        stem = Path(sys.argv[0]).stem

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(_LOG_DIR / f"{stem}.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(_FMT)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.DEBUG if debug else logging.WARNING)
    sh.setFormatter(_FMT)
    logger.addHandler(sh)

    return logger
