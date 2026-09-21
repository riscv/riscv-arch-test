# ACT Configuration for the BSC Sargantana Core

[Sargantana](https://github.com/bsc-loca/sargantana) is an open-source 64-bit RISC-V core from the
Barcelona Supercomputing Center. It is verified here as it is delivered in the
[core_tile](https://github.com/bsc-loca/core_tile) integration, which adds the instruction cache,
the OpenHW HPDcache and the MMU that the core needs in order to run. Every UDB and Sail parameter
in the configuration cites the supporting RTL text plus a permalink pinned to the commit it was
written against.

| Config                  | ISA                                            | Modes     | Pinned commit                        |
| ----------------------- | ---------------------------------------------- | --------- | ------------------------------------ |
| `sargantana-rv64imafdb` | RV64IMAFDB_Zicsr_Zifencei_Zicond_Zicbom_Zicboz | M + S + U | core_tile `2528e7df`, core `403975c` |

The design is taken at its shipped `drac_pkg::DracDefaultConfig`; no build-time knobs are changed,
so what is measured is the core as released.

Notable shape of the configuration:

- **No C extension.** `misa` hardwires bit 2 to zero and the decoder rejects every 16-bit
  encoding, so IALIGN is 32 and `mepc` masks bit 1.
- **No PMP.** `pmpcfg0-3` and `pmpaddr0-15` exist only as empty case arms that read zero and drop
  writes; there is no address matcher in the RTL. `NUM_PMP_ENTRIES` is 0 and the PMP suites are
  not selected.
- **No misaligned support.** Every misaligned scalar load, store, AMO and LR/SC traps. The vendor's
  own test runner skips `rv64ui-*-ma_data` for the same reason.
- **Sv39 and Bare only**, with software A/D management (Svade, not Svadu), and no Svnapot, Svpbmt
  or Svinval.
- **`Sm 1.12`**, because `menvcfg` and `mstateen0-3` are implemented. The CSR file's README still
  claims privileged spec 1.11, which predates that support. RV64 means there is no `mstatush` for
  the choice to misfire on.
- **No interrupt controller.** The tile takes its timer, software and external interrupts as
  sideband pins and the standalone testbench ties all of them, and the `time` input, to zero. There
  is no CLINT and no PLIC, so `RVMODEL_MTIME_ADDRESS` is left undefined and the interrupt-driven
  suites cannot run.
- **`misa` claims V and H**, which this configuration deliberately does not: the vector support is
  a subset of RVV 1.0 with one non-standard opcode, and the hypervisor support is untested by the
  vendor flow and unsupported by ACT's invisible trap handler.

`ci.yaml` records the specific measured reason for every excluded suite.

## Building and running

```bash
# once: build the tile's Verilator model (see .github/scripts/install-sargantana.sh)
git clone --recursive https://github.com/bsc-loca/core_tile ~/repos/core_tile
cd ~/repos/core_tile && make -j"$(nproc)" sim

# build and run the tests
export PATH=<act root>/.github/scripts:$PATH   # holds run-sargantana.sh
export SARGANTANA_TILE=$HOME/repos/core_tile
cd <act root>
make CONFIG_FILES=config/cores/sargantana/sargantana-rv64imafdb/test_config.yaml
./run_tests.py "run-sargantana.sh --elf" work/sargantana-rv64imafdb/elfs
```

Two platform details are easy to get wrong and cost a lot of time:

- **`tohost` must be 64-byte aligned.** The tile recognises a tohost write by comparing the
  HPDcache write-buffer request address, which is the enclosing 64-byte memory word, against the
  address of the `tohost` symbol. A `tohost` that is not at the start of such a word never matches
  and every test silently runs to the cycle limit. `link.ld` places the whole HTIF block on its own
  64-byte boundaries for this reason.
- **The HTIF console needs a settle delay and a word-aligned buffer.** `RVMODEL_IO_WRITE_STR`
  copies the string into an aligned staging buffer (the DPI reads the buffer with word-aligned
  accesses and asserts otherwise) and spins briefly before writing `tohost`, so the syscall block
  has drained out of the write buffer by the time the model reads it.
