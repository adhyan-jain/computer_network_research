# Novelty and limits, one page

**Core idea.** In a shared reorder buffer, the cross-flow blocking of a packet is the largest lateness among the other flows. That makes each packet an *airport game* (Littlechild-Owen 1973), a classical cost-sharing game. To our knowledge (limited literature search) nobody has applied it to resequencing or head-of-line blame.

**What it gives, all proved and exactly tested**
1. Replay-free closed-form Shapley blame, computed from one trace in O(m log m) per packet instead of 2^m counterfactual runs.
2. Leave-one-out misses exactly the second-largest lateness; the "last arrival takes all" rule charges one of several tied flows arbitrarily and has no stability bound. Minimal example: lateness (3,3,1) gives LOO (0,0,0), releaser (3,0,0), Shapley (4/3, 4/3, 1/3).
3. Shapley blame is L1-Lipschitz in the lateness with constant 2 (independent of load, flow count, window).
4. The structure survives forced release (finite window, hold timer): same law on effective arrival times, bounded error 2*m*delta between ideal and forced-release blame, and a per-packet certificate of where the reference theory applies.
5. Confirmed on: our simulator (700 runs), 900 stress traces with windows/timers/loss (249k packets, error 0), and ns-3.47's own reorder buffer (3.25M packets, release-law error 0).

**What is honestly modest or negative**
- The structure theorem is short; the contribution is the identification and its consequences.
- Simulation only; no hardware, no public external trace.
- In the simulator and ns-3, most blocked packets have a single late flow, so the blame rules rarely differ in practice; no decision benefit was shown.
- Shapley is more stable only in the worst case, not on average (preregistered test H18b failed).
- The applicability certificate is conservative (44% of packets certified in stress traces).
- Not tested: ns-3's block-ack-request forced release, duplicates, hardware.

**Process strength.** Six preregistered studies (hash and commit before data), every failure reported, independent recomputation and byte-for-byte reproducibility audited (`AUDIT_REPORT.md`).

**Fit.** A solid, honest contribution for a mid-to-upper Q1/Q2 networking venue; top-tier is unlikely without hardware or real-trace validation.
