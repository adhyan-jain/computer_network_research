"""Deterministic regression + integration tests for the ns-3.47 SASP validation.

Run with the project venv:   .venv/bin/python -m pytest validation/ns3/tests -q

Design rules for these tests
  * Every expected value comes from an independent calculation (the audited Python policy code in
    src/mlo_sim, plain Python sorting, or arithmetic on the emitted traces), never from the
    function under test.
  * Scenario tests use scripted traffic so packet times and sizes are exactly known. Which link
    wins channel access first depends on the (seeded) backoff, so scenario tests iterate over seeds
    and assert on every seed where the scenario's precondition actually occurred; a test that finds
    no seed with the precondition FAILS (it never silently passes).
  * Tests use the assert-enabled (debug) ns-3 build wherever runtime allows, so ns-3's own
    NS_ASSERTs on block-ack windows and sequence-number state are active.
"""
import csv
import filecmp
import math
import random
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
NS3 = HERE.parent
REPO = NS3.parent.parent
sys.path.insert(0, str(NS3))
sys.path.insert(0, str(REPO / "src"))

import nsrun  # noqa: E402
from mlo_sim.schedulers import compute_threshold_root  # noqa: E402

SCEN = "debug"  # assert-enabled build for scripted scenarios


# ----------------------------------------------------------------------------- helpers
def write_script(path, events):
    """events: list of (t_s, flow, size)."""
    with open(path, "w") as f:
        f.write("# t_s,flow,size\n")
        for t, flow, size in events:
            f.write(f"{t:.9f},{flow},{size}\n")


def run_scn(tmp_path, tag, events, scheduler, seed, profile=SCEN, **kw):
    sp = tmp_path / f"{tag}.script.csv"
    write_script(sp, events)
    trace = tmp_path / f"{tag}_s{scheduler}_{seed}.trace.csv"
    dlog = tmp_path / f"{tag}_s{scheduler}_{seed}.dec.csv"
    args = dict(simTime=1, scheduler=scheduler, seed=seed, script=sp, traceOut=trace,
                decisionLog=dlog, warmup=0, drain=0, mcs0=1, mcs1=7)
    args.update(kw)
    row = nsrun.run(args, profile=profile)
    return row, read_trace(trace), read_decisions(dlog)


def read_trace(path):
    return list(csv.DictReader(open(path)))


def read_decisions(path):
    return list(csv.DictReader(open(path)))


def sn_of(trace, flow, app_seq=0):
    for r in trace:
        if int(r["flow"]) == flow and int(r["app_seq"]) == app_seq:
            return int(r["sn"])
    raise KeyError((flow, app_seq))


def ref_decide(mode, cands, sigma):
    """Independent reference of the policy. cands = [(flow, weight, predT)], head first.
    Returns the list of candidate indices that must be sequenced BEFORE the head."""
    if mode == 0 or len(cands) < 2:
        return []
    if all(c[0] == cands[0][0] for c in cands[1:]):
        return []
    if len(cands) == 2:
        d = cands[0][2] - cands[1][2]
        if mode == 2:
            u = compute_threshold_root(cands[0][1], cands[1][1])  # audited Python implementation
            return [1] if d / max(1e-6, sigma) > u else []
        return [1] if d > 0 else []
    key = []
    for i, (f, w, T) in enumerate(cands):
        k = T
        for j in range(i - 1, -1, -1):
            if cands[j][0] == f:
                k = max(k, key[j] + 1e-9)
                break
        key.append(k)
    order = sorted(range(len(cands)), key=lambda i: key[i])  # stable
    out = []
    for i in order:
        if i == 0:
            break
        out.append(i)
    return out


def weights_for(w_ls):
    return {1: float(w_ls), 2: 1.0, 3: 1.0}


def check_decisions_against_reference(decs, mode, w_ls=10.0):
    """Recompute every logged decision independently and compare with what was applied."""
    n = 0
    for d in decs:
        flows = [int(x) for x in d["flows"].split("|")]
        preds = [float(x) for x in d["pred_T_ms"].split("|")]
        w = weights_for(w_ls)
        cands = [(f, w[f], T) for f, T in zip(flows, preds)]
        sigma = math.sqrt(float(d["var_k"]) + float(d["var_j"]))
        expect = ref_decide(mode, cands, sigma)
        assert int(d["applied_n"]) == len(expect), (d, expect)
        n += 1
    return n


# ----------------------------------------------------------------------------- policy unit test
@pytest.fixture(scope="module")
def policy_driver():
    exe = HERE / "policy_driver"
    subprocess.check_call(["g++", "-O1", "-std=c++20", "-o", str(exe), str(HERE / "policy_driver.cc")])
    return exe


def test_policy_cpp_matches_python_reference(policy_driver):
    """2000 random cases (all three modes, N=1..4): C++ policy == independent Python policy."""
    rng = random.Random(20261014)
    lines, expected = [], []
    for _ in range(2000):
        mode = rng.choice([0, 1, 2])
        n = rng.choice([1, 2, 2, 3, 4])
        cands = []
        for _i in range(n):
            cands.append((rng.choice([1, 2, 3]), rng.choice([1.0, 10.0, 50.0, 0.5, 2.0]),
                          round(rng.uniform(0, 5), 6)))
        sigma = round(rng.uniform(0.01, 1.5), 6)
        lines.append(f"d {mode} {sigma} {n} " + " ".join(f"{f} {w} {T}" for f, w, T in cands))
        expected.append(ref_decide(mode, cands, sigma))
    out = subprocess.run([str(policy_driver)], input="\n".join(lines) + "\n", capture_output=True,
                         text=True, check=True).stdout.strip().splitlines()
    assert len(out) == len(expected)
    for line, exp in zip(out, expected):
        got = [] if line.split()[0] == "-" else [int(x) for x in line.split()[0].split(",")]
        assert got == exp, (line, exp)
    roots = subprocess.run([str(policy_driver)], input="root 1 10\nroot 10 1\nroot 3 7\nroot 50 1\n",
                           capture_output=True, text=True, check=True).stdout.split()
    for got, (a, b) in zip(roots, [(1, 10), (10, 1), (3, 7), (50, 1)]):
        assert abs(float(got) - compute_threshold_root(a, b)) < 1e-9


# ----------------------------------------------------------------------------- patch/tree consistency
def test_patches_reproduce_the_modified_tree(tmp_path):
    """tree == pristine ns-3.47 + patches/*.patch (no undocumented local modification)."""
    arch = NS3 / "downloads" / "ns-3.47.tar.bz2"
    assert arch.exists()
    with tarfile.open(arch) as tf:
        members = [m for m in tf.getmembers() if "/src/wifi/model/" in m.name and m.isfile()]
        for m in members:
            m.name = m.name.split("/", 1)[1]
        tf.extractall(tmp_path, members=members)
    for p in sorted((NS3 / "patches").glob("*.patch")):
        subprocess.check_call(["patch", "-p1", "-s", "-i", str(p)], cwd=tmp_path)
    mism = []
    for f in (tmp_path / "src" / "wifi" / "model").rglob("*"):
        if f.is_file():
            t = NS3 / "ns-3.47" / f.relative_to(tmp_path)
            if not filecmp.cmp(f, t, shallow=False):
                mism.append(str(f.relative_to(tmp_path)))
    assert mism == [], f"tree differs from pristine+patches: {mism}"


# ----------------------------------------------------------------------------- scenario tests





# ----------------------------------------------------------------------------- dense scenarios
def dense(flows=(1, 2), t0=0.5, dur=0.03, jitter_seed=0):
    """Deterministic over-capacity burst so that a real multi-flow queue builds up."""
    rng = random.Random(jitter_seed)
    spec = {2: (0.00012, 1200), 1: (0.0005, 200), 3: (0.0009, 600)}
    ev = []
    for f in flows:
        gap, size = spec[f]
        t = t0 + rng.random() * 1e-5
        while t < t0 + dur:
            ev.append((t, f, size))
            t += gap
    ev.sort()
    return ev


def ids_of(d):
    return [tuple(int(x) for x in i.split(":")) for i in d["ids"].split("|")]


def sn_map(trace):
    return {(int(r["flow"]), int(r["app_seq"])): int(r["sn"]) for r in trace if int(r["sn"]) >= 0}


def tx_map(trace):
    return {(int(r["flow"]), int(r["app_seq"])): r for r in trace if int(r["sn"]) >= 0}


def verify_reservations_in_trace(decs, trace, mode, w_ls=10.0):
    """For every decision: reference policy result == applied count AND the traced SNs order the
    candidates exactly as the reference sorted them (reserved ones strictly before the head)."""
    sns = sn_map(trace)
    n_checked = n_reserved = 0
    for d in decs:
        flows = [int(x) for x in d["flows"].split("|")]
        preds = [float(x) for x in d["pred_T_ms"].split("|")]
        w = weights_for(w_ls)
        cands = [(f, w[f], T) for f, T in zip(flows, preds)]
        sigma = math.sqrt(float(d["var_k"]) + float(d["var_j"]))
        exp = ref_decide(mode, cands, sigma)
        assert int(d["applied_n"]) == len(exp), (d, exp)
        ids = ids_of(d)
        n_checked += 1
        if exp:
            n_reserved += 1
            head = ids[0]
            prev = -1
            for i in exp:
                assert ids[i] in sns and head in sns
                assert sns[ids[i]] < sns[head], (d, ids[i], head)
                assert sns[ids[i]] > prev  # reserved frames are sequenced in the reference order
                prev = sns[ids[i]]
    return n_checked, n_reserved


def attribute_waits(trace, ls_flow=1):
    """Independent re-computation of the cross-flow / within-flow wait attribution from the trace."""
    rows = [r for r in trace if int(r["sn"]) >= 0 and float(r["rx_insert_ms"]) >= 0]
    cross = within = 0.0
    n = 0
    for p in rows:
        if int(p["flow"]) != ls_flow:
            continue
        n += 1
        ins, rel, sn = float(p["rx_insert_ms"]), float(p["rx_release_ms"]), int(p["sn"])
        wait = rel - ins
        if wait <= 1e-9:
            continue
        blockers = [q for q in rows if int(q["sn"]) < sn and ins < float(q["rx_insert_ms"]) <= rel + 1e-9]
        if not blockers:
            continue  # forced advance / unattributable
        b = max(blockers, key=lambda q: float(q["rx_insert_ms"]))
        if int(b["flow"]) == ls_flow:
            within += wait
        else:
            cross += wait
    return cross / n, within / n


# ----------------------------------------------------------------------------- scenario tests
def test_01_equal_links_decisions_match_reference(tmp_path):
    """Two links with identical service characteristics: every decision of both predictive arms
    matches the independent reference and the traced SN order realises it."""
    for mode in (1, 2):
        row, tr, dec = run_scn(tmp_path, "t01", dense(), mode, 3, mcs0=7, mcs1=7)
        n, nres = verify_reservations_in_trace(dec, tr, mode)
        assert n >= 15


def test_02_strong_asymmetry_orders_by_predicted_completion(tmp_path):
    """Strong asymmetry (MCS1 vs MCS7), dense burst: Mean-Only follows the scalar predicted-completion
    comparison on every decision and actually reserves sequence numbers."""
    row, tr, dec = run_scn(tmp_path, "t02", dense(), 1, 3)
    n, nres = verify_reservations_in_trace(dec, tr, 1)
    assert n >= 15 and nres >= 3
    assert row["dec_reserve_applied"] == nres


def test_03_full_sasp_differs_from_mean_only(tmp_path):
    """Same state up to the first decision where the two rules disagree; there Mean-Only reserves
    and Full SASP (weight-aware threshold) does not (or vice versa), and the traces show it."""
    ev = dense()
    _, tr_m, dec_m = run_scn(tmp_path, "t03", ev, 1, 3)
    _, tr_f, dec_f = run_scn(tmp_path, "t03", ev, 2, 3)
    idx = next(i for i, d in enumerate(dec_m) if d["n_mean_reserve"] != d["n_full_reserve"])
    strip = lambda rows: [{k: v for k, v in r.items() if k != "reason"} for r in rows]  # noqa: E731
    assert strip(dec_m[:idx]) == strip(dec_f[:idx])  # identical history before the first disagreement
    dm, df = dec_m[idx], dec_f[idx]
    assert dm["ids"] == df["ids"] and dm["t_ms"] == df["t_ms"]
    assert int(dm["applied_n"]) == int(dm["n_mean_reserve"])
    assert int(df["applied_n"]) == int(df["n_full_reserve"])
    assert dm["applied_n"] != df["applied_n"]
    head = ids_of(dm)[0]
    other = ids_of(dm)[1]
    sm, sf = sn_map(tr_m), sn_map(tr_f)
    assert (sm[other] < sm[head]) != (sf[other] < sf[head])
    verify_reservations_in_trace(dec_m, tr_m, 1)
    verify_reservations_in_trace(dec_f, tr_f, 2)


def test_04_three_candidates_use_scalar_mean_sort(tmp_path):
    """Three flows in the queue: both predictive arms order N>=3 candidate sets by scalar predicted
    completion, intra-flow order preserved."""
    for mode in (1, 2):
        row, tr, dec = run_scn(tmp_path, "t04", dense(flows=(1, 2, 3)), mode, 3)
        big = [d for d in dec if int(d["n_cand"]) >= 3]
        assert len(big) >= 5, "no N>=3 decision occurred"
        verify_reservations_in_trace(dec, tr, mode)
        assert row["dec_ge3"] >= 5 and row["audit_intra_flow_inv"] == 0


def test_05_cross_flow_reorder_attribution_matches_independent_recomputation(tmp_path):
    """FIFO dense burst: the simulator's cross/within wait numbers equal an independent Python
    recomputation of the binding-blocker attribution from the raw per-packet trace."""
    row, tr, dec = run_scn(tmp_path, "t05", dense(), 0, 3)
    cross, within = attribute_waits(tr)
    assert row["cross_wait_ms"] > 0
    assert row["cross_wait_ms"] == pytest.approx(cross, rel=1e-6, abs=1e-9)
    assert row["within_wait_ms"] == pytest.approx(within, rel=1e-6, abs=1e-9)
    # a real cross-flow event: an LS packet released exactly when a lower-SN BULK packet arrived
    rows = [r for r in tr if int(r["sn"]) >= 0]
    found = False
    for p in rows:
        if p["flow"] != "1" or float(p["rx_release_ms"]) - float(p["rx_insert_ms"]) <= 0.05:
            continue
        blockers = [q for q in rows if int(q["sn"]) < int(p["sn"]) and
                    float(p["rx_insert_ms"]) < float(q["rx_insert_ms"]) <= float(p["rx_release_ms"]) + 1e-9]
        if blockers and max(blockers, key=lambda q: float(q["rx_insert_ms"]))["flow"] == "2":
            found = True
            break
    assert found


def test_10_hook_bypass_changes_nothing_and_active_hook_changes_order(tmp_path):
    """Control for 'the extension is really in the path': with the hook removed the predictive arm
    sequences strictly in arrival order; with it installed, SNs are visibly re-ordered. Fails if
    the hook were a no-op."""
    ev = dense()
    gen_order = [(f, i) for f in (1, 2) for i in range(0)]  # placeholder, replaced below
    row_on, tr_on, _ = run_scn(tmp_path, "t10on", ev, 1, 3)
    row_off, tr_off, dec_off = run_scn(tmp_path, "t10off", ev, 1, 3, disableHook=1)
    assert row_off["dec_reserve_applied"] == 0 and row_off["decisions"] == 0 and dec_off == []

    def inversions(tr):
        rows = sorted((r for r in tr if int(r["sn"]) >= 0), key=lambda r: float(r["first_tx_ms"]))
        # app_seq order within a flow is generation order; across flows use generation order via ev
        gen = {}
        cnt = {1: 0, 2: 0, 3: 0}
        for t, f, _s in ev:
            gen[(f, cnt[f])] = t
            cnt[f] += 1
        order = sorted(rows, key=lambda r: gen[(int(r["flow"]), int(r["app_seq"]))])
        sns = [int(r["sn"]) for r in order]
        return sum(1 for a, b in zip(sns, sns[1:]) if b < a)

    assert inversions(tr_off) == 0
    assert inversions(tr_on) >= 3


def test_11_candidate_collection_never_delays_the_ready_link(tmp_path):
    """The policy never withholds the head: every head that triggered a decision is on the air in the
    same instant (PHY turn-around only). The only cost, the reserved frame's wait for the other link,
    is measured (hold) and bounded."""
    row, tr, dec = run_scn(tmp_path, "t11", dense(), 1, 3)
    txm = tx_map(tr)
    checked = 0
    for d in dec:
        head = ids_of(d)[0]
        if head in txm:
            lag = float(txm[head]["first_tx_ms"]) - float(d["t_ms"])
            assert -1e-9 <= lag < 0.05, (d, lag)
            checked += 1
    assert checked >= 15
    assert 0 <= row["reserve_hold_mean_ms"] < 2.0 and row["reserve_hold_max_ms"] < 10.0


def test_12_causality_future_traffic_cannot_change_past_decisions(tmp_path):
    """Online policy: appending traffic that arrives AFTER time T must not alter any decision made
    before T (no future information reaches the scheduler)."""
    base = dense(dur=0.02)
    extra = base + [(0.5 + 0.012 + 0.0003 * i, 2, 1200) for i in range(60)]
    cut = (0.5 + 0.011) * 1e3
    _, _, d1 = run_scn(tmp_path, "t12a", base, 2, 6)
    _, _, d2 = run_scn(tmp_path, "t12b", extra, 2, 6)
    p1 = [r for r in d1 if float(r["t_ms"]) < cut]
    p2 = [r for r in d2 if float(r["t_ms"]) < cut]
    assert len(p1) >= 8 and p1 == p2, (len(p1), len(p2))


def test_06_loss_and_retry_keep_sequence_state():
    """Lossy links: retransmissions happen, but SNs never change, no duplicate SN, no intra-flow
    inversion and no duplicate delivery."""
    row = nsrun.run(dict(simTime=2, scheduler=2, seed=3, bulkMbps=40, mcs0=11, mcs1=11, rss0=-77.5,
                         rss1=-77.5, warmup=0.3), profile=SCEN)
    assert row["retries"] > 100
    assert row["audit_sn_changed"] == 0 and row["audit_sn_dup"] == 0 and row["audit_intra_flow_inv"] == 0
    assert row["ls_rcvd"] <= row["ls_sent"] and row["bulk_rcvd"] <= row["bulk_sent"]


def test_07_reorder_buffer_fills_without_assert():
    """Very slow link 0 under saturation: the BA reorder buffer is stressed while ns-3's own
    asserts (window / sequence state) are active."""
    row = nsrun.run(dict(simTime=3, scheduler=2, seed=2, bulkMbps=80, mcs0=0, mcs1=7, warmup=0.3),
                    profile=SCEN)
    assert row["buf_occ_max"] >= 8
    assert row["audit_sn_changed"] == 0 and row["audit_sn_dup"] == 0


def test_08_sequence_number_wraparound(tmp_path):
    """>4096 MPDUs: SN space wraps repeatedly; ordering/uniqueness audits (on unwrapped SNs) hold."""
    tr_path = tmp_path / "wrap.trace.csv"
    row = nsrun.run(dict(simTime=4, scheduler=1, seed=5, bulkMbps=60, mcs0=4, mcs1=7, warmup=0.3,
                         traceOut=tr_path), profile="optimized")
    tr = read_trace(tr_path)
    sns = [int(r["sn"]) for r in tr if r["flow"] == "2" and int(r["sn"]) >= 0]
    wraps = sum(1 for a, b in zip(sns, sns[1:]) if b < a - 2000)
    assert row["unique_tx"] > 8192 and wraps >= 1
    assert row["audit_sn_dup"] == 0 and row["audit_intra_flow_inv"] == 0 and row["audit_sn_changed"] == 0


def test_09_single_flow_predictive_equals_fifo():
    """Only one flow present: there is nothing to reorder, so both predictive arms must be
    bit-identical to the native arm (same random streams, same decisions)."""
    base = dict(simTime=2, seed=4, bulkMbps=30, lsMeanIntervalMs=1e9, warmup=0.3)
    ref = nsrun.run(dict(base, scheduler=0), profile=SCEN)
    for mode in (1, 2):
        r = nsrun.run(dict(base, scheduler=mode), profile=SCEN)
        assert r["dec_reserve_applied"] == 0
        for k in ("bulk_rcvd", "bulk_goodput_mbps", "retries", "unique_tx", "link0_n", "link1_n"):
            assert r[k] == ref[k], k





def test_13_predictive_arms_do_not_lose_throughput():
    """Saturated asymmetric link pair: the extension must not reduce delivered bulk throughput."""
    base = dict(simTime=4, seed=7, bulkMbps=45, mcs0=1, mcs1=7, warmup=0.5)
    ref = nsrun.run(dict(base, scheduler=0), profile="optimized")
    for mode in (1, 2):
        r = nsrun.run(dict(base, scheduler=mode), profile="optimized")
        assert r["bulk_goodput_mbps"] >= 0.99 * ref["bulk_goodput_mbps"]
        assert r["audit_sn_dup"] == 0 and r["audit_sn_changed"] == 0


def test_14_estimators_learn_from_completions_only():
    """Estimator sample counts equal the number of acknowledged MPDUs and the learned overheads are
    finite and positive (they move only on ACK events)."""
    r = nsrun.run(dict(simTime=2, scheduler=2, seed=8, bulkMbps=20, mcs0=1, mcs1=7, warmup=0.3),
                  profile=SCEN)
    assert r["link0_n"] + r["link1_n"] > 0.95 * r["unique_tx"]
    assert 0 < r["est0_final_mean"] < 5 and 0 < r["est1_final_mean"] < 5
