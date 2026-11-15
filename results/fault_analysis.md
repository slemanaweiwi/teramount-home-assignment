# Fault analysis — evidence notes

Sources:

- `results/task1_results.csv` and `results/task2_results.csv`;
- the figures in `results/figures/`;
- a pixel-by-pixel comparison of each scan with its twin in the other dataset.

Dataset 2 file *i* is the same chip as dataset 1 file *i*, rotated and tilted
(see `tests/test_real_data.py`). So whenever an element is noisy in only one
dataset, its twin gives the noise-free reference.

**Reference values for clean elements** (all files except the flagged ones):

| Metric | Clean range |
|---|---|
| Pivot plane-fit RMS | plane 1: 40–55 nm; plane 2: 20–26 nm |
| Xpander fit RMS | 7–9 nm (nRMS 0.50–0.62 %, R² ≥ 0.9995) |
| Pivot step | 18.114–18.226 µm |
| Radii | Rx 811.7–843.8 µm, Ry 817.9–838.0 µm |
| Cross offset from the channel axis | ≤ 0.61 µm |
| Apex offset from the channel axis | ≤ 0.81 µm |

## Task 1 — file 6.npy: Pivot and Xpander both noisy (faulty)

**Flags:** `plane1_noisy`, `plane2_noisy`, `xpander_surface_noisy` (statistical
outliers on the same metrics).

**Pivot:**

- Plane-fit RMS is 586 / 570 nm, against 40–55 / 20–26 nm on clean planes.
  That's 12–25 times rougher.
- Compared with its clean twin (task 2, file 6), the added height noise is
  **uniform between −1.0 and +1.0 µm**: std 0.583 µm, kurtosis −1.21, minimum
  −1.002, maximum +1.011.
- **The measurement survives the noise.** The step reads 18.214 µm against
  18.171 µm on the clean twin. The 0.043 µm gap is about 2.7 times the
  statistical error expected from ±1 µm noise on a plane of about 1,500 px.
  The cross centres stay on the axis (offset 0.16 µm).

**Xpander:**

- Fit RMS is 231 nm (nRMS 16.0 %, R² 0.765), against 7–9 nm on clean domes.
- The noise is **uniform between −0.4 and +0.4 µm**: std 0.231 µm, kurtosis
  −1.20. It is spatially white (figure: grainy residual map, no pattern).
- **The radius survives the noise.** Rx/Ry = 833.4 / 827.5 µm against
  833.8 / 830.5 µm on the clean twin, within the 95 % CI of ±3.2 µm.

**Verdict:** both elements carry strong surface noise (or measurement
artefacts). On a Pivot whose planes are flat to about 50 nm, ±1 µm of noise
is a defect: the element cannot be trusted as an optical or mechanical
reference.

## Task 2 — file 3.npy: Xpander noisy (faulty)

**Flags:** `xpander_surface_noisy` (statistical `xpander_rms_um_outlier`).

- Fit RMS is 154 nm (nRMS 10.6 %, R² 0.880). The residual map shows a
  periodic grid texture.
- The noise is bounded at ±0.40 µm, like task 1 file 6, but its std is lower
  (154 nm instead of 231) and it is less flat (kurtosis −0.65 instead of −1.2).
  That fits ±0.4 µm uniform noise that was added *before* the dataset's
  synthetic rotation: the bilinear interpolation of the rotation averaged
  neighbouring noise values and left the grid-shaped moiré.
- **Measurement:** Rx/Ry = 826.1 / 820.7 µm against 827.2 / 821.4 µm on the
  clean twin (task 1, file 3), within the CI of ±2.1 µm.
- The Pivot of this file is clean.

## Task 2 — file 7.npy: Pivot noisy (faulty)

**Flags:** `plane1_noisy`, `plane2_noisy` (statistical outliers on the plane
RMS).

- Plane-fit RMS is 396 / 372 nm.
- The noise is bounded at about ±1 µm with a std of 0.36–0.38 µm and a
  kurtosis of about −0.8. That is the same signature: ±1 µm uniform noise added
  before the rotation, then smoothed by the interpolation.
- **Measurement:** the step reads 18.191 µm against 18.182 µm on the clean
  twin (task 1, file 7).
- The Xpander of this file is clean.

## Task 2 — file 13.npy: Xpander noisy (faulty)

**Flags:** `xpander_surface_noisy` (statistical `xpander_rms_um_outlier`).

- Fit RMS is 154 nm (nRMS 10.6 %, R² 0.880), with the same grid texture and
  the same ±0.40 µm bounds as task 2 file 3.
- **Measurement:** Rx/Ry = 829.8 / 822.1 µm against 829.1 / 822.7 µm on the
  clean twin.
- Plane 2 is unusually *smooth* (20 nm against 22–25 nm). That is not a
  defect, so it is not flagged: for roughness and axis offsets the
  statistical check only reports unusually high values.

## Observations that are not faults

- **Files 1, 12 and 14 (both datasets) are a different variant.** The channel
  sits at another position (x ≈ 498–503 px instead of 511–521 px), the
  neighbouring structure on the left is missing, and the raw heights are about
  5 µm lower.
  - Their Xpanders are more strongly curved along x than along y:
    **Ry exceeds Rx by 11.3–15.4 µm** (1.4–1.9 %). Every other file has the
    opposite sign, Rx > Ry by 3.4–7.7 µm (0.4–0.9 %).
  - This is systematic, so it is most likely a die-position or process
    difference. It is within the 5 % astigmatism limit and the nominal radius
    tolerance, so it is reported but not flagged.
- **File 11 has the largest radius** (Rx 843.8 µm, +2.2 % above the median).
  It is within tolerance and not a statistical outlier.
- **The Pivot step is about 0.06 µm higher on files 11–14** (18.21–18.23 µm)
  than on files 0–10 (18.11–18.19 µm). This is a small systematic difference,
  within tolerance.
- **No element is missing**, no cross or apex is off the channel axis (worst
  0.61 / 0.81 µm), and the Pivot planes are parallel within 0.28° in every
  dataset-1 file. In dataset 2 the worst is 0.42°, on the noisy Pivot of
  file 7.
