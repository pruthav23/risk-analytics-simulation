"""Real-estate risk mitigation matrix: probability thresholds -> strategy."""

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from common import heading, save, set_style
from risk.data import load_mitigation_matrix
from risk.mitigation import recommend

LEVELS = ["Low", "Medium", "High"]
LEVEL_LABELS = ["Low risk\nP < 40%", "Medium risk\n40% ≤ P < 65%", "High risk\nP ≥ 65%"]
LEVER_COLOURS = {
    "Low-cost action": "#d5f5e3",
    "Cash reserve": "#d6eaf8",
    "Cash-flow timing": "#aed6f1",
    "Operating cost": "#fcf3cf",
    "Revenue (NOI protection)": "#fad7a0",
    "Capital investment (CapEx)": "#f5b7b1",
}
EXAMPLE_PROBABILITIES = [0.25, 0.40, 0.64, 0.65, 0.80]


def wrap(text, width=24):
    words, lines, line = text.split(), [], ""
    for word in words:
        if len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return "\n".join(lines + [line])


def plot_matrix(matrix):
    risks = list(dict.fromkeys(matrix["risk"]))
    figure, axis = plt.subplots(figsize=(12, 7.5))
    for row, risk in enumerate(risks):
        for col, level in enumerate(LEVELS):
            entry = matrix[(matrix["risk"] == risk) & (matrix["level"] == level)].iloc[0]
            axis.add_patch(plt.Rectangle((col, row), 1, 1, facecolor=LEVER_COLOURS[entry.lever],
                                         edgecolor="white", linewidth=3))
            axis.text(col + 0.5, row + 0.5, wrap(entry.strategy), ha="center", va="center",
                      fontsize=9)
    axis.set_xlim(0, 3)
    axis.set_ylim(len(risks), 0)
    axis.set_xticks([0.5, 1.5, 2.5], LEVEL_LABELS)
    axis.xaxis.tick_top()
    axis.set_yticks([i + 0.5 for i in range(len(risks))], [wrap(r, 30) for r in risks])
    axis.grid(False)
    for spine in axis.spines.values():
        spine.set_visible(False)
    axis.set_title("Real-Estate Risk Mitigation Matrix", fontweight="bold", pad=45)
    axis.legend(handles=[Patch(facecolor=c, label=l) for l, c in LEVER_COLOURS.items()],
                loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=3, frameon=False)
    save(figure, "mitigation_matrix.png")


def main():
    set_style()
    matrix = load_mitigation_matrix()

    heading("1) MITIGATION MATRIX (strategy chosen for each risk level)")
    for risk, group in matrix.groupby("risk", sort=False):
        print(f"  {risk}")
        for entry in group.itertuples():
            print(f"    {entry.level:<7} {entry.strategy:<52} [{entry.lever}]")

    heading("2) HOW THE RESPONSE ESCALATES WITH RISK LEVEL")
    print(f"  {'Lever':<28}" + "".join(f"{level:>8}" for level in LEVELS))
    counts = matrix.groupby(["lever", "level"]).size().unstack(fill_value=0)
    for lever in LEVER_COLOURS:
        row = counts.loc[lever] if lever in counts.index else None
        cells = "".join(f"{(row[level] if row is not None and level in row else 0):>8}"
                        for level in LEVELS)
        print(f"  {lever:<28}{cells}")
    print("  Low risk -> low-cost and reserve actions; medium -> operating and cash-flow")
    print("  measures; high -> capital investment (CapEx) or direct revenue moves to protect NOI.")

    heading("3) PROBABILITY -> STRATEGY (property tax increase, boundary check)")
    for p in EXAMPLE_PROBABILITIES:
        result = recommend(matrix, "An increase in property taxes", p)
        print(f"  P = {p:.0%}  ->  {result['level']:<7} {result['strategy']}")

    plot_matrix(matrix)


if __name__ == "__main__":
    main()
