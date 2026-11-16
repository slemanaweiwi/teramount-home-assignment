"""Per-scan diagnostic figure: what was detected, where, and how well it fits.

Uses matplotlib's object-oriented ``Figure`` directly (no pyplot), so it needs
no display, keeps no global state and is safe in batch runs.

Panels: (1) the whole leveled scan with every detected element and the edges
used for the rotation estimate; (2) the Pivot close-up; (3) the Xpander
close-up with the fitted aperture; (4) the Xpander fit residuals; (5) height
profiles through the apex with the fitted curves; (6) the key numbers.
"""

from __future__ import annotations

import math
import textwrap
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Circle

from .config import Config
from .results import FaultReport, ScanResult

_DPI = 90


def save_scan_figure(result: ScanResult, path: Path, config: Config) -> None:
    """Draw the diagnostic figure of one analysed scan and save it as PNG."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dbg = result.debug
    if dbg is None or dbg.regions is None or dbg.z_canonical is None or result.frame is None:
        fig = _failure_figure(result)
    else:
        fig = _full_figure(result, config)
    fig.savefig(path, dpi=_DPI)


def _limits(z: np.ndarray) -> tuple[float, float]:
    lo, hi = np.nanpercentile(z, [1.0, 99.7])
    return float(lo), float(hi)


def _failure_figure(result: ScanResult) -> Figure:
    fig = Figure(figsize=(7, 9), layout="constrained")
    ax = fig.add_subplot(1, 1, 1)
    if result.debug is not None:
        z = result.debug.z_leveled
        ax.imshow(z, cmap="viridis", vmin=_limits(z)[0], vmax=_limits(z)[1])
    else:
        ax.axis("off")
    message = textwrap.fill(result.error or "analysis failed", 60)
    ax.set_title(f"{result.file}: {result.status}\n{message}", fontsize=10, color="darkred")
    return fig


def _full_figure(result: ScanResult, config: Config) -> Figure:
    p = config.pixel_size_um
    dbg, frame, reg, xp = result.debug, result.frame, result.debug.regions, result.xpander
    fig = Figure(figsize=(20, 11), layout="constrained")
    gs = fig.add_gridspec(2, 4, width_ratios=[0.9, 1.3, 1.3, 1.15])
    ax_full = fig.add_subplot(gs[:, 0])
    ax_pivot, ax_xp = fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[0, 2])
    ax_res, ax_prof = fig.add_subplot(gs[1, 1]), fig.add_subplot(gs[1, 2])
    ax_text = fig.add_subplot(gs[:, 3])
    crosses = [c for c in (result.cross1, result.cross2) if c is not None and c.found]
    xp_found = xp is not None and xp.found

    # (1) whole scan, original frame
    z = dbg.z_leveled
    ax_full.imshow(z, cmap="viridis", vmin=_limits(z)[0], vmax=_limits(z)[1],
                   interpolation="nearest")
    for mask, color in ((reg.plane1, "deepskyblue"), (reg.plane2, "orange")):
        ax_full.contour(frame.pull_back(mask), levels=[0.5], colors=[color], linewidths=0.8)
    for c in crosses:
        ax_full.add_patch(Circle((c.x_px, c.y_px), 30, fill=False, ec="red", lw=1.5))
    if xp_found:
        ax_full.add_patch(Circle((xp.apex_x_px, xp.apex_y_px), xp.aperture_radius_um / p,
                                 fill=False, ec="white", ls="--", lw=1.2))
    if result.rotation is not None:
        for ln in result.rotation.lines:
            ax_full.plot([ln.x0, ln.x1], [ln.y0, ln.y1], color="cyan", lw=0.8)
    ax_full.set_title(f"{result.file}: leveled scan\nedges used for rotation (cyan)", fontsize=10)

    # (2) Pivot close-up, canonical frame
    zc = dbg.z_canonical
    rr, cc = np.nonzero(reg.plane1 | reg.plane2)
    pad = int(config.px(10.0))
    r0, r1 = max(rr.min() - pad, 0), min(rr.max() + pad, zc.shape[0])
    c0, c1 = max(cc.min() - pad, 0), min(cc.max() + pad, zc.shape[1])
    crop = zc[r0:r1, c0:c1]
    extent = (c0 - 0.5, c1 - 0.5, r1 - 0.5, r0 - 0.5)
    ax_pivot.imshow(crop, cmap="viridis", vmin=_limits(crop)[0], vmax=_limits(crop)[1],
                    extent=extent)
    us, vs = np.arange(c0, c1), np.arange(r0, r1)
    for mask, color in ((reg.plane1, "deepskyblue"), (reg.plane2, "orange")):
        ax_pivot.contour(us, vs, mask[r0:r1, c0:c1], levels=[0.5], colors=[color],
                         linewidths=1.0)
    for c in crosses:
        if c.mask is not None:
            ax_pivot.contour(us, vs, c.mask[r0:r1, c0:c1], levels=[0.5], colors=["red"],
                             linewidths=0.8)
        ax_pivot.add_patch(Circle((c.u_px, c.v_px), 20, fill=False, ec="red", lw=1.5))
        ax_pivot.plot(c.u_px, c.v_px, "r+", ms=8)
    ax_pivot.set_title("Pivot (rotation-corrected): plane 1 blue, plane 2 orange, "
                       "crosses red", fontsize=10)

    # (3)-(5) Xpander
    if xp_found:
        _xpander_panels(ax_xp, ax_res, ax_prof, fig, zc, xp, p)
    else:
        for ax in (ax_xp, ax_res, ax_prof):
            ax.axis("off")
        reason = xp.reason if xp is not None else "not analysed"
        ax_xp.set_title(f"Xpander not measured:\n{textwrap.fill(reason, 50)}", fontsize=10,
                        color="darkred")

    # (6) numbers
    ax_text.axis("off")
    ax_text.text(0.0, 1.0, _summary_text(result, config), va="top", ha="left",
                 family="monospace", fontsize=9, transform=ax_text.transAxes)
    return fig


def _xpander_panels(ax_xp, ax_res, ax_prof, fig: Figure, zc: np.ndarray, xp, p: float) -> None:
    radius = xp.aperture_radius_um / p
    half = int(1.3 * radius)
    u0, v0 = int(round(xp.apex_u_px)), int(round(xp.apex_v_px))
    r0, r1 = max(v0 - half, 0), min(v0 + half, zc.shape[0])
    c0, c1 = max(u0 - half, 0), min(u0 + half, zc.shape[1])
    extent = (c0 - 0.5, c1 - 0.5, r1 - 0.5, r0 - 0.5)
    crop = zc[r0:r1, c0:c1]
    ax_xp.imshow(crop, cmap="viridis", vmin=_limits(crop)[0], vmax=_limits(crop)[1],
                 extent=extent)
    ax_xp.add_patch(Circle((xp.apex_u_px, xp.apex_v_px), radius, fill=False, ec="white",
                           ls="--", lw=1.2))
    ax_xp.plot(xp.apex_u_px, xp.apex_v_px, "w+", ms=10)
    ax_xp.set_title(f"Xpander: aperture r = {xp.aperture_radius_um:.1f} µm", fontsize=10)

    if xp.residual_map is not None:
        lim_nm = 3000.0 * xp.rms_um
        img = ax_res.imshow(xp.residual_map[r0:r1, c0:c1] * 1000.0, cmap="RdBu_r",
                            vmin=-lim_nm, vmax=lim_nm, extent=extent)
        fig.colorbar(img, ax=ax_res, label="fit residual [nm]", shrink=0.85)
    ax_res.set_title(f"fit residual: RMS {xp.rms_um * 1000:.1f} nm, "
                     f"nRMS {xp.nrms_pct:.2f} %, R² {xp.r_squared:.4f}", fontsize=10)

    n = int(radius)
    us = np.arange(max(u0 - n, 0), min(u0 + n + 1, zc.shape[1]))
    vs = np.arange(max(v0 - n, 0), min(v0 + n + 1, zc.shape[0]))
    s_u, s_v = (us - xp.apex_u_px) * p, (vs - xp.apex_v_px) * p
    ax_prof.plot(s_u, zc[v0, us], ".", ms=2, color="tab:blue", label="data along x")
    ax_prof.plot(s_u, xp.apex_z_um - s_u**2 / (2 * xp.rx_um), color="tab:blue",
                 label=f"fit, Rx = {xp.rx_um:.1f} µm")
    ax_prof.plot(s_v, zc[vs, u0], ".", ms=2, color="tab:orange", label="data along y")
    ax_prof.plot(s_v, xp.apex_z_um - s_v**2 / (2 * xp.ry_um), color="tab:orange",
                 label=f"fit, Ry = {xp.ry_um:.1f} µm")
    ax_prof.set_xlabel("distance from apex [µm]")
    ax_prof.set_ylabel("height above base [µm]")
    ax_prof.legend(fontsize=8)
    ax_prof.set_title("profiles through the apex", fontsize=10)


def _summary_text(result: ScanResult, config: Config) -> str:
    m = result.metrics(config)
    faults = result.faults or FaultReport()

    def f(key: str, fmt: str, scale: float = 1.0) -> str:
        v = m[key]
        return format(v * scale, fmt) if math.isfinite(v) else "-"

    lines = [
        f"{result.file}   status: {result.status}",
        *(textwrap.wrap(f"note: {result.error}", 46) if result.error else []),
        "",
        "TILT / ROTATION",
        f" tilt x   {f('tilt_x_deg', '+.4f')} deg",
        f" tilt y   {f('tilt_y_deg', '+.4f')} deg",
        f" total    {f('tilt_total_deg', '.4f')} deg",
        f" rotation {f('rotation_deg', '+.3f')} +/- {f('rotation_se_deg', '.3f')} deg"
        f" ({f('rotation_lines', '.0f')} edges)",
        f" scan-line streaks {f('streak_level_um', '.1f', 1000)} nm",
        "",
        "PIVOT",
        f" height diff   {f('pivot_height_diff_um', '.3f')} µm",
        f" with crosses  {f('pivot_height_diff_with_crosses_um', '.3f')} µm",
        f" plane RMS     {f('plane1_rms_um', '.0f', 1000)} / {f('plane2_rms_um', '.0f', 1000)} nm",
        f" parallelism   {f('plane_parallelism_deg', '.3f')} deg",
    ]
    for n in (1, 2):
        lines += [f" cross {n}  x {f(f'cross{n}_x_px', '.2f')}  y {f(f'cross{n}_y_px', '.2f')} px",
                  f"          ({f(f'cross{n}_x_um', '.2f')}, {f(f'cross{n}_y_um', '.2f')}) µm"]
    lines += [
        "",
        "XPANDER",
        f" Rx  {f('xpander_rx_um', '.1f')} +/- {f('xpander_rx_ci95_um', '.2f')} µm",
        f" Ry  {f('xpander_ry_um', '.1f')} +/- {f('xpander_ry_ci95_um', '.2f')} µm",
        f" R1/R2  {f('xpander_r1_um', '.1f')} / {f('xpander_r2_um', '.1f')} µm"
        f" @ {f('xpander_principal_angle_deg', '.0f')} deg",
        f" sphere R   {f('xpander_r_sphere_um', '.1f')} µm",
        f" profile Rx/Ry  {f('xpander_rx_profile_um', '.1f')} /"
        f" {f('xpander_ry_profile_um', '.1f')}",
        f" RMS {f('xpander_rms_um', '.1f', 1000)} nm  nRMS {f('xpander_nrms_pct', '.2f')} %",
        f" outlier pixels dropped {f('xpander_outlier_pct', '.2f')} %",
        f" R²  {f('xpander_r_squared', '.4f')}",
        f" stability over apertures {f('xpander_stability_pct', '.2f')} %",
        "",
        "FLAGS",
        *textwrap.wrap(" geometric: " + (", ".join(faults.geometric) or "none"), 46),
        *textwrap.wrap(" nominal:   " + (", ".join(faults.nominal) or "none"), 46),
        *(textwrap.wrap(" warnings:  " + ", ".join(result.warnings), 46)
          if result.warnings else []),
        " statistical: see the CSV (needs the whole run)",
    ]
    return "\n".join(lines)
