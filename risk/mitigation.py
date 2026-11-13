"""Real-estate risk mitigation matrix.

Each property risk is given a probability P of occurring. P sets the risk
level, and the level selects a mitigation strategy:

    Low risk     P < 40%          low-cost, non-disruptive, research-oriented
    Medium risk  40% <= P < 65%   targeted operating measures that steady cash flow
    High risk    P >= 65%         structural or capital-intensive intervention
"""

LOW_MAX = 0.40
MEDIUM_MAX = 0.65


def risk_level(probability):
    if not 0 <= probability <= 1:
        raise ValueError("probability must be between 0 and 1")
    if probability < LOW_MAX:
        return "Low"
    if probability < MEDIUM_MAX:
        return "Medium"
    return "High"


def recommend(matrix, risk, probability):
    """Strategy, lever and rationale for a risk at a given probability."""
    level = risk_level(probability)
    row = matrix[(matrix["risk"] == risk) & (matrix["level"] == level)]
    if row.empty:
        raise KeyError(f"no strategy for {risk!r} at {level} risk")
    row = row.iloc[0]
    return {
        "risk": risk,
        "probability": probability,
        "level": level,
        "strategy": row["strategy"],
        "lever": row["lever"],
        "rationale": row["rationale"],
    }
