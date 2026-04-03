from pathlib import Path

from tltools.dse import _area_proxy_um2, _expand_points, _parse_stats_summary, _render_template


def test_render_template_replaces_all_keys() -> None:
    rendered = _render_template("A={{FOO}},B={{BAR}}", {"FOO": 1, "BAR": 2})
    assert rendered == "A=1,B=2"


def test_expand_points_cartesian_product() -> None:
    points = _expand_points(
        {
            "pe_x": [8, 16],
            "global_buffer_depth": [2048],
            "backing_storage_bw": [16],
            "local_buffer_bw": [8, 16],
        },
        {
            "pe_y": 8,
            "local_buffer_depth": 64,
        },
    )
    assert len(points) == 4
    assert points[0].pe_count == 64


def test_parse_stats_summary_from_fixture() -> None:
    stats = _parse_stats_summary(Path("src/tests/fixtures/minimal/timeloop-model.stats.txt"))
    assert stats["summary_cycles"] == 16
    assert stats["summary_utilization_percent"] == 100.0


def test_area_proxy_changes_with_design_size() -> None:
    points = _expand_points(
        {
            "pe_dim": [8, 16],
            "global_buffer_depth": [2048],
            "backing_storage_bw": [16],
        },
        {
            "local_buffer_depth": 64,
            "local_buffer_bw": 8,
        },
    )
    constants = {"datawidth": 8}
    small = _area_proxy_um2(points[0], constants)
    large = _area_proxy_um2(points[1], constants)
    assert large > small
