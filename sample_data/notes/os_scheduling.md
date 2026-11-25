# Operating Systems: CPU Scheduling

CPU scheduling decides which ready process runs on a CPU core next when multiple processes compete for execution. Good scheduling balances responsiveness, fairness, and hardware utilization.

## Key Metrics & Definitions

- **Burst Time ($B$):** Total CPU time a process needs to finish its current CPU cycle.
- **Arrival Time ($A$):** Time at which a process enters the ready queue.
- **Completion Time ($C$):** Time at which a process finishes execution.
- **Turnaround Time ($TAT = C - A$):** Total time spent in the system from arrival to completion.
- **Waiting Time ($WT = TAT - B$):** Total time a process spends waiting in the ready queue.
- **Response Time:** Time from arrival until the process gets the CPU for the first time.

## Common Scheduling Algorithms

1. **First-Come, First-Served (FCFS):** Non-preemptive; runs processes in arrival order. Simple, but suffers from the **convoy effect** when a long CPU-bound job delays short jobs behind it.
2. **Shortest Job First (SJF) / SRTF:** Picks the process with the smallest CPU burst (SRTF is its preemptive version). Provably minimizes average waiting time, though exact burst times must be estimated and long jobs can starve.
3. **Round Robin (RR):** Preemptive; gives each process a fixed **time quantum** $q$ in circular order. Great for interactive systems and response time; if $q$ is too small, context-switch overhead dominates.
4. **Multilevel Feedback Queue (MLFQ):** Uses multiple priority queues with aging so interactive I/O-bound processes stay responsive while CPU-bound processes do not starve.

## Worked Example (Round Robin, $q = 4$)

Suppose three processes arrive at $t = 0$ in order $P_1, P_2, P_3$ with burst times $B_1 = 6$, $B_2 = 4$, $B_3 = 2$:

- **Timeline (Gantt chart):**
  - $0 \to 4$: $P_1$ runs for $4$ (remaining: $2$)
  - $4 \to 8$: $P_2$ runs for $4$ and finishes ($C_2 = 8$)
  - $8 \to 10$: $P_3$ runs for $2$ and finishes ($C_3 = 10$)
  - $10 \to 12$: $P_1$ runs remaining $2$ and finishes ($C_1 = 12$)

- **Metrics:**
  - $P_1$: $TAT = 12 - 0 = 12$, $WT = 12 - 6 = 6$
  - $P_2$: $TAT = 8 - 0 = 8$, $WT = 8 - 4 = 4$
  - $P_3$: $TAT = 10 - 0 = 10$, $WT = 10 - 2 = 8$
  - **Average Waiting Time:** $(6 + 4 + 8) / 3 = 6.0$ time units.
