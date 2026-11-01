import kodalo_package


def test_version_is_defined() -> None:
    assert isinstance(kodalo_package.__version__, str)
