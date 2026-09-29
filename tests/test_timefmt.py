from transcriptor.timefmt import format_timestamp


def test_timestamp_formatting():
    assert format_timestamp(0) == "00:00:00"
    assert format_timestamp(3723.9) == "01:02:03"
    assert format_timestamp(1.234, milliseconds=True) == "00:00:01.234"

