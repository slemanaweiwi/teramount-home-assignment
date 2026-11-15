# Teramount Home Assignment — Pivot & Xpander analysis

A Python tool that takes 3D topography scans of Teramount chips (`.npy` height
maps), finds the **Pivot** (its two flat planes and their two crosses) and the
**Xpander** (the dome), corrects **tilt** and **in-plane rotation**, and
measures:

- the Pivot height difference (plane 2 − plane 1),
- the centre of each Pivot cross,
- the Xpander radius of curvature along X and Y (µm),
- tilt and rotation angles,
- quality metrics and fault flags for every element.

Results go to a CSV, and every scan gets a diagnostic figure that shows what
was detected. The written answers to the assignment questions are in
[ANSWERS.md](ANSWERS.md). How AI tools were used is in [AI_USAGE.md](AI_USAGE.md).

## Requirements and installation

- Python 3.10 or newer.
- numpy, scipy, scikit-image, matplotlib.

```bash
py -m pip install -r requirements.txt          # Windows ("py" launcher)
python3 -m pip install -r requirements.txt     # Linux / macOS
```

All commands below use `py`. On Linux or macOS write `python3` instead.

## Quick start

Put the two provided folders next to `run.py`, then run:

```bash
py run.py --data 15_files_task_1 --name task1
py run.py --data 15_files_task_2 --name task2
```

Each command analyses every scan in the folder (about 10 s per scan). It
writes:

- `results/task1_results.csv` — one row per scan,
- `results/figures/task1/<scan>.png` — one diagnostic figure per scan,

and prints a summary table.

## Loading other datasets

The program makes no assumption about file names, scan size or where the
channel sits in the image. Point `--data` at any input:

```bash
py run.py --data path/to/new_scans               # every *.npy in the folder, natural order
py run.py --data path/to/new_scans/7.npy         # a single scan
py run.py --data path/to/new_scans --name batch3 --out my_results
```

**Input format:** a NumPy `.npy` file holding one 2-D array of heights.

- Rows are y and columns are x.
- Heights are in µm. Use `--z-scale` if they are stored in another unit, for
  example `--z-scale 0.001` for nm.
- Invalid pixels may be `NaN`.
- Pickled objects are refused for safety.

| Option | Meaning |
|---|---|
| `--data PATH` | Folder of `.npy` scans, or one `.npy` file (required). |
| `--out DIR` | Output folder (default `results`). |
| `--name NAME` | Name for the outputs (default: the data folder's name). |
| `--pixel-size UM` | Lateral pixel size in µm (default 0.252). Every size setting scales with it. |
| `--z-scale F` | Multiply stored heights by F to get µm (default 1). |
| `--no-tilt-correction` | Remove only a constant offset, keep the tilt. |
| `--no-rotation-correction` | Do not measure or undo the in-plane rotation. |
| `--no-figures` | Skip the figures (faster). |
| `--nominal-step UM`, `--nominal-radius UM` | Nominal spec used by the "out of spec" checks. |
| `--log-level` | `DEBUG`, `INFO` (default) or `WARNING`. |

Exit code:

- **0** — the run completed.
- **1** — every scan failed.
- **2** — the data path is missing or invalid.

One bad scan never stops a run: it gets a row with `status = failed` and the
reason in `error`.

### Python API

```python
from teramount_analysis import Config, analyse_file

cfg = Config()                                  # or Config(pixel_size_um=0.3, ...)
result = analyse_file("15_files_task_2/3.npy", cfg)
m = result.metrics(cfg)                         # same keys as the CSV columns
print(result.status, m["pivot_height_diff_um"], m["xpander_rx_um"], result.faults)
```

`analyse_scan(z, cfg)` takes a 2-D NumPy array of heights in µm directly. An
array that is not a usable height map gives a `failed` result with the reason,
just like an unreadable file.

## What it does

1. **Tilt.** The base, the large flat surface around the structures, is found
   with RANSAC on the flat pixels and refined with a robust plane fit. It is
   then subtracted, so every height is relative to the base.
2. **Rotation.** The long straight edges of the structures are measured with
   sub-pixel precision: Canny, then Hough segments, then a mid-level crossing
   on every row or column. The rotation is the median of their angles.
3. **Orientation and Pivot.** Plane 2 is the highest flat plateau lying fully
   inside the scan. The direction of its ramp gives the channel orientation.
   Plane 1 is the first large plateau reached down the ramp.
4. **Crosses.** Each is a plus-shaped region etched into its plane. Its centre
   is the depth-weighted centroid of the original pixels.
5. **Pivot height difference.** Both planes are fitted robustly with the
   crosses removed, and the difference is evaluated at the plane-2 centre.
6. **Xpander.** The apex is found first. Rays are cast to the valley that
   separates it from the neighbouring dome, and a quadric surface is fitted in
   80 % of that radius. This gives Rx = −1/(2c₃) and Ry = −1/(2c₄), plus a
   sphere fit and profile fits as cross-checks.
7. **Faults.** Three separate layers:
   - **geometric:** a missing element, a noisy surface, an element off the
     channel axis;
   - **nominal:** a value outside the nominal spec;
   - **statistical:** an outlier relative to the other scans in the run. For
     roughness and axis offsets only unusually high values count: an
     unusually smooth plane is not a defect.

   Limits of the analysis itself, such as a rotation that could not be
   measured, are reported as **warnings**. They never make a scan faulty.

Masks are found on a rotation-corrected (resampled) image. **All
measurements use the original, non-interpolated pixels**, with their
coordinates transformed into the corrected frame.

[ANSWERS.md](ANSWERS.md) explains each step in depth, with the numbers.

## Outputs

### CSV columns

**Conventions:**

- `x` is the column and `y` the row of the original scan. The origin is the
  centre of the top-left pixel. µm = px × pixel size.
- `u`, `v` are the same in the rotation-corrected frame.
- `rotation_deg` is positive counter-clockwise as displayed (same convention as
  `scipy.ndimage.rotate`).
- `xpander_principal_angle_deg` is the direction of R1, the more strongly
  curved principal direction, measured from the chip x axis, also
  counter-clockwise, in (−90°, 90°]. About 0° means R1 lies along x; about
  ±90°, along y.
- Empty cell = not available.

| Group | Columns |
|---|---|
| Identity | `file`, `status` (`ok` / `partial` / `failed`), `error`, `warnings` (limits of the analysis, e.g. `rotation_not_measured`; never a fault) |
| Tilt | `tilt_x_deg`, `tilt_y_deg` (slope angles along x and y), `tilt_total_deg`, `tilt_azimuth_deg`, `base_rms_um` |
| Rotation | `rotation_deg`, `rotation_se_deg` (standard error), `rotation_lines` (edges used) |
| Pivot | `pivot_height_diff_um` (crosses excluded), `pivot_height_diff_with_crosses_um` (for comparison), `plane1_rms_um`, `plane2_rms_um`, `plane_parallelism_deg` |
| Crosses (1 = plane 1, 2 = plane 2) | `crossN_x_px`, `crossN_y_px`, `crossN_x_um`, `crossN_y_um`, `crossN_u_px`, `crossN_v_px`, `crossN_depth_um`, `crossN_axis_offset_um` |
| Xpander position | `xpander_apex_x_px`, `xpander_apex_y_px`, `xpander_apex_u_px`, `xpander_apex_v_px`, `xpander_apex_z_um`, `xpander_apex_axis_offset_um` |
| Xpander curvature | `xpander_rx_um`, `xpander_ry_um`, `xpander_rx_ci95_um`, `xpander_ry_ci95_um`, `xpander_r1_um`, `xpander_r2_um`, `xpander_principal_angle_deg` |
| Xpander fit quality | `xpander_rms_um`, `xpander_nrms_pct` (RMS / sag), `xpander_r_squared`, `xpander_sag_um`, `xpander_aperture_radius_um`, `xpander_stability_pct` |
| Xpander cross-checks | `xpander_r_sphere_um`, `xpander_rx_profile_um`, `xpander_ry_profile_um` |
| Faults | `geometric_flags`, `nominal_flags`, `statistical_flags` (`;`-separated), `faulty` (`yes` when a geometric or nominal check failed) |

### Figures

Each figure (`results/figures/<name>/<scan>.png`) has six panels:

1. The whole leveled scan, with the detected planes, the crosses (red circles),
   the Xpander aperture, and the edges used for the rotation estimate.
2. A close-up of the Pivot with plane 1, plane 2 and the cross outlines.
3. A close-up of the Xpander with the fitted aperture.
4. The Xpander fit residuals.
5. Height profiles through the apex, with the fitted curves.
6. The key numbers and flags.

## Tests

```bash
py -m pip install -r requirements-dev.txt
py -m pytest                                   # everything (~13 min, includes the real data)
py -m pytest -m "not slow and not realdata"    # quick run (~4 min)
py -m ruff check .                             # lint
```

The tests run the analysis on **synthetic scans with known ground truth**:
`tests/synthetic.py` generates scans with a chosen tilt, rotation, noise,
radii, missing crosses and so on. When the provided data folders are present,
`tests/test_real_data.py` also checks the results on the real scans.

## Project layout

```
run.py                     command-line entry point
teramount_analysis/
  config.py                all tunable parameters (physical units)
  io.py                    finding and loading scans
  surface.py               NaN filling, smoothing, slope, flatness
  fitting.py               plane / RANSAC / quadric / sphere / circle fits
  tilt.py                  base plane and leveling
  rotation.py              rotation from straight edges
  frame.py                 original <-> rotation-corrected coordinates
  pivot.py                 Pivot planes, orientation, height difference
  crosses.py               cross detection and centres
  xpander.py               apex, aperture, curvature, figures of merit
  results.py               per-scan result and the CSV metric columns
  faults.py                geometric / nominal / statistical checks
  pipeline.py              analyse_scan / analyse_file / analyse_dataset
  report.py, figures.py    CSV, console summary, diagnostic figures
  cli.py                   argument parsing
tests/                     pytest suite and the synthetic-scan generator
results/                   generated CSVs and figures
docs/design.md             design document; docs/implementation-plan.md: build plan
```

## Design notes

- **Physical units.** Every tunable parameter is in `Config`, with no pixel
  coordinates or file-specific values. Every size (of a feature, a search
  region or a filter) is in µm, so another resolution only needs
  `--pixel-size`; the tests also run the whole pipeline at 0.35 and
  0.5 µm/px. The one setting in pixels is the straight-edge residual, a
  sub-pixel precision limit that belongs to the sampling, not to the chip.
- **Result types.** Each result type lives next to the code that produces it
  (`TiltResult` in `tilt.py`, and so on). `results.py` defines the CSV columns
  once.
- **Labeling.** Elements are found from their shape and their relationships:
  the highest complete plateau, the ramp direction, the first plateau down the
  ramp, the first dome along the axis. Never from fixed positions.
- **Resampling.** Resampled images are used only to locate things. Plane fits,
  cross centres and the dome fit use the original pixels.

## Assumptions and limitations

- Heights are in µm, or are converted with `--z-scale`.
- The scans show the same chip family: a Pivot with a ramp and an Xpander on
  the low side of the ramp.
- The fine rotation search covers ±10° around each multiple of 90°; the
  quarter turn itself (0°, 90°, 180° or 270°) is detected from the ramp
  direction. A rotation further than 10° from a quarter turn is not
  supported: no straight edge is found, and the scan is analysed as
  unrotated with the warning `rotation_not_measured`.
- A channel cut by the image border, or by the empty corners of a rotated
  scan, is reported as not found with the reason. It is never measured on
  part of the element.
- With `--no-tilt-correction` the tilt stays in the data. The dome boundary
  is found from height differences, so on a tilted scan the Xpander fit area
  shrinks, and on a strongly tilted one the dome can be reported as not found.
- The nominal spec (Pivot step 18.18 ± 0.30 µm, radius 826 ± 30 µm) was
  estimated from the clean provided scans. Override it for other designs.
