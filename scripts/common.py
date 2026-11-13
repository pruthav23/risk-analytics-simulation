"""Shared helpers for the report scripts."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import seaborn as sns  # noqa: E402

from risk.data import FIGURES_DIR  # noqa: E402

CATEGORY_COLOURS = {"Low Risk": "#2e7d32", "Medium Risk": "#f9a825", "High Risk": "#c62828"}


def set_style():
    sns.set_theme(style="whitegrid", context="notebook")


def shade_risk_bands(axis, vertical=False):
    """Background bands for the scorecard's High / Medium / Low ranges."""
    span = axis.axvspan if vertical else axis.axhspan
    span(0, 33, color=CATEGORY_COLOURS["High Risk"], alpha=0.07, zorder=0)
    span(33, 66, color=CATEGORY_COLOURS["Medium Risk"], alpha=0.07, zorder=0)
    span(66, 100, color=CATEGORY_COLOURS["Low Risk"], alpha=0.07, zorder=0)


def save(figure, name):
    FIGURES_DIR.mkdir(exist_ok=True)
    figure.savefig(FIGURES_DIR / name, dpi=200, bbox_inches="tight")
    plt.close(figure)
    print(f"  saved figures/{name}")


def heading(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)
