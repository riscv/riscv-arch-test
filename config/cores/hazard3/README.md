# ACT Configuration for the Hazard3 Core

[Hazard3](https://github.com/Wren6991/Hazard3) is an open-source 32-bit RISC-V core by Luke Wren,
best known as the CPU in the Raspberry Pi RP2350. This configuration is written against a pinned
upstream commit, and every non-obvious UDB and Sail parameter cites the supporting text plus a
permalink to it.

| Config                    | ISA                      | Modes                 | Pinned commit |
| ------------------------- | ------------------------ | --------------------- | ------------- |
| `hazard3-rv32imacb-u-pmp` | RV32IMACB_Zicsr_Zifencei | M + U, 16 PMP regions | `8af9929`     |

The full ISA is RV32I + M + A + C + ratified B 1.0 (Zba/Zbb/Zbs) + Zbc + Zbkb + Zbkx + Zcb +
Zicsr + Zifencei + Zicntr, with M-mode and U-mode, 16 PMP regions at a 4-byte granule with
OFF/NA4/NAPOT/TOR, and no F/D and no virtual memory. Hazard3 implements privileged specification
1.12, so it is declared `Sm 1.12.0`: `mstatush` is decoded (hardwired 0) and `mconfigptr` is
implemented, both of which 1.12 made mandatory.

`Zihpm` is deliberately not claimed. `mhpmcounter3..31` and `mhpmevent3..31` are decoded but
hardwired to 0, and the unprivileged `hpmcounter3..31` shadows that Zihpm actually provides to
U-mode are not decoded at all.

`Zicntr` **is** claimed, with `TIME_CSR_IMPLEMENTED: false`. Hazard3 has no `time`/`timeh` CSR, but
the reference testbench provides a standard memory-mapped 64-bit machine timer at `0xC000_0100`, so
ACT emulates `time` reads from it through the invisible trap handler. That also makes the machine
timer interrupt testable, which is the piece most small cores have to drop.

## The RTL configuration

The core is built from `test/sim/tb_common/hdl/config_act.vh`, which
`.github/scripts/install-hazard3.sh` writes into the Hazard3 tree. It is the bundled
`config_pmpfull.vh` (the RP2350 feature set plus Zbc and 16 PMP regions) with five changes:

- `RESET_VECTOR = 0x80000000`, the base of the testbench's RAM. The image is loaded as a flat
  binary at `MEM_BASE` and there is no boot ROM, so the reset vector must equal the link address.
- `EXTENSION_XH3IRQ = 0`. With Hazard3's nonstandard interrupt controller enabled, external
  interrupts arrive through a 512-source priority controller and its `meiea`/`meipa` CSRs instead
  of plain `mip.MEIP`, and ACT's external-interrupt tests never see the interrupt.
- `EXTENSION_XH3BEXTM / XH3PMPM / XH3POWER = 0`: custom extensions with no ACT suite, occupying
  encodings ACT expects to be illegal.
- `EXTENSION_ZILSD / ZCLSD / ZCMP = 0`: frozen rather than ratified, no ACT suite, and the RISC-V
  GCC 15.2 multilib set has no Zcmp library.
- `MVENDORID_VAL` and `MCONFIGPTR_VAL` set to 0. The bundled values are placeholders; the manual
  permits all-zeroes for both, which is what the UDB config declares.

## Building and running

```bash
# once: build Verilator and the Hazard3 testbench
.github/scripts/install-hazard3.sh ~/repos/Hazard3-builds

# build and run the tests
export PATH=$HOME/repos/Hazard3-builds/bin:$PATH   # holds run-hazard3.sh
export HAZARD3_SIM=$HOME/repos/Hazard3-builds/bin/hazard3-tb
make CONFIG_FILES=config/cores/hazard3/hazard3-rv32imacb-u-pmp/test_config.yaml
./run_tests.py "run-hazard3.sh --elf" work/hazard3-rv32imacb-u-pmp/elfs
```

Two gotchas in Hazard3's bundled testbench Makefile, both handled by `install-hazard3.sh`:
`BUILD_DIR` is keyed on the file list rather than on `CONFIG` and the verilate stamp does not
depend on `config_*.vh`, so a build directory left over from another `CONFIG` is silently
relinked; and the library rule forces a precompiled header that makes GCC spend over ten minutes
in one `cc1plus`, which is avoided by driving the generated `Vtb.mk` directly.

## Platform contract

16 MB of plain RAM at `0x8000_0000` and one IO window at `0xC000_0000`: console at `+0x000`,
pass/fail exit code at `+0x008`, software-interrupt set/clear at `+0x010`/`+0x014`, the AHB5 global
exclusive monitor enable at `+0x018`, external-interrupt set/clear at `+0x020`/`+0x030`, and
`mtime`/`mtimecmp` at `+0x100`/`+0x108`. With `--cpuret` the testbench's process exit status is the
word the CPU wrote to the exit register, so the runner needs no log scraping. `0x9000_0000` is
unmapped and is used as `RVMODEL_ACCESS_FAULT_ADDRESS`.

`RVMODEL_BOOT` does three things: clears `mcountinhibit` (`.CY` and `.IR` reset to 1, so the
counters are stopped out of reset), writes all-ones to `mtimecmp` (it resets to 0 while `mtime`
starts at 0 and increments every cycle, so `mip.MTIP` is asserted from cycle 0), and enables the
testbench's global exclusive monitor (`HEXOKAY` is tied high until then, which would let every
`sc.w` with a live local reservation succeed regardless of address).

## Results

258 tests selected, 240 pass. `ci.yaml` records the reason for every excluded suite, and
`~/reviews/act-ports/hazard3-discrepancies.md` has the per-test analysis. Every failing test also
passes on `config/sail/sail-rv32-max`, so none of them is an ACT framework bug.
