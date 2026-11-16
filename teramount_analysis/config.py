"""Analysis configuration.

All tunable parameters live here. Every size — of a feature, a search region
or a filter — is in **physical units** (µm, µm², µm/µm slopes, degrees), so
the same values work for scans of a different size or resolution: only
``pixel_size_um`` changes. Lengths are converted to pixels at the point of use
(:meth:`Config.px`, :meth:`Config.whole_px`, :meth:`Config.odd_px`).

The one setting in pixels, ``rotation_max_line_rms_px``, is a sub-pixel
precision limit, which is a property of the sampling, not of the chip. A few
internal constants are pixel counts for the same reason (the Hough vote
threshold, minimum pixel counts for a fit, 1-px de-noising before an argmax).
Defaults given in µm that look odd (0.756, 1.26) are whole pixel counts at
the provided 0.252 µm/px.
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
    correct_streaks: bool = True  # remove scan-line streaks when clearly present

    # --- Segmentation surface ------------------------------------------------
    seg_median_um: float = 1.26  # median pre-filter size [µm] (spike noise; 5 px)
    seg_sigma_um: float = 1.0  # Gaussian smoothing for segmentation [µm]
    flat_slope_max: float = 0.25  # max slope of a "flat" pixel [µm/µm]

    # --- Scan-line streaks ---------------------------------------------------
    streak_min_um: float = 0.01  # streaks below this are left alone (clean scans: <= 3 nm) [µm]
    streak_noise_factor: float = 4.0  # ...and below this many times the noise floor
    streak_trend_um: float = 2.0  # sigma of the running mean that keeps the surface trend [µm]

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
    rotation_profile_half_um: float = 1.5  # half-width of the edge profile [µm] (>= 6 px)
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
    # Mean resultant length of the downhill unit vectors near plane 2 (1 = all
    # parallel, 0 = no preferred direction). Below it the ramp direction, and so
    # the orientation, is ambiguous. Provided scans: 0.23-0.26 (other sloped
    # pixels dilute it); a plateau with ramps on all sides: about 0.
    ramp_min_resultant: float = 0.1
    plane_edge_margin_um: float = 0.5  # plane edge excluded from fits [µm]
    walk_max_um: float = 100.0  # max walk from plane 2 to plane 1 [µm]

    # --- Crosses -------------------------------------------------------------
    cross_polarity: str = "recessed"  # "recessed" (etched) or "raised"
    cross_min_depth_um: float = 0.6  # residual threshold for cross pixels [µm]
    cross_median_um: float = 0.756  # median de-noising before the threshold [µm] (3 px)
    cross_sigma_um: float = 0.252  # Gaussian de-noising before the threshold [µm] (1 px)
    cross_margin_um: float = 0.5  # cross outline grown by this before plane fits [µm]
    # In the depth-weighted centroid no pixel counts for more than the cross depth plus
    # max(this, 5 x the floor's noise), so a deep spike barely pulls the centre. Real
    # cross floors reach 0.66 µm below their median depth (1.4 µm on a noisy plane) [µm].
    cross_depth_tol_um: float = 1.0
    cross_area_min_um2: float = 5.0  # cross area lower bound [µm²]
    cross_area_max_um2: float = 100.0  # cross area upper bound [µm²]
    cross_solidity_min: float = 0.75  # area / convex-hull area lower bound
    cross_solidity_max: float = 0.97  # upper bound (rejects square/round pits)
    cross_aspect_min: float = 0.7  # bounding-box width / height lower bound
    cross_aspect_max: float = 1.4  # bounding-box width / height upper bound

    # --- Xpander -------------------------------------------------------------
    xpander_smooth_um: float = 2.0  # smoothing for apex and boundary search [µm]
    # Dust particles narrower than this are removed (grey opening) from the copy
    # used to find the apex and the dome boundary; the fit then drops them as outliers.
    xpander_particle_um: float = 10.0
    # The dome search covers the scan down to this far below the top of plane 1 [µm].
    xpander_rows_below_plane1_um: float = 20.0
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
    # Outlier pixels (spikes, dust, local features) are dropped from the dome and Pivot
    # plane fits when their residual exceeds max(clip_sigma x robust sigma, clip_min). The
    # floor lies above the residual pattern of a clean dome (about +-40 nm), so clean data
    # loses nothing, and the sigma term scales with real roughness, so a noisy surface is
    # never "cleaned".
    outlier_clip_sigma: float = 5.0  # [robust standard deviations]
    outlier_clip_min_um: float = 0.1  # [µm]
    xpander_max_outlier_pct: float = 1.0  # more dropped pixels than this: warning [%]
    # A compact cluster of dropped pixels at least this large is a local feature (dust or
    # a defect: a bump or a pit), reported as a fault of its element; it is excluded from
    # the fit together with a ring of feature_margin_um around it [µm², µm].
    feature_min_um2: float = 1.0
    feature_margin_um: float = 3.0

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

    def whole_px(self, um: float, minimum: int = 1) -> int:
        """A length in whole pixels (rounded), at least ``minimum``."""
        return max(minimum, int(round(self.px(um))))

    def odd_px(self, um: float) -> int:
        """A filter window in pixels: the nearest odd count (1 = no filtering)."""
        return max(1, 2 * int(round((self.px(um) - 1) / 2)) + 1)
