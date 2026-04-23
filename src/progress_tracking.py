"""
Longitudinal progress tracking for combined corpora (21 children:
Rollins 5 + Flusberg 6 + Quigley 10, each with multiple sessions).

For each child we track the trajectory of core speech-language features
across sessions and fit a simple linear trend.  This mirrors the clinical
question raised by the advisor:

    "Can AI tell whether the child's speech improves from session to session?"

Outputs:
    reports/figures/longitudinal_trajectories.png      (per-feature, per-child lines)
    reports/figures/longitudinal_composite_score.png   (composite progress score)
    reports/metrics/longitudinal_trends.csv            (slope, r, p per child-feature)
    reports/metrics/longitudinal_progress_summary.csv  (first vs last session delta)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FIG_DIR = PROJECT_ROOT / "reports" / "figures"
METRIC_DIR = PROJECT_ROOT / "reports" / "metrics"
FIG_DIR.mkdir(parents=True, exist_ok=True)
METRIC_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="talk")

# Features we expect to IMPROVE over therapy.
# +1 = higher is better  |  -1 = lower is better
FEATURE_DIRECTION = {
    "mlu": +1,
    "mluw": +1,
    "ttr": +1,
    "total_words": +1,
    "total_utterances": +1,
    "unintelligible_ratio": -1,
    "zero_vocalization_count": -1,
}


def compute_trends(df: pd.DataFrame) -> pd.DataFrame:
    """Fit a linear regression of feature ~ session_order for each child-feature."""
    rows = []
    for child, g in df.groupby("child"):
        g = g.sort_values("session_order")
        x = g["session_order"].to_numpy(dtype=float)
        for feat, direction in FEATURE_DIRECTION.items():
            y = g[feat].to_numpy(dtype=float)
            if len(x) < 2 or np.all(np.isnan(y)):
                continue
            res = stats.linregress(x, y)
            improving = (res.slope * direction) > 0
            rows.append({
                "child": child,
                "feature": feat,
                "direction": "higher=better" if direction > 0 else "lower=better",
                "slope": round(res.slope, 4),
                "intercept": round(res.intercept, 4),
                "r": round(res.rvalue, 4),
                "p_value": round(res.pvalue, 4),
                "n_sessions": len(x),
                "improving": bool(improving),
            })
    return pd.DataFrame(rows)


def compute_progress_summary(df: pd.DataFrame) -> pd.DataFrame:
    """First vs last session delta per child."""
    rows = []
    for child, g in df.groupby("child"):
        g = g.sort_values("session_order")
        first, last = g.iloc[0], g.iloc[-1]
        row = {
            "child": child,
            "n_sessions": len(g),
            "age_start_mo": first["age_months"],
            "age_end_mo": last["age_months"],
            "duration_mo": (
                round(last["age_months"] - first["age_months"], 1)
                if pd.notna(last["age_months"]) and pd.notna(first["age_months"])
                else np.nan
            ),
        }
        for feat in FEATURE_DIRECTION:
            row[f"{feat}_start"] = round(first[feat], 3)
            row[f"{feat}_end"] = round(last[feat], 3)
            row[f"{feat}_delta"] = round(last[feat] - first[feat], 3)
        rows.append(row)
    return pd.DataFrame(rows)


def plot_trajectories(df: pd.DataFrame) -> None:
    feats = list(FEATURE_DIRECTION.keys())
    fig, axes = plt.subplots(3, 3, figsize=(18, 14))

    # Create child+corpus label for clarity
    df = df.copy()
    df["child_label"] = df["child"] + " (" + df["corpus"].str[:4] + ")"

    for ax, feat in zip(axes.flat, feats):
        sns.lineplot(
            data=df, x="session_order", y=feat,
            hue="child_label", marker="o", ax=ax,
        )
        ax.set_title(feat)
        ax.set_xlabel("Session order")
        ax.set_ylabel("")
        ax.legend(fontsize=8, loc="best")
    # Hide unused subplots
    for ax in axes.flat[len(feats):]:
        ax.set_visible(False)
    fig.suptitle("Longitudinal: per-child trajectories across sessions\n(Rollins + Flusberg + Quigley)", y=1.00)
    fig.tight_layout()
    out = FIG_DIR / "longitudinal_trajectories.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved  {out.relative_to(PROJECT_ROOT)}")


def compute_composite_score(df: pd.DataFrame) -> pd.DataFrame:
    """Per-session composite score: z-scored features combined with direction.

    Score = mean over features of (z(feature) * direction).
    Higher = better / more typical language production.
    """
    df = df.copy()
    zdf = pd.DataFrame(index=df.index)
    for feat, direction in FEATURE_DIRECTION.items():
        x = df[feat].astype(float)
        mu, sd = x.mean(), x.std(ddof=0)
        if sd == 0 or np.isnan(sd):
            zdf[feat] = 0.0
        else:
            zdf[feat] = direction * (x - mu) / sd
    df["composite_score"] = zdf.mean(axis=1)
    return df


def plot_composite(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 7))

    # Create child+corpus label for clarity
    df = df.copy()
    df["child_label"] = df["child"] + " (" + df["corpus"].str[:4] + ")"

    sns.lineplot(
        data=df, x="session_order", y="composite_score",
        hue="child_label", marker="o", linewidth=2.5, ax=ax,
    )
    ax.axhline(0, color="gray", linestyle="--", alpha=0.5)
    ax.set_title("Longitudinal composite progress score\n(z-scored, direction-adjusted)\n(Rollins + Flusberg + Quigley)")
    ax.set_xlabel("Session order")
    ax.set_ylabel("Composite score (higher = better)")
    fig.tight_layout()
    out = FIG_DIR / "longitudinal_composite_score.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved  {out.relative_to(PROJECT_ROOT)}")


def main() -> None:
    csv_path = DATA_DIR / "longitudinal_features.csv"
    df = pd.read_csv(csv_path)
    df = df.sort_values(["child", "session_order"]).reset_index(drop=True)
    print(f"Loaded {len(df)} sessions from {df['corpus'].nunique()} corpora "
          f"for {df['child'].nunique()} children.\n")
    print("Corpus distribution:")
    print(df.groupby("corpus")["child"].nunique())
    print()

    # Per-child per-feature linear trends
    trends = compute_trends(df)
    # Add corpus info to trends
    child_corpus = df.groupby("child")["corpus"].first().to_dict()
    trends["corpus"] = trends["child"].map(child_corpus)
    out = METRIC_DIR / "longitudinal_trends.csv"
    trends.to_csv(out, index=False)
    print(f"[saved] {out.relative_to(PROJECT_ROOT)}")

    # First-vs-last session summary
    summary = compute_progress_summary(df)
    # Add corpus info to summary
    summary["corpus"] = summary["child"].map(child_corpus)
    out = METRIC_DIR / "longitudinal_progress_summary.csv"
    summary.to_csv(out, index=False)
    print(f"[saved] {out.relative_to(PROJECT_ROOT)}")

    # Plots
    plot_trajectories(df)
    df_c = compute_composite_score(df)
    plot_composite(df_c)

    # Print human-readable verdict
    print("\n=== Per-child improvement summary ===")
    improved_flags = (
        trends.groupby("child")["improving"].sum()
        .reindex(sorted(trends["child"].unique()))
    )
    total_feats = len(FEATURE_DIRECTION)
    for child, n_improved in improved_flags.items():
        verdict = "IMPROVING" if n_improved > total_feats / 2 else "mixed / stalling"
        print(f"  {child:8s}  {int(n_improved)}/{total_feats} features improving  ->  {verdict}")

    print("\n=== Top improving child-feature pairs (by |r|) ===")
    sig = trends[trends["improving"]].copy()
    sig = sig.reindex(sig["r"].abs().sort_values(ascending=False).index)
    print(sig.head(10).to_string(index=False))

    print("\n=== Composite score: first vs last session ===")
    for child, g in df_c.groupby("child"):
        g = g.sort_values("session_order")
        first = g["composite_score"].iloc[0]
        last = g["composite_score"].iloc[-1]
        arrow = "↑" if last > first else "↓"
        print(f"  {child:8s}  {first:+.2f}  ->  {last:+.2f}   "
              f"({arrow} delta = {last - first:+.2f})")

    print("\n[done] progress tracking complete.")


if __name__ == "__main__":
    main()
