"""Build app/index.html from app/template.html, the CSVs in data/ and the
fitted default model in results/calibration.json.

The interactive page embeds the same persona data, mitigation matrix and
default model as the Python analysis, so the two can never drift apart.

Usage:
    python app/build.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

APP = Path(__file__).resolve().parent
DATA = APP.parent / "data"
sys.path.insert(0, str(APP.parent))

from risk import calibration  # noqa: E402


def personas():
    frame = pd.read_csv(DATA / "personas.csv")
    return [
        {
            "name": row.persona,
            "income": int(row.annual_income),
            "credit": int(row.credit_score),
            "debt": int(row.debt),
            "savings": int(row.savings),
            "late": int(row.late_payments),
            "profile": row.profile,
        }
        for row in frame.itertuples()
    ]


def matrix():
    return pd.read_csv(DATA / "mitigation_matrix.csv").to_dict("records")


def default_model():
    results = calibration.load()
    return {
        "intercept": results["intercept"],
        "coefficients": results["coefficients"],
        "weights": calibration.calibrated_weights(results),
        "loan_rate": calibration.LOAN_RATE,
        "loan_months": calibration.LOAN_MONTHS,
        "lgd": calibration.LGD,
    }


def main():
    page = (APP / "template.html").read_text()
    page = page.replace("/*PERSONAS*/", json.dumps(personas(), ensure_ascii=False))
    page = page.replace("/*MATRIX*/", json.dumps(matrix(), ensure_ascii=False))
    page = page.replace("/*CALIBRATION*/", json.dumps(default_model()))
    (APP / "index.html").write_text(page)
    print("Wrote app/index.html")


if __name__ == "__main__":
    main()
