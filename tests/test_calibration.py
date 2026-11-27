import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from risk import calibration  # noqa: E402
from risk.credit import Borrower  # noqa: E402
from risk.data import load_personas  # noqa: E402

RESULTS = calibration.load()
PERSONAS = {p.name: p for p in load_personas()}


def test_coefficients_point_the_right_way():
    c = RESULTS["coefficients"]
    assert c["income"] < 0      # more income -> less default
    assert c["leverage"] > 0    # more leverage -> more default
    assert c["late"] > 0        # more late payments -> more default


def test_model_beats_chance_on_held_out_borrowers():
    assert RESULTS["test_auc"] > 0.75


def test_default_rate_rises_with_late_payments():
    rates = [r["default_rate"] for r in RESULTS["default_rate_by_late_payments"]]
    assert rates == sorted(rates)


def test_calibrated_weights_sum_to_one_and_keep_untested_inputs():
    w = calibration.calibrated_weights(RESULTS)
    assert sum(w.values()) == pytest.approx(1.0)
    assert w["credit_score"] == w["savings"] == 0.25


def test_payment_to_income_uses_five_year_loan_at_eight_percent():
    borrower = Borrower("x", annual_income=120_000, credit_score=700,
                        debt=100_000, savings=0, late_payments=0)
    # 100k over 60 months at 8% is about $2,028 a month, or $24,330 a year
    assert calibration.payment_to_income(borrower) == pytest.approx(24_330 / 120_000, rel=0.002)


def test_pd_ranks_personas_like_the_written_assessment():
    pd_ = {name: calibration.probability_of_default(p, RESULTS) for name, p in PERSONAS.items()}
    assert pd_["Persona 1"] < pd_["Persona 2"] < pd_["Persona 4"] < pd_["Persona 3"]


def test_more_late_payments_raise_pd():
    p = PERSONAS["Persona 2"]
    assert (calibration.probability_of_default(p.adjust(late_payments=3), RESULTS)
            > calibration.probability_of_default(p, RESULTS))


@pytest.mark.skipif(not calibration.RAW_PATH.exists(), reason="Kaggle data not downloaded")
def test_refit_reproduces_saved_results():
    refit = calibration.fit()
    for key, value in RESULTS["coefficients"].items():
        assert refit["coefficients"][key] == pytest.approx(value, rel=1e-4)
