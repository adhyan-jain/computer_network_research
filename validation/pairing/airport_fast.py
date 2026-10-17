"""airport_fast.py - vectorised helpers for Study 5 (added after the preregistration commit; they change speed only, equivalence
with the frozen airport.py is tested in tests/test_study5.py)."""
import numpy as np


def shapley_airport_batch(L):
    """Closed-form airport Shapley for many games at once. L: (N, m) lateness; returns (N, m) blame, rows sum to L.max(1)."""
    L = np.asarray(L, float)
    N, m = L.shape
    if m == 0:
        return np.zeros((N, 0))
    order = np.argsort(L, axis=1, kind="mergesort")
    S = np.take_along_axis(L, order, axis=1)
    prev = np.concatenate([np.zeros((N, 1)), S[:, :-1]], axis=1)
    inc = (S - prev) / (m - np.arange(m))[None, :]
    acc = np.cumsum(inc, axis=1)
    phi = np.empty_like(acc)
    np.put_along_axis(phi, order, acc, axis=1)
    return phi


def mc_poisson_vec(victim, others, rates, N, rng, pad=1.0):
    """Vectorised Monte Carlo of the infinite-server resequencer for a tagged victim packet sent at time 0.
    Returns the (N, m) lateness matrix of the other flows."""
    dists = [victim] + list(others)
    H = max(d.upper() for d in dists) + pad
    dk = victim.sample(rng, N)
    M = []
    for d, r in zip(dists, rates):
        n = rng.poisson(r * H, size=N)
        tot = int(n.sum())
        mx = np.full(N, -np.inf)
        if tot:
            idx = np.repeat(np.arange(N), n)
            vals = -rng.uniform(0, H, tot) + d.sample(rng, tot)
            np.maximum.at(mx, idx, vals)
        M.append(mx)
    b = np.maximum(dk, M[0])
    return np.maximum(0.0, np.stack(M[1:], axis=1) - b[:, None])
