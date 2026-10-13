"""
Channel, physical layer transmission, and EDCA contention models for Wi-Fi 7 MLO links.
Supports independent fading, contention backoff, frame errors, and Gilbert-Elliott burst loss.
"""

import math
import random
from dataclasses import dataclass
from typing import Tuple


@dataclass
class ChannelParameters:
    slot_time_us: float = 9.0        # 802.11be standard slot time (9 microseconds)
    sifs_time_us: float = 16.0       # SIFS duration
    ack_time_us: float = 32.0        # BlockAck frame transmission duration
    preamble_time_us: float = 40.0   # EHT PPDU preamble
    cw_min: int = 15                 # Best effort default CWmin
    cw_max: int = 1023               # Best effort default CWmax
    max_retries: int = 7             # Standard 802.11 retry limit


class WirelessChannel:
    """
    Models physical layer transmission duration, channel contention, and loss.
    """

    def __init__(
        self,
        bandwidth_mbps: float,
        base_propagation_ms: float = 0.05,
        contention_sigma_ms: float = 0.1,
        fer: float = 0.0,
        burst_prob: float = 0.0,
        burst_recovery: float = 0.5,
        params: ChannelParameters = None
    ):
        self.bandwidth_mbps = bandwidth_mbps
        self.base_propagation_ms = base_propagation_ms
        self.contention_sigma_ms = contention_sigma_ms
        self.fer = fer
        self.burst_prob = burst_prob
        self.burst_recovery = burst_recovery
        self.params = params or ChannelParameters()
        
        # Gilbert-Elliott state: 0 = Good, 1 = Bad (burst loss)
        self.ge_state = 0

    def compute_phy_duration_ms(self, frame_size_bytes: int) -> float:
        """Compute frame PHY transmission duration in milliseconds."""
        bits = frame_size_bytes * 8
        data_time_us = (bits / self.bandwidth_mbps)
        total_time_us = (
            self.params.preamble_time_us + 
            data_time_us + 
            self.params.sifs_time_us + 
            self.params.ack_time_us
        )
        return (total_time_us / 1000.0) + self.base_propagation_ms

    def sample_backoff_duration_ms(self, attempt: int, rng: random.Random) -> float:
        """Sample EDCA backoff delay in milliseconds."""
        cw = min(2**(attempt - 1) * (self.params.cw_min + 1) - 1, self.params.cw_max)
        slots = rng.randint(0, cw)
        base_backoff_ms = (slots * self.params.slot_time_us) / 1000.0
        
        # Contention noise representing background BSS traffic
        noise = max(0.0, rng.gauss(0.0, self.contention_sigma_ms))
        return base_backoff_ms + noise

    def sample_frame_loss(self, rng: random.Random) -> bool:
        """Determine if current attempt suffers frame error (incorporating burstiness)."""
        if self.burst_prob > 0.0:
            # Transition Gilbert-Elliott model
            if self.ge_state == 0:
                if rng.random() < self.burst_prob:
                    self.ge_state = 1
            else:
                if rng.random() < self.burst_recovery:
                    self.ge_state = 0
            
            # Loss probability is 1.0 in Bad state, baseline fer in Good state
            if self.ge_state == 1:
                return True

        return rng.random() < self.fer

    def simulate_transmission_attempt(
        self, frame_size_bytes: int, attempt: int, rng: random.Random
    ) -> Tuple[float, bool]:
        """
        Simulate a single transmission attempt on this link.
        Returns (attempt_duration_ms, is_success).
        """
        backoff_ms = self.sample_backoff_duration_ms(attempt, rng)
        phy_ms = self.compute_phy_duration_ms(frame_size_bytes)
        total_duration_ms = backoff_ms + phy_ms
        lost = self.sample_frame_loss(rng)
        return total_duration_ms, not lost
