import os
import sys
import json
from pathlib import Path
from textwrap import dedent
from datetime import datetime

import facebook
from nicfit.aio import Application
from nicfit.logger import getLogger

from .login import facebookLogin
from . import lastfm, collage, CACHE_D, version

log = getLogger("topfm.__main__")
TOPFM_URL = "https://github.com/nicfit/TopFM"
FB_AUTH_JSON_FILE = CACHE_D / "facebook.json"


class TopFmApp(Application):
    def _addArguments(self, parser):
        parser.add_argument("--display-name")
        parser.add_argument("--post-facebook", action="store_true")

        subs = parser.add_subparsers(title="Subcommands", dest="subcommand")
        artists_parser = subs.add_parser("artists", help="Query top artists.")
        albums_parser = subs.add_parser("albums", help="Query top albums.")
        for args, kwargs in [
            (("-u", "--user"), {"default": "nicfit", "dest": "lastfm_user",
                                "metavar": "LASTFM_USER"}),
            (("-N", "--top-n"), {"default": 10, "type": int, "dest": "top_n",
                                 "metavar": "N"}),
            (("-P", "--period"), {"default": "overall",
                                  "choices": lastfm.PERIODS, "dest": "period"}),
            (("--collage",), {"default": None, "const": "1x2x2", "nargs": "?",
                              "choices": ["2x2", "3x3", "4x4", "5x5", "5x2",
                                          "5x3", "1x2x2", "10x10"],
                              "dest": "collage"}),
            (("--collage-name",), {"default": None, "type": str,
                                   "dest": "collage_name", "metavar": "NAME"}),
            (("--image-size",), {"default": collage.IMG_SZ, "type": int,
                                 "dest": "image_size", "metavar": "N"}),
            (("--image-margin",), {"default": 0, "type": int,
                                   "dest": "image_margin", "metavar": "N"}),
        ]:
            for p in (artists_parser, albums_parser):
                p.add_argument(*args, **kwargs)

    async def _main(self, args):
        log.debug("{} started: {}".format(sys.argv[0], args))
        log.verbose("main args: {}".format(args))

        if args.subcommand not in ("artists", "albums"):
            print(f"Unknown sub command: {args.subcommand}")
            self.arg_parser.print_usage()
            return 1

        if not CACHE_D.exists():
            CACHE_D.mkdir(parents=True)
        log.debug(f"Using cache directory {CACHE_D}")

        lastfm_user = lastfm.User(args.lastfm_user)
        display_name = args.display_name or lastfm_user.name

        tops = None
        if args.subcommand == "albums":
            tops = lastfm.topAlbums(lastfm_user, args.period, num=args.top_n)
        elif args.subcommand == "artists":
            tops = lastfm.topArtists(lastfm_user, args.period, num=args.top_n)

        if args.period == "overall":
            reg = datetime.fromtimestamp(lastfm_user.get_unixtime_registered())
            period = f"overall (Since {reg:%b %d, %Y})"
        else:
            period = lastfm.periodString(args.period)

        if not tops:
            print(f"\nNo Top {args.subcommand} found for {period}:")
            return 2

        text = dedent(f"""
        {display_name}'s Top {args.top_n} {args.subcommand} {period}:\n
        """)
        iwitdh = len(str(len(tops))) + 2
        for i, obj in tops:
            itext = f"#{i:d}:"
            text += f" {itext:>{iwitdh}} {obj}\n"
        text += "\n"
        print(text)

        collage_path = None
        if args.collage:
            if args.collage == "1x2x2":
                img = collage.img1x2x2(tops)
            else:
                assert(args.collage.count("x") == 1)
                rows, cols = (int(n) for n in args.collage.split("x"))
                try:
                    img = collage.imgNxN(tops, rows=rows, cols=cols,
                                         sz=args.image_size,
                                         margin=args.image_margin)
                except ValueError as err:
                    print(str(err))
                    return 4
            assert(img)

            if args.collage_name is None:
                # FIXME: add period, type, size, etc. to the default
                args.collage_name = "collage"

            collage_path = "{}.png".format(args.collage_name)
            print("Writing {}...".format(collage_path))
            img.save(collage_path)

            # TODO: add option to skip this
            os.system("eog {}".format(collage_path))

        if args.post_facebook:
            await _postFacebook(collage_path, text)


async def _postFacebook(collage_path, text):
    if not FB_AUTH_JSON_FILE.exists():
        fb_creds = await facebookLogin()
        FB_AUTH_JSON_FILE.write_text(json.dumps(fb_creds))
    else:
        fb_creds = json.loads(FB_AUTH_JSON_FILE.read_text())

    print("Posting to facebook...")
    fb = facebook.GraphAPI(access_token=fb_creds["access_token"], timeout=90,
                           version="2.7")
    message = f"{text}\n\n" +\
              f"\tCreated with {TOPFM_URL}\n"

    if collage_path:
        put = fb.put_photo(image=Path(collage_path).read_bytes(),
                           message=message)
    else:
        put = fb.put_object(parent_object="me", connection_name="feed",
                            message=message)
    log.debug(f"Facebook resp: {put}")


app = TopFmApp(version=version)
if __name__ == "__main__":
    app.run()
