from pathlib import Path

import pytest


@pytest.fixture
def conv1d_example_dir() -> Path:
    return Path("/usr/local/src/timeloop-python/arch_spec_examples/sparseloop/03.2.1-conv1d")