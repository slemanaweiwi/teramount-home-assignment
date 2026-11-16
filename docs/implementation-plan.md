# Teramount Topography Analysis — Implementation Plan

> **Historical document:** the 17-task build plan, followed test-first. The code,
> `README.md` and `ANSWERS.md` describe the final result.

**Goal:** A tested Python package + one-command CLI that labels the Pivot and Xpander in 3D topography scans, corrects tilt/rotation, extracts all requested parameters with quality metrics and fault flags, and writes a CSV, per-scan diagnostic figures, and the written answers.

**Architecture:** A pipeline of small pure-function modules: level (tilt) → estimate fine rotation → build a canonical coordinate `Frame` → segment the Pivot (which also fixes coarse orientation) → crosses → Pivot heights → Xpander fit → fault checks → CSV/figures. Masks are found on a resampled ("canonical") image, but every measurement uses the original, non-interpolated pixels with their canonical coordinates.

**Tech Stack:** Python ≥ 3.10 (developed on 3.14 via the `py` launcher), numpy, scipy, scikit-image, matplotlib; pytest + ruff for development.

**Spec:** `docs/design.md` (approved). Read it before starting; this plan argues from it.

## Global Constraints

- Code must run on Python 3.10+: every module starts with `from __future__ import annotations`; no 3.11+-only APIs.
- Runtime dependencies are exactly: numpy, scipy, scikit-image, matplotlib. Dev: pytest, ruff. No pandas, no OpenCV.
- No hard-coded pixel coordinates or file-specific logic. Every tunable lives in `Config` in physical units (µm, µm², µm/µm, degrees) and is converted with `config.px(...)`.
- Pixel size default 0.252 µm; heights assumed µm (`z_scale` multiplies raw values).
- Coordinate convention everywhere: `x` = column, `y` = row, origin = centre of the top-left pixel; µm = px × pixel size. Canonical (corrected) coordinates are `u`, `v` (same convention, in the canonical image).
- `rotation_deg` sign: positive = counter-clockwise as displayed with origin at the top-left — identical to the `angle` that `scipy.ndimage.rotate(unrotated, angle, reshape=False)` applies (verified in exploration).
- Never measure interpolated data: resampled images are used only to find masks/locations; plane fits, cross centres and the Xpander fit use original pixels.
- One scan failing never stops a run: expected failures raise subclasses of `AnalysisError` and become `status`/`error` in the CSV.
- `logging` (module-level loggers) — no `print` outside the CLI summary.
- Deterministic: all randomness from `numpy.random.default_rng(config.random_seed)`.
- Type hints and NumPy-style docstrings on every public function/class; `py -m ruff check .` clean.
- Not committed: `15_files_task_*/`, `*.docx`, `.claude/`, caches. Commit after every task; commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Xpander cut by the image border** (channel near the top edge) — expect Pivot results and `xpander_not_found` with a reason, never a fit on half a dome. Test: Task 10 `test_dome_cut_by_border_is_not_found`.
2. **Large global height offset** (e.g. every height +100 µm, different instrument zero) — all results unchanged. Test: Task 12 `test_global_offset_does_not_change_results`.
3. **Invalid pixels (NaN dropouts)** typical of real profilometers — no crash, results within tolerance. Tests: Task 4 `test_tilt_ignores_nan_pixels`, Task 12 `test_nan_dropouts_are_tolerated`.
4. **Two complete channels visible** (scan shifted by half a pitch) — the channel closest to the image centre is analysed, deterministically. Test: Task 7 `test_two_channels_picks_most_central`.
5. **Degenerate input** (constant image, tiny image, 1-D array) — clean `failed` row with a message. Tests: Task 1 `test_load_rejects_non_2d`, Task 12 `test_constant_scan_fails_cleanly`.

## Data facts established during exploration (do not re-derive)

- Each scan: `float64`, 2840 × 1000, no NaNs; heights in µm. Layout top→bottom: supporting band; a row of Xpander domes with pitch 126 µm (neighbours meet at gentle valleys, not steep edges); the Pivot below the central dome; a large flat base containing an isolated 23.5 µm block with a cross (ignore it).
- Leveled heights (base = 0): tooth ≈ 11.0, plane 1 ≈ 12.9, plane 2 ≈ 31.0, dome apex ≈ 12.4 (sag ≈ 2.7 µm). Pivot height difference ≈ 18.13–18.25 µm on clean files.
- Crosses are **recessed** plus signs ≈ 6.5 µm across, 1.6–1.75 µm deep, area 17.6–20.1 µm², solidity 0.88–0.93, bbox aspect 1.0–1.2. Raised square pads (+2 µm) sit beside plane 1.
- **Task 2 file i = Task 1 file i rotated about the array centre** (scipy convention) **plus a tilt plane** (correlation 1.000). Applied rotations: `[1.0, 0, -0.25, 0.5, -1.0, 0.75, -0.75, 0.25, -0.5, 1.0, 0, -0.25, 0.5, -1.0, 0.75]` (index = file number). Rotated-in corners hold a constant ≈ base level. Task 2 tilts ≤ ~0.12°; Task 1 ≈ 0.004°.
- Planted faults (white noise on whole elements): T1-6 Pivot (σ ≈ 0.6–0.7 µm) and Xpander (fit RMS ≈ 231 nm); T2-3 Xpander (≈ 123 nm); T2-13 Xpander (≈ 123 nm, grid-like pattern); T2-7 Pivot (≈ 0.33 µm). T2-6 is clean.
- Prototype results to reproduce: paraboloid fit RMS 7–9 nm on clean domes, R ≈ 812–844 µm, auto aperture ≈ 49 µm radius (0.8 × distance to the valley); rotation via edge-line mid-level crossing matches applied angles within 0.018°.

## File Structure

```
.gitignore, pyproject.toml, requirements.txt, requirements-dev.txt, run.py
README.md, ANSWERS.md, AI_USAGE.md
teramount_analysis/
  __init__.py     public API: Config, analyse_scan, analyse_file, analyse_dataset, ScanResult
  errors.py       AnalysisError hierarchy
  config.py       Config dataclass (all tunables, physical units)
  io.py           discover & load scans
  surface.py      NaN filling, smoothing, slope, flatness mask
  fitting.py      plane (LS, robust, RANSAC), quadric, sphere, profile-circle fits
  tilt.py         base-plane fit, tilt angles, leveling
  frame.py        Frame: original <-> canonical coordinates, canonical image, mask pull-back
  rotation.py     fine rotation from straight edges
  pivot.py        plane 2 / ramp / orientation / plane 1 segmentation + height difference
  crosses.py      cross detection and centres
  xpander.py      apex, aperture, surface fit, curvature, figures of merit
  results.py      ScanResult, FaultReport, metrics() -> flat dict (single source of CSV column names)
  faults.py       geometric / nominal / statistical checks
  pipeline.py     analyse_scan / analyse_file / analyse_dataset
  report.py       CSV writer, console summary
  figures.py      per-scan diagnostic figure
  cli.py          argparse entry point
tests/
  conftest.py, synthetic.py, test_*.py (one per module), test_real_data.py
results/          generated CSVs + figures (committed at the end)
docs/design.md, docs/implementation-plan.md
```

Builder calls refining the design (record in README "Design notes"): result dataclasses live next to the module that produces them (no central `models.py`); `leveling.py` is split into `tilt.py`, `rotation.py`, `frame.py`; shared fits live in `fitting.py`; pandas dropped (csv module suffices); bootstrap and Hough-as-primary dropped per design §12.

---

### Task 1: Repository scaffold, config, errors, scan loading

**Files:**
- Create: `.gitignore`, `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `teramount_analysis/__init__.py`, `teramount_analysis/errors.py`, `teramount_analysis/config.py`, `teramount_analysis/io.py`, `tests/conftest.py`, `tests/test_io.py`, `tests/test_config.py`

**Interfaces:**
- Produces:
  - `errors.AnalysisError(Exception)`; subclasses `ScanLoadError`, `ElementNotFoundError`, `RotationError`, `FitError`.
  - `config.Config` — frozen dataclass, fields and defaults exactly as listed in Step 3; methods `px(um: float) -> float` (µm→px) and `um(px: float) -> float`; `__post_init__` raises `ValueError` for `pixel_size_um <= 0`, `z_scale == 0`, `xpander_aperture_fraction` not in (0, 1].
  - `io.discover_scans(path: Path) -> list[Path]` — a `.npy` file → `[path]`; a folder → all `*.npy` sorted naturally (`2.npy` before `10.npy`); raises `FileNotFoundError` (missing) / `ScanLoadError` (no `.npy`).
  - `io.load_scan(path: Path, z_scale: float = 1.0) -> np.ndarray` — float64 2-D copy × `z_scale`; raises `ScanLoadError` if not 2-D, either side < 64 px, or no finite values.

- [ ] **Step 1: Initialise git and tooling**

`git init -b main`. `.gitignore`: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `.claude/`, `15_files_task_*/`, `*.docx`. `requirements.txt`: `numpy>=1.24`, `scipy>=1.10`, `scikit-image>=0.21`, `matplotlib>=3.7`. `requirements-dev.txt`: `-r requirements.txt`, `pytest>=7`, `ruff>=0.4`. `pyproject.toml`: `[project]` name `teramount-analysis`, version `1.0.0`, `requires-python = ">=3.10"`; `[tool.pytest.ini_options]` `testpaths = ["tests"]`, markers `realdata: needs the provided .npy datasets` and `slow: takes more than ~10 s`; `[tool.ruff]` `line-length = 100`, `target-version = "py310"`, lint select `["E", "F", "I", "B", "UP", "NPY"]`. Run `py -m pip install -r requirements-dev.txt`.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_io.py
def test_discover_sorts_naturally(tmp_path):
    for n in (10, 2, 1):
        np.save(tmp_path / f"{n}.npy", np.zeros((64, 64)))
    assert [p.name for p in discover_scans(tmp_path)] == ["1.npy", "2.npy", "10.npy"]

def test_discover_single_file(tmp_path): ...            # returns [that file]
def test_discover_missing_path_raises(tmp_path): ...    # FileNotFoundError
def test_discover_empty_folder_raises(tmp_path): ...    # ScanLoadError

def test_load_applies_z_scale(tmp_path):
    np.save(tmp_path / "a.npy", np.ones((64, 80)))
    z = load_scan(tmp_path / "a.npy", z_scale=1e-3)
    assert z.dtype == np.float64 and z.shape == (64, 80) and np.allclose(z, 1e-3)

def test_load_rejects_non_2d(tmp_path): ...             # 1-D and 3-D -> ScanLoadError
def test_load_rejects_tiny_and_all_nan(tmp_path): ...   # (10, 10) and all-NaN (64, 64) -> ScanLoadError

# tests/test_config.py
def test_px_um_roundtrip():
    c = Config()
    assert c.px(0.252) == pytest.approx(1.0) and c.um(4.0) == pytest.approx(1.008)

def test_invalid_config_rejected():
    with pytest.raises(ValueError):
        Config(pixel_size_um=0)
```

- [ ] **Step 3: Implement `errors.py`, `config.py`, `io.py`, `__init__.py`**

`Config` fields (name: type = default — units):

| Group | Fields |
|---|---|
| Units | `pixel_size_um: float = 0.252`, `z_scale: float = 1.0` |
| Switches | `correct_tilt: bool = True`, `correct_rotation: bool = True`, `random_seed: int = 0` |
| Segmentation surface | `seg_median_px: int = 5`, `seg_sigma_um: float = 1.0`, `flat_slope_max: float = 0.25` (µm/µm) |
| Tilt | `ransac_iterations: int = 300`, `ransac_inlier_um: float = 0.1`, `ransac_sample_size: int = 50_000` |
| Rotation | `rotation_search_deg: float = 10.0`, `rotation_canny_sigma_um: float = 0.5`, `rotation_canny_low: float = 0.5`, `rotation_canny_high: float = 1.5` (Sobel units, µm/px), `rotation_min_line_um: float = 20.0`, `rotation_line_gap_um: float = 0.75`, `rotation_profile_half_px: int = 6`, `rotation_max_line_rms_px: float = 0.25`, `rotation_min_valid_fraction: float = 0.6` |
| Pivot | `plane2_min_area_um2: float = 50.0`, `plane2_tie_um: float = 1.0`, `plane1_min_area_um2: float = 200.0`, `plane1_min_drop_um: float = 5.0`, `ramp_search_um: float = 30.0`, `ramp_slope_min: float = 0.3`, `ramp_slope_max: float = 1.5`, `plane_edge_margin_um: float = 0.5`, `walk_max_um: float = 100.0` |
| Crosses | `cross_polarity: str = "recessed"`, `cross_min_depth_um: float = 0.6`, `cross_area_min_um2: float = 5.0`, `cross_area_max_um2: float = 100.0`, `cross_solidity_min: float = 0.75`, `cross_solidity_max: float = 0.97`, `cross_aspect_min: float = 0.7`, `cross_aspect_max: float = 1.4` |
| Xpander | `xpander_smooth_um: float = 2.0`, `xpander_search_um: float = 250.0`, `xpander_min_prominence_um: float = 0.5`, `xpander_refine_um: float = 15.0`, `xpander_ray_count: int = 72`, `xpander_ray_rise_um: float = 0.05`, `xpander_steep_slope: float = 0.3`, `xpander_aperture_fraction: float = 0.8`, `xpander_min_aperture_um: float = 20.0`, `xpander_fit_iterations: int = 3`, `xpander_stability_fractions: tuple[float, ...] = (0.5, 0.75, 1.0)` |
| Nominal spec | `nominal_pivot_step_um: float = 18.18`, `tol_pivot_step_um: float = 0.30`, `nominal_radius_um: float = 826.0`, `tol_radius_um: float = 30.0` |
| Quality limits | `max_plane_rms_um: float = 0.15`, `max_xpander_nrms_pct: float = 2.0`, `max_cross_axis_offset_um: float = 1.0`, `max_apex_axis_offset_um: float = 3.0`, `max_plane_parallelism_deg: float = 0.5`, `max_radius_asymmetry_pct: float = 5.0` |
| Statistics | `outlier_z: float = 3.5`, `min_files_for_statistics: int = 5` |

Each field gets a one-line comment stating its unit and meaning; the nominal block's comment says "estimated from the clean files of the provided datasets; override via CLI". `__init__.py` exports `__version__ = "1.0.0"` (other exports added in Task 12).

- [ ] **Step 4: Run tests** — `py -m pytest tests/test_io.py tests/test_config.py -v` → all PASS; `py -m ruff check .` → clean.

- [ ] **Step 5: Commit** — `git add` the scaffold, package, tests, and `docs/` (design + this plan); message `chore: scaffold package, config, scan loading`.

---

### Task 2: Synthetic scan generator (test infrastructure)

**Files:**
- Create: `tests/synthetic.py`, `tests/test_synthetic.py`

**Interfaces:**
- Produces (used by every later test):
  - `SyntheticTruth` frozen dataclass: `rotation_deg: float`, `slope_x: float`, `slope_y: float`, `pivot_step_um: float`, `cross1_xy_px: tuple[float, float]`, `cross2_xy_px: tuple[float, float]`, `apex_xy_px: tuple[float, float]`, `rx_um: float`, `ry_um: float`, `plane2_center_xy_px: tuple[float, float]`.
  - `make_scan(*, shape=(1200, 800), pixel_size_um=0.252, rotation_deg=0.0, quarter_turns=0, slope_x=0.0, slope_y=0.0, noise_um=0.012, pivot_noise_um=0.0, xpander_noise_um=0.0, rx_um=820.0, ry_um=840.0, dome="paraboloid", channel_offset_um=0.0, second_channel=False, cross1=True, cross2=True, crop_top_um=0.0, nan_fraction=0.0, seed=0) -> tuple[np.ndarray, SyntheticTruth]`.
- The generator must not import `teramount_analysis` (truth must be independent of the code under test).

- [ ] **Step 1: Write the failing tests**

```python
def test_levels_at_known_points():
    z, t = make_scan(noise_um=0.0)
    px = 0.252
    xc = 800 * px / 2
    at = lambda x_um, y_um: z[int(round(y_um / px)), int(round(x_um / px))]
    assert at(xc + 10, 190.0) == pytest.approx(31.0, abs=0.05)      # plane 2
    assert at(xc - 30, 154.0) == pytest.approx(12.9, abs=0.05)      # plane 1
    assert at(xc, 158.5) == pytest.approx(11.1, abs=0.1)            # cross 1 floor
    assert at(xc, 80.0) == pytest.approx(12.4, abs=0.01)            # dome apex
    assert at(xc - 60, 260.0) == pytest.approx(0.0, abs=0.05)       # base (the block is at xc+50)
    assert t.pivot_step_um == pytest.approx(18.1)

def test_rotation_moves_truth_points_like_scipy():
    z0, t0 = make_scan(noise_um=0.0)
    z1, t1 = make_scan(noise_um=0.0, rotation_deg=1.0)
    # truth apex moves by the scipy rotation about the array centre
    c = np.array([(800 - 1) / 2, (1200 - 1) / 2]); a = np.deg2rad(1.0)
    M = np.array([[np.cos(a), np.sin(a)], [-np.sin(a), np.cos(a)]])
    assert np.allclose(t1.apex_xy_px, c + M @ (np.array(t0.apex_xy_px) - c), atol=1e-9)

def test_tilt_and_nans_and_crop():
    z, _ = make_scan(slope_x=0.001, noise_um=0.0, nan_fraction=0.01, crop_top_um=40.0)
    assert np.isnan(z).mean() == pytest.approx(0.01, abs=0.002)
    assert z.shape[0] == 1200 - int(round(40.0 / 0.252))
```

- [ ] **Step 2: Run to verify failure** — `py -m pytest tests/test_synthetic.py -v` → FAIL (import error).

- [ ] **Step 3: Implement `make_scan`**

Render in the canonical frame at pixel centres (`x_um = col·p`, `y_um = row·p`), channel centre `xc = W·p/2 + channel_offset_um`. Heights (later rows override earlier ones):

| Feature | Region (µm) | Height (µm) |
|---|---|---|
| base | everywhere | 0 |
| top band | `y < 12` | 13.0 |
| dome row | `12 ≤ y < 145` | max over k∈{−1,0,1} of `dome(x − xc − 126k, y − 80)` |
| tooth | `|x−xc| ≤ 43`, `145 ≤ y < 200` | 11.0 |
| plane 1 | `|x−xc| ≤ 38`, `152 ≤ y < 199` | 12.9 |
| pads | 4×4 squares centred `x = xc ± 34`, `y ∈ {160,170,180,190}` | 14.9 |
| ramp | `|x−xc| ≤ 16`, `165 ≤ y < 182.6` | `12.9 + (y−165)·18.1/17.6` |
| plane 2 | `|x−xc| ≤ 16`, `182.6 ≤ y < 194.2` | 31.0 |
| cross 1 (if `cross1`) | plus at `(xc, 158.5)`: (`|dx| ≤ 3.25` & `|dy| ≤ 1.25`) or (`|dx| ≤ 1.25` & `|dy| ≤ 3.25`) | 11.1 |
| cross 2 (if `cross2`) | same plus at `(xc, 188.4)` | 29.5 |
| block | `|x−(xc+50)| ≤ 30`, `|y−250| ≤ 30`, with a recessed plus (−1.5) at its centre | 23.5 |

`dome(dx, dy)`: paraboloid `12.4 − dx²/(2·rx) − dy²/(2·ry)`; `dome="sphere"` → `12.4 − (rx − sqrt(rx² − dx² − dy²))`. `second_channel=True` renders tooth/plane1/pads/ramp/plane2/crosses again at `xc + 126`. Then, in order: Gaussian blur σ = 0.7 px; `scipy.ndimage.rotate(z, rotation_deg, reshape=False, order=1, mode="constant", cval=0.0)`; `np.rot90(z, quarter_turns)`; crop `round(crop_top_um/p)` rows from the top; add `slope_x·x_um + slope_y·y_um` (final-frame coordinates); add N(0, `noise_um`) everywhere, N(0, `pivot_noise_um`) inside the plane-1 rectangle, N(0, `xpander_noise_um`) inside the dome cell `|x−xc| ≤ 63, 12 ≤ y < 145` (noise regions transformed with the same rotation/quarter-turn/crop); finally set `nan_fraction` of random pixels to NaN. Truth points are mapped with the generator's own copy of the rotation formula (`p = c + M(q − c)`, `M` as in the test), the `rot90` index formula (k=1: `x' = y`, `y' = W−1−x`, shape swaps; repeat k times), then the crop (`y −= crop rows`). `truth.rotation_deg = rotation_deg + 90·quarter_turns`. All randomness from `default_rng(seed)`.

- [ ] **Step 4: Run tests** — `py -m pytest tests/test_synthetic.py -v` → PASS.

- [ ] **Step 5: Commit** — `test: synthetic scan generator with known truth`.

---

### Task 3: Fitting primitives

**Files:**
- Create: `teramount_analysis/fitting.py`, `tests/test_fitting.py`

**Interfaces:**
- Produces:
  - `PlaneFit` (frozen): `a`, `b`, `c` (z = a·x + b·y + c), `rms`, `n_used`; `evaluate(x, y) -> np.ndarray`; `normal() -> np.ndarray` (unit vector `(−a, −b, 1)/‖·‖`).
  - `fit_plane(x, y, z) -> PlaneFit` — ordinary least squares; raises `FitError` if < 3 points.
  - `fit_plane_robust(x, y, z, clip_sigma: float = 3.0, iterations: int = 5) -> PlaneFit` — LS, then repeatedly refit on points with |residual| < clip_sigma·1.4826·MAD (MAD floor 1e-6); `rms` = std of the final inliers' residuals.
  - `ransac_plane(x, y, z, tol: float, iterations: int, rng: np.random.Generator) -> np.ndarray` — boolean inlier mask of the 3-point model with most points within `tol`.
  - `QuadricFit` (frozen): `coeffs` (6,) for `z = c0 + c1·u + c2·v + c3·u² + c4·v² + c5·u·v`, `cov` (6,6) = `σ²(AᵀA)⁻¹` with `σ² = SSE/(N−6)`, `rms`, `r2`, `n`, `residuals`; `evaluate(u, v)`, `hessian() -> np.ndarray` (`[[2c3, c5], [c5, 2c4]]`), `vertex() -> tuple[float, float]` (solves `H·[u0,v0] = −[c1,c2]`; raises `FitError` if singular).
  - `fit_quadric(u, v, z) -> QuadricFit` — raises `FitError` if < 10 points.
  - `SphereFit` (frozen): `xc`, `yc`, `zc`, `radius`, `rms`. `fit_sphere(x, y, z, initial: tuple[float, float, float, float]) -> SphereFit` — `scipy.optimize.least_squares` on geometric residuals `‖p − c‖ − R`.
  - `fit_profile_circle(s, z) -> tuple[float, float]` — `(radius, rms)` of a circle fitted to a 1-D profile (initial guess from a parabola fit; geometric residuals via `least_squares`).

- [ ] **Step 1: Write the failing tests**

```python
def test_plane_exact():
    x, y = np.meshgrid(np.arange(20.0), np.arange(30.0))
    f = fit_plane(x.ravel(), y.ravel(), (0.01 * x - 0.02 * y + 3).ravel())
    assert (f.a, f.b, f.c) == pytest.approx((0.01, -0.02, 3.0), abs=1e-12)

def test_robust_plane_ignores_20pct_outliers():
    # 20 % of points raised by +2: robust fit recovers the plane within 1e-3, OLS does not
    ...

def test_ransac_finds_majority_plane():
    # 60 % points on plane A, 40 % on plane B 5 units higher -> inliers == plane-A points (>= 99 %)
    ...

def test_quadric_recovers_curvature_and_vertex():
    u, v = np.meshgrid(np.linspace(-40, 40, 161), np.linspace(-40, 40, 161))
    z = 2.0 + 0.003 * u - 0.002 * v - u**2 / (2 * 800) - v**2 / (2 * 850)
    q = fit_quadric(u.ravel(), v.ravel(), z.ravel())
    assert -1 / (2 * q.coeffs[3]) == pytest.approx(800, rel=1e-9)
    assert -1 / (2 * q.coeffs[4]) == pytest.approx(850, rel=1e-9)
    assert q.vertex() == pytest.approx((0.003 * 800, -0.002 * 850), rel=1e-6)

def test_sphere_and_profile_circle_recover_radius():
    # spherical cap R = 830 sampled within r <= 45 -> fit_sphere radius within 0.05 %;
    # its central profile -> fit_profile_circle radius within 0.1 %
    ...
```

- [ ] **Step 2: Run to verify failure** — `py -m pytest tests/test_fitting.py -v` → FAIL.
- [ ] **Step 3: Implement `fitting.py`** — centre coordinates before each solve (subtract means) for conditioning; use `np.linalg.lstsq`.
- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Commit** — `feat: least-squares, robust, RANSAC, quadric and sphere fits`.

---

### Task 4: Surface helpers and tilt correction

**Files:**
- Create: `teramount_analysis/surface.py`, `teramount_analysis/tilt.py`, `tests/test_surface.py`, `tests/test_tilt.py`

**Interfaces:**
- Consumes: `Config`, `fitting.ransac_plane`, `fitting.fit_plane_robust`.
- Produces:
  - `surface.fill_invalid(z) -> tuple[np.ndarray, np.ndarray]` — `(filled copy, valid mask)`; non-finite pixels take the value of the nearest valid pixel (`ndimage.distance_transform_edt(..., return_indices=True)`).
  - `surface.smooth(z, sigma_px: float, median_px: int = 0) -> np.ndarray` — optional median pre-filter, then Gaussian.
  - `surface.slope(z, pixel_size_um: float) -> np.ndarray` — `hypot(*np.gradient(z)) / pixel_size_um` (µm/µm).
  - `surface.segmentation_surface(z, config) -> np.ndarray` — `smooth(fill_invalid(z)[0], config.px(config.seg_sigma_um), config.seg_median_px)`.
  - `surface.flat_mask(z_seg, config) -> np.ndarray` — `slope(z_seg) < config.flat_slope_max`.
  - `tilt.TiltResult` (frozen): `slope_x`, `slope_y` (µm/µm), `offset_um` (plane height at pixel (0,0)), `tilt_x_deg`, `tilt_y_deg`, `tilt_total_deg`, `tilt_azimuth_deg` (= `degrees(atan2(slope_y, slope_x))`), `base_rms_um`, `base_fraction`.
  - `tilt.fit_base_plane(z, config) -> TiltResult` — raises `FitError` if < 1 % of pixels are flat.
  - `tilt.remove_tilt(z, tilt, config) -> np.ndarray` — subtracts the plane (only `offset_um` when `config.correct_tilt` is False); keeps NaNs.

Algorithm for `fit_base_plane`: flat valid pixels → coordinates in µm → random sample of ≤ `ransac_sample_size` → `ransac_plane(tol=ransac_inlier_um, iterations=ransac_iterations)` → keep all flat pixels within `3·ransac_inlier_um` of that plane → `fit_plane_robust` → angles `degrees(arctan(...))`. Rationale for the docstring: the base is the largest flat surface on the chip; RANSAC finds it even though raised structures cover a large share of the image.

- [ ] **Step 1: Write the failing tests**

```python
def test_fill_invalid_uses_nearest(): ...           # NaN next to a 5.0 pixel becomes 5.0; mask marks it invalid
def test_slope_units():
    x = np.arange(100.0) * 0.252
    z = np.tile(0.5 * x, (50, 1))                   # 0.5 µm per µm
    assert np.allclose(slope(z, 0.252)[5:-5, 5:-5], 0.5)

def test_tilt_recovered_on_synthetic():
    z, t = make_scan(slope_x=0.0015, slope_y=-0.0010, rotation_deg=0.5)
    r = fit_base_plane(z, Config())
    assert r.slope_x == pytest.approx(0.0015, abs=2e-5)
    assert r.slope_y == pytest.approx(-0.0010, abs=2e-5)
    assert r.tilt_x_deg == pytest.approx(np.degrees(np.arctan(0.0015)), abs=0.002)
    assert r.base_rms_um < 0.02

def test_tilt_ignores_nan_pixels():
    z, t = make_scan(slope_x=0.001, nan_fraction=0.02)
    assert fit_base_plane(z, Config()).slope_x == pytest.approx(0.001, abs=2e-5)

def test_remove_tilt_levels_base():
    z, _ = make_scan(slope_x=0.001, slope_y=0.002)
    lev = remove_tilt(z, fit_base_plane(z, Config()), Config())
    assert abs(np.nanmedian(lev[-100:, :])) < 0.01   # bottom rows are base
```

- [ ] **Step 2: Run to verify failure** → FAIL.
- [ ] **Step 3: Implement `surface.py` and `tilt.py`.**
- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Commit** — `feat: base-plane tilt estimation and leveling`.

---

### Task 5: Coordinate frame

**Files:**
- Create: `teramount_analysis/frame.py`, `tests/test_frame.py`

**Interfaces:**
- Produces `Frame` (frozen dataclass): `shape: tuple[int, int]` (original H, W), `angle_deg: float` (fine rotation φ), `quarter_turns: int = 0` (k ∈ 0..3).
  - `canonical_shape -> tuple[int, int]` — `shape` if k even else swapped.
  - `rotation_deg -> float` — `φ − 90·k` normalised to (−180, 180].
  - `to_canonical(x, y) -> tuple[np.ndarray, np.ndarray]` and `to_original(u, v)` — accept scalars or arrays.
  - `canonical_image(z, order: int = 1) -> np.ndarray` — `np.rot90(ndimage.rotate(fill_invalid(z)[0], −φ, reshape=False, order=order, mode="nearest"), k)`.
  - `canonical_coordinates() -> tuple[np.ndarray, np.ndarray]` — `(U, V)` for every original pixel, shape `shape`; cached (`functools.cached_property`-backed) because it is reused by every measurement.
  - `pull_back(mask_canonical: np.ndarray) -> np.ndarray` — original-shape bool mask: pixel is True when its canonical coordinates round to a True pixel inside the canonical image.

Math (verified against scipy in exploration): with `c = ((W−1)/2, (H−1)/2)` and `M = [[cos φ, sin φ], [−sin φ, cos φ]]` acting on `(x, y)`: fine-corrected `f = c + Mᵀ(p − c)`; inverse `p = c + M(f − c)`. Quarter turn (`np.rot90(·, 1)`) on an image of width `W'`: `(x, y) → (y, W' − 1 − x)`, shape `(H', W') → (W', H')`; apply k times; inverse applies the reverse map k times.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("phi,k", [(0.0, 0), (1.0, 0), (-0.75, 0), (3.0, 1), (0.5, 2), (-2.0, 3)])
def test_roundtrip(phi, k):
    f = Frame((300, 200), phi, k)
    x, y = np.random.default_rng(0).uniform(0, 199, 50), np.random.default_rng(1).uniform(0, 299, 50)
    assert np.allclose(f.to_original(*f.to_canonical(x, y)), (x, y), atol=1e-9)

@pytest.mark.parametrize("phi,k", [(10.0, 0), (-4.0, 1), (7.0, 2), (2.0, 3)])
def test_canonical_image_matches_to_canonical(phi, k):
    img = np.zeros((301, 201)); img[60, 140] = 1.0
    f = Frame(img.shape, phi, k)
    cy, cx = ndimage.center_of_mass(f.canonical_image(img))
    assert (cx, cy) == pytest.approx(f.to_canonical(140.0, 60.0), abs=0.15)

def test_rotation_deg_normalised():
    assert Frame((10, 10), 1.0, 2).rotation_deg == pytest.approx(-179.0)

def test_pull_back_identity_when_unrotated():
    m = np.zeros((50, 40), bool); m[10:20, 5:9] = True
    assert (Frame(m.shape, 0.0).pull_back(m) == m).all()
```

- [ ] **Step 2: Run to verify failure** → FAIL.
- [ ] **Step 3: Implement `frame.py`.**
- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Commit** — `feat: coordinate frame between original and canonical scans`.

---

### Task 6: Fine rotation estimation

**Files:**
- Create: `teramount_analysis/rotation.py`, `tests/test_rotation.py`

**Interfaces:**
- Consumes: `Config`, `surface.fill_invalid`, `surface.smooth`.
- Produces:
  - `EdgeLine` (frozen): `x0, y0, x1, y1: float`, `vertical: bool`, `angle_deg: float`, `rms_px: float`, `n_points: int`.
  - `RotationResult` (frozen): `angle_deg: float`, `se_deg: float`, `n_lines: int`, `lines: tuple[EdgeLine, ...]`.
  - `edge_crossing(heights: np.ndarray, gradients: np.ndarray) -> float | None` — sub-pixel index of the step's mid-level crossing.
  - `line_angle(points: np.ndarray, vertical: bool) -> tuple[float, float]` — `(angle_deg, rms_px)`.
  - `estimate_rotation(z_leveled: np.ndarray, config: Config) -> RotationResult` — raises `RotationError` when no line survives.

Algorithm (the method that reached ≤ 0.018° error on the real data; the gradient-peak variant was biased toward 0° by pixel locking, so do not use it):
1. `zf = fill_invalid(z)[0]`; `edges = skimage.feature.canny(zf, sigma=config.px(rotation_canny_sigma_um), low_threshold=rotation_canny_low, high_threshold=rotation_canny_high, mode="nearest")`. `mode="nearest"` is required: canny's default zero padding creates artificial edges along the image border at exactly 0°, which bias the estimate toward 0 (seen in the prototype as a "line" on row 1). Also discard any segment with an endpoint closer than `ceil(3·sigma_px) + rotation_profile_half_px` px to the image border.
2. Hough angle set (normal angles) `S = rotation_search_deg`: `deg2rad(r_[linspace(−S, S, 8S+1), 90 + linspace(−S, S, 8S+1)])`, wrapped into [−π/2, π/2). `segments = probabilistic_hough_line(edges, threshold=10, line_length=round(px(rotation_min_line_um)), line_gap=round(px(rotation_line_gap_um)), theta=..., rng=config.random_seed)`.
3. `zs = smooth(zf, 1.0)`, `g = hypot(sobel_y(zs), sobel_x(zs))`. For each segment, `vertical = |dy| > |dx|`. Vertical: for every integer row `r` strictly inside the segment (skip 2 px at both ends), `xl` = segment x at `r`, `c0 = round(xl)`, `h = rotation_profile_half_px`; `p = edge_crossing(zs[r, c0−h:c0+h+1], g[r, c0−h:c0+h+1])`; point `(c0 − h + p, r)`. Horizontal: same with columns, point `(c, r0 − h + p)`. Positions are relative to the **rounded** pixel, never to the Hough line (that bug biased angles by 30 % in the prototype).
4. Keep segments with ≥ `rotation_min_valid_fraction` valid points; `line_angle`: vertical fits `x = a + b·y`, angle `= degrees(atan(b))`; horizontal fits `y = a + b·x`, angle `= −degrees(atan(b))`. Drop lines with `rms_px > rotation_max_line_rms_px`.
5. `angle_deg` = median of line angles weighted by `n_points`; `se_deg = 1.2533 · 1.4826 · MAD / sqrt(n_lines)`.

`edge_crossing`: `i = argmax(gradients)`; require `1 < i < len−2`; `left = median(heights[max(i−6,0):max(i−3,1)])`, `right = median(heights[i+4:i+7])` (return None if either slice is empty); `mid = (left+right)/2`; for `k` in `[i−3, i+2]` find the first sign change of `heights − mid` between `k` and `k+1` and return `k + (mid − h[k])/(h[k+1] − h[k])`; else None.

- [ ] **Step 1: Write the failing tests**

```python
def test_edge_crossing_subpixel():
    x = np.arange(13.0)
    h = 1 / (1 + np.exp(-(x - 6.3) / 0.6))            # step centred at 6.3
    assert edge_crossing(h, np.gradient(h)) == pytest.approx(6.3, abs=0.02)

@pytest.mark.parametrize("phi", [0.0, 0.5, -1.0, 3.0, -7.5])
def test_rotation_recovered_on_synthetic(phi):
    z, t = make_scan(rotation_deg=phi)
    r = estimate_rotation(z, Config())
    assert r.angle_deg == pytest.approx(phi, abs=0.03)
    assert r.n_lines >= 10 and r.se_deg < 0.05

def test_flat_image_raises():
    with pytest.raises(RotationError):
        estimate_rotation(np.zeros((300, 300)), Config())
```

(The real-data accuracy test — Task 1 files ≈ 0°, Task 2 − Task 1 = applied angle ± 0.03° — lives in `tests/test_real_data.py`, Task 15.)

- [ ] **Step 2: Run to verify failure** → FAIL.
- [ ] **Step 3: Implement `rotation.py`.**
- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Commit** — `feat: sub-pixel straight-edge rotation estimator`.

---

### Task 7: Pivot segmentation and coarse orientation

**Files:**
- Create: `teramount_analysis/pivot.py` (segmentation part), `tests/helpers.py`, `tests/test_pivot_segmentation.py`

`tests/helpers.py` (shared by Tasks 7–10): `prepare(z, phi) -> (z_leveled, frame, z_canonical, z_seg)` = level with `fit_base_plane`/`remove_tilt`, `frame = Frame(z.shape, phi, 0)`, `z_canonical = frame.canonical_image(z_leveled)`, `z_seg = segmentation_surface(z_canonical, Config())`; and `seg(z) = prepare(z, 0.0)[3]`. Tasks 8–10 add `run_crosses(z, phi) -> tuple[CrossResult, CrossResult]`, `run_pivot(z, phi) -> PivotResult`, `run_xpander(z, phi) -> XpanderResult` here (each runs the chain up to its own function with the known `phi`, isolating the unit from rotation estimation).

**Interfaces:**
- Consumes: `Config`, `surface.flat_mask`, `surface.slope`, `Frame`.
- Produces:
  - `PivotRegions` (frozen): `plane1: np.ndarray`, `plane2: np.ndarray` (bool, canonical), `plane2_level_um: float`, `plane2_centroid_uv: tuple[float, float]`, `axis_u: float` (centroid u of `plane1 | plane2`, px).
  - `find_plane2(z_seg, config) -> np.ndarray` — raises `ElementNotFoundError("plane 2 not found")`.
  - `ramp_direction(z_seg, plane2, config) -> tuple[float, float]` — unit vector pointing down the ramp (toward plane 1).
  - `quarter_turns_for(direction) -> int` — `α = degrees(atan2(−dy, dx))`, `k = round((90 − α)/90) mod 4`.
  - `find_plane1(z_seg, plane2, config) -> np.ndarray` — canonical orientation only (walks toward −v).
  - `segment_pivot(z_seg, config) -> PivotRegions` — find plane 2; require the ramp to point up (`dy < −0.7` else `ElementNotFoundError("unexpected orientation")`); find plane 1.

Algorithms:
- `find_plane2`: label `flat_mask` (8-connectivity); candidates = components with area ≥ `plane2_min_area_um2` not touching the image border; `top` = max component median height; finalists = median ≥ `top − plane2_tie_um`; choose the finalist whose centroid is closest to the image centre.
- `ramp_direction`: `dist = distance_transform_edt(~plane2)·pixel_size`; ring = `0 < dist ≤ ramp_search_um` & `ramp_slope_min ≤ slope ≤ ramp_slope_max` & `z_seg < level2 − 1`; mean of downhill unit vectors `−∇z/|∇z|`, normalised; `ElementNotFoundError` if the ring has < 50 px. (Side walls cancel by symmetry; the cliff is too steep to qualify.)
- `find_plane1`: from the plane-2 centroid step 1 px toward −v for up to `walk_max_um`; the first pixel lying in a flat component that is not plane 2, has median height < `level2 − plane1_min_drop_um`, and area ≥ `plane1_min_area_um2` → that component (smaller components, e.g. noise specks, are walked past). Not found → `ElementNotFoundError("plane 1 not found")`.

- [ ] **Step 1: Write the failing tests** (all on `segmentation_surface(remove_tilt(...))` of synthetic scans)

```python
def test_plane2_and_plane1_found():
    z, t = make_scan()
    reg = segment_pivot(seg(z), Config())
    assert reg.plane2_centroid_uv == pytest.approx(t.plane2_center_xy_px, abs=4)
    assert reg.plane2_level_um == pytest.approx(31.0, abs=0.1)
    assert 200 < reg.plane1.sum() * 0.252**2 < 3600     # µm²; 3600 = full plane-1 rectangle

def test_noisy_pivot_still_segmented():
    z, t = make_scan(pivot_noise_um=0.6)
    reg = segment_pivot(seg(z), Config())
    assert reg.plane1.sum() * 0.252**2 > 200

@pytest.mark.parametrize("k,expected", [(0, (0, -1)), (2, (0, 1)), (1, (-1, 0)), (3, (1, 0))])
def test_ramp_direction_follows_quarter_turns(k, expected):
    z, _ = make_scan(quarter_turns=k)
    s = seg(z); d = ramp_direction(s, find_plane2(s, Config()), Config())
    assert np.dot(d, expected) > 0.95

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
    cy, cx = ndimage.center_of_mass(p2)
    assert cx == pytest.approx(t.plane2_center_xy_px[0], abs=4)
```

- [ ] **Step 2: Run to verify failure** → FAIL.
- [ ] **Step 3: Implement the segmentation half of `pivot.py`.**
- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Commit** — `feat: pivot plane segmentation and coarse orientation`.

---

### Task 8: Cross detection and centres

**Files:**
- Create: `teramount_analysis/crosses.py`, `tests/test_crosses.py`

**Interfaces:**
- Consumes: `Frame` (`canonical_coordinates`, `pull_back`), `fitting.fit_plane_robust`, `PivotRegions`.
- Produces:
  - `CrossResult` (frozen): `found: bool`, `x_px, y_px` (original), `u_px, v_px` (canonical), `depth_um`, `area_um2`, `solidity`, `axis_offset_um` (`|u − axis_u|·pixel_size`), `mask: np.ndarray | None` (canonical). Not found → `found=False`, numeric fields NaN, `mask=None`.
  - `find_cross(z_leveled, frame, z_canonical, plane_mask, axis_u, config) -> CrossResult`.

Algorithm: robust plane fit on `z_canonical` over `binary_erosion(plane_mask, 2)`; residual over `convex_hull_image(plane_mask)`; smooth the residual (median 3, then Gaussian σ = 1 px); candidates = residual `< −cross_min_depth_um` (`> +` when `cross_polarity == "raised"`); keep components with area, solidity, and bbox aspect (width/height) inside the configured ranges; choose the smallest `|u_centroid − axis_u|`. Centre: pull the chosen mask (dilated by 1 px) back to original pixels, drop NaN pixels, compute each pixel's raw (unsmoothed) residual against the same plane using its canonical coordinates, weight `w = max(−residual, 0)` (`max(residual, 0)` for raised); `(x, y)` = weighted mean of original coordinates, `(u, v)` = weighted mean of canonical coordinates. (Depth weighting makes the centre sub-pixel accurate; a binary centroid jitters with the pixelated outline.) `depth_um` = median |residual| inside the eroded mask.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("phi", [0.0, 0.75])
def test_cross_centres_match_truth(phi):
    z, t = make_scan(rotation_deg=phi)
    c1, c2 = run_crosses(z, phi)   # helper: level, Frame(phi), canonical image, segment_pivot, find_cross x2
    assert (c1.x_px, c1.y_px) == pytest.approx(t.cross1_xy_px, abs=0.3)
    assert (c2.x_px, c2.y_px) == pytest.approx(t.cross2_xy_px, abs=0.3)
    assert c1.depth_um == pytest.approx(1.8, abs=0.2) and c2.depth_um == pytest.approx(1.5, abs=0.2)

def test_noisy_plane_cross_still_found():
    z, t = make_scan(pivot_noise_um=0.6)
    c1, c2 = run_crosses(z, 0.0)
    assert (c1.x_px, c1.y_px) == pytest.approx(t.cross1_xy_px, abs=0.6)

def test_missing_cross_reported_not_raised():
    z, t = make_scan(cross2=False)
    c1, c2 = run_crosses(z, 0.0)
    assert c1.found and not c2.found and np.isnan(c2.x_px)
```

- [ ] **Step 2: Run to verify failure** → FAIL.
- [ ] **Step 3: Implement `crosses.py`.**
- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Commit** — `feat: recessed cross detection with sub-pixel centres`.

---

### Task 9: Pivot height difference

**Files:**
- Modify: `teramount_analysis/pivot.py` (measurement part)
- Create: `tests/test_pivot_measurement.py`

**Interfaces:**
- Consumes: `PivotRegions`, `CrossResult.mask`, `Frame`, `fitting.fit_plane_robust`, `fitting.fit_plane`.
- Produces:
  - `PivotResult` (frozen): `height_diff_um`, `height_diff_with_crosses_um`, `plane1_level_um`, `plane2_level_um` (both evaluated at the plane-2 centroid), `plane1_rms_um`, `plane2_rms_um`, `parallelism_deg`.
  - `measure_pivot(z_leveled, frame, regions, cross1_mask: np.ndarray | None, cross2_mask: np.ndarray | None, config) -> PivotResult`.

Algorithm: per plane, fit mask (canonical) = `binary_erosion(plane, px(plane_edge_margin_um))` minus `binary_dilation(cross_mask, 2)` (the raised pads are already holes in the plane-1 component, so they are excluded too); pull back to original pixels (dropping NaN pixels); `fit_plane_robust` on canonical coordinates in µm and original leveled heights. `height_diff = plane2(u_c, v_c) − plane1(u_c, v_c)` at the plane-2 centroid. "With crosses" variant: fit mask plus the dilated cross mask, plain `fit_plane` (no clipping, otherwise the clipping would drop the cross again). `parallelism_deg` = angle between the two plane normals.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("phi,slopes", [(0.0, (0, 0)), (-1.0, (0.0015, -0.001))])
def test_height_difference(phi, slopes):
    z, t = make_scan(rotation_deg=phi, slope_x=slopes[0], slope_y=slopes[1])
    p = run_pivot(z, phi)            # helper: level -> frame -> segment -> crosses -> measure_pivot
    assert p.height_diff_um == pytest.approx(18.1, abs=0.02)
    assert p.parallelism_deg < 0.05

def test_height_difference_with_pivot_noise():
    z, _ = make_scan(pivot_noise_um=0.6)
    p = run_pivot(z, 0.0)
    assert p.height_diff_um == pytest.approx(18.1, abs=0.05)
    assert p.plane1_rms_um > 0.4

def test_crosses_bias_naive_estimate():
    z, _ = make_scan(noise_um=0.0)
    p = run_pivot(z, 0.0)
    assert 0.005 < abs(p.height_diff_with_crosses_um - p.height_diff_um) < 1.0
```

- [ ] **Step 2: Run to verify failure** → FAIL.
- [ ] **Step 3: Implement `measure_pivot`.**
- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Commit** — `feat: pivot plane fits and height difference`.

---

### Task 10: Xpander localisation, aperture and curvature

**Files:**
- Create: `teramount_analysis/xpander.py`, `tests/test_xpander.py`

**Interfaces:**
- Consumes: `PivotRegions`, `Frame`, `surface.smooth`, `surface.slope`, `fitting.fit_quadric`, `fitting.fit_sphere`, `fitting.fit_profile_circle`.
- Produces:
  - `XpanderResult` (frozen): `found: bool`, `reason: str`, `apex_x_px, apex_y_px, apex_u_px, apex_v_px`, `axis_offset_um`, `aperture_radius_um`, `rx_um, ry_um, rx_ci95_um, ry_ci95_um`, `r1_um, r2_um, principal_angle_deg`, `rms_um, nrms_pct, r2, sag_um`, `r_sphere_um`, `rx_profile_um, ry_profile_um`, `stability_pct`, `n_points: int`, `residual_map: np.ndarray | None` (canonical-shape array, NaN outside the aperture). Not found → `found=False`, `reason` set, numbers NaN.
  - `locate_apex(z_canonical, regions, config) -> tuple[float, float]` — raises `ElementNotFoundError`.
  - `boundary_distances(z_smooth, apex_uv, config) -> np.ndarray` — per-ray distances in px.
  - `measure_xpander(z_leveled, frame, z_canonical, regions, config) -> XpanderResult` — never raises for "not found"; returns `found=False`.

Algorithms:
- `locate_apex`: `zs = smooth(z_canonical, px(xpander_smooth_um))`; column `u = round(axis_u)`; walk up from 5 px above the top of `plane1` for `px(xpander_search_um)` rows; `scipy.signal.find_peaks(profile, prominence=xpander_min_prominence_um)`; the **first** peak (closest to the Pivot) is the seed; refine to the argmax of `zs` within ± `px(xpander_refine_um)`.
- `boundary_distances`: `xpander_ray_count` rays from the apex; along each ray (1 px steps, nearest pixel) stop at the first point where `slope > xpander_steep_slope`, or the height rises more than `xpander_ray_rise_um` above the running minimum (the valley to the neighbouring dome has been passed), or the image border is reached; return the stop distances.
- Iterate `xpander_fit_iterations` times: `radius = xpander_aperture_fraction · min(distances)`; if `radius < px(xpander_min_aperture_um)` → not found (`"aperture too small (dome cut by border or neighbour)"`); select original pixels whose canonical distance to the apex ≤ radius (bounding box first, for speed; drop NaNs); `fit_quadric` on µm coordinates relative to the apex; require `c3 < 0` and `c4 < 0` (else not found, `"surface not convex"`); move the apex to the vertex (shift > radius/2 → not found, `"apex unstable"`).
- Outputs: `rx = −1/(2c3)`, `ry = −1/(2c4)`; `ci95 = 1.96·sqrt(cov[3,3])/(2c3²)` (same for y); principal radii `−1/λ` of `hessian()` (R1 = smaller radius) with the angle of R1's eigenvector from the +u axis, in degrees within (−90, 90]; `sag` = max − min of the fitted values over the aperture; `nrms_pct = 100·rms/sag`; `r_sphere` from `fit_sphere` (initial: apex u, v, `z_vertex − (rx+ry)/2`, `(rx+ry)/2`); `rx_profile`/`ry_profile` from `fit_profile_circle` on aperture pixels within ±0.5 px of the line `v = v0` (resp. `u = u0`); `stability_pct = 100·(max − min)/mean` of `(rx+ry)/2` refitted at each `xpander_stability_fractions` × radius; `axis_offset_um = |u_apex − axis_u|·pixel_size`.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("phi", [0.0, -1.0])
def test_paraboloid_radii_recovered(phi):
    z, t = make_scan(rotation_deg=phi, rx_um=820, ry_um=840)
    x = run_xpander(z, phi)            # helper: level -> frame -> canonical -> segment -> measure_xpander
    assert x.found
    assert x.rx_um == pytest.approx(820, rel=0.003) and x.ry_um == pytest.approx(840, rel=0.003)
    assert (x.apex_x_px, x.apex_y_px) == pytest.approx(t.apex_xy_px, abs=1.0)
    assert x.aperture_radius_um == pytest.approx(0.8 * 63, rel=0.1)
    assert x.nrms_pct < 1.0 and x.r2 > 0.999

def test_sphere_cap_cross_checks():
    z, _ = make_scan(dome="sphere", rx_um=830, ry_um=830)
    x = run_xpander(z, 0.0)
    assert x.r_sphere_um == pytest.approx(830, rel=0.003)
    assert x.rx_um == pytest.approx(830, rel=0.005) and x.rx_profile_um == pytest.approx(830, rel=0.01)

def test_noisy_dome_radius_unbiased_but_flagged_by_nrms():
    z, _ = make_scan(xpander_noise_um=0.2, rx_um=820, ry_um=840)
    x = run_xpander(z, 0.0)
    assert x.rx_um == pytest.approx(820, rel=0.01) and x.nrms_pct > 2.0
    assert abs(x.rx_um - 820) < 3 * x.rx_ci95_um + 1.0

def test_dome_cut_by_border_is_not_found():
    z, _ = make_scan(crop_top_um=60.0)   # top 60 µm removed: dome apex 20 µm from the border
    x = run_xpander(z, 0.0)
    assert not x.found and x.reason      # rejected by prominence or by aperture size, never fitted
```

- [ ] **Step 2: Run to verify failure** → FAIL.
- [ ] **Step 3: Implement `xpander.py`.**
- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Commit** — `feat: xpander apex, auto aperture, curvature and figures of merit`.

---

### Task 11: Result container and fault checks

**Files:**
- Create: `teramount_analysis/results.py`, `teramount_analysis/faults.py`, `tests/test_faults.py`

**Interfaces:**
- Consumes: `TiltResult`, `RotationResult`, `Frame`, `PivotRegions`, `PivotResult`, `CrossResult`, `XpanderResult`, `Config`.
- Produces:
  - `results.FaultReport` (frozen): `geometric: tuple[str, ...]`, `nominal: tuple[str, ...]`, `statistical: tuple[str, ...]`; property `faulty -> bool` = `bool(geometric or nominal)` (a statistical anomaly alone is reported but is not a defect).
  - `results.ScanDebug`: `z_leveled`, `z_canonical`, `regions: PivotRegions | None` (arrays for figures only).
  - `results.ScanResult` (mutable dataclass): `file: str`, `status: str` (`"ok" | "partial" | "failed"`), `error: str`, `tilt`, `rotation`, `frame`, `pivot`, `cross1`, `cross2`, `xpander` (each `... | None`), `faults: FaultReport | None`, `debug: ScanDebug | None`; method `metrics(config) -> dict[str, float]` with exactly the keys of `METRIC_COLUMNS` (NaN when unavailable).
  - `results.METRIC_COLUMNS: tuple[str, ...]` — in this order: `tilt_x_deg, tilt_y_deg, tilt_total_deg, tilt_azimuth_deg, base_rms_um, rotation_deg, rotation_se_deg, rotation_lines, pivot_height_diff_um, pivot_height_diff_with_crosses_um, plane1_rms_um, plane2_rms_um, plane_parallelism_deg`, then for `n` in 1, 2: `cross{n}_x_px, cross{n}_y_px, cross{n}_x_um, cross{n}_y_um, cross{n}_u_px, cross{n}_v_px, cross{n}_depth_um, cross{n}_axis_offset_um`, then `xpander_apex_x_px, xpander_apex_y_px, xpander_apex_u_px, xpander_apex_v_px, xpander_apex_axis_offset_um, xpander_rx_um, xpander_ry_um, xpander_rx_ci95_um, xpander_ry_ci95_um, xpander_r1_um, xpander_r2_um, xpander_principal_angle_deg, xpander_rms_um, xpander_nrms_pct, xpander_r2, xpander_sag_um, xpander_aperture_um, xpander_r_sphere_um, xpander_rx_profile_um, xpander_ry_profile_um, xpander_stability_pct`. (`rotation_deg` = `frame.rotation_deg`; µm columns = px × pixel size.)
  - `faults.geometric_flags(result: ScanResult, config) -> tuple[str, ...]` — codes: `rotation_not_measured` (rotation correction requested but `result.rotation is None`), `plane2_not_found`, `plane1_not_found`, `cross1_not_found`, `cross2_not_found`, `xpander_not_found`, `plane1_noisy`, `plane2_noisy` (rms > `max_plane_rms_um`), `xpander_surface_noisy` (nrms > `max_xpander_nrms_pct`), `cross1_off_axis`, `cross2_off_axis` (> `max_cross_axis_offset_um`), `apex_off_axis` (> `max_apex_axis_offset_um`), `planes_not_parallel`, `xpander_astigmatic` (`100·|rx−ry|/mean > max_radius_asymmetry_pct`).
  - `faults.nominal_flags(result, config) -> tuple[str, ...]` — `pivot_step_out_of_spec`, `rx_out_of_spec`, `ry_out_of_spec`.
  - `faults.STAT_METRICS = ("pivot_height_diff_um", "xpander_rx_um", "xpander_ry_um", "xpander_nrms_pct", "plane1_rms_um", "plane2_rms_um", "cross1_axis_offset_um", "cross2_axis_offset_um", "xpander_apex_axis_offset_um")`.
  - `faults.statistical_flags(metrics_list: Sequence[Mapping[str, float]], config) -> list[tuple[str, ...]]` — per metric, robust z = `0.6745·(x − median)/MAD` over finite values; `|z| > outlier_z` → `"<metric>_outlier"`; skip a metric whose MAD is 0; return all-empty when fewer than `min_files_for_statistics` files have finite values for it.

- [ ] **Step 1: Write the failing tests** (fabricate `ScanResult`s with small dataclass instances — no images needed)

```python
def test_noisy_plane_and_dome_flagged(): ...        # plane1_rms 0.5, nrms 9 % -> {"plane1_noisy", "xpander_surface_noisy"}
def test_missing_elements_flagged(): ...            # cross2 found=False, xpander found=False -> both *_not_found
def test_out_of_spec_step(): ...                    # height 17.5 with nominal 18.18 ± 0.30 -> ("pivot_step_out_of_spec",)
def test_clean_result_has_no_flags_and_not_faulty(): ...
def test_statistical_outlier():
    rows = [{"xpander_rx_um": v} for v in (820, 822, 825, 819, 821, 823, 900)]
    flags = statistical_flags(rows, Config())
    assert flags[-1] == ("xpander_rx_um_outlier",) and all(f == () for f in flags[:-1])
def test_statistics_need_five_files():
    assert statistical_flags([{"xpander_rx_um": v} for v in (1, 2, 100)], Config()) == [(), (), ()]
def test_metrics_keys_match_columns(): ...          # set(result.metrics(cfg)) == set(METRIC_COLUMNS)
```

- [ ] **Step 2: Run to verify failure** → FAIL.
- [ ] **Step 3: Implement `results.py` and `faults.py`.**
- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Commit** — `feat: result container and three-layer fault checks`.

---

### Task 12: Pipeline

**Files:**
- Create: `teramount_analysis/pipeline.py`, `tests/test_pipeline.py`
- Modify: `teramount_analysis/__init__.py` (export `Config, ScanResult, analyse_scan, analyse_file, analyse_dataset`)

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `analyse_scan(z: np.ndarray, config: Config, name: str = "") -> ScanResult` — never raises for `AnalysisError`; unexpected exceptions are also caught, logged with traceback at DEBUG, and reported as `status="failed"`.
  - `analyse_file(path: Path, config: Config) -> ScanResult` — load errors → `failed` row.
  - `analyse_dataset(paths: Sequence[Path], config: Config, on_scan: Callable[[ScanResult], None] | None = None) -> list[ScanResult]` — calls `on_scan` (figures) per scan, then sets `debug = None` (memory), then applies `statistical_flags` across the run and rebuilds each `FaultReport`.

Order inside `analyse_scan`: `fit_base_plane` → `remove_tilt` → `estimate_rotation` (skipped → φ = 0 when `correct_rotation` is False; a `RotationError` → φ = 0, warning logged, `rotation = None`, which yields the `rotation_not_measured` flag, and the analysis continues) → `Frame(shape, φ, 0)` → `segmentation_surface(canonical_image)` → `find_plane2` → `ramp_direction` → `k = quarter_turns_for` → `Frame(shape, φ, k)`; `z_canonical = frame.canonical_image(z_leveled)`; `z_seg = np.rot90(previous z_seg, k)` → `segment_pivot` → `find_cross` ×2 → `measure_pivot` → `measure_xpander` → faults. Status: `ok` when pivot, both crosses and the Xpander are found; `partial` when the pivot succeeded but something else is missing; `failed` otherwise.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("phi,k", [(0.75, 0), (-0.5, 2)])
def test_end_to_end_synthetic(phi, k):
    z, t = make_scan(rotation_deg=phi, quarter_turns=k, slope_x=0.001, slope_y=-0.0015)
    r = analyse_scan(z, Config(), "syn")
    m = r.metrics(Config())
    assert r.status == "ok" and not r.faults.faulty
    assert ((m["rotation_deg"] - t.rotation_deg + 180) % 360 - 180) == pytest.approx(0, abs=0.03)
    assert m["pivot_height_diff_um"] == pytest.approx(18.1, abs=0.02)
    assert (m["cross1_x_px"], m["cross1_y_px"]) == pytest.approx(t.cross1_xy_px, abs=0.3)
    assert m["xpander_rx_um"] == pytest.approx(820, rel=0.003)

def test_global_offset_does_not_change_results():
    z, _ = make_scan(rotation_deg=0.5)
    a, b = analyse_scan(z, Config()).metrics(Config()), analyse_scan(z + 100.0, Config()).metrics(Config())
    for key in ("pivot_height_diff_um", "xpander_rx_um", "cross2_x_px", "rotation_deg"):
        assert a[key] == pytest.approx(b[key], abs=1e-6)

def test_nan_dropouts_are_tolerated():
    z, _ = make_scan(nan_fraction=0.01)
    r = analyse_scan(z, Config())
    assert r.status == "ok" and r.metrics(Config())["pivot_height_diff_um"] == pytest.approx(18.1, abs=0.03)

def test_constant_scan_fails_cleanly():
    r = analyse_scan(np.zeros((300, 300)), Config(), "flat")
    assert r.status == "failed" and r.error

def test_noisy_dome_is_faulty():
    z, _ = make_scan(xpander_noise_um=0.2)
    r = analyse_scan(z, Config())
    assert "xpander_surface_noisy" in r.faults.geometric and r.faults.faulty

@pytest.mark.slow
def test_dataset_applies_statistics(tmp_path):
    for i in range(6):
        np.save(tmp_path / f"{i}.npy", make_scan(seed=i, rx_um=820 + i, ry_um=840)[0])
    np.save(tmp_path / "6.npy", make_scan(rx_um=950, ry_um=840)[0])
    res = analyse_dataset(discover_scans(tmp_path), Config())
    assert "xpander_rx_um_outlier" in res[-1].faults.statistical and res[0].debug is None
```

- [ ] **Step 2: Run to verify failure** → FAIL.
- [ ] **Step 3: Implement `pipeline.py`; update `__init__.py`.**
- [ ] **Step 4: Run tests** — `py -m pytest tests/test_pipeline.py -v` → PASS; then the whole suite `py -m pytest -m "not realdata"` → PASS.
- [ ] **Step 5: Commit** — `feat: end-to-end scan and dataset pipeline`.

---

### Task 13: CSV report and diagnostic figures

**Files:**
- Create: `teramount_analysis/report.py`, `teramount_analysis/figures.py`, `tests/test_report.py`

**Interfaces:**
- Consumes: `ScanResult`, `METRIC_COLUMNS`, `Frame`.
- Produces:
  - `report.CSV_COLUMNS = ("file", "status", "error", *METRIC_COLUMNS, "geometric_flags", "nominal_flags", "statistical_flags", "faulty")`.
  - `report.write_csv(results, path: Path, config) -> None` — `csv` module; floats formatted with up to 6 significant digits; NaN → empty cell; flags joined with `;`; `faulty` → `yes`/`no` (empty for failed rows); creates parent folders.
  - `report.summary_table(results) -> str` — fixed-width console table: file, status, height diff, Rx, Ry, rotation, tilt, flags.
  - `figures.save_scan_figure(result, path: Path, config) -> None` — `matplotlib.use("Agg")` before importing pyplot; 2×3 panels: (1) full leveled scan, original frame, with plane outlines (pulled-back masks), red circles at the cross centres, the Xpander aperture circle and the rotation edge lines; (2) Pivot close-up (canonical) with plane-1/plane-2 contours, cross contours and red circles; (3) Xpander close-up with aperture and apex; (4) fit residual map (diverging colormap, symmetric limits ±3·rms); (5) profiles through the apex along u and v with the fitted curves; (6) text panel: key numbers and flags. Failed scans get a single-panel figure with the error text. Closes the figure.

- [ ] **Step 1: Write the failing tests**

```python
def test_csv_header_and_values(tmp_path): ...   # header == CSV_COLUMNS; row values round-trip; NaN -> ""
def test_failed_row_written(tmp_path): ...      # status "failed", error text, metrics blank, faulty blank
def test_figure_written(tmp_path):
    z, _ = make_scan(rotation_deg=0.5)
    r = analyse_scan(z, Config(), "syn")
    save_scan_figure(r, tmp_path / "syn.png", Config())
    assert (tmp_path / "syn.png").stat().st_size > 20_000
```

- [ ] **Step 2: Run to verify failure** → FAIL.
- [ ] **Step 3: Implement `report.py` and `figures.py`.**
- [ ] **Step 4: Run tests** → PASS; open one generated PNG and confirm the panels look right.
- [ ] **Step 5: Commit** — `feat: CSV report and per-scan diagnostic figures`.

---

### Task 14: Command-line interface and README

**Files:**
- Create: `teramount_analysis/cli.py`, `run.py`, `README.md`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `discover_scans`, `analyse_dataset`, `write_csv`, `summary_table`, `save_scan_figure`, `Config`.
- Produces:
  - `cli.build_parser() -> argparse.ArgumentParser` — `--data PATH` (required; folder or `.npy`), `--out DIR` (default `results`), `--name NAME` (default: the data folder's name), `--pixel-size UM` (0.252), `--z-scale F` (1.0), `--no-tilt-correction`, `--no-rotation-correction`, `--no-figures`, `--nominal-step UM`, `--nominal-radius UM`, `--log-level {DEBUG,INFO,WARNING}` (INFO).
  - `cli.config_from_args(args) -> Config`.
  - `cli.main(argv: Sequence[str] | None = None) -> int` — writes `<out>/<name>_results.csv` and `<out>/figures/<name>/<stem>.png`; prints `summary_table` and output paths; exit 0 on success, 1 when every scan failed, 2 for a missing/invalid `--data` (message on stderr, no traceback).
  - `run.py`: `from teramount_analysis.cli import main` / `raise SystemExit(main())`.

- [ ] **Step 1: Write the failing tests**

```python
def test_cli_runs_on_folder(tmp_path):
    data = tmp_path / "scans"; data.mkdir()
    np.save(data / "0.npy", make_scan()[0]); np.save(data / "1.npy", make_scan(rotation_deg=0.5)[0])
    assert main(["--data", str(data), "--out", str(tmp_path / "out"), "--name", "t"]) == 0
    rows = list(csv.DictReader(open(tmp_path / "out" / "t_results.csv")))
    assert [r["file"] for r in rows] == ["0.npy", "1.npy"] and all(r["status"] == "ok" for r in rows)
    assert (tmp_path / "out" / "figures" / "t" / "1.png").exists()

def test_cli_missing_path_exit_2(tmp_path, capsys):
    assert main(["--data", str(tmp_path / "nope")]) == 2 and "not found" in capsys.readouterr().err.lower()

def test_cli_overrides_reach_config():
    args = build_parser().parse_args(["--data", "x", "--pixel-size", "0.5", "--nominal-step", "17"])
    c = config_from_args(args)
    assert c.pixel_size_um == 0.5 and c.nominal_pivot_step_um == 17
```

- [ ] **Step 2: Run to verify failure** → FAIL.
- [ ] **Step 3: Implement `cli.py` and `run.py`; write `README.md`** — sections: Overview; Requirements & installation (`py -m pip install -r requirements.txt`; note `python` vs `py`); Quick start (both task commands); **Loading other datasets** (folder, single file, `--pixel-size`, `--z-scale`, expected array format: 2-D heights in µm, `.npy`); Outputs (CSV column guide grouped by element, figure panels); Python API (`analyse_file`); Running tests (`py -m pytest`, `-m "not slow and not realdata"`); Project layout; Design notes (the builder calls listed under File Structure); Assumptions & limitations (heights in µm, rotation search ±10° plus quarter turns, same chip family).
- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Commit** — `feat: command-line interface and README`.

---

### Task 15: Real-data validation, results generation, fault analysis

**Files:**
- Create: `tests/test_real_data.py`, `results/task1_results.csv`, `results/task2_results.csv`, `results/figures/**`
- Modify (only if justified below): `teramount_analysis/config.py`

**Interfaces:**
- Consumes: `analyse_dataset`, the CLI, the data folders `15_files_task_1/`, `15_files_task_2/`.

- [ ] **Step 1: Write the real-data tests** (module marked `realdata` and `slow`; `pytest.skip` when the folders are absent; module-scoped fixtures `t1_results`/`t2_results` run `analyse_dataset` once per folder and return `list[ScanResult]`; `t1`/`t2` are the matching lists of `result.metrics(Config())` dicts)

```python
APPLIED_ROTATION = [1.0, 0, -0.25, 0.5, -1.0, 0.75, -0.75, 0.25, -0.5, 1.0, 0, -0.25, 0.5, -1.0, 0.75]
NOISY_XPANDER = {("t1", 6), ("t2", 3), ("t2", 13)}
NOISY_PIVOT = {("t1", 6), ("t2", 7)}

def test_all_scans_analysed(t1, t2): ...            # every status == "ok"
def test_task1_unrotated(t1): ...                   # |rotation_deg| < 0.03 for all 15
def test_task2_rotation_matches_applied(t1, t2):
    for i in range(15):
        d = t2[i]["rotation_deg"] - t1[i]["rotation_deg"]
        assert d == pytest.approx(APPLIED_ROTATION[i], abs=0.03)
def test_task2_matches_task1_after_correction(t1, t2):
    for i in range(15):
        a, b = t1[i], t2[i]
        if ("t1", i) not in NOISY_PIVOT and ("t2", i) not in NOISY_PIVOT:
            assert b["pivot_height_diff_um"] == pytest.approx(a["pivot_height_diff_um"], abs=0.03)
            for n in (1, 2):   # canonical centres coincide (both frames rotate about the array centre)
                assert (b[f"cross{n}_u_px"], b[f"cross{n}_v_px"]) == pytest.approx(
                    (a[f"cross{n}_u_px"], a[f"cross{n}_v_px"]), abs=0.5)
        tol = 0.01 if {("t1", i), ("t2", i)} & NOISY_XPANDER else 0.003
        assert b["xpander_rx_um"] == pytest.approx(a["xpander_rx_um"], rel=tol)
def test_planted_faults_flagged(t1_results, t2_results):
    flags = lambda r: set(r.faults.geometric)
    assert {"plane1_noisy", "plane2_noisy", "xpander_surface_noisy"} <= flags(t1_results[6])
    assert "xpander_surface_noisy" in flags(t2_results[3]) and "xpander_surface_noisy" in flags(t2_results[13])
    assert {"plane1_noisy", "plane2_noisy"} <= flags(t2_results[7])
    noisy = {"plane1_noisy", "plane2_noisy", "xpander_surface_noisy"}
    assert not (noisy & flags(t2_results[6]))       # clean twin of T1-6
    assert not (noisy & flags(t1_results[3])) and not (noisy & flags(t1_results[13])) and not (noisy & flags(t1_results[7]))
```

- [ ] **Step 2: Run** — `py -m pytest tests/test_real_data.py -v` → PASS. When a test fails, find the root cause in the pipeline. Do not loosen a tolerance or a `Config` limit just to pass; the only allowed `Config` change is the nominal spec being re-estimated as the median of the clean files, if the final pipeline's median differs from the defaults by more than 10 % of the tolerance. Record any such change in the README.

- [ ] **Step 3: Generate the deliverables** — `py run.py --data 15_files_task_1 --name task1` and `py run.py --data 15_files_task_2 --name task2` → `results/task1_results.csv`, `results/task2_results.csv`, 30 figures.

- [ ] **Step 4: Inspect** — look at all 30 figures and the flag columns. For every flagged file, and for anything else that looks unusual (e.g. the Rx/Ry asymmetry of files 1, 12, 14), write a short evidence note (file, element, numbers, figure) into `results/fault_analysis.md`. This becomes the source for ANSWERS.md.

- [ ] **Step 5: Commit** — `test: real-data validation; add results and fault analysis`.

---

### Task 16: ANSWERS.md

**Files:**
- Create: `ANSWERS.md`, `docs/figures/*.png` (a few explanatory figures copied or produced from results)

- [ ] **Step 1: Write ANSWERS.md**, answering every assignment question in order, each with numbers from the CSVs, a figure where it helps, and a short plain-language "why":
  - **Task 1:** element labeling explained step by step; crosses removed, with the measured bias (mean and max of `pivot_height_diff_with_crosses_um − pivot_height_diff_um`); the cross-centre table (px and µm); the radius-of-curvature method in depth (leveling, apex search, valley-based aperture, quadric model and why it absorbs tilt, Rx = −1/(2c3), iteration, units, sphere and profile cross-checks, paraboloid vs sphere agreement); figure of merit (nRMS and R², plus the 95 % CI and aperture stability) with the per-file table; the noisier-Xpander answer, citing T1-6 against its clean twin T2-6; faulty files with evidence.
  - **Task 2:** tilt and rotation per file (table) with the validation against the applied rotations (errors); the tilt/rotation algorithm in depth (RANSAC base plane; Canny + Hough + sub-pixel mid-level crossings + weighted median; why the gradient-peak method was rejected; quarter-turn orientation from the ramp; never measuring interpolated data); labeling and parameters (tables); the same grading applied, and whether it is still good: R² and RMS penalise noise even when R is right (T2-3 and T2-13 vs their twins), and the rotation interpolation lowers RMS for the same chip (cite RMS T1 vs T2 for clean twins); proposed better grading (CI of R + aperture stability + twin consistency); differences between the datasets (rotation and tilt values, planted faults moved); faulty files with evidence.
  - Assumptions and limitations; how to reproduce each number (commands).
- [ ] **Step 2: Check** — every question in the .docx has an answer, and every number matches the CSVs (recompute a few by hand from the CSV).
- [ ] **Step 3: Commit** — `docs: answers to the assignment questions`.

---

### Task 17: AI usage disclosure and final quality pass

**Files:**
- Create: `AI_USAGE.md`
- Modify: `README.md` (link the answers and AI usage files)

- [ ] **Step 1: Extract the candidate's prompts** verbatim and in order from the Claude Code session transcripts in `C:\Users\LENOVO\.claude\projects\C--Users-LENOVO-Downloads-Teramount-Home-Assignment\*.jsonl`: messages with `type == "user"` whose content is human-typed text (skip tool results and system reminders). Use a throwaway script in the scratchpad, not in the repo.
- [ ] **Step 2: Write AI_USAGE.md** — tools: Claude Code (model Claude Opus 5.5) for data exploration, design, implementation, tests and drafting docs; ChatGPT for a design review. What each was used for, what the candidate decided and reviewed, the Claude Code prompts verbatim, and the ChatGPT prompts as supplied by the candidate (ask the candidate for them; leave a clearly marked placeholder until they arrive).
- [ ] **Step 3: Final checks** — `py -m ruff check .` clean; `py -m pytest` (full, including realdata) PASS; fresh-clone check: `git clone . %TEMP%\tm_check`, copy the two data folders in, `py -m pip install -r requirements.txt`, and run both README commands successfully.
- [ ] **Step 4: Commit** — `docs: AI usage disclosure; final polish`.
