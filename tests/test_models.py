import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from risk.credit import Borrower, assess, risk_category, scorecard  # noqa: E402
from risk.data import load_mitigation_matrix, load_personas  # noqa: E402
from risk.mitigation import recommend, risk_level  # noqa: E402

BASE = Borrower("Test", annual_income=100_000, credit_score=700,
                debt=50_000, savings=50_000, late_payments=1)


def test_more_debt_lowers_corrected_score():
    assert scorecard(BASE.adjust(debt=150_000)) < scorecard(BASE)


def test_more_late_payments_lowers_corrected_score():
    assert scorecard(BASE.adjust(late_payments=3)) < scorecard(BASE)


def test_original_calculator_had_debt_backwards():
    assert scorecard(BASE.adjust(debt=150_000), corrected=False) > scorecard(BASE, corrected=False)


def test_persona_metrics_match_written_assessment():
    results = {p.name: assess(p) for p in load_personas()}
    assert results["Persona 1"]["dti"] == pytest.approx(0.536, abs=0.001)
    assert results["Persona 3"]["dti"] == pytest.approx(0.90)
    assert results["Persona 4"]["dti"] == pytest.approx(1.333, abs=0.001)
    assert results["Persona 2"]["net_liquid_assets"] == 20_000
    assert results["Persona 4"]["net_liquid_assets"] == -120_000


@pytest.mark.parametrize("score, category", [
    (33, "High Risk"), (33.1, "Medium Risk"), (66, "Medium Risk"), (66.1, "Low Risk"),
])
def test_scorecard_bands(score, category):
    assert risk_category(score) == category


@pytest.mark.parametrize("probability, level", [
    (0.0, "Low"), (0.399, "Low"), (0.40, "Medium"), (0.649, "Medium"), (0.65, "High"), (1.0, "High"),
])
def test_probability_thresholds(probability, level):
    assert risk_level(probability) == level


def test_probability_out_of_range():
    with pytest.raises(ValueError):
        risk_level(1.2)


def test_every_risk_has_a_strategy_at_every_level():
    matrix = load_mitigation_matrix()
    for risk in matrix["risk"].unique():
        for p in (0.1, 0.5, 0.9):
            assert recommend(matrix, risk, p)["strategy"]
