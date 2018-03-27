import datetime

import pylast
from pylast import LastFMNetwork

API_KEY = "1932ab33ea535ba390526dae88a782af"
API_SEC = "aa8ee0a4c0a2bcc5bd33e506e7a5fefe"


def _lastfmGet(func, period, num=4):
    if period[-1] == 's':
        # String forms are not plural, as are the constants are opts so chop
        period = period[:-1]

    tops = func(period, limit=num)[:num]
    tops = list(enumerate([a.item for a in tops], 1))
    if len(tops) != num:
        raise Exception("Requested number of items not returned.")
    else:
        return tops


def topArtists(user, period, num=5):
    return _lastfmGet(user.get_top_artists, period, num=num)


def topAlbums(user, period, num=5):
    return _lastfmGet(user.get_top_albums, period, num=num)


def User(username):
    return pylast.User(username, LastFMNetwork(api_key=API_KEY,
                                               api_secret=API_SEC))


PERIODS = (pylast.PERIOD_12MONTHS + 's', pylast.PERIOD_1MONTH,
           pylast.PERIOD_3MONTHS + 's', pylast.PERIOD_6MONTHS + 's',
           pylast.PERIOD_7DAYS + 's', pylast.PERIOD_OVERALL)


def periodString(p):
    for unit in ("days", "months", "month"):
        if p.endswith(unit):
            val = int(p[:p.find(unit)])
            td = datetime.timedelta(days=val) if unit == "days" \
                    else datetime.timedelta(weeks=val * 4)
            return f"in the last {val} {unit} "\
                   f"(since {datetime.date.today() - td:%b %d, %Y})"
    return p
