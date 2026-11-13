"""Run every report and save the printed output to results/analysis_output.txt."""

import contextlib
import io
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ["01_credit_profiles.py", "02_stress_test.py", "03_mitigation_matrix.py"]


def main():
    sys.path.insert(0, str(ROOT / "scripts"))
    buffer = io.StringIO()
    for script in SCRIPTS:
        with contextlib.redirect_stdout(buffer):
            print(f"\n##### {script}")
            runpy.run_path(str(ROOT / "scripts" / script), run_name="__main__")

    output = buffer.getvalue().lstrip()
    print(output)
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "analysis_output.txt").write_text(output)
    print("Saved results/analysis_output.txt")


if __name__ == "__main__":
    main()
