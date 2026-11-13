"""Credit risk profiles for the four borrower personas."""

import matplotlib.pyplot as plt

from common import CATEGORY_COLOURS, heading, save, set_style, shade_risk_bands
from risk.credit import WEIGHTS, assess, contributions, scorecard
from risk.data import load_personas

LABELS = {
    "credit_score": "Credit score",
    "annual_income": "Income",
    "debt": "Low debt",
    "savings": "Savings",
    "late_payments": "Clean payment history",
}


def plot_scorecard(personas):
    figure, axis = plt.subplots(figsize=(10, 4.5))
    shade_risk_bands(axis, vertical=True)
    names = [p.name for p in personas][::-1]
    left = [0.0] * len(names)
    palette = ["#1f4e79", "#2e86c1", "#85c1e9", "#48c9b0", "#a9cce3"]
    for colour, attribute in zip(palette, WEIGHTS):
        values = [contributions(p)[attribute] for p in personas][::-1]
        axis.barh(names, values, left=left, color=colour, label=LABELS[attribute])
        left = [a + b for a, b in zip(left, values)]
    for y, persona in enumerate(personas[::-1]):
        result = assess(persona)
        label_x = max(result["score"], scorecard(persona, corrected=False)) + 2
        axis.text(label_x, y, f"{result['score']:.1f}  {result['category']}",
                  va="center", fontsize=10, fontweight="bold",
                  color=CATEGORY_COLOURS[result["category"]])
        axis.plot(scorecard(persona, corrected=False), y, marker="x", color="black",
                  markersize=9, linestyle="none",
                  label="Original calculator" if y == 0 else None)
    axis.set_xlim(0, 100)
    axis.set_xlabel("Risk score (higher = safer)   |   High < 33 < Medium < 66 < Low")
    axis.set_title("Weighted Credit Risk Scorecard by Persona", fontweight="bold")
    axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=6, frameon=False, fontsize=9)
    save(figure, "persona_scorecard.png")


def plot_leverage(personas):
    figure, axis = plt.subplots(figsize=(8, 5))
    for persona in personas:
        result = assess(persona)
        axis.scatter(result["dti"] * 100, result["net_liquid_assets"] / 1000, s=160,
                     color=CATEGORY_COLOURS[result["category"]], edgecolor="black", zorder=3)
        axis.annotate(f"{persona.name}\n{persona.late_payments} late payment(s)",
                      (result["dti"] * 100, result["net_liquid_assets"] / 1000),
                      xytext=(10, -4), textcoords="offset points", fontsize=9)
    axis.axhline(0, color="grey", linewidth=1)
    axis.axvline(100, color="grey", linewidth=1, linestyle="--")
    axis.text(102, 240, "debt exceeds\none year's income →", fontsize=8, color="grey")
    axis.set_xlim(40, 160)
    axis.set_xlabel("Debt-to-income (total debt ÷ annual income, %)")
    axis.set_ylabel("Net liquid assets ($k, savings − debt)")
    axis.set_title("Leverage vs Liquidity", fontweight="bold")
    save(figure, "leverage_vs_liquidity.png")


def main():
    set_style()
    personas = load_personas()

    heading("1) KEY CREDIT METRICS")
    print(f"  {'':<10}{'Income':>10}{'Credit':>8}{'Debt':>10}{'Savings':>10}{'Late':>6}"
          f"{'DTI':>9}{'Net liquid':>13}")
    for p in personas:
        r = assess(p)
        print(f"  {p.name:<10}{p.annual_income:>10,.0f}{p.credit_score:>8.0f}{p.debt:>10,.0f}"
              f"{p.savings:>10,.0f}{p.late_payments:>6d}{r['dti']:>9.1%}"
              f"{r['net_liquid_assets']:>+13,.0f}")

    heading("2) WEIGHTED RISK SCORECARD (corrected)")
    print("  Weights: " + ", ".join(f"{LABELS[k]} {v:.0%}" for k, v in WEIGHTS.items()))
    print(f"  {'':<10}{'Original':>10}{'Corrected':>11}  Category")
    ranked = sorted(personas, key=scorecard, reverse=True)
    for p in ranked:
        print(f"  {p.name:<10}{scorecard(p, corrected=False):>10.1f}"
              f"{scorecard(p):>11.1f}  {assess(p)['category']}")
    print("  Ranking (safest to riskiest): " + " > ".join(p.name for p in ranked))
    print("  The original calculator added debt and late payments as positives; the")
    print("  corrected version inverts them. Persona 4 (most debt) is the only one whose")
    print("  score falls after the fix.")

    plot_scorecard(personas)
    plot_leverage(personas)


if __name__ == "__main__":
    main()
