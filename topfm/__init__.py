from pathlib import Path
from enum import Enum, auto
from nicfit import getLogger
from .__about__ import __version__ as version

log = getLogger(__package__)
CACHE_D = Path().home() / ".cache" / "TopFM"

__all__ = ["log", "getLogger", "version", "CACHE_D"]


class PromptMode(Enum):
    ON = auto()
    OFF = auto()
    FAIL = auto()
