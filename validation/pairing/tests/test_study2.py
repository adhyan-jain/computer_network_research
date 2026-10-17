"""Study 2 harness validity (smoke seeds 1-3 only; confirmatory seeds 20000-20099 are never used here)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import study2 as s2  # noqa: E402

SMOKE = [1, 2, 3]


def delays(scenario, seed, ids):
    D = {}
    for mask, keep in s2.masks(ids):
        _, _, out = s2.run_coalition(scenario, keep, "FIFO", seed)
        for f, v in out.items():
            D.setdefault(f, {})[keep] = v
    return D


@pytest.mark.parametrize("seed", SMOKE)
def test_v1_shapley_efficiency_and_v2_replay(seed):
    ids = [1, 2, 3, 4]
    D = delays("S4", seed, ids)
    for i in ids:
        # V2: flow i's arrivals identical in every coalition that contains it
        assert len({v["sig"] for v in D[i].values()}) == 1
        Di = {k: v["D"] for k, v in D[i].items()}
        phi, E = s2.shapley_for_victim(Di, i, ids)
        assert abs(sum(phi.values()) - E) <= 1e-9


@pytest.mark.parametrize("seed", SMOKE)
def test_v4_attribution_completeness(seed):
    sim, rx, _ = s2.run_coalition("S4", {1, 2, 3, 4}, "FIFO", seed, blame=True)
    for i in (1, 2, 3, 4):
        mine = [p for p in rx.delivered_packets if p.flow_id == i]
        if not mine:
            continue
        attributed = sum(v for (j, vic), v in rx.blame.items() if vic == i) + rx.forced_cross.get(i, 0.0)
        assert abs(attributed - sum(p.cross_blocking for p in mine)) <= 1e-9


def test_single_flow_has_no_blame_and_no_cross_blocking():
    sim, rx, _ = s2.run_coalition("S4", {1}, "FIFO", 1, blame=True)
    assert not rx.blame and all(p.cross_blocking == 0 for p in rx.delivered_packets)
