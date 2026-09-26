<!--
Copyright (c) 2026, Harvey Mudd College
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
--->

## DUT Configuration for lowRISC Ibex

[Ibex](https://github.com/lowRISC/ibex) ([docs](https://ibex-core.readthedocs.io/)) is a
small 32-bit RISC-V CPU core from lowRISC, used as the main processor in OpenTitan.

`ibex-opentitan` is the `opentitan` named configuration — the largest one lowRISC runs
nightly regressions against — with `BaseIsa` forced to plain `RV32I` so the CHERIoT
logic is left out. That gives RV32IMC with `Zba`/`Zbb`/`Zbc`/`Zbs`, `Zcb`, U-mode,
16 PMP entries at granularity 0, 10 hardware performance counters, and priv spec 1.12.

The DUT is run under [Ibex Simple System](https://github.com/lowRISC/ibex/tree/master/examples/simple_system),
verilated: a single 1 MB RAM at `0x0010_0000`, a character/halt device at `0x0002_0000`
and a RISC-V machine timer at `0x0003_0000`. Tests link at `0x0010_0080`, which is the
reset vector, so no boot stub is needed.

### Building and running

```
$ make CONFIG_FILES=config/cores/ibex/ibex-opentitan/test_config.yaml
$ make ibex-opentitan
```

`make ibex-opentitan` runs `run-ibex.sh`, which must be on `$PATH`, with `IBEX_SNAPSHOT`
pointing at the FuseSoC build root (the directory containing
`lowrisc_ibex_ibex_simple_system_0/sim-verilator/Vibex_simple_system`). CI does both
through `.github/scripts/install-ibex.sh` and `.github/scripts/setup-ibex.sh`; locally,

```
$ .github/scripts/install-ibex.sh ~/ibex-install
$ export PATH=~/ibex-install/bin:$PATH IBEX_SNAPSHOT=~/ibex-install/ot-rv32i
```

### Things worth knowing about this DUT

- **The simulator always exits 0.** Pass and fail share one halt path (a store to the
  SimCtrl register) and the cycle limit also exits 0, so `run-ibex.sh` derives the
  verdict from the `RVCP-SUMMARY` line instead.
- **Console output never reaches stdout.** `simulator_ctrl` writes it to
  `ibex_simple_system.log` in the current directory, so each test runs in its own
  directory and the runner copies the log to stdout.
- **mip.MTIP is pending out of reset**, because `mtimecmp` resets to 0 while `mtime`
  starts counting. `RVMODEL_BOOT` pushes `mtimecmp` to all-ones to clear it.
- **Instruction fetches can never raise an access fault** in Simple System: the
  instruction port bypasses the bus and indexes the RAM with `addr[19:2]`. See
  `ci.yaml` for the three tests this costs.
