"""Check that the interactive page's model matches the Python model.

Runs the page's <script id="model"> block in Node and compares its scores,
stress results and thresholds with risk/. Skipped if Node is not installed.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from risk import calibration  # noqa: E402
from risk.credit import assess, scorecard  # noqa: E402
from risk.data import load_personas  # noqa: E402
from risk.mitigation import risk_level  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node not installed")

PROBE = """
const m = require(process.argv[2]);
const out = {scores: {}, original: {}, severe: {}, levels: {}, paths: {}, calibrated: {}, pd: {}, el: {}};
for (const p of m.PERSONAS) {
  out.calibrated[p.name] = m.scoreOf(p, "calibrated");
  out.pd[p.name] = m.pd(p);
  out.el[p.name] = m.expectedLoss(p);
  out.scores[p.name] = m.scoreOf(p, true);
  out.original[p.name] = m.scoreOf(p, false);
  out.severe[p.name] = m.scoreOf(m.shock(p, 0.30, 0.40, 1), true);
  const target = m.category(out.scores[p.name]) === "High" ? 33 : 66;
  const improve = m.category(out.scores[p.name]) !== "Low";
  out.paths[p.name] = m.LEVERS.map(lv => {
    const r = m.leverMove(p, lv, target, true, improve);
    return {k: lv.k, kind: r.kind, value: r.value ?? null, target, improve};
  });
}
for (const p of [0, 0.399, 0.40, 0.649, 0.65, 1]) out.levels[p] = m.propLevel(p);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def page_model(tmp_path_factory):
    subprocess.run([sys.executable, str(ROOT / "app" / "build.py")], check=True,
                   capture_output=True)
    html = (ROOT / "app" / "index.html").read_text()
    script = re.search(r'<script id="model">(.*?)</script>', html, re.S).group(1)
    folder = tmp_path_factory.mktemp("page")
    (folder / "model.js").write_text(script)
    (folder / "probe.js").write_text(PROBE)
    result = subprocess.run(["node", str(folder / "probe.js"), str(folder / "model.js")],
                            check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def test_scores_match_python(page_model):
    for persona in load_personas():
        assert page_model["scores"][persona.name] == pytest.approx(scorecard(persona))
        assert page_model["original"][persona.name] == pytest.approx(
            scorecard(persona, corrected=False))


def test_severe_recession_matches_python(page_model):
    for persona in load_personas():
        shocked = persona.adjust(annual_income=persona.annual_income * 0.70,
                                 savings=persona.savings * 0.60,
                                 late_payments=persona.late_payments + 1)
        assert page_model["severe"][persona.name] == pytest.approx(assess(shocked)["score"])


def test_property_thresholds_match_python(page_model):
    for probability, level in page_model["levels"].items():
        assert level == risk_level(float(probability))


FIELD = {"debt": "debt", "savings": "savings", "income": "annual_income",
         "credit": "credit_score"}


def test_path_to_next_tier_is_minimal(page_model):
    """Each suggested change crosses the tier boundary, and one step less does not."""
    steps = {"debt": 1000, "savings": 1000, "income": 1000, "credit": 1}
    for persona in load_personas():
        for move in page_model["paths"][persona.name]:
            if move["kind"] != "ok" or not move["improve"]:
                continue
            field, value = FIELD[move["k"]], move["value"]
            assert scorecard(persona.adjust(**{field: value})) > move["target"]
            current = getattr(persona, field)
            one_less = value + steps[move["k"]] if value < current else value - steps[move["k"]]
            assert scorecard(persona.adjust(**{field: one_less})) <= move["target"]


def test_default_model_matches_python(page_model):
    results = calibration.load()
    for persona in load_personas():
        assert page_model["pd"][persona.name] == pytest.approx(
            calibration.probability_of_default(persona, results))
        assert page_model["el"][persona.name] == pytest.approx(
            calibration.expected_loss(persona, results))
        assert page_model["calibrated"][persona.name] == pytest.approx(
            calibration.calibrated_score(persona, results))
