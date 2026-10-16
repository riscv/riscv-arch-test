# ACT Configuration for XiangShan

[XiangShan](https://github.com/OpenXiangShan/XiangShan) is an open-source out-of-order RV64 core
from the Institute of Computing Technology (CAS) and the Beijing Institute of Open Source Chip.
The configuration runs the RTL of Kunminghu V2, the RVA23 design on the `kunminghu-v2` branch,
pinned to `e7bab53`, as the SimTop difftest emulator built with Verilator.

| Config            | ISA                                    | Modes                        |
| ----------------- | -------------------------------------- | ---------------------------- |
| `xiangshan-kmhv2` | RV64GCBVH_Zfa_Zfh_Zcb_Zk_Zks_Zvbb_Zvfh | M + S + U + VS + VU, Sv39/48 |

- XiangShan `KunminghuV2Config` (CHI bus, 1 MB L2, 16 MB OpenLLC). `DefaultConfig`, the Makefile
  default, is a TileLink system on which the Zicbom/Zicboz instructions raise illegal-instruction
  exceptions. Privileged 1.13, VLEN 128, ELEN 64, 32 of 64 PMP entries with a
  4 KiB grain (no NA4), 48-bit physical addresses, Sv39x4/Sv48x4 G-stage, GEILEN 7.
- AIA (Smaia/Ssaia with IMSIC), Smstateen, Sscofpmf, Sstc, Svnapot, Svpbmt, Svinval, Zicbo\*,
  pointer masking and Sdtrig are declared. Smrnmi is implemented but not declared, because the
  Sail reference model does not implement it.

## Building and running

XiangShan is not run in CI. To run it manually:

```bash
.github/scripts/install-xiangshan.sh ~/repos/xiangshan-builds
export PATH=$HOME/repos/xiangshan-builds/bin:$PATH
export XIANGSHAN_EMU=$HOME/repos/xiangshan-builds/bin/emu
make CONFIG_FILES=config/cores/xiangshan/xiangshan-kmhv2/test_config.yaml   # generate tests, build ELFs
./run_tests.py -j 16 --timeout 14400 "$(cat config/cores/xiangshan/xiangshan-kmhv2/run_cmd.txt)" \
  work/xiangshan-kmhv2/elfs
```

Add `EXTENSIONS=<suites>` to the `make` command to build a subset. A test takes from 2 minutes to
more than an hour at a few hundred cycles per second, so pass `--timeout` to `run_tests.py` as above:
`make xiangshan-kmhv2` runs the same command with the 300 s default timeout, which most tests exceed.
`run-xiangshan.sh` also takes a cycle limit (`XIANGSHAN_CYCLES`, default 20 M).

The build needs mill 0.12.3 (downloaded by the script), a JDK 11 or newer, clang, and about 24 GB
of memory for Chisel elaboration.

## Platform

- RAM at `0x8000_0000`. The emulator loads the ELF there; the reset vector is a flash image at
  `0x1000_0000` that sets `mnstatus.NMIE`, clears `mstatus.MDT` and jumps to it.
- Console: byte stores to the UART-lite transmit register at `0x4060_0004`.
- Termination: XiangShan's trap instruction (`0x0000006b`, code in `a0`); code 0 is a pass.
- CLINT at `0x3800_0000` (`msip`, `mtimecmp` `+0x4000`, `mtime` `+0xBFF8`); `mtime` advances once
  every 100 core cycles.
- External interrupts: the simulation interrupt generator at `0x4007_0000` drives PLIC source 1;
  the PLIC is at `0x3C00_0000`.
- `RVMODEL_ACCESS_FAULT_ADDRESS` is `0x3980_0000`, which the PMA table gives no permissions.
- The emulator exits 0 on a cycle-limit timeout, so `run-xiangshan.sh` passes only when the run ends
  on the trap instruction.
