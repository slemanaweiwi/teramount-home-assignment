"""Xpander: apex search, automatic aperture, surface fit and curvature.

The Xpander is the dome above the Pivot on the channel axis. Neighbouring
Xpanders form a row like a microlens array and meet at gentle valleys rather
than steep edges, so the dome is delimited geometrically:

1. **Apex**: walking away from the Pivot along the axis, the first prominent
   peak of the smoothed height profile.
2. **Aperture**: rays are cast from the apex until the surface stops
   descending (the valley to a neighbour) or meets a steep step; the fit uses a
   circle of ``xpander_aperture_fraction`` x the shortest ray, so it only sees
   this dome's surface.
3. **Fit**: the quadric ``z = c0 + c1 u + c2 v + c3 u² + c4 v² + c5 uv`` is
   fitted by least squares to the original pixels (canonical coordinates in
   µm, relative to the apex). The linear terms absorb any residual tilt, and
   the curvature along an axis is the second derivative: Rx = -1/(2 c3),
   Ry = -1/(2 c4). The fit is re-centred on the fitted vertex and repeated.

Figures of merit and cross-checks: RMS residual, residual / sag (nRMS), R²,
95 % confidence intervals of Rx, Ry from the parameter covariance, principal
radii, the stability of R over smaller apertures, an exact sphere fit, and
circle fits to the X and Y profiles through the apex.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.signal import find_peaks

from .config import Config
from .errors import ElementNotFoundError, FitError
from .fitting import QuadricFit, fit_profile_circle, fit_quadric, fit_sphere
from .frame import Frame
from .pivot import PivotRegions
from .surface import slope, smooth

_NAN = float("nan")


@dataclass(frozen=True, eq=False)
class XpanderResult:
    """Xpander measurement. When ``found`` is False every number is NaN."""

    found: bool
    reason: str  # why the Xpander was not measured ("" when found)
    apex_x_px: float  # apex (fitted vertex), original frame
    apex_y_px: float
    apex_u_px: float  # apex, canonical frame
    apex_v_px: float
    apex_z_um: float  # fitted apex height above the base [µm]
    axis_offset_um: float  # |u_apex - channel axis| [µm]
    aperture_radius_um: float  # radius of the fitted area [µm]
    rx_um: float  # radius of curvature along the chip x axis [µm]
    ry_um: float  # radius of curvature along the chip y axis [µm]
    rx_ci95_um: float  # 95 % confidence half-width of rx [µm]
    ry_ci95_um: float
    r1_um: float  # smaller principal radius [µm]
    r2_um: float  # larger principal radius [µm]
    principal_angle_deg: float  # direction of R1 from +u, in (-90, 90] [deg]
    rms_um: float  # RMS fit residual [µm]
    nrms_pct: float  # RMS residual / sag [%]
    r_squared: float  # coefficient of determination
    sag_um: float  # height of the fitted dome over the aperture [µm]
    r_sphere_um: float  # radius of the best-fit sphere (cross-check) [µm]
    rx_profile_um: float  # circle fit to the x profile through the apex [µm]
    ry_profile_um: float  # circle fit to the y profile through the apex [µm]
    stability_pct: float  # spread of R over the stability apertures [%]
    n_points: int  # pixels in the fit
    residual_map: np.ndarray | None  # canonical-frame residuals [µm], NaN elsewhere

    @classmethod
    def not_found(cls, reason: str) -> XpanderResult:
        """Result for an Xpander that could not be measured."""
        return cls(False, reason, *([_NAN] * 22), 0, None)


_not_found = XpanderResult.not_found


def _apex_seed(zs: np.ndarray, regions: PivotRegions, config: Config) -> tuple[float, float]:
    """First prominent peak above the Pivot on the axis, refined locally."""
    u = int(round(regions.axis_u))
    top = int(np.nonzero(regions.plane1.any(axis=1))[0].min())
    start = top - 5
    stop = max(start - int(config.px(config.xpander_search_um)), -1)
    if start <= 0:
        raise ElementNotFoundError("no room above the Pivot for an Xpander")
    rows = np.arange(start, stop, -1)  # walking away from the Pivot
    peaks, _ = find_peaks(zs[rows, u], prominence=config.xpander_min_prominence_um)
    if len(peaks) == 0:
        raise ElementNotFoundError("Xpander apex not found (no prominent dome above the Pivot)")
    v = int(rows[peaks[0]])
    half = int(round(config.px(config.xpander_refine_um)))
    r0, c0 = max(v - half, 0), max(u - half, 0)
    window = zs[r0:v + half + 1, c0:u + half + 1]
    dv, du = np.unravel_index(int(np.argmax(window)), window.shape)
    return float(c0 + du), float(r0 + dv)


def locate_apex(z_canonical: np.ndarray, regions: PivotRegions, config: Config
                ) -> tuple[float, float]:
    """Canonical ``(u, v)`` seed of the Xpander apex.

    Raises
    ------
    ElementNotFoundError
        If no prominent dome lies above the Pivot.
    """
    return _apex_seed(smooth(z_canonical, config.px(config.xpander_smooth_um)), regions, config)


def boundary_distances(z_smooth: np.ndarray, apex_uv: tuple[float, float], config: Config
                       ) -> np.ndarray:
    """Distance (px) from the apex to the dome boundary along each ray.

    A ray stops where the slope exceeds ``xpander_steep_slope`` (a step), where
    the height rises ``xpander_ray_rise_um`` above its running minimum (the
    valley to a neighbouring dome is behind), or at the image border.
    """
    u0, v0 = apex_uv
    rows, cols = z_smooth.shape
    rmax = int(config.px(config.xpander_search_um))
    r = np.arange(1, rmax + 1, dtype=np.float64)
    grad = slope(z_smooth, config.pixel_size_um)
    out = np.empty(config.xpander_ray_count)
    for i, a in enumerate(np.linspace(0, 2 * np.pi, config.xpander_ray_count, endpoint=False)):
        ui = np.rint(u0 + r * math.cos(a)).astype(np.intp)
        vi = np.rint(v0 + r * math.sin(a)).astype(np.intp)
        inside = (ui >= 0) & (ui < cols) & (vi >= 0) & (vi < rows)
        n_in = int(np.argmin(inside)) if not inside.all() else rmax
        h = z_smooth[vi[:n_in], ui[:n_in]]
        prev_min = np.minimum.accumulate(np.r_[h[:1], h[:-1]]) if n_in else h
        stop = (grad[vi[:n_in], ui[:n_in]] > config.xpander_steep_slope) | (
            h > prev_min + config.xpander_ray_rise_um)
        out[i] = r[int(np.argmax(stop))] if stop.any() else (r[n_in - 1] + 1 if n_in else 1.0)
    return out


@dataclass(frozen=True, eq=False)
class _Aperture:
    rows: np.ndarray
    cols: np.ndarray
    du: np.ndarray  # u - u_apex [µm]
    dv: np.ndarray  # v - v_apex [µm]
    z: np.ndarray


def _select(z_leveled: np.ndarray, frame: Frame, u0: float, v0: float, radius_px: float
            ) -> _Aperture:
    """Original pixels whose canonical position lies within the aperture."""
    x0, y0 = frame.to_original(u0, v0)  # rotations preserve distances
    r0, r1 = max(int(y0 - radius_px) - 2, 0), int(y0 + radius_px) + 3
    c0, c1 = max(int(x0 - radius_px) - 2, 0), int(x0 + radius_px) + 3
    u_all, v_all = frame.canonical_coordinates()
    u, v, z = u_all[r0:r1, c0:c1], v_all[r0:r1, c0:c1], z_leveled[r0:r1, c0:c1]
    inside = ((u - u0) ** 2 + (v - v0) ** 2 <= radius_px**2) & np.isfinite(z)
    rr, cc = np.nonzero(inside)
    return _Aperture(rr + r0, cc + c0, u[rr, cc] - u0, v[rr, cc] - v0, z[rr, cc])


def _fit(ap: _Aperture, pixel_size_um: float) -> QuadricFit:
    q = fit_quadric(ap.du * pixel_size_um, ap.dv * pixel_size_um, ap.z)
    if q.coeffs[3] >= 0 or q.coeffs[4] >= 0:
        raise FitError("surface not convex")
    return q


def measure_xpander(z_leveled: np.ndarray, frame: Frame, z_canonical: np.ndarray,
                    regions: PivotRegions, config: Config) -> XpanderResult:
    """Locate the Xpander and measure its radii of curvature.

    Never raises for a missing or unmeasurable Xpander; returns
    ``found=False`` with the reason instead.
    """
    p = config.pixel_size_um
    zs = smooth(z_canonical, config.px(config.xpander_smooth_um))
    try:
        u0, v0 = _apex_seed(zs, regions, config)
    except ElementNotFoundError as exc:
        return _not_found(str(exc))

    def aperture_radius(u: float, v: float) -> float:
        shortest_ray = float(boundary_distances(zs, (u, v), config).min())
        return config.xpander_aperture_fraction * shortest_ray

    try:
        for _ in range(config.xpander_fit_iterations):
            radius = aperture_radius(u0, v0)
            if radius < config.px(config.xpander_min_aperture_um):
                return _not_found("aperture too small (dome cut by border or neighbour)")
            q = _fit(_select(z_leveled, frame, u0, v0, radius), p)
            du0, dv0 = q.vertex()
            if math.hypot(du0, dv0) / p > radius / 2:
                return _not_found("apex unstable")
            u0, v0 = u0 + du0 / p, v0 + dv0 / p
        radius = aperture_radius(u0, v0)
        if radius < config.px(config.xpander_min_aperture_um):
            return _not_found("aperture too small (dome cut by border or neighbour)")
        ap = _select(z_leveled, frame, u0, v0, radius)
        q = _fit(ap, p)
    except FitError as exc:
        return _not_found(str(exc))
    return _summarise(q, ap, frame, regions, u0, v0, radius, config)


def _summarise(q: QuadricFit, ap: _Aperture, frame: Frame, regions: PivotRegions, u0: float,
               v0: float, radius_px: float, config: Config) -> XpanderResult:
    p = config.pixel_size_um
    c, cov = q.coeffs, q.cov
    du, dv = ap.du * p, ap.dv * p
    lam, vec = np.linalg.eigh(q.hessian())  # ascending: lam[0] most curved
    angle = math.degrees(math.atan2(vec[1, 0], vec[0, 0]))
    angle = angle + 180.0 if angle <= -90.0 else (angle - 180.0 if angle > 90.0 else angle)
    fitted = q.evaluate(du, dv)
    sag = float(fitted.max() - fitted.min())
    x0, y0 = frame.to_original(u0, v0)

    r_mean = 0.5 * (-1 / (2 * c[3]) - 1 / (2 * c[4]))
    try:
        u_v, v_v = q.vertex()
        sphere = fit_sphere(du, dv, ap.z, initial=(u_v, v_v, float(q.evaluate(u_v, v_v)) - r_mean,
                                                   r_mean)).radius
    except FitError:
        sphere = _NAN

    def profile(s: np.ndarray, across: np.ndarray) -> float:
        band = np.abs(across) <= 0.5 * p
        try:
            return fit_profile_circle(s[band], ap.z[band])[0]
        except FitError:
            return _NAN

    radii = []
    rho = np.hypot(du, dv)
    for f in config.xpander_stability_fractions:
        sel = rho <= f * radius_px * p
        try:
            qf = fit_quadric(du[sel], dv[sel], ap.z[sel])
            radii.append(0.5 * (-1 / (2 * qf.coeffs[3]) - 1 / (2 * qf.coeffs[4])))
        except FitError:
            continue
    stability = 100.0 * (max(radii) - min(radii)) / float(np.mean(radii)) if radii else _NAN

    residual_map = np.full(frame.canonical_shape, np.nan)
    u_all, v_all = frame.canonical_coordinates()
    ui = np.clip(np.rint(u_all[ap.rows, ap.cols]).astype(np.intp), 0, residual_map.shape[1] - 1)
    vi = np.clip(np.rint(v_all[ap.rows, ap.cols]).astype(np.intp), 0, residual_map.shape[0] - 1)
    residual_map[vi, ui] = q.residuals

    return XpanderResult(
        found=True,
        reason="",
        apex_x_px=float(x0),
        apex_y_px=float(y0),
        apex_u_px=float(u0),
        apex_v_px=float(v0),
        apex_z_um=float(q.evaluate(*q.vertex())),
        axis_offset_um=abs(u0 - regions.axis_u) * p,
        aperture_radius_um=radius_px * p,
        rx_um=float(-1 / (2 * c[3])),
        ry_um=float(-1 / (2 * c[4])),
        rx_ci95_um=float(1.96 * math.sqrt(cov[3, 3]) / (2 * c[3] ** 2)),
        ry_ci95_um=float(1.96 * math.sqrt(cov[4, 4]) / (2 * c[4] ** 2)),
        r1_um=float(-1 / lam[0]),
        r2_um=float(-1 / lam[1]),
        principal_angle_deg=angle,
        rms_um=q.rms,
        nrms_pct=100.0 * q.rms / sag if sag > 0 else _NAN,
        r_squared=q.r_squared,
        sag_um=sag,
        r_sphere_um=float(sphere),
        rx_profile_um=profile(du, dv),
        ry_profile_um=profile(dv, du),
        stability_pct=float(stability),
        n_points=q.n,
        residual_map=residual_map,
    )
