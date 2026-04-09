# GUIDE.md — Coverpoint Template Reference

All coverpoint templates live in this directory (`generators/coverage/templates/`). This guide covers file naming, format rules, copy-paste patterns, and the `ins` object API. This is the single source of truth — do not duplicate this content elsewhere.

## File Naming

- **One coverpoint per file** — every template file contains exactly one coverpoint
- **Filename**: Matches the coverpoint name exactly (e.g., `cp_custom_vfp_flags_set.sv`, `cp_vstart_gt_vl.sv`)
- Each file is completely independent — define any helpers it needs inline

## Template Format Rules

1. **NO COVERGROUP WRAPPER** — Never write `covergroup ... endgroup`. Files are pasted into an existing covergroup.
2. **Header**: `//` line (~80 chars), `// cp_name`, `//` line. First `//` starts at column 0.
3. **Footer**: `//// end cp_name` + slashes to ~80 chars
4. **Indentation**: 4 spaces for coverpoints, 8 spaces for bins
5. **No unused coverpoints**: Every helper MUST appear in at least one cross. Review after writing.
6. **No unfillable custom bins**: Every custom bin MUST be reachable by tests. If a bin can never be hit, delete it. Custom bins must reach **100% coverage**. Residual 0% on framework-generated bins (not defined in the template) is acceptable — those are filled by the full suite.
7. **One blank line** at end of file
8. **Comments**: Maximum 1 line. Readers have the CSV already.

### Non-Custom Template

```systemverilog
//////////////////////////////////////////////////////////////////////////////////
    // cp_example_name
    //////////////////////////////////////////////////////////////////////////////////

    cp_example_name: coverpoint (condition1 &
                                 condition2 &
                                 condition3) {
        bins true = {1};
    }

    //// end cp_example_name////////////////////////////////////////////////
```

### Custom Template (with crosses)

```systemverilog
//////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vexample
    //////////////////////////////////////////////////////////////////////////////////

    std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        ins.trap == 0
                    }
    {
        bins true = {1'b1};
    }

    vtype_lmul_4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins four = {2};
    }

    vd_aligned_lmul_4: coverpoint ins.current.insn[11:7] {
        wildcard bins divisible_by_4 = {5'b???00};
    }

    cp_custom_vexample_lmul4: cross std_vec, vtype_lmul_4, vd_aligned_lmul_4;

    //// end cp_custom_vexample////////////////////////////////////////////////
```

## Template Replacement Keywords

| Keyword      | Replaced With                                  |
| ------------ | ---------------------------------------------- |
| `INSTR`      | instruction mnemonic (e.g., `vfredosum.vs`)    |
| `INSTRNODOT` | mnemonic with `.` → `_` (e.g., `vfredosum_vs`) |
| `ARCH`       | extension lowercase (e.g., `vx64`)             |
| `EFFEW`      | vector element width (e.g., `16`, `32`)        |

## Allowed Bin Syntax

```systemverilog
bins name = {value};                          // Single value
bins name = {[start:end]};                    // Range
bins name[] = {[start:end]};                  // One bin per value
wildcard bins name = {5'b???00};              // Wildcard pattern
wildcard bins name = (before => after);       // Transition
ignore_bins name = {value};                   // Exclude
wildcard ignore_bins name = {5'b???00};       // Exclude wildcard
```

## Copy-Paste Patterns

### Standard Vector Conditions (std_vec)

```systemverilog
    std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        ins.trap == 0
                    }
    {
        bins true = {1'b1};
    }
```

### LMUL Coverpoints (vlmul: mf8=5, mf4=6, mf2=7, m1=0, m2=1, m4=2, m8=3)

```systemverilog
    // Single LMUL
    vtype_lmul_1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one = {0};
    }
    vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }
    vtype_lmul_4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins four = {2};
    }
    vtype_lmul_8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins eight = {3};
    }

    // All integer LMULs (no guards needed — always supported)
    vtype_all_lmulge1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one = {0}; bins two = {1}; bins four = {2}; bins eight = {3};
    }

    // All LMULs including fractional (REQUIRED when covering fractional — DUT-optional)
    // NOTE: For FP instructions (SEW >= 16), fractional LMULs must satisfy LMUL >= SEW/ELEN.
    // Gate fractional bins with COVER_VFCUSTOM* defines (aliases defined in header_vector.sv,
    // still valid after VfCustom merge into Vf): mf8 never valid for FP,
    // mf4 only at SEW=16 (COVER_VFCUSTOM16), mf2 not at SEW=64 (ifndef COVER_VFCUSTOM64).
    vtype_all_lmul: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        `ifdef LMULf8_SUPPORTED
            bins eighth  = {5};
        `endif
        `ifdef LMULf4_SUPPORTED
            bins fourth = {6};
        `endif
        `ifdef LMULf2_SUPPORTED
            bins half   = {7};
        `endif
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }
```

### SEW Coverpoints (vsew: e8=0, e16=1, e32=2, e64=3)

```systemverilog
    // Single SEW
    vtype_sew_8:  coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") { bins e8  = {0}; }
    vtype_sew_16: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") { bins e16 = {1}; }
    vtype_sew_32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") { bins e32 = {2}; }
    vtype_sew_64: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") { bins e64 = {3}; }

    // All SEW values (REQUIRED when covering all SEW — guard fractional support)
    vtype_all_sew: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        `ifdef SEW8_SUPPORTED
            bins e8  = {0};
        `endif
        `ifdef SEW16_SUPPORTED
            bins e16 = {1};
        `endif
        `ifdef SEW32_SUPPORTED
            bins e32 = {2};
        `endif
        `ifdef SEW64_SUPPORTED
            bins e64 = {3};
        `endif
    }
```

### Register Bit Fields (vd[11:7], vs1[19:15], vs2[24:20], vm[25])

```systemverilog
    vd_v0:        coverpoint ins.current.insn[11:7] { bins zero   = {5'b00000}; }
    vd_not_v0:    coverpoint ins.current.insn[11:7] { bins not_v0[] = {[1:31]}; }
    vs2_v0:       coverpoint ins.current.insn[24:20] { bins v0    = {5'b00000}; }
    mask_enabled: coverpoint ins.current.insn[25]   { bins masked = {1'b0}; }
```

### Register Alignment for LMUL

```systemverilog
    vd_aligned_lmul_2: coverpoint ins.current.insn[11:7] { wildcard bins div2 = {5'b????0}; }
    vd_aligned_lmul_4: coverpoint ins.current.insn[11:7] { wildcard bins div4 = {5'b???00}; }
    vd_aligned_lmul_8: coverpoint ins.current.insn[11:7] { wildcard bins div8 = {5'b??000}; }

    // NOT aligned (off-group)
    wildcard ignore_bins divisible_by_4 = {5'b???00};  // use inside a coverpoint
```

### VL at VLMAX

```systemverilog
    vl_max: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")
                        == get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)) {
        bins target = {1'b1};
    }
```

### VL Zero

```systemverilog
    vl_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        bins zero = {0};
    }
```

### vstart >= vl

```systemverilog
    vstart_ge_vl: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") >=
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")) {
        bins true = {1'b1};
    }
```

### Trap Occurred

```systemverilog
    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }
```

### Valid vtype (vill=0)

```systemverilog
    vtype_valid: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
        bins valid = {1'b0};
    }
```

### FRM (Floating-Point Rounding Mode)

```systemverilog
    frm_valid: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "frm") {
        bins rne = {3'b000};
        bins rtz = {3'b001};
        bins rdn = {3'b010};
        bins rup = {3'b011};
        bins rmm = {3'b100};
    }
    frm_invalid: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "frm") {
        bins reserved_5 = {3'b101};
        bins reserved_6 = {3'b110};
        bins reserved_7 = {3'b111};
    }
```

### mstatus.vs Active

```systemverilog
    mstatus_vs_active: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins active[] = {[1:3]};
    }
```

### Widening Overlap Detection

```systemverilog
    // vd[4:1] == vs2[4:1] (LMUL=1, 2-register widened group)
    vs2_vd_overlap_lmul1: coverpoint (ins.current.insn[24:21] == ins.current.insn[11:8]) {
        bins overlapping = {1'b1};
    }
    // vd[4:2] == vs2[4:2] (LMUL=2, 4-register widened group)
    vs2_vd_overlap_lmul2: coverpoint (ins.current.insn[24:22] == ins.current.insn[11:9]) {
        bins overlapping = {1'b1};
    }
    // vd[4:3] == vs2[4:3] (LMUL=4, 8-register widened group)
    vs2_vd_overlap_lmul4: coverpoint (ins.current.insn[24:23] == ins.current.insn[11:10]) {
        bins overlapping = {1'b1};
    }
```

### Compound Coverpoints (multi-field bins)

```systemverilog
    my_compound_cp : {coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                      coverpoint ins.current.insn[31:29]} {
        bins combo1 = {3'b011, 3'b001};  // vlmul=8, nf=1
        bins combo2 = {3'b010, 3'b011};  // vlmul=4, nf=3
    }
```

### EMUL Computation for Load/Store (3-field compound)

Width field (bits 14:12) encodes EEW: 000=8, 101=16, 110=32, 111=64.

```systemverilog
    emul_8_ls : {coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")[2:0],
                 coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")[1:0],
                 coverpoint ins.current.insn[14:12]} {
        bins m8_sew8_eew8  = {3'b011, 2'b00, 3'b000};  // EEW=SEW, LMUL=8
        bins m4_sew8_eew16 = {3'b010, 2'b00, 3'b101};  // EEW=2*SEW, LMUL=4
    }
```

### XLEN / SEW Conditionals

```systemverilog
    `ifdef XLEN32
        bins val32 = {32'hFFFFFFFF};
    `endif
    `ifdef XLEN64
        bins val64 = {64'hFFFFFFFFFFFFFFFF};
    `endif
    `ifdef SEW64_SUPPORTED
        // SEW=64 specific bins
    `endif

    // D extension guard
    `ifndef D_COVERAGE
        // bins for SEW=64 being unsupported for FP
    `endif
```

### SEW-Specific Bin Values (COVER_VFCUSTOM guards)

When bins need different values per SEW (e.g., NaN encodings at different FP widths), use
`ifdef COVER_VFCUSTOMxx` guards. VfCustom is now merged into Vf (like VxCustom is part of Vx),
but the `COVER_VFCUSTOM*` macros are still defined as aliases in `header_vector.sv`, so existing
templates using them continue to work. Each generated coverage file (`Vf16_coverage.svh`, etc.)
defines both `COVER_VFxx` and `COVER_VFCUSTOMxx`. Sibling macros are automatically `undef`'d by
`generate.py` at the top of each file, so only one SEW variant is active at compile time. Both
`ifdef`/`endif` chains and `ifdef`/`elsif`/`endif` chains are safe.

```systemverilog
    vs2_element0 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val) {
        `ifdef COVER_VFCUSTOM16
            bins val = {64'h0000_0000_0000_7E00}; // half
        `endif
        `ifdef COVER_VFCUSTOM32
            bins val = {64'h0000_0000_7FC0_0000}; // single
        `endif
        `ifdef COVER_VFCUSTOM64
            bins val = {64'h7FF8_0000_0000_0000}; // double
        `endif
    }
```

**Important**: The `undef` logic lives in `generate.py` (`_get_sibling_sew_macros`). If a new
vector category with SEW variants is added, it is handled automatically. Do NOT manually add
`define`/`undef` in templates — `generate.py` handles this.

### SEW64 FP — Excluding Custom Bins

SEW=64 FP instructions require FLEN ≥ 64 (D extension). Systems without D extension cannot
execute SEW=64 FP instructions, so the covergroup shell (`cp_asm_count`, `std_vec`) will
always be 0% — this is **expected and acceptable**. However, custom bins in templates must
be excluded so they don't create unfillable coverage holes. Use `ifndef COVER_VFCUSTOM64`
(alias still valid after VfCustom→Vf merge) / `else` / `ifdef FLEN64`:

```systemverilog
`ifndef COVER_VFCUSTOM64
    // SEW16/SEW32 — always include
    my_cp : coverpoint (...) { bins target = {1}; }
    cp_custom_foo : cross std_vec, my_cp;
`else
    `ifdef FLEN64
    // SEW64 — only when FLEN >= 64 (D extension)
    my_cp : coverpoint (...) { bins target = {1}; }
    cp_custom_foo : cross std_vec, my_cp;
    `endif
`endif
```

When reviewing coverage and Vf64 shows custom bins at 0% on a system without D
extension, wrap them with this pattern. The residual `cp_asm_count`/`std_vec` at 0% is
fine — they are framework-generated and cannot be guarded from the template.

### GPR Value Access

```systemverilog
    ins.current.rs1_val  // Value of rs1 GPR
    ins.current.rs2_val  // Value of rs2 GPR
```

## ins Object Reference

### Direct Fields

| Field         | Type   | Description              |
| ------------- | ------ | ------------------------ |
| `ins.trap`    | bit    | 1 if instruction trapped |
| `ins.hart`    | int    | Hart ID                  |
| `ins.issue`   | int    | Issue number             |
| `ins.ins_str` | string | Instruction mnemonic     |

### ins.current Fields

**Instruction bits**: `ins.current.insn[31:0]`

| Bits    | Field         |
| ------- | ------------- |
| [6:0]   | opcode        |
| [11:7]  | rd/vd         |
| [14:12] | funct3        |
| [19:15] | rs1/vs1       |
| [24:20] | rs2/vs2       |
| [25]    | vm (0=masked) |
| [31:25] | funct7        |

**Register values**:

- `ins.current.rd_val`, `ins.current.rd_val_pre`
- `ins.current.rs1_val`, `ins.current.rs2_val`
- `ins.current.fd_val`, `ins.current.fs1_val`, `ins.current.fs2_val`
- `ins.current.vd_val`, `ins.current.vs1_val`, `ins.current.vs2_val`
- `ins.current.v0_val` — mask register

**Vector state**:

- `ins.current.vm` — 1=unmasked, 0=masked
- `ins.current.eSEW` — 0=e8, 1=e16, 2=e32, 3=e64
- `ins.current.mLMUL` — 5=mf8, 6=mf4, 7=mf2, 0=m1, 1=m2, 2=m4, 3=m8
- `ins.current.ta`, `ins.current.ma` — tail/mask agnostic

**Other**:

- `ins.current.imm` — immediate value
- `ins.current.mode` — 0=User, 1=Supervisor, 3=Machine
- `ins.current.mem_addr` — calculated memory address

### ins.prev Fields

Pre-instruction state. Same structure as `ins.current`.

- `ins.prev.x_wdata[idx]` — GPR values before instruction
- `ins.prev.f_wdata[idx]` — FPR values before instruction

## Global Helper Functions

### Sampling Constants

```systemverilog
`SAMPLE_BEFORE   // (1) state before instruction
`SAMPLE_AFTER    // (0) state after instruction
```

### CSR Access

```systemverilog
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill")    // vill bit
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")   // LMUL field
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")    // SEW field
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")         // vector length
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") // vstart
get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER,  "fcsr", "fflags")   // FP flags after
get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "frm")      // rounding mode
```

**Note**: `fsflagsi` writes CSR 001 (fflags) but NOT CSR 003 (fcsr). Use `get_csr_val("fcsr", "fflags")` carefully after `fsflagsi` — may read stale value. See `claude-scripts/knowledge.md`.

### Register Number Conversion

```systemverilog
get_vr_num("v1")     // returns 1
get_gpr_num("x1")    // returns 1  (also handles ABI names like "ra")
get_fpr_num("f1")    // returns 1
```

### Vector Helpers

```systemverilog
get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)  // element 0 at current SEW
get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)           // VLMAX value
vs_edges_check(ins.hart, ins.issue, val, sew_multiplier)       // edge case check
```

### Register Lookup

```systemverilog
ins.get_gpr_reg(ins.current.rd)   // gpr_name_t
ins.get_fpr_reg(ins.current.fs1)  // fpr_name_t
ins.get_vr_reg(ins.current.vs1)   // vr_name_t
ins.get_gpr_val(ins.hart, ins.issue, "x1", `SAMPLE_BEFORE)
ins.get_vr_val(ins.hart, ins.issue, "v1", `SAMPLE_BEFORE)
```

## Self-Maintenance Rule

Whenever you add a new pattern, fix a bug in a template, or discover a new API call, add it to this file before finishing. This is the single source of truth — the next Claude will read this file and must not repeat your mistakes.
