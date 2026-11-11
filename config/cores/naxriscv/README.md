# ACT Configuration for the NaxRiscv Core

[NaxRiscv](https://github.com/SpinalHDL/NaxRiscv) is Charles Papon's out-of-order superscalar
RISC-V core, written in SpinalHDL. This configuration runs its standard RV64 configuration in
NaxRiscv's own Verilator simulator (`src/test/cpp/naxriscv`), pinned to commit `9f452d5` (main,
2026-01-23).

| Config                | ISA                                                         | Modes           |
| --------------------- | ----------------------------------------------------------- | --------------- |
| `naxriscv-rv64imafdc` | RV64IMAFDC_Zicsr_Zicntr_Zihpm_Zifencei_Zaamo_Zalrsc_Zca_Zcd | M + S + U, Sv39 |

- Privileged specification 1.11 (`Sm 1.11.0`, `S 1.11.0`): there is no `menvcfg`, `senvcfg`,
  `mconfigptr` or `mcountinhibit`. Sv39 with no ASID bits, 32-bit physical addresses, no PMP.
- Out-of-order core: 2-wide decode, dispatch and commit, a 64-entry reorder buffer, 64 integer
  and 64 floating-point physical registers, two ALU/branch units, one unit for multiply, divide,
  load/store address generation, CSR accesses and FPU-to-integer operations, and an FPU;
  16-entry load and store queues.
- 16 KiB 4-way instruction and data caches with 64-byte lines; the data cache is non-blocking
  with two refill and two writeback slots. 4-way/2-way TLBs of 32 sets refilled in hardware.
- Branch prediction: a 512-entry BTB, a 4 KiB GShare with 24 bits of history and a 16-entry
  return address stack.
- `mhpmcounter3`-`6` count events. `time` is not implemented; ACT emulates it from the
  simulator's `mtime`.
- `medeleg` can delegate only exceptions 0, 3, 8, 9, 12, 13 and 15.

## Generator configuration

`.github/scripts/install-naxriscv.sh` generates the RTL as NaxRiscv's Makefile does for its
default target, `rv64imafdcsu`:

```
sbt "runMain naxriscv.Gen64 --withRvc --withFloat --withDouble"
```

`Gen64` (`src/main/scala/naxriscv/Gen.scala`) calls `Config.plugins` with `xlen = 64`,
`withRdTime = false`, `aluCount = 2`, `decodeCount = 2`, `withDebug = false`, `debugTriggers = 4`
(unused without debug), `lqSize = sqSize = 16`, `asic = false`, supervisor and user modes on, and
the `Config.plugins` defaults for the rest: reset vector `0x8000_0000`, MMU on, I/O at address
bits 31:28 = 1, memory where bit 31 is set, perf counters with 4 extra counters, 32 MMU sets,
ROB 64, 32 dispatch slots, 16 branch contexts, distributed RAM and Lsu2.

The install script builds NaxRiscv's Spike fork (which the simulator links for its optional
lock-step check) and ELFIO at the commits the Makefile names, uses the system SDL2, and builds
the simulator with `make compile TRACE=no` and one makefile change: it does not link
`package.so`, a shared library made from the same Spike objects, because the second copy of
Spike's device registry aborts the simulator at start (`Plugin "clint" already registered`).
The JDK (17.0.16) and sbt (1.10.11) are the only other tools it installs.

## Simulator patch

`patches/naxriscv-sim-mtime.patch` (its SHA-256 is pinned in the install script) changes the
simulator's CLINT model in `src/test/cpp/naxriscv/src/main.cpp`:

- `mtime` is writable (it was read-only, so a store to it took a store access fault);
- `mtime` advances once every 10 cycles instead of every cycle, so that reading `time` through
  ACT's emulation trap handler returns a value close to a just-written `mtime`;
- `mip.MTIP` is set when `mtime >= mtimecmp` (it was `>`).

## Platform

- Memory at `0x8000_0000`, loaded by the simulator from the ELF. Instruction and data refills
  have a one-cycle minimum latency, and each 64-bit beat is then delivered with probability
  100/128 per cycle (the simulator's default random stall).
- Console (`putc`) at `0x1000_0000`, machine and supervisor external interrupt controls at
  `0x1000_0010` and `0x1000_0018`, CLINT at `0x1001_0000`.
- `run-naxriscv.sh` passes `--pass-symbol nax_pass` (defined by `RVMODEL_HALT_PASS`);
  `RVMODEL_HALT_FAIL` stores to the simulator's failure address `0x1000_0080`. The simulator
  always exits 0, so the runner turns its `PASS` file into the exit status. Lock-step checking
  against Spike is off (`--spike-disabled`): the tests check themselves against Sail.
- `RVMODEL_BOOT` sets `mtimecmp` to all ones; the simulator resets it to 0.
- `RVMODEL_ACCESS_FAULT_ADDRESS_LOAD` and `_STORE` are `0x1F00_0000`, an unmapped I/O address:
  loads and stores there take a bus-error access fault. The simulator's own fault address,
  `0x1230`, is neither memory nor I/O, and the core reports loads, stores and fetches there as
  page faults.
- `_FETCH` is not defined: a fetch from I/O, which is not executable, raises an instruction page
  fault instead of an access fault, and no other address gives an instruction access fault.
- `_AMO` and `_LRSC` are not defined: AMOs and SCs take the data cache's atomic path, so an AMO
  to I/O returns all ones without a fault, and an `sc.w` with no reservation fails without a bus
  access. Bus errors are implementation-defined, so both are legal.

## Building and running

```bash
.github/scripts/install-naxriscv.sh ~/repos/naxriscv-builds
export PATH=$HOME/repos/naxriscv-builds/bin:$PATH
export NAXRISCV_SIM=$HOME/repos/naxriscv-builds/bin/VNaxRiscv
make CONFIG_FILES=config/cores/naxriscv/naxriscv-rv64imafdc/test_config.yaml
./run_tests.py "run-naxriscv.sh --elf" work/naxriscv-rv64imafdc/elfs
```

The two exports do what `.github/scripts/setup-naxriscv.sh` does in CI.

## Configuration notes

The UDB feature extractor (riscv-arch-test #2442) was run on the simulator; the yaml differs from
what it reports where the source or a directed probe shows otherwise:

- `Sscounterenw` is not claimed: `scounteren` reads 0 and ignores writes.
- `PHYS_ADDR_WIDTH` is 32, the MMU's `physicalWidth` (the extractor gave an assumed 56).
- `REPORT_*_IN_STVAL_*` for illegal instructions and misaligned accesses are true, like the `mtval`
  values: those exceptions cannot be delegated, so the extractor could not observe `stval`.
- `Svade` is not claimed because UDB defines it only from `Sm 1.12`, but the MMU raises a page
  fault when A is clear and refuses stores when D is clear.
- `Zicntr` is claimed with `TIME_CSR_IMPLEMENTED: false`.

## Excluded tests (`ci.yaml`)

Each is a deviation from the specification:

- `mcounteren` and `scounteren` read 0 but do not stop S- and U-mode reads of `cycle`, `instret`
  and `hpmcounter*`.
- Interrupt priority: STI is taken before SSI, and an undelegated supervisor interrupt before a
  pending machine interrupt.
- With `mstatus.MPRV` = 1 and MPP = S, `SUM` and the U-page check are not applied.
- Sv39 translates non-canonical virtual addresses instead of raising a page fault.
- `feq`, `flt`, `fle`, `fmin` and `fmax` treat the subnormal with only the top mantissa bit set
  (`0x0040_0000` single, `0x0008_0000_0000_0000` double) as equal to zero.
