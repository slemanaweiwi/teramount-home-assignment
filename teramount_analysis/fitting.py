"""Least-squares models shared by the analysis steps.

* planes: ordinary, robust (iterative outlier clipping) and RANSAC;
* the quadric surface used for the Xpander curvature;
* sphere and circle fits used as independent cross-checks.

All functions take flat coordinate arrays in consistent units (the analysis
uses µm for x, y and z) and raise :class:`~teramount_analysis.errors.FitError`
when the data cannot support the model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

from .errors import FitError

_MAD_TO_SIGMA = 1.4826  # MAD of a normal distribution x 1.4826 = sigma


def _flat(*arrays: np.ndarray) -> tuple[np.ndarray, ...]:
    out = tuple(np.asarray(a, dtype=np.float64).ravel() for a in arrays)
    if len({a.size for a in out}) != 1:
        raise FitError("coordinate arrays have different lengths")
    return out


# --------------------------------------------------------------------------- planes


@dataclass(frozen=True)
class PlaneFit:
    """Plane ``z = a*x + b*y + c``."""

    a: float
    b: float
    c: float
    rms: float  # root-mean-square residual of the points used
    n_used: int  # number of points the final fit used

    def evaluate(self, x: np.ndarray | float, y: np.ndarray | float) -> np.ndarray:
        """Plane height at ``(x, y)``."""
        return self.a * np.asarray(x) + self.b * np.asarray(y) + self.c

    def normal(self) -> np.ndarray:
        """Unit normal vector pointing to +z."""
        n = np.array([-self.a, -self.b, 1.0])
        return n / np.linalg.norm(n)


def fit_plane(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> PlaneFit:
    """Ordinary least-squares plane.

    Raises
    ------
    FitError
        With fewer than 3 points or collinear points.
    """
    x, y, z = _flat(x, y, z)
    if x.size < 3:
        raise FitError(f"plane fit needs >= 3 points, got {x.size}")
    mx, my, mz = x.mean(), y.mean(), z.mean()  # centring keeps the system well conditioned
    a_mat = np.column_stack([x - mx, y - my, np.ones_like(x)])
    sol, _, rank, _ = np.linalg.lstsq(a_mat, z - mz, rcond=None)
    if rank < 3:
        raise FitError("plane fit: points are collinear")
    a, b, c0 = sol
    c = c0 + mz - a * mx - b * my
    res = z - (a * x + b * y + c)
    return PlaneFit(float(a), float(b), float(c), float(np.sqrt(np.mean(res**2))), int(x.size))


def fit_plane_robust(x: np.ndarray, y: np.ndarray, z: np.ndarray, clip_sigma: float = 3.0,
                     iterations: int = 5) -> PlaneFit:
    """Plane fit that ignores outliers.

    Starts from the least-squares plane and repeatedly refits on the points
    whose residual lies within ``clip_sigma`` robust standard deviations
    (1.4826 x median absolute deviation, floored at 1e-6) of the median
    residual. Typical outliers: a cross etched into the plane, dust, edges.
    """
    x, y, z = _flat(x, y, z)
    fit = fit_plane(x, y, z)
    keep = np.ones(x.size, dtype=bool)
    for _ in range(iterations):
        res = z - fit.evaluate(x, y)
        med = np.median(res[keep])
        sigma = max(_MAD_TO_SIGMA * np.median(np.abs(res[keep] - med)), 1e-6)
        new_keep = np.abs(res - med) < clip_sigma * sigma
        if new_keep.sum() < 3 or np.array_equal(new_keep, keep):
            break
        keep = new_keep
        fit = fit_plane(x[keep], y[keep], z[keep])
    res_in = z[keep] - fit.evaluate(x[keep], y[keep])
    return PlaneFit(fit.a, fit.b, fit.c, float(np.sqrt(np.mean(res_in**2))), int(keep.sum()))


def ransac_plane(x: np.ndarray, y: np.ndarray, z: np.ndarray, tol: float, iterations: int,
                 rng: np.random.Generator) -> np.ndarray:
    """Inlier mask of the plane supported by the most points (RANSAC).

    Each iteration fits a plane through 3 random points and counts the points
    within ``tol`` of it; the largest consensus wins. Robust even when the
    plane holds well under half of the points.
    """
    x, y, z = _flat(x, y, z)
    n = x.size
    if n < 3:
        raise FitError(f"RANSAC needs >= 3 points, got {n}")
    scale2 = (np.ptp(x) + np.ptp(y)) ** 2 + 1e-300
    best_mask, best_count = None, -1
    for _ in range(iterations):
        i = rng.choice(n, size=3, replace=False)
        area2 = abs((x[i[1]] - x[i[0]]) * (y[i[2]] - y[i[0]])
                    - (x[i[2]] - x[i[0]]) * (y[i[1]] - y[i[0]]))
        if area2 < 1e-9 * scale2:  # (nearly) collinear sample
            continue
        a, b, c = np.linalg.solve(np.column_stack([x[i], y[i], np.ones(3)]), z[i])
        mask = np.abs(z - (a * x + b * y + c)) < tol
        count = int(mask.sum())
        if count > best_count:
            best_mask, best_count = mask, count
    if best_mask is None:
        raise FitError("RANSAC found no valid plane")
    return best_mask


# --------------------------------------------------------------------------- quadric


@dataclass(frozen=True, eq=False)
class QuadricFit:
    """Surface ``z = c0 + c1*u + c2*v + c3*u^2 + c4*v^2 + c5*u*v``."""

    coeffs: np.ndarray  # (6,) c0..c5
    cov: np.ndarray  # (6, 6) parameter covariance = sigma^2 (A^T A)^-1
    rms: float  # root-mean-square residual
    r_squared: float  # coefficient of determination
    n: int  # number of points
    residuals: np.ndarray  # z - model, in input order

    def evaluate(self, u: np.ndarray | float, v: np.ndarray | float) -> np.ndarray:
        """Model height at ``(u, v)``."""
        c = self.coeffs
        u, v = np.asarray(u), np.asarray(v)
        return c[0] + c[1] * u + c[2] * v + c[3] * u**2 + c[4] * v**2 + c[5] * u * v

    def hessian(self) -> np.ndarray:
        """Matrix of second derivatives ``[[2c3, c5], [c5, 2c4]]``."""
        c = self.coeffs
        return np.array([[2 * c[3], c[5]], [c[5], 2 * c[4]]])

    def vertex(self) -> tuple[float, float]:
        """Stationary point (apex of a dome).

        Raises
        ------
        FitError
            If the surface has no unique stationary point (e.g. a plane).
        """
        h = self.hessian()
        if abs(np.linalg.det(h)) < 1e-18:
            raise FitError("quadric has no unique vertex (singular Hessian)")
        u0, v0 = np.linalg.solve(h, -self.coeffs[1:3])
        return float(u0), float(v0)


def fit_quadric(u: np.ndarray, v: np.ndarray, z: np.ndarray) -> QuadricFit:
    """Least-squares quadric surface with parameter covariance.

    The design matrix is column-scaled before solving (conditioning) and the
    coefficients and covariance are transformed back, so they refer to the
    caller's ``(u, v)`` coordinates.
    """
    u, v, z = _flat(u, v, z)
    n = u.size
    if n < 10:
        raise FitError(f"quadric fit needs >= 10 points, got {n}")
    s = max(np.abs(u).max(), np.abs(v).max(), 1e-12)
    us, vs = u / s, v / s
    a_s = np.column_stack([np.ones(n), us, vs, us**2, vs**2, us * vs])
    coef_s, _, rank, _ = np.linalg.lstsq(a_s, z, rcond=None)
    if rank < 6:
        raise FitError("quadric fit: points do not span a 2-D area")
    scale = np.array([1.0, s, s, s**2, s**2, s**2])
    coeffs = coef_s / scale
    residuals = z - a_s @ coef_s
    sse = float(residuals @ residuals)
    sigma2 = sse / max(n - 6, 1)
    cov_s = sigma2 * np.linalg.inv(a_s.T @ a_s)
    cov = cov_s / np.outer(scale, scale)
    sst = float(((z - z.mean()) ** 2).sum())
    r_squared = 1.0 - sse / sst if sst > 0 else (1.0 if sse == 0 else 0.0)
    return QuadricFit(coeffs, cov, float(np.sqrt(sse / n)), float(r_squared), n, residuals)


# --------------------------------------------------------------------------- sphere / circle


@dataclass(frozen=True)
class SphereFit:
    """Sphere with centre ``(xc, yc, zc)`` and ``radius``."""

    xc: float
    yc: float
    zc: float
    radius: float
    rms: float  # root-mean-square geometric residual


def fit_sphere(x: np.ndarray, y: np.ndarray, z: np.ndarray,
               initial: tuple[float, float, float, float]) -> SphereFit:
    """Geometric least-squares sphere (minimises distance to the surface).

    Internally parametrised by the apex height ``h = zc + R`` instead of
    ``zc``: for a shallow cap ``zc`` and ``R`` are almost perfectly correlated,
    while ``h`` and ``R`` are not, which makes the problem well conditioned.

    Parameters
    ----------
    initial
        Starting guess ``(xc, yc, zc, R)``.
    """
    x, y, z = _flat(x, y, z)
    if x.size < 4:
        raise FitError(f"sphere fit needs >= 4 points, got {x.size}")
    xc0, yc0, zc0, r0 = initial

    def residuals(p: np.ndarray) -> np.ndarray:
        xc, yc, h, r = p
        return np.sqrt((x - xc) ** 2 + (y - yc) ** 2 + (z - h + r) ** 2) - r

    sol = least_squares(residuals, x0=[xc0, yc0, zc0 + r0, r0], method="lm",
                        xtol=1e-14, ftol=1e-14, gtol=1e-14)
    xc, yc, h, r = sol.x
    return SphereFit(float(xc), float(yc), float(h - r), float(abs(r)),
                     float(np.sqrt(np.mean(sol.fun**2))))


def fit_profile_circle(s: np.ndarray, z: np.ndarray) -> tuple[float, float]:
    """Radius of the circle best fitting a 1-D profile ``z(s)``.

    The starting guess comes from a parabola fit; the circle is then refined by
    geometric least squares (apex-height parametrisation, as in
    :func:`fit_sphere`).

    Returns
    -------
    (radius, rms)
    """
    s, z = _flat(s, z)
    if s.size < 5:
        raise FitError(f"profile circle fit needs >= 5 points, got {s.size}")
    p2, p1, p0 = np.polyfit(s, z, 2)
    if p2 == 0:
        raise FitError("profile is straight; no curvature")
    s0 = -p1 / (2 * p2)
    apex = p0 + p1 * s0 + p2 * s0**2
    r0 = 1.0 / (2 * abs(p2))
    sign = 1.0 if p2 < 0 else -1.0  # dome: centre below the apex

    def residuals(p: np.ndarray) -> np.ndarray:
        sc, h, r = p
        return np.sqrt((s - sc) ** 2 + (z - h + sign * r) ** 2) - r

    sol = least_squares(residuals, x0=[s0, apex, r0], method="lm",
                        xtol=1e-14, ftol=1e-14, gtol=1e-14)
    return float(abs(sol.x[2])), float(np.sqrt(np.mean(sol.fun**2)))
