"""
Exploratory Data Analysis (EDA) for the combined ASD-project features.

Produces:
    reports/figures/group_counts.png
    reports/figures/age_distribution.png
    reports/figures/feature_boxplots.png
    reports/figures/correlation_heatmap.png
    reports/figures/feature_pairplot.png
    reports/metrics/summary_stats.csv
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FIG_DIR = PROJECT_ROOT / "reports" / "figures"
METRIC_DIR = PROJECT_ROOT / "reports" / "metrics"
FIG_DIR.mkdir(parents=True, exist_ok=True)
METRIC_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="talk")

GROUP_ORDER = ["TD", "DD", "ASD"]
GROUP_PALETTE = {"TD": "#4C9F70", "DD": "#E7B416", "ASD": "#C0392B"}

FEATURES = [
    "age_months",
    "total_utterances",
    "mlu",
    "mluw",
    "ttr",
    "total_words",
    "unintelligible_ratio",
    "zero_vocalization_count",
    "nonverbal_vocalization_count",
    "question_ratio",
]


def _save(fig, name: str) -> None:
    path = FIG_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved  {path.relative_to(PROJECT_ROOT)}")


def plot_group_counts(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.countplot(
        data=df, x="group", hue="corpus",
        order=GROUP_ORDER, ax=ax,
    )
    ax.set_title("Sample counts per group (by corpus)")
    ax.set_xlabel("Group")
    ax.set_ylabel("Number of children")
    for c in ax.containers:
        ax.bar_label(c, padding=2, fontsize=11)
    _save(fig, "group_counts.png")


def plot_age_distribution(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.boxplot(
        data=df, x="group", y="age_months",
        order=GROUP_ORDER, palette=GROUP_PALETTE, ax=ax,
    )
    sns.stripplot(
        data=df, x="group", y="age_months",
        order=GROUP_ORDER, color="black", alpha=0.4, size=4, ax=ax,
    )
    ax.set_title("Age distribution by group")
    ax.set_ylabel("Age (months)")
    _save(fig, "age_distribution.png")


def plot_feature_boxplots(df: pd.DataFrame) -> None:
    core = ["mlu", "mluw", "ttr", "total_words",
            "unintelligible_ratio", "question_ratio"]
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    for ax, feat in zip(axes.flat, core):
        sns.boxplot(
            data=df, x="group", y=feat,
            order=GROUP_ORDER, palette=GROUP_PALETTE, ax=ax,
        )
        ax.set_title(feat)
        ax.set_xlabel("")
    fig.suptitle("Linguistic features by group", y=1.02)
    fig.tight_layout()
    _save(fig, "feature_boxplots.png")


def plot_correlation_heatmap(df: pd.DataFrame) -> None:
    corr = df[FEATURES].corr(numeric_only=True)
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        corr, annot=True, fmt=".2f", cmap="coolwarm",
        center=0, vmin=-1, vmax=1, ax=ax,
    )
    ax.set_title("Feature correlation matrix")
    _save(fig, "correlation_heatmap.png")


def plot_pairplot(df: pd.DataFrame) -> None:
    cols = ["mlu", "ttr", "total_words", "unintelligible_ratio", "group"]
    g = sns.pairplot(
        df[cols].dropna(), hue="group",
        hue_order=GROUP_ORDER, palette=GROUP_PALETTE,
        diag_kind="kde", plot_kws={"alpha": 0.7, "s": 30},
    )
    g.fig.suptitle("Pairwise feature relationships", y=1.02)
    path = FIG_DIR / "feature_pairplot.png"
    g.fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(g.fig)
    print(f"  saved  {path.relative_to(PROJECT_ROOT)}")


def save_summary_stats(df: pd.DataFrame) -> None:
    summary = (
        df.groupby("group")[FEATURES]
        .agg(["mean", "std", "median", "count"])
        .round(3)
    )
    out = METRIC_DIR / "summary_stats.csv"
    summary.to_csv(out)
    print(f"  saved  {out.relative_to(PROJECT_ROOT)}")
    print("\nPer-group summary (mean ± std):")
    for feat in ["age_months", "mlu", "ttr", "total_words", "unintelligible_ratio"]:
        print(f"\n  {feat}:")
        for g in GROUP_ORDER:
            sub = df[df["group"] == g][feat].dropna()
            if len(sub):
                print(f"    {g:4s}  n={len(sub):3d}  "
                      f"{sub.mean():.3f} ± {sub.std():.3f}")


def main() -> None:
    csv_path = DATA_DIR / "combined_features.csv"
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} rows from {csv_path.relative_to(PROJECT_ROOT)}\n")

    print("Generating figures...")
    plot_group_counts(df)
    plot_age_distribution(df)
    plot_feature_boxplots(df)
    plot_correlation_heatmap(df)
    plot_pairplot(df)

    print("\nComputing summary statistics...")
    save_summary_stats(df)

    print("\n[done] EDA complete.")


if __name__ == "__main__":
    main()
