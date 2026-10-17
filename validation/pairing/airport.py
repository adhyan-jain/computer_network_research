"""airport.py - the airport-game theory of cross-flow reordering delay (see PREREGISTRATION_STUDY5.md).

Ideal resequencer (no forced window advance): a packet k is released at R_k = max_{j <= k (SN order)} A_j. With the packet's own-flow
release time b_k = max(A_k, max own-flow predecessors), the cross-blocking X_k = R_k - b_k equals the largest 'lateness'
l_{j,k} = max(0, max A over flow-j predecessors - b_k) over the other flows j: a per-packet AIRPORT game
(coalition cost = cost of its largest member, Littlechild & Owen 1973).

Functions
  lateness_table(packets)            per delivered packet: flow, b, A, release and the lateness of every other flow
  shapley_airport(l)                 closed-form Shapley value of the airport game (sequential equal split), O(m log m)
  shapley_bruteforce(l)              subset enumeration (oracle)
  releaser_blame(l)                  all of X to the arg-max flow (what a releaser-attribution trace tool reports)
  loo_blame(l)                       leave-one-out marginal  X(N) - X(N\\j)
  rebuild_cross_blocking(...)        ground-truth oracle: delete flows from a trace, re-run the real BlockAckReceiver
  poisson_game_value / shapley_poisson  closed forms for the stochastic (Poisson, infinite-server) model
"""
import itertools
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.mlo_sim.core import BlockAckReceiver, Packet  # noqa: E402

trap = getattr(np, "trapezoid", None) or np.trapz


# ---------------------------------------------------------------------------------------------------------------------
# trace -> lateness table
# ---------------------------------------------------------------------------------------------------------------------
def lateness_table(received, delivered_ids=None, flows=None):
    """received: iterable of packets with seq_num, flow_id, arr_rx_time (ALL packets that reached the receiver PHY).
    Returns dict with arrays over delivered packets (SN order): sn, flow, A, b, ell (P x F, own column 0), flows (list), and
    prefix_max (max A over all SN <= own). delivered_ids: set of packet_id released (default: all received)."""
    rec = sorted((p for p in received if p.arr_rx_time is not None), key=lambda p: p.seq_num)
    fl = sorted({p.flow_id for p in rec}) if flows is None else list(flows)
    fidx = {f: k for k, f in enumerate(fl)}
    sn = np.array([p.seq_num for p in rec])
    fo = np.array([fidx[p.flow_id] for p in rec])
    A = np.array([p.arr_rx_time for p in rec])
    P, F = len(rec), len(fl)
    prefix_all = np.maximum.accumulate(A) if P else A
    M = np.full((P, F), -np.inf)            # M[p, j] = max A of flow-j packets with position < p
    for j in range(F):
        a = np.where(fo == j, A, -np.inf)
        cm = np.maximum.accumulate(a) if P else a
        M[1:, j] = cm[:-1]
    own = M[np.arange(P), fo]
    b = np.maximum(A, own)
    ell = np.maximum(0.0, M - b[:, None])
    ell[np.arange(P), fo] = 0.0
    keep = np.ones(P, bool) if delivered_ids is None else np.array([p.packet_id in delivered_ids for p in rec])
    return dict(sn=sn[keep], flow=fo[keep], A=A[keep], b=b[keep], ell=ell[keep], flows=fl, prefix_max=prefix_all[keep],
                packets=[p for p, k in zip(rec, keep) if k])


# ---------------------------------------------------------------------------------------------------------------------
# per-packet airport game
# ---------------------------------------------------------------------------------------------------------------------
def shapley_airport(l):
    """Closed-form Shapley blame. l: 1-D array of non-negative lateness values of the m other flows. phi sums to max(l)."""
    l = np.asarray(l, float)
    m = len(l)
    phi = np.zeros(m)
    if m == 0:
        return phi
    order = np.argsort(l, kind="mergesort")
    prev, acc = 0.0, 0.0
    for r, idx in enumerate(order):           # r = 0..m-1 ; flows with rank >= r share increment l_(r) - l_(r-1)
        acc += (l[idx] - prev) / (m - r)
        prev = l[idx]
        phi[idx] = acc
    return phi


def shapley_bruteforce(l):
    l = np.asarray(l, float)
    m = len(l)
    phi = np.zeros(m)
    for j in range(m):
        rest = [k for k in range(m) if k != j]
        for r in range(m):
            w = math.factorial(r) * math.factorial(m - r - 1) / math.factorial(m)
            for T in itertools.combinations(rest, r):
                base = max((l[k] for k in T), default=0.0)
                phi[j] += w * (max(base, l[j]) - base)
    return phi


def releaser_blame(l):
    l = np.asarray(l, float)
    out = np.zeros(len(l))
    if len(l) and l.max() > 0:
        out[int(np.argmax(l))] = l.max()
    return out


def loo_blame(l):
    l = np.asarray(l, float)
    m = len(l)
    full = l.max() if m else 0.0
    return np.array([full - (np.delete(l, j).max() if m > 1 else 0.0) for j in range(m)])


# ---------------------------------------------------------------------------------------------------------------------
# metamorphic oracle: truncate the trace, rebuild with the REAL receiver
# ---------------------------------------------------------------------------------------------------------------------
def rebuild_cross_blocking(received, keep_flows):
    """Delete all packets of flows not in keep_flows from the trace (keeping physical arrival times), renumber sequence numbers
    densely in SN order, replay arrivals through the unmodified BlockAckReceiver with an unbounded window. Returns
    {packet_id: cross_blocking} for every released packet of the kept flows."""
    kept = sorted((p for p in received if p.flow_id in keep_flows and p.arr_rx_time is not None), key=lambda p: p.seq_num)
    clones = {}
    for new_sn, p in enumerate(kept):
        c = Packet(packet_id=p.packet_id, flow_id=p.flow_id, size_bytes=p.size_bytes, arr_time=p.arr_time, weight=p.weight)
        c.seq_num = new_sn
        clones[p.packet_id] = (c, p.arr_rx_time)
    rx = BlockAckReceiver(win_size=10 ** 9)
    for pid, (c, t) in sorted(clones.items(), key=lambda kv: (kv[1][1], kv[1][0].seq_num)):
        rx.receive_packet(c, t)
    return {p.packet_id: p.cross_blocking for p in rx.delivered_packets}


# ---------------------------------------------------------------------------------------------------------------------
# stochastic model: Poisson flows, independent per-flow path delays, infinite-server paths
# ---------------------------------------------------------------------------------------------------------------------
class PathDelay:
    """Delay distribution: mixture of links, each deterministic base + optional exponential jitter.
    comps: list of (prob, base_ms, exp_mean_ms (0 = none))."""

    def __init__(self, comps):
        self.comps = comps
        assert abs(sum(c[0] for c in comps) - 1) < 1e-12

    def cdf(self, x):
        x = np.asarray(x, float)
        out = np.zeros_like(x)
        for p, base, mu in self.comps:
            y = x - base
            out += p * (np.where(y >= 0, 1.0, 0.0) if mu == 0 else np.where(y > 0, 1 - np.exp(-np.maximum(y, 0) / mu), 0.0))
        return out

    def resid(self, x):
        """mu(x) = E[(d - x)^+]."""
        x = np.asarray(x, float)
        out = np.zeros_like(x)
        for p, base, mu in self.comps:
            if mu == 0:
                out += p * np.maximum(base - x, 0.0)
            else:   # E[(base + Exp(mu) - x)^+]
                y = x - base
                out += p * np.where(y <= 0, -y + mu, mu * np.exp(-np.maximum(y, 0) / mu))
        return out

    def sample(self, rng, size):
        k = rng.choice(len(self.comps), size=size, p=[c[0] for c in self.comps])
        d = np.empty(size)
        for i, (p, base, mu) in enumerate(self.comps):
            m = k == i
            d[m] = base + (rng.exponential(mu, int(m.sum())) if mu > 0 else 0.0)
        return d

    def upper(self, q=1 - 1e-12):
        return max(base + (mu * -math.log(1 - q) if mu > 0 else 0.0) for _, base, mu in self.comps)


def _grid(dists, n=20001):
    hi = max(d.upper() for d in dists)
    return np.linspace(0.0, hi, n)


def poisson_game_value(victim, others, rates, T, n=20001):
    """v(T) = E[cross-blocking of a tagged victim packet when the coalition T (indices into `others`) of other flows is present].
    rates: [lambda_victim, lambda_others...] per ms."""
    dists = [victim] + list(others)
    x = _grid(dists, n)
    Lam = [r * d.resid(x) for r, d in zip(rates, dists)]
    f = victim.cdf(x) * np.exp(-Lam[0])
    LT = sum(Lam[1 + j] for j in T) if len(T) else np.zeros_like(x)
    return float(trap(f * (1 - np.exp(-LT)), x))


def shapley_poisson(victim, others, rates, n=20001, nt=2001):
    dists = [victim] + list(others)
    x = _grid(dists, n)
    Lam = [r * d.resid(x) for r, d in zip(rates, dists)]
    f = victim.cdf(x) * np.exp(-Lam[0])
    m = len(others)
    t = np.linspace(0, 1, nt)
    phi = []
    for j in range(m):
        prod = np.ones((nt, len(x)))
        for k in range(m):
            if k != j:
                prod *= (1 - t[:, None] * (1 - np.exp(-Lam[1 + k]))[None, :])
        inner = trap(prod, t, axis=0)
        phi.append(float(trap(f * (1 - np.exp(-Lam[1 + j])) * inner, x)))
    return np.array(phi)


def mc_poisson(victim, others, rates, N, rng, pad=1.0):
    """Monte Carlo of the infinite-server resequencer for a tagged victim packet sent at time 0. Returns X (N,) and the
    airport-Shapley blame of every other flow (N x m)."""
    dists = [victim] + list(others)
    H = max(d.upper() for d in dists) + pad
    m = len(others)
    Xs = np.zeros(N)
    PH = np.zeros((N, m))
    dk = victim.sample(rng, N)
    for s in range(N):
        M = []
        for d, r in zip(dists, rates):
            n = rng.poisson(r * H)
            if n:
                t = rng.uniform(0, H, n)           # sent at -t
                M.append((-t + d.sample(rng, n)).max())
            else:
                M.append(-np.inf)
        b = max(dk[s], M[0])
        l = np.maximum(0.0, np.array(M[1:]) - b)
        Xs[s] = l.max() if m else 0.0
        PH[s] = shapley_airport(l)
    return Xs, PH
