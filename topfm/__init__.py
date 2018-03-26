from pathlib import Path
from nicfit import getLogger
from .__about__ import __version__ as version

log = getLogger(__package__)
CACHE_D = Path().home() / ".cache" / "TopFM"

__all__ = ["log", "getLogger", "version", "CACHE_D"]
