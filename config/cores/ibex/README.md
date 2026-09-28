<!--
Copyright (c) 2026, Harvey Mudd College
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
--->

# ACT Configuration for the Ibex Core

[Ibex](https://github.com/lowRISC/ibex) is a small 32-bit RISC-V core from lowRISC, the main
processor in OpenTitan. The configuration runs
[Ibex Simple System](https://github.com/lowRISC/ibex/tree/master/examples/simple_system) under
Verilator, pinned to `lowRISC/ibex` at `e9f5534`.

| Config           | ISA                         | Modes                 |
| ---------------- | --------------------------- | --------------------- |
| `ibex-opentitan` | RV32IMC_Zba_Zbb_Zbc_Zbs_Zcb | M + U, 16 PMP entries |

- Privileged specification 1.12.
- PMP: 16 entries, granularity 0.
- 10 hardware performance counters, 32 bits wide (`mhpmcounter3h..12h` are read-only zero).

## RTL configuration

The `opentitan` named configuration with `BaseIsa` set to `RV32I` (CHERIoT logic left out).

## Building and running

```bash
.github/scripts/install-ibex.sh ~/ibex-install
export PATH=~/ibex-install/bin:$PATH IBEX_SNAPSHOT=~/ibex-install/ot-rv32i
make CONFIG_FILES=config/cores/ibex/ibex-opentitan/test_config.yaml
make ibex-opentitan
```

`IBEX_SNAPSHOT` is the FuseSoC build root containing
`lowrisc_ibex_ibex_simple_system_0/sim-verilator/Vibex_simple_system`.

## Platform

- RAM: 1 MB at `0x0010_0000`. Character/halt device at `0x0002_0000`, machine timer at
  `0x0003_0000`.
- Tests link at the reset vector `0x0010_0080`; no boot stub.
- The simulator always exits 0; `run-ibex.sh` takes the verdict from the `RVCP-SUMMARY` line.
- Console output goes to `ibex_simple_system.log` in the current directory; `run-ibex.sh` runs
  each test in its own directory and copies the log to stdout.
- Instruction fetches never raise an access fault: the instruction port bypasses the bus and
  indexes the RAM with `addr[19:2]`. Data-side access faults work.
- `RVMODEL_BOOT` sets `mtimecmp` to all-ones (`mip.MTIP` is pending from reset otherwise).
