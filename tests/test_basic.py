"""Basic smoke tests for wingman."""

from wingman.config.paths import WingmanPaths


def test_wingman_importable():
    """Verify the wingman package can be imported."""
    import wingman

    assert wingman is not None


def test_paths_created():
    """Verify WingmanPaths initializes without error."""
    paths = WingmanPaths()
    assert paths.config_dir is not None
    assert paths.data_dir is not None
    assert paths.log_dir is not None
