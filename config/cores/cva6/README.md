## DUT Configuration for the CV32A65X

| Config     | ISA                               | Notes                                          |
| ---------- | --------------------------------- | ---------------------------------------------- |
| `cv32a65x` | RV32IMC_Zicsr_Zcb_Zba_Zbb_Zbc_Zbs | Formal release version of the CVA6 32-bit core |

See the [CV32A65X Design Document](https://docs.openhwfoundation.org/projects/cva6-user-manual/04_cv32a65x/design/design.html).

### ACT config vs CVA6 RTL (`cv32a65x_config_pkg.sv`)

| Item | RTL / TB | ACT config |
| ---- | -------- | ---------- |
| ISA | `RV32IMCZicsr_Zcb_Zba_Zbb_Zbc_Zbs` | `cv32a65x.yaml` implemented extensions |
| Privilege | M-only (`RVS=0`, `RVU=0`) | no S/U in yaml or sail |
| `mtvec` | direct-only (`DirectVecOnly=1`); RTL clears `mtvec[1:0]` (4-byte); ACT yaml uses 256 for UDB/Sail sig compatibility | `MTVEC_BASE_ALIGNMENT_DIRECT: 256`, sail `base_alignment: 8` |
| `mtval` | hardwired 0 (`TvalEn=0`) | all `REPORT_*_IN_MTVAL_*: false`, `MTVAL_WIDTH: 0` |
| MSIP / M-mode software IRQ | `SoftwareInterruptEn=0`, CLINT MSIP N/A | sail `machine.software: false`; **Sm tests excluded** (see `ci.yaml`) |
| MEXT / UART IRQ | PLIC present; Verilator TB `InclUART=0` (no UART→PLIC wire-up) | `RVMODEL_SET_MEXT_INT` macros present; MEXT covered when Sm enabled |
| Timer (MTIP) | CLINT `0x02000000` | `RVMODEL_MTIME/MTIMECMP` in `rvmodel_macros.h` |
| PMP | 8 entries in RTL (`NrPMPEntries=8`), no NAPOT (`PMPNapotEn=0`) | UDB yaml `NUM_PMP_ENTRIES: 0` (only valid value without PMPSm); PMPSm excluded in `ci.yaml` |
| HPM / counters | `RVZicntr=0`, `RVZihpm=0`, `PerfCounterEn=0` | no Zicntr/Zihpm; all HPM counters disabled |
| Halt | `tohost` pass/fail (1/3) | `RVMODEL_HALT_*` + runner `+tohost_addr=` |

Same flow as CVE2 (`install-cve2.sh` → `export PATH` → `export *_ROOT` → `make <config>`).

### One-time setup

**Later** (runner on upstream `openhwgroup/cva6`):

```bash
cd riscv-arch-test
bash .github/scripts/install-cva6.sh ./cva6
```

**Local fork** (clone or copy your checkout into the staging tree first, same as other cores):

```bash
cd riscv-arch-test
git clone /path/to/your/cva6 ./cva6/cva6   # or copy tree into ./cva6/cva6/
bash .github/scripts/install-cva6.sh ./cva6
```

This creates a staging layout (same pattern as CVE2/CVE4):

```
./cva6/
├── bin/run-cv32a65x.sh
└── cva6/              # CVA6 source tree (tools/, work-ver/, …)
```

### Every new shell (minimum — same as other cores)

```bash
cd riscv-arch-test
export PATH="$(pwd)/cva6/bin:$PATH"
export CVA6_ROOT="$(pwd)/cva6/cva6"
```

### Run tests

```bash
make cv32a65x JOBS=1 EXCLUDE_EXTENSIONS=Sm
```

For serial simulation (avoids Verilator OOM), run the sim phase separately:

```bash
make CONFIG_FILES=config/cores/cva6/cv32a65x/test_config.yaml JOBS=1 EXCLUDE_EXTENSIONS=Sm
./run_tests.py -j 1 "$(cat config/cores/cva6/cv32a65x/run_cmd.txt)" work/cv32a65x/elfs
```

### Build ELFs only

```bash
make CONFIG_FILES=config/cores/cva6/cv32a65x/test_config.yaml
```

### Debug traces (`DEBUG=True`)

With `make cv32a65x DEBUG=True`, ACT generates Sail reference traces at build time (`work/cv32a65x/build/<test>.sig.trace`) and, during the run, DUT artifacts under `work/cv32a65x/logs/`:

| File | Content |
| ---- | ------- |
| `<test>.trace.log` | DUT instruction trace (RVFI via spike-dasm) |
| `<test>.fst` | Verilator waveform (FST) |
| `<test>.log` | Simulator stdout and RVCP-SUMMARY |
