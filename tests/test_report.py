"""Tests for the CSV report, console summary and diagnostic figures."""

from __future__ import annotations

import csv

import numpy as np
from helpers import fake_result
from synthetic import make_scan

from teramount_analysis import Config, analyse_scan
from teramount_analysis.figures import save_scan_figure
from teramount_analysis.report import CSV_COLUMNS, summary_table, write_csv
from teramount_analysis.results import METRIC_COLUMNS, FaultReport, ScanResult
from teramount_analysis.xpander import XpanderResult


def _rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.reader(fh))


def test_csv_header_and_values(tmp_path):
    good = fake_result(faults=FaultReport(("plane1_noisy",), (), ("xpander_rx_um_outlier",)))
    partial = fake_result(file="y.npy", status="partial", error="xpander not found: no dome",
                          xpander=XpanderResult.not_found("no dome"), faults=FaultReport())
    out = tmp_path / "sub" / "r.csv"
    write_csv([good, partial], out, Config())
    header, row, row2 = _rows(out)
    assert tuple(header) == CSV_COLUMNS
    rec = dict(zip(header, row, strict=True))
    assert rec["file"] == "x.npy" and rec["status"] == "ok"
    assert rec["pivot_height_diff_um"] == "18.18"
    assert rec["cross1_x_um"] == f"{500.0 * 0.252:.6g}"
    assert rec["geometric_flags"] == "plane1_noisy" and rec["faulty"] == "yes"
    assert rec["statistical_flags"] == "xpander_rx_um_outlier"
    rec2 = dict(zip(header, row2, strict=True))
    assert rec2["xpander_rx_um"] == "" and rec2["faulty"] == "no"
    assert rec2["error"] == "xpander not found: no dome"


def test_warnings_column_is_separate_from_faults(tmp_path):
    r = fake_result(warnings=("rotation_not_measured",), faults=FaultReport())
    write_csv([r], tmp_path / "r.csv", Config())
    header, row = _rows(tmp_path / "r.csv")
    rec = dict(zip(header, row, strict=True))
    assert header[:4] == ["file", "status", "error", "warnings"]
    assert rec["warnings"] == "rotation_not_measured" and rec["faulty"] == "no"
    assert "rotation_not_measured" in summary_table([r])


def test_failed_row_written(tmp_path):
    bad = ScanResult(file="bad.npy", status="failed", error="cannot read", faults=FaultReport())
    write_csv([bad], tmp_path / "r.csv", Config())
    header, row = _rows(tmp_path / "r.csv")
    rec = dict(zip(header, row, strict=True))
    assert rec["status"] == "failed" and rec["error"] == "cannot read" and rec["faulty"] == ""
    assert all(rec[c] == "" for c in METRIC_COLUMNS)


def test_summary_table_lists_every_file():
    table = summary_table([fake_result(), ScanResult(file="bad.npy", status="failed")])
    assert "x.npy" in table and "bad.npy" in table and "failed" in table and "18.18" in table


def test_figure_written(tmp_path):
    z, _ = make_scan(rotation_deg=0.5)
    r = analyse_scan(z, Config(), "syn")
    save_scan_figure(r, tmp_path / "syn.png", Config())
    assert (tmp_path / "syn.png").stat().st_size > 20_000


def test_failed_scan_figure_written(tmp_path):
    r = analyse_scan(np.zeros((300, 300)), Config(), "flat")
    save_scan_figure(r, tmp_path / "flat.png", Config())
    assert (tmp_path / "flat.png").stat().st_size > 5_000


def test_figure_marks_the_dropped_dome_pixels(tmp_path):
    from synthetic import add_particle

    z, t = make_scan()
    ax, ay = t.apex_xy_px
    r = analyse_scan(add_particle(z, (ax + 80, ay + 60), 3.0, 3.0), Config(), "dust")
    assert r.xpander.outlier_map is not None and r.xpander.outlier_map.sum() > 100
    save_scan_figure(r, tmp_path / "dust.png", Config())
    assert (tmp_path / "dust.png").stat().st_size > 20_000


def test_csv_uses_lf_line_endings(tmp_path):
    write_csv([fake_result()], tmp_path / "r.csv", Config())
    assert b"\r\n" not in (tmp_path / "r.csv").read_bytes()
