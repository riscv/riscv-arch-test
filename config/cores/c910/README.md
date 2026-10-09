<!--
Copyright (c) 2026, Harvey Mudd College
SPDX-License-Identifier: Apache-2.0
--->

# ACT Configuration for the XuanTie OpenC910

[OpenC910](https://github.com/T-head-Semi/openc910) is T-Head's open-source 64-bit, 3-issue
out-of-order application-class core. The configuration runs the `smart_run/` SoC under Verilator
5.036, pinned to `b91c909`.

| Config          | ISA        | Modes                  |
| --------------- | ---------- | ---------------------- |
| `c910-openc910` | RV64IMAFDC | M + S + U, Sv39, 8 PMP |

- C910 implements privileged specification 1.10. `Sm` and `S` are declared at 1.11.0, the lowest
  version UDB offers.
- PMP: 16 entries, of which 8 are usable, with a 4 KB granule. 16 hardware performance counters.

## RTL configuration

- `install-c910.sh` verilates directly with `--no-timing`, because the vendor `smart_run/Makefile`
  flow does not work with Verilator 5.
- `setup-c910.sh` patches the testbench to load a 4 MB image, to end the simulation on a store to
  a pass or fail address, and to take the cycle limit from the Verilator command line.
- Hart 1 is held in reset by the SoC wrapper; ACT sees one hart.

## Building and running

```bash
.github/scripts/install-c910.sh ~/c910-install
export PATH=~/c910-install/bin:$PATH
export C910_SNAPSHOT=~/c910-install/openc910/smart_run/work
EXCLUDE_EXTENSIONS=Sv make c910-openc910
```

The install script checks out the pinned commit and installs `run-c910.sh`. `Sv` is excluded
because the reference model cannot run `Sv_sv39_VA_all_zeros_Smode`, which maps VA 0 over the
test image; `ci.yaml` lists the other suites that fail.

The model runs at 1,000 to 2,000 cycles per second. The CSR tests in `S`, `U` and
`ExceptionsZaamo` take about 280,000 cycles, so on a busy host they can exceed the 300 s limit
that `run_tests.py` sets for each test.

## Platform

- RAM is a 32 MB AXI SRAM at `0x0000_0000`, and hart 0 resets to address 0, so tests link there.
- The testbench prints stores to `0x01FF_FFF0` and ends the simulation on a store to
  `0x01FF_FFE0` (pass) or `0x01FF_FFD0` (fail).
- The CLINT at `0xB400_0000` has no `mtime` register and is beyond the reach of `la`, so
  `RVMODEL_MTIME_ADDRESS`, `RVMODEL_MTIMECMP_ADDRESS` and `RVMODEL_MSIP_ADDRESS` are undefined.
- `RVMODEL_BOOT` clears `mxstatus.THEADISAEE` and `mxstatus.MAEE`, which reset to 1, and enables
  the caches and branch prediction.
