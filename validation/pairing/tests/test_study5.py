"""Study 5 theory checks (airport.py). Smoke seeds 1-3 only for simulator traces; confirmatory seeds 26000+ are never used here.
Property tests: closed-form Shapley vs brute force, efficiency, null/symmetry, ranking, core membership, leave-one-out masking,
sub-additivity, L1-Lipschitz stability and releaser discontinuity, M/G/1 supermodularity, simulator oracles, Poisson closed form."""
import itertools
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import airport as ap  # noqa: E402
import study as st  # noqa: E402
from study2 import BlameReceiver  # noqa: E402

RNG = np.random.default_rng(5)


def rand_l(m, ties=False):
    l = RNG.exponential(1.0, m) * (RNG.random(m) < 0.8)
    if ties and m > 1:
        l[RNG.integers(0, m, m // 2)] = l[0]
    return l


@pytest.mark.parametrize("m", [1, 2, 3, 4, 6, 7])
def test_closed_form_equals_bruteforce_and_efficiency(m):
    for it in range(60):
        l = rand_l(m, ties=it % 3 == 0)
        phi = ap.shapley_airport(l)
        assert np.allclose(phi, ap.shapley_bruteforce(l), atol=1e-12)
        assert phi.sum() == pytest.approx(l.max() if m else 0.0, abs=1e-12)
        assert (phi >= -1e-15).all() and (phi <= l + 1e-12).all()          # phi_j <= stand-alone cost
        for a, b in itertools.combinations(range(m), 2):                    # ranking and symmetry
            if l[a] <= l[b]:
                assert phi[a] <= phi[b] + 1e-12
            if l[a] == l[b]:
                assert phi[a] == pytest.approx(phi[b], abs=1e-12)
        assert all(phi[j] == 0 for j in range(m) if l[j] == 0)              # null player


def test_core_membership():
    for m in (3, 5):
        for _ in range(40):
            l = rand_l(m)
            phi = ap.shapley_airport(l)
            for r in range(1, m + 1):
                for S in itertools.combinations(range(m), r):
                    assert phi[list(S)].sum() <= l[list(S)].max() + 1e-12


def test_masking_and_subadditivity():
    for m in (2, 3, 5):
        for _ in range(80):
            l = rand_l(m)
            loo = ap.loo_blame(l)
            X = l.max()
            assert loo.sum() <= X + 1e-12 <= l.sum() + 2e-12               # sum LOO <= X <= sum of stand-alone costs
            top = int(np.argmax(l))
            second = np.sort(l)[-2]
            for j in range(m):
                want = (X - second) if (j == top and (l == X).sum() == 1) else 0.0
                assert loo[j] == pytest.approx(want, abs=1e-12)


def test_l1_lipschitz_stability_and_releaser_discontinuity():
    for m in (2, 3, 5, 7):
        for _ in range(300):
            l = rand_l(m, ties=True)
            lp = np.maximum(0.0, l + RNG.uniform(-0.05, 0.05, m) * (RNG.random(m) < 0.7))
            assert np.abs(ap.shapley_airport(lp) - ap.shapley_airport(l)).sum() <= 2 * np.abs(lp - l).sum() + 1e-12
    for delta in (1e-3, 1e-6, 1e-9):                                          # releaser rule jumps by 2x however small delta
        a, b = np.array([1.0, 1.0 + delta]), np.array([1.0 + delta, 1.0])
        assert np.abs(ap.releaser_blame(a) - ap.releaser_blame(b)).sum() >= 2.0
        assert np.abs(ap.shapley_airport(a) - ap.shapley_airport(b)).sum() <= 4 * delta


def test_mg1_queueing_externality_is_supermodular():
    """Pollaczek-Khinchine mean wait of a victim sharing a FIFO M/G/1 server with coalition T of Poisson flows."""
    for _ in range(50):
        n = 5
        lam = RNG.uniform(0.01, 0.15, n)
        s1 = RNG.uniform(0.5, 1.5, n)
        s2 = s1 ** 2 * RNG.uniform(1.0, 2.0, n)

        def W(T):
            T = list(T)
            rho = float((lam[T] * s1[T]).sum())
            return float((lam[T] * s2[T]).sum()) / (2 * (1 - rho)) if T else 0.0
        subsets = [S for r in range(0, 4) for S in itertools.combinations(range(n), r)]
        for A in subsets:
            for B in subsets:
                if not set(A) <= set(B):
                    continue
                for j in range(n):
                    if j in B:
                        continue
                    assert W(A + (j,)) - W(A) <= W(B + (j,)) - W(B) + 1e-12      # marginal grows with the coalition
        full = list(range(n))
        assert sum(W(full) - W([k for k in full if k != j]) for j in full) >= W(full) - 1e-12   # sum of LOO >= total


@pytest.mark.parametrize("scale,sched", [("S4", "FIFO"), ("S4", "FullSASP"), ("S8", "FIFO")])
def test_simulator_oracles_smoke(scale, sched):
    for seed in (1, 2, 3):
        flows, links, chans = st.build(scale, fer=0.01)
        sim = st.StudySimulator(flows, links, chans, st.make_sched(sched), seed=seed, design="keyed")
        sim.receiver = BlameReceiver(win_size=sim.win_size)
        rx = sim.run(duration_ms=st.DURATION_MS)
        assert rx.window_advances_forced == 0
        deliv = {p.packet_id for p in rx.delivered_packets}
        T = ap.lateness_table(list(rx.history.values()), deliv)
        rel = {p.packet_id: (p.rel_time, p.cross_blocking) for p in rx.delivered_packets}
        for k, p in enumerate(T["packets"]):
            assert rel[p.packet_id][0] == pytest.approx(T["prefix_max"][k], abs=1e-9)      # release = prefix maximum
            assert rel[p.packet_id][1] == pytest.approx(T["ell"][k].max(), abs=1e-9)        # X = max lateness
        ids = T["flows"]
        got = {}
        for k, p in enumerate(T["packets"]):                                                # releaser blame = BlameReceiver
            l = np.delete(T["ell"][k], T["flow"][k])
            oth = [f for f in ids if f != p.flow_id]
            for f, v in zip(oth, ap.releaser_blame(l)):
                if v:
                    got[(f, p.flow_id)] = got.get((f, p.flow_id), 0.0) + v
        for key in set(got) | set(rx.blame):
            assert got.get(key, 0.0) == pytest.approx(rx.blame.get(key, 0.0), abs=1e-9)
        rng = np.random.default_rng(seed)
        vic = int(rng.choice(ids))
        others = [f for f in ids if f != vic]
        Tset = [o for o in others if rng.random() < 0.5]
        out = ap.rebuild_cross_blocking(list(rx.history.values()), set(Tset) | {vic})      # real receiver on truncated trace
        col = [ids.index(o) for o in Tset]
        for k, p in enumerate(T["packets"]):
            if p.flow_id == vic and p.packet_id in out:
                assert out[p.packet_id] == pytest.approx(max([T["ell"][k][c] for c in col], default=0.0), abs=1e-9)


def test_poisson_closed_form_tiny():
    rng = np.random.default_rng(11)
    fast = ap.PathDelay([(1.0, 1.0, 0.3)])
    slow = ap.PathDelay([(0.6, 1.0, 0.3), (0.4, 3.0, 0.5)])
    victim, others, rates = fast, [slow, fast], [0.2, 0.15, 0.3]
    phi = ap.shapley_poisson(victim, others, rates)
    v = ap.poisson_game_value(victim, others, rates, [0, 1])
    assert phi.sum() == pytest.approx(v, rel=1e-6)
    assert ap.poisson_game_value(victim, others, rates, []) == 0.0
    X, PH = ap.mc_poisson(victim, others, rates, 4000, rng)
    assert abs(X.mean() - v) < 5 * X.std() / np.sqrt(len(X))


def test_fast_helpers_match_frozen_versions():
    import airport_fast as af
    L = np.vstack([rand_l(5, ties=(i % 2 == 0)) for i in range(300)])
    batch = af.shapley_airport_batch(L)
    for i in range(len(L)):
        assert np.allclose(batch[i], ap.shapley_airport(L[i]), atol=1e-12)
    victim = ap.PathDelay([(1.0, 1.0, 0.3)])
    others = [ap.PathDelay([(0.6, 1.0, 0.3), (0.4, 3.0, 0.5)]), ap.PathDelay([(1.0, 2.0, 0.0)])]
    rates = [0.2, 0.15, 0.3]
    Lmc = af.mc_poisson_vec(victim, others, rates, 60000, np.random.default_rng(3))
    phi_cf = ap.shapley_poisson(victim, others, rates)
    v_cf = ap.poisson_game_value(victim, others, rates, [0, 1])
    X = Lmc.max(1)
    assert abs(X.mean() - v_cf) < 5 * X.std() / np.sqrt(len(X))
    PH = af.shapley_airport_batch(Lmc)
    for j in range(2):
        assert abs(PH[:, j].mean() - phi_cf[j]) < 5 * PH[:, j].std() / np.sqrt(len(PH))
