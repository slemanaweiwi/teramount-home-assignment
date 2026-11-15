"""Analysis configuration.

All tunable parameters live here, expressed in **physical units** (µm, µm²,
µm/µm slopes, degrees) rather than pixels, so the same values work for scans
of a different size or resolution. Use :meth:`Config.px` to convert a length to
pixels at the point of use.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Immutable set of analysis parameters (defaults suit the provided scans)."""

    # --- Units ---------------------------------------------------------------
    pixel_size_um: float = 0.252  # lateral size of one pixel [µm]
    z_scale: float = 1.0  # factor converting raw heights to µm

    # --- Switches ------------------------------------------------------------
    correct_tilt: bool = True  # subtract the fitted base plane (False: offset only)
    correct_rotation: bool = True  # measure and undo the in-plane rotation
    random_seed: int = 0  # seed for every random choice (RANSAC, Hough)

    # --- Segmentation surface ------------------------------------------------
    seg_median_px: int = 5  # median pre-filter size [px] (suppresses spike noise)
    seg_sigma_um: float = 1.0  # Gaussian smoothing for segmentation [µm]
    flat_slope_max: float = 0.25  # max slope of a "flat" pixel [µm/µm]

    # --- Tilt (RANSAC base plane) --------------------------------------------
    ransac_iterations: int = 300  # number of 3-point plane hypotheses
    ransac_inlier_um: float = 0.1  # inlier distance to a plane hypothesis [µm]
    ransac_sample_size: int = 50_000  # flat pixels sampled for RANSAC

    # --- Rotation (straight-edge estimator) ----------------------------------
    rotation_search_deg: float = 10.0  # search range around the axes [deg]
    rotation_canny_sigma_um: float = 0.5  # Canny smoothing [µm]
    rotation_canny_low: float = 0.5  # Canny low threshold [µm/px, Sobel units]
    rotation_canny_high: float = 1.5  # Canny high threshold [µm/px, Sobel units]
    rotation_min_line_um: float = 20.0  # shortest straight segment used [µm]
    rotation_line_gap_um: float = 0.75  # largest gap bridged inside a segment [µm]
    rotation_profile_half_px: int = 6  # half-width of the edge profile [px]
    rotation_max_line_rms_px: float = 0.25  # max straight-line fit residual [px]
    rotation_min_valid_fraction: float = 0.6  # min share of rows/cols with an edge hit

    # --- Pivot ---------------------------------------------------------------
    plane2_min_area_um2: float = 50.0  # smallest accepted plane-2 region [µm²]
    plane2_tie_um: float = 1.0  # plateaus this close to the highest compete [µm]
    plane1_min_area_um2: float = 200.0  # smallest accepted plane-1 region [µm²]
    plane1_min_drop_um: float = 5.0  # plane 1 lies at least this far below plane 2 [µm]
    ramp_search_um: float = 30.0  # ramp search distance around plane 2 [µm]
    ramp_slope_min: float = 0.3  # ramp slope lower bound [µm/µm]
    ramp_slope_max: float = 1.5  # ramp slope upper bound [µm/µm]
    plane_edge_margin_um: float = 0.5  # plane edge excluded from fits [µm]
    walk_max_um: float = 100.0  # max walk from plane 2 to plane 1 [µm]

    # --- Crosses -------------------------------------------------------------
    cross_polarity: str = "recessed"  # "recessed" (etched) or "raised"
    cross_min_depth_um: float = 0.6  # residual threshold for cross pixels [µm]
    cross_area_min_um2: float = 5.0  # cross area lower bound [µm²]
    cross_area_max_um2: float = 100.0  # cross area upper bound [µm²]
    cross_solidity_min: float = 0.75  # area / convex-hull area lower bound
    cross_solidity_max: float = 0.97  # upper bound (rejects square/round pits)
    cross_aspect_min: float = 0.7  # bounding-box width / height lower bound
    cross_aspect_max: float = 1.4  # bounding-box width / height upper bound

    # --- Xpander -------------------------------------------------------------
    xpander_smooth_um: float = 2.0  # smoothing for apex and boundary search [µm]
    xpander_search_um: float = 250.0  # search distance beyond plane 1 [µm]
    xpander_min_prominence_um: float = 0.5  # minimum dome prominence [µm]
    xpander_refine_um: float = 15.0  # apex refinement window half-size [µm]
    xpander_ray_count: int = 72  # rays cast to find the dome boundary
    xpander_ray_rise_um: float = 0.05  # rise past the valley that ends a ray [µm]
    xpander_steep_slope: float = 0.3  # slope that ends a ray (step edge) [µm/µm]
    xpander_aperture_fraction: float = 0.8  # aperture = fraction x shortest ray
    xpander_min_aperture_um: float = 20.0  # smaller apertures are rejected [µm]
    xpander_fit_iterations: int = 3  # fit / re-centre iterations
    xpander_stability_fractions: tuple[float, ...] = (0.5, 0.75, 1.0)  # aperture scan

    # --- Nominal spec --------------------------------------------------------
    # Estimated from the clean files of the provided datasets; override via CLI.
    nominal_pivot_step_um: float = 18.18  # nominal plane-2 minus plane-1 height [µm]
    tol_pivot_step_um: float = 0.30  # allowed deviation of the pivot step [µm]
    nominal_radius_um: float = 826.0  # nominal Xpander radius of curvature [µm]
    tol_radius_um: float = 30.0  # allowed deviation of Rx and Ry [µm]

    # --- Quality limits (geometric checks) -----------------------------------
    max_plane_rms_um: float = 0.15  # plane-fit residual above this = noisy plane [µm]
    # Dome fit residual above this = noisy surface [µm]. Absolute, not relative to
    # the sag: the sag shrinks with the aperture (e.g. a dome near the border), the
    # roughness of the surface does not. Clean domes: 7-9 nm; noisy ones: 150-230 nm.
    max_xpander_rms_um: float = 0.03
    max_cross_axis_offset_um: float = 1.0  # cross centre distance from the axis [µm]
    max_apex_axis_offset_um: float = 3.0  # Xpander apex distance from the axis [µm]
    max_plane_parallelism_deg: float = 0.5  # angle between plane 1 and plane 2 [deg]
    max_radius_asymmetry_pct: float = 5.0  # |Rx - Ry| / mean above this [%]

    # --- Statistics across a run ---------------------------------------------
    outlier_z: float = 3.5  # robust z-score marking a statistical outlier
    min_files_for_statistics: int = 5  # fewer successful files: no statistics

    def __post_init__(self) -> None:
        if not self.pixel_size_um > 0:
            raise ValueError(f"pixel_size_um must be > 0, got {self.pixel_size_um}")
        if self.z_scale == 0:
            raise ValueError("z_scale must be non-zero")
        if not 0 < self.xpander_aperture_fraction <= 1:
            raise ValueError(
                f"xpander_aperture_fraction must be in (0, 1], got {self.xpander_aperture_fraction}"
            )
        if self.cross_polarity not in ("recessed", "raised"):
            raise ValueError(
                f"cross_polarity must be 'recessed' or 'raised', got {self.cross_polarity!r}"
            )

    def px(self, um: float) -> float:
        """Convert a lateral length from µm to pixels."""
        return um / self.pixel_size_um

    def um(self, px: float) -> float:
        """Convert a lateral length from pixels to µm."""
        return px * self.pixel_size_um
