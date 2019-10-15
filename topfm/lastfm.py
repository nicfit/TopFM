import re
import datetime

import pylast
from pylast import LastFMNetwork

API_KEY = "1932ab33ea535ba390526dae88a782af"
API_SEC = "aa8ee0a4c0a2bcc5bd33e506e7a5fefe"


def _filterExcludes(items, excludes: dict) -> list:
    exc_regexes = {}
    for key, expressions in (excludes or {}).items():
        exc_regexes[key] = list([re.compile(e) for e in excludes[key]]) if excludes[key] else []
    excludes = exc_regexes

    def f(item):
        obj = item.item

        if isinstance(obj, pylast.Artist):
            for regex in excludes["artist"]:
                if regex.search(obj.name):
                    return False

        elif isinstance(obj, pylast.Album):
            for regex in excludes["album"]:
                if regex.search(obj.title):
                    return False

            for regex in excludes["artist"]:
                if regex.search(obj.artist.name):
                    return False

        elif isinstance(obj, pylast.Track):
            for regex in excludes["track"]:
                if regex.search(obj.title):
                    return False

            for regex in excludes["artist"]:
                if regex.search(obj.artist.name):
                    return False

            album = None
            for regex in excludes["album"]:
                album = obj.get_album() if album is None else album
                if album:
                    if regex.search(album.title):
                        return False

        return True

    return list(filter(f, items) if excludes else items)


def _lastfmGet(func, period, num=4, excludes=None):
    if period[-1] == 's':
        # Pylast periods are not plural, as are the constants are opts so chop
        period = period[:-1]

    tops = []
    attempts, max_attempts = 0, 5
    while len(tops) < num and attempts < max_attempts:
        attempts += 1
        tops = _filterExcludes(func(period, limit=num + (25 * attempts)), excludes)

    tops = tops[:num]
    if len(tops) != num:
        raise Exception("Requested number of items not returned.")
    else:
        tops = list(enumerate([a.item for a in tops], 1))
        return tops


def topArtists(user, period, num=5, excludes=None):
    return _lastfmGet(user.get_top_artists, period, num=num, excludes=excludes)


def topAlbums(user, period, num=5, excludes: list=None):
    return _lastfmGet(user.get_top_albums, period, num=num, excludes=excludes)


def topTracks(user, period, num=5, excludes=None):
    return _lastfmGet(user.get_top_tracks, period, num=num, excludes=excludes)


def User(username, password=None):
    password = pylast.md5(password) if password else None
    return pylast.User(username,
                       LastFMNetwork(api_key=API_KEY, api_secret=API_SEC,
                                     password_hash=password))


PERIODS = (pylast.PERIOD_12MONTHS + 's', pylast.PERIOD_1MONTH,
           pylast.PERIOD_3MONTHS + 's', pylast.PERIOD_6MONTHS + 's',
           pylast.PERIOD_7DAYS + 's', pylast.PERIOD_OVERALL)


def periodToTimedelta(p):
    for unit in ("days", "months", "month"):
        if p.endswith(unit):
            val = int(p[:p.find(unit)])
            if unit == "days":
                return datetime.timedelta(days=val)
            else:
                return datetime.timedelta(weeks=val * 4)

    raise ValueError(f"Unsupported period value: `{p}`")


def periodString(p):
    for unit in ("days", "months", "month"):
        if p.endswith(unit):
            val = int(p[:p.find(unit)])
            td = periodToTimedelta(p)
            return f"in the last {val} {unit} "\
                   f"(since {datetime.date.today() - td:%b %d, %Y})"

    return p

