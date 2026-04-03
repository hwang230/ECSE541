from pathlib import Path

from tltools.runner import timeloop_model_metrics


def test_minimal_metrics_are_parsed() -> None:
    fixture_dir = Path("src/tests/fixtures/minimal")

    result = timeloop_model_metrics(
        "arch_example.yaml",
        "problem_example.yaml",
        "mapping_example.yaml",
        cwd=fixture_dir,
        clock_seconds=1e-9,
    )

    print(result["stdout"])
    print(result["stderr"])
    print(result["metrics"])

    assert result["returncode"] == 0
    assert result["metrics"]["parsed"] is True
    assert result["metrics"]["cycles"] == 16
    assert result["metrics"]["latency_ns"] == 16.0
    assert result["metrics"]["utilization"] == 1.0

    assert result["outputs"]["ert_summary"] is not None
    assert result["outputs"]["art_summary"] is not None