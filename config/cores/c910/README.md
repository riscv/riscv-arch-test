<!--
Copyright (c) 2026, Harvey Mudd College
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
--->

# ACT Configuration for the XuanTie OpenC910

[OpenC910](https://github.com/T-head-Semi/openc910) is T-Head's open-source 64-bit, 3-issue
out-of-order application-class core. The configuration runs the `smart_run/` SoC under Verilator
5.036, pinned to `b91c909`.

| Config          | ISA        | Modes                  |
| --------------- | ---------- | ---------------------- |
| `c910-openc910` | RV64IMAFDC | M + S + U, Sv39, 8 PMP |

- Privileged specification 1.10: `mconfigptr`, `menvcfg`, `mseccfg`, `mtinst`, `mtval2` and
  `mstatush` are absent; `mcountinhibit` is present. `Sm`/`S` are declared at 1.11.0, the lowest
  UDB offers.
- PMP: 8 entries, 4 KB granule. 16 hardware performance counters.
- `Zba`/`Zbb`/`Zbs`/`Zicbom`/`Zicboz` are not claimed: C910's bit-manipulation and
  cache-maintenance instructions are XuanTie custom encodings.
- `Zicntr`: `time` is implemented natively.

## RTL configuration

- `install-c910.sh` verilates directly with `--no-timing` (the vendor `smart_run/Makefile` flow
  does not work with Verilator 5).
- `setup-c910.sh` patches the testbench: the image loader no longer truncates past 256 KB,
  pass/fail detection is fixed, and the process exit status reflects the result.
- Hart 1 is held in reset by the SoC wrapper; ACT sees one hart.

## Building and running

```bash
.github/scripts/install-c910.sh ~/c910-install
export PATH=~/c910-install/bin:$PATH
export C910_SNAPSHOT=~/c910-install/openc910/smart_run/work
make CONFIG_FILES=config/cores/c910/c910-openc910/test_config.yaml
make c910-openc910
```

## Platform

- RAM: 32 MB AXI SRAM at `0x0000_0000`; hart 0 resets at address 0. AXI error responder from
  `0x0200_0000`. PLIC at `0xB000_0000`, CLINT at `0xB400_0000`. Testbench character device at
  `0x01FF_FFF0`.
- No memory-mapped `mtime`: `RVMODEL_MTIME_ADDRESS` is undefined and machine-timer interrupts are
  not tested.
- The CLINT is out of `la` range under `-mcmodel=medany`: `RVMODEL_MSIP_ADDRESS`/
  `RVMODEL_MTIMECMP_ADDRESS` are undefined and the software-interrupt macros use `li`.
- `RVMODEL_BOOT` clears `mxstatus.THEADISAEE` (XuanTie custom instructions) and `mxstatus.MAEE`
  (Sv39 PTE bits 63:59 as memory attributes), both set at reset, and enables the caches.
