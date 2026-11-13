# ACT Configuration for BlackParrot

[BlackParrot](https://github.com/black-parrot/black-parrot) is a Linux-capable RV64GC core from the
University of Washington and Boston University. It is tested in its `bp_tethered` testbench under
Verilator, pinned to black-parrot `909619a6`, in the default unicore configuration
`e_bp_unicore_cfg` (`bp_default_cfg_p`): 32 KB I$, 32 KB write-back D$, Sv39, no PMP, and a 128 KB
L2 in front of the testbench DRAM.

| Config                | ISA                                                      | Modes     |
| --------------------- | -------------------------------------------------------- | --------- |
| `blackparrot-rv64gcb` | RV64IMAFDCB_Zicsr_Zifencei_Zicntr_Zihpm_Sv39 (priv 1.11) | M + S + U |

The UDB configuration was checked with the UDB feature extractor. BlackParrot also decodes the
Zicbom and Zicboz instructions, but has no `menvcfg` or `senvcfg` (it implements priv 1.11), so they
are not claimed. `time` is not a CSR: M-mode emulates it from the CLINT's `mtime`.

## Building and running

```bash
.github/scripts/install-blackparrot.sh $HOME/blackparrot
export PATH=$HOME/blackparrot/bin:$PATH
export BLACKPARROT_SIM=$HOME/blackparrot/black-parrot/bp_top/verilator/results/bp_tethered.e_bp_unicore_cfg/simsc
make blackparrot-rv64gcb
```

`install-blackparrot.sh` builds Verilator and the testbench at the pinned commits and installs
`run-blackparrot.sh`. The exports match what `setup-blackparrot.sh` sets in CI.
