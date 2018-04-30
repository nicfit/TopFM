import os
import sys
import json
import argparse
from pathlib import Path
from textwrap import dedent
from datetime import datetime

import facebook
from nicfit.aio import Application
from nicfit.logger import getLogger

from .login import facebookLogin
from . import lastfm, collage, CACHE_D, version, PromptMode

log = getLogger("topfm.__main__")
TOPFM_URL = "https://github.com/nicfit/TopFM"
FB_AUTH_JSON_FILE = CACHE_D / "facebook.json"


class TopFmApp(Application):
    def _addArguments(self, parser: argparse.ArgumentParser):
        parser.add_argument("--display-name")
        parser.add_argument("--post-facebook", action="store_true")
        parser.add_argument("-u", "--user", default="nicfit",
                            dest="lastfm_user", metavar="LASTFM_USER")

        prompt_group = parser.add_mutually_exclusive_group()
        prompt_group.add_argument("--no-prompt", action="store_true")
        prompt_group.add_argument("--fail-if-prompt", action="store_true")

        subs = parser.add_subparsers(title="Subcommands", dest="subcommand")
        artists_parser = subs.add_parser("artists", help="Query top artists.")
        albums_parser = subs.add_parser("albums", help="Query top albums.")
        tracks_parser = subs.add_parser("tracks", help="Query top tracks.")

        recent_parser = subs.add_parser("recent", help="Query recent tracks.")
        recent_parser.add_argument("-L", "--loved")

        for args, kwargs, parsers in [
            (("-N", "--top-n"),
             {"default": 10, "type": int, "dest": "top_n", "metavar": "N"},
             (artists_parser, albums_parser, tracks_parser, recent_parser),
            ),
            (("-P", "--period"), {"default": "overall",
                                  "choices": lastfm.PERIODS, "dest": "period"},
             (artists_parser, albums_parser, tracks_parser, recent_parser),
            ),
            (("--collage",), {"default": None, "const": "1x2x2", "nargs": "?",
                              "choices": ["2x2", "3x3", "4x4", "5x5", "5x2",
                                          "5x3", "1x2x2", "10x10"],
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

        ]:
            for p in parsers:
                p.add_argument(*args, **kwargs)

    def _getTops(self, args, lastfm_user):
        display_name = args.display_name or lastfm_user.name

        handler = getattr(lastfm, f"top{args.subcommand.title()}")
        tops = handler(lastfm_user, args.period, num=args.top_n)

        if args.period == "overall":
            reg = datetime.fromtimestamp(lastfm_user.get_unixtime_registered())
            period = f"overall (Since {reg:%b %d, %Y})"
        else:
            period = lastfm.periodString(args.period)

        text = dedent(f"""
            {display_name}'s Top {args.top_n} {args.subcommand} {period}:\n
            """)
        iwitdh = len(str(len(tops))) + 2
        for i, obj in tops:
            itext = f"#{i:d}:"
            obj_text = f"{obj}"
            text += f" {itext:>{iwitdh}} {obj_text}\n"
        text += "\n"

        return tops, text

    async def _handleAlbumsCmd(self, args, lastfm_user):
        tops, text = self._getTops(args, lastfm_user)
        print(text)

        collage_path = None
        if args.collage:
            try:
                if args.collage == "1x2x2":
                    img = collage.img1x2x2(tops, prompts=args.prompt_mode)
                else:
                    assert(args.collage.count("x") == 1)
                    rows, cols = (int(n) for n in args.collage.split("x"))
                    img = collage.imgNxN(tops, rows=rows, cols=cols,
                                         sz=args.image_size,
                                         margin=args.image_margin,
                                         prompts=args.prompt_mode)
            except ValueError as err:
                print(str(err))
                return 4

            assert(img)
            if args.collage_name is None:
                args.collage_name = \
                    f"{args.subcommand}_collage-{args.collage}-{args.period}"

            collage_path = "{}.png".format(args.collage_name)
            print("\nWriting {}...".format(collage_path))
            img.save(collage_path)

            if not args.no_image_view:
                os.system("eog {}".format(collage_path))

        comments = []
        for _, a in tops:
            comments.append(a.get_url())

        if args.post_facebook:
            await _postFacebook(text, collage_path, comments)

    async def _handleArtistsCmd(self, args, lastfm_user):
        return await self._handleAlbumsCmd(args, lastfm_user)

    async def _handleTracksCmd(self, args, lastfm_user):
        tops, text = self._getTops(args, lastfm_user)
        print(text)

        comments = []
        for _, t in tops:
            comments.append(t.get_url())

        if args.post_facebook:
            await _postFacebook(text, None, comments)

    async def _handleRecentCmd(self, args, lastfm_user):
        tracks = lastfm_user.get_recent_tracks(limit=300)
        for t in tracks:
            t.track.username = "nicfit"
            print("<3:", t.track.get_userloved())
        print(len(tracks))
        print(tracks[0])
        print(tracks[-1])

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

        lastfm_user = lastfm.User(args.lastfm_user,
                                  os.getenv("LASTFM_PASSWORD"))

        handler = getattr(self, f"_handle{args.subcommand.title()}Cmd", None)
        try:
            await handler(args, lastfm_user)
        except facebook.GraphAPIError as err:
            print(f"Facebook error: {err}")


async def _postFacebook(message, photo_path, comments):
    if not FB_AUTH_JSON_FILE.exists():
        fb_creds = await facebookLogin()
        FB_AUTH_JSON_FILE.write_text(json.dumps(fb_creds))
    else:
        fb_creds = json.loads(FB_AUTH_JSON_FILE.read_text())

    print("Posting to facebook...")
    fb = facebook.GraphAPI(access_token=fb_creds["access_token"], timeout=90,
                           version="2.7")
    message = f"{message}\n\n" +\
              f"\tCreated with {TOPFM_URL}\n"

    if photo_path:
        put = fb.put_photo(image=Path(photo_path).read_bytes(),
                           message=message)
    else:
        put = fb.put_object(parent_object="me", connection_name="feed",
                            message=message)
    log.debug(f"Facebook resp: {put}")

    if comments:
        # TODO: error, need "page access token"
        #for cmt in (comments or []):
        #    fb.put_comment(object_id=put["id"], message=cmt)
        ...


app = TopFmApp(version=version)
if __name__ == "__main__":
    app.run()
