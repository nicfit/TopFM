# -*- coding: utf-8 -*-
import topfm
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
