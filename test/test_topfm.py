import shlex
import pytest
import topfm
import topfm.__main__
"""
test_topfm
----------------------------------

Tests for `topfm` module.
"""


def test_metadata():
    assert topfm.version
    assert topfm.__about__.__license__
    assert topfm.__about__.__project_name__
    assert topfm.__about__.__author__
    assert topfm.__about__.__author_email__
    assert topfm.__about__.__version__
    assert topfm.__about__.__version_info__
    assert topfm.__about__.__release__
    assert topfm.__about__.__version_txt__


functional_test_cases = (
    "tracks -N 12",
    "albums -P 7days --exclude-album Midvinterblot",
    "artists -P1month --exclude-artist Unleashed",
    "albums -N 10 -P 3months",
    "tracks -N 50 -P 6months --unique-artist --exclude-artist Cryptopsy",
    "artists --period 12months",
    "tracks -N 10 -P overall --exclude-track='Scars Of The Crucifix' --exclude-artist Deicide",
    "loved --exclude-artist Bathory --exclude-album Bathory",
    " --no-prompt albums -N 5 --exclude-album 'K&G mixtape' --exclude-artist 'Unleashed' --collage 2x2 --no-image-view --no-cache",
    " --no-prompt albums -N 5 --exclude-album 'K&G mixtape' --exclude-artist 'Unleashed' --collage 2x2 --no-image-view",
    " --no-prompt artists -N 10 --collage 1x2x2 --no-image-view --no-cache",
    " --no-prompt artists -N 10 --collage 1x2x2 --no-image-view",
)


@pytest.mark.asyncio
@pytest.mark.parametrize("args", [shlex.split(cmd) for cmd in functional_test_cases],
                         ids=list(functional_test_cases))
async def test_functional(args):
    try:
        code = await topfm.__main__.app.main(args_list=args)
        assert code == 0
    except SystemExit as sys_exit:
        assert sys_exit.code == 0
