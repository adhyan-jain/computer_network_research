# System Model

**Module:** IEEE 802.11be MLO Upper/Lower MAC and Wireless Channel Formalization  

---

## 1. Network Topology and Flow Characterization

- **Transmitter (Tx MLD):** Access Point (AP) or Station (STA) equipped with $K$ radio interfaces, denoted $\mathcal{K} = \{1, 2, \dots, K\}$.
- **Receiver (Rx MLD):** Affiliated peer station equipped with matching $K$ radio interfaces.
- **Simultaneous Transmit and Receive (STR):** The radios operate on non-overlapping frequency bands with sufficient isolation (e.g., 2.4 GHz, 5 GHz, 6 GHz), enabling independent, concurrent transmissions without in-device cross-talk blinding.
- **Traffic Identifier (TID):** All considered traffic belongs to a single $\text{TID} \in \{0, \dots, 7\}$.
- **Flows:** A set of $M$ independent application flows $\mathcal{F} = \{1, \dots, M\}$ generate packets destined to the Rx MLD under this TID. Packets from flow $f$ arrive according to a general renewal or Poisson arrival process with rate $\lambda_f > 0$. The aggregate arrival rate is $\Lambda = \sum_{f=1}^M \lambda_f$.

---

## 2. Channel and Service Time Stochastic Process

Each link $k \in \mathcal{K}$ operates an independent IEEE 802.11 EDCA channel access engine with parameters $(\text{AIFS}_k, \text{CW}_{\min, k}, \text{CW}_{\max, k})$ and PHY Modulation and Coding Scheme $\text{MCS}_k$.

When a frame is dispatched to link $k$:
1. **Per-Attempt Transmission Duration:**
   $$T_{\text{frame}, k} = T_{\text{preamble}} + \left\lceil \frac{L_{\text{MPDU}} + L_{\text{header}}}{\text{PHYRate}_k} \right\rceil + T_{\text{SIFS}} + T_{\text{BA}}$$
2. **Channel Contention Delay:**
   The backoff duration for attempt $r \in \{1, \dots, L_{\max}\}$ is a random variable:
   $$B_{k, r} = U\left[0, \text{CW}_k(r)\right] \cdot \sigma_{\text{slot}}$$
   where $\text{CW}_k(r) = \min(2^{r-1} (\text{CW}_{\min, k} + 1) - 1, \text{CW}_{\max, k})$, and $\sigma_{\text{slot}}$ is the slot time (e.g., $9\,\mu\text{s}$). Under background contention from co-channel BSSs, backoff slots are frozen during busy channel intervals.
3. **Channel Frame Error Rate (FER):**
   Each transmission attempt on link $k$ encounters a frame error with probability $p_k \in [0, 1)$, dictated by the signal-to-interference-plus-noise ratio ($\text{SINR}_k$) and channel fading.
4. **Total Link Service Time:**
   Let $N_k \in \{1, 2, \dots, L_{\max}\}$ denote the number of attempts until successful reception (or discard at the retry limit $L_{\max}$). Conditioned on eventual success ($N_k \le L_{\max}$):
   $$D_k = \sum_{r=1}^{N_k} \left( B_{k, r} + T_{\text{frame}, k} \right)$$
   $D_k$ is a positive random variable with:
   - Mean: $\mu_k = \mathbb{E}[D_k]$
   - Variance: $\sigma_k^2 = \text{Var}(D_k)$
   - Probability density function: $f_k(t)$, cumulative distribution function: $F_k(t)$.
   - Sub-Gaussian parameter: $\nu_k^2$ such that $\mathbb{E}[e^{\theta (D_k - \mu_k)}] \le e^{\theta^2 \nu_k^2 / 2}$ for all $\theta \in \mathbb{R}$.

---

## 3. Upper MAC (U-MAC) Scheduling State and Action Space

The transmitter maintains:
1. **Per-flow queues:** $Q_1(t), \dots, Q_M(t)$ storing unassigned, incoming packets.
2. **Link state trackers:** For each link $k \in \mathcal{K}$, the sender maintains online estimates of the channel completion distribution $(\hat{\mu}_k, \hat{\sigma}_k^2)$ updated via exponential smoothing over completed transmissions.
3. **Block Ack state tracker:**
   - $S_{\text{next}}$: Next available sequence number to be issued in the global TID sequence space.
   - $\mathcal{O}$: Set of outstanding (in-flight) frames dispatched across all links, where each frame $j \in \mathcal{O}$ is parameterized by its assigned sequence number $s_j$, flow $f_j$, link $\ell_j$, dispatch time $t_j^{\text{disp}}$, and estimated remaining service time $\hat{D}_{\ell_j}$.
   - $s_{\text{min, in-flight}} = \min_{j \in \mathcal{O}} s_j$: The earliest unacknowledged sequence number.

### Action Space at Scheduling Epoch $t$:
When link $k$ is idle (or queue space is available):
1. **Flow Selection:** Choose flow $f \in \mathcal{F}$ with non-empty queue $Q_f(t) > 0$.
2. **Packet Selection:** Take the head-of-line packet $i$ of flow $f$ (enforcing intra-flow FIFO).
3. **Link Assignment:** Assign packet $i$ to link $\ell_i = k$.
4. **Sequence Number Assignment:** Assign sequence number $s_i \in \mathbb{N}$ respecting intra-flow monotonicity and BA window bounds:
   $$s_i - s_{\text{min, in-flight}} < W$$

---

## 4. Receiver Block Ack and Delivery Semantics

The receiver MLD manages a standard IEEE 802.11be Block Ack Agreement:
- **Receive Buffer Window:** $[W_{\text{start}}, W_{\text{start}} + W - 1]$.
- **Window Size:** $W \in \{64, 256, 1024\}$.
- **Delivery Condition:** Upon arrival of MPDU $i$ with sequence number $s_i$ at physical completion time $A_i$:
  - If $s_i = W_{\text{start}}$: Packet $i$ is immediately released to LLC/IP, and $W_{\text{start}}$ is advanced to the smallest sequence number not yet received.
  - If $s_i > W_{\text{start}}$: Packet $i$ is buffered in the receive reordering buffer. It cannot be released until all missing sequence numbers $s' \in [W_{\text{start}}, s_i - 1]$ arrive or are timed out.
  - If $s_i \ge W_{\text{start}} + W$: The frame falls outside the current window. Under 802.11 semantics, receiving a frame beyond the window forces $W_{\text{start}}$ to advance to $s_i - W + 1$, dropping or force-delivering skipped frames.
