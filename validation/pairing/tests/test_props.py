"""Property tests for Prop A (arrival coupling) and Prop B (censoring bound) on 500 random scenarios.
Seeds >= 100000, never the confirmatory seeds."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import study as st  # noqa: E402

N = 500
ARMS = st.ARMS


def scenario(i):
    r = random.Random(424242 + i)
    n = r.randint(1, 8)
    spec = [(r.choice([1.0, 5.0, 20.0, 50.0]), r.uniform(50, 400)) for _ in range(n)]
    return spec, 100000 + i, r.choice(ARMS), r.choice(ARMS)


def run(spec, design, arm, seed, duration, **kw):
    st.SCALES["_P"] = spec
    return st.simulate("_P", design, arm, seed, duration=duration, **kw)


def test_prop_a_arrival_coupling_naive_and_keyed():
    for i in range(N):
        spec, seed, a1, a2 = scenario(i)
        for design in ("naive", "keyed"):
            sigs = []
            for arm in (a1, a2):
                sim, rx, w = run(spec, design, arm, seed, 100.0)
                sigs.append(st.summarize(sim, rx, 100.0, w)["arr_sig"])
            assert sigs[0] == sigs[1], (i, design, a1, a2)


def test_prop_b_censoring_is_pointwise_lower_bound_and_monotone():
    for i in range(N):
        spec, seed, arm, _ = scenario(i)
        H1, H2 = 60.0, 100.0
        s1, r1, _ = run(spec, "keyed", arm, seed, H1)
        s2, r2, _ = run(spec, "keyed", arm, seed, H2)
        sd, rd, _ = run(spec, "keyed", arm, seed, H2, arrival_horizon=H2, drain=True)
        e2e_d = {p.packet_id: p.end_to_end_delay for p in rd.delivered_packets}
        e2e_2 = {p.packet_id: p.end_to_end_delay for p in r2.delivered_packets}
        e2e_1 = {p.packet_id: p.end_to_end_delay for p in r1.delivered_packets}
        for p in s2.all_packets:                      # censored at H2 <= drained delay
            c2 = e2e_2.get(p.packet_id, max(0.0, H2 - p.arr_time))
            if p.packet_id in e2e_d:
                assert c2 <= e2e_d[p.packet_id] + 1e-9, (i, p.packet_id)
        for p in s1.all_packets:                      # monotone in horizon
            c1 = e2e_1.get(p.packet_id, max(0.0, H1 - p.arr_time))
            c2 = e2e_2.get(p.packet_id, max(0.0, H2 - p.arr_time))
            assert c1 <= c2 + 1e-9, (i, p.packet_id)
