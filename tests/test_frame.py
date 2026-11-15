"""Tests for the original <-> canonical coordinate frame."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import ndimage

from teramount_analysis.frame import Frame


@pytest.mark.parametrize("phi,k", [(0.0, 0), (1.0, 0), (-0.75, 0), (3.0, 1), (0.5, 2), (-2.0, 3)])
def test_roundtrip(phi, k):
    f = Frame((300, 200), phi, k)
    x = np.random.default_rng(0).uniform(0, 199, 50)
    y = np.random.default_rng(1).uniform(0, 299, 50)
    assert np.allclose(f.to_original(*f.to_canonical(x, y)), (x, y), atol=1e-9)


@pytest.mark.parametrize("phi,k", [(10.0, 0), (-4.0, 1), (7.0, 2), (2.0, 3)])
def test_canonical_image_matches_to_canonical(phi, k):
    img = np.zeros((301, 201))
    img[60, 140] = 1.0
    f = Frame(img.shape, phi, k)
    cy, cx = ndimage.center_of_mass(f.canonical_image(img))
    assert (cx, cy) == pytest.approx(f.to_canonical(140.0, 60.0), abs=0.15)


@pytest.mark.parametrize("k", [0, 1, 2, 3])
def test_canonical_valid_everywhere_without_fine_rotation(k):
    f = Frame((300, 200), 0.0, k)
    assert f.canonical_valid().shape == f.canonical_shape and f.canonical_valid().all()


@pytest.mark.parametrize("phi,k", [(10.0, 0), (-8.0, 1)])
def test_canonical_valid_excludes_extrapolated_corners(phi, k):
    f = Frame((300, 200), phi, k)
    valid = f.canonical_valid()
    v, u = np.indices(f.canonical_shape, dtype=float)
    x, y = f.to_original(u, v)
    inside = (x >= 0) & (x <= 199) & (y >= 0) & (y <= 299)
    assert valid.shape == f.canonical_shape and 0.8 < valid.mean() < 0.95
    assert not valid[0, 0] and not valid[-1, -1] and valid[150 if k % 2 == 0 else 100, 100]
    assert (valid == inside).mean() > 0.999  # equal except on the boundary itself


def test_rotation_deg_normalised():
    assert Frame((10, 10), 1.0, 2).rotation_deg == pytest.approx(-179.0)
    assert Frame((10, 10), 0.0, 2).rotation_deg == pytest.approx(180.0)
    assert Frame((10, 10), -0.5, 1).rotation_deg == pytest.approx(-90.5)
    assert Frame((10, 10), 0.5, 3).rotation_deg == pytest.approx(90.5)


def test_canonical_shape_swaps_on_odd_turns():
    assert Frame((300, 200), 0.0, 1).canonical_shape == (200, 300)
    assert Frame((300, 200), 0.0, 2).canonical_shape == (300, 200)
    assert Frame((300, 200), 0.0, 1).canonical_image(np.zeros((300, 200))).shape == (200, 300)


def test_canonical_coordinates_match_to_canonical():
    f = Frame((30, 20), 5.0, 1)
    u, v = f.canonical_coordinates()
    assert u.shape == (30, 20)
    assert (u[7, 3], v[7, 3]) == pytest.approx(f.to_canonical(3.0, 7.0))
    assert f.canonical_coordinates()[0] is u  # cached


def test_pull_back_identity_when_unrotated():
    m = np.zeros((50, 40), bool)
    m[10:20, 5:9] = True
    assert (Frame(m.shape, 0.0).pull_back(m) == m).all()


def test_pull_back_rotated_disk():
    f = Frame((400, 300), 3.0, 1)
    hc, wc = f.canonical_shape
    vv, uu = np.indices((hc, wc))
    disk = (uu - 180) ** 2 + (vv - 140) ** 2 <= 20**2
    back = f.pull_back(disk)
    u, v = f.canonical_coordinates()
    assert np.all((u[back] - 180) ** 2 + (v[back] - 140) ** 2 <= 21**2)
    assert back.sum() == pytest.approx(np.pi * 20**2, rel=0.05)


def test_canonical_image_fills_nans():
    img = np.ones((60, 50))
    img[5:8, 5:8] = np.nan
    assert np.isfinite(Frame(img.shape, 2.0).canonical_image(img)).all()


def test_pull_back_rejects_wrong_shape():
    with pytest.raises(ValueError):
        Frame((40, 30), 0.0, 1).pull_back(np.zeros((40, 30), bool))
