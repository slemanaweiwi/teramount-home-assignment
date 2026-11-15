"""Tests for scan discovery and loading."""

from __future__ import annotations

import numpy as np
import pytest

from teramount_analysis.errors import ScanLoadError
from teramount_analysis.io import discover_scans, load_scan


def test_discover_sorts_naturally(tmp_path):
    for n in (10, 2, 1):
        np.save(tmp_path / f"{n}.npy", np.zeros((64, 64)))
    assert [p.name for p in discover_scans(tmp_path)] == ["1.npy", "2.npy", "10.npy"]


def test_discover_single_file(tmp_path):
    path = tmp_path / "scan.npy"
    np.save(path, np.zeros((64, 64)))
    assert discover_scans(path) == [path]


def test_discover_missing_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        discover_scans(tmp_path / "does_not_exist")


def test_discover_empty_folder_raises(tmp_path):
    with pytest.raises(ScanLoadError):
        discover_scans(tmp_path)


def test_discover_rejects_non_npy_file(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("not a scan")
    with pytest.raises(ScanLoadError):
        discover_scans(path)


def test_load_applies_z_scale(tmp_path):
    np.save(tmp_path / "a.npy", np.ones((64, 80)))
    z = load_scan(tmp_path / "a.npy", z_scale=1e-3)
    assert z.dtype == np.float64 and z.shape == (64, 80) and np.allclose(z, 1e-3)


def test_load_returns_independent_float64_copy(tmp_path):
    np.save(tmp_path / "i.npy", np.arange(64 * 64, dtype=np.int32).reshape(64, 64))
    z = load_scan(tmp_path / "i.npy")
    assert z.dtype == np.float64 and z[0, 1] == 1.0


@pytest.mark.parametrize("shape", [(100,), (64, 64, 3)])
def test_load_rejects_non_2d(tmp_path, shape):
    np.save(tmp_path / "bad.npy", np.zeros(shape))
    with pytest.raises(ScanLoadError, match="2-D"):
        load_scan(tmp_path / "bad.npy")


def test_load_rejects_tiny_and_all_nan(tmp_path):
    np.save(tmp_path / "tiny.npy", np.zeros((10, 10)))
    np.save(tmp_path / "nan.npy", np.full((64, 64), np.nan))
    with pytest.raises(ScanLoadError, match="small"):
        load_scan(tmp_path / "tiny.npy")
    with pytest.raises(ScanLoadError, match="finite"):
        load_scan(tmp_path / "nan.npy")


def test_load_rejects_corrupt_and_pickled_files(tmp_path):
    (tmp_path / "garbage.npy").write_bytes(b"this is not a numpy file")
    np.save(tmp_path / "obj.npy", np.array([object()], dtype=object), allow_pickle=True)
    with pytest.raises(ScanLoadError):
        load_scan(tmp_path / "garbage.npy")
    with pytest.raises(ScanLoadError):
        load_scan(tmp_path / "obj.npy")
