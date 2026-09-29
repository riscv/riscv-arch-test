# ACT Configuration for the Hazard3 Core

[Hazard3](https://github.com/Wren6991/Hazard3) is a 32-bit RISC-V core by Luke Wren, the CPU in the
Raspberry Pi RP2350. The configuration runs the RTL under Verilator 5.036, pinned to the `develop`
branch at `ba0c83c`.

| Config                    | ISA                                                               | Modes                 |
| ------------------------- | ----------------------------------------------------------------- | --------------------- |
| `hazard3-rv32imacb-u-pmp` | RV32IMAC_Zba_Zbb_Zbc_Zbs_Zbkb_Zbkc_Zbkx_Zcb_Zicsr_Zifencei_Zicntr | M + U, 16 PMP regions |

- Privileged specification 1.12 (`Sm 1.12.0`); no F/D, no virtual memory.
- PMP: 16 regions, 4-byte granule, OFF/NA4/NAPOT/TOR.
- `Zihpm` is not claimed: `mhpmcounter3..31`/`mhpmevent3..31` are read-only zero and
  `hpmcounter3..31` are not decoded.
- `Zicntr` is claimed with `TIME_CSR_IMPLEMENTED: false`; `time` reads are emulated from the
  testbench's memory-mapped timer.

## RTL configuration

`.github/scripts/install-hazard3.sh` writes `test/sim/tb_common/hdl/config_act.vh`: Hazard3's
full feature set with `RESET_VECTOR = 0x80000000`, `MVENDORID_VAL = MCONFIGPTR_VAL = 0`, and these
extensions off: `XH3IRQ` (replaces `mip.MEIP` with a custom interrupt controller), `XH3BEXTM`,
`XH3PMPM`, `XH3POWER`, `XH3SFX`, `ZIBI`, `ZILSD`, `ZCLSD` and `ZCMP` (no ACT suites).

## Building and running

```bash
.github/scripts/install-hazard3.sh ~/repos/Hazard3-builds
export PATH=$HOME/repos/Hazard3-builds/bin:$PATH
export HAZARD3_SIM=$HOME/repos/Hazard3-builds/bin/hazard3-tb
make CONFIG_FILES=config/cores/hazard3/hazard3-rv32imacb-u-pmp/test_config.yaml
./run_tests.py "run-hazard3.sh --elf" work/hazard3-rv32imacb-u-pmp/elfs
```

## Platform

- RAM: 16 MB at `0x8000_0000`. IO at `0xC000_0000`: console `+0x000`, exit code `+0x008`, software
  interrupt set/clear `+0x010`/`+0x014`, global exclusive monitor enable `+0x018`, external
  interrupt set/clear `+0x020`/`+0x030`, `mtime`/`mtimecmp` `+0x100`/`+0x108`.
- `RVMODEL_ACCESS_FAULT_ADDRESS` is `0x9000_0000` (unmapped).
- `RVMODEL_BOOT` clears `mcountinhibit` (`CY`/`IR` reset to 1), sets `mtimecmp` to all-ones
  (`mip.MTIP` is set from reset otherwise) and enables the global exclusive monitor.
