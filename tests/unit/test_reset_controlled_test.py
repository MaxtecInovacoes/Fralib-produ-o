from scripts.reset_controlled_test import CACHE_DIRS


def test_controlled_reset_clears_builder_runtime_artifacts():
    configured = {path.as_posix() for path in CACHE_DIRS}

    assert any(path.endswith("/logs/builder_manifests") for path in configured)
    assert any(path.endswith("/.tmp/builder-workspaces") for path in configured)
