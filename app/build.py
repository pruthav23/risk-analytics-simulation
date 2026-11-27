"""Build app/index.html from app/template.html and the CSVs in data/.

The interactive page embeds the same persona data and mitigation matrix as
the Python analysis, so the two can never drift apart.

Usage:
    python app/build.py
"""

import json
from pathlib import Path

import pandas as pd

APP = Path(__file__).resolve().parent
DATA = APP.parent / "data"


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


def main():
    page = (APP / "template.html").read_text()
    page = page.replace("/*PERSONAS*/", json.dumps(personas(), ensure_ascii=False))
    page = page.replace("/*MATRIX*/", json.dumps(matrix(), ensure_ascii=False))
    (APP / "index.html").write_text(page)
    print("Wrote app/index.html")


if __name__ == "__main__":
    main()
