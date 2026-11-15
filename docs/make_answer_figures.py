"""Draw the explanatory figures used in ANSWERS.md from the results CSVs.

Run after both datasets were analysed::

    py run.py --data 15_files_task_1 --name task1
    py run.py --data 15_files_task_2 --name task2
    py docs/make_answer_figures.py

The applied rotations of dataset 2 were established independently by
registering each dataset-2 scan onto its dataset-1 twin (see
tests/test_real_data.py); they are used here only to show the error.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures"
APPLIED_ROTATION = [1.0, 0, -0.25, 0.5, -1.0, 0.75, -0.75, 0.25, -0.5, 1.0, 0, -0.25, 0.5, -1.0,
                    0.75]
NOISY_XPANDER = {(1, 6), (2, 3), (2, 13)}


def _load(task: int) -> list[dict[str, float]]:
    path = ROOT / "results" / f"task{task}_results.csv"
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return [{k: (float(v) if v and k not in ("file", "status", "error") and not k.endswith(
        ("flags", "faulty")) else v) for k, v in r.items()} for r in rows]


def rotation_figure(t1: list[dict], t2: list[dict]) -> None:
    fig = Figure(figsize=(11, 4.2), layout="constrained")
    ax1, ax2 = fig.add_subplot(1, 2, 1), fig.add_subplot(1, 2, 2)
    applied = np.array(APPLIED_ROTATION)
    measured = np.array([r["rotation_deg"] for r in t2])
    baseline = np.array([r["rotation_deg"] for r in t1])
    ax1.plot([-1.2, 1.2], [-1.2, 1.2], color="0.7", lw=1)
    ax1.plot(applied, measured, "o", label="dataset 2, measured")
    ax1.set(xlabel="applied rotation [deg]", ylabel="measured rotation [deg]",
            title="Rotation: measured vs applied")
    ax1.legend()
    idx = np.arange(15)
    ax2.bar(idx - 0.2, (measured - applied) * 1000, 0.4, label="dataset 2 - applied")
    ax2.bar(idx + 0.2, (measured - baseline - applied) * 1000, 0.4,
            label="(dataset 2 - dataset 1) - applied")
    ax2.axhline(0, color="0.3", lw=0.8)
    ax2.set(xlabel="file", ylabel="error [millidegree]", title="Rotation error per file",
            xticks=idx)
    ax2.legend(fontsize=8)
    fig.savefig(OUT / "rotation_validation.png", dpi=110)


def radius_figure(t1: list[dict], t2: list[dict]) -> None:
    fig = Figure(figsize=(11, 4.2), layout="constrained")
    for k, (key, label) in enumerate((("rx", "Rx"), ("ry", "Ry"))):
        ax = fig.add_subplot(1, 2, k + 1)
        for task, rows, shift in ((1, t1, -0.15), (2, t2, 0.15)):
            for i, r in enumerate(rows):
                noisy = (task, i) in NOISY_XPANDER
                ax.errorbar(i + shift, r[f"xpander_{key}_um"], yerr=r[f"xpander_{key}_ci95_um"],
                            fmt="s" if noisy else "o", ms=5, capsize=3,
                            color=("tab:red" if noisy else ("tab:blue" if task == 1 else
                                                             "tab:orange")))
        ax.set(xlabel="file", ylabel=f"{label} [µm]", xticks=range(15),
               title=f"{label}: dataset 1 blue, dataset 2 orange, noisy dome red\n"
                     "(error bars = 95 % confidence interval)")
    fig.savefig(OUT / "radius_twins.png", dpi=110)


def crosses_figure(t1: list[dict]) -> None:
    fig = Figure(figsize=(7, 3.6), layout="constrained")
    ax = fig.add_subplot(1, 1, 1)
    idx = np.arange(15)
    bias = [(r["pivot_height_diff_with_crosses_um"] - r["pivot_height_diff_um"]) * 1000 for r in t1]
    ax.bar(idx, bias, color="tab:purple")
    ax.set(xlabel="file (dataset 1)", ylabel="bias [nm]", xticks=idx,
           title="Pivot step: crosses kept in the fit minus crosses removed")
    fig.savefig(OUT / "crosses_bias.png", dpi=110)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t1, t2 = _load(1), _load(2)
    rotation_figure(t1, t2)
    radius_figure(t1, t2)
    crosses_figure(t1)
    print(f"figures written to {OUT}")


if __name__ == "__main__":
    main()
