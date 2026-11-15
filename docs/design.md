# Teramount Home Assignment — Design

Date: 2026-11-15
Status: draft for approval

## 1. Intent and why

The candidate is applying for a **software engineer** position at Teramount. The
assignment (`Teramount Home Assignment.docx`) asks for a Python tool that takes
3D topography microscope scans of Teramount chips, labels the two optical
elements of a channel (the **Pivot** and the **Xpander**), extracts their
geometric parameters, corrects tilt/rotation in a second dataset, and flags faulty
elements.

The submission is graded on **coding standards** as well as on results, and the
code **will be re-run by Teramount on a hidden dataset**. The candidate will
likely have to walk through and defend the code in a follow-up interview, so
every algorithmic choice must have a short, plain-language justification that is
written down.

Success looks like:
- A reviewer runs one documented command on any folder of `.npy` scans and gets
  a correct CSV plus diagnostic images, without editing code.
- Results are accurate and self-consistent across the 30 provided files, and the
  per-file diagnostic images make it visually obvious the labeling is right.
- The code reads like production code: small modules, typed, documented, tested,
  no magic numbers buried in functions.
- The answers file answers every question in the assignment, with numbers and
  reasoning, in language the candidate can repeat in an interview.

## 2. Goals, non-goals, anti-goals

Goals
- One pipeline handles both tasks; Task 1 data simply yields ~0 tilt/rotation.
- Works on unseen data: channel not centered, different absolute heights,
  different tilt/rotation, missing/faulty elements.
- Every reported number has an accompanying quality metric.
- Never crashes on a bad file: a file that fails is reported in the CSV with a
  reason, and the run continues.

Non-goals
- GUI, web service, database, packaging to PyPI.
- Analysing the supporting structure, the neighbouring (partial) channels at the
  image edges, or the isolated rectangle with a cross near the bottom of the scan
  (≈ rows 2150–2400). The assignment says "you will deal with this channel
  structure only".
- Machine learning / training-based segmentation (15 files per task is far too
  few, and it would be hard to defend).

Anti-goals (would be a failure even if numbers look right)
- Hard-coded pixel coordinates, file-specific thresholds, or anything tuned to
  these 30 files that would break on the hidden dataset.
- A single long script with global state.
- Results without evidence (no diagnostic plots / no quality metric).
- Answers the candidate cannot explain.

## 3. What the data looks like (from exploration of all 30 files)

- Each file: `float64` array, shape `(2840, 1000)` (rows = Y, cols = X), no NaNs.
  The hidden dataset may differ in shape — never assume it.
- Values are heights in **µm**; lateral pixel pitch **0.252 µm** (given).
- Layout (top → bottom): a band of supporting structure; the **Xpander** dome
  centered around row ≈ 380 (≈ 500 px ≈ 126 µm wide, only ≈ 2.7 µm sag),
  flanked by half-domes of neighbouring channels at the left/right edges; the
  **Pivot** directly below it (rows ≈ 730–910): a flat lower plane (plane 1,
  ≈ 21.4 µm) with a small recessed cross, a ramp, and a flat upper plane
  (plane 2, ≈ 39.4 µm) with a second recessed cross (crosses are ≈ 2 µm deep);
  two deep slots on either side; then a large flat base (≈ 8.4 µm) for the
  rest of the image, containing an isolated rectangle with a cross.
- Pivot height difference is ≈ 18.0 µm in almost all files (rough estimate).
- Files 1, 12, 14 (both tasks) are shifted / have a different surrounding layout
  and all heights ≈ 5 µm lower → absolute heights cannot be used for
  thresholds; everything must be relative to the local base.
- Task 2 scans show visible in-plane rotation (order of ~1°) and a height
  gradient (tilt) across the base.
- Early suspect for a faulty element: Task 1 file 6 (pivot step ≈ 17.5 µm vs
  ≈ 18.0 µm, slightly larger dome sag). Full fault analysis is part of the work.

## 4. Deliverables (the submission folder)

```
Teramount_Home_Assignment/
├── README.md                 # setup, how to run, how to load other datasets
├── ANSWERS.md                # answers to every question, with numbers & figures
├── AI_USAGE.md               # tool used (Claude Code, Claude Opus 5.5) + prompts
├── requirements.txt          # pinned: numpy, scipy, pandas, matplotlib, scikit-image, pytest
├── pyproject.toml            # project metadata, tool config (ruff, pytest)
├── run.py                    # thin CLI entry point
├── teramount_analysis/       # the package
├── tests/                    # pytest suite (synthetic + real-data smoke tests)
├── results/
│   ├── task1_results.csv
│   ├── task2_results.csv
│   └── figures/<task>/<file>.png   # one diagnostic figure per scan
└── docs/design.md            # this document
```

The assignment asks for "a python script"; a small package plus a single
`run.py` entry point satisfies that while showing structure. (My call.)

## 5. Command-line interface

```
py run.py --data 15_files_task_1 --out results --name task1
py run.py --data 15_files_task_2 --out results --name task2
py run.py --data some/folder/scan.npy          # single file also accepted
```

Options: `--pixel-size 0.252` (µm), `--no-correction` (skip tilt/rotation
correction), `--no-figures`, `--log-level`. `--data` accepts a folder (all `*.npy`
in natural numeric order) or a single file. All tunable parameters live in one
`Config` dataclass expressed in **physical units (µm, degrees)**, not pixels,
so they transfer to scans with a different size.

## 6. Architecture

```
teramount_analysis/
├── config.py        # Config dataclass: pixel size, tolerances, in µm
├── io.py            # discover & load .npy files, validate (2D, finite)
├── leveling.py      # tilt: robust base-plane fit & removal; rotation: angle estimation & correction
├── segmentation.py  # locate channel → Pivot ROI, plane 1/2 masks, crosses, Xpander ROI/mask
├── pivot.py         # plane fits, height difference, cross centers
├── xpander.py       # surface fit, radius of curvature X/Y, figures of merit
├── faults.py        # per-file checks + dataset-level outlier detection
├── models.py        # dataclasses for results (PivotResult, XpanderResult, ScanResult, ...)
├── report.py        # CSV writer, diagnostic figures
└── pipeline.py      # analyse_scan(array, config) -> ScanResult; analyse_dataset(path)
```

Rules: pure functions on arrays wherever possible; no I/O outside `io.py` and
`report.py`; type hints and docstrings (NumPy style) on every public function;
`logging`, not `print`; a failure inside one scan becomes a `ScanResult` with
`status="failed"` and `error=<message>`.

## 7. Algorithms

All coordinates in outputs are reported in **both pixels (of the original,
uncorrected scan) and µm**; the CSV states the convention (origin = top-left
pixel center, X → right/columns, Y → down/rows).

### 7.1 Tilt correction (Task 2; also run on Task 1)

1. Estimate the **base plane**: the largest flat region in the scan (the base
   that covers most of the lower part of the image). Select candidate pixels
   with low local gradient, then fit `z = a·x + b·y + c` with a robust method
   (RANSAC or iteratively re-weighted least squares with sigma clipping) so the
   raised structures don't bias it.
2. Report tilt as angles: `tilt_x = atan(a)`, `tilt_y = atan(b)` (x, y in µm,
   so the slopes are dimensionless), and total tilt `atan(√(a²+b²))`, in
   degrees.
3. Subtract the plane. After this, all heights are relative to the base
   (base ≈ 0), which also removes the 5 µm absolute offset between file groups.

Justification: a tilt is a linear term added to every height; the base is the
largest, flattest, most trustworthy reference surface on the chip.

### 7.2 Rotation correction

1. On the leveled scan, estimate the dominant orientation of the long straight
   structure edges (channel walls, slot edges, band edges). **Updated after data
   exploration:** the projection-sharpness search was tried and rejected (on
   unrotated Task 1 scans it jumped between 0° and −0.5° because different
   walls disagree slightly). The method is now: Canny edges → probabilistic
   Hough to find candidate straight segments (±10° of horizontal/vertical) →
   each segment re-measured at sub-pixel precision (the mid-level crossing of
   the step on every row/column; the gradient-peak variant was rejected
   because of pixel-locking bias) → line fit, reject non-straight lines →
   length-weighted median of the line angles, with its standard error.
   Measured accuracy on the provided data: ≤ 0.018° against the known applied
   rotations. Validation: the Xpander apex and both crosses must lie on the
   corrected channel axis (geometric fault flags).
2. Report rotation in degrees (sign convention documented: positive =
   counter-clockwise as displayed).
3. Apply the correction by rotating **coordinates**, not by resampling the data
   used for fitting: segmentation runs on a rotated copy
   (`scipy.ndimage.rotate`, bilinear), but the final plane fits and Xpander fit
   use original pixel values with their rotated coordinates, so interpolation
   doesn't smooth the dome or the crosses. Cross centers are mapped back to the
   original pixel frame for reporting (also reported in the corrected frame).

### 7.3 Labeling the channel (both tasks)

Everything is relative to the leveled base and expressed in µm.

1. **Pivot top (plane 2)**: the highest large flat region. Threshold on height
   relative to base and low gradient; connected components; discard components
   touching the image border (the partial neighbouring channels) and too-small
   ones; choose the remaining component that is largest/most central. This
   anchors the channel; no fixed coordinates.
2. **Pivot ROI**: grown from plane 2 to the enclosing raised "tooth" bounded by
   the two deep slots (found as the nearest strong downward steps left/right).
3. **Plane 1**: the flat plateau inside the pivot ROI on the far side of the
   ramp from plane 2 (height cluster ≈ plane 2 − ~18 µm in the provided data but
   found by clustering flat pixels by height, not by a fixed value).
4. **Crosses**: inside each plane mask, fit a robust plane, compute residuals;
   the cross is the connected recessed region (residual < −k·σ) with a cross-like
   shape (two perpendicular arms; checked via area, bounding-box aspect and
   moment-based symmetry). Center = intersection of the two arm axes, refined to
   sub-pixel by matching a cross template / centroid of the cleaned mask.
5. **Xpander**: search above the pivot along the channel axis. **Updated
   after data exploration:** neighbouring Xpanders meet at gentle valleys (like
   a microlens array), not at steep edges, so a "no steep edges" region does
   not isolate one dome. The apex is the first prominent peak (≥ 0.5 µm) of
   the smoothed height profile walking away from the Pivot along the axis;
   rays are cast from the apex until the surface stops descending (the valley
   to the neighbour) or meets a steep step; the fit aperture is 80 % of the
   shortest ray, so the fit only sees this dome's surface. The fit is iterated
   (re-centred on the fitted vertex).

6. **Consistency check of the labeling** (several signals, not height alone):
   plane 2 above plane 1 by a plausible step and both flat; one cross found on
   each plane; Xpander apex on the Pivot's channel axis (within tolerance) and
   on the plane-1 side of the ramp; dome is convex with a plausible aperture.
   Any violation → the element is reported as not found / suspicious with the
   reason, never silently accepted.

Each labeled element is drawn on the per-file diagnostic figure (outlines of
plane 1, plane 2, both crosses with centers, the Xpander aperture).

### 7.4 Pivot height difference

- Robust plane fit to plane 1 and plane 2 **with the crosses and a ~2 µm edge
  margin removed**; height difference = (plane 2 − plane 1) evaluated at the
  plane-2 centroid (after leveling the planes should be parallel; their slope
  difference is reported as a check).
- Uncertainty reported as the residual RMS of each plane fit.

**Crosses: removed.** They are recessed alignment marks (~2 µm deep), not part
of the plane surface; including them biases the plane height down by
(cross area fraction × depth). The answers file quantifies the bias by also
computing the difference with crosses included.

### 7.5 Xpander radius of curvature

Primary model — a general paraboloid (the standard paraxial model of a curved
optical surface), fitted by linear least squares on the masked dome:

`z = c0 + c1·x + c2·y + c3·x² + c4·y² + c5·x·y`

- Linear terms absorb any residual tilt.
- Radius of curvature along an axis = `1 / |z''|` = `1 / (2|c3|)` (X) and
  `1 / (2|c4|)` (Y), in µm (x, y converted to µm with 0.252).
- **Rx and Ry are the primary reported result**, because the assignment asks
  for the radius of curvature along the X and Y axes, and after rotation
  correction X/Y are the chip axes. `c5` tells whether the dome's principal axes
  are rotated relative to the chip; principal radii and their orientation
  (eigen-decomposition of the Hessian) are reported as supplementary columns,
  so an astigmatic or twisted dome is detected.

Cross-checks reported alongside:
- exact sphere/ellipsoid-cap fit (non-linear least squares,
  `scipy.optimize.least_squares`) — validates the paraboloid approximation
  (sag/aperture is small so they should agree within <1%);
- 1D circle fits on the X and Y profiles through the apex.

Figures of merit (one for the answer to "how good is your extracted value"):
- RMS residual (µm) and normalised RMS (% of dome sag); R².
- Parameter standard error of R from the fit covariance → 95% CI (bootstrap
  dropped: with ~10⁵ points the covariance estimate is adequate).
- **Aperture stability**: R re-fitted on apertures of 50%…100% of the max
  radius; the spread tells whether the shape is truly spherical/parabolic.
- Residual map shown in the diagnostic figure (structured residuals reveal
  defects; white noise means the model fits).

Noisier Xpander: keep the global surface fit (it averages noise over
~10⁵ pixels, unlike local derivatives), switch to a robust loss (soft-L1 /
Huber), and use bootstrap CIs. Explained in the answers.

### 7.6 Faulty-element detection

Two layers, all thresholds in physical units / robust statistics:
1. **Per-file sanity checks**: missing element, cross not found or misshapen,
   cross off the pivot axis, dome apex off the pivot axis, dome residual
   structure / high normalised RMS, large Rx–Ry asymmetry, plane slope
   mismatch.
2. **Dataset-level outliers**: for each metric, robust z-score using median and
   MAD across the files in the run; |z| > 3.5 flags the file.

These are kept as **separate categories**, because a statistical outlier is
not necessarily a defect and a systematic defect may not be an outlier:
`geometric_flags` (structure violates expected geometry), `nominal_flags`
(measurement outside the nominal spec tolerance), `statistical_flags`
(outlier relative to the other scans in the run). Each is a semicolon-separated
list of reasons, plus an overall `faulty` yes/no column. The CSV and the answers file
discusses each flagged file with its diagnostic figure.

## 8. CSV schema (one row per scan)

`file, status, error, tilt_x_deg, tilt_y_deg, tilt_total_deg, rotation_deg,
pivot_height_diff_um, plane1_rms_um, plane2_rms_um,
cross1_x_px, cross1_y_px, cross1_x_um, cross1_y_um, cross2_x_px, cross2_y_px,
cross2_x_um, cross2_y_um,
xpander_apex_x_px, xpander_apex_y_px, xpander_Rx_um, xpander_Ry_um,
xpander_Rx_ci95_um, xpander_Ry_ci95_um, xpander_rms_um, xpander_nrms_pct,
xpander_r2, xpander_aperture_um, xpander_R_sphere_um,
xpander_R1_um, xpander_R2_um, xpander_principal_angle_deg,
geometric_flags, nominal_flags, statistical_flags, faulty`

Cross 1 = cross on plane 1, cross 2 = cross on plane 2.

## 9. Testing and validation

- **Synthetic scans** (`tests/synthetic.py`): generate a scan with a known base,
  pivot planes, crosses at known positions, a dome with known Rx/Ry, plus known
  tilt, rotation, and noise. Tests assert the pipeline recovers each value within
  tolerance. This is the strongest evidence of correctness.
- Unit tests per module (plane fit, rotation estimation, cross center, curvature
  fit).
- Real-data smoke test: all 30 files run without failure and results fall in
  plausible ranges.
- Consistency check: Task 2 files are the same chips as the Task 1 files with
  the same index (correlation 0.95–0.999), so Task 2 parameters after correction
  should agree with Task 1 values — a strong end-to-end validation of the tilt
  and rotation correction, reported in ANSWERS.md.
- Lint/format with `ruff`.

## 10. Answers file

`ANSWERS.md` answers every question in the order of the assignment, with:
numbers from the CSV, a figure where it helps, and a short "why" in plain
language. Also: what differs between dataset 1 and dataset 2; the faulty files
and why; whether the figure of merit is still good for Task 2 (expected
discussion: the paraboloid's linear terms make R insensitive to residual tilt,
but residual rotation mixes Rx/Ry, so the rotation-invariant principal radii and
the aperture-stability metric matter more there).

## 11. AI usage documentation

`AI_USAGE.md`: tool = Claude Code (model Claude Opus 5.5), what it was used for
(data exploration, design, implementation, tests, drafting answers), and the
candidate's prompts verbatim, in order.

## 12. Calls made by the designer (not decided by the candidate)

- Package + `run.py` instead of one monolithic script.
- One pipeline for both tasks; correction always on (can be disabled).
- Ignore partial neighbouring channels and the isolated bottom rectangle.
- Remove crosses from plane fits.
- Paraboloid fit as the primary curvature method, with sphere + 1D profile
  cross-checks.
- Markdown for README / answers.
- Initialise a local git repository for the work (not pushed anywhere).

- **Orientation range of unseen data**: assume same chip family and microscope
  (Xpander above Pivot, near-vertical channel). Fine rotation search over
  ±10°. Before it, a cheap **coarse orientation check** (0/90/180/270°) using the
  element relationship — the Xpander dome lies on the low-plane side of the
  Pivot ramp — so a flipped/rotated scan is corrected or fails with a clear
  error rather than silently mislabeling. Synthetic tests cover a 180° case.
- **Fault reference**: three independent layers, so detection works even on a
  single hidden file:
  1. structural checks that need no reference (element missing, cross
     misshapen/missing, cross or apex off the channel axis, structured dome
     residuals, Rx/Ry asymmetry, plane slope mismatch);
  2. **nominal spec** values with tolerances in `Config` (pivot step ≈ 18.0 µm,
     nominal R), clearly labeled as "nominal values estimated from the provided
     good files" and overridable from the CLI (`--nominal-step`, etc.);
  3. dataset-level robust z-scores (median/MAD), applied only when the run has
     ≥ 5 successful files.
- Small raised pads on the plane-1 level are masked out like the crosses (only
  the clean plane surface is fitted); plane 1 is the ≈ 21.4 µm level that
  carries the first cross.
- **AI prompts**: exported from the Claude Code session transcripts stored on
  this machine (`~/.claude/projects/...`), user prompts only, verbatim, in
  order; any prompts used with other AI tools must be added by the candidate.
- **Priority order** (deadline: a few days): (1) pipeline + labeling + CSV +
  diagnostic figures, (2) synthetic tests, (3) fault detection, (4) ANSWERS.md /
  README / AI_USAGE.md, (5) cross-checks (sphere, 1D profiles, aperture
  stability). Items in (5) are cut first if time runs short. Synthetic tests
  are written alongside each module, not at the end.
- **External review**: the design was also reviewed with ChatGPT. Accepted:
  labeling consistency check, independent rotation validation, separate fault
  categories, dropping bootstrap. (Dropping Hough was accepted at first; after
  data exploration Hough was kept, but only to propose candidate segments:
  every angle comes from the sub-pixel re-measurement, see §7.2.) Not
  accepted: making principal radii the primary result (the assignment asks
  for X/Y axes explicitly).
- **AI disclosure** lists both tools: Claude Code (exploration, design,
  implementation, tests, docs) and ChatGPT (design review); the candidate
  supplies the prompts they sent to ChatGPT.

## 13. Left to the builder

- Exact RANSAC vs IRLS choice, thresholds' default values (in µm), template
  details for the cross, figure styling.
- Whether Hough or projection search is primary for rotation, as long as both
  agree on the provided data. *(Decided during the build: Hough candidates
  plus sub-pixel re-measurement; the projection search was rejected, §7.2.)*
