"""Load the simulation inputs from data/."""

from pathlib import Path

import pandas as pd

from risk.credit import Borrower

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
FIGURES_DIR = ROOT / "figures"


def load_personas():
    frame = pd.read_csv(DATA_DIR / "personas.csv")
    return [
        Borrower(
            name=row.persona,
            annual_income=row.annual_income,
            credit_score=row.credit_score,
            debt=row.debt,
            savings=row.savings,
            late_payments=row.late_payments,
        )
        for row in frame.itertuples()
    ]


def load_mitigation_matrix():
    return pd.read_csv(DATA_DIR / "mitigation_matrix.csv")
