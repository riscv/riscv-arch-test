# ACT Configuration for SERV

[SERV](https://github.com/olofk/serv) is a bit-serial 32-bit RISC-V core. The configuration runs
SERV inside its `servant` reference SoC under its stock Verilator testbench, pinned to `f200eb2e`.

| Config         | ISA                    | Modes |
| -------------- | ---------------------- | ----- |
| `serv-rv32imc` | RV32IMC_Zicsr_Zifencei | M     |

- Privileged specification 1.11 (`Sm 1.11.0` in UDB, `Privileged_ISA_1_11` in Sail); no
  `mstatush`.
- `MCOUNTINHIBIT_IMPLEMENTED: false`; every `HPM_COUNTER_EN` is false.
- CSR addresses are decoded from instruction bits 26, 22, 21 and 20 only, and there is no
  illegal-CSR exception: `misa` and `mhpmevent3..31` alias onto `mtvec`, `mstatush` and
  `mcountinhibit` onto `mstatus`, `mip` onto `mscratch`.

## RTL configuration

Built with `width=1`, `compressed=1`, `with_csr=1`, `MDU=1`, `memsize=8388608`. SERV, `servant`
and the testbench are not patched.

## Building and running

```bash
.github/scripts/install-serv.sh ~/repos/serv-builds
export PATH=$HOME/repos/serv-builds/bin:$PATH
export SERV_SNAPSHOT=$HOME/repos/serv-builds/act
make CONFIG_FILES=config/cores/serv/serv-rv32imc/test_config.yaml
./run_tests.py "run-serv.sh --elf" work/serv-rv32imc/elfs
```

## Platform

- Tests link at address 0, the reset vector (`servant.v` does not pass `reset_pc` through).
- Console: a byte store to `0x8000_0000` appends to the `+signature=` file. Exit: a store to
  `0x9000_0000` prints `Test complete` and calls `$finish`.
- `bench/servant_tb.cpp` always exits 0, so `run-serv.sh` takes the verdict from the console.
- No custom `RVMODEL_BOOT_TO_MMODE`.
