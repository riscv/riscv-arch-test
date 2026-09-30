# ACT Configuration for the Rocket Core

[Rocket](https://github.com/chipsalliance/rocket-chip) is the in-order RV64 core of rocket-chip. This
configuration runs it with the [Saturn](https://github.com/ucb-bar/saturn-vectors) vector unit and
the hypervisor extension, built through [Chipyard](https://github.com/ucb-bar/chipyard) 1.14.0
(`0acc1e1`) and simulated with Verilator 5.036.

| Config                   | ISA                                                                | Modes               |
| ------------------------ | ------------------------------------------------------------------ | ------------------- |
| `rocket-saturn-rv64gcvh` | RV64IMAFDCVH_Zfh_Zba_Zbb_Zbs_Zvfh_Zvbb_Zicsr_Zifencei_Zihpm_Za64rs | M + S + U + VS + VU |

- Privileged specification 1.12 (`Sm 1.12.0`, `S 1.12.0`), `H 1.0`; Sv39 and Sv48, Sv39x4 and
  Sv48x4; Svade.
- V 1.0 from Saturn: VLEN 128, DLEN 64, ELEN 64, with Zvfh and Zvbb.
- PMP: 8 regions, 4 KiB granule (the hypervisor extension raises it from 4 bytes), OFF/TOR/NAPOT.
- 29 HPM counters, 40 bits wide.
- `Zicntr` is not claimed: `time` is not implemented, and act4 cannot yet emulate it on a hart with
  the hypervisor extension (riscv/riscv-arch-test#2651).
- `B` is not claimed: Zba, Zbb and Zbs are implemented, but `misa.B` reads 0.

## Chipyard configuration

`.github/scripts/install-rocket.sh` adds `ACTRocketSaturnHConfig` to Chipyard:

```scala
new chipyard.config.WithNPerfCounters(29) ++
new freechips.rocketchip.rocket.WithHypervisor ++
new freechips.rocketchip.rocket.WithSV48 ++
new chipyard.config.WithBroadcastManager ++
new chipyard.config.WithNoDebug ++
new chipyard.MINV128D64RocketConfig
```

The broadcast coherence manager (instead of the L2) and the removal of the debug module do not
change the core; with the smaller Saturn configuration they make the model about 1.7x faster than
`REFV256D128RocketConfig`. The script builds without Chipyard's conda environment: it installs
Verilator, a JDK, CIRCT firtool, espresso and Spike's `libfesvr`/`libriscv`. espresso is required:
without it Chisel falls back to its QMC minimizer, which runs out of memory on Saturn's decoder.

## Building and running

```bash
.github/scripts/install-rocket.sh ~/repos/chipyard-builds
export PATH=$HOME/repos/chipyard-builds/bin:$PATH
make CONFIG_FILES=config/cores/rocket/rocket-saturn-rv64gcvh/test_config.yaml
./run_tests.py "run-rocket.sh --elf" work/rocket-saturn-rv64gcvh/elfs
```

## Platform

- RAM: 256 MiB at `0x8000_0000`. The ELF is preloaded with `+loadmem`, and the boot ROM jumps to
  `0x8000_0000` once fesvr raises `msip`.
- Console and exit: HTIF `tohost`/`fromhost`, polled by fesvr over the serial-TileLink port. The
  console waits for `tohost` to read 0 before each character.
- CLINT at `0x0200_0000`; `mtime` advances once every 1000 core cycles.
- External interrupts come from the SiFive UART (`0x1002_0000`, PLIC source 1): its transmit
  watermark interrupt fires when `txmark` = 1 and the FIFO is empty. PLIC context 0 is M-mode,
  context 1 S-mode.
- `RVMODEL_ACCESS_FAULT_ADDRESS` is `0x4000_0000` (unmapped).
- `RVMODEL_BOOT` clears `mie`: the boot ROM leaves `mie.MSIE` set.
- `run-rocket.sh` scores a test as passed only when the simulator exits 0 and prints the
  `RVCP-SUMMARY: TEST PASSED` line.
