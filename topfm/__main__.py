import os
import sys
import json
from  pathlib import Path
from textwrap import dedent

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
            (("--collage-name",), {"default": "collage", "type": str,
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

        if not CACHE_D.exists():
            CACHE_D.mkdir(parents=True)
        log.debug(f"Using cache directory {CACHE_D}")

        lastfm_user = lastfm.User(args.lastfm_user)
        display_name = args.display_name or lastfm_user.name

        if args.subcommand in ("artists", "albums"):

            tops = None
            if args.subcommand == "albums":
                tops = lastfm.topAlbums(lastfm_user, args.period,
                                        num=args.top_n)
            elif args.subcommand == "artists":
                tops = lastfm.topArtists(lastfm_user, args.period,
                                         num=args.top_n)

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

            img_filename = None
            if args.collage:
                if args.collage == "1x2x2":
                    img = collage.img1x2x2(tops)
                else:
                    assert(args.collage.count("x") == 1)
                    rows , cols = (int(n) for n in args.collage.split("x"))
                    try:
                        img = collage.imgNxN(tops, rows=rows, cols=cols,
                                             sz=args.image_size,
                                             margin=args.image_margin)
                    except ValueError as err:
                        print(str(err))
                        return 4
                assert(img)

                img_filename = "{}.png".format(args.collage_name)
                print("Writing {}...".format(img_filename))
                img.save(img_filename)
                os.system("eog {}".format(img_filename))

            if args.post_facebook:
                fb_creds = None
                if fb_creds is None and not FB_AUTH_JSON_FILE.exists():
                    fb_creds = await facebookLogin()
                    FB_AUTH_JSON_FILE.write_text(json.dumps(fb_creds))
                    print("Login success")
                else:
                    fb_creds = json.loads(FB_AUTH_JSON_FILE.read_text())

                print("Posting to facebook...")
                fb = facebook.GraphAPI(access_token=fb_creds["access_token"],
                                       timeout=90, version="2.6")
                message = f"{text}\n\n" +\
                     f"\tCreated with {TOPFM_URL}\n"

                if args.collage:
                    put = fb.put_photo(image=Path(img_filename).read_bytes(),
                                       message=message)
                else:
                    put = fb.put_object(parent_object="me",
                                        connection_name="feed",
                                        message=message)
                log.debug(f"Facebook resp: {put}")
                print("Done")
        else:
            print(f"Unknown sub command: {args.subcommand}")
            self.arg_parser.print_usage()
            return 1

        return 0


app = TopFmApp(version=version)
if __name__ == "__main__":
    app.run()
