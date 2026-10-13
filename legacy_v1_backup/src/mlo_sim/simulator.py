"""
Discrete-event simulation engine for IEEE 802.11be Multi-Link Operation.
Manages event queue, traffic generation, L-MAC channel execution,
U-MAC scheduling invocations, and receiver reordering buffer delivery.
"""

import heapq
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

from .core import Packet, Flow, Link, BlockAckReceiver
from .channel import WirelessChannel
from .schedulers import BaseScheduler


# Event types
EVENT_PACKET_ARRIVAL = 1
EVENT_LINK_TX_COMPLETE = 2


@dataclass(order=True)
class Event:
    time: float
    event_type: int
    data: Any = field(compare=False)


class MloSimulator:
    """
    Discrete-event simulation engine for Wi-Fi 7 MLO.
    """

    def __init__(
        self,
        flows: List[Flow],
        links: List[Link],
        channels: List[WirelessChannel],
        scheduler: BaseScheduler,
        win_size: int = 64,
        seed: int = 42
    ):
        self.flows: Dict[int, Flow] = {f.flow_id: f for f in flows}
        self.links: Dict[int, Link] = {l.link_id: l for l in links}
        self.channels: Dict[int, WirelessChannel] = {l.link_id: ch for l, ch in zip(links, channels)}
        self.scheduler = scheduler
        self.win_size = win_size
        self.seed = seed
        
        self.rng = random.Random(seed)
        self.receiver = BlockAckReceiver(win_size=win_size)
        
        self.queues: Dict[int, deque] = {f.flow_id: deque() for f in flows}
        self.inflight_packets: List[Packet] = []
        self.event_queue: List[Event] = []
        
        self.current_time_ms: float = 0.0
        self.total_generated_packets: int = 0
        self.packet_counter: int = 0

    def schedule_event(self, time_ms: float, event_type: int, data: Any):
        heapq.heappush(self.event_queue, Event(time=time_ms, event_type=event_type, data=data))

    def _schedule_next_packet_arrival(self, flow: Flow):
        """Schedule next Poisson packet arrival for given flow."""
        # Inter-arrival time in ms: Exp(lambda)
        rate_per_ms = flow.rate_pkts_per_sec / 1000.0
        inter_arrival_ms = self.rng.expovariate(rate_per_ms)
        arr_time = self.current_time_ms + inter_arrival_ms
        self.schedule_event(arr_time, EVENT_PACKET_ARRIVAL, flow.flow_id)

    def run(self, duration_ms: float = 1000.0) -> BlockAckReceiver:
        """
        Run the simulation until duration_ms.
        Returns the BlockAckReceiver containing all delivered packets and metrics.
        """
        target_duration_ms = duration_ms
        # Initialize initial packet arrivals for each flow
        for flow in self.flows.values():
            self._schedule_next_packet_arrival(flow)

        while self.event_queue:
            event = heapq.heappop(self.event_queue)
            self.current_time_ms = event.time
            
            if self.current_time_ms > target_duration_ms:
                break

            if event.event_type == EVENT_PACKET_ARRIVAL:
                flow_id = event.data
                flow = self.flows[flow_id]
                self.packet_counter += 1
                pkt = Packet(
                    packet_id=self.packet_counter,
                    flow_id=flow_id,
                    size_bytes=flow.packet_size_bytes,
                    arr_time=self.current_time_ms,
                    weight=flow.weight
                )
                self.queues[flow_id].append(pkt)
                flow.packets_generated += 1
                self.total_generated_packets += 1
                
                # Schedule subsequent arrival
                self._schedule_next_packet_arrival(flow)
                
                # Trigger scheduler
                self._trigger_scheduler()

            elif event.event_type == EVENT_LINK_TX_COMPLETE:
                link_id, packet = event.data
                link = self.links[link_id]
                channel = self.channels[link_id]
                
                # Check outcome of this attempt
                packet.attempts += 1
                lost = channel.sample_frame_loss(self.rng)
                
                if not lost:
                    # Successful transmission
                    link.total_transmitted_pkts += 1
                    link.busy_until = self.current_time_ms
                    link.current_packet = None
                    
                    if packet in self.inflight_packets:
                        self.inflight_packets.remove(packet)
                    
                    # Notify scheduler of completion
                    tx_elapsed_ms = self.current_time_ms - packet.disp_time
                    self.scheduler.on_packet_completed(packet, True, tx_elapsed_ms, link)
                    
                    # Deliver to BlockAckReceiver
                    self.receiver.receive_packet(packet, self.current_time_ms)
                    
                    # Link is now free, trigger scheduler
                    self._trigger_scheduler()
                else:
                    # Frame error, retry if within limit
                    link.total_retries += 1
                    if packet.attempts < link.max_retries:
                        # Schedule next attempt on same link (or allow steering)
                        attempt_delay, _ = channel.simulate_transmission_attempt(
                            packet.size_bytes, packet.attempts + 1, self.rng
                        )
                        completion_time = self.current_time_ms + attempt_delay
                        link.busy_until = completion_time
                        self.schedule_event(completion_time, EVENT_LINK_TX_COMPLETE, (link_id, packet))
                    else:
                        # Dropped after retry limit
                        link.total_dropped_pkts += 1
                        link.busy_until = self.current_time_ms
                        link.current_packet = None
                        if packet in self.inflight_packets:
                            self.inflight_packets.remove(packet)
                        self._trigger_scheduler()

        return self.receiver

    def _trigger_scheduler(self):
        """Invoke U-MAC scheduler for any available idle links."""
        available_links = [
            l for l in self.links.values()
            if l.current_packet is None and self.current_time_ms >= l.busy_until
        ]
        
        while available_links:
            decision = self.scheduler.schedule(
                current_time=self.current_time_ms,
                available_links=available_links,
                queues=self.queues,
                flows=self.flows,
                inflight_packets=self.inflight_packets,
                win_size=self.win_size,
                win_start=self.receiver.win_start
            )
            
            if decision is None:
                # Scheduler declined or window stalled
                break

            packet, selected_link, assigned_sn = decision
            packet.seq_num = assigned_sn
            packet.link_id = selected_link.link_id
            packet.disp_time = self.current_time_ms
            
            selected_link.current_packet = packet
            self.inflight_packets.append(packet)
            available_links.remove(selected_link)

            # Compute attempt duration
            channel = self.channels[selected_link.link_id]
            attempt_delay, _ = channel.simulate_transmission_attempt(
                packet.size_bytes, 1, self.rng
            )
            completion_time = self.current_time_ms + attempt_delay
            selected_link.busy_until = completion_time
            self.schedule_event(completion_time, EVENT_LINK_TX_COMPLETE, (selected_link.link_id, packet))
