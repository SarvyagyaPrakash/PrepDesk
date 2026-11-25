# Computer Networks: TCP Fundamentals

Transmission Control Protocol (TCP) is a connection-oriented, reliable, byte-stream transport protocol layered on top of IP. Unlike UDP, TCP guarantees in-order, error-checked delivery of bytes between applications.

## Core Mechanisms

- **Three-Way Handshake (Connection Setup):**
  1. Client sends `SYN` with initial sequence number $x$.
  2. Server replies `SYN-ACK` acknowledging $x + 1$ and sending its own sequence number $y$.
  3. Client sends `ACK` acknowledging $y + 1$. Data transfer can now begin.
- **Sequence & Acknowledgment Numbers:** Every byte has a sequence number; `ACK` carries the next expected byte (cumulative acknowledgment).
- **Flow Control (`rwnd`):** The receiver advertises its available buffer space (`receive window`) in every header so a fast sender does not overflow a slow receiver.
- **Congestion Control (`cwnd`):** The sender limits in-flight unacknowledged bytes to $\min(\text{cwnd}, \text{rwnd})$ to avoid overwhelming intermediate routers.

## Congestion Control Phases

1. **Slow Start:** Starts with a small `cwnd` (e.g., $1$ or $10$ MSS) and doubles `cwnd` every RTT (exponential growth) until reaching `ssthresh` or packet loss.
2. **Congestion Avoidance:** Above `ssthresh`, `cwnd` grows linearly by roughly $1\text{ MSS}$ per RTT (AIMD: Additive Increase, Multiplicative Decrease).
3. **Loss Detection:**
   - **Timeout:** Severe congestion signal; `ssthresh = cwnd / 2` and `cwnd` resets to $1\text{ MSS}$.
   - **3 Duplicate ACKs (Fast Retransmit):** Milder signal; `ssthresh = cwnd / 2` and `cwnd` drops to `ssthresh` (Fast Recovery) instead of $1\text{ MSS}$.

## Worked Example

Suppose a TCP sender starts with $\text{cwnd} = 1\text{ MSS}$ and $\text{ssthresh} = 8\text{ MSS}$ (assume large `rwnd`):
- **RTT 0:** $\text{cwnd} = 1$ (Slow Start)
- **RTT 1:** $\text{cwnd} = 2$
- **RTT 2:** $\text{cwnd} = 4$
- **RTT 3:** $\text{cwnd} = 8$ (reaches `ssthresh`, switches to Congestion Avoidance)
- **RTT 4:** $\text{cwnd} = 9$ (linear increase $+1$)
- **RTT 5:** $\text{cwnd} = 10$, and **3 duplicate ACKs** arrive!

The sender immediately retransmits the missing segment, sets $\text{ssthresh} = 10 / 2 = 5\text{ MSS}$, and enters Fast Recovery with $\text{cwnd} = 5\text{ MSS}$, then resumes linear growth ($6, 7, \dots$) in subsequent RTTs.
