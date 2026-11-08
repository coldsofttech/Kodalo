import kodalo.core


def test_version_is_defined() -> None:
    assert isinstance(kodalo.core.__version__, str)
