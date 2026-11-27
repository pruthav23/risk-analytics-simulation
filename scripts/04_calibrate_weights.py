"""Test the scorecard's hand-set weights against real default data.

If data/external/cs-training.csv is present (download it from Kaggle's
"Give Me Some Credit" competition), the model is refitted and
results/calibration.json is rewritten. Otherwise the saved results are used.
"""

import matplotlib.pyplot as plt

from common import heading, save, set_style
from risk import calibration
from risk.credit import WEIGHTS, assess, risk_category
from risk.data import load_personas

SIM_SPLIT = {  # simulation weights for the three inputs the data covers, rescaled to 100%
    "income": WEIGHTS["annual_income"] / 0.5,
    "leverage": WEIGHTS["debt"] / 0.5,
    "late": WEIGHTS["late_payments"] / 0.5,
}
LABELS = {"income": "Income", "leverage": "Debt / leverage", "late": "Late payments"}


def plot_late_payments(results):
    rows = results["default_rate_by_late_payments"]
    figure, axis = plt.subplots(figsize=(8, 4.5))
    labels = [f"{r['late_payments']}" + ("+" if r["late_payments"] == 5 else "") for r in rows]
    rates = [r["default_rate"] * 100 for r in rows]
    bars = axis.bar(labels, rates, color="#1f4e79")
    for bar, row in zip(bars, rows):
        axis.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                  f"{row['default_rate']:.0%}", ha="center", fontsize=10, fontweight="bold")
        axis.text(bar.get_x() + bar.get_width() / 2, -6.5, f"n={row['borrowers']:,}",
                  ha="center", fontsize=8, color="grey")
    axis.set_ylim(-9, 66)
    axis.axhline(0, color="black", linewidth=0.8)
    axis.set_xlabel("Late payments in the last two years", labelpad=14)
    axis.set_ylabel("Defaulted within 2 years (%)")
    axis.set_title(f"Default rate by payment history ({results['borrowers']:,} real borrowers)",
                   fontweight="bold")
    save(figure, "default_rate_by_late_payments.png")


def plot_weights(results):
    shares = calibration.data_shares(results)
    figure, axis = plt.subplots(figsize=(8, 3.8))
    for y, key in enumerate(["late", "income", "leverage"]):
        sim, data = SIM_SPLIT[key] * 100, shares[key] * 100
        axis.plot([sim, data], [y, y], color="grey", linewidth=2, zorder=1)
        axis.scatter([sim], [y], s=110, facecolors="white", edgecolors="black", zorder=2,
                     label="Simulation (hand-set)" if y == 0 else None)
        axis.scatter([data], [y], s=110, color="#c62828", zorder=3,
                     label="Fitted to default data" if y == 0 else None)
        axis.text(sim, y + 0.28, f"{sim:.0f}%", ha="center", fontsize=9)
        axis.text(data, y + 0.28, f"{data:.0f}%", ha="center", fontsize=9, color="#c62828",
                  fontweight="bold")
    axis.set_yticks(range(3), [LABELS[k] for k in ["late", "income", "leverage"]])
    axis.set_ylim(-0.6, 2.7)
    axis.set_xlim(0, 80)
    axis.set_xlabel("Share of weight among the three inputs the data covers (%)")
    axis.set_title("Payment history matters far more than the simulation assumed",
                   fontweight="bold")
    axis.legend(loc="upper right", fontsize=9)
    save(figure, "weights_simulation_vs_data.png")


def main():
    set_style()
    if calibration.RAW_PATH.exists():
        calibration.save(calibration.fit())
        print(f"  refitted on {calibration.RAW_PATH.name}")
    results = calibration.load()

    heading("1) MODEL FITTED TO REAL DEFAULT DATA")
    print(f"  Source: {results['source']}")
    print(f"  Borrowers: {results['borrowers']:,}   default rate {results['default_rate']:.1%}")
    print(f"  Held-out AUC {results['test_auc']:.3f}   Gini {results['test_gini']:.3f}")
    print("  Default rate by late payments:")
    for row in results["default_rate_by_late_payments"]:
        print(f"    {row['late_payments']}{'+' if row['late_payments'] == 5 else ' '}"
              f"  {row['default_rate']:6.1%}   ({row['borrowers']:,} borrowers)")
    print("  Calibration on held-out borrowers (predicted vs actual, by decile):")
    print("    " + "  ".join(f"{d['predicted']:.1%}/{d['actual']:.1%}"
                             for d in results["calibration_by_decile"]))

    heading("2) WEIGHTS: SIMULATION vs DATA (three inputs the data covers)")
    shares = calibration.data_shares(results)
    print(f"  {'Input':<18}{'Simulation':>12}{'Data':>8}")
    for key in ["late", "income", "leverage"]:
        print(f"  {LABELS[key]:<18}{SIM_SPLIT[key]:>12.0%}{shares[key]:>8.0%}")
    print("  Credit score and savings are not in the dataset; they keep their 25% each.")
    weights = calibration.calibrated_weights(results)
    print("  Calibrated scorecard weights: " + ", ".join(
        f"{k.replace('_', ' ')} {v:.1%}" for k, v in weights.items()))

    heading("3) PERSONAS: PROBABILITY OF DEFAULT AND EXPECTED LOSS")
    print(f"  Assumes debt is repaid over {calibration.LOAN_MONTHS} months at "
          f"{calibration.LOAN_RATE:.0%}; LGD {calibration.LGD:.0%}; exposure = current debt.")
    print(f"  {'':<10}{'Pay/income':>11}{'2-yr PD':>9}{'Exp. loss':>11}"
          f"{'Sim score':>11}{'Calibrated':>12}")
    for persona in load_personas():
        pd_ = calibration.probability_of_default(persona, results)
        cal = calibration.calibrated_score(persona, results)
        print(f"  {persona.name:<10}{calibration.payment_to_income(persona):>11.1%}{pd_:>9.1%}"
              f"{calibration.expected_loss(persona, results):>11,.0f}"
              f"{assess(persona)['score']:>11.1f}{cal:>7.1f} {risk_category(cal)}")

    plot_late_payments(results)
    plot_weights(results)


if __name__ == "__main__":
    main()
