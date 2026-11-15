"""Tests for the least-squares fitting primitives."""

from __future__ import annotations

import numpy as np
import pytest

from teramount_analysis.errors import FitError
from teramount_analysis.fitting import (
    fit_plane,
    fit_plane_robust,
    fit_profile_circle,
    fit_quadric,
    fit_sphere,
    ransac_plane,
)


def _grid(n=40):
    x, y = np.meshgrid(np.arange(float(n)), np.arange(float(n)))
    return x.ravel(), y.ravel()


def test_plane_exact():
    x, y = np.meshgrid(np.arange(20.0), np.arange(30.0))
    f = fit_plane(x.ravel(), y.ravel(), (0.01 * x - 0.02 * y + 3).ravel())
    assert (f.a, f.b, f.c) == pytest.approx((0.01, -0.02, 3.0), abs=1e-12)
    assert f.rms == pytest.approx(0.0, abs=1e-12) and f.n_used == 600


def test_plane_normal_points_up():
    x, y = _grid(10)
    f = fit_plane(x, y, 0.0 * x + 1.0)
    assert f.normal() == pytest.approx((0.0, 0.0, 1.0))


def test_robust_plane_ignores_20pct_outliers():
    rng = np.random.default_rng(1)
    x, y = _grid()
    z = 0.01 * x - 0.02 * y + 3 + rng.normal(0, 1e-4, x.size)
    outliers = rng.choice(x.size, size=x.size // 5, replace=False)
    z[outliers] += 2.0
    robust = fit_plane_robust(x, y, z)
    ols = fit_plane(x, y, z)
    assert (robust.a, robust.b, robust.c) == pytest.approx((0.01, -0.02, 3.0), abs=1e-3)
    assert abs(ols.c - 3.0) > 0.1
    assert robust.n_used == pytest.approx(0.8 * x.size, rel=0.02)
    assert robust.rms == pytest.approx(1e-4, rel=0.2)


def test_ransac_finds_majority_plane():
    rng = np.random.default_rng(2)
    n = 5000
    x, y = rng.uniform(0, 500, n), rng.uniform(0, 700, n)
    on_a = rng.random(n) < 0.6
    z = 0.01 * x + 0.02 * y + np.where(on_a, 0.0, 5.0) + rng.normal(0, 0.01, n)
    inliers = ransac_plane(x, y, z, tol=0.05, iterations=100, rng=np.random.default_rng(0))
    assert (inliers == on_a).mean() >= 0.99


def test_quadric_recovers_curvature_and_vertex():
    u, v = np.meshgrid(np.linspace(-40, 40, 161), np.linspace(-40, 40, 161))
    z = 2.0 + 0.003 * u - 0.002 * v - u**2 / (2 * 800) - v**2 / (2 * 850)
    q = fit_quadric(u.ravel(), v.ravel(), z.ravel())
    assert -1 / (2 * q.coeffs[3]) == pytest.approx(800, rel=1e-9)
    assert -1 / (2 * q.coeffs[4]) == pytest.approx(850, rel=1e-9)
    assert q.vertex() == pytest.approx((0.003 * 800, -0.002 * 850), rel=1e-6)
    assert q.r_squared == pytest.approx(1.0) and q.n == u.size


def test_quadric_noise_statistics():
    rng = np.random.default_rng(3)
    u, v = (a.ravel() for a in np.meshgrid(np.linspace(-40, 40, 121), np.linspace(-40, 40, 121)))
    z = 2.0 - u**2 / 1600 - v**2 / 1700 + rng.normal(0, 0.01, u.size)
    q = fit_quadric(u, v, z)
    assert q.rms == pytest.approx(0.01, rel=0.05)
    assert 0.99 < q.r_squared < 1.0
    se_c3 = np.sqrt(q.cov[3, 3])
    assert abs(q.coeffs[3] + 1 / 1600) < 4 * se_c3  # truth inside a 4-sigma band
    assert q.hessian() == pytest.approx(np.array([[2 * q.coeffs[3], q.coeffs[5]],
                                                  [q.coeffs[5], 2 * q.coeffs[4]]]))


def test_quadric_vertex_of_a_plane_raises():
    u, v = _grid(20)
    with pytest.raises(FitError):
        fit_quadric(u, v, 0.1 * u + 2.0).vertex()


def test_too_few_points_raise():
    with pytest.raises(FitError):
        fit_plane(np.arange(2.0), np.arange(2.0), np.arange(2.0))
    with pytest.raises(FitError):
        fit_quadric(np.arange(5.0), np.arange(5.0), np.arange(5.0))


def test_sphere_and_profile_circle_recover_radius():
    radius, xc, yc, apex = 830.0, 5.0, -3.0, 12.0
    u, v = (a.ravel() for a in np.meshgrid(np.linspace(-45, 45, 181), np.linspace(-45, 45, 181)))
    inside = (u - xc) ** 2 + (v - yc) ** 2 <= 45**2
    u, v = u[inside], v[inside]
    z = apex - radius + np.sqrt(radius**2 - (u - xc) ** 2 - (v - yc) ** 2)
    s = fit_sphere(u, v, z, initial=(0.0, 0.0, apex - 800.0, 800.0))
    assert s.radius == pytest.approx(radius, rel=5e-4)
    assert (s.xc, s.yc) == pytest.approx((xc, yc), abs=0.05)
    profile = np.abs(v - yc) < 1e-9
    r_profile, rms = fit_profile_circle(u[profile], z[profile])
    assert r_profile == pytest.approx(radius, rel=1e-3) and rms < 1e-6
