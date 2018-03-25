import os
import sys
import json
import asyncio
import logging
import configparser
from argparse import ArgumentParser

from nicfit.aio import Application
from nicfit.logger import getLogger
from .login import facebookLogin
from . import lastfm, collage, CACHE_D

log = getLogger("topfm.__main__")


class TopFmApp(Application):
    def _addArguments(self, parser):
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

        subs.add_parser("login", help="Social networking authorization.")

    async def _main(self, args):
        log.debug("{} started: {}".format(sys.argv[0], args))
        log.verbose("main args: {}".format(args))

        if not CACHE_D.exists():
            CACHE_D.mkdir(parents=True)
        log.debug(f"Using cache directory {CACHE_D}")

        if args.subcommand in ("artists", "albums"):
            lastfm_user = lastfm.user(args)

            if args.subcommand == "albums":
                tops = lastfm.topAlbums(lastfm_user, args.period,
                                        num=args.top_n)
            elif args.subcommand == "artists":
                tops = lastfm.topArtists(lastfm_user, args.period,
                                         num=args.top_n)
            else:
                print(f"Unknown sub command: {args.subcommand}")
                self.arg_parser.print_usage()
                return 1

            period = lastfm.periodString(args.period)
            print(f"\nTop {args.top_n} {args.subcommand} {period}:")
            text = ""
            for i, obj in tops:
                text += "#{}: {}\n".format(i, obj)
            print(text)

            if args.collage:
                if args.collage == "1x2x2":
                    img = collage.img1x2x2(tops)
                else:
                    assert(args.collage.count("x") == 1)
                    rows , cols = (int(n) for n in args.collage.split("x"))
                    img = collage.imgNxN(tops, rows=rows, cols=cols,
                                         sz=args.image_size,
                                         margin=args.image_margin)
                assert(img)

                filename = "{}.png".format(args.collage_name)
                print("Writing {}...".format(filename))
                img.save(filename)
                os.system("eog {}".format(filename))
        else:
            assert args.subcommand == "login"
            access_tok = await facebookLogin()
            (CACHE_D / "facebook.json").write_text(json.dumps(access_tok))
            print("Login success")

        return 0


app = TopFmApp()
if __name__ == "__main__":
    app.run()
