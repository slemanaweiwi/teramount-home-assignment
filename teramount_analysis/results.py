"""Per-scan result container and the flat metric table built from it.

:data:`METRIC_COLUMNS` is the single source of truth for the measured columns
of the results CSV; :meth:`ScanResult.metrics` fills exactly those keys.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .config import Config
from .crosses import CrossResult
from .frame import Frame
from .pivot import PivotRegions, PivotResult
from .rotation import RotationResult
from .tilt import TiltResult
from .xpander import XpanderResult

_CROSS_FIELDS = ("x_px", "y_px", "x_um", "y_um", "u_px", "v_px", "depth_um", "axis_offset_um")

METRIC_COLUMNS: tuple[str, ...] = (
    "tilt_x_deg", "tilt_y_deg", "tilt_total_deg", "tilt_azimuth_deg", "base_rms_um",
    "rotation_deg", "rotation_se_deg", "rotation_lines",
    "pivot_height_diff_um", "pivot_height_diff_with_crosses_um", "plane1_rms_um",
    "plane2_rms_um", "plane_parallelism_deg",
    *(f"cross{n}_{f}" for n in (1, 2) for f in _CROSS_FIELDS),
    "xpander_apex_x_px", "xpander_apex_y_px", "xpander_apex_u_px", "xpander_apex_v_px",
    "xpander_apex_z_um", "xpander_apex_axis_offset_um", "xpander_rx_um", "xpander_ry_um",
    "xpander_rx_ci95_um",
    "xpander_ry_ci95_um", "xpander_r1_um", "xpander_r2_um", "xpander_principal_angle_deg",
    "xpander_rms_um", "xpander_nrms_pct", "xpander_r_squared", "xpander_sag_um",
    "xpander_aperture_radius_um", "xpander_r_sphere_um", "xpander_rx_profile_um",
    "xpander_ry_profile_um", "xpander_stability_pct",
)


@dataclass(frozen=True)
class FaultReport:
    """Fault flags in three separate categories.

    A statistical anomaly alone does not make a scan faulty: being unusual
    compared with the other scans of a run is not the same as being defective,
    and a defect shared by every scan would not look unusual at all.
    """

    geometric: tuple[str, ...] = ()  # structure violates its expected geometry
    nominal: tuple[str, ...] = ()  # measurement outside the nominal spec tolerance
    statistical: tuple[str, ...] = ()  # outlier relative to the other scans of the run

    @property
    def faulty(self) -> bool:
        """True when a geometric or nominal check failed."""
        return bool(self.geometric or self.nominal)


@dataclass(eq=False)
class ScanDebug:
    """Large intermediate arrays kept only until the scan's figure is drawn."""

    z_leveled: np.ndarray
    z_canonical: np.ndarray | None = None
    regions: PivotRegions | None = None


@dataclass(eq=False)
class ScanResult:
    """Everything measured for one scan."""

    file: str
    status: str = "failed"  # "ok" | "partial" | "failed"
    error: str = ""  # reason for a failed or partial analysis
    # Limits of the analysis that are not chip defects, e.g. "rotation_not_measured"
    # (the scan was then analysed as unrotated). They never make a scan faulty.
    warnings: tuple[str, ...] = ()
    tilt: TiltResult | None = None
    rotation: RotationResult | None = None  # None when not measured
    frame: Frame | None = None
    pivot: PivotResult | None = None
    cross1: CrossResult | None = None
    cross2: CrossResult | None = None
    xpander: XpanderResult | None = None
    missing: tuple[str, ...] = ()  # elements that could not be located ("plane2", "plane1")
    faults: FaultReport | None = None
    debug: ScanDebug | None = field(default=None, repr=False)

    def metrics(self, config: Config) -> dict[str, float]:
        """Flat ``{column: value}`` map with every key of METRIC_COLUMNS (NaN if unknown)."""
        p = config.pixel_size_um
        m: dict[str, float] = dict.fromkeys(METRIC_COLUMNS, float("nan"))
        if self.tilt is not None:
            t = self.tilt
            m.update(tilt_x_deg=t.tilt_x_deg, tilt_y_deg=t.tilt_y_deg,
                     tilt_total_deg=t.tilt_total_deg, tilt_azimuth_deg=t.tilt_azimuth_deg,
                     base_rms_um=t.base_rms_um)
        if self.frame is not None:
            m["rotation_deg"] = self.frame.rotation_deg
        if self.rotation is not None:
            m["rotation_se_deg"] = self.rotation.se_deg
            m["rotation_lines"] = float(self.rotation.n_lines)
        if self.pivot is not None:
            pv = self.pivot
            m.update(pivot_height_diff_um=pv.height_diff_um,
                     pivot_height_diff_with_crosses_um=pv.height_diff_with_crosses_um,
                     plane1_rms_um=pv.plane1_rms_um, plane2_rms_um=pv.plane2_rms_um,
                     plane_parallelism_deg=pv.parallelism_deg)
        for n, c in ((1, self.cross1), (2, self.cross2)):
            if c is not None and c.found:
                values = (c.x_px, c.y_px, c.x_px * p, c.y_px * p, c.u_px, c.v_px, c.depth_um,
                          c.axis_offset_um)
                m.update({f"cross{n}_{f}": v for f, v in zip(_CROSS_FIELDS, values, strict=True)})
        x = self.xpander
        if x is not None and x.found:
            m.update(
                xpander_apex_x_px=x.apex_x_px, xpander_apex_y_px=x.apex_y_px,
                xpander_apex_u_px=x.apex_u_px, xpander_apex_v_px=x.apex_v_px,
                xpander_apex_z_um=x.apex_z_um, xpander_apex_axis_offset_um=x.axis_offset_um,
                xpander_rx_um=x.rx_um,
                xpander_ry_um=x.ry_um, xpander_rx_ci95_um=x.rx_ci95_um,
                xpander_ry_ci95_um=x.ry_ci95_um, xpander_r1_um=x.r1_um, xpander_r2_um=x.r2_um,
                xpander_principal_angle_deg=x.principal_angle_deg, xpander_rms_um=x.rms_um,
                xpander_nrms_pct=x.nrms_pct, xpander_r_squared=x.r_squared,
                xpander_sag_um=x.sag_um, xpander_aperture_radius_um=x.aperture_radius_um,
                xpander_r_sphere_um=x.r_sphere_um, xpander_rx_profile_um=x.rx_profile_um,
                xpander_ry_profile_um=x.ry_profile_um, xpander_stability_pct=x.stability_pct,
            )
        return m
