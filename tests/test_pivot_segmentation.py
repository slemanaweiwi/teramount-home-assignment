"""Tests for Pivot plane segmentation and coarse orientation."""

from __future__ import annotations

import numpy as np
import pytest
from helpers import seg
from scipy import ndimage
from synthetic import make_scan

from teramount_analysis.config import Config
from teramount_analysis.errors import ElementNotFoundError
from teramount_analysis.pivot import (
    find_plane2,
    quarter_turns_for,
    ramp_direction,
    segment_pivot,
)


def test_plane2_and_plane1_found():
    z, t = make_scan()
    reg = segment_pivot(seg(z), Config())
    # The smoothed 18 um cliff erodes the flat region more on the far side than the
    # gentle ramp does, shifting the centroid ~1 um toward the ramp: 6 px tolerance.
    assert reg.plane2_centroid_uv == pytest.approx(t.plane2_center_xy_px, abs=6)
    assert reg.plane2_level_um == pytest.approx(31.0, abs=0.1)
    assert 200 < reg.plane1.sum() * 0.252**2 < 3600  # µm²; 3600 = full plane-1 rectangle
    assert reg.axis_u == pytest.approx(t.plane2_center_xy_px[0], abs=2)
    assert not (reg.plane1 & reg.plane2).any()


def test_block_is_never_plane2():
    z, t = make_scan()
    p2 = find_plane2(seg(z), Config())
    cy, cx = ndimage.center_of_mass(p2)
    assert (cx, cy) == pytest.approx(t.plane2_center_xy_px, abs=6)


def test_noisy_pivot_still_segmented():
    z, _ = make_scan(pivot_noise_um=0.6)
    reg = segment_pivot(seg(z), Config())
    assert reg.plane1.sum() * 0.252**2 > 200


@pytest.mark.parametrize("k,expected", [(0, (0, -1)), (2, (0, 1)), (1, (-1, 0)), (3, (1, 0))])
def test_ramp_direction_follows_quarter_turns(k, expected):
    z, _ = make_scan(quarter_turns=k)
    s = seg(z)
    d = ramp_direction(s, find_plane2(s, Config()), Config())
    assert np.dot(d, expected) > 0.95


def test_symmetric_plateau_has_no_ramp_direction():
    # A plateau with identical ramps on all four sides (a square frustum): the
    # downhill directions cancel, so the orientation must not be guessed.
    p = 0.252
    rows, cols = np.indices((600, 600), dtype=float)
    d = np.maximum(np.abs(cols - 299.5), np.abs(rows - 299.5)) * p  # µm from the centre
    z = ndimage.gaussian_filter(np.clip(30.0 - (d - 10.0), 0.0, 30.0), 1.0 / p)
    plane2 = d <= 9.0
    with pytest.raises(ElementNotFoundError, match="ambiguous"):
        ramp_direction(z, plane2, Config())


@pytest.mark.parametrize("d,k", [((0, -1), 0), ((1, 0), 1), ((0, 1), 2), ((-1, 0), 3)])
def test_quarter_turns_for(d, k):
    assert quarter_turns_for(d) == k


def test_upside_down_scan_rejected_without_turning():
    z, _ = make_scan(quarter_turns=2)
    with pytest.raises(ElementNotFoundError, match="orientation"):
        segment_pivot(seg(z), Config())


def test_two_channels_picks_most_central():
    z, t = make_scan(shape=(1200, 1000), channel_offset_um=-50, second_channel=True)
    p2 = find_plane2(seg(z), Config())
    _, cx = ndimage.center_of_mass(p2)
    assert cx == pytest.approx(t.plane2_center_xy_px[0], abs=4)


def test_featureless_scan_raises():
    with pytest.raises(ElementNotFoundError, match="plane 2"):
        find_plane2(np.zeros((300, 300)), Config())
