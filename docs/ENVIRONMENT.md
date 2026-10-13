# Environment Inventory and Reproducibility Baseline

**Date:** 2026-10-12  
**Host Architecture:** x86_64  
**Operating System:** Linux (Arch Linux `7.2.4-arch1-2 #1 SMP PREEMPT_DYNAMIC` x86_64)  
**Host Machine:** Intel(R) Core(TM) i7-13620H (10 physical cores / 16 threads, up to 4.90 GHz)  
**Memory:** 15 GiB Total Physical RAM, 22 GiB Swap, ~3.4 GiB Available  
**Storage:** 475 GB filesystem on `/home`, 67 GB available (86% utilized)  

---

## 1. Toolchains and Compilers

| Tool | Version / Path | Status |
| :--- | :--- | :--- |
| **Python** | Python 3.14.7 (`/usr/bin/python3`) | Active |
| **C/C++ Compiler** | GCC 16.2.1 20260810 (`/usr/bin/g++`) | Verified |
| **CMake** | CMake 4.4.4 (`/usr/bin/cmake`) | Verified |
| **Ninja** | Ninja 1.13.2 (`/usr/bin/ninja`) | Verified |
| **LaTeX Engine** | pdfTeX 3.141592653-2.6-1.40.26 (`/usr/bin/pdflatex`) | Verified |
| **BibTeX** | BibTeX 0.99d (`/usr/bin/bibtex`) | Verified |
| **Latexmk** | Latexmk 4.83 (`/usr/bin/latexmk`) | Verified |

---

## 2. Python Environment

- **Dedicated Virtual Environment:** `/home/adhyan/Desktop/wifi7_mlo_hol/.venv`
- **Package Manager:** `pip` 26.2.1
- **Installed Scientific Stack:**
  - `numpy` 2.5.2+ (vectorized matrix computations, random variable simulation)
  - `scipy` (statistical hypothesis testing, distributions, confidence intervals)
  - `matplotlib` (vector graphics generation for paper plots)
  - `pytest` (automated unit and property-based verification)
  - `pyyaml` (experiment configuration management)

---

## 3. Simulator Inventory & Feasibility Assessment

1. **System ns-3 Scan:**
   - Scan of `/home/adhyan` revealed no pre-installed ns-3 builds or system binary packages.
   - While ns-3 has added initial 802.11be MLO frame exchanges in recent releases (ns-3.38 to ns-3.41+), upstream ns-3’s 802.11be implementation models standard Upper MAC / Lower MAC architectures where all MPDUs for a given TID share a single FIFO `WifiMacQueueContainer` and sequence numbers are assigned deterministically at queue enqueue time, with Lower MAC link queues managing EDCA access independently.
   - Upstream ns-3 does **not** natively expose cross-flow sequence-aware scheduling hooks or non-FIFO predictive sequence number assignment out of the box.
2. **Evaluation Strategy:**
   - **Primary Rigorous Discrete-Event & Stochastic Simulation Model (`src/mlo_sim`):** A custom, mathematically exact, discrete-event simulation engine written in Python that explicitly implements the IEEE 802.11be Upper MAC (U-MAC) queueing architecture, TID-to-link mapping, dynamic channel contention (EDCA backoff, CWmin/CWmax, AIFS), multi-rate PHY transmissions, bursty Rayleigh/Nakagami-fading frame error rates (FER), Block Ack (BA) sliding window tracking (WinStart, WinSize, bitmap updates), retransmissions, and fine-grained per-packet delay decomposition into self-blocking ($\mathcal{S}$) and cross-flow blocking ($\mathcal{X}$).
   - **Validation & Sanity Checks:** The custom simulation framework is validated against hand-derived deterministic cases, single-link vs. multi-link invariant checks, and statistical convergence tests against theoretical stochastic expectations.

---

## 4. Preservation of Unrelated Research

- Existing directory `/home/adhyan/Desktop/CN` contains an independent project (*Drift-Aware GAN-Augmented IDS for SDN*). It remains untouched.
- Existing directory `/home/adhyan/Desktop/CN_research` contains preliminary exploratory notes on telemetry security. It remains untouched.
- All research artifacts, code, theory, and manuscripts for this project are strictly isolated within `/home/adhyan/Desktop/wifi7_mlo_hol/`.
