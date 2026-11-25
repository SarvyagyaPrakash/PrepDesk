# Operating Systems: Virtual Memory

Virtual memory separates the logical address space seen by a process from the physical memory (RAM) managed by the hardware.

## Paging and Page Tables
- Physical memory is divided into fixed-size **frames**, and logical memory is divided into **pages** of the same size (commonly 4 KB).
- A **page table** maps each virtual page number (VPN) to a physical frame number (PFN) plus permission and valid bits.
- When a program accesses a virtual address whose valid bit is 0, the CPU raises a **page fault**, trapping into the OS kernel to load the page from disk.

## Translation Lookaside Buffer (TLB)
- Because reading the page table in RAM on every memory access doubles memory latency, CPUs cache recent VPN-to-PFN translations in the **TLB**.
- A **TLB hit** resolves the physical address in a single cycle; a **TLB miss** walks the page table (and may use a multi-level page table to save memory).

## Page Replacement Policies
- **FIFO:** Evicts the oldest loaded page; simple but suffers from Belady's anomaly.
- **LRU (Least Recently Used):** Evicts the page unused for the longest time; approximates Belady's optimal algorithm well.
