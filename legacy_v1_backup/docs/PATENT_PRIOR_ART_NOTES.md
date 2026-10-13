# Patent Prior Art Notes and Freedom-to-Invent Analysis

**Purpose:** Adversarial review of patent disclosures surrounding Wi-Fi 7 Multi-Link Operation, Block Acknowledgment mechanisms, and traffic reordering to establish strict boundaries between prior patented techniques and our academic contribution.

---

## 1. MediaTek Patent: US12470496B2 / US20240244007A1

- **Title:** *Data Reordering Method and Apparatus Thereof*
- **Applicant:** MediaTek Inc.
- **Inventors:** Chi-Han Huang, Yen-Hsiung Tseng, Cheng-Ying Wu, Wei-Wen Lin
- **Filing Date:** January 17, 2024. **Publication Date:** July 18, 2024. **Grant Date:** 2025/2026.
- **Independent Claim 1 Analysis:**
  > *"A data reordering method performed by a receiving apparatus, comprising: receiving a first physical layer (PHY) protocol data unit (PPDU) from a transmitting apparatus, wherein the first PPDU comprises a plurality of medium access control (MAC) PDUs (MPDUs), and the MPDUs correspond to the same block acknowledgement (BA) window; determining a traffic that each of the MPDUs belongs to according to an MPDU identification, wherein traffics that the plurality of MPDUs belonging to comprise a first traffic and a second traffic which is different from the first traffic; performing a reordering operation for the MPDUs belonging to the first traffic, and a reordering operation for the MPDUs belonging to the second traffic, respectively; and transmitting a block acknowledgement (BA) frame in response to the first PPDU to the transmitting apparatus..."*

- **Technical Implications:**
  1. **Receiver-Side Modification:** The MediaTek patent specifically protects a **receiving apparatus** that breaks the standard single per-TID reordering buffer by inspecting the MPDU payload (IP header, DSCP, TOS, or descriptor) and demultiplexing incoming frames into multiple independent reordering pipelines.
  2. **Standard Non-Compliance:** Standard IEEE 802.11be receivers (e.g., standard consumer devices, IoT stations, or legacy Wi-Fi 7 chipsets) maintain only one reordering buffer per BA agreement / TID. They deliver MSDUs to LLC strictly in sequence number order.
  3. **Strict Research Boundary:** Proposing a receiver-side multi-queue reordering engine would directly overlap with MediaTek's claims and would fail to solve the problem for standard-compliant ecosystems.
  4. **Our Non-Infringing Architecture:** Our research proposes a **purely sender-side scheduling and sequence-assignment policy (SASP)** residing in the transmitting U-MAC. The receiving station executes standard, unmodified IEEE 802.11be Block Ack logic with a single reordering buffer. By strategically coordinating packet selection, link mapping, and sequence number assignment at the transmitter, our solution achieves low cross-flow blocking across standard receivers without any receiver-side changes.

---

## 2. Patent US20260113165A1

- **Focus:** Multi-link Block Ack buffer tracking and WinStart sliding rules across asynchronous links.
- **Core Mechanism:** Addresses how the receive buffer shifts its `WinStart` sequence pointer when MPDUs arrive across disparate links with missing gaps.
- **Distinction:** Our work accepts standard `WinStart` and `WinSize` receiver mechanics as an immutable constraint, proving how transmitter dispatching and sequencing can avoid tripping `WinStart` window stalls.

---

## 3. Patent US20250016104A1

- **Focus:** Traffic-identifier spreading and dynamic TID-to-link mapping in multi-link devices.
- **Core Mechanism:** Assigns entire TIDs (e.g., TID 6 to 6 GHz link, TID 0 to 2.4 GHz link) to partition traffic.
- **Distinction:** TID-to-link mapping separates traffic across *different* TIDs, each with its own sequence number space and BA agreement. It does **not** address the common scenario where multiple distinct application flows (e.g., interactive WebRTC audio, Zoom video, and background TCP downloads) share the *same* TID (e.g., TID 0 Best Effort). Furthermore, our work proves that if multiple flows sharing one TID are pinned to different links without sequence coordination, the faster link causes rapid BA window collapse.

---

## 4. Conclusion and Novelty Boundary

Our academic contribution is strictly delineated:
- **No receiver modifications:** Full compliance with IEEE Std 802.11be-2024.
- **Sender-side intelligence:** Operates at the U-MAC scheduler of the transmitting MLD.
- **Theoretical grounding:** Establishes the first mathematical model of cross-flow HOL delay under shared sequence spaces and proves the optimal sequence assignment threshold under stochastic link delays.
