# ACT Configuration for the NEORV32 Processor

[NEORV32](https://github.com/stnolting/neorv32) is a small, highly configurable RISC-V
microcontroller written in VHDL by Stephan Nolting. The configuration runs it in a minimal
testbench, pinned to release `v1.13.7` (`b1f3072`). The RTL is not patched.

| Config                    | ISA                                                                                           | Modes                 |
| ------------------------- | --------------------------------------------------------------------------------------------- | --------------------- |
| `neorv32-rv32imacb-u-pmp` | RV32IMACB_Zbc_Zbkc_Zcb_Zicond_Zicsr_Zifencei_Zicntr_Zihpm_Zihintntl_Zihintpause_Zkt_Smcntrpmf | M + U, 16 PMP regions |

NEORV32 implements privileged specification 1.12.

## Simulation

`.github/scripts/neorv32-act-top.vhd` sets the generics of the processor top level, `neorv32_top`,
that ACT depends on; the rest keep their defaults. GHDL's synthesis front end converts it to a single Verilog module, as NEORV32's
own `rtl/verilog` flow does, and Verilator simulates that module inside
`.github/scripts/neorv32-act-tb.sv`. Simulating the VHDL directly under GHDL gives the same
results on the whole suite but runs about a hundred times slower.

The internal IMEM and DMEM are disabled, so every access outside the processor's 2 MB IO region
goes to the external bus (XBUS). The testbench is the only device on that bus. It provides 4 MB
of RAM at `0x8000_0000` that acknowledges each request in the next cycle, a console register, an
exit register and a register that drives the machine external interrupt, all at `0xF000_0000`,
and it answers every other address with a bus error. The timer and software interrupts come from
the processor's CLINT at `0xFFF4_0000`.

## Configuration

The configuration is a fast single-core microcontroller: the standard extensions that suit a
microcontroller, with the fast multiplier, the barrel shifter and an instruction cache.

| Generic                                                                                                                       | Value                  | Reason                                                                                                               |
| ----------------------------------------------------------------------------------------------------------------------------- | ---------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `CLOCK_FREQUENCY`                                                                                                             | 100 MHz                | Only scales peripheral prescalers; none are used.                                                                    |
| `DUAL_CORE_EN`                                                                                                                | `false`                | ACT tests one hart.                                                                                                  |
| `TRACE_PORT_EN`, `TRACE_SIMLOG_EN`                                                                                            | `false`                | Debug only; `neorv32-act-top.vhd` exposes them as `TRACE_EN` for a GHDL run.                                         |
| `BOOT_MODE_SELECT`, `BOOT_ADDR_CUSTOM`                                                                                        | 1, `0x8000_0000`       | Start at the base of RAM, where the tests are linked, without the bootloader or an IMEM image.                       |
| `OCD_EN`                                                                                                                      | `false`                | No on-chip debugger, so neither Sdext nor Sdtrig.                                                                    |
| `RISCV_ISA_C`, `RISCV_ISA_M`, `RISCV_ISA_U`                                                                                   | `true`                 | Compressed instructions, multiply/divide and user mode.                                                              |
| `RISCV_ISA_E`                                                                                                                 | `false`                | Full register file.                                                                                                  |
| `RISCV_ISA_Zaamo`, `RISCV_ISA_Zalrsc`                                                                                         | `true`                 | Together they make A.                                                                                                |
| `RISCV_ISA_Zba`, `RISCV_ISA_Zbb`, `RISCV_ISA_Zbs`, `RISCV_ISA_Zbc`                                                            | `true`                 | Together the first three make B; Zbc adds carry-less multiply (and with it Zbkc).                                    |
| `RISCV_ISA_Zcb`, `RISCV_ISA_Zicond`                                                                                           | `true`                 | Code-size and branch-free instructions that compilers use.                                                           |
| `RISCV_ISA_Zicntr`, `RISCV_ISA_Zihpm`                                                                                         | `true`                 | Base counters and performance monitors.                                                                              |
| `RISCV_ISA_Smcntrpmf`                                                                                                         | `true`                 | Privilege-mode filtering of `mcycle` and `minstret`, as in NEORV32's own testbench.                                  |
| `RISCV_ISA_Zbkb`, `RISCV_ISA_Zbkx`, `RISCV_ISA_Zknd`, `RISCV_ISA_Zkne`, `RISCV_ISA_Zknh`, `RISCV_ISA_Zksed`, `RISCV_ISA_Zksh` | `false`                | Scalar cryptography is not part of a general-purpose microcontroller.                                                |
| `RISCV_ISA_Zfinx`                                                                                                             | `false`                | No fused multiply-add, division or square root, and subnormals flush to zero, so it is not IEEE 754 conformant.      |
| `RISCV_ISA_Zibi`                                                                                                              | `false`                | Not ratified.                                                                                                        |
| `RISCV_ISA_Zimop`, `RISCV_ISA_Zcmop`                                                                                          | `false`                | Placeholders for future extensions; no microcontroller software uses them.                                           |
| `RISCV_ISA_Zmmul`                                                                                                             | `false`                | M already includes it.                                                                                               |
| `RISCV_ISA_Xcfu`                                                                                                              | `false`                | Custom instructions.                                                                                                 |
| `CPU_CONSTT_BR_EN`                                                                                                            | `false`                | Not-taken branches skip the pipeline flush.                                                                          |
| `CPU_FAST_MUL_EN`, `CPU_FAST_MUL_REGS`                                                                                        | `true`, 1              | Single-stage parallel multiplier instead of the 32-cycle serial one.                                                 |
| `CPU_FAST_SHIFT_EN`                                                                                                           | `true`                 | Barrel shifter instead of the serial one. It also makes shifts and rotates data-independent, so NEORV32 reports Zkt. |
| `CPU_RF_ARCH_SEL`                                                                                                             | 0                      | Default synchronous-read register file.                                                                              |
| `PMP_NUM_REGIONS`, `PMP_MIN_GRANULARITY`                                                                                      | 16, 4                  | The most regions, at the finest granularity (G=0), so NA4 is available.                                              |
| `PMP_TOR_MODE_EN`, `PMP_NAP_MODE_EN`                                                                                          | `true`                 | TOR, NA4 and NAPOT.                                                                                                  |
| `HPM_NUM_CNTS`, `HPM_CNT_WIDTH`                                                                                               | 4, 64                  | Four 64-bit counters, `mhpmcounter3`..`6`; the others read as zero.                                                  |
| `IMEM_EN`, `DMEM_EN`                                                                                                          | `false`                | The tests run from the testbench RAM on the external bus.                                                            |
| `ICACHE_EN`, `ICACHE_NUM_BLOCKS`, `CACHE_BLOCK_SIZE`, `CACHE_BURSTS_EN`                                                       | `true`, 64, 64, `true` | A 4 KB instruction cache filled by bursts, so instruction fetches do not compete with loads and stores for the bus.  |
| `DCACHE_EN`                                                                                                                   | `false`                | The RAM already answers in one cycle.                                                                                |
| `CACHE_UC_BASE`                                                                                                               | `0xF000_0000`          | Default; the testbench registers and the access-fault address are uncached.                                          |
| `XBUS_EN`, `XBUS_TIMEOUT`, `XBUS_REGSTAGE_EN`                                                                                 | `true`, 2048, `false`  | External bus to the testbench, with the default timeout and no extra register stage.                                 |
| `IO_CLINT_EN`                                                                                                                 | `true`                 | `mtime`, `mtimecmp` and `msip` for the timer and software interrupts, and the source of the `time` CSR.              |
| All other `IO_*` peripherals, `SMC_EN`                                                                                        | off                    | Not used by the tests.                                                                                               |

## Building and running

```bash
.github/scripts/install-neorv32.sh ~/repos/neorv32-builds
export PATH=$HOME/repos/neorv32-builds/bin:$PATH
export NEORV32_SIM=$HOME/repos/neorv32-builds/bin/neorv32-tb
make neorv32-rv32imacb-u-pmp
```

The install script builds GHDL and Verilator, converts and verilates the processor, and installs
the `run-neorv32.sh` runner. Building GHDL needs GNAT. The two exports do what
`.github/scripts/setup-neorv32.sh` does in CI.

## Parameters confirmed by probes

Directed probes on this testbench agree with `neorv32-rv32imacb-u-pmp.yaml` on every extension and
parameter they can measure. These entries rest on a directed probe or the data sheet:

- Zihintpause, Zihintntl and Zkt are claimed although the extractor cannot detect them: PAUSE and
  the NTL hints execute as a FENCE and as no-ops, and NEORV32 reports Zkt with the barrel shifter.
- `LRSC_FAIL_ON_NON_EXACT_LRSC: false`: an SC to another word of the reserved 64-byte granule
  succeeds and writes memory.
- `MISALIGNED_LDST_EXCEPTION_PRIORITY: high`: a misaligned load or store to a bus-error address
  raises the misaligned exception.
- `REPORT_VA_IN_MTVAL_ON_INSTRUCTION_ACCESS_FAULT: false`: a fetch access fault writes 0 to `mtval`.
- `WFI_U_MODE: true`: WFI in U-mode with `mstatus.TW` clear sleeps until the interrupt and does not
  trap.
- `PRECISE_SYNCHRONOUS_EXCEPTIONS: true` and `PMA_GRANULARITY: 2`, which no probe can measure, come
  from the data sheet and the 32-bit bus.
- `sail.json` maps Sail's own CLINT and interrupt generator at their usual addresses, which
  `tests/env/sail_macros.h` uses in the reference build, rather than the DUT's CLINT.
