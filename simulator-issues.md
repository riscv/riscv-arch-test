# Simulator & Coverage Issues Tracker

This file tracks known failures and confirmed simulator (Sail) bugs discovered during coverage
test suite runs. The purpose of this test suite is to **verify the simulator** — identifying a
Sail bug is a significant finding.

## Bug Report Standard

Every claimed Sail bug **must** include:

1. **Exact command** to reproduce (copy-pasteable)
2. **Trace quote** — the relevant lines from the Sail trace log showing the failure
3. **Analysis** — why the observed behavior contradicts the RISC-V specification
4. **Comparison** — if applicable, show correct behavior on a different config (e.g. RV64 vs RV32)

Without all four elements, the issue is "suspected" not "confirmed."

## Status Legend

- **confirmed-sail-bug**: Sail produces incorrect results, with full reproduction evidence below
- **suspected-sail-bug**: Behavior is suspicious, needs trace evidence before confirming
- **unsupported**: Added to `unsupported_tests` in `vector-testgen-unpriv.py`
- **resolved**: Issue has been fixed

---

## Confirmed Issues

### 7. RV32 `vloxei64.v` (and all ei64 indexed LS) — Illegal instruction decode

- **Status**: confirmed-sail-bug
- **Instructions**: All `*ei64*` indexed LS on RV32:
  `vloxei64.v`, `vluxei64.v`, `vsoxei64.v`, `vsuxei64.v`, and all segmented variants
  (`vloxseg*ei64.v`, `vluxseg*ei64.v`, `vsoxseg*ei64.v`, `vsuxseg*ei64.v`)
- **Affected**: RV32 only (RV64 works correctly)
- **Custom bins blocked on RV32**:
  `cp_custom_indexed_emul_data_only`, `cp_custom_masked_vs2_v0`,
  `cp_custom_ls_indexed_truncated`, `cp_custom_ls_indexed_zero_extended_sew*`

#### Reproduction

```bash
# Config: sail-rv32-max with V extension "Full", elen_exp=6 (ELEN=64), vlen_exp=10 (VLEN=1024)
# Required: MAXINDEXEEW=64 in config/sail/sail-rv32-max/rvtest_config.h

# 1. Build the test
make clean && make vector-tests
# 2. Run Sail with trace (will hang — use 10s timeout)
timeout 10s sail_riscv_sim --trace-all \
  --trace-output /tmp/vloxei64_rv32_trace.log \
  --config config/sail/sail-rv32-max/sail.json \
  work/sail-rv32-max/build/rv32i/VlsCustom16/VlsCustom16-vloxei64.v.sig.elf
# Exit code 124 (timeout) — Sail hangs in infinite trap loop
```

#### Trace Evidence

Last valid instruction before the hang (from `/tmp/vloxei64_rv32_trace.log`):

```
[161] [M]: 0x80000272 (0x5E0FBE57) vmv.v.i v28, -0x1
v28 <- 0x...FFFFFFFFFFFFFFFF

[162] [M]: 0x80000276 (0x0FC9FB87) illegal 0xfc9fb87    VlsCustom16_vloxei64_v_cg_cp_custom_ls_indexed+0
trapping from M to M to handle illegal-instruction
handling exc#illegal-instruction at priv M with tval 0x0FC9FB87
CSR mcause (0x342) <- 0x00000002
CSR mepc (0x341) <- 0x80000276

trapping from M to M to handle fetch-access-fault
handling exc#fetch-access-fault at priv M with tval 0x00000000
CSR mcause (0x342) <- 0x00000001
CSR mepc (0x341) <- 0x00000000
[... infinite trap loop at PC=0x0 ...]
```

#### Analysis

Encoding `0x0FC9FB87` decodes as:

- `opcode[6:0] = 0000111` (LOAD-FP / vector load)
- `funct3[14:12] = 111` (EEW=64, indexed load)
- `funct6[31:26] = 000011` (unordered indexed)
- `vm[25] = 1` (unmasked)
- `vd = v23, rs1 = x19, vs2 = v28`

This is `vloxei64.v v23, (x19), v28` — a valid RISC-V V instruction. Per the V spec (Section 7.3),
indexed vector loads are valid as long as the implementation supports the index EEW, which it does
(`elen_exp=6` in `sail.json` → ELEN=64). **Sail incorrectly decodes this as `illegal` on RV32.**

#### Comparison with RV64

The same instruction class succeeds on RV64:

```bash
timeout 10s sail_riscv_sim --trace-all \
  --trace-output /tmp/vloxei64_rv64_trace.log \
  --config config/sail/sail-rv64-max/sail.json \
  work/sail-rv64-max/build/rv64i/VlsCustom16/VlsCustom16-vloxei64.v.sig.elf
# Exit code 0 — SUCCESS
```

RV64 trace shows correct decode:

```
[187] [M]: 0x00000000800002DA (0x0FCA7B87) vloxei64.v v23, (x20), v28
```

#### Workaround

`config/sail/sail-rv32-max/rvtest_config.h` sets `MAXINDEXEEW 32` to skip ei64 tests on RV32,
avoiding the hang. This is correct given the Sail bug — the config should be changed to
`MAXINDEXEEW 64` once Sail is fixed.

---

### 1–3. Segmented loads — resolved (Spike validates Sail)

- **Status**: resolved
- **Date tested**: 2026-04-08
- **Instructions**: `vlseg3e32.v`, `vlseg3e32ff.v`, `vlseg4e32.v`

All 24 Spike tests PASS on both RV32 and RV64 across all SEW variants (Vls8–Vls64).
Sail and Spike agree — these are not simulator bugs. Removed from `unsupported_tests`.

#### Reproduction

```bash
# 1. Comment out vlseg3e32.v, vlseg3e32ff.v, vlseg4e32.v in unsupported_tests
# 2. Isolate and build:
python3 isolate_coverpoint.py Vls --tests vlseg3e32.v vlseg3e32ff.v vlseg4e32.v
make clean && make vector-tests
# 3. Build spike ELFs and run:
CONFIG_FILES="config/spike/spike-rv64-max/test_config.yaml config/spike/spike-rv32-max/test_config.yaml" \
  EXTENSIONS=Vls8,Vls16,Vls32,Vls64 make elfs
./run_tests.py "$(cat config/spike/spike-rv64-max/run_cmd.txt)" work/spike-rv64-max/elfs
./run_tests.py "$(cat config/spike/spike-rv32-max/run_cmd.txt)" work/spike-rv32-max/elfs
# Result: All 12 RV64 + 12 RV32 = 24 tests PASS
python3 isolate_coverpoint.py --restore Vls
```

---

### 4–5. Segmented stores (`vsseg3e32.v`, `vsseg3e64.v`) — confirmed Sail/Spike disagreement

- **Status**: confirmed-sail-spike-mismatch
- **Date tested**: 2026-04-08
- **Instructions**: `vsseg3e32.v`, `vsseg3e64.v`
- **Affected**: RV32 + RV64, all SEW variants that complete Sail simulation

Spike FAILS on every self-checking ELF for both instructions. Sail generates signatures
that Spike disagrees with, specifically in masked segmented store operations.

| Instruction   | Spike RV64 | Spike RV32 |
| ------------- | ---------- | ---------- |
| `vsseg3e32.v` | 3/3 FAIL   | 3/3 FAIL   |
| `vsseg3e64.v` | 1/1 FAIL   | 1/1 FAIL   |

**Note**: Some SEW variants (Vls8, Vls16 for e32; Vls8–Vls32 for e64) hang during Sail
simulation due to a test-gen register alignment bug. The tests that DO complete Sail
simulation all fail the Spike comparison.

#### Spike Evidence (vsseg3e32.v, Vls32, RV64)

```
RVCP-SUMMARY: TEST FAILED - Test File "vsseg3e32.v.S"
RVCP: Test Info: "test: 63; cp: Vls32_vsseg3e32.v_cg/cp_masking_edges (Test v0 = zeroes)"
RVCP: Bad Value:      0x000000008002bb40
RVCP: Expected Value: 0x000000008f0d885c
```

Sail produced `0x8f0d885c` as the expected signature value; Spike produced `0x8002bb40`.
The mismatch occurs in `cp_masking_edges` — a masked store operation.

#### Reproduction

```bash
# 1. Comment out vsseg3e32.v, vsseg3e64.v in unsupported_tests
python3 isolate_coverpoint.py Vls --tests vsseg3e32.v vsseg3e64.v
make clean && make vector-tests
CONFIG_FILES="config/spike/spike-rv64-max/test_config.yaml config/spike/spike-rv32-max/test_config.yaml" \
  EXTENSIONS=Vls8,Vls16,Vls32,Vls64 make elfs
./run_tests.py "$(cat config/spike/spike-rv64-max/run_cmd.txt)" work/spike-rv64-max/elfs
./run_tests.py "$(cat config/spike/spike-rv32-max/run_cmd.txt)" work/spike-rv32-max/elfs
# Result: All tests FAIL
# Logs: work/spike-rv64-max/logs/rv64i/Vls32/Vls32-vsseg3e32.v.log
python3 isolate_coverpoint.py --restore Vls
```

---

### 6. `vwredsum.vs` — resolved (Spike validates Sail; was typo in unsupported list)

- **Status**: resolved
- **Date tested**: 2026-04-08
- **Instruction**: `vwredsum.vs` (in `Vx-save.csv`)

The `unsupported_tests` entry had a typo: `vwredusum.vs` instead of `vwredsum.vs`.
Because of the typo, the entry had no effect. Testing the correct instruction via Spike:
all 6 tests PASS (3 RV64 + 3 RV32). Sail and Spike agree. Removed from `unsupported_tests`.

#### Reproduction

```bash
python3 isolate_coverpoint.py Vx --tests vwredsum.vs
make clean && make vector-tests
CONFIG_FILES="config/spike/spike-rv64-max/test_config.yaml config/spike/spike-rv32-max/test_config.yaml" \
  EXTENSIONS=Vx8,Vx16,Vx32,Vx64 make elfs
./run_tests.py "$(cat config/spike/spike-rv64-max/run_cmd.txt)" work/spike-rv64-max/elfs
./run_tests.py "$(cat config/spike/spike-rv32-max/run_cmd.txt)" work/spike-rv32-max/elfs
# Result: All 3 RV64 + 3 RV32 = 6 tests PASS
python3 isolate_coverpoint.py --restore Vx
```

---

### How to validate suspected Sail bugs via Spike

**Important**: Comparing `.sig` vs `.results` files is circular — both come from Sail.
The authoritative test is running self-checking ELFs on Spike via `run_tests.py`.

```bash
# 1. Comment out the instruction in unsupported_tests in vector-testgen-unpriv.py
# 2. Isolate (check CSV with: grep -rl '<instr>' working-testplans/duplicates/)
python3 isolate_coverpoint.py <CSV> --tests <instr1> <instr2>
# 3. Build spike ELFs
make clean && make vector-tests
CONFIG_FILES="config/spike/spike-rv64-max/test_config.yaml config/spike/spike-rv32-max/test_config.yaml" \
  EXTENSIONS=<ext8>,<ext16>,<ext32>,<ext64> make elfs
# 4. Run Spike
./run_tests.py "$(cat config/spike/spike-rv64-max/run_cmd.txt)" work/spike-rv64-max/elfs
./run_tests.py "$(cat config/spike/spike-rv32-max/run_cmd.txt)" work/spike-rv32-max/elfs
# 5. Interpret: PASS = Sail and Spike agree. FAIL = they disagree (one has a bug).
# 6. Restore
python3 isolate_coverpoint.py --restore <CSV>
```

---

## Coverage Summary (as of 2026-04-08)

### RV64 VlsCustom

- **Custom bin coverage: 100%**
- All ZERO covergroups are residual (cp_asm_count/std_vec only, no custom bins)

### RV32 VlsCustom

- **Custom bin coverage: 100% excluding ei64 (Sail bug #7)**
- ei64 indexed LS instructions are guarded by `MAXINDEXEEW=32` to avoid Sail hang
- All other ZERO covergroups are residual
