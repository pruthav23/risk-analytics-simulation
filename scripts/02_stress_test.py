"""Stress-test the personas under borrower events and macro shocks."""

import matplotlib.pyplot as plt

from common import CATEGORY_COLOURS, heading, save, set_style, shade_risk_bands
from risk import stress
from risk.data import load_personas


def print_results(results, scenario):
    for r in results:
        moved = "" if r["category_before"] == r["category_after"] else "  <- category change"
        print(f"    {r['persona']:<10} score {r['score_before']:5.1f} -> {r['score_after']:5.1f}"
              f"   DTI {r['dti_before']:5.0%} -> {r['dti_after']:5.0%}"
              f"   {r['category_after']}{moved}")
    if not scenario.model_captures:
        print("    (scorecard inputs unchanged: the benefit is real but the model cannot see it)")


def plot_macro(personas):
    figure, axis = plt.subplots(figsize=(9, 4.5))
    shade_risk_bands(axis)
    stages = ["Baseline", "Mild downturn", "Severe recession"]
    finals = {}
    for persona in personas:
        baseline = stress.run(stress.MACRO_SHOCKS[0], [persona])[0]["score_before"]
        scores = [baseline] + [stress.run(s, [persona])[0]["score_after"]
                               for s in stress.MACRO_SHOCKS]
        line, = axis.plot(stages, scores, marker="o", linewidth=2, label=persona.name)
        finals[persona.name] = (scores[-1], line.get_color())

    # Final-score labels, nudged apart so close values do not overlap.
    label_y = None
    for name, (score, colour) in sorted(finals.items(), key=lambda item: item[1][0]):
        y = score if label_y is None else max(score, label_y + 3.5)
        axis.text(2.06, y - 2.5, f"{score:.1f}", fontsize=9, color=colour,
                  fontweight="bold", va="center")
        label_y = y
    axis.axhline(66, color=CATEGORY_COLOURS["Low Risk"], linestyle="--", linewidth=1)
    axis.axhline(33, color=CATEGORY_COLOURS["High Risk"], linestyle="--", linewidth=1)
    axis.text(2.25, 67, "Low risk above 66", fontsize=8, color=CATEGORY_COLOURS["Low Risk"])
    axis.text(2.25, 30, "High risk below 33", fontsize=8, color=CATEGORY_COLOURS["High Risk"])
    axis.set_ylim(20, 95)
    axis.set_xlim(-0.2, 2.6)
    axis.set_ylabel("Risk score (higher = safer)")
    axis.set_title("Macro Stress Test: Persona Risk Scores", fontweight="bold")
    axis.legend(loc="upper right", fontsize=9)
    save(figure, "macro_stress_test.png")


def main():
    set_style()
    personas = load_personas()

    heading("1) BORROWER EVENTS (from the simulation's scenario questions)")
    for scenario in stress.BORROWER_EVENTS:
        print(f"  {scenario.name} [{scenario.persona}]")
        print(f"    {scenario.describe}")
        print(f"    Expected effect: {scenario.expected_direction}")
        print_results(stress.run(scenario, personas), scenario)

    heading("2) MACRO SHOCKS (applied to all personas)")
    for scenario in stress.MACRO_SHOCKS:
        print(f"  {scenario.name}: {scenario.describe}")
        print_results(stress.run(scenario, personas), scenario)

    plot_macro(personas)


if __name__ == "__main__":
    main()
