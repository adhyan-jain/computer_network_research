"""Study 4 checks: the certificate r >= q (Proposition 4) on random smoke scenarios (seeds 1-6, never 25000+), the identity
used by V10, and the Spearman helper. Confirmatory seeds are not used here."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analyze_study4 as a4  # noqa: E402
from run_study4 import py_run  # noqa: E402

D_MIN = 1.69


@pytest.mark.parametrize("scale,lm,dm", [("S4", 0.75, 3.0), ("S4", 0.15, 0.5), ("S8", 1.0, 3.0)])
def test_certificate_and_identity_on_smoke_seeds(scale, lm, dm):
    ids = list(range(1, (4 if scale == "S4" else 8) + 1))
    E = X = T = 0.0
    n = 0
    for seed in range(1, 7):
        full = py_run(scale, lm, dm, set(ids), seed)
        for i in ids:
            solo = py_run(scale, lm, dm, {i}, seed)[i]
            f = full[i]
            e = f["e2e"] - solo["e2e"]
            parts = (f["net"] - solo["net"]) + (f["S"] - solo["S"]) + f["X"]
            assert abs(e - parts) < 1e-9
            assert solo["X"] == 0.0 or solo["X"] != solo["X"]  # a single flow is never cross-blocked
            assert solo["e2e"] >= D_MIN
            E, X, T, n = E + e, X + f["X"], T + f["e2e"], n + 1
    assert E > 0
    assert X / E >= X / T - 1e-12
    assert X / E >= X / (T - D_MIN * n) - 1e-12


def test_spearman_helper():
    assert a4.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert a4.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert a4.spearman([1, 1, 1], [1, 2, 3]) != a4.spearman([1, 1, 1], [1, 2, 3])  # undefined -> nan
    x = np.array([3.0, 1.0, 2.0, 2.0])
    assert a4.spearman(x, x) == pytest.approx(1.0)
