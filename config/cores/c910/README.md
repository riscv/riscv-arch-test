<!--
Copyright (c) 2026, Harvey Mudd College
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
--->

## DUT Configuration for the XuanTie OpenC910

[OpenC910](https://github.com/T-head-Semi/openc910) is the open-source release of
T-Head's XuanTie C910: a 64-bit, 3-issue out-of-order application-class core with an
MMU, caches and an L2, released together with a small SoC and a Verilog testbench.

`c910-openc910` is the only configuration: OpenC910 has no ISA feature knobs, so the
extension set is fixed. It is RV64IMAFDC with M/S/U modes, Sv39 only, 8 PMP entries at
4 KB granularity, 16 hardware performance counters and **privileged specification
1.10** (`mconfigptr`, `menvcfg`, `mseccfg`, `mtinst`, `mtval2` and `mstatush` are all
absent; `mcountinhibit` is present). The UDB config therefore declares `Sm`/`S` at
1.11.0, the lowest UDB offers. C910's bit-manipulation, cache-maintenance and
memory-indexed instructions are XuanTie _custom_ encodings, not `Zba`/`Zbb`/`Zbs` or
`Zicbom`/`Zicboz`, so none of those are claimed.

The DUT is the SoC in `smart_run/`, verilated: one 32 MB AXI SRAM at `0x0000_0000`, an
error responder from `0x0200_0000`, the core's CLINT at `0xB400_0000` and PLIC at
`0xB000_0000`, and a testbench character device at `0x01FF_FFF0`. Hart 0 resets at
address 0; hart 1 is held in permanent reset by the SoC wrapper, so ACT sees one hart.

### Building and running

```
$ make CONFIG_FILES=config/cores/c910/c910-openc910/test_config.yaml
$ make c910-openc910
```

`make c910-openc910` runs `run-c910.sh`, which must be on `$PATH`, with `C910_SNAPSHOT`
pointing at the directory containing `obj_dir/Vtop`. CI does both through
`.github/scripts/install-c910.sh` and `.github/scripts/setup-c910.sh`; locally,

```
$ .github/scripts/install-c910.sh ~/c910-install
$ export PATH=~/c910-install/bin:$PATH
$ export C910_SNAPSHOT=~/c910-install/openc910/smart_run/work
```

### Things worth knowing about this DUT

- **The vendor build flow does not work with Verilator 5** (`smart_run/Makefile` passes
  `-Os`, and the SoC glue has `assign #1` delays). `install-c910.sh` verilates directly
  with `--no-timing`.
- **The testbench needs three patches before it can score an ACT test at all**, all
  applied by `setup-c910.sh` and documented there: the image loader silently truncates
  anything past 256 KB, pass/fail is snooped off the integer write-back bus (with a
  bug that scores a failing value as a pass), and the process exit status is always 0.
- **Two mxstatus bits are enabled at reset and must be cleared.** `THEADISAEE` makes
  the XuanTie custom instruction set live, and `MAEE` reinterprets Sv39 PTE bits 63:59
  as memory attributes. `RVMODEL_BOOT` clears both; see `rvmodel_macros.h`.
- **`RVMODEL_BOOT` also enables the caches.** They are off out of reset, and enabling
  them is worth about 4x on every test.
- **There is no memory-mapped `mtime`**, so `RVMODEL_MTIME_ADDRESS` is undefined and
  the machine-timer-interrupt family is not tested. The `time` CSR itself is
  implemented natively, so `Zicntr` needs no emulation.
- **The CLINT is 2.8 GB away from the tests**, which is outside `la`'s reach under
  `-mcmodel=medany`, so `RVMODEL_MSIP_ADDRESS`/`RVMODEL_MTIMECMP_ADDRESS` are left
  undefined and the software-interrupt macros use `li` instead.
