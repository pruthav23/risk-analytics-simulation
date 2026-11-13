"""Credit metrics and a weighted risk scorecard for individual borrowers.

The scorecard follows the simulation's Risk Calculator: each attribute is
normalised to 0-100, weighted, and summed. A higher score means a
stronger borrower (lower risk).

The original calculator added *debt* and *late payments* to the score
without inverting them, so more debt or more missed payments made a
borrower look safer. `scorecard(..., corrected=True)` fixes that by using
100 minus the normalised value for those two attributes.
"""

from dataclasses import dataclass, replace

WEIGHTS = {
    "credit_score": 0.25,
    "annual_income": 0.20,
    "debt": 0.20,
    "savings": 0.25,
    "late_payments": 0.10,
}

# Attributes where a larger value means MORE risk.
ADVERSE = {"debt", "late_payments"}

HIGH_RISK_MAX = 33     # score <= 33  -> High Risk
MEDIUM_RISK_MAX = 66   # score <= 66  -> Medium Risk, above -> Low Risk


@dataclass(frozen=True)
class Borrower:
    name: str
    annual_income: float
    credit_score: float
    debt: float
    savings: float
    late_payments: int

    def adjust(self, **changes):
        """Return a copy with some attributes changed (used for scenarios)."""
        return replace(self, **changes)


def debt_to_income(borrower):
    """Total debt divided by annual income.

    Note: this is a leverage ratio on *total* debt. Lenders' DTI usually
    means monthly debt *payments* over gross monthly income, which needs
    payment data the simulation does not provide.
    """
    return borrower.debt / borrower.annual_income


def net_liquid_assets(borrower):
    """Savings minus total debt: the cushion left if all debt were repaid."""
    return borrower.savings - borrower.debt


def normalise(borrower):
    """Each attribute on a 0-100 scale, using the calculator's caps."""
    return {
        "credit_score": (borrower.credit_score - 300) / (850 - 300) * 100,
        "annual_income": min(borrower.annual_income / 300_000, 1) * 100,
        "debt": min(borrower.debt / 300_000, 1) * 100,
        "savings": min(borrower.savings / 500_000, 1) * 100,
        "late_payments": min(borrower.late_payments / 5, 1) * 100,
    }


def contributions(borrower, corrected=True):
    """Weighted points each attribute adds to the score."""
    points = {}
    for attribute, value in normalise(borrower).items():
        if corrected and attribute in ADVERSE:
            value = 100 - value
        points[attribute] = value * WEIGHTS[attribute]
    return points


def scorecard(borrower, corrected=True):
    return sum(contributions(borrower, corrected).values())


def risk_category(score):
    if score <= HIGH_RISK_MAX:
        return "High Risk"
    if score <= MEDIUM_RISK_MAX:
        return "Medium Risk"
    return "Low Risk"


def assess(borrower, corrected=True):
    score = scorecard(borrower, corrected)
    return {
        "persona": borrower.name,
        "dti": debt_to_income(borrower),
        "net_liquid_assets": net_liquid_assets(borrower),
        "score": score,
        "category": risk_category(score),
    }
