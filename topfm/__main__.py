import os
import sys
import argparse
from textwrap import dedent
from datetime import datetime

import pylast
from nicfit.aio import Application
from nicfit.logger import getLogger

from . import lastfm, collage, CACHE_D, version, PromptMode

log = getLogger("topfm.__main__")


class TopFmApp(Application):
    def _addArguments(self, parser: argparse.ArgumentParser):
        parser.add_argument("--display-name")
        parser.add_argument("-u", "--user", default="nicfit",
                            dest="lastfm_user", metavar="LASTFM_USER")

        prompt_group = parser.add_mutually_exclusive_group()
        prompt_group.add_argument("--no-prompt", action="store_true")
        prompt_group.add_argument("--fail-if-prompt", action="store_true")

        subs = parser.add_subparsers(title="Subcommands", dest="subcommand")
        artists_parser = subs.add_parser("artists", help="Query top artists.")
        albums_parser = subs.add_parser("albums", help="Query top albums.")
        tracks_parser = subs.add_parser("tracks", help="Query top tracks.")
        loved_parser = subs.add_parser("loved", help="Query loved tracks.")
        recent_parser = subs.add_parser("recent", help="Query recent tracks.")

        for args, kwargs, parsers in [
            (("-N", "--top-n"),
             {"default": 10, "type": int, "dest": "top_n", "metavar": "N"},
             (artists_parser, albums_parser, tracks_parser),
            ),
            (("-n", "--limit"),
             {"default": 50, "type": int, "dest": "limit", "metavar": "N"},
             (recent_parser, loved_parser),
             ),
            (("-P", "--period"), {"default": "overall",
                                  "choices": lastfm.PERIODS,
                                  "dest": "period"},
             (artists_parser, albums_parser, tracks_parser),
            ),
            (("--collage",), {"default": None, "const": "1x2x2", "nargs": "?",
                              "choices": ["2x2", "2x4", "3x3", "4x4", "4x2",
                                          "5x5", "5x2", "5x3", "5x100",
                                          "1x2x2", "10x10", "20x20", "8x8"],
                              "dest": "collage"},
             (artists_parser, albums_parser),
            ),
            (("--collage-name",), {"default": None, "type": str,
                                   "dest": "collage_name", "metavar": "NAME"},
             (artists_parser, albums_parser),
            ),
            (("--image-size",), {"default": collage.IMG_SZ, "type": int,
                                 "dest": "image_size", "metavar": "N"},
             (artists_parser, albums_parser),
            ),
            (("--image-margin",), {"default": 0, "type": int,
                                   "dest": "image_margin", "metavar": "N"},
             (artists_parser, albums_parser),
            ),
            (("--no-image-view",), {"action": "store_true"},
             (artists_parser, albums_parser),
            ),
            (("--exclude-artist",), {"action": "append",
                                     "dest": "artist_excludes"},
             (artists_parser, albums_parser, tracks_parser, recent_parser, loved_parser),
            ),
            (("--exclude-album",), {"action": "append",
                                    "dest": "album_excludes"},
             (artists_parser, albums_parser, tracks_parser, recent_parser, loved_parser),
            ),
            (("--exclude-track",), {"action": "append",
                                    "dest": "track_excludes"},
             (artists_parser, albums_parser, tracks_parser, recent_parser, loved_parser),
            ),
            (("--unique-artist",), {"action": "store_true",
                                    "help": "Only include top item for each artist."},
             (albums_parser, tracks_parser),
            ),
            (("--no-cache",), {"action": "store_true",
                               "help": "Refrain from using/updating image cache."},
             (albums_parser, artists_parser),
            ),
            (("-L", "--show-listens"), {"action": "store_true",
                                         "help": "Show # of listens with each result."},
             (artists_parser, albums_parser, tracks_parser),
            ),

        ]:
            for p in parsers:
                p.add_argument(*args, **kwargs)

    @staticmethod
    async def _handleAlbumsCmd(args, lastfm_user):
        tops, formatted = _getTops(args, lastfm_user)
        print(formatted)

        if args.collage:
            try:
                if args.collage == "1x2x2":
                    img = collage.img1x2x2(tops, prompts=args.prompt_mode,
                                           disable_cache=args.no_cache)
                else:
                    assert args.collage.count("x") == 1
                    rows, cols = (int(n) for n in args.collage.split("x"))
                    img = collage.imgNxN(tops, rows=rows, cols=cols,
                                         sz=args.image_size,
                                         margin=args.image_margin,
                                         prompts=args.prompt_mode,
                                         disable_cache=args.no_cache)
            except ValueError as err:
                print(str(err))
                return 4

            assert img
            if args.collage_name is None:
                args.collage_name = \
                    f"[{lastfm_user}]{args.subcommand}_collage-{args.collage}-{args.period}"

            collage_path = "{}.png".format(args.collage_name)
            print("\nWriting {}...".format(collage_path))
            img.save(collage_path)

            if not args.no_image_view:
                os.system("eog {}".format(collage_path))

    @staticmethod
    async def _handleArtistsCmd(args, lastfm_user):
        return await TopFmApp._handleAlbumsCmd(args, lastfm_user)

    @staticmethod
    async def _handleTracksCmd(args, lastfm_user):
        tops, formatted = _getTops(args, lastfm_user)
        print(formatted)

    @staticmethod
    async def _handleRecentCmd(args, lastfm_user):
        # TODO: show album name
        # TODO: query, show loved, not working
        # yes, asking for limit=N returns len() N-1, so the +1
        tracks = lastfm_user.get_recent_tracks(limit=args.limit + 1)
        tracks = lastfm.filterExcludes(tracks, excludes={"artist": args.artist_excludes,
                                                         "album": args.album_excludes,
                                                         "track": args.track_excludes,
                                                        })

        text = _formatResults(tracks, args, lastfm_user, list_label="")
        print(text)

    @staticmethod
    async def _handleLovedCmd(args, lastfm_user):
        # TODO: show album name
        loved = lastfm.filterExcludes(
            lastfm_user.get_loved_tracks(limit=args.limit or None),
            excludes={"artist": args.artist_excludes,
                      "album": args.album_excludes,
                      "track": args.track_excludes,
                     })

        text = _formatResults(loved, args, lastfm_user, list_label="Last")
        print(text)
        # TODO: json output: {"track": recent.track.title, "artist": recent.track.artist.name}
        '''
        import json
        for item in loved:
            print(json.dumps({"track": item.track.title, "artist": item.track.artist.name}))
        '''

    async def _main(self, args):
        log.debug("{} started: {}".format(sys.argv[0], args))
        log.verbose("main args: {}".format(args))
        if args.no_prompt:
            args.prompt_mode = PromptMode.OFF
            args.no_image_view = True
        elif args.fail_if_prompt:
            args.prompt_mode = PromptMode.FAIL
        else:
            args.prompt_mode = PromptMode.ON

        if not CACHE_D.exists():
            CACHE_D.mkdir(parents=True)
        log.debug(f"Using cache directory {CACHE_D}")

        lastfm_user = lastfm.User(args.lastfm_user, os.getenv("LASTFM_PASSWORD"))

        handler = getattr(self, f"_handle{args.subcommand.title()}Cmd", None)
        try:
            await handler(args, lastfm_user)
        except pylast.WSError as auth_err:
            print(f"{auth_err}", file=sys.stderr)
            return 2


def _getTops(args, lastfm_user):
    handler = getattr(lastfm, f"top{args.subcommand.title()}")
    handler_kwargs = dict(num=args.top_n,
                          excludes={"artist": args.artist_excludes,
                                    "album": args.album_excludes,
                                    "track": args.track_excludes,
                                   })
    if "unique_artist" in args and args.unique_artist:
        handler_kwargs["unique_artist"] = args.unique_artist

    tops = handler(lastfm_user, args.period, **handler_kwargs)

    text = _formatResults(tops, args, lastfm_user)
    return tops, text


def _formatResults(top_items, args, lastfm_user, list_label="Top"):
    display_name = args.display_name or lastfm_user.name

    if "period" not in args or args.period == "overall":
        reg = datetime.fromtimestamp(lastfm_user.get_unixtime_registered())
        period = f"overall (Since {reg:%b %d, %Y})"
    else:
        period = lastfm.periodString(args.period)

    # top_n = limit
    if "top_n" not in args and "limit" in args:
        args.top_n = args.limit

    list_label = f" {list_label}" if list_label else ""
    text = dedent(f"""
        {display_name}'s{list_label} {args.top_n} {args.subcommand} {period}:\n
        """)
    iwitdh = len(str(len(top_items))) + 2
    for i, obj in enumerate(top_items, 1):
        itext = f"#{i:d}:"
        weight = None

        if isinstance(obj, pylast.TopItem):
            obj_text = str(obj.item)
            weight = obj.weight
        elif isinstance(obj, (pylast.LovedTrack, pylast.PlayedTrack)):
            obj_text = f"{obj.track.artist.name} - {obj.track.title}"
        else:
            raise NotImplemented(f"Unknown format type: {obj.__class__.__name__}")

        weight_text = ""
        if weight and args.show_listens:
            weight_text = f" ({weight} listens)"

        text += f" {itext:>{iwitdh}} {obj_text}{weight_text}\n"

    text += "\n"
    return text


app = TopFmApp(version=version)
if __name__ == "__main__":
    app.run()
