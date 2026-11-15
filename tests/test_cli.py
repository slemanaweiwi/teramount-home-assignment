"""Tests for the command-line interface."""

from __future__ import annotations

import csv

import numpy as np
from synthetic import make_scan

from teramount_analysis.cli import build_parser, config_from_args, main


def _read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_cli_runs_on_folder(tmp_path, capsys):
    data = tmp_path / "scans"
    data.mkdir()
    np.save(data / "0.npy", make_scan()[0])
    np.save(data / "1.npy", make_scan(rotation_deg=0.5)[0])
    assert main(["--data", str(data), "--out", str(tmp_path / "out"), "--name", "t"]) == 0
    rows = _read(tmp_path / "out" / "t_results.csv")
    assert [r["file"] for r in rows] == ["0.npy", "1.npy"]
    assert all(r["status"] == "ok" for r in rows)
    assert (tmp_path / "out" / "figures" / "t" / "1.png").exists()
    printed = capsys.readouterr().out
    assert "0.npy" in printed and "t_results.csv" in printed


def test_cli_default_name_is_folder_name(tmp_path):
    data = tmp_path / "my_scans"
    data.mkdir()
    np.save(data / "0.npy", make_scan()[0])
    assert main(["--data", str(data), "--out", str(tmp_path / "out"), "--no-figures"]) == 0
    assert (tmp_path / "out" / "my_scans_results.csv").exists()
    assert not (tmp_path / "out" / "figures").exists()


def test_cli_missing_path_exit_2(tmp_path, capsys):
    assert main(["--data", str(tmp_path / "nope")]) == 2
    assert "not found" in capsys.readouterr().err.lower()


def test_cli_all_failed_exit_1(tmp_path):
    data = tmp_path / "bad"
    data.mkdir()
    (data / "0.npy").write_bytes(b"garbage")
    assert main(["--data", str(data), "--out", str(tmp_path / "out"), "--no-figures"]) == 1
    assert _read(tmp_path / "out" / "bad_results.csv")[0]["status"] == "failed"


def test_cli_overrides_reach_config():
    args = build_parser().parse_args(["--data", "x", "--pixel-size", "0.5", "--nominal-step", "17",
                                      "--no-rotation-correction", "--z-scale", "0.001"])
    c = config_from_args(args)
    assert c.pixel_size_um == 0.5 and c.nominal_pivot_step_um == 17
    assert not c.correct_rotation and c.correct_tilt and c.z_scale == 0.001
