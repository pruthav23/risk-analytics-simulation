"""Re-estimate the scorecard's weights from real default data.

The simulation's weights were set by hand. Here they are tested against the
Kaggle "Give Me Some Credit" dataset: about 118,000 U.S. borrowers (after
cleaning), each labelled with whether they went 90+ days delinquent within
two years.

The dataset covers three of the scorecard's five inputs:

    scorecard input   dataset field
    income            MonthlyIncome x 12
    debt              DebtRatio (monthly debt payments / monthly income)
    late payments     30-59, 60-89 and 90+ days-late counts, summed

It has no credit score and no savings, so those two weights (50% of the
scorecard) are kept from the simulation and only the other 50% is re-split.

Each input is scaled to 0-100 exactly as the scorecard scales it, so the
fitted logistic-regression coefficients are directly comparable: a larger
coefficient means that input moves the odds of default more across its range.
"""

import json
from pathlib import Path

import numpy as np

from risk.credit import WEIGHTS

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "external" / "cs-training.csv"
RESULTS_PATH = ROOT / "results" / "calibration.json"

FEATURES = ["income", "leverage", "late"]
LATE_COLUMNS = ["NumberOfTime30-59DaysPastDueNotWorse",
                "NumberOfTime60-89DaysPastDueNotWorse",
                "NumberOfTimes90DaysLate"]

# Personas give total debt, not monthly payments. To compare them with the
# dataset's payment-based ratio, debt is assumed to be repaid over 5 years at 8%.
LOAN_RATE = 0.08
LOAN_MONTHS = 60
LGD = 0.45   # loss given default for unsecured lending (Basel foundation-IRB value)


def scale(income, leverage, late):
    """Scale inputs to 0-100 the way the scorecard does (leverage capped at 100% of income)."""
    return np.column_stack([
        np.minimum(np.asarray(income, float) / 300_000, 1) * 100,
        np.minimum(np.asarray(leverage, float), 1) * 100,
        np.minimum(np.asarray(late, float) / 5, 1) * 100,
    ])


def load_dataset(path=RAW_PATH):
    """Clean the Kaggle file: drop rows with no income and the 96/98 'late' codes."""
    import pandas as pd

    frame = pd.read_csv(path, index_col=0)
    keep = (frame["MonthlyIncome"].notna() & (frame["MonthlyIncome"] > 0)
            & ~(frame[LATE_COLUMNS] >= 90).any(axis=1))
    frame = frame[keep]
    x = scale(frame["MonthlyIncome"] * 12, frame["DebtRatio"],
              frame[LATE_COLUMNS].sum(axis=1))
    return x, frame["SeriousDlqin2yrs"].to_numpy(), frame


def fit(path=RAW_PATH, seed=42):
    """Fit the model on 70% of borrowers, score the other 30%, and summarise."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import train_test_split

    x, y, frame = load_dataset(path)
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.3, random_state=seed, stratify=y)
    model = LogisticRegression(C=1e6, max_iter=2000).fit(x_train, y_train)
    predicted = model.predict_proba(x_test)[:, 1]
    auc = roc_auc_score(y_test, predicted)

    deciles = np.array_split(np.argsort(predicted), 10)
    late_counts = frame[LATE_COLUMNS].sum(axis=1).clip(upper=5)
    by_late = frame.groupby(late_counts)["SeriousDlqin2yrs"].agg(["mean", "count"])

    return {
        "source": "Kaggle 'Give Me Some Credit' (2011), cs-training.csv",
        "borrowers": int(len(y)),
        "default_rate": float(y.mean()),
        "intercept": float(model.intercept_[0]),
        "coefficients": dict(zip(FEATURES, map(float, model.coef_[0]))),
        "test_auc": float(auc),
        "test_gini": float(2 * auc - 1),
        "calibration_by_decile": [
            {"predicted": float(predicted[i].mean()), "actual": float(y_test[i].mean())}
            for i in deciles],
        "default_rate_by_late_payments": [
            {"late_payments": int(k), "default_rate": float(r["mean"]), "borrowers": int(r["count"])}
            for k, r in by_late.iterrows()],
    }


def save(results, path=RESULTS_PATH):
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(results, indent=2) + "\n")


def load(path=RESULTS_PATH):
    return json.loads(path.read_text())


def data_shares(results):
    """Each input's share of the total |coefficient|: its data-implied relative weight."""
    size = {k: abs(v) for k, v in results["coefficients"].items()}
    total = sum(size.values())
    return {k: v / total for k, v in size.items()}


def calibrated_weights(results):
    """Simulation weights for credit score and savings; data split for the rest."""
    kept = WEIGHTS["credit_score"] + WEIGHTS["savings"]
    shares = data_shares(results)
    return {
        "credit_score": WEIGHTS["credit_score"],
        "savings": WEIGHTS["savings"],
        "annual_income": (1 - kept) * shares["income"],
        "leverage": (1 - kept) * shares["leverage"],
        "late_payments": (1 - kept) * shares["late"],
    }


def payment_to_income(borrower):
    """Estimated monthly debt payments / monthly income (5-year loan at 8%)."""
    r = LOAN_RATE / 12
    monthly_payment = borrower.debt * r / (1 - (1 + r) ** -LOAN_MONTHS)
    return monthly_payment * 12 / borrower.annual_income


def probability_of_default(borrower, results):
    """Two-year probability of serious delinquency from the fitted model."""
    x = scale(borrower.annual_income, payment_to_income(borrower), borrower.late_payments)[0]
    coef = np.array([results["coefficients"][k] for k in FEATURES])
    return float(1 / (1 + np.exp(-(results["intercept"] + x @ coef))))


def expected_loss(borrower, results):
    """PD x LGD x EAD, with exposure at default = current debt."""
    return probability_of_default(borrower, results) * LGD * borrower.debt


def calibrated_score(borrower, results):
    """The scorecard re-weighted with data-derived weights (higher = safer)."""
    w = calibrated_weights(results)
    return (
        w["credit_score"] * (borrower.credit_score - 300) / 550 * 100
        + w["savings"] * min(borrower.savings / 500_000, 1) * 100
        + w["annual_income"] * min(borrower.annual_income / 300_000, 1) * 100
        + w["leverage"] * (100 - min(payment_to_income(borrower), 1) * 100)
        + w["late_payments"] * (100 - min(borrower.late_payments / 5, 1) * 100)
    )
