"""Stress tests: re-score borrowers after a shock and see how their risk moves.

Two kinds of scenario:

1. Borrower events from the simulation's scenario questions (a new mortgage,
   liquidating savings, drawing an unused credit line, ...). Where the
   question gives no amount, an illustrative amount is stated explicitly.
2. Macro shocks applied to every borrower (falling income and asset values,
   plus payment stress), to test how the portfolio behaves in a downturn.
"""

from dataclasses import dataclass, field

from risk.credit import assess


@dataclass(frozen=True)
class Scenario:
    name: str
    persona: str               # persona affected, or "All" for macro shocks
    describe: str
    changes: dict = field(default_factory=dict)   # function(borrower) -> dict of new values
    expected_direction: str = ""                  # qualitative answer to the simulation question
    model_captures: bool = True                   # can the scorecard see this change?


def _changes(**fixed):
    return lambda b: {k: v(b) if callable(v) else v for k, v in fixed.items()}


BORROWER_EVENTS = [
    Scenario(
        "New mortgage on top of existing debt", "Persona 2",
        "Takes a $300,000 mortgage (illustrative amount) without repaying the existing $100,000",
        _changes(debt=lambda b: b.debt + 300_000),
        "Increase: higher total debt",
    ),
    Scenario(
        "Debt consolidation", "Persona 3",
        "Combines debts into one loan; total debt unchanged",
        _changes(),
        "Decrease: one payment is easier to manage, often at a lower rate",
        model_captures=False,
    ),
    Scenario(
        "Liquidate assets to fund a start-up", "Persona 1",
        "Moves $200,000 of savings (illustrative amount) into a new venture",
        _changes(savings=lambda b: b.savings - 200_000),
        "Increase: smaller liquid buffer",
    ),
    Scenario(
        "Unused $10,000 credit card fully drawn", "Persona 1",
        "Worst case for an undrawn line: the full $10,000 limit becomes debt",
        _changes(debt=lambda b: b.debt + 10_000),
        "Increase (marginal): an undrawn limit is potential exposure",
    ),
    Scenario(
        "Three-year salary agreement", "Persona 2",
        "Income is contractually fixed for three years",
        _changes(),
        "Decrease: income is more certain",
        model_captures=False,
    ),
    Scenario(
        "$50,000 business loan repaid on schedule", "Persona 4",
        "Loan is already part of total debt; two years of on-time repayments",
        _changes(),
        "Decrease: proven repayment history",
        model_captures=False,
    ),
]

MACRO_SHOCKS = [
    Scenario(
        "Mild downturn", "All",
        "Income -15%, savings -20%",
        _changes(annual_income=lambda b: b.annual_income * 0.85,
                 savings=lambda b: b.savings * 0.80),
    ),
    Scenario(
        "Severe recession", "All",
        "Income -30%, savings -40%, one additional late payment",
        _changes(annual_income=lambda b: b.annual_income * 0.70,
                 savings=lambda b: b.savings * 0.60,
                 late_payments=lambda b: b.late_payments + 1),
    ),
]


def run(scenario, borrowers):
    """Assess each affected borrower before and after the scenario."""
    results = []
    for borrower in borrowers:
        if scenario.persona not in ("All", borrower.name):
            continue
        before = assess(borrower)
        after = assess(borrower.adjust(**scenario.changes(borrower)))
        results.append({
            "scenario": scenario.name,
            "persona": borrower.name,
            "score_before": before["score"],
            "score_after": after["score"],
            "category_before": before["category"],
            "category_after": after["category"],
            "dti_before": before["dti"],
            "dti_after": after["dti"],
            "nla_after": after["net_liquid_assets"],
        })
    return results
