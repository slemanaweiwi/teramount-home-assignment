"""Shared helpers that run the analysis chain up to one stage (tests only).

Each helper uses the *known* rotation ``phi`` instead of estimating it, so a
test exercises only its own stage.
"""

from __future__ import annotations

import dataclasses

import numpy as np

from teramount_analysis.config import Config
from teramount_analysis.crosses import CrossResult, find_cross
from teramount_analysis.frame import Frame
from teramount_analysis.pivot import PivotResult, measure_pivot, segment_pivot
from teramount_analysis.results import ScanResult
from teramount_analysis.rotation import RotationResult
from teramount_analysis.surface import segmentation_surface
from teramount_analysis.tilt import TiltResult, fit_base_plane, remove_tilt
from teramount_analysis.xpander import XpanderResult, measure_xpander


def prepare(z: np.ndarray, phi: float, config: Config | None = None
            ) -> tuple[np.ndarray, Frame, np.ndarray, np.ndarray]:
    """Level the scan and build its canonical image and segmentation surface."""
    config = config or Config()
    z_leveled = remove_tilt(z, fit_base_plane(z, config), config)
    frame = Frame(z.shape, phi, 0)
    z_canonical = frame.canonical_image(z_leveled)
    return z_leveled, frame, z_canonical, segmentation_surface(z_canonical, config)


def seg(z: np.ndarray) -> np.ndarray:
    """Segmentation surface of an unrotated scan."""
    return prepare(z, 0.0)[3]


def run_crosses(z: np.ndarray, phi: float, config: Config | None = None
                ) -> tuple[CrossResult, CrossResult]:
    """Crosses on plane 1 and plane 2, using the known rotation ``phi``."""
    config = config or Config()
    z_leveled, frame, z_canonical, z_seg = prepare(z, phi, config)
    reg = segment_pivot(z_seg, config)
    return (find_cross(z_leveled, frame, z_canonical, reg.plane1, reg.axis_u, config),
            find_cross(z_leveled, frame, z_canonical, reg.plane2, reg.axis_u, config))


def run_pivot(z: np.ndarray, phi: float, config: Config | None = None,
              use_cross_masks: bool = True) -> PivotResult:
    """Pivot height measurement, using the known rotation ``phi``."""
    config = config or Config()
    z_leveled, frame, z_canonical, z_seg = prepare(z, phi, config)
    reg = segment_pivot(z_seg, config)
    c1 = find_cross(z_leveled, frame, z_canonical, reg.plane1, reg.axis_u, config)
    c2 = find_cross(z_leveled, frame, z_canonical, reg.plane2, reg.axis_u, config)
    masks = (c1.mask, c2.mask) if use_cross_masks else (None, None)
    return measure_pivot(z_leveled, frame, reg, *masks, config)


def fake_cross(offset_um: float = 0.2) -> CrossResult:
    """A found cross with plausible values (no image needed)."""
    return CrossResult(True, 500.0, 770.0, 500.5, 770.2, 1.75, 19.0, 0.9, offset_um, None)


def fake_xpander(rx: float = 826.0, ry: float = 824.0, nrms: float = 0.6,
                 offset: float = 0.5) -> XpanderResult:
    """A found Xpander with plausible values (no image needed)."""
    return dataclasses.replace(
        XpanderResult.not_found("unused"), found=True, reason="", apex_x_px=512.0,
        apex_y_px=385.0, apex_u_px=512.0, apex_v_px=385.0, apex_z_um=12.4,
        axis_offset_um=offset, aperture_radius_um=49.0, rx_um=rx, ry_um=ry, rx_ci95_um=0.1,
        ry_ci95_um=0.1, r1_um=min(rx, ry), r2_um=max(rx, ry), principal_angle_deg=0.0,
        rms_um=nrms / 100 * 1.45, nrms_pct=nrms, r_squared=0.9996, sag_um=1.45,
        r_sphere_um=0.5 * (rx + ry), rx_profile_um=rx, ry_profile_um=ry, stability_pct=1.0,
        outlier_pct=0.0, n_points=120_000)


def fake_result(**overrides) -> ScanResult:
    """A complete, clean ScanResult built from plausible values."""
    result = ScanResult(
        file="x.npy", status="ok", error="",
        tilt=TiltResult(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.012, 0.65),
        rotation=RotationResult(0.0, 0.01, 30, ()),
        frame=Frame((100, 100), 0.0),
        pivot=PivotResult(18.18, 18.0, 12.9, 31.08, 0.045, 0.025, 0.05),
        cross1=fake_cross(), cross2=fake_cross(), xpander=fake_xpander(),
    )
    return dataclasses.replace(result, **overrides)


def run_xpander(z: np.ndarray, phi: float, config: Config | None = None) -> XpanderResult:
    """Xpander measurement, using the known rotation ``phi``."""
    config = config or Config()
    z_leveled, frame, z_canonical, z_seg = prepare(z, phi, config)
    reg = segment_pivot(z_seg, config)
    return measure_xpander(z_leveled, frame, z_canonical, reg, config)
