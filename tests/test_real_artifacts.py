"""Measurement artefacts added to real scans (skipped when the data is absent).

Real optical-profilometer scans can carry artefacts the provided files do not
show: dust spikes, dust particles, scan-line streaks, ringing at steep edges
and missing pixels. Each is added to three real scans (a standard chip, the
other variant, and the noisy file 6), alone and all together. Every
measurement must stay close to the result on the unaltered scan, and the
faulty / clean verdict must not change.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from synthetic import add_edge_overshoot, add_particle, add_spikes, add_streaks

from teramount_analysis import Config, analyse_scan
from teramount_analysis.io import load_scan
from teramount_analysis.surface import slope

pytestmark = [pytest.mark.realdata, pytest.mark.slow]

ROOT = Path(__file__).resolve().parents[1]
FILES = (0, 12, 6)  # standard chip, other variant, noisy Pivot and Xpander
P = 0.252


def _dropouts(z: np.ndarray, seed: int = 0) -> np.ndarray:
    """2 % random missing pixels plus 30 % of the steep-wall pixels."""
    rng = np.random.default_rng(seed)
    out = z.copy()
    out.flat[rng.choice(z.size, int(0.02 * z.size), replace=False)] = np.nan
    walls = np.argwhere(slope(z, P) > 1.5)
    pick = walls[rng.random(len(walls)) < 0.3]
    out[pick[:, 0], pick[:, 1]] = np.nan
    return out


def _dust(z: np.ndarray, apex_xy: tuple[float, float]) -> np.ndarray:
    """Two 3 um particles: inside the dome fit area, and on the axis toward the Pivot."""
    ax, ay = apex_xy
    z = add_particle(z, (ax + 20 / P, ay + 15 / P), 3.0, 3.0)
    return add_particle(z, (ax, ay + 50 / P), 3.0, 3.0)


ARTEFACTS = {
    "spikes": lambda z, apex: add_spikes(z, 0.0005),
    "dust": _dust,
    "streaks": lambda z, apex: add_streaks(z, 0.03),
    "edge_ringing": lambda z, apex: add_edge_overshoot(z, 0.1),
    "dropouts": lambda z, apex: _dropouts(z),
    "all_together": lambda z, apex: _dropouts(
        add_streaks(add_spikes(_dust(z, apex), 0.0005), 0.02)),
}


@pytest.fixture(scope="module")
def baselines():
    out = {}
    for i in FILES:
        path = ROOT / "15_files_task_1" / f"{i}.npy"
        if not path.is_file():
            pytest.skip("provided dataset 15_files_task_1 not present")
        z = load_scan(path)
        r = analyse_scan(z, Config(), path.name)
        out[i] = (z, r, r.metrics(Config()))
    return out


@pytest.mark.parametrize("artefact", list(ARTEFACTS))
@pytest.mark.parametrize("file_index", FILES)
def test_artefact_leaves_results_and_verdict_unchanged(baselines, file_index, artefact):
    z, base, b = baselines[file_index]
    apex = (b["xpander_apex_x_px"], b["xpander_apex_y_px"])
    r = analyse_scan(ARTEFACTS[artefact](z, apex), Config(), f"{file_index}+{artefact}")
    m = r.metrics(Config())
    assert r.status == "ok", r.error
    assert r.faults.faulty == base.faults.faulty, (r.faults, base.faults)
    assert m["pivot_height_diff_um"] == pytest.approx(b["pivot_height_diff_um"], abs=0.03)
    # Radii: 0.3 %, or twice the scan's own 95 % interval on a noisy dome (file 6:
    # +-3.2 um); along streaks up to 0.6 % (their slow part is indistinguishable
    # from the surface, see test_pipeline).
    ry_rel = 0.006 if artefact in ("streaks", "all_together") else 0.003
    for axis, rel in (("x", 0.003), ("y", ry_rel)):
        tol = max(rel * b[f"xpander_r{axis}_um"], 2 * b[f"xpander_r{axis}_ci95_um"])
        assert m[f"xpander_r{axis}_um"] == pytest.approx(b[f"xpander_r{axis}_um"], abs=tol)
    for n in (1, 2):
        xy = (m[f"cross{n}_x_px"], m[f"cross{n}_y_px"])
        assert xy == pytest.approx((b[f"cross{n}_x_px"], b[f"cross{n}_y_px"]), abs=0.3), n
    assert m["rotation_deg"] == pytest.approx(b["rotation_deg"], abs=0.03)
