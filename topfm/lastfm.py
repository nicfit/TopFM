import re
import datetime

import pylast
from pylast import LastFMNetwork

API_KEY = "1932ab33ea535ba390526dae88a782af"
API_SEC = "aa8ee0a4c0a2bcc5bd33e506e7a5fefe"


def _getItemObj(item):
    """Extract the lastfm object from a list item."""
    if isinstance(item, (pylast.PlayedTrack, pylast.LovedTrack)):
        obj = item
    else:
        obj = item.item
    return obj


def filterExcludes(items, excludes: dict) -> list:
    exc_regexes = {}
    for key, expressions in (excludes or {}).items():
        exc_regexes[key] = list([re.compile(e) for e in excludes[key]]) if excludes[key] else []
    excludes = exc_regexes

    def f(item):
        obj = _getItemObj(item)

        def _artist(o):
            if isinstance(o, pylast.Artist):
                return o.name
            elif isinstance(o, (pylast.Album, pylast.Track)):
                return o.artist.name
            elif isinstance(o, (pylast.PlayedTrack, pylast.LovedTrack)):
                return o.track.artist.name
            else:
                raise NotImplementedError(f"FIXME: accessor for {o.__class__.__name__}")

        def _album(o):
            if isinstance(o, pylast.Album):
                return o.title
            elif isinstance(o, (pylast.Track, pylast.LovedTrack)):
                a = o.get_album()
                return a.title if a else None
            elif isinstance(o, pylast.PlayedTrack):
                return o.album
            else:
                raise NotImplementedError(f"FIXME: accessor for {o.__class__.__name__}")

        def _track(o):
            if isinstance(o, pylast.Track):
                return o.title
            elif isinstance(o, (pylast.PlayedTrack, pylast.LovedTrack)):
                return o.track.title
            else:
                raise NotImplementedError(f"FIXME: accessor for {o.__class__.__name__}")

        if isinstance(obj, pylast.Artist):
            for regex in excludes["artist"]:
                if regex.search(_artist(obj)):
                    return False

        elif isinstance(obj, pylast.Album):
            for regex in excludes["album"]:
                if regex.search(_album(obj)):
                    return False

            for regex in excludes["artist"]:
                if regex.search(_artist(obj)):
                    return False

        elif isinstance(obj, pylast.Track):
            for regex in excludes["track"]:
                if regex.search(_track(obj)):
                    return False

            for regex in excludes["artist"]:
                if regex.search(_artist(obj)):
                    return False

            album = _album(obj) if len(excludes["album"]) else None
            if album:
                for regex in excludes["album"]:
                    if regex.search(album):
                        return False

        elif isinstance(obj, pylast.PlayedTrack):
            for regex in excludes["track"]:
                if regex.search(_track(obj)):
                    return False

            for regex in excludes["artist"]:
                if regex.search(_artist(obj)):
                    return False

            for regex in excludes["album"]:
                if obj.album:
                    if regex.search(_album(obj)):
                        return False

        return True

    return list(filter(f, items) if excludes else items)


def uniqueArtist(items) -> list:
    results = []
    seen_artists = set()

    for item in items:
        obj = _getItemObj(item)
        if obj.artist.name not in seen_artists:
            results.append(item)
            seen_artists.add(obj.artist.name)

    return results


def _lastfmGet(func, period, num=4, excludes=None, unique_artist=False):
    if period[-1] == 's':
        # Pylast periods are not plural, as are the constants are opts so chop
        period = period[:-1]

    tops = []
    attempts, max_attempts = 0, 5

    while len(tops) < num and attempts < max_attempts:
        attempts += 1
        tops = filterExcludes(func(period, limit=num + (25 * attempts)), excludes)
        if unique_artist:
            tops = uniqueArtist(tops)

    tops = tops[:num]
    if len(tops) != num:
        raise Exception("Requested number of items not returned.")
    else:
        return tops


def topArtists(user, period, num=5, excludes=None):
    return _lastfmGet(user.get_top_artists, period, num=num, excludes=excludes)


def topAlbums(user, period, num=5, excludes: list=None, unique_artist=False):
    return _lastfmGet(user.get_top_albums, period, num=num, excludes=excludes,
                      unique_artist=unique_artist)


def topTracks(user, period, num=5, excludes=None, unique_artist=False):
    return _lastfmGet(user.get_top_tracks, period, num=num, excludes=excludes,
                      unique_artist=unique_artist)


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

