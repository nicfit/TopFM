import os
from io import BytesIO
from pathlib import Path
import pylast
import requests
from PIL import Image
from . import CACHE_D

IMG_SZ = 300


def img1x2x2(tops):
    collage = Image.new("RGB", (800, 400), "white")

    for i, obj in tops[:5]:
        x, y, w, h = [(0, 0, 400, 400),
                      (400, 0, 200, 200), (600, 0, 200, 200),
                      (400, 200, 200, 200), (600, 200, 200, 200)][i - 1]

        img = _getImg(i, obj)
        _addCover(collage, img, x, y, w, h)

    return collage


def imgNxN(tops, rows=2, cols=2, sz=IMG_SZ, margin=0):
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

    for i, obj in tops[:rows * cols]:
        x, y = coords[i - 1]

        img = _getImg(i, obj)
        _addCover(collage, img, x, y, sz, sz)

    return collage


def _addCover(image, cover_src, x, y, w, h):
    cimg = cover_src
    cimg = cimg.resize((w, h))
    image.paste(cimg, (x, y))
    return cimg


def _getImg(i, obj):
    if isinstance(obj, pylast.Album):
        print("#{i} {title} by {artist}\n"
              "\tdownloading {cover_url}"
              .format(i=i, title=obj.title, cover_url=obj.get_cover_image(),
                      artist=obj.artist.name))
    elif isinstance(obj, pylast.Artist):
        print("#{i} {artist}\n"
              "\tdownloading {cover_url}"
              .format(i=i, cover_url=obj.get_cover_image(),
                      artist=obj.name))
    else:
        raise ValueError("Invalid type: {}".format(obj.__class__.__name__))

    cache_id = obj.get_mbid()
    if not cache_id:
        cache_id = obj.get_name()
        if hasattr(obj, "artist"):
            cache_id += f"_{obj.artist.name}"
    cache_id = cache_id.replace(os.sep, '-')

    if not CACHE_D.exists():
        CACHE_D.mkdir()

    cached_img = CACHE_D / Path(f"{cache_id}.png")
    if cached_img.exists():
        print("Using cached image: {}".format(cached_img))
        img = Image.open(str(cached_img))
    else:
        cover_url = obj.get_cover_image()
        if not cover_url:
            print("No cover URL, enter valid URL: ", end='')
            cover_url = input()

        cover_req = requests.get(cover_url)
        if cover_req.status_code == 200:
            img = Image.open(BytesIO(cover_req.content))
        else:
            raise ValueError(f"Download of '{cover_url}' failed: {cover_req}")
        img.save(str(cached_img))

    return img
