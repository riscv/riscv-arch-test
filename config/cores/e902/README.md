<!--
Copyright (c) 2026, Harvey Mudd College
SPDX-License-Identifier: Apache-2.0
--->

# ACT Configuration for the XuanTie OpenE902

[OpenE902](https://github.com/T-head-Semi/opene902) is T-Head's open-source 32-bit, two-stage
in-order microcontroller core. The configuration runs the `smart_run/` SoC testbench under
Verilator 5.052, pinned to `9918364`.

| Config               | ISA     | Modes              |
| -------------------- | ------- | ------------------ |
| `e902-rv32emc-u-pmp` | RV32EMC | M + U, 8 PMP, CLIC |

The release is generated RTL. No RTL file tests the `ifdef` options in `cpu_cfig.h`; the RTL reads
only a few of its values (the CLIC's interrupt count and priority bits, and the `mcpuid` version
fields). So this is the only configuration: RV32E with 16 GPRs, M with an iterative multiplier and
divider, C, Zicsr, Zifencei, U-mode, 8 PMP entries with a 4-byte grain, and a CLIC. There is no
cache. E902 implements privileged specification 1.10, so `Sm` is declared at 1.11.0, the lowest
version UDB offers.

The PMP grain follows the RTL and the user manual (4 bytes). The datasheet says "Minimum 4KB address
range" instead.

## Status

- The UDB yaml declares the E base, which UDB 0.1.18 rejects ("E is not a known extension"). The
  configuration builds once UDB has E ([riscv-unified-db#2643](https://github.com/riscv/riscv-unified-db/pull/2643)).
  `ci.yaml` keeps it out of CI until then.
- ACT's privileged tests all require I, so on an E base ACT runs only the unprivileged suites: E, M,
  Zca and Zmmul. `ci.yaml` lists the tests that fail.

## Testbench patch and build

- `setup-e902.sh` patches `smart_run/logical/tb/tb.v` to load one 512 KB image, `mem.pat`, into
  the instruction-bus SRAM, to print the cycle count at the end, to take `MAX_RUN_TIME` and
  `LAST_CYCLE` from the Verilator command line, to declare the `uart0_sout` net, and to skip the
  no-retire watchdog on cycle 0. The RTL is not changed.
- `install-e902.sh` verilates the testbench with `--timing`, because the vendor `smart_run/Makefile`
  supports only iverilog, VCS and irun, and the testbench uses delays, `wait` and `force`. It caps a
  test at 20 M cycles. The model runs at about 150,000 cycles per second.

## Building and running

```bash
.github/scripts/install-e902.sh ~/e902-install
export PATH=~/e902-install/bin:$PATH
export E902_SNAPSHOT=~/e902-install/opene902/smart_run/work
make e902-rv32emc-u-pmp
```

## Platform

- The core resets to address 0 and sends fetches, loads and stores below `0x2000_0000` to a 512 KB
  instruction-bus SRAM with no wait states, so tests link at 0. The top 4 KB, `0x7_F000`, is kept
  out of the image for the trap trampoline.
- The testbench prints the low byte of every store to `0x6000_FFF8` and ends the simulation when the
  stored word is `0xFFF` (pass) or `0xEEE` (fail).
- The system bus answers addresses outside its RAM and peripheral windows with an error, so
  `RVMODEL_ACCESS_FAULT_ADDRESS` is `0x3000_0000`.
- Interrupts reach the core only through the CLIC, and `mie` and `mip` read 0, so the interrupt
  macros are undefined.

## Deviations from the privileged specification

- `mtvec.MODE` is hardwired to 3 (CLIC mode). Exceptions go to `BASE` with bits 5:2 cleared, so the
  configuration declares direct mode with 64-byte alignment. Because `mtvec` reads back MODE 3, the
  trap prolog copies its trampoline to the `mtvec` target, and `RVMODEL_BOOT` points `mtvec` at
  `0x7_F000` first.
- In CLIC mode `mcause` bits 29:27 alias `mstatus.MPP` and `MPIE`, so an M-mode trap reads
  `0x3000_0000` above the cause.
- `mcounteren`, which a hart with U-mode must implement, raises illegal instruction, as do the
  recommended `mhpmcounter3-31`, `mhpmcounter3h-31h` and `mhpmevent3-31`.
  `rvtest_setup.h` writes them on every boot, so `RVMODEL_INVISIBLE_TRAP_HANDLER` emulates M-mode
  accesses to them as read-only zero.
- `minstret` reads 0, and `cycle`, `time` and `instret` do not exist, so Zicntr is not declared.
