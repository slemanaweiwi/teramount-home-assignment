# Answers

All numbers come from `results/task1_results.csv` and
`results/task2_results.csv`. The last section explains how to reproduce them.

Every scan has a diagnostic figure in `results/figures/task1/` and
`results/figures/task2/`. Each figure shows where every element was detected
and how well each fit matches.

**Conventions:**

- Heights are in µm, and every height is relative to the leveled base (base = 0).
- One pixel is 0.252 µm.
- `x` is the column and `y` the row of the original scan, with the origin at
  the centre of the top-left pixel.
- Rotation is positive counter-clockwise as displayed.

---

## Summary

| | Dataset 1 | Dataset 2 |
|---|---|---|
| Pivot height difference | 18.114 – 18.226 µm | 18.114 – 18.224 µm |
| Xpander Rx / Ry | 811.7 – 843.8 / 817.9 – 838.0 µm | same chips, same values (see §2.5) |
| Fit quality of clean domes | RMS 8.0 – 8.9 nm (nRMS 0.55 – 0.62 %) | RMS 7.3 – 8.9 nm (nRMS 0.50 – 0.62 %) |
| Tilt (total) | 0.003 – 0.005° (practically level) | 0.048 – 0.123° |
| Rotation | −0.015 … +0.011° (practically none) | −0.994 … +1.012° (applied: −1 … +1° in 0.25° steps) |
| Faulty files | **6** (Pivot and Xpander noisy) | **3** (Xpander), **7** (Pivot), **13** (Xpander) |

**Validation:** each dataset-2 scan is its dataset-1 twin, rotated and tilted.
After correction, every clean element in dataset 2 matches its twin:

- Pivot height difference within **0.004 µm**;
- radii within **0.017 µm**;
- cross centres within **0.23 px**.

The measured rotations are within **0.0155°** of the applied ones.

---

# Task 1 — Basic labeling and data extraction

## 1.1 How the labeling works

Nothing is located by fixed pixel position. Every element is recognised by
its **shape** and by its **relation to the other elements**, so the code
works wherever the channel sits in the image.

1. **Level the scan.** The base is the large flat surface surrounding the
   structures. The pixels whose local slope is below 0.25 µm/µm (measured on a
   smoothed copy) are flat; RANSAC picks the plane supported by the most of
   them. RANSAC is needed because the structures cover a large part of the
   image, and an ordinary fit would be pulled up by them. A robust
   least-squares fit then refines that plane, and it is subtracted.
2. **Map the flat regions.** On a smoothed copy (median 1.26 µm, i.e. 5 px,
   then Gaussian 1 µm), every pixel with slope below 0.25 µm/µm is "flat".
   The smoothing matters on noisy elements: without it, noise breaks a
   plateau into specks.
3. **Plane 2** (the Pivot's top plane) is the **highest flat plateau lying
   completely inside the image**.
   - Plateaus that touch the border belong to the neighbouring channels, which
     are cut by the image edge, and are ignored.
   - If two complete channels were visible, the one nearest the image centre
     would win.
   - The 23.5 µm block with the cross in the lower part of the scan is lower
     than plane 2 (31 µm), so it is never chosen.
4. **Orientation.** The Pivot has a gentle ramp on one side of plane 2 and
   steep walls on the others. The average downhill direction of the
   moderately sloped pixels next to plane 2 points down the ramp. The side
   walls cancel out and the cliff is too steep to count. If the ramp does not
   point up, the scan is turned in 90° steps until it does, so upside-down or
   sideways scans are handled too.
5. **Plane 1** is found by walking from plane 2 down the ramp. It is the first
   flat plateau that is at least 5 µm lower and larger than 200 µm². Smaller
   plateaus, such as noise specks or the floor of a cross, are walked past.
   The plateau found is U-shaped around the ramp. The raised square pads next
   to it are separate plateaus, so they are automatically excluded.
6. **Crosses.** A plane is fitted to each Pivot plane, and the crosses are the
   regions lying more than 0.6 µm *below* that plane. They are etched (about
   1.7 µm deep), while the pads are raised.
   - A candidate must have a plausible area (5–100 µm²), a cross-like
     *solidity* (0.75–0.97), and a roughly square bounding box.
   - Solidity is area divided by convex-hull area. A plus sign does not fill
     its hull, unlike a square pad or a round pit.
   - When several candidates qualify, the one nearest the channel axis wins.
7. **Xpander.** Walking away from the Pivot along the channel axis, the
   Xpander apex is the **first prominent peak** (≥ 0.5 µm) of the smoothed
   height profile. Its extent is described in §1.4.

**Tests:** the steps are covered by tests on **synthetic scans with known
ground truth**: an off-centre channel, two channels, quarter turns, rotation,
tilt, noise, NaN dropouts, a missing cross, and a dome cut by the border. The
real-data tests check all 30 provided scans.

## 1.2 Pivot height difference — and the crosses

**Method:**

- Each plane is fitted with a robust plane fit on the **original pixels**.
- A 0.5 µm edge margin is excluded, and so is the cross.
- The difference (plane 2 − plane 1) is evaluated at the centre of plane 2. A
  residual tilt common to both planes therefore cancels.
- The two planes are parallel within 0.02–0.13° on every clean file, which
  confirms the leveling.

**Are the crosses relevant? No. They are removed.**

- The crosses are alignment marks etched about 1.7 µm into the surface; they
  are not part of the planes being measured. A plane fit that includes them
  is pulled down by (cross area / plane area) × depth.
- The two planes are affected differently. The cross covers about 13 % of the
  small plane 2 but only about 2 % of plane 1. So the error does not cancel
  in the difference.
- Measured (figure `docs/figures/crosses_bias.png`): keeping the crosses
  lowers the Pivot step by **0.154–0.197 µm** (mean 0.172 µm) in dataset 1.
  That is about 1 % of the step. It is 40 times larger than the measurement
  repeatability (0.004 µm) and half the ±0.30 µm tolerance used for fault
  checks.
- The raised pads are excluded for the same reason.

| File | Step [µm] | Step with crosses kept [µm] |
|---|---|---|
| 0 | 18.140 | 17.986 |
| 1 | 18.173 | 18.011 |
| 2 | 18.185 | 18.024 |
| 3 | 18.121 | 17.955 |
| 4 | 18.114 | 17.944 |
| 5 | 18.134 | 17.967 |
| 6 | 18.214 | 18.017 |
| 7 | 18.182 | 18.015 |
| 8 | 18.148 | 17.970 |
| 9 | 18.116 | 17.943 |
| 10 | 18.144 | 17.973 |
| 11 | 18.221 | 18.041 |
| 12 | 18.219 | 18.027 |
| 13 | 18.207 | 18.038 |
| 14 | 18.226 | 18.054 |

## 1.3 Cross centres

Cross 1 is on plane 1 and cross 2 is on plane 2.

**Method:** each centre is the **depth-weighted centroid of the original
pixels** of the cross. Deeper pixels count more, which makes the result
sub-pixel accurate even though the cross outline is pixelated.

**Accuracy:**

- on synthetic scans, within 0.3 px of the truth;
- on the real twins, within 0.23 px of each other;
- every cross lies on the channel axis within 0.61 µm.

Coordinates are in the original image.

| File | Cross 1 x, y [px] | Cross 1 x, y [µm] | Cross 2 x, y [px] | Cross 2 x, y [µm] |
|---|---|---|---|---|
| 0 | 512.58, 772.71 | 129.17, 194.72 | 512.30, 890.33 | 129.10, 224.36 |
| 1 | 497.83, 785.73 | 125.45, 198.00 | 497.83, 903.44 | 125.45, 227.67 |
| 2 | 511.99, 771.77 | 129.02, 194.49 | 512.21, 889.16 | 129.08, 224.07 |
| 3 | 512.34, 776.55 | 129.11, 195.69 | 511.96, 894.18 | 129.01, 225.33 |
| 4 | 512.93, 775.79 | 129.26, 195.50 | 512.64, 893.49 | 129.19, 225.16 |
| 5 | 510.98, 769.78 | 128.77, 193.98 | 511.00, 887.33 | 128.77, 223.61 |
| 6 | 514.27, 766.46 | 129.59, 193.15 | 514.29, 884.17 | 129.60, 222.81 |
| 7 | 517.27, 766.66 | 130.35, 193.20 | 517.34, 884.16 | 130.37, 222.81 |
| 8 | 516.18, 771.08 | 130.08, 194.31 | 516.40, 888.51 | 130.13, 223.91 |
| 9 | 513.42, 766.67 | 129.38, 193.20 | 513.43, 884.36 | 129.38, 222.86 |
| 10 | 511.81, 770.76 | 128.98, 194.23 | 511.78, 888.18 | 128.97, 223.82 |
| 11 | 521.16, 764.14 | 131.33, 192.56 | 520.89, 881.75 | 131.26, 222.20 |
| 12 | 500.90, 771.70 | 126.23, 194.47 | 500.69, 889.38 | 126.17, 224.12 |
| 13 | 519.96, 762.04 | 131.03, 192.03 | 519.92, 879.67 | 131.02, 221.68 |
| 14 | 503.12, 767.49 | 126.79, 193.41 | 503.14, 885.10 | 126.79, 223.04 |

## 1.4 Xpander radius of curvature — the method in depth

The Xpander is a shallow dome, about 1.45 µm high over a 49 µm radius. Its
radius of curvature is about 820 µm.

**1. Find the apex.** Walk away from the Pivot along the channel axis on a
smoothed copy (Gaussian 2 µm). The apex is the first peak that rises at least
0.5 µm above its surroundings; that requirement rejects bumps and flat bands.
The apex is then refined locally.

**2. Choose the fit area (aperture) automatically.**

- Neighbouring Xpanders form a row, like a microlens array. They meet at
  gentle *valleys*, not at steep edges. Edge detection therefore cannot
  delimit one dome.
- Instead, 72 rays are cast from the apex. A ray stops where the surface
  starts rising again (it has crossed the valley into the neighbouring dome)
  or meets a steep step (the supporting band).
- The fit uses a circle of **80 % of the shortest ray**, which is 48.4–49.0 µm
  on every scan. That keeps it on this dome's own surface.
- In exploration, the fit residual jumped from about 9 nm to 14 nm when the
  circle reached the valleys. The 80 % rule keeps clear of that.

**3. Fit a quadric surface by least squares** to every original pixel inside
the aperture (about 117,000 points). Coordinates are converted to µm, relative
to the apex:

`z = c0 + c1·u + c2·v + c3·u² + c4·v² + c5·u·v`

- **Why this model:**
  - It is the standard paraxial model of a curved optical surface.
  - Over this aperture, a sphere and a parabola differ by at most
    r⁴/(8R³) ≈ 1.5 nm, which is below the noise. The sphere cross-check below
    confirms this.
  - The linear terms c1 and c2 absorb any residual tilt, so a leveling error
    cannot bias the curvature.
  - The cross term c5 allows a dome whose curvature axes are not aligned with
    the image.
- **Radius along each axis.** The curvature along an axis is the second
  derivative, so **Rx = −1/(2·c3)** and **Ry = −1/(2·c4)**. That is exactly
  the radius of the x and y profiles through the vertex. Because u and v are
  in µm, R comes out in µm (pixel size 0.252 µm).
- **Iteration.** The apex is moved to the fitted vertex (where the gradient is
  zero), and the aperture and fit are recomputed. This runs three times, which
  removes any bias from a slightly off-centre start.
- **No interpolation.** The fit always uses the original pixels, never
  resampled ones. Interpolation would smooth the data and change both the
  noise and the residuals.

**4. Cross-checks** (all in the CSV):

- **Principal radii:** the eigenvalues of the Hessian [[2c3, c5], [c5, 2c4]],
  and their direction (the angle of R1 from the chip x axis, counter-clockwise
  like the rotation angle).
- **Exact sphere fit** (geometric least squares): within **0.09 %** of
  (Rx+Ry)/2 on every scan, which confirms the paraxial model.
- **Circle fits to the single x and y profiles through the apex:** within
  0.9 % of Rx and Ry on clean domes, but unstable on noisy ones (see §1.6).

| File | Rx [µm] (95 % CI) | Ry [µm] (95 % CI) | RMS [nm] | nRMS [%] | R² | Aperture stability [%] | Sphere R [µm] |
|---|---|---|---|---|---|---|---|
| 0 | 822.6 ± 0.12 | 817.9 ± 0.12 | 8.6 | 0.59 | 0.9996 | 1.81 | 821.0 |
| 1 | 811.7 ± 0.12 | 827.2 ± 0.13 | 8.9 | 0.62 | 0.9995 | 1.99 | 820.1 |
| 2 | 822.7 ± 0.11 | 818.6 ± 0.11 | 8.2 | 0.56 | 0.9996 | 1.42 | 821.4 |
| 3 | 827.2 ± 0.12 | 821.4 ± 0.12 | 8.9 | 0.61 | 0.9995 | 0.36 | 825.0 |
| 4 | 828.0 ± 0.11 | 823.1 ± 0.11 | 8.3 | 0.57 | 0.9996 | 1.59 | 826.3 |
| 5 | 831.2 ± 0.12 | 826.8 ± 0.12 | 8.7 | 0.60 | 0.9996 | 0.44 | 829.7 |
| **6** | **833.0 ± 3.31** | **827.0 ± 3.26** | **231.4** | **16.22** | **0.7588** | 2.43 | 830.3 |
| 7 | 831.4 ± 0.12 | 824.4 ± 0.12 | 8.4 | 0.58 | 0.9996 | 0.84 | 828.6 |
| 8 | 829.7 ± 0.12 | 824.3 ± 0.12 | 8.7 | 0.60 | 0.9996 | 0.98 | 827.7 |
| 9 | 827.5 ± 0.11 | 823.5 ± 0.11 | 8.0 | 0.55 | 0.9996 | 0.60 | 826.2 |
| 10 | 823.2 ± 0.11 | 818.0 ± 0.11 | 8.2 | 0.56 | 0.9996 | 0.82 | 821.3 |
| 11 | 843.8 ± 0.12 | 838.0 ± 0.12 | 8.3 | 0.58 | 0.9996 | 0.72 | 841.6 |
| 12 | 819.9 ± 0.12 | 831.7 ± 0.12 | 8.4 | 0.58 | 0.9996 | 0.89 | 826.5 |
| 13 | 829.1 ± 0.12 | 822.7 ± 0.12 | 8.8 | 0.61 | 0.9996 | 1.55 | 826.6 |
| 14 | 814.5 ± 0.12 | 825.8 ± 0.12 | 8.7 | 0.60 | 0.9996 | 1.89 | 820.8 |

## 1.5 Figure of merit

**The primary figure of merit is the normalised RMS residual:**

> **nRMS = RMS(z − fitted surface) / sag × 100 %**

The *sag* is the height of the fitted dome over the aperture, about 1.45 µm
here. nRMS is the typical deviation of the surface from the model, as a
percentage of the size of the feature being measured.

- It is dimensionless, so it compares the fit quality of domes of different
  size.
- It is **not** used to decide whether a surface is defective. Over a smaller
  aperture (for example a dome near the image border) the sag shrinks with
  r², so nRMS rises even for a perfect surface. The noisy-surface fault flag
  therefore uses the **absolute RMS** instead: above 30 nm, against 7–9 nm on
  clean domes and 154–231 nm on noisy ones.
- It is easy to read: 0.6 % means the surface follows the model to within
  0.6 % of its height.
- **R²** (the share of the height variance the model explains) is reported
  alongside it.
  - Over a circular aperture, a dome's height is spread uniformly between the
    apex and the rim, with standard deviation sag/√12. So
    **R² ≈ 1 − 12·nRMS²**: for 0.6 % this gives 0.99957, and 0.9996 is
    measured.
  - R² therefore carries the same information as nRMS, but squeezes every good
    fit into the digits just below 1. That is why nRMS is the primary measure.

**Scores in dataset 1:**

- Clean domes: nRMS **0.55–0.62 %** and R² **0.9995–0.9996**. The model
  describes the surface to about 8–9 nm.
- File 6: nRMS **16.2 %** and R² **0.759**. This is a poor fit (see §1.7).

**Two uncertainty measures complete the picture of how good R is:**

- **95 % confidence interval of Rx and Ry**, from the covariance of the fit
  parameters: σ²(AᵀA)⁻¹, propagated through R = −1/(2c). It is ±0.11–0.13 µm
  on clean domes. This is the *statistical* uncertainty.
- **Aperture stability**: R refitted on 50 %, 75 % and 100 % of the aperture.
  The spread is 0.36–1.99 %. This is the *model* uncertainty.
  - The residual maps show a faint ring-and-cross pattern of about ±40 nm, the
    same on every clean dome. The real Xpander profile is very slightly
    non-parabolic, so R depends a little on how much of the dome is used.
  - This is the largest uncertainty for clean domes: ±0.12 µm statistical,
    against several µm from the choice of aperture. The aperture is therefore
    fixed by a rule (80 % of the distance to the valley) and reported in the
    CSV.

## 1.6 If the Xpander were noisier, would I change the approach?

**Mostly no. The method is already built for noise, and dataset 1 file 6
proves it.**

That dome carries uniform noise of ±0.4 µm, about 25 times the clean RMS. Its
twin in dataset 2 (file 6) is the same chip without the noise. The noisy
measurement gives Rx/Ry = 833.0/827.0 µm, against 834.0/830.3 µm on the clean
twin: Rx is 1.0 µm off, well inside its 95 % CI of ±3.3 µm (0.4 %), and Ry
3.3 µm off, right at its CI. That is what a 95 % interval allows; see
`docs/figures/radius_twins.png`.

**Why it holds:**

- The fit averages about 117,000 points, so the statistical error of R grows
  only as σ/√N.
- Zero-mean noise does not bias least squares. Smoothing a quadric does not
  change its curvature either, so the apex and aperture search (on a 2 µm
  smoothed copy) are unaffected.
- **No local derivatives are used**, because derivatives amplify noise. The
  single-profile circle fits show what happens otherwise: on the noisy dome
  they give 858.9/797.6 µm, while the 2-D fit gives 833.0/827.0.

**What I would change for much noisier data, or a different kind of noise:**

- **Outliers, spikes and dust do not average out, so the code handles them
  explicitly** (details and tests in "Assumptions, artefacts and limits" at
  the end):
  - the dome fit drops pixels whose residual exceeds max(5 robust standard
    deviations, 0.1 µm), refits, and reports the share it dropped
    (`xpander_outlier_pct`). The threshold follows the surface's own spread,
    so a genuinely noisy dome is never "cleaned": its noise is reported and
    flagged;
  - the apex and the edge of the dome are found on a copy with spikes and
    dust particles removed;
  - missing (NaN) pixels are excluded from every fit.
- **Spatially correlated noise.** The covariance-based CI assumes independent
  pixels, so it would be optimistic. I would use a block bootstrap, or
  repeated fits on sub-apertures, to estimate the uncertainty instead.
- **Very low signal-to-noise.** Weight the fit, or use the largest safe
  aperture: more points give a smaller statistical error, at the cost of a
  slightly larger model error.
- **Pre-smoothing the data would not help.** Least squares already averages
  optimally, and a smoothed edge would bias the fit near the aperture border.

## 1.7 Faulty elements in dataset 1

Every file passes the structural checks:

- every element is found;
- crosses are on the axis within 0.58 µm and the apex within 0.81 µm;
- the planes are parallel within 0.28°;
- steps are 18.11–18.23 µm and radii are within 811–844 µm.

One file stands out:

**File 6 — both the Pivot and the Xpander are faulty (noisy).**

- **Pivot:** the plane-fit RMS is **586 / 570 nm**, against 40–55 / 20–26 nm
  on every other file (12–25 times rougher). A pixel-by-pixel comparison with
  the clean twin shows the added noise is **uniform between −1.0 and +1.0 µm**
  (std 0.58 µm, kurtosis −1.21, the signature of a uniform distribution).
  - Planes whose job is to be flat references to about 50 nm cannot be
    trusted with ±1 µm roughness.
  - The step is still measured as 18.214 µm, against 18.171 µm on the clean
    twin. The 0.043 µm gap is about 2.7 times the statistical error that this
    noise causes on a plane of roughly 1,500 px.
- **Xpander:** fit RMS **231 nm** (nRMS 16 %, R² 0.759), against 8–9 nm.
  The noise is uniform between −0.4 and +0.4 µm and spatially white (figure
  `results/figures/task1/6.png`, panel 4).

Flags: `plane1_noisy`, `plane2_noisy` and `xpander_surface_noisy` (geometric),
plus the matching statistical outliers.

**Not faults, but worth noting:**

- **Files 1, 12 and 14 are a different variant.** The channel sits at another
  position, a neighbouring structure is missing, and the raw heights are about
  5 µm lower. Their Xpanders are more strongly curved along x than along y:
  Ry exceeds Rx by 11.3–15.4 µm (1.4–1.9 %). Every other file has the opposite
  sign, Rx > Ry by 3.4–7.7 µm (0.4–0.9 %). This is within tolerance, and most
  likely a die-position or process difference.
- **File 11 has the largest radius** (843.8/838.0 µm, +2 %). It is within
  tolerance.
- **Files 11–14 have a step about 0.06 µm higher** (18.21–18.23 µm) than files
  0–10. This is within tolerance.

---

# Task 2 — Tilt and rotation

## 2.1 Tilt and rotation angles

The tilt angles are the slope angles of the base plane along x and y. The
total tilt is the angle between the base normal and the z axis. The azimuth
is the direction of steepest ascent, measured from +x toward +y (downward in
the image).

| File | Tilt x [°] | Tilt y [°] | Total tilt [°] | Azimuth [°] | Rotation [°] (± s.e.) | Applied rotation [°] | Error [°] |
|---|---|---|---|---|---|---|---|
| 0 | +0.0602 | +0.0793 | 0.0996 | +52.8 | +1.012 ± 0.015 | +1.00 | +0.012 |
| 1 | −0.0087 | +0.0474 | 0.0482 | +100.4 | −0.008 ± 0.013 | 0 | −0.008 |
| 2 | +0.1085 | −0.0368 | 0.1145 | −18.7 | −0.248 ± 0.012 | −0.25 | +0.002 |
| 3 | −0.0288 | +0.0412 | 0.0502 | +125.0 | +0.509 ± 0.017 | +0.50 | +0.009 |
| 4 | −0.0777 | +0.0888 | 0.1180 | +131.2 | −0.994 ± 0.012 | −1.00 | +0.006 |
| 5 | −0.0251 | +0.1158 | 0.1185 | +102.2 | +0.755 ± 0.016 | +0.75 | +0.005 |
| 6 | +0.0707 | −0.0846 | 0.1103 | −50.1 | −0.737 ± 0.008 | −0.75 | +0.013 |
| 7 | −0.0044 | +0.1107 | 0.1108 | +92.3 | +0.235 ± 0.016 | +0.25 | −0.015 |
| 8 | −0.0770 | +0.0459 | 0.0897 | +149.2 | −0.504 ± 0.015 | −0.50 | −0.004 |
| 9 | −0.0422 | −0.0478 | 0.0638 | −131.5 | +1.005 ± 0.013 | +1.00 | +0.005 |
| 10 | −0.1133 | −0.0488 | 0.1234 | −156.7 | −0.002 ± 0.017 | 0 | −0.002 |
| 11 | −0.0855 | +0.0067 | 0.0858 | +175.5 | −0.245 ± 0.009 | −0.25 | +0.005 |
| 12 | −0.0790 | −0.0797 | 0.1123 | −134.7 | +0.510 ± 0.008 | +0.50 | +0.010 |
| 13 | −0.0810 | −0.0533 | 0.0970 | −146.7 | −0.985 ± 0.011 | −1.00 | +0.015 |
| 14 | +0.0140 | −0.1099 | 0.1108 | −82.7 | +0.760 ± 0.008 | +0.75 | +0.010 |

**Where the applied rotations come from.** During data exploration, each
dataset-2 scan was registered onto its dataset-1 twin by searching for the
rotation that maximises their correlation. Every pair matched at
correlation 1.000, at a rotation that is a multiple of 0.25°. Those values were
used **only to validate** the estimator, never as an input.

**Accuracy:**

- The mean absolute error is **0.008°** and the worst is **0.0155°**
  (figure `docs/figures/rotation_validation.png`).
- The reported standard errors are 0.008–0.017°, consistent with the actual
  errors.
- Measured against the dataset-1 twin (whose own rotation is
  −0.015 … +0.011°), the worst error is 0.021°.
- Dataset 1 is level (total tilt 0.003–0.005°) and unrotated.

## 2.2 How the tilt and rotation correction works

**Tilt.**

1. On a smoothed copy, every pixel with slope below 0.25 µm/µm is a
   candidate.
2. RANSAC fits 300 planes, each through 3 random candidate pixels, and keeps
   the plane supported by the most candidates within ±0.1 µm. That plane is
   the base, the largest flat surface on the chip. An ordinary fit over all
   flat pixels would be biased upward by the many plateaus.
3. A robust least-squares fit, with iterative 3σ clipping, refines the plane
   on all base pixels within ±0.3 µm. The fit residual is about 12 nm.
4. The tilt angles are atan(slope_x) and atan(slope_y), with x and y in µm.
   The plane is subtracted, which makes every height relative to the base.
   That also removes the absolute height offset that differs between scans:
   files 1, 12 and 14 sit about 5 µm lower.

**Rotation.** The scan's straight edges (channel walls, slot edges, band
edges) are lithographic edges, parallel to the chip axes. Their angle is the
rotation.

1. Canny edge detection, then a probabilistic Hough transform, finds
   candidate straight segments within ±10° of horizontal or vertical. Canny is
   run with edge-replicating borders, because zero-padding creates fake 0°
   edges along the image border.
2. **Each segment is re-measured with sub-pixel precision.** On every row (for
   a near-vertical edge) or column (near-horizontal edge), the edge position
   is where the height profile crosses half-way up the step, interpolated
   linearly.
   - Locating the edge at the *peak of the gradient* instead suffers from
     "pixel locking": positions are biased toward pixel centres. On short,
     slightly tilted edges that flattens the measured angle. In my prototype
     an applied 0.25° was measured as 0.21°, with a worst error of 0.047°.
   - The mid-level crossing does not have this bias. The worst error dropped
     to 0.0155°.
3. A straight line is fitted to the points of each edge. Edges whose points
   are not straight (RMS > 0.25 px) are rejected.
4. The rotation is the **median of the 32–46 edge angles, weighted by edge
   length**. Different walls of a real chip disagree slightly (by up to 0.3°),
   and the median ignores those outliers. Its standard error is
   1.25 × 1.4826 × MAD / √n.

**Orientation.** The fine search only covers ±10° around each multiple of
90°. Coarse 90° turns are detected from the Pivot ramp direction (§1.1,
step 4), so a scan turned by 90°, 180° or 270° (plus up to ±10°) is also
handled.

**Measuring without interpolation.** A rotation-corrected ("canonical") copy
of the scan is made only to *find* the elements. Every *measurement* (plane
fits, cross centres, the Xpander fit) uses the **original pixels**, whose
coordinates are rotated into the corrected frame.

Resampling would smooth the data. Dataset 2 shows the effect: Teramount's own
rotation of these scans lowered the RMS of every rotated clean dome by about
8 % (§2.4). Never measuring interpolated data avoids adding a second smoothing.

## 2.3 Labeling and parameters (dataset 2)

The labeling is the same as in Task 1, applied in the corrected frame.

The table gives the cross centres in the **original** (rotated) image.
Corrected-frame coordinates (u, v) are in the CSV. In the corrected frame each
cross lands within 0.23 px of its dataset-1 twin.

| File | Step [µm] | Cross 1 x, y [px] | Cross 2 x, y [px] | Rx [µm] | Ry [µm] |
|---|---|---|---|---|---|
| 0 | 18.140 | 501.29, 772.60 | 503.05, 890.22 | 822.6 ± 0.11 | 817.9 ± 0.11 |
| 1 | 18.173 | 497.83, 785.73 | 497.83, 903.44 | 811.7 ± 0.12 | 827.2 ± 0.13 |
| 2 | 18.185 | 514.86, 771.83 | 514.50, 889.19 | 822.7 ± 0.10 | 818.6 ± 0.10 |
| 3 | 18.122 | 506.68, 776.45 | 507.35, 894.10 | 826.1 ± 2.14 | 820.7 ± 2.11 |
| 4 | 18.114 | 524.13, 776.09 | 521.80, 893.72 | 828.0 ± 0.11 | 823.1 ± 0.10 |
| 5 | 18.130 | 502.46, 769.69 | 504.00, 887.26 | 831.2 ± 0.11 | 826.8 ± 0.11 |
| 6 | 18.171 | 522.93, 766.80 | 521.35, 884.50 | 834.0 ± 0.12 | 830.3 ± 0.11 |
| 7 | 18.191 | 514.51, 766.46 | 515.23, 884.15 | 831.4 ± 0.11 | 824.4 ± 0.11 |
| 8 | 18.145 | 521.85, 771.23 | 521.05, 888.63 | 829.7 ± 0.11 | 824.3 ± 0.11 |
| 9 | 18.116 | 501.99, 766.54 | 504.07, 884.23 | 827.5 ± 0.10 | 823.5 ± 0.10 |
| 10 | 18.145 | 511.81, 770.76 | 511.76, 888.18 | 823.2 ± 0.11 | 818.0 ± 0.11 |
| 11 | 18.224 | 524.03, 764.22 | 523.22, 881.84 | 843.8 ± 0.11 | 838.0 ± 0.11 |
| 12 | 18.221 | 495.24, 771.71 | 496.05, 889.41 | 819.9 ± 0.11 | 831.7 ± 0.11 |
| 13 | 18.206 | 531.41, 762.45 | 529.33, 879.99 | 830.1 ± 2.18 | 822.3 ± 2.14 |
| 14 | 18.224 | 494.57, 767.51 | 496.16, 885.11 | 814.5 ± 0.11 | 825.8 ± 0.11 |

In the corrected frame, all extracted parameters match dataset 1:

- Pivot step within 0.004 µm on every file without a noisy Pivot;
- radii within 0.017 µm on clean domes;
- noisy domes within their confidence interval
  (`docs/figures/radius_twins.png`).

## 2.4 Grading the radius with the same method — is it still good?

**Scores, using the same nRMS / R² as Task 1:**

| File | RMS [nm] | nRMS [%] | R² |
|---|---|---|---|
| 0 | 7.9 | 0.54 | 0.9996 |
| 1 | 8.9 | 0.62 | 0.9995 |
| 2 | 7.6 | 0.52 | 0.9997 |
| **3** | **153.8** | **10.60** | **0.8804** |
| 4 | 7.6 | 0.52 | 0.9997 |
| 5 | 8.1 | 0.56 | 0.9996 |
| 6 | 8.2 | 0.57 | 0.9996 |
| 7 | 7.7 | 0.53 | 0.9997 |
| 8 | 8.0 | 0.55 | 0.9996 |
| 9 | 7.3 | 0.50 | 0.9997 |
| 10 | 8.2 | 0.56 | 0.9996 |
| 11 | 7.7 | 0.53 | 0.9997 |
| 12 | 7.7 | 0.54 | 0.9996 |
| **13** | **153.5** | **10.69** | **0.8783** |
| 14 | 8.0 | 0.55 | 0.9996 |

**Is it still a good grading method? No, not for grading the *extracted
radius*.** This dataset exposes two weaknesses.

1. **It grades the surface, not the measurement.**
   - Files 3 and 13 score badly (nRMS 10.6–10.7 %, R² 0.88) because their domes
     are noisy.
   - Yet their radii are accurate. File 3 gives Rx/Ry = 826.1/820.7 µm against
     827.2/821.4 µm on its clean twin, and file 13 gives 830.1/822.3 against
     829.1/822.7. Both are off by 0.3–1.1 µm (≤ 0.14 %), within their CI.
   - nRMS is a good *fault detector* for the surface, but a poor grade for
     the number we report.
2. **It depends on how the data was processed, not on the chip.**
   - The rotated clean domes score *better* than their identical twins in
     dataset 1: RMS 7.3–8.2 nm against 8.0–8.9 nm, about 8 % lower.
   - The two files without rotation (1 and 10) score exactly the same in both
     datasets. The difference comes only from the interpolation used to rotate
     the scans, which smooths the noise.
   - So the same element gets a different grade depending on the processing.

**A better grading method: the uncertainty of R itself.** I would grade each
radius by its relative uncertainty:

> **U(R) = √( CI₉₅² + (ΔR_aperture / 2)² ) / R**

- **CI₉₅** is the statistical part, from the fit covariance. It grows with the
  noise and shrinks with the number of points: ±0.11 µm on clean domes,
  ±2.1 µm on the noisy ones.
- **ΔR_aperture** is the model part: the spread of R over 50/75/100 %
  apertures (`xpander_stability_pct`).

With this grade, the noisy domes of files 3 and 13 score about 0.3–1.3 %,
close to the clean ones (0.2–1.0 %). That correctly says "R is reliable",
while nRMS separately says "this surface is defective".

Two refinements:

- In dataset 2 the noise is spatially correlated, because the rotation
  interpolated it, so the covariance-based CI is somewhat optimistic. A block
  bootstrap would make it exact.
- The strongest test is **repeatability**: two measurements of the same
  element should agree within their uncertainty. Here the twin datasets
  provide that check, and they do agree (§2.3).

## 2.5 Differences between the two datasets

1. **Same chips, transformed.** Each dataset-2 scan is the dataset-1 scan of
   the same index:
   - rotated about the image centre by **−1° … +1° in 0.25° steps**;
   - with a tilt plane of **0.05–0.12°** added;
   - with the rotated-in corners filled at base level.
2. **The planted faults are in different files.**
   - Dataset 1: file 6 (Pivot and Xpander).
   - Dataset 2: files 3 (Xpander), 7 (Pivot) and 13 (Xpander). File 6 is clean
     in dataset 2.
3. **The noise was added at a different stage.**
   - In dataset 1 (file 6) it is raw uniform noise: ±0.4 µm on the dome
     (std 0.231 µm) and ±1 µm on the Pivot (std 0.58 µm).
   - In dataset 2 the noise has the same bounds, but a lower std: 0.154 µm on
     the domes and 0.36–0.38 µm on the Pivot. It also shows a periodic grid
     texture in the residual maps (`results/figures/task2/13.png`).
   - That is the signature of noise added **before** the synthetic rotation,
     then smoothed unevenly by the interpolation: the grid is the moiré of
     the sub-pixel shift.
4. **Interpolation smoothing.** Every rotated scan has slightly lower
   fit residuals than its twin (§2.4).
5. **After correction the measurements are identical.** That validates the
   tilt and rotation correction end to end.

## 2.6 Faulty elements in dataset 2

- **File 3 — Xpander faulty (noisy).** Fit RMS **154 nm** (nRMS 10.6 %,
  R² 0.880), against 7–9 nm on the clean domes. The noise is bounded at
  ±0.40 µm and smoothed into a grid texture. The radius is still measured
  correctly (826.1/820.7 µm, twin 827.2/821.4). The Pivot is clean.
- **File 7 — Pivot faulty (noisy).** Plane-fit RMS **396 / 372 nm**, against
  40–54 / 20–25 nm. The noise is bounded at about ±1 µm with std 0.36–0.38 µm.
  The step is still 18.191 µm (twin 18.182). The Xpander is clean.
- **File 13 — Xpander faulty (noisy).** Fit RMS **154 nm** (nRMS 10.7 %,
  R² 0.878), with the same grid texture. Radius 830.1/822.3 µm (twin
  829.1/822.7).
  - Its plane 2 is unusually *smooth* (20 nm against 22–25 nm). That is not
    a defect, so it is not flagged: for roughness and axis offsets the
    statistical check only reports unusually high values.
  - Statistical outliers are reported in their own column and never mark a
    file as faulty by themselves: unusual is not the same as defective.
- **Every other file passes** all geometric and nominal checks. The variant
  files 1, 12 and 14 behave as in dataset 1.

Details for each file: `results/fault_analysis.md`.

---

## Assumptions, artefacts and limits

Teramount confirmed that the test scans use the same units and pixel size,
and a similar chip design. They also pointed out that real scans can carry
artefacts, so this section lists every assumption the code makes, every
artefact it handles (with the test that proves it), and what it deliberately
does not handle, and why.

### Assumptions

| Assumption | Why it holds | If it does not hold |
|---|---|---|
| Heights in µm, pixels of 0.252 µm | Confirmed by Teramount for the test data. | `--z-scale` and `--pixel-size`. Every size setting is in µm, so it scales; the tests also run at 0.35 and 0.5 µm/px. |
| The chip family: a Pivot (two flat planes, a ramp between them, a recessed cross on each plane) with the Xpander dome along the same axis on the low side of the ramp | Confirmed as "similar"; true in all 30 scans. | The missing element is reported "not found" with the reason, never measured on the wrong structure. |
| Plane 2 is the highest flat plateau lying fully inside the scan | True in all scans; the only other tall plateau (23.5 µm) is lower than plane 2 (31 µm). | A larger, taller flat object (big debris) would be taken for plane 2; the orientation or plane-1 search then fails with a clear reason. |
| The chip axes are within ±10° of the image axes, up to a quarter turn | The microscope aligns the chip; dataset 2 is within ±1°. | No straight edge is found: warning `rotation_not_measured`, and the scan is analysed as unrotated. |
| The base is a plane (tilt only) | Base residual about 12 nm after the RANSAC plane. | A bowed base is not modelled; a bow with a radius above 1 m would change R by less than 0.7 µm, and the Pivot step is measured locally. |
| The dome is smooth and convex, close to a paraboloid over the fit area | Sphere and paraboloid differ by ≤ 1.5 nm over the aperture; the exact sphere fit agrees within 0.09 %. | A non-convex dome is reported "surface not convex". |
| Neighbouring domes are separated by valleys or steps | Layout of the chip; all scans. | The fit area is limited and the reason is reported. |
| Nominal spec 18.18 ± 0.30 µm and 826 ± 30 µm | Estimated from the clean provided files; the design is "similar". | `--nominal-step`, `--nominal-radius`. The geometric and statistical checks do not depend on them. |
| Noise limits: plane RMS 150 nm, dome RMS 30 nm (after outliers are dropped) | Clean surfaces: 20–55 nm and 7–9 nm; the noisy ones: 370–590 nm and 150–230 nm. | Settings in `config.py`. |

### Artefacts the code handles

| Artefact | What it did before | How it is handled | Proven by |
|---|---|---|---|
| Random noise | — | Least squares over more than 100,000 points; confidence intervals reported; a noisy surface is flagged by its absolute RMS. | Noisy files 6 (dataset 1), 3, 7, 13 (dataset 2); `test_noisy_dome_*`. |
| Single-pixel spikes (dust glints, bad pixels) | Every clean dome was flagged "noisy". | The dome fit drops outliers and reports their share; the plane fits drop outliers (3σ); segmentation uses a median filter; in a cross centroid no pixel counts for more than a floor pixel. | `test_dust_spikes_*`, `test_deep_spikes_inside_a_cross_*` (6 spikes: 0.8 px → < 0.2 px), real scans with spikes. |
| Dust particles up to 10 µm | A 3 µm particle on the dome, or between the Pivot and the dome, made the Xpander "not found". | The apex and the dome edge are found on a copy with particles removed (grey opening); the fit then drops the particle's pixels. | `test_dust_particle_*` (3 positions), real scans with dust. |
| Missing pixels (NaN), including dropouts on steep walls | — | Filled only to find things; excluded from every fit; the rotation never measures a filled pixel. | `test_nan_*`, `test_clustered_nan_*`, `test_wall_dropouts_*`, real scans with dropouts. |
| Scan-line streaks (each line offset by its own height) | 50 nm streaks raised false "noisy dome" and "planes not parallel" faults. | Measured on every scan (`streak_level_um`; clean scans: under 1 nm) and removed when above 10 nm, with the warning `scan_line_streaks_removed`. | `test_streaks.py`, `test_scan_line_streaks_*`, real scans with streaks. |
| Ringing ("batwings") at steep edges | — | Plane fits exclude a 0.5 µm edge margin; the rotation reads each edge's plateaus away from the edge, and takes the median of 32–46 edges. | Real scans with 10 % edge ringing. |
| Tilt and height offset | — | RANSAC base plane, subtracted. | Dataset 2; `test_tilt.py`. |

`tests/test_real_artifacts.py` adds each artefact, and all of them together,
to three real scans: a standard chip, the other variant (file 12) and the
noisy file 6. The step stays within 0.03 µm, the radii within 0.3 % (or
twice the scan's own uncertainty on the noisy dome), the crosses within
0.3 px, and the faulty / clean verdict does not change.

### Not handled, by choice

- **Particles wider than 10 µm and debris taller than plane 2.** They are the
  size of the chip's own features, so they cannot be told apart from them
  without the design layout. Inside the fit area their pixels are still
  dropped as outliers (and counted); elsewhere they make an element "not
  found" with a reason, never a wrong measurement in silence.
- **Pits and scratches** are not removed from the copy used to find the dome,
  because removing pits would also fill the valleys that separate
  neighbouring domes. Inside the fit area they are dropped as outliers.
- **The slow part of scan-line streaks** cannot be told apart from the real
  surface shape. With 50 nm streaks it shifts the radius along the streak
  direction by up to 0.5 %, corrected or not.
- **A bowed base** (see above) and **saturated or clipped heights**, which
  none of the scans show.
- **Rotations further than 10° from a quarter turn** (see above).
- **The aperture.** The radius depends slightly (0.4–2 %) on the fit area,
  because the real profile is not exactly a quadric. The fit area therefore
  follows a fixed rule and is reported.

## Reproducing every number

```bash
py -m pip install -r requirements.txt
py run.py --data 15_files_task_1 --name task1     # results/task1_results.csv + figures
py run.py --data 15_files_task_2 --name task2     # results/task2_results.csv + figures
py docs/make_answer_figures.py                    # docs/figures/*.png
py -m pytest                                      # includes the real-data validation
```
