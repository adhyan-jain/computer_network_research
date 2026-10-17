"""study6.py - window-aware effective arrivals (T8/T9) and ns-3 per-packet trace helpers (see PREREGISTRATION_STUDY6.md).

  effective_arrivals(A, W)         F_j = min A_s over s >= j+W ; At_j = min(A_j, F_j)
  gen_g4(seed, W)                  synthetic traces with permanent loss, heavy-tailed delays, run through the real BlockAckReceiver
  slot_packets(...)                Packet objects for every slot with arr_rx_time = effective arrival (None if never resolved)
  unwrap_ext(rows)                 12-bit sequence numbers -> extended SN, exactly as the ns-3 binary (insertion order, running maximum)
  binding_blockers(rows)           ns-3 rule: last-inserted lower-SN MPDU after the packet's own insertion (ties: larger SN)
"""
import bisect
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.mlo_sim.core import BlockAckReceiver, Packet  # noqa: E402


def effective_arrivals(A, W):
    A = np.asarray(A, float)
    n = len(A)
    F = np.full(n, np.inf)
    if W < n:
        suffix_min = np.minimum.accumulate(A[::-1])[::-1]          # suffix_min[i] = min A[i:]
        F[: n - W] = suffix_min[W:]
    return F, np.minimum(A, F)


def gen_g4(seed, W, n=300, nf=4, ploss=0.05):
    """Returns (rx, A, F, At, flows, send_times). Lost packets have A = inf and are never fed to the receiver."""
    rng = np.random.default_rng(seed)
    t = np.cumsum(rng.exponential(1.0, n))
    fl = rng.integers(1, nf + 1, n)
    delay = (1.0 - rng.random(n)) ** (-1 / 1.5) + rng.uniform(0, 2, n)
    lost = rng.random(n) < ploss
    A = np.where(lost, np.inf, t + delay)
    rx = BlockAckReceiver(win_size=W)
    pk = []
    for sn in range(n):
        p = Packet(packet_id=sn + 1, flow_id=int(fl[sn]), size_bytes=1500, arr_time=float(t[sn]))
        p.seq_num = sn
        pk.append(p)
    for sn in sorted(range(n), key=lambda s: (A[s], s)):
        if np.isfinite(A[sn]):
            rx.receive_packet(pk[sn], float(A[sn]))
    F, At = effective_arrivals(A, W)
    return rx, A, F, At, fl, t


def slot_packets(fl, t, At):
    """One Packet per slot; arr_rx_time is the effective arrival (None if the slot is never resolved)."""
    out = []
    for sn in range(len(fl)):
        p = Packet(packet_id=sn + 1, flow_id=int(fl[sn]), size_bytes=1500, arr_time=float(t[sn]))
        p.seq_num = sn
        p.arr_rx_time = float(At[sn]) if np.isfinite(At[sn]) else None
        out.append(p)
    return out


def sdiff(a, b):
    d = (a - b) % 4096
    return d - 4096 if d >= 2048 else d


def unwrap_ext(rows):
    """rows: dicts with 'ins' (float) and 'sn' (int, 12 bit). Adds 'ext' in place, processing in insertion order."""
    ref = 0
    for r in sorted(rows, key=lambda r: (r["ins"], r["flow"], r["app_seq"])):
        r["ext"] = ref + sdiff(r["sn"], ref % 4096)
        ref = max(ref, r["ext"])
    return rows


def binding_blockers(rows):
    """For each row with wait > 1e-9 returns the flow of the binding blocker (or None), keyed by row index.
    Candidates: lower-SN rows inserted strictly after the packet's own insertion and no later than its release."""
    order = sorted(range(len(rows)), key=lambda i: (rows[i]["ins"], rows[i]["ext"]))
    ins = [rows[i]["ins"] for i in order]
    res = {}
    for i, r in enumerate(rows):
        if r["rel"] < 0 or r["rel"] - r["ins"] <= 1e-9:
            continue
        lo = bisect.bisect_right(ins, r["ins"])
        hi = bisect.bisect_right(ins, r["rel"])
        blocker = None
        for q in range(hi - 1, lo - 1, -1):
            o = rows[order[q]]
            if o["ext"] < r["ext"]:
                blocker = o["flow"]
                break
        res[i] = blocker
    return res


# ---------------------------------------------------------------------------------------------------------------------
# timeout extension (reference timer receiver implemented here; the project's BlockAckReceiver has no timer)
# ---------------------------------------------------------------------------------------------------------------------
class TimeoutReceiver(BlockAckReceiver):
    """BlockAckReceiver plus a hold timer: a buffered packet that has been held for tau is released at A_s + tau, skipping every
    missing slot below it (and releasing buffered lower-SN packets first). Window forced advance is inherited."""

    def __init__(self, win_size, tau):
        super().__init__(win_size=win_size)
        self.tau = tau
        self.timeout_events = 0

    def advance_to(self, t):
        if not np.isfinite(self.tau):
            return
        while self.buffer:
            s = min(self.buffer, key=lambda sn: (self.buffer[sn].arr_rx_time, sn))
            t_e = self.buffer[s].arr_rx_time + self.tau
            if t_e > t:
                break
            self.timeout_events += 1
            for old in sorted(k for k in self.buffer if k < s):
                self._finalize_release(self.buffer.pop(old), t_e)
            self.win_start = max(self.win_start, s)
            while self.win_start in self.buffer:
                self._finalize_release(self.buffer.pop(self.win_start), t_e)
                self.win_start += 1


def effective_arrivals_timeout(A, W, tau):
    """Resolution time of every slot for a receiver with window W and hold timer tau (tau = inf: window only)."""
    A = np.asarray(A, float)
    F, _ = effective_arrivals(A, W)
    n = len(A)
    T = np.full(n, np.inf)
    if np.isfinite(tau):
        suffix_min = np.minimum.accumulate(A[::-1])[::-1]
        T[: n - 1] = suffix_min[1:] + tau
    return F, T, np.minimum(A, np.minimum(F, T))


def gen_trace(seed, W, tau, n=300, nf=4, ploss=0.05, heavy=True):
    """Trace through the window (+timer) receiver. ploss=0 gives a loss-free trace whose skipped slots are late arrivals."""
    rng = np.random.default_rng(seed)
    t = np.cumsum(rng.exponential(1.0, n))
    fl = rng.integers(1, nf + 1, n)
    delay = ((1.0 - rng.random(n)) ** (-1 / 1.5) if heavy else rng.exponential(1.0, n)) + rng.uniform(0, 2, n)
    lost = rng.random(n) < ploss
    A = np.where(lost, np.inf, t + delay)
    rx = TimeoutReceiver(W, tau)
    pk = []
    for sn in range(n):
        p = Packet(packet_id=sn + 1, flow_id=int(fl[sn]), size_bytes=1500, arr_time=float(t[sn]))
        p.seq_num = sn
        pk.append(p)
    for sn in sorted(range(n), key=lambda s: (A[s], s)):
        if np.isfinite(A[sn]):
            rx.advance_to(float(A[sn]))
            rx.receive_packet(pk[sn], float(A[sn]))
    rx.advance_to(float("inf"))
    F, T, At = effective_arrivals_timeout(A, W, tau)
    return rx, A, F, T, At, fl, t
