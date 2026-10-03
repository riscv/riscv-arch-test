# ACT Configuration for the Rocket Core

[Rocket](https://github.com/chipsalliance/rocket-chip) is the in-order RV64 core of rocket-chip. This
configuration runs it with the [Saturn](https://github.com/ucb-bar/saturn-vectors) vector unit and
the hypervisor extension, built through [Chipyard](https://github.com/ucb-bar/chipyard) 1.14.0
(`0acc1e1`, rocket-chip `55bcad0`) with Saturn master (`8ef05c9`) and three local patches, and
simulated with Verilator 5.036.

| Config                   | ISA                                                                | Modes               |
| ------------------------ | ------------------------------------------------------------------ | ------------------- |
| `rocket-saturn-rv64gcvh` | RV64IMAFDCVH_Zfh_Zba_Zbb_Zbs_Zvfh_Zvbb_Zicsr_Zifencei_Zihpm_Za64rs | M + S + U + VS + VU |

- Privileged specification 1.12 (`Sm 1.12.0`, `S 1.12.0`), `H 1.0`; Sv39 and Sv48, Sv39x4 and
  Sv48x4; Svade.
- V 1.0 from Saturn: VLEN 128, DLEN 64, ELEN 64, with Zvfh and Zvbb.
- PMP: 8 regions, 4 KiB granule (the hypervisor extension raises it from 4 bytes), OFF/TOR/NAPOT.
- 29 HPM counters, 40 bits wide.
- `Zicntr` is not claimed: `time` is not implemented (chipsalliance/rocket-chip#3207). act4 can
  emulate it on a hart with the hypervisor extension since riscv/riscv-arch-test#2651; this
  configuration does not use the emulation yet.
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

## Saturn version and local patches

The script checks out Saturn ([ucb-bar/saturn-vectors](https://github.com/ucb-bar/saturn-vectors))
at master `8ef05c9c6044f05750c49e166a784ef8fbdcb883` instead of Chipyard 1.14.0's pin `dfe75de`.
Master has fixes for `vror.vi`, `vsll.vi`, `vsra.vi`, `vssra.vi` (Saturn PR #94) and `vsmul` at
SEW 64 (PR #98), and builds with Chipyard 1.14.0 unchanged. It then applies the patches in
`patches/`, whose SHA-256 sums the script pins:

- `rocket-chip-pr3820-d1d2c5e7.patch`: rocket-chip
  [PR #3820](https://github.com/chipsalliance/rocket-chip/pull/3820) (open) at its head commit
  `d1d2c5e78138ddda9d439be0bb3081f107416ab9`. The FPU hands a `.vf` scalar to the vector unit as the
  full 64-bit register. Saturn master checks that single and half scalars are NaN-boxed (Saturn PR
  #88), but rocket-chip `55bcad0` hands them over with the low bits replicated, so without this
  patch every such scalar becomes the canonical NaN (for example `vfmv.v.f` of 1.0f gives
  `0x7fc00000`).
- `rocket-chip-tlb-superpage-gpa.patch`: the TLB superpage refill writes the entry selected by
  `waddr` (the entry that hit), as the sectored refill does (`rocket/TLB.scala`). Without it, a
  VS/VU load or store whose VS-stage leaf is a 2 MiB or 1 GiB page and whose G-stage translation
  faults neither retires nor traps; three hypervisor tests that reach such a fault time out.
- `saturn-acc-done-valid.patch`: the permute/reduction sequencer clears `valid` on `acc_done` only
  while it holds an instruction (`backend/SpecialSequencer.scala`; related issue
  [ucb-bar/saturn-vectors#74](https://github.com/ucb-bar/saturn-vectors/issues/74)). Without it, a
  stale `acc`/`acc_done` pair drops a slide or reduction at dispatch and the vector unit deadlocks;
  115 Vx and Vls tests hang, and all of them pass with the patch.

The two one-line fixes are not upstream; they let the suites run to completion so that the
remaining exclusions in `ci.yaml` reflect the other behavior of the core.

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
