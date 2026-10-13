# Formal Problem Statement

**Title:** Cross-Flow Head-of-Line Blocking Minimization in IEEE 802.11be Multi-Link Operation  

---

## 1. Context and Setup

We consider an IEEE 802.11be Multi-Link Device (MLD) transmitter communicating with an affiliated MLD receiver over a set of $K \ge 2$ orthogonal wireless links $\mathcal{K} = \{1, 2, \dots, K\}$ (e.g., in the 2.4 GHz, 5 GHz, and 6 GHz ISM/UNII bands) operating in Simultaneous Transmit and Receive (STR) mode.

A set of $M \ge 2$ distinct higher-layer network flows $\mathcal{F} = \{1, 2, \dots, M\}$ generate packets mapped to a single Traffic Identifier ($\text{TID}$). Each flow $f \in \mathcal{F}$ represents an independent application stream (for instance, an interactive audio/video flow with tight delay constraints alongside a bulk data transfer flow).

Under the IEEE 802.11be MAC standard:
1. A single **Block Acknowledgment (BA)** agreement is established between the peer MLDs for the given TID.
2. A single, unified **Sequence Number (SN)** space $s \in \mathbb{Z}_{4096}$ is shared by all frames transmitted under this TID across all $K$ links.
3. The receiver maintains a single receive reordering buffer governed by a sliding window $[W_{\text{start}}, W_{\text{start}} + W - 1]$, where $W$ is the negotiated BA buffer size (typically $W \in \{64, 256, 1024\}$).
4. The receiver delivers received MAC Service Data Units (MSDUs) to the upper layer (LLC/IP) in strictly increasing sequence number order: an MSDU with sequence number $s$ is released only after all sequence numbers $s' < s$ within the current window have been either successfully received or acknowledged as advanced by the transmitter.

---

## 2. Dynamic Frame Execution and Delay Components

Let packet $i$ arrive at the transmitter's Upper MAC (U-MAC) at arrival time $t_i^{\text{arr}}$, belonging to flow $f_i \in \mathcal{F}$.
The scheduler assigns packet $i$:
1. A link $\ell_i \in \mathcal{K}$.
2. A dispatch time $t_i^{\text{disp}} \ge t_i^{\text{arr}}$.
3. An IEEE 802.11 sequence number $s_i \in \mathbb{N}$ (modulo 4096).

Upon dispatch to link $\ell_i$, the frame undergoes Lower MAC (L-MAC) channel access (EDCA backoff), physical transmission, and potential retransmissions in case of frame corruption. The physical completion/arrival time of packet $i$ at the receiver's physical layer is:
$$A_i = t_i^{\text{disp}} + D_i(\ell_i)$$
where $D_i(\ell_i) > 0$ is the total link transfer time, a continuous random variable drawn from the channel service distribution $F_{\ell_i}$.

Because the receiver enforces in-order delivery over the shared sequence space, packet $i$ is released to the higher layer at time:
$$R_i = \max\left(A_i, \max_{k: s_k < s_i} A_k\right)$$
assuming all preceding frames are eventually received.

The **Receiver Reordering Delay** (or Head-of-Line stall duration) experienced by packet $i$ is:
$$\Delta_i = R_i - A_i = \max\left(0, \max_{k: s_k < s_i} A_k - A_i\right)$$

---

## 3. The Cross-Flow Blocking Problem

Within each individual flow $f \in \mathcal{F}$, packets must naturally be delivered in order of their generation:
$$R_i^{\text{intra}} = \max\left(A_i, \max_{j: f_j = f_i, s_j < s_i} A_j\right)$$
The delay component $\mathcal{S}_i = R_i^{\text{intra}} - A_i$ is **Self-Blocking (Intra-Flow HOL)**: the waiting time unavoidable due to reordering within flow $f_i$ itself.

However, because multiple flows share the sequence number space, packet $i$ may also be stalled by packets from *other* flows $g \neq f_i$:
$$\mathcal{X}_i = R_i - R_i^{\text{intra}} = \max\left(0, \max_{k: f_k \neq f_i, s_k < s_i} A_k - R_i^{\text{intra}}\right)$$
The delay component $\mathcal{X}_i$ is **Cross-Flow Blocking (Inter-Flow HOL)**: delay suffered by flow $f_i$ purely because preceding sequence numbers were assigned to frames of other flows that were dispatched on slower or lossier links.

---

## 4. Optimization Objective

Let each flow $f \in \mathcal{F}$ be associated with a non-negative priority/delay penalty weight $w_f > 0$. The objective of the transmitter U-MAC scheduler is to determine an online, causal scheduling policy $\pi = (\text{Select}, \text{Map}, \text{Sequence})$ that minimizes the expected weighted cross-flow blocking cost:
$$\min_{\pi \in \Pi} \limsup_{N \to \infty} \frac{1}{N} \sum_{i=1}^N w_{f_i} \mathbb{E}\left[\mathcal{X}_i\right]$$
subject to:
1. **Flow FIFO Ordering (Intra-flow monotonicity):** For any two packets $a, b$ with $f_a = f_b$, if $t_a^{\text{arr}} < t_b^{\text{arr}}$, then $s_a < s_b$.
2. **Shared Sequence Space:** Sequence numbers $\{s_i\}_{i=1}^N$ form a contiguous permutation of $\{1, 2, \dots, N\}$.
3. **Causality:** Decisions at time $t$ depend only on historical information $\mathcal{H}_t$.
4. **Standard Receiver Semantics:** The receiver uses an unmodified IEEE 802.11be Block Ack reordering buffer of size $W$.
