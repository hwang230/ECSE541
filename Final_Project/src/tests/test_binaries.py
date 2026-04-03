import shutil


def test_accelergy_exists() -> None:
    assert shutil.which("accelergy") is not None


def test_timeloop_model_exists() -> None:
    assert shutil.which("timeloop-model") is not None


def test_timeloop_mapper_exists() -> None:
    assert shutil.which("timeloop-mapper") is not None