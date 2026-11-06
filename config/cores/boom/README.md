# ACT Configuration for BOOM

[BOOM](https://github.com/riscv-boom/riscv-boom) (the Berkeley Out-of-Order Machine) is a
superscalar out-of-order RV64 core. This configuration runs BOOM v3 as Chipyard's
`MediumBoomV3Config`, built through [Chipyard](https://github.com/ucb-bar/chipyard) 1.14.0
(`0acc1e1`, BOOM `5223e44`, rocket-chip `55bcad0`) with one local patch, and simulated with
Verilator 5.036.

| Config                  | ISA                                                   | Modes     |
| ----------------------- | ----------------------------------------------------- | --------- |
| `boom-v3-medium-rv64gc` | RV64IMAFDC_Zicsr_Zifencei_Zicntr_Zihpm_Za64rs_Za128rs | M + S + U |

- Privileged specification 1.12 (`Sm 1.12.0`, `S 1.12.0`); Sv39; Svade.
- PMP: 8 regions, 4-byte granule, OFF/TOR/NA4/NAPOT.
- 6 HPM counters (`mhpmcounter3`-`8`), 40 bits wide.
- `time` is not implemented (chipsalliance/rocket-chip#3207), so `TIME_CSR_IMPLEMENTED` is false and
  the framework emulates `time` from the CLINT `mtime`.
- BOOM writes 0 to `xtval` on illegal-instruction exceptions.
- A misaligned load, store, LR, SC or AMO raises a misaligned exception before translation, with
  priority over page and access faults (`MISALIGNED_LDST_EXCEPTION_PRIORITY: high`).
- BOOM v3 has no bit-manipulation, Zicond, Zfh or vector support (`useZba`, `useZbb`, `useZbs`
  and `useConditionalZero` are false in `BoomCoreParams`), and no hypervisor or debug triggers.

The microarchitecture is that of `MediumBoomV3Config`: 2-wide decode, dispatch and commit, 4-wide
fetch, a 64-entry ROB, separate memory (1-wide, 12 entries), integer (2-wide, 20 entries) and FP
(1-wide, 16 entries) issue queues, 80 integer and 64 FP physical registers, 16-entry load and store
queues, a TAGE-L branch predictor, and 16 KiB 4-way L1 instruction and data caches.

## Chipyard configuration

`.github/scripts/install-boom.sh` adds `ACTMediumBoomV3Config` to Chipyard:

```scala
new chipyard.config.WithBroadcastManager ++
new chipyard.config.WithNoDebug ++
new chipyard.MediumBoomV3Config
```

These are the only changes to `MediumBoomV3Config`, and neither changes the core:

- `WithBroadcastManager` replaces the inclusive L2 cache with a broadcast coherence manager in
  front of DRAM, which makes the model faster to build and to simulate.
- `WithNoDebug` removes the debug module. ACT does not use it, and without it the harness has no
  JTAG/DMI port to drive.

The script builds without Chipyard's conda environment: it installs Verilator, a JDK, CIRCT
firtool, espresso and Spike's `libfesvr`/`libriscv`. espresso is required: without it Chisel falls
back to its QMC minimizer, which can run out of memory on large decoders.

## Local patch

`install-boom.sh` applies `patches/boom-sc-fail-assert.patch`, whose SHA-256 sum it pins. It
removes a simulation-only assertion in `lsu/dcache.scala` that stops the simulation when 100 SCs in
a row fail at one address. A failing SC is legal, and the Zalrsc tests retry each SC outside the
reservation set, which must fail, 100 times; without the patch `Zalrsc-sc.w` and `Zalrsc-sc.d`
abort. The patch does not change the hardware.

## Comparison with the UDB feature extractor

The configuration was checked against the UDB feature extractor (riscv/riscv-arch-test#2442) run
on this simulator. These differences are kept:

- `Zicntr` with `TIME_CSR_IMPLEMENTED: false`: the extractor does not report Zicntr because `time`
  traps; `cycle` and `instret` exist and ACT emulates `time` from the CLINT.
- `Svade`, `Za64rs` and `Za128rs`: the extractor does not test them; they follow the RTL.
- `LRSC_FAIL_ON_VA_SYNONYM: false`: the extractor measures true, but its probe executes a load
  between the LR and the SC, and on BOOM every data-cache access clears the reservation. The
  reservation holds the physical block address.
- `PRECISE_SYNCHRONOUS_EXCEPTIONS: true` and `PMA_GRANULARITY: 12` cannot be measured; BOOM traps
  precisely, and every region in the device tree is 4 KiB aligned.
- `REPORT_VA_IN_{M,S}TVAL_ON_INSTRUCTION_MISALIGNED: false` (not measurable, because C cannot be
  disabled) and `REPORT_VA_IN_STVAL_ON_*_ACCESS_FAULT: true` (not observable, because access faults
  cannot be delegated) follow the RTL.
- `WFI_U_MODE: true`: not measured by the extractor; WFI in U-mode with `mstatus.TW` = 0 does not
  trap in the RTL.

## Building and running

```bash
.github/scripts/install-boom.sh ~/boom-act
export PATH=$HOME/boom-act/bin:$PATH
make CONFIG_FILES=config/cores/boom/boom-v3-medium-rv64gc/test_config.yaml
./run_tests.py "run-boom.sh --elf" work/boom-v3-medium-rv64gc/elfs
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
- `RVMODEL_BOOT` clears `mie` (the boot ROM leaves `mie.MSIE` set) and disables the UART source in
  both PLIC contexts.
