import os
from io import BytesIO
from pathlib import Path

import pylast
import requests
from PIL import Image

from . import CACHE_D, PromptMode

IMG_SZ = 300
UNKNOWN_ALBUM_IMG = None  # Set lazily
UNKNOWN_ALBUM_FILE = Path(__file__).parent / "unknown-cover.jpg"


def img1x2x2(tops, prompts=PromptMode.ON, disable_cache=False):
    collage = Image.new("RGB", (800, 400), "white")

    for i, obj in enumerate(tops[:5], 1):
        x, y, w, h = [(0, 0, 400, 400),
                      (400, 0, 200, 200), (600, 0, 200, 200),
                      (400, 200, 200, 200), (600, 200, 200, 200)][i - 1]

        img = _getImg(i, obj.item, prompts=prompts, disable_cache=disable_cache)
        _addCover(collage, img, x, y, w, h)

    return collage


def imgNxN(tops, rows=2, cols=2, sz=IMG_SZ, margin=0, prompts=PromptMode.ON, disable_cache=False):
    if len(tops) < rows * cols:
        raise ValueError("{:d} top image items required, {:d} provided"
                         .format(rows * cols, len(tops)))
    coords = []
    for r in range(rows):
        for c in range(cols):
            x_margin = margin if c == 0 else (margin * (c + 1))
            y_margin = margin if r == 0 else (margin * (r + 1))
            coords.append(((c * sz) + x_margin,
                           (r * sz) + y_margin))
    assert(len(coords) == rows * cols)

    collage = Image.new("RGB", (sz * cols + (margin * (rows + 1)),
                                sz * rows + (margin * (cols + 1))),
                        "red")

    for i, obj in enumerate(tops[:rows * cols], 1):
        x, y = coords[i - 1]

        img = _getImg(i, obj.item, prompts=prompts, disable_cache=disable_cache)
        _addCover(collage, img, x, y, sz, sz)

    return collage


def _addCover(image, cover_src, x, y, w, h):
    cimg = cover_src.resize((w, h))
    image.paste(cimg, (x, y))
    return cimg


def _imageFromCache(obj):
    try:
        cache_id = obj.get_mbid()
    except pylast.WSError:
        # Fall thru...
        cache_id = None

    if not cache_id:
        cache_id = obj.get_name()
        if hasattr(obj, "artist"):
            cache_id += f"_{obj.artist.name}"

    cache_id = cache_id.replace(os.path.sep, '-')

    if not CACHE_D.exists():
        CACHE_D.mkdir()

    cached_path = CACHE_D / Path(f"{cache_id}.png")
    if cached_path.exists():
        print(" [cached]: {}".format(cached_path))
        return Image.open(str(cached_path)), cached_path

    return None, cached_path


def _getImg(i, obj, prompts=PromptMode.ON, disable_cache=False):
    global UNKNOWN_ALBUM_IMG

    if isinstance(obj, pylast.Album):
        print(f"#{i} Album art: {obj.title} by {obj.artist.name}", end=" ")
    elif isinstance(obj, pylast.Artist):
        print("Artist img: {artist}".format(i=i, artist=obj.name), end=" ")
    else:
        raise ValueError("Invalid type: {}".format(obj.__class__.__name__))

    img, cache_path = None, None
    if not disable_cache:
        img, cache_path = _imageFromCache(obj)

    if not img:
        try:
            cover_url = obj.get_cover_image()
        except pylast.WSError:
            # Fall thru...
            cover_url = None

        if not cover_url:
            if prompts == PromptMode.FAIL:
                raise ValueError("No cover found, and prompting is fail mode")

            cover_url = input("\nNo cover URL, enter download URL: ").strip()\
                            if prompts == PromptMode.ON else UNKNOWN_ALBUM_FILE

        if cover_url and cover_url != UNKNOWN_ALBUM_FILE:
            print(" [downloading]: {}".format(cover_url))
            try:
                cover_req = requests.get(cover_url)
            except Exception as ex:
                raise ValueError(str(ex)) from None

            if cover_req.status_code == 200:
                img = Image.open(BytesIO(cover_req.content))
            else:
                raise ValueError(f"Download of '{cover_url}' failed: {cover_req}")

            # Update cache if using
            if not disable_cache:
                img.save(str(cache_path))
        else:
            img = UNKNOWN_ALBUM_IMG if UNKNOWN_ALBUM_IMG \
                        else Image.open(UNKNOWN_ALBUM_FILE)
            UNKNOWN_ALBUM_IMG = img
            print("  [default]")

    return img
