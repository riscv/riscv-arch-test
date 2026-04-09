# Debugging Sail Hangs

**Read this guide when a test hangs during the build/sim phase.**

## Timing Reference

| What                          | Expected   | Hard max |
| ----------------------------- | ---------- | -------- |
| Single Sail simulation        | ~5 seconds | 20s      |
| Isolated coverpoint coverage  | < 30s      | 60s      |
| Full custom suite (e.g. Vls)  | ~10 min    | 5 min timeout while iterating |

## First Instinct: Assume It's a Hang

A single Sail sim typically finishes in ~5 seconds; the longest should never exceed 20 seconds. If it's been more than ~10 seconds on one file, it is almost certainly hanging. **Do not wait** — find the ELF (Step 1) and run it manually with graduated `--inst-limit` values (Step 2). If Sail consistently runs to the instruction limit, it's an infinite loop.

## Coverage Saves Progress

Completed `.sig` files persist between runs. A timed-out run loses nothing — just fix the hang and re-run. **Do NOT `make clean` while iterating on a hang** — you'll discard all saved progress.

**Only run `make clean` once you believe the hang is fixed**, to do a full clean run and verify a consistently-compiled test suite passes end-to-end.

## Sail Binary & Location

- Binary: `/opt/riscv/bin/sail_riscv_sim`
- Config reference: `config/sail/sail-rv64-max/test_config.yaml` (field `ref_model_exe`)

## Step 1: Find the ELF

Hanging tests show in build output like:

```
oldest: .../work/sail-rv64-max/build/rv64i/Vf16/Vf16-vfmv.s.f.sig
```

The ELF is at that path with `.elf` appended. The partial log is at that path with `.log` appended.

## Step 2: Run with Instruction Trace and Limit

```bash
timeout 30 /opt/riscv/bin/sail_riscv_sim \
  --inst-limit 50000 \
  --trace-instr \
  --test-signature /dev/null \
  <path-to-elf>
```

- `--inst-limit 50000` prevents infinite loops (raise if needed)
- `--trace-instr` prints every executed instruction with address and disassembly
- `--test-signature /dev/null` is required (sail expects it)
- `timeout 30` as a safety net

The last few lines of output show exactly where the hang occurs. Look for:

- `illegal 0x...` — an illegal instruction causing a trap loop
- A repeating sequence of addresses — an infinite loop in trap handler
- A specific instruction that sail can't complete

## Step 3: Programmatically Check for Traps

Before reading the full trace, grep for `mcause` writes to instantly detect traps:

```bash
timeout 120 /opt/riscv/bin/sail_riscv_sim \
  --inst-limit 500000 \
  --trace-instr --trace-reg \
  --test-signature /dev/null \
  <path-to-elf> 2>&1 | grep -B5 "mcause"
```

The `-B5` context lines show the faulting instruction and its test label. See "Common Hang Causes" below for `mcause` value meanings (2 = illegal instruction is the most common).

## Step 4: Add Register Trace if Needed

```bash
timeout 30 /opt/riscv/bin/sail_riscv_sim \
  --inst-limit 500 \
  --trace-instr --trace-reg \
  --test-signature /dev/null \
  <path-to-elf>
```

- `--trace-reg` shows register reads/writes (very verbose, use smaller inst-limit)
- Useful for checking vtype/vl state: grep for `vtype` or `vl` in output

## Step 5: Read the Source Assembly and Identify the Coverpoint

Open the source `.S` file at `tests/rv64i/<Extension>/<filename>.S` (not in `work/`). Each test section has a comment like:

```asm
# Testcase cp_custom_ffLS_update_vl (vle16ff.v, lmul=2, vl=vlmax, masked)
```

Find the section containing the failing instruction address and read the full assembly for that testcase. The comment names the `cp_custom_*` script that generated it.

## Step 6: Diagnose from the Assembly First

Understand the problem from the assembly before reading any Python. The assembly shows exactly what instructions execute and in what order. Common things to check:

- Is a vector register misaligned for the current LMUL? (e.g. `vid.v v1` with LMUL=2)
- Is vtype valid after the most recent `vsetvli`?
- Is the failing instruction part of the test itself or part of scaffolding (mask setup, operand loads)?

If the issue is in scaffolding (mask preamble, register loads), the fix likely belongs in `vector_testgen_common.py`. If it's in the test instruction itself, the fix belongs in the `cp_custom_*.py` script named in the comment.

Only read `vector_testgen_common.py` after you understand the assembly-level problem and know which function to target.

## Step 7: Cross-reference with objdump if Needed

Use `objdump` to correlate addresses back to test labels:

```bash
riscv64-unknown-elf-objdump -d <path-to-elf> | grep -A2 -B2 "<address>"
```

## Other Useful Sail Flags

| Flag                     | Purpose                                         |
| ------------------------ | ----------------------------------------------- |
| `--trace-mem`            | Trace memory accesses                           |
| `--trace-ptw`            | Trace page table walks                          |
| `--trace-rvfi`           | RVFI trace output                               |
| `--trace-output <file>`  | Write trace to file instead of stdout           |
| `--print-isa-string`     | Print supported ISA string                      |
| `--print-default-config` | Print full default config (includes VLEN, ELEN) |
| `--config <file>`        | Use specific config file                        |

## Common Hang Causes

### 1. Illegal vtype (vill bit set)

If `vsetvli` or `vsetvl` produces `vtype = 0x8000000000000000` (RV64) or `0x80000000` (RV32), the **vill** bit is set. All subsequent vector instructions become illegal, causing a trap loop.

**Diagnosis**: In `--trace-reg` output, look for `CSR vtype <- 0x80000000...`. This means the SEW/LMUL combination is unsupported.

**Common trigger**: Fractional LMUL values (mf8, mf4, mf2) where `VLMAX = VLEN * LMUL / SEW < 1`, or configurations the sail model doesn't support.

**Fix**: Either guard the code with appropriate `#ifdef` checks, or avoid the unsupported SEW/LMUL combination in the test generator.

### 2. No trap handler

The test framework doesn't install trap handlers. Any exception (illegal instruction, misaligned access, etc.) causes an infinite loop at the default trap vector.

### 3. LMUL-misaligned vector register in scaffolding (fixed)

`prepMaskV()` used `vid.v v1` regardless of LMUL — illegal when LMUL>=2. Fixed: now uses LMUL-aligned temp register. Diagnosis: `mcause <- 0x2` after `vid.v` on odd register with LMUL>1.

### 4. vmv.v.i before vsetvli (fixed)

Mask init emitted before `vsetvli` — hung when `vtype.vill=1` after reset. Fixed: now emits after `prepBaseV`. See `knowledge-archive.md` for details.

## Sail Model Configuration

- Default VLEN: 256 bits (`vlen_exp: 8` in config)
- Default ELEN: 64 bits (`elen_exp: 6` in config)
- VLMAX = VLEN \* LMUL / SEW (must be >= 1 for valid vtype)
