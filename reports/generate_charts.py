"""
Generate comparison charts for Lab 2 — Chunking Benchmark.
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


def load_results(filepath: str = "data/chunks/benchmark_results.json") -> list:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def plot_metrics_comparison(results: list, output_dir: str = "reports"):
    """Bar chart comparing all metrics across strategies."""
    strategies = [r["strategy"] for r in results]
    metrics = ["recall@1", "recall@3", "recall@5", "hitrate@1", "hitrate@3", "mrr"]

    x = np.arange(len(strategies))
    width = 0.12
    colors = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#F44336", "#00BCD4"]

    fig, ax = plt.subplots(figsize=(14, 7))

    for i, metric in enumerate(metrics):
        values = [r[metric] for r in results]
        bars = ax.bar(x + i * width, values, width, label=metric.upper(), color=colors[i])
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f"{val:.3f}", ha="center", va="bottom", fontsize=7, rotation=90)

    ax.set_xlabel("Chunking Strategy")
    ax.set_ylabel("Score")
    ax.set_title("Chunking Benchmark: Retrieval Quality by Strategy", fontweight="bold")
    ax.set_xticks(x + width * 2.5)
    ax.set_xticklabels(strategies, fontsize=11)
    ax.legend(loc="lower right", ncol=3)
    ax.set_ylim(0, 1.15)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    output_path = Path(output_dir) / "metrics_comparison.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def plot_chunk_distribution(results: list, output_dir: str = "reports"):
    """Pie chart showing chunk counts per strategy."""
    import json
    from pathlib import Path

    chunks_dir = Path("data/chunks")
    strategies = []
    counts = []

    for f in sorted(chunks_dir.glob("chunks_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        strategies.append(f.stem.replace("chunks_", ""))
        counts.append(len(data))

    colors = ["#2196F3", "#4CAF50", "#FF9800", "#F44336"]
    explode = (0, 0, 0.1, 0)

    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, texts, autotexts = ax.pie(
        counts, labels=strategies, autopct="%1.1f%%",
        colors=colors, explode=explode,
        startangle=140, textprops={"fontsize": 11}
    )
    ax.set_title(f"Chunk Distribution: {sum(counts)} Total Chunks", fontweight="bold")

    plt.tight_layout()
    output_path = Path(output_dir) / "chunk_distribution.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def plot_mrr_focused(results: list, output_dir: str = "reports"):
    """Focused bar chart on MRR — the most important metric."""
    strategies = [r["strategy"] for r in results]
    mrr_values = [r["mrr"] for r in results]

    colors = ["#2196F3", "#4CAF50", "#FF9800", "#F44336"]
    best_idx = mrr_values.index(max(mrr_values))
    colors[best_idx] = "#FFD700"

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(strategies, mrr_values, color=colors, edgecolor="black", linewidth=1.5)

    for bar, val in zip(bars, mrr_values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.015,
                f"{val:.3f}", ha="center", fontsize=14, fontweight="bold")

    ax.set_ylabel("MRR Score", fontsize=12)
    ax.set_title("Most Important: Mean Reciprocal Rank (MRR)", fontweight="bold", fontsize=14)
    ax.set_ylim(0, 1.2)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    output_path = Path(output_dir) / "mrr_comparison.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    results = load_results()

    print("Generating charts...")
    plot_metrics_comparison(results)
    plot_chunk_distribution(results)
    plot_mrr_focused(results)
    print("Done! All charts saved to reports/")