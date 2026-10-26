# ACT Configuration for SERV

[SERV](https://github.com/olofk/serv) is a bit-serial 32-bit RISC-V core. The configuration runs
SERV in its `servant` reference SoC under the stock Verilator testbench, pinned to commit
`f200eb2e`. The RTL is built with `width=1`, `compressed=1`, `with_csr=1`, `MDU=1` and
`memsize=8388608`, and is not patched.

| Config         | ISA                    | Modes |
| -------------- | ---------------------- | ----- |
| `serv-rv32imc` | RV32IMC_Zicsr_Zifencei | M     |

SERV implements privileged specification 1.11.

## Building and running

```bash
.github/scripts/install-serv.sh ~/repos/serv-builds
export PATH=$HOME/repos/serv-builds/bin:$PATH
export SERV_SNAPSHOT=$HOME/repos/serv-builds/act
make serv-rv32imc
```

The install script builds Verilator and the SERV simulator and installs the `run-serv.sh` runner.
The two exports do what `.github/scripts/setup-serv.sh` does in CI.
