# Formal Assumptions and Scope

**Scope:** IEEE 802.11be Multi-Link Operation Reordering Dynamics  

---

## 1. Protocol Assumptions

- **(A1) Single-TID Multi-Flow Multiplexing:** Multiple application flows $\mathcal{F} = \{1, \dots, M\}$ share a common Access Category (e.g., Best Effort AC_BE or Video AC_VI) and are consequently mapped to the same 802.11 Traffic Identifier ($\text{TID}$).
  - *Practical Justification:* IEEE 802.11 supports only 8 TIDs (0–7). Operating systems routinely map diverse concurrent traffic (e.g., streaming video, interactive telemetry, background cloud sync) to the default Best Effort TID (TID 0).
- **(A2) Common Per-TID Sequence Number Space:** The transmitter allocates sequence numbers $s \in [0, 4095]$ from a unified sequence number pool for all transmissions under the given TID across all affiliated links.
  - *Standard Conformance:* Strictly mandated by IEEE Std 802.11be-2024 Section 9.2.4.4.
- **(A3) Unmodified IEEE 802.11be Receiver:** The receiver MLD operates standard Block Ack agreement handling. It does not perform Deep Packet Inspection (DPI) to identify application flows or maintain separate reordering buffers per flow (distinguishing this work from MediaTek patent US12470496B2).
  - *Practical Justification:* Guarantees compatibility with existing commercial client devices, IoT stations, and standard operating system network stacks.
- **(A4) Monotonic Intra-Flow Sequence Ordering:** For every individual flow $f \in \mathcal{F}$, if packet $a$ was generated before packet $b$ ($t_a^{\text{arr}} < t_b^{\text{arr}}$), the assigned sequence numbers satisfy $s_a < s_b$.
  - *Justification:* Enforces end-to-end transport-layer in-order delivery requirements (e.g., TCP segment ordering or RTP packet ordering).
- **(A5) Modulo Arithmetic Wrap-around Unwrapping:** For theoretical derivations, the sequence number space is analyzed over the integers $\mathbb{Z}$, with the assumption that the sliding window size $W \ll 4096 / 2$ prevents sequence ambiguity (as required by 802.11 standard rules: $W \le 1024 < 2048$).

---

## 2. Channel and Service Assumptions

- **(A6) Simultaneous Transmit and Receive (STR):** Links $\mathcal{K}$ are separated in frequency (e.g., 2.4 GHz vs. 5 GHz vs. 6 GHz) such that transmission on link $k$ does not collide with or blind reception on link $k' \ne k$.
- **(A7) Independence Across Links:** Channel fading and contention processes on link $k$ are statistically independent of channel fading and contention on link $k' \ne k$.
- **(A8) Non-Degenerate, Finite Moments:** For each link $k \in \mathcal{K}$, the link service time $D_k$ has strictly positive mean $\mu_k = \mathbb{E}[D_k] > 0$ and bounded variance $\sigma_k^2 = \text{Var}(D_k) < \infty$.
- **(A9) Sub-Gaussian Delay Fluctuations:** Link completion times $D_k$ exhibit sub-Gaussian tails with parameter $\nu_k^2$:
  $$\mathbb{E}\left[e^{\theta (D_k - \mu_k)}\right] \le \exp\left(\frac{\theta^2 \nu_k^2}{2}\right), \quad \forall \theta \in \mathbb{R}$$
  - *Justification:* Standard discrete-time backoff processes over bounded contention windows ($CW \le 1023$) and finite retry limits ($L_{\max} \le 7$) have bounded support, and all bounded random variables are sub-Gaussian by Hoeffding's Lemma.
- **(A10) Causal Filtration:** The scheduler $\pi$ at epoch $t$ has access to the filtration $\mathcal{H}_t = \sigma(\{A_j, \ell_j, s_j : A_j \le t\} \cup \{t_i^{\text{arr}} : t_i^{\text{arr}} \le t\})$, but has no non-causal knowledge of future contention durations $B_{k, r}$ or channel realization errors.
