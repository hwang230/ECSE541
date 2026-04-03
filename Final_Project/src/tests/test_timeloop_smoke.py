from pathlib import Path

from tltools.runner import timeloop_model


def test_timeloop_model_starts() -> None:
    fixture_dir = Path("src/tests/fixtures/minimal")

    result = timeloop_model(
        "arch_example.yaml",
        "problem_example.yaml",
        "mapping_example.yaml",
        cwd=fixture_dir,
    )
    print("STDOUT:\n", result.stdout)
    print("STDERR:\n", result.stderr)
    assert result.returncode == 0
    combined = result.stdout + "\n" + result.stderr
    assert "Cycles =" in combined
    assert "Utilization =" in combined