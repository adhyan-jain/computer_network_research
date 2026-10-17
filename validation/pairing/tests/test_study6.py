"""Study 6 checks (smoke seeds 1-6 only; confirmatory seeds 27000+ and ns-3 seeds 61+ are never used here):
window- and timer-aware release law, delivered-set characterisation, T10 bound, certificate soundness, SN unwrapping and the
ns-3 binding-blocker rule on a hand-built example."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import airport as ap  # noqa: E402
import study6 as s6  # noqa: E402

INF = float("inf")


@pytest.mark.parametrize("W", [8, 64])
@pytest.mark.parametrize("tau", [INF, 3.0, 10.0])
@pytest.mark.parametrize("ploss", [0.05, 0.0])
def test_window_timer_release_law_and_delivered_set(W, tau, ploss):
    for seed in range(1, 7):
        rx, A, F, T, At, fl, t = s6.gen_trace(seed, W, tau, ploss=ploss)
        n = len(A)
        R = np.maximum.accumulate(At)
        deliv = {p.seq_num: p for p in rx.delivered_packets}
        want = {k for k in range(n) if A[k] < min(F[k], T[k]) and np.isfinite(R[k])}
        assert want == set(deliv)
        for k, p in deliv.items():
            assert p.rel_time == pytest.approx(R[k], abs=1e-9)


def test_effective_arrivals_basic():
    F, At = s6.effective_arrivals([5.0, 1.0, 2.0, 3.0], 2)
    assert list(F[:2]) == [2.0, 3.0] and np.isinf(F[2:]).all()
    assert list(At) == [2.0, 1.0, 2.0, 3.0]                    # slot 0 is skipped when SN 2 arrives
    F, T, At = s6.effective_arrivals_timeout([5.0, 1.0, 2.0, 3.0], 99, 1.5)
    assert T[0] == pytest.approx(2.5) and At[0] == pytest.approx(2.5)


def rx_rel(rx, sn):
    return next(p.rel_time for p in rx.delivered_packets if p.seq_num == sn)


def test_certificate_soundness_and_t10_bound():
    for seed in range(1, 7):
        rx, A, F, T, At, fl, t = s6.gen_trace(seed, 8, 3.0, ploss=0.0)
        ids = {p.packet_id for p in rx.delivered_packets}
        slots = s6.slot_packets(fl, t, At)
        phys = s6.slot_packets(fl, t, A)
        T1 = ap.lateness_table(slots, ids)
        T0 = ap.lateness_table(phys, ids)
        skipped = np.maximum.accumulate((At < A).astype(int))
        delta = np.maximum.accumulate(A - At)
        for k, p in enumerate(T0["packets"]):
            ok = abs(rx_rel(rx, p.seq_num) - T0["prefix_max"][k]) <= 1e-9
            assert ok or skipped[p.seq_num]                       # no false rejection
            l1, l0 = np.delete(T1["ell"][k], T1["flow"][k]), np.delete(T0["ell"][k], T0["flow"][k])
            d = delta[p.seq_num]
            assert np.abs(l1 - l0).max() <= d + 1e-12
            assert np.abs(ap.shapley_airport(l1) - ap.shapley_airport(l0)).sum() <= 2 * len(l1) * d + 1e-12


def test_unwrap_and_binding_blocker_example():
    rows = [dict(flow=1, app_seq=i, sn=sn, ins=float(i), rel=-1.0) for i, sn in enumerate([2040, 2045, 4090, 4095, 3, 8])]
    s6.unwrap_ext(rows)
    assert [r["ext"] for r in rows] == [2040, 2045, 4090, 4095, 4099, 4104]
    # packet A (flow 1, SN 10) arrives at 1.0; packet B (flow 2, SN 9) arrives at 3.0 and releases both; C (flow 1, SN 8) at 2.0
    rec = [dict(flow=1, app_seq=0, ext=10, ins=1.0, rel=3.0), dict(flow=2, app_seq=0, ext=9, ins=3.0, rel=3.0),
           dict(flow=1, app_seq=1, ext=8, ins=2.0, rel=2.0)]
    bb = s6.binding_blockers(rec)
    assert bb == {0: 2}                                          # last-inserted lower-SN MPDU is flow 2's
