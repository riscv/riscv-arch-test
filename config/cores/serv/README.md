# ACT Configuration for SERV

[SERV](https://github.com/olofk/serv) is the award-winning bit-serial RISC-V CPU: a 32-bit core
whose datapath is one bit wide, so every instruction takes 32 or more cycles. This configuration
targets SERV inside its own `servant` reference SoC and its stock Verilator testbench. It is
written against a pinned upstream commit, and every non-obvious UDB and Sail parameter cites the
supporting RTL text plus a permalink to it.

| Config         | ISA                    | Modes | Pinned commit |
| -------------- | ---------------------- | ----- | ------------- |
| `serv-rv32imc` | RV32IMC_Zicsr_Zifencei | M     | `f200eb2e`    |

The build knobs are the ones SERV's own compliance flow uses: `width=1`, `compressed=1`,
`with_csr=1`, `MDU=1`, `memsize=8388608`. Nothing in SERV, `servant` or the testbench is patched;
this port is config plus scripts.

SERV implements privileged specification 1.11, so it is declared `Sm 1.11.0` to UDB and
`Privileged_ISA_1_11` to Sail. That matters: `mstatush` arrived in 1.12, SERV has no `mstatush`,
and ACT guards every access to it behind `SM1P12P0_OR_LATER_SUPPORTED`.

Declaring 1.11 to Sail rather than 1.12 costs one test, `Sm_mcsr_walk-11` at bin
`mstatush_set_bit_6`. At 1.12 the reference model and SERV happened to agree, because SERV aliases
`mstatush` onto `mstatus`; at 1.11 they do not, which is the aliasing showing through rather than a
new defect. `Sm` is excluded either way, so the CI result is unchanged.

## The CSR address aliasing, and why the configuration is enough

SERV decodes a CSR address from four instruction bits only - 26, 22, 21 and 20 - and never raises
an illegal-CSR exception, so every unimplemented CSR silently aliases onto one of the seven real
ones: `misa` and `mhpmevent3..31` onto `mtvec`, `mstatush` and `mcountinhibit` onto `mstatus`,
`mip` onto `mscratch`.

That is survivable only because ACT's boot and trap handler are gated. This configuration declares
`Sm 1.11.0` (no `mstatush`), `MCOUNTINHIBIT_IMPLEMENTED: false` and every `HPM_COUNTER_EN` false,
which removes all 31 boot writes that would otherwise land on `mtvec` or `mstatus`; the `misa`
reads in the trap handler are inside `#ifdef H_SUPPORTED`. The only `mip` access that survives is
`csrw mip, zero` in the boot sequence, which lands on `mscratch` before the trap prolog
initializes it and is therefore harmless. The two trap-handler `mip` reads are both on
interrupt-only paths that this M-mode-only, interrupt-free configuration never reaches. No custom
`RVMODEL_BOOT_TO_MMODE` is needed.

Current results: 88/116 with nothing excluded, 77/77 with the exclusions in `ci.yaml`, which
records the measured reason for every excluded suite.

## Building and running

```bash
# once: clone and verilate (see .github/scripts/install-serv.sh for the exact command)
.github/scripts/install-serv.sh ~/repos/serv-builds

# build and run the tests
export PATH=$HOME/repos/serv-builds/bin:$PATH   # holds run-serv.sh
export SERV_SNAPSHOT=$HOME/repos/serv-builds/act
cd <act root>
make CONFIG_FILES=config/cores/serv/serv-rv32imc/test_config.yaml
./run_tests.py "run-serv.sh --elf" work/serv-rv32imc/elfs
```

The tests link at address 0 because `servant.v` does not plumb `servile`'s `reset_pc` parameter
through, so 0 is the reset vector and no boot stub is possible without patching the RTL.

`run-serv.sh` derives the verdict from the console rather than the exit code: `bench/servant_tb.cpp`
ends in an unconditional `exit(0)`, so a hang, a timeout and a failing test all look like success
to the shell.

## Console and termination

`servile_mux` provides two simulation hooks, and this port uses both instead of the bit-banged
UART, which would be ruinously slow on a bit-serial core: a byte store to `0x8000_0000` appends to
the `+signature=` file, which serves as the console, and a store to `0x9000_0000` prints
`Test complete` and calls `$finish`.
