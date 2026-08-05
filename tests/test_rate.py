from clasificador_video.rate import rate_for_fps


def test_fps_2997_es_ntsc_timebase_30():
    timebase, ntsc = rate_for_fps(29.97)
    assert timebase == 30
    assert ntsc is True


def test_fps_30_exacto_no_es_ntsc():
    timebase, ntsc = rate_for_fps(30.0)
    assert timebase == 30
    assert ntsc is False


def test_fps_23976_es_ntsc_timebase_24():
    timebase, ntsc = rate_for_fps(23.976)
    assert timebase == 24
    assert ntsc is True


def test_fps_25_exacto_no_es_ntsc():
    timebase, ntsc = rate_for_fps(25.0)
    assert timebase == 25
    assert ntsc is False


def test_fps_5994_es_ntsc_timebase_60():
    timebase, ntsc = rate_for_fps(59.94)
    assert timebase == 60
    assert ntsc is True
