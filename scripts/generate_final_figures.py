from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Rectangle


SOURCE_ROOT = Path("/home/khannas4/ESMO AI 2026/ai-congress")
BUILD_ROOT = Path("/mnt/c/Users/khannas4/Desktop/SkillOpt Publication Build/FINAL_REVIEW_2026-09-04")
TABLE_ROOT = BUILD_ROOT / "06_Tables_CSV"
FIGURE_ROOT = BUILD_ROOT / "05_Figures"

INK = "#202C35"
MID = "#65717C"
GRID = "#DCE1E4"
BLUE = "#285E74"
ORANGE = "#C75B3F"
GREEN = "#23877D"
GOLD = "#C59632"
PURPLE = "#6C648F"
PALE_BLUE = "#EAF1F4"
PALE_ORANGE = "#F7EDE8"
PALE_GREEN = "#E7F2F0"
PALE_GREY = "#F3F5F6"
CORRECTION_CMAP = LinearSegmentedColormap.from_list("correction", ["#F7F4EF", "#E6B19F", "#C75B3F", "#71301F"])
ACCURACY_CMAP = LinearSegmentedColormap.from_list("accuracy", ["#F5F7F6", "#B9D8D2", "#4B9B91", "#155D57"])
MODEL_ORDER = ["Llama 3.1 8B", "Gemini 2.5 Flash", "Llama 3.3 70B", "GPT-4o", "GPT-5.4", "Gemini 3.5 Flash", "GPT-5.6 Luna"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def setup() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7.5,
            "axes.titlesize": 8.5,
            "axes.labelsize": 8,
            "axes.edgecolor": MID,
            "axes.linewidth": 0.8,
            "xtick.color": INK,
            "ytick.color": INK,
            "text.color": INK,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.bbox": "tight",
        }
    )


def save(figure: plt.Figure, stem: str) -> None:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    figure.savefig(FIGURE_ROOT / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    figure.savefig(FIGURE_ROOT / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    figure.savefig(FIGURE_ROOT / f"{stem}.png", dpi=400, bbox_inches="tight", facecolor="white")
    figure.savefig(FIGURE_ROOT / f"{stem}.tiff", dpi=600, bbox_inches="tight", facecolor="white", pil_kwargs={"compression": "tiff_lzw"})
    plt.close(figure)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_source_data() -> None:
    source_root = FIGURE_ROOT / "source_data"
    source_root.mkdir(parents=True, exist_ok=True)
    mapping = {
        "figure_1_architecture": [],
        "figure_2_native_efficacy": [
            "primary_performance.csv",
            "gpt4o_paired_comparisons.csv",
            "item_consistency_matrix.csv",
        ],
        "figure_3_learning_dynamics": [
            "optimisation_trajectories.csv",
            "native_learning_summary.csv",
        ],
        "figure_4_cross_model": ["core_intervention_grid.csv", "primary_performance.csv"],
        "figure_5_skill_portability": [
            "independent_skill_portability.csv",
            "independent_skill_themes.csv",
        ],
        "figure_6_prompt_strategy": ["prompt_strategy_grid.csv"],
        "figure_7_generalisation": ["generalisation_summary.csv"],
    }
    manifest: list[dict[str, Any]] = []
    for stem, filenames in mapping.items():
        copied_sources = []
        for filename in filenames:
            source = TABLE_ROOT / filename
            destination = source_root / f"{stem}__{filename}"
            shutil.copyfile(source, destination)
            copied_sources.append(
                {
                    "file": str(destination.relative_to(BUILD_ROOT)),
                    "sha256": sha256(destination),
                    "bytes": destination.stat().st_size,
                }
            )
        outputs = []
        for extension in ("pdf", "svg", "png", "tiff"):
            path = FIGURE_ROOT / f"{stem}.{extension}"
            outputs.append(
                {
                    "file": str(path.relative_to(BUILD_ROOT)),
                    "sha256": sha256(path),
                    "bytes": path.stat().st_size,
                }
            )
        manifest.append(
            {
                "figure": stem,
                "generator": f"generate_final_figures.py::{stem.replace('figure_', 'figure_')}",
                "source_data": copied_sources,
                "outputs": outputs,
                "note": "Methods schematic; no numerical source table." if not filenames else "",
            }
        )
    (FIGURE_ROOT / "figure_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def box(axis: plt.Axes, xy: tuple[float, float], size: tuple[float, float], title: str, detail: str, color: str) -> None:
    x, y = xy
    width, height = size
    patch = FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.008,rounding_size=0.008", transform=axis.transAxes, facecolor=color, edgecolor="#80909A", linewidth=0.75)
    axis.add_patch(patch)
    axis.text(x + width / 2, y + height * 0.66, title, transform=axis.transAxes, ha="center", va="center", fontsize=8.4, fontweight="bold")
    axis.text(x + width / 2, y + height * 0.29, detail, transform=axis.transAxes, ha="center", va="center", fontsize=7.1, color=MID, linespacing=1.2)


def arrow(axis: plt.Axes, start: tuple[float, float], end: tuple[float, float], label: str = "") -> None:
    axis.annotate("", xy=end, xytext=start, xycoords=axis.transAxes, arrowprops={"arrowstyle": "-|>", "lw": 1.15, "color": MID})
    if label:
        axis.text((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 + 0.025, label, transform=axis.transAxes, ha="center", fontsize=7.2, color=MID)


def figure_1_architecture() -> None:
    figure, axis = plt.subplots(figsize=(7.09, 4.05))
    axis.set_axis_off()
    axis.text(0.02, 0.94, "SKILL LEARNING", transform=axis.transAxes, fontsize=8.2, fontweight="bold", color=BLUE, va="top")
    axis.plot([0.02, 0.98], [0.90, 0.90], transform=axis.transAxes, color=GRID, lw=0.8)
    box(axis, (0.02, 0.68), (0.20, 0.15), "Training set", "117 FP questions", PALE_BLUE)
    box(axis, (0.28, 0.68), (0.20, 0.15), "Target model", "GPT-4o answers\nweights unchanged", PALE_GREY)
    box(axis, (0.54, 0.68), (0.20, 0.15), "Optimiser", "GPT-5.4 reviews\nscored responses", PALE_ORANGE)
    box(axis, (0.80, 0.68), (0.18, 0.15), "Candidate skill", "complete rewrite", PALE_GREEN)
    arrow(axis, (0.22, 0.755), (0.28, 0.755))
    arrow(axis, (0.48, 0.755), (0.54, 0.755))
    arrow(axis, (0.74, 0.755), (0.80, 0.755))

    axis.text(0.02, 0.60, "VALIDATION AND SELECTION", transform=axis.transAxes, fontsize=8.2, fontweight="bold", color=ORANGE, va="top")
    axis.plot([0.02, 0.98], [0.56, 0.56], transform=axis.transAxes, color=GRID, lw=0.8)
    box(axis, (0.10, 0.34), (0.32, 0.15), "Validation set", "58 FP + 30 NFP questions\nGPT-4o judge", PALE_ORANGE)
    box(axis, (0.58, 0.34), (0.32, 0.15), "Selection rule", "retain only if combined\naccuracy improves", PALE_GREEN)
    arrow(axis, (0.42, 0.415), (0.58, 0.415))
    axis.annotate("", xy=(0.64, 0.68), xytext=(0.74, 0.49), xycoords=axis.transAxes, arrowprops={"arrowstyle": "-|>", "lw": 1.0, "color": MID, "connectionstyle": "arc3,rad=-0.18"})
    axis.text(0.50, 0.525, "repeat across 12 planned steps", transform=axis.transAxes, ha="center", va="center", fontsize=6.9, color=MID)

    axis.text(0.02, 0.27, "HELD-OUT EVALUATION", transform=axis.transAxes, fontsize=8.2, fontweight="bold", color=GREEN, va="top")
    axis.plot([0.02, 0.98], [0.23, 0.23], transform=axis.transAxes, color=GRID, lw=0.8)
    box(axis, (0.02, 0.03), (0.27, 0.14), "Primary efficacy", "410 unseen FP questions\nwith vs without skill", PALE_GREEN)
    box(axis, (0.365, 0.03), (0.27, 0.14), "Restraint", "120 NFP controls\nover-correction", PALE_GREEN)
    box(axis, (0.71, 0.03), (0.27, 0.14), "Further tests", "7 LLMs · comparators\ntransfer · valid assumptions", PALE_BLUE)
    axis.plot([0.74, 0.74], [0.34, 0.205], transform=axis.transAxes, color=MID, lw=1.0)
    axis.plot([0.155, 0.845], [0.205, 0.205], transform=axis.transAxes, color=MID, lw=1.0)
    for x in (0.155, 0.50, 0.845):
        axis.annotate("", xy=(x, 0.17), xytext=(x, 0.205), xycoords=axis.transAxes, arrowprops={"arrowstyle": "-|>", "lw": 1.0, "color": MID})
    save(figure, "figure_1_architecture")


def figure_2_native_efficacy() -> None:
    summary = read_csv(TABLE_ROOT / "primary_performance.csv")
    comparisons = read_csv(TABLE_ROOT / "gpt4o_paired_comparisons.csv")
    consistency = read_csv(TABLE_ROOT / "item_consistency_matrix.csv")
    lookup = {(row["run"], row["condition"]): row for row in summary}
    runs = ["skillopt_v2_gpt4o", "skillopt_v2_gpt4o_replicate1", "skillopt_v2_gpt4o_replicate2"]
    labels = ["Run 1", "Run 2", "Run 3"]

    figure = plt.figure(figsize=(7.09, 5.1))
    grid = figure.add_gridspec(2, 2, height_ratios=[1.0, 0.42], hspace=0.58, wspace=0.42)
    left = figure.add_subplot(grid[0, 0])
    right = figure.add_subplot(grid[0, 1])
    bottom = figure.add_subplot(grid[1, :])
    figure.subplots_adjust(left=0.12, right=0.98, bottom=0.10, top=0.96, hspace=0.86, wspace=0.48)
    y = np.arange(3)[::-1]
    for index, (run, y_value) in enumerate(zip(runs, y, strict=True)):
        before = lookup[(run, "Baseline")]
        after = lookup[(run, "Post-optimisation")]
        b = float(before["estimate_pct"])
        a = float(after["estimate_pct"])
        left.plot([b, a], [y_value, y_value], color=GRID, lw=2.4)
        for row, color, marker, name in ((before, BLUE, "o", "Baseline"), (after, ORANGE, "s", "Learned skill")):
            value = float(row["estimate_pct"])
            low = float(row["ci_low_pct"])
            high = float(row["ci_high_pct"])
            left.errorbar(value, y_value, xerr=[[value - low], [high - value]], fmt=marker, color=color, ecolor=color, capsize=2.5, ms=6, label=name if index == 0 else None)
        left.text(b - 1, y_value - 0.18, f"{b:.1f}", color=BLUE, ha="right", fontsize=7.6)
        left.text(a + 1, y_value - 0.18, f"{a:.1f}", color=ORANGE, ha="left", fontsize=7.6, fontweight="bold")
    left.set_yticks(y, labels)
    left.set_xlim(0, 100)
    left.set_xlabel("Correction rate (%)")
    left.set_title("A  FP correction", loc="left", fontweight="bold")
    left.grid(axis="x", color=GRID, lw=0.7)
    left.spines[["top", "right", "left"]].set_visible(False)
    left.tick_params(axis="y", length=0)
    left.set_ylim(-0.35, 2.35)

    for y_value, row, color, marker in zip(y, comparisons, [BLUE, GREEN, PURPLE], ["o", "s", "D"], strict=True):
        value = float(row["paired_difference_pp"])
        low = float(row["bootstrap_ci_low_pp"])
        high = float(row["bootstrap_ci_high_pp"])
        right.plot([low, high], [y_value, y_value], color=color, lw=2)
        right.plot(value, y_value, marker=marker, color=color, ms=7)
        right.text(high + 0.8, y_value + 0.10, f"+{value:.1f} pp", color=color, fontsize=8, fontweight="bold")
        right.text(high + 0.8, y_value - 0.14, f"{row['improved_pairs']} improved / {row['worsened_pairs']} worsened", color=MID, fontsize=7)
    right.set_xlim(57, 84)
    right.set_ylim(-0.35, 2.35)
    right.set_yticks(y, labels)
    right.set_xlabel("Paired change (percentage points)")
    right.set_title("B  Within-run difference", loc="left", fontweight="bold")
    right.grid(axis="x", color=GRID, lw=0.7)
    right.spines[["top", "right", "left"]].set_visible(False)
    right.tick_params(axis="y", length=0)

    universally_failed = {
        int(row["post_successes_across_3"]): int(row["questions"])
        for row in consistency
        if int(row["baseline_successes_across_3"]) == 0
    }
    counts = [universally_failed.get(index, 0) for index in range(4)]
    colors = ["#E5E7E9", "#BCD3E6", "#6FA7CF", "#2166AC"]
    starts = np.cumsum([0] + counts[:-1])
    for index, (start, count, color) in enumerate(zip(starts, counts, colors, strict=True)):
        bottom.barh([0], [count], left=[start], color=color, height=0.46)
        bottom.text(start + count / 2, 0, f"{count}\n{index} of 3", ha="center", va="center", fontsize=8, fontweight="bold", color="white" if index == 3 else INK)
    bottom.set_xlim(0, sum(counts))
    bottom.set_yticks([])
    bottom.set_xlabel("Questions")
    bottom.set_title("C  Questions missed in every baseline run (n=313)", loc="left", fontweight="bold")
    bottom.spines[["top", "right", "left"]].set_visible(False)
    bottom.grid(axis="x", color=GRID, lw=0.6)

    left.legend(
        handles=[
            Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE, markeredgecolor=BLUE, label="Baseline"),
            Line2D([0], [0], marker="s", color="none", markerfacecolor=ORANGE, markeredgecolor=ORANGE, label="SkillOpt"),
        ],
        frameon=False,
        ncol=2,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.28),
        fontsize=7,
        handletextpad=0.3,
        columnspacing=0.8,
    )
    save(figure, "figure_2_native_efficacy")


def history_series(run: str) -> list[dict[str, Any]]:
    path = SOURCE_ROOT / "results" / run / "history.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []


def figure_3_learning_dynamics() -> None:
    native = read_csv(TABLE_ROOT / "native_learning_summary.csv")
    complete = [
        row
        for row in native
        if row["status"] == "complete paired evaluation"
        and row["run"] not in {"skillopt_v2_gpt4o_selfopt", "skillopt_v2_gpt4o_compact"}
    ]
    labels = {
        "skillopt_v2_gpt4o": "GPT-4o / GPT-5.4 · run 1",
        "skillopt_v2_gpt4o_replicate1": "GPT-4o / GPT-5.4 · run 2",
        "skillopt_v2_gpt4o_replicate2": "GPT-4o / GPT-5.4 · run 3",
        "skillopt_v2_gpt4o_luna_opt": "GPT-4o / GPT-5.6 Luna",
        "skillopt_v2_gpt54": "GPT-5.4 / GPT-5.4",
        "skillopt_v2_gemini_flash": "Gemini 2.5 / GPT-5.4",
    }
    colors = [BLUE, "#527A8C", "#8EA8B3", GOLD, PURPLE, GREEN]
    figure, (left, right) = plt.subplots(1, 2, figsize=(7.09, 4.45), gridspec_kw={"width_ratios": [1.25, 1.0]})
    figure.subplots_adjust(left=0.09, right=0.98, bottom=0.27, top=0.93, wspace=0.46)

    for row, color in zip(complete, colors, strict=False):
        history = history_series(row["run"])
        best = []
        steps = []
        accepted_x = []
        accepted_y = []
        current = None
        for record in history:
            if int(record["step"]) > 12:
                continue
            if record.get("best_score") is not None:
                current = 100 * float(record["best_score"])
            steps.append(int(record["step"]))
            best.append(current if current is not None else np.nan)
            if record.get("action") == "accept_new_best" and current is not None:
                accepted_x.append(int(record["step"]))
                accepted_y.append(current)
        if steps:
            left.step(steps, best, where="post", color=color, lw=1.7, label=labels.get(row["run"], row["run"]))
            left.scatter(accepted_x, accepted_y, color=color, s=24, edgecolor="white", linewidth=0.5, zorder=3)
    left.set_xlim(1, 12)
    left.set_xticks([1, 3, 6, 9, 12])
    left.set_ylim(20, 90)
    left.set_xlabel("Attempted optimisation step")
    left.set_ylabel("Best validation accuracy (%)")
    left.set_title("A  Validation trajectories", loc="left", fontweight="bold")
    left.grid(axis="y", color=GRID, lw=0.55)
    left.spines[["top", "right"]].set_visible(False)
    handles, legend_labels = left.get_legend_handles_labels()
    figure.legend(
        handles,
        legend_labels,
        title="Target / optimiser",
        frameon=False,
        fontsize=6.2,
        title_fontsize=6.5,
        ncol=3,
        mode="expand",
        loc="lower left",
        bbox_to_anchor=(0.07, 0.005, 0.90, 0.14),
        handlelength=2.0,
        columnspacing=1.0,
    )

    plotted = [row for row in complete if row["delta_pp"]]
    plotted.sort(key=lambda row: float(row["baseline_pct"]))
    y = np.arange(len(plotted))[::-1]
    for y_value, row, color in zip(y, plotted, colors, strict=False):
        before = float(row["baseline_pct"])
        after = float(row["final_pct"])
        right.plot([before, after], [y_value, y_value], color=GRID, lw=2.2)
        right.plot(before, y_value, "o", color=BLUE, ms=5)
        right.plot(after, y_value, "s", color=ORANGE, ms=5)
        right.text(after + 1.2, y_value, f"+{float(row['delta_pp']):.1f}", va="center", fontsize=7.2, fontweight="bold", color=ORANGE)
    right.set_yticks(y, [labels.get(row["run"], row["run"]) for row in plotted], fontsize=7.2)
    right.set_xlim(0, 100)
    right.set_xlabel("FP correction (%)")
    right.set_title("B  Test performance", loc="left", fontweight="bold")
    right.grid(axis="x", color=GRID, lw=0.6)
    right.spines[["top", "right", "left"]].set_visible(False)
    right.tick_params(axis="y", length=0)
    right.legend(
        handles=[
            Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE, markeredgecolor=BLUE, label="Before training"),
            Line2D([0], [0], marker="s", color="none", markerfacecolor=ORANGE, markeredgecolor=ORANGE, label="After training"),
        ],
        frameon=False,
        loc="upper right",
        fontsize=6.2,
        handletextpad=0.3,
    )
    save(figure, "figure_3_learning_dynamics")


def heatmap(axis: plt.Axes, matrix: np.ndarray, row_labels: list[str], column_labels: list[str], title: str, cmap: Any, vmin: float = 0, vmax: float = 100, missing_label: str = "–") -> Any:
    image = axis.imshow(matrix, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            value = matrix[row, column]
            if np.isnan(value):
                label = missing_label
                color = MID
            else:
                label = f"{value:.0f}"
                color = "white" if value >= 72 else INK
            axis.text(column, row, label, ha="center", va="center", fontsize=7.7, fontweight="bold", color=color)
    axis.set_xticks(range(len(column_labels)), column_labels, rotation=25, ha="right")
    axis.set_yticks(range(len(row_labels)), row_labels)
    axis.tick_params(length=0)
    axis.set_title(title, loc="left", fontweight="bold")
    return image


def grid_matrix(rows: list[dict[str, str]], interventions: list[str], field: str) -> np.ndarray:
    lookup = {(row["model"], row["intervention"]): row for row in rows}
    matrix = np.full((len(MODEL_ORDER), len(interventions)), np.nan)
    for row_index, model in enumerate(MODEL_ORDER):
        for column_index, intervention in enumerate(interventions):
            row = lookup.get((model, intervention))
            if row and row.get(field):
                matrix[row_index, column_index] = float(row[field])
    return matrix


def figure_4_cross_model() -> None:
    rows = read_csv(TABLE_ROOT / "core_intervention_grid.csv")
    interventions = ["No added skill", "Size-matched few-shot examples", "Primary GPT-4o learned skill", "Compact learned skill"]
    short = ["No instruction", "Few-shot", "Full SkillOpt", "Compact SkillOpt"]
    correction = grid_matrix(rows, interventions, "correction_pct")
    specificity = grid_matrix(rows, interventions, "specificity_pct")
    primary = read_csv(TABLE_ROOT / "primary_performance.csv")
    run_1 = next(row for row in primary if row["run"] == "skillopt_v2_gpt4o" and row["condition"] == "Post-optimisation")
    correction[MODEL_ORDER.index("GPT-4o"), interventions.index("Primary GPT-4o learned skill")] = float(run_1["estimate_pct"])
    secondary = read_csv(TABLE_ROOT / "secondary_heldout_performance.csv")
    gpt4o_nfp = next(row for row in secondary if row["condition_dir"] == "skillopt_v2_gpt4o_best_gpt-4o-2024-11-20_nfp_run1")
    specificity[MODEL_ORDER.index("GPT-4o"), interventions.index("Primary GPT-4o learned skill")] = float(gpt4o_nfp["estimate_pct_conservative"])
    figure, (left, right) = plt.subplots(1, 2, figsize=(7.09, 3.65), gridspec_kw={"width_ratios": [1, 1]})
    figure.subplots_adjust(left=0.17, right=0.99, bottom=0.24, top=0.92, wspace=0.16)
    heatmap(left, correction, MODEL_ORDER, short, "A  FP correction", CORRECTION_CMAP)
    heatmap(right, specificity, MODEL_ORDER, short, "B  NFP accuracy", ACCURACY_CMAP)
    right.set_yticklabels([])
    save(figure, "figure_4_cross_model")


def figure_5_skill_portability() -> None:
    portability = read_csv(TABLE_ROOT / "independent_skill_portability.csv")
    themes = read_csv(TABLE_ROOT / "independent_skill_themes.csv")
    common_models = ["Llama 3.3 70B", "GPT-5.4", "Gemini 3.5 Flash"]
    skills = ["Primary skill", "Replicate 1", "Replicate 2"]
    lookup = {(row["recipient_model"], row["skill"]): float(row["correction_pct"]) for row in portability}
    p_matrix = np.array([[lookup.get((model, skill), np.nan) for skill in skills] for model in common_models])
    theme_order = [
        "Checks the question's assumption",
        "Corrects before giving advice",
        "States the assumption is wrong\nand replaces it",
        "Uses conditional wording",
        "Explains relevant clinical factors",
        "Recommends oncology-team input",
        "Avoids advice that reinforces\nthe false assumption",
        "Uses supportive language",
    ]
    source_theme_order = ["Premise audit", "Correction before advice", "Explicit negate-then-replace template", "Conditional framing", "Clinical determinants", "Oncology-team referral", "Avoid downstream reinforcement", "Supportive or empathetic tone"]
    t_lookup = {(row["theme"], row["skill"]): int(row["present"]) for row in themes}
    t_matrix = np.array([[t_lookup[(source_theme, skill)] for skill in skills] for source_theme in source_theme_order])

    run_labels = ["Run 1", "Run 2", "Run 3"]
    x = np.arange(3)
    figure, (left, right) = plt.subplots(1, 2, figsize=(8.5, 4.35), gridspec_kw={"width_ratios": [1, 1]})
    figure.subplots_adjust(left=0.08, right=0.99, bottom=0.22, top=0.90, wspace=0.55)
    model_colors = [ORANGE, BLUE, GREEN]
    model_markers = ["o", "s", "D"]
    for row, (model, color, marker) in enumerate(zip(common_models, model_colors, model_markers, strict=True)):
        values = p_matrix[row]
        left.plot(x, values, color=color, marker=marker, markersize=5.5, linewidth=1.8, label=model, zorder=3)
        for x_value, value in zip(x, values, strict=True):
            left.annotate(
                f"{value:.0f}",
                (x_value, value),
                xytext=(0, 7 if model != "Gemini 3.5 Flash" else -11),
                textcoords="offset points",
                ha="center",
                fontsize=6.8,
                color=color,
                fontweight="bold",
            )
    left.set_xlim(-0.25, 2.25)
    left.set_ylim(48, 102)
    left.set_xticks(x, run_labels)
    left.set_ylabel("FP correction after transfer (%)")
    left.set_title("A  Transfer performance by learning run", loc="left", fontweight="bold")
    left.grid(axis="y", color=GRID, linewidth=0.55)
    left.spines[["top", "right"]].set_visible(False)
    left.legend(frameon=False, loc="lower right", fontsize=6.7, handlelength=1.7)

    right.set_xlim(-0.5, 2.5)
    right.set_ylim(len(theme_order) - 0.5, -0.5)
    right.set_facecolor("white")
    for row in range(t_matrix.shape[0]):
        for column in range(t_matrix.shape[1]):
            if t_matrix[row, column]:
                color = ORANGE if row == 2 else GREEN
                right.text(column, row, "✓", ha="center", va="center", fontsize=10, fontweight="bold", color=color, zorder=2)
            else:
                right.text(column, row, "–", ha="center", va="center", fontsize=8, color="#A8B0B6", zorder=2)
    right.set_xticks(x, run_labels)
    right.set_yticks(range(len(theme_order)), theme_order)
    right.tick_params(length=0, axis="both", labelsize=6.8)
    right.set_title("B  Instructions explicitly present in each skill", loc="left", fontweight="bold")
    right.spines[["top", "right", "bottom", "left"]].set_visible(False)
    for boundary in np.arange(-0.5, len(theme_order), 1):
        right.axhline(boundary, color=GRID, linewidth=0.45, zorder=0)
    for boundary in np.arange(-0.5, 3, 1):
        right.axvline(boundary, color="#EEF1F2", linewidth=0.45, zorder=0)
    right.add_patch(Rectangle((0.5, 1.5), 1, 1, fill=False, edgecolor=ORANGE, linewidth=1.1, zorder=3))
    figure.text(
        0.56,
        0.055,
        "Run 2 alone explicitly instructed the model to reject an incorrect assumption and replace it with accurate framing.",
        ha="left",
        va="center",
        fontsize=6.6,
        color=ORANGE,
    )
    save(figure, "figure_5_skill_portability")


def figure_6_prompt_strategy() -> None:
    rows = read_csv(TABLE_ROOT / "prompt_strategy_grid.csv")
    interventions = ["Natural-language instruction", "Approximately 5k-character instruction", "Approximately 2k-character instruction", "Size-matched few-shot examples"]
    labels = ["Long rules\n14.7k", "Medium rules\n5.8k", "Short rules\n2.8k", "Few-shot\n6.0k"]
    correction = grid_matrix(rows, interventions, "correction_pct")
    specificity = grid_matrix(rows, interventions, "specificity_pct")
    figure, (left, right) = plt.subplots(1, 2, figsize=(7.09, 3.9))
    figure.subplots_adjust(left=0.17, right=0.97, bottom=0.25, top=0.93, wspace=0.28)
    heatmap(left, correction, MODEL_ORDER, labels, "A  FP correction", CORRECTION_CMAP)
    heatmap(right, specificity, MODEL_ORDER, labels, "B  NFP accuracy", ACCURACY_CMAP)
    right.set_yticklabels([])
    save(figure, "figure_6_prompt_strategy")


def figure_7_generalisation() -> None:
    rows = read_csv(TABLE_ROOT / "generalisation_summary.csv")
    sets = ["Near-transfer expansion A", "Far-transfer expansion B1", "Adversarial true-premise controls B2"]
    models = ["GPT-4o", "GPT-5.4", "Llama 3.3 70B"]
    arms = ["Baseline", "Few-shot", "Learned skill"]
    colors = [MID, BLUE, ORANGE]
    lookup = {(row["set"], row["model"], row["arm"]): float(row["success_pct"]) for row in rows}
    figure, axes = plt.subplots(1, 3, figsize=(7.09, 3.1), sharey=True)
    figure.subplots_adjust(left=0.08, right=0.99, bottom=0.24, top=0.82, wspace=0.20)
    x = np.arange(3)
    width = 0.24
    for axis, set_name in zip(axes, sets, strict=True):
        for arm_index, (arm, color) in enumerate(zip(arms, colors, strict=True)):
            values = [lookup[(set_name, model, arm)] for model in models]
            bars = axis.bar(x + (arm_index - 1) * width, values, width, color=color, label=arm)
            for bar, value in zip(bars, values, strict=True):
                axis.text(bar.get_x() + bar.get_width() / 2, min(value + 2, 102), f"{value:.0f}", ha="center", va="bottom", fontsize=6.9, color=color, fontweight="bold")
        axis.set_xticks(x, models, rotation=25, ha="right")
        axis.set_ylim(0, 108)
        axis.grid(False)
        axis.spines[["top", "right"]].set_visible(False)
        title = {sets[0]: "A  New FP questions\nsame format (n=50)", sets[1]: "B  New FP questions\ndifferent formats (n=50)", sets[2]: "C  Valid assumptions\n(n=25)"}[set_name]
        axis.set_title(title, loc="left", fontweight="bold")
    axes[0].set_ylabel("Correct response (%)")
    handles = [Line2D([0], [0], color=color, lw=6, label="No instruction" if arm == "Baseline" else "SkillOpt" if arm == "Learned skill" else arm) for arm, color in zip(arms, colors, strict=True)]
    figure.legend(handles=handles, frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.52, 0.99), fontsize=7)
    save(figure, "figure_7_generalisation")


def main() -> None:
    setup()
    figure_1_architecture()
    figure_2_native_efficacy()
    figure_3_learning_dynamics()
    figure_4_cross_model()
    figure_5_skill_portability()
    figure_6_prompt_strategy()
    figure_7_generalisation()
    package_source_data()
    print(f"Generated 7 publication figures in {FIGURE_ROOT}.")


if __name__ == "__main__":
    main()
