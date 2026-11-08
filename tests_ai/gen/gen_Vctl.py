#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate the vector control rule-derived tests: tests_ai/V (programmer's model, vtype/vl/vstart/vxrm/vxsat/vcsr/
vlenb, mstatus.VS, vset*, element mapping, masking and tail/mask policies, prestart/body/tail elements, vector
exception handling, element groups, and the V/Zve* subset rules).

Rules are the norm: tags in src/unpriv/vector-common.adoc (sections up to Vector Instruction Formats, the arithmetic
format rules, Exception Handling and Vector Element Groups), src/unpriv/v-st-ext.adoc, src/unpriv/zve*.adoc, and the
mstatus.VS rules of src/priv/machine.adoc not already tested by tests_ai/Sm. VLEN, ELEN and the supported vtypes are
implementation parameters: tests read vlenb and compute VLMAX at run time; ELEN >= 64 comes from Zve64x.

Usage: gen_Vctl.py [rule ...]   (default: every rule)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
import hmem
from aigen import TestFile, X, sext
from vctllib import (
    BUF,
    BUF2,
    CSR,
    E64,
    ILLEGAL,
    ISSUE,
    LMUL_CODE,
    LOAD_PF,
    MAC,
    MARCH,
    MARCH_D,
    MARCH_V,
    STORE_PF,
    VC,
    VILL,
    VS_CLEAN,
    VS_DIRTY,
    VS_INIT,
    VS_MASK,
    VS_OFF,
    VST,
    ZVE32X,
    VTest,
    check_agn,
    csr_forms,
    fill,
    iota,
    ld_elem,
    read_vs,
    set_mvs,
    set_vs,
    store,
    vlmax,
    vset,
    vset_max,
    vt,
    vtypei,
    vwin,
)

if TYPE_CHECKING:
    from collections.abc import Callable

SUITE = "Vctl"
NO_ALTFMT = "!defined(ZVFBFA_SUPPORTED)"  # Zvfbfa defines vtype bit 8 (altfmt)
MUT = os.environ.get("AI_MUTANT", "")

MUTANTS = {
    "vtype_writable": "vtype accepts CSR writes (no illegal-instruction trap)",
    "vl_writable": "vl accepts CSR writes",
    "vlenb_bits": "vlenb holds VLEN in bits",
    "vlenb_writable": "vlenb accepts CSR writes",
    "vtype_changed_by_vadd": "a vector arithmetic instruction rewrites vtype (vta cleared)",
    "vl_changed_by_load": "a vector load sets vl to VLMAX",
    "vstart_rmw_wrong": "csrrs on vstart writes rs1 instead of old | rs1",
    "vstart_full_width": "vstart keeps every written bit",
    "vstart_one_bit_short": "vstart has one writable bit fewer than log2(VLEN)",
    "vstart_not_reset": "vstart is not reset to 0 after a vector instruction",
    "vset_keeps_vstart": "vset* leave vstart unchanged",
    "vset_vstart_traps": "vset* raise illegal-instruction when vstart != 0",
    "vxrm_3bits": "vxrm keeps bit 2",
    "vcsr_vxrm_low": "vcsr holds vxrm in bits 1:0",
    "vcsr_vxsat_bit3": "vcsr holds vxsat in bit 3",
    "vxsat_not_set": "a saturating instruction does not set vxsat",
    "vxsat_set_always": "any fixed-point instruction sets vxsat",
    "rne_as_rnu": "vxrm=1 (rne) rounds half up",
    "rod_as_rdn": "vxrm=3 (rod) truncates",
    "vset_rd_avl": "vset* write the AVL, not vl, to rd",
    "vsetvl_imm_vtype": "vsetvl ignores rs2 and decodes vtype from the instruction bits",
    "vtype_vta_vma_swapped": "vta and vma are swapped in vtype",
    "avl_signed": "AVL is signed (AVL = -1 gives vl = 0)",
    "avl_32bit": "AVL is truncated to 32 bits on RV64",
    "rs1x0_keeps_vl": "rs1=x0, rd!=x0 keeps the old vl",
    "keep_vl_uses_vlmax": "rs1=x0, rd=x0 sets vl = VLMAX",
    "vsetivli_sext": "vsetivli sign-extends its 5-bit AVL",
    "vl_no_clamp": "vl = AVL when VLMAX < AVL < 2*VLMAX",
    "vl_old_vlmax": "vl is bounded by the previous VLMAX",
    "vill_keeps_vtype": "an unsupported vtype keeps its other bits with vill",
    "vill_keeps_vl": "an unsupported vtype leaves vl unchanged",
    "reserved_bits_ignored": "reserved vtype bits are ignored (vill = 0)",
    "vill_bit_ignored": "a vsetvl rs2 with vill set but otherwise valid is accepted",
    "e64_on_v_unsupported": "V sets vill for SEW=64",
    "vill_whole_reg_traps": "whole-register loads/stores trap when vill is set",
    "vill_vadd_ok": "vadd executes when vill is set",
    "vsew_ignored": "VLMAX ignores SEW (VLEN/8 at every SEW)",
    "lmul_unsigned": "vlmul is decoded unsigned (codes 5-7 act as LMUL 8)",
    "frac_lmul_unsupported": "fractional LMUL 1/2 sets vill",
    "tail_ones_under_tu": "tu tail elements are overwritten with 1s",
    "inactive_ones_under_mu": "mu inactive elements are overwritten with 1s",
    "agnostic_zero": "agnostic elements are written with 0",
    "mask_tail_zeroed": "mask-result tail bits are cleared",
    "vlm_tail_loaded": "vlm.v writes loaded bytes past ceil(vl/8)",
    "flmul_tail_written": "with LMUL<1 the rest of the register is written with the result pattern",
    "mask_from_v1": "the mask is read from v1 instead of v0",
    "vm_inverted": "vm=1 masks the instruction",
    "prestart_updated": "elements below vstart are updated",
    "vstart_ge_vl_tail_ones": "vstart >= vl still writes agnostic 1s to the tail",
    "vl0_scalar_skip": "vmv.x.s does not write rd when vl = 0",
    "vstart_not_recorded": "a fault at element k leaves vstart = 0",
    "precise_younger_ran": "the instruction after a faulting vector load executes before the trap",
    "precise_store_lost": "elements before the faulting one of a vector store are not written",
    "inactive_faults": "a masked-off element that would fault raises a page fault",
    "tail_faults": "a tail element that would fault raises a page fault",
    "prestart_faults": "a prestart element that would fault raises a page fault",
    "active_no_fault": "an active element in an invalid page does not fault",
    "vstart_cleared_on_illegal": "an illegal-instruction trap clears vstart",
    "vs_off_csr_ok": "vector CSRs are accessible with VS=Off",
    "vs_off_vset_ok": "vset* execute with VS=Off",
    "vs_clean_stays": "changing vector state with VS=Clean leaves VS=Clean",
    "vs_initial_stays": "changing vector state with VS=Initial leaves VS=Initial",
    "sd_ignores_vs": "SD ignores VS (SD = 0 with VS=Dirty and FS=Off)",
    "sstatus_vs_independent": "sstatus.VS is a separate field from mstatus.VS",
    "vreg_count_16": "only 16 vector registers (v16-v31 alias v0-v15)",
    "mask_spans_group": "a mask result at LMUL=8 also writes the next register",
    "mask_bit_per_byte": "mask bit for element i is bit 8*i",
    "widen_dest_one_reg": "a widening result wraps within one register (EMUL=LMUL)",
    "narrow_vs1_wide": "the narrowing vs1 operand is read with EEW=2*SEW",
    "pack_msb_first": "LMUL=1 elements are packed from the most-significant end",
    "group_interleaved": "register-group elements alternate between the registers",
    "scalar_needs_group": "a scalar operand in an odd register at LMUL=8 is read from the group base",
    "overlap_result_in_tail": "with overlapping EEWs the tail receives computed values",
    "vmulh_e64_illegal": "V traps vmulh at SEW=64 (Zve64x subset only)",
    "vsmul_e64_illegal": "V traps vsmul at SEW=64",
    "vlenb_lt_16": "V allows VLEN = 64",
    "egs_any_vl": "with element groups, vl for VLMAX < AVL < 2*VLMAX may be any value in range (vl=AVL-1 accepted)",
    "vector_misa_v_clear": "misa.V reads 0 with V",
}


def mut(name: str) -> bool:
    assert name in MUTANTS, name
    return name == MUT


def out() -> str:
    return "V" if SUITE == "Vctl" else SUITE


def new(rule: str, **kw: object) -> VTest:
    return VTest(out(), rule, **kw)


def snew(rule: str, **kw: object) -> VTest:
    """An S-mode test (boot S)."""
    kw.setdefault("boot", "S")
    kw.setdefault("required", ["I", "S", "Zve32x"])
    return VTest(out(), rule, **kw)


def mnew(rule: str, **kw: object) -> VTest:
    """The M-mode part of a rule (<rule>_Sm.S)."""
    kw.setdefault("boot", "M")
    kw.setdefault("required", ["I", "Sm", "Zve32x"])
    kw.setdefault("suffix", "_Sm")
    return VTest(out(), rule, **kw)


ALL: dict[str, Callable[[], list[TestFile]]] = {}


def rule(fn: Callable[[], list[TestFile] | TestFile]) -> Callable[[], list[TestFile]]:
    def wrap() -> list[TestFile]:
        r = fn()
        return r if isinstance(r, list) else [r]

    ALL[fn.__name__.removeprefix("g_")] = wrap
    return wrap


def eq_reg(t: TestFile, a: str, b: str, lab: str, desc: str, tmp: str = "x9") -> None:
    """Check a == b (registers) as a == b -> tmp = 0."""
    t.emit(f"sub {tmp}, {a}, {b}")
    t.check(tmp, 0, lab, desc + " (difference must be 0)")


def mark(t: TestFile) -> str:
    lab = t.label("c")
    t.emit(f"{lab}:", 0)
    return lab


# ======================================================================== CSRs
def ro_csr(
    rule_name: str,
    csr: str,
    text: str,
    ctx: str,
    plan: str,
    setup: Callable[[TestFile], None],
    value: Callable[[TestFile, str], None],
    mutant: str,
) -> TestFile:
    """A read-only vector CSR: every write form raises illegal instruction; read forms return the value; the value
    is unchanged afterwards. value(t, reg) puts the expected value in reg."""
    t = new(rule_name)
    t.describe(rule_text=text, source=VC, context=ctx, plan=plan)
    setup(t)
    t.li("x6", 0x55)
    for asm, _num, kind, writes in csr_forms(csr):
        exp = ILLEGAL if writes and not mut(mutant) else "ok"
        lab = vwin(t, [asm], exp, f"{kind} of {csr}")
        if not writes:
            value(t, "x8")
            eq_reg(t, "x7", "x8", lab, f"{kind} of {csr} returns its value")
    lab = mark(t)
    t.emit(f"csrr x7, {csr}")
    value(t, "x8")
    eq_reg(t, "x7", "x8", lab, f"{csr} is unchanged by the trapping writes")
    return t


@rule
def g_vtype_sz_acc_op() -> TestFile:
    vti = vtypei(16, "m2", 1, 0)

    def setup(t: TestFile) -> None:
        t.comment(f"vtype = e16, m2, ta, mu ({hex(vti)}), vl = 3")
        vset(t, "x0", 3, 16, "m2", 1, 0)

    def value(t: TestFile, reg: str) -> None:
        t.li(reg, vti)

    t = ro_csr(
        "vtype_sz_acc_op",
        "vtype",
        "The read-only XLEN-wide vector type CSR, vtype provides the default type used to interpret the contents of "
        "the vector register file, and can only be updated by vsetvli, vsetivli, and vsetvl instructions.",
        "Zicsr: a CSR instruction that would write a read-only CSR raises illegal-instruction; csrrs/csrrc with "
        "rs1=x0 and csrrsi/csrrci with uimm=0 only read. xtval of the trap is 0 or the instruction bits.",
        "1. vtype = e16, m2, ta, mu by vsetivli. The eight CSR instruction forms on vtype: the six that write raise "
        "illegal-instruction; the two reads return the vsetivli value, which is unchanged afterwards.\n"
        "2. Instructions other than vset* leave vtype alone: vadd.vv, vle8.v, vse8.v, vmv.x.s, csrw vstart, csrwi vxrm "
        "and csrwi vcsr; vtype still reads e16, m2, ta, mu. vsetivli then changes it (e8, m1, tu, ma).",
        setup,
        value,
        "vtype_writable",
    )
    t.comment("2. other vector instructions and vector CSR writes do not update vtype")
    t.la("x6", BUF)
    for ln in [
        "vadd.vv v2, v4, v6",
        "vle8.v v1, (x6)",
        "vse8.v v1, (x6)",
        "vmv.x.s x7, v2",
        "csrw vstart, x0",
        "csrwi vxrm, 2",
        "csrwi vcsr, 0",
    ]:
        t.emit(ln)
    lab = mark(t)
    t.emit("csrr x7, vtype")
    t.check(
        "x7",
        vti if not mut("vtype_changed_by_vadd") else vti & ~0x40,
        lab,
        "vtype after vadd/vle8/vse8/vmv.x.s/vector CSR writes",
    )
    vset(t, "x0", 1, 8, "m1", 0, 1)
    lab = mark(t)
    t.emit("csrr x7, vtype")
    t.check("x7", vtypei(8, "m1", 0, 1), lab, "vsetivli e8, m1, tu, ma updates vtype")
    return t


@rule
def g_vl_acc() -> TestFile:
    def setup(t: TestFile) -> None:
        t.comment("vtype = e8, m1, vl = 3")
        vset(t, "x0", 3, 8, "m1")

    def value(t: TestFile, reg: str) -> None:
        t.li(reg, 3)

    t = ro_csr(
        "vl_acc",
        "vl",
        "The XLEN-bit-wide read-only vl CSR can only be updated by the vset* instructions, and the fault-only-first "
        "vector load instruction variants.",
        "Zicsr: a CSR instruction that would write a read-only CSR raises illegal-instruction. Fault-only-first loads "
        "belong to the vector memory tests.",
        "1. vl = 3 by vsetivli. The eight CSR instruction forms on vl: the six that write raise illegal-instruction; "
        "the reads return 3, and vl is still 3.\n"
        "2. vadd.vv, vle8.v (not fault-only-first, with AVL < VLMAX), vse8.v, vmv.s.x, vmv.x.s and writes of vstart, "
        "vxrm and vcsr leave vl = 3. vsetivli 2 then sets vl = 2.",
        setup,
        value,
        "vl_writable",
    )
    t.la("x6", BUF)
    for ln in [
        "vadd.vv v2, v4, v6",
        "vle8.v v1, (x6)",
        "vse8.v v1, (x6)",
        "vmv.s.x v3, x6",
        "vmv.x.s x7, v2",
        "csrw vstart, x0",
        "csrwi vxrm, 1",
        "csrwi vcsr, 0",
    ]:
        t.emit(ln)
    lab = mark(t)
    t.emit("csrr x7, vl")
    if mut("vl_changed_by_load"):
        vlmax(t, "x8", 8, "m1")
        eq_reg(t, "x7", "x8", lab, "vl after other vector instructions")
    else:
        t.check("x7", 3, lab, "vl after vadd/vle8/vse8/vmv/vector CSR writes")
    vset(t, "x0", 2, 8, "m1")
    lab = mark(t)
    t.emit("csrr x7, vl")
    t.check("x7", 2, lab, "vsetivli 2 updates vl")
    return t


@rule
def g_vlenb_acc_op() -> TestFile:
    def setup(t: TestFile) -> None:
        vset(t, "x0", 1, 32, "m4")

    def value(t: TestFile, reg: str) -> None:
        t.comment(f"VLMAX(e8, m1) = VLEN/8, from vsetvli rd, x0 (into {reg})")
        t.emit(f"vsetvli {reg}, x0, e8, m1, tu, mu")
        if mut("vlenb_bits"):
            t.emit(f"slli {reg}, {reg}, 3")

    t = ro_csr(
        "vlenb_acc_op",
        "vlenb",
        "The XLEN-bit-wide read-only CSR vlenb holds the value VLEN/8, i.e., the vector register length in bytes.",
        "VLMAX = LMUL*VLEN/SEW (norm:vlmax), so vsetvli rd, x0, e8, m1 returns VLEN/8 independently of vlenb. VLEN is "
        "a power of two of at least 32 bits for Zve32x (Zvl32b), so vlenb is a power of two >= 4.",
        "1. The eight CSR instruction forms on vlenb (vtype e32, m4): the six that write raise illegal-instruction; the "
        "reads return VLMAX(e8, m1), and vlenb is unchanged.\n"
        "2. vlenb is a power of two >= 4, equals VLMAX(e8, m8)/8, and reads the same under e8, mf2 as under e32, m4.",
        setup,
        value,
        "vlenb_writable",
    )
    lab = mark(t)
    t.emit("csrr x7, vlenb")
    t.emit("addi x8, x7, -1")
    t.emit("and x8, x8, x7")
    t.check("x8", 0, lab, "vlenb is a power of two (vlenb & (vlenb-1))")
    t.emit("sltiu x8, x7, 4")
    t.check("x8", 0, lab, "vlenb >= 4 (VLEN >= 32)")
    t.emit("vsetvli x8, x0, e8, m8, tu, mu")
    t.emit("srli x8, x8, 3")
    eq_reg(t, "x7", "x8", lab, "vlenb == VLMAX(e8, m8)/8")
    t.emit("vsetvli x8, x0, e8, mf2, tu, mu")
    t.emit("csrr x8, vlenb")
    eq_reg(t, "x7", "x8", lab, "vlenb does not depend on vtype")
    return t


@rule
def g_vlen() -> TestFile:
    t = new("vlen")
    t.describe(
        rule_text="The number of bits in a single vector register, VLEN >= 8, which must be a power of 2, and must be "
        "no greater than 2^16.",
        source=VC,
        context="VLEN = 8*vlenb (norm:vlenb_acc_op). Zve32x also requires VLEN >= ELEN = 32.",
        plan="vlenb is a power of two with 1 <= vlenb <= 8192 (8 <= VLEN <= 2^16); VLMAX(e8, m8) = 8*vlenb = VLEN "
        "is also a power of two <= 2^16.",
    )
    lab = mark(t)
    t.emit("csrr x7, vlenb")
    t.emit("addi x8, x7, -1")
    t.emit("and x8, x8, x7")
    t.check("x8", 0, lab, "vlenb is a power of two")
    t.emit("seqz x8, x7")
    t.check("x8", 0, lab, "vlenb != 0 (VLEN >= 8)")
    t.li("x9", 8193)
    t.emit("sltu x8, x7, x9")
    t.check_bool("x8", lab, "vlenb <= 8192 (VLEN <= 2^16)")
    t.emit("vsetvli x8, x0, e8, m8, tu, mu")
    t.emit("slli x9, x7, 3")
    eq_reg(t, "x8", "x9", lab, "VLMAX(e8, m8) = VLEN = 8*vlenb", tmp="x1")
    return t


@rule
def g_vreg_count() -> TestFile:
    t = new("vreg_count")
    t.describe(
        rule_text="The vector extension adds 32 architectural vector registers, v0-v31 to the base scalar RISC-V ISA.",
        source=VC,
        plan="e8, m1, vl = 1: vmv.s.x writes a distinct byte (0x40+i) into element 0 of every register v0-v31, then "
        "vmv.x.s reads each back: every register holds its own value (no aliasing among the 32).",
    )
    vset(t, "x0", 1, 8, "m1")
    for i in range(32):
        t.li("x6", 0x40 + i)
        t.emit(f"vmv.s.x v{i}, x6")
    for i in range(32):
        lab = mark(t)
        t.emit(f"vmv.x.s x7, v{i}")
        exp = 0x40 + i
        if mut("vreg_count_16") and i >= 16:
            exp = 0x40 + i - 16
        t.check("x7", exp, lab, f"v{i} element 0")
    return t


@rule
def g_vstart_acc_sz() -> TestFile:
    t = new("vstart_acc_sz")
    t.describe(
        rule_text="The XLEN-bit-wide read-write vstart CSR specifies the index of the first element to be executed by "
        "a vector instruction, as described in <<sec-inactive-defs>>.",
        source=VC,
        context="vstart holds any element index below the maximum VLMAX = VLEN (e8, m8) (norm:vstart_sz_writable); "
        "VLEN >= 32 for Zve32x, so values below 32 are held exactly. CSR instructions are not vector instructions, so "
        "they do not reset vstart (norm:vstart_update).",
        plan="Before each of the eight CSR forms, vstart = 10 (csrwi). x6 = 6, the immediate forms use 3. Each form "
        "returns the old value 10 in rd and leaves the Zicsr result: read 10, write 6, swap 6, set 14, clear 8, write "
        "immediate 3, read (uimm=0) 10, clear immediate 8. No form traps. vstart is cleared at the end.",
    )
    t.li("x6", 6)
    res = {
        "csrrs x7, 0x8, x0": 10,
        "csrrw x0, 0x8, x6": 6,
        "csrrw x7, 0x8, x6": 6,
        "csrrs x7, 0x8, x6": 14,
        "csrrc x7, 0x8, x6": 8,
        "csrrwi x7, 0x8, 3": 3,
        "csrrsi x7, 0x8, 0": 10,
        "csrrci x7, 0x8, 3": 8,
    }
    for asm, new_v in res.items():
        t.emit("csrwi vstart, 10")
        t.emit("li x7, 0")
        lab = mark(t)
        t.emit(asm)
        if "x7" in asm.split(",")[0]:
            t.check("x7", 10, lab, f"{asm}: rd = old vstart")
        t.emit("csrr x8, vstart")
        if mut("vstart_rmw_wrong") and asm == "csrrs x7, 0x8, x6":
            new_v = 6
        t.check("x8", new_v, lab, f"{asm}: new vstart")
    t.emit("csrw vstart, x0")
    return t


@rule
def g_vstart_sz_writable() -> TestFile:
    t = new("vstart_sz_writable")
    t.describe(
        rule_text="The vstart CSR is defined to have only enough writable bits to hold the largest element index (one "
        "less than the maximum VLMAX).",
        source=VC,
        context="The maximum VLMAX is VLEN (SEW=8 and LMUL=8 are always supported), so vstart has log2(VLEN) "
        "writable bits: a write keeps the value modulo VLEN.",
        plan="VLEN = 8*vlenb. Write vstart = all ones: it reads VLEN-1. Write VLEN: reads 0. Write VLEN-2 and "
        "VLEN+1: read VLEN-2 and 1. Write 2^(XLEN-1)+5: reads 5. vstart is cleared afterwards.",
    )
    t.emit("csrr x8, vlenb")
    t.emit("slli x8, x8, 3  // VLEN")
    cases = [
        ("li x6, -1", "addi x9, x8, -1", "all ones"),
        ("mv x6, x8", "li x9, 0", "VLEN"),
        ("addi x6, x8, -2", "addi x9, x8, -2", "VLEN-2"),
        ("addi x6, x8, 1", "li x9, 1", "VLEN+1"),
    ]
    for set_src, exp, d in cases:
        t.emit(set_src)
        lab = mark(t)
        t.emit("csrw vstart, x6")
        t.emit("csrr x7, vstart")
        if mut("vstart_full_width"):
            t.emit("mv x9, x6")
        elif mut("vstart_one_bit_short") and d == "all ones":
            t.emit("srli x9, x8, 1")
            t.emit("addi x9, x9, -1")
        else:
            t.emit(exp)
        eq_reg(t, "x7", "x9", lab, f"vstart written with {d} keeps the value mod VLEN", tmp="x1")
    t.load("x6", X((1 << 31) | 5, (1 << 63) | 5), "2^(XLEN-1) + 5")
    lab = mark(t)
    t.emit("csrw vstart, x6")
    t.emit("csrr x7, vstart")
    t.check(
        "x7",
        5 if not mut("vstart_full_width") else X((1 << 31) | 5, (1 << 63) | 5),
        lab,
        "vstart written with 2^(XLEN-1)+5",
    )
    t.emit("csrw vstart, x0")
    return t


def rw_small_csr(
    rule_name: str,
    csr: str,
    width_mask: int,
    text: str,
    ctx: str,
    plan: str,
    mutant: str | None,
    imm: int,
    src: int,
    old: int,
) -> TestFile:
    t = new(rule_name)
    t.describe(rule_text=text, source=VC, context=ctx, plan=plan)
    t.li("x6", src)
    num = CSR[csr]
    forms = {
        f"csrrs x7, {num}, x0": old,
        f"csrrw x0, {num}, x6": src,
        f"csrrw x7, {num}, x6": src,
        f"csrrs x7, {num}, x6": old | src,
        f"csrrc x7, {num}, x6": old & ~src,
        f"csrrwi x7, {num}, {imm}": imm,
        f"csrrsi x7, {num}, 0": old,
        f"csrrci x7, {num}, {imm}": old & ~imm,
    }
    for asm, nv in forms.items():
        t.emit(f"csrwi {num}, {old}")
        lab = mark(t)
        t.emit(asm)
        if asm.split()[1].startswith("x7"):
            t.check_masked("x7", width_mask, old, lab, f"{asm}: rd = old {csr} (bits {hex(width_mask)})")
        t.emit(f"csrr x8, {num}")
        t.check_masked("x8", width_mask, nv & width_mask, lab, f"{asm}: new {csr} (bits {hex(width_mask)})")
    t.emit(f"csrwi {num}, 0")
    return t


@rule
def g_vxrm_val_sz_acc() -> TestFile:
    t = rw_small_csr(
        "vxrm_val_sz_acc",
        "vxrm",
        3,
        "The vector fixed-point rounding-mode register holds a two-bit read-write rounding-mode field in the "
        "least-significant bits (vxrm[1:0]). The upper bits, vxrm[XLEN-1:2], should be written as zeros.",
        "Only vxrm[1:0] is defined; upper bits are written as zeros here and not checked (their read value is not "
        "specified).",
        "1. Each value 0-3 written with csrwi reads back in vxrm[1:0].\n"
        "2. Before each of the eight CSR forms, vxrm = 1; x6 = 2, immediates 3: results read 1, write 2, swap 2, "
        "set 3, clear 1, write immediate 3, read 1, clear immediate 0, in bits 1:0 (rd returns the old 1).",
        "vxrm_3bits",
        3,
        2,
        1,
    )
    for v in range(4):
        t.emit(f"csrwi vxrm, {v}")
        lab = mark(t)
        t.emit("csrr x7, vxrm")
        t.check_masked("x7", 3, v, lab, f"vxrm written with {v}")
    t.emit("csrwi vxrm, 0")
    if mut("vxrm_3bits"):
        t.li("x6", 7)
        t.emit("csrw vxrm, x6")
        lab = mark(t)
        t.emit("csrr x7, vxrm")
        t.check_masked("x7", 7, 7, lab, "vxrm keeps bit 2")
        t.emit("csrwi vxrm, 0")
    return t


@rule
def g_vxsat_op_acc_sz() -> TestFile:
    t = rw_small_csr(
        "vxsat_op_acc_sz",
        "vxsat",
        1,
        "The vxsat CSR has a single read-write least-significant bit (vxsat[0]) that indicates if a fixed-point "
        "instruction has had to saturate an output value to fit into a destination format. The remaining bits, "
        "vxsat[XLEN-1:1], should be written as zeros.",
        "Only vxsat[0] is checked. vsaddu.vv saturates when the unsigned sum overflows SEW bits "
        "(norm:vsaddu_vsadd_vssubu_vssub_op_overflow_vxsat_op_vsaddsub).",
        "1. Eight CSR forms on vxsat, each starting from vxsat = 0, x6 = 1, immediates 1: bit 0 reads 0, 1, 1, 1, 0, "
        "1, 0, 0.\n"
        "2. e8, vl = 1: vxsat = 0, vsaddu.vv of 1 + 2 (no saturation) leaves vxsat[0] = 0; vsaddu.vv of 200 + 100 "
        "(saturates to 255) sets vxsat[0] = 1 and the result is 255.",
        None,
        1,
        1,
        0,
    )
    vset(t, "x0", 1, 8, "m1")
    for a, b, sat in ((1, 2, 0), (200, 100, 1)):
        t.emit("csrwi vxsat, 0")
        t.li("x6", a)
        t.emit("vmv.s.x v1, x6")
        t.li("x6", b)
        t.emit("vmv.s.x v2, x6")
        lab = mark(t)
        t.emit("vsaddu.vv v3, v1, v2")
        t.emit("csrr x7, vxsat")
        exp = sat
        if mut("vxsat_not_set"):
            exp = 0
        if mut("vxsat_set_always"):
            exp = 1
        t.check_masked("x7", 1, exp, lab, f"vxsat after vsaddu {a}+{b} at e8")
        t.emit("vmv.x.s x7, v3")
        t.check("x7", sext(min(a + b, 255), 8), lab, f"vsaddu {a}+{b} result (sign-extended by vmv.x.s)")
    t.emit("csrwi vxsat, 0")
    return t


@rule
def g_vcsr_vxrm_vxsat_acc() -> TestFile:
    t = rw_small_csr(
        "vcsr_vxrm_vxsat_acc",
        "vcsr",
        7,
        "The vxrm and vxsat separate CSRs can also be accessed via fields in the XLEN-bit-wide vector control and "
        "status CSR, vcsr.",
        "vcsr layout: vxsat in bit 0, vxrm in bits 2:1, bits XLEN-1:3 reserved (not checked).",
        "1. Eight CSR forms on vcsr from vcsr = 3, x6 = 5, immediates 6: bits 2:0 read 3, 5, 5, 7, 2, 6, 3, 1.\n"
        "2. For each vcsr value 0-7 written with csrwi: vxsat reads bit 0 and vxrm reads bits 2:1.",
        None,
        6,
        5,
        3,
    )
    for v in range(8):
        t.emit(f"csrwi vcsr, {v}")
        lab = mark(t)
        t.emit("csrr x7, vxsat")
        t.check_masked("x7", 1, (v & 1) if not mut("vcsr_vxsat_bit3") else 0, lab, f"vcsr={v}: vxsat")
        t.emit("csrr x7, vxrm")
        t.check_masked("x7", 3, (v >> 1) if not mut("vcsr_vxrm_low") else v & 3, lab, f"vcsr={v}: vxrm")
    t.emit("csrwi vcsr, 0")
    return t


@rule
def g_vcsr_vxrm_op() -> TestFile:
    t = new("vcsr_vxrm_op")
    t.describe(
        rule_text="The vector fixed-point rounding-mode is given a separate CSR address to allow independent access, "
        "but is also reflected as a field in vcsr.",
        source=VC,
        context="vcsr[2:1] is vxrm (vcsr layout figure).",
        plan="With vxsat = 1: for vxrm = 0-3 written through vxrm, vcsr[2:0] reads 2*vxrm+1 (vxsat kept). Then for "
        "vcsr written with vxrm field 0-3 (and vxsat = 0), vxrm reads the field. A write of vxrm does not change "
        "vxsat.",
    )
    t.emit("csrwi vxsat, 1")
    for v in range(4):
        t.emit(f"csrwi vxrm, {v}")
        lab = mark(t)
        t.emit("csrr x7, vcsr")
        exp = (v << 1) | 1 if not mut("vcsr_vxrm_low") else v | 1
        t.check_masked("x7", 7, exp, lab, f"vxrm={v} with vxsat=1: vcsr[2:0]")
    for v in range(4):
        t.emit(f"csrwi vcsr, {v << 1}")
        lab = mark(t)
        t.emit("csrr x7, vxrm")
        t.check_masked("x7", 3, v if not mut("vcsr_vxrm_low") else (v << 1) & 3, lab, f"vcsr={v << 1}: vxrm")
        t.emit("csrr x7, vxsat")
        t.check_masked("x7", 1, 0, lab, f"vcsr={v << 1}: vxsat")
    t.emit("csrwi vcsr, 0")
    return t


@rule
def g_vcsr_vxsat_op() -> TestFile:
    t = new("vcsr_vxsat_op")
    t.describe(
        rule_text="The vxsat bit is mirrored in vcsr.",
        source=VC,
        context="vcsr[0] is vxsat.",
        plan="1. vxrm = 2: vxsat written 1 then 0 through vxsat: vcsr[2:0] reads 5 then 4.\n"
        "2. vcsr written with 1 and 0 (vxrm = 0): vxsat reads 1 and 0.\n"
        "3. A saturating vsaddu.vv (e8, 255 + 1) from vxsat = 0 makes vcsr[0] = 1.",
    )
    t.emit("csrwi vxrm, 2")
    for v in (1, 0):
        t.emit(f"csrwi vxsat, {v}")
        lab = mark(t)
        t.emit("csrr x7, vcsr")
        t.check_masked("x7", 7, 4 | v if not mut("vcsr_vxsat_bit3") else 4, lab, f"vxsat={v}, vxrm=2: vcsr[2:0]")
    for v in (1, 0):
        t.emit(f"csrwi vcsr, {v}")
        lab = mark(t)
        t.emit("csrr x7, vxsat")
        t.check_masked("x7", 1, v if not mut("vcsr_vxsat_bit3") else 0, lab, f"vcsr={v}: vxsat")
    vset(t, "x0", 1, 8, "m1")
    t.emit("csrwi vcsr, 0")
    t.li("x6", 255)
    t.emit("vmv.s.x v1, x6")
    t.li("x6", 1)
    t.emit("vmv.s.x v2, x6")
    lab = mark(t)
    t.emit("vsaddu.vv v3, v1, v2")
    t.emit("csrr x7, vcsr")
    t.check_masked(
        "x7",
        1,
        1 if not (mut("vxsat_not_set") or mut("vcsr_vxsat_bit3")) else 0,
        lab,
        "vcsr[0] after a saturating vsaddu",
    )
    t.emit("csrwi vcsr, 0")
    return t


def roundoff(v: int, d: int, mode: int) -> int:
    """norm:vxrm_op: (v >> d) + r."""
    if d == 0:
        return v

    def bit(i: int) -> int:
        return (v >> i) & 1 if i >= 0 else 0

    low = v & ((1 << d) - 1)
    if mode == 0:  # rnu
        r = bit(d - 1)
    elif mode == 1:  # rne
        r = bit(d - 1) & (int((v & ((1 << (d - 1)) - 1)) != 0) | bit(d))
    elif mode == 2:  # rdn
        r = 0
    else:  # rod
        r = int(not bit(d)) & int(low != 0)
    return (v >> d) + r


@rule
def g_vxrm_op() -> TestFile:
    t = new("vxrm_op")
    cases = [
        (0x2B, 0),
        (1, 1),
        (2, 1),
        (3, 1),
        (2, 2),
        (6, 2),
        (5, 2),
        (7, 2),
        (4, 2),
        (0x18, 4),
        (0x28, 4),
        (0x7FFF, 15),
        (0xFFFF, 15),
        (0x8000, 15),
        (0x1234, 8),
        (0x12FF, 8),
    ]
    t.describe(
        rule_text="The fixed-point rounding algorithm is specified as follows. Suppose the pre-rounding result is v, "
        "and d bits of that result are to be rounded off. Then the rounded result is (v >> d) + r, where r depends on "
        "the rounding mode as specified in the following table.",
        source=VC,
        context="Table: rnu (0) r = v[d-1]; rne (1) r = v[d-1] & (v[d-2:0] != 0 | v[d]); rdn (2) r = 0; rod (3) "
        "r = !v[d] & v[d-1:0] != 0. vssrl.vx is a scaling shift whose result is exactly roundoff_unsigned(vs2, "
        "rs1[log2(SEW)-1:0]) (norm:vssrl_vssra_op), so it exposes r directly.",
        plan="e16, vl = 1. For each vxrm 0-3 and each (v, d): "
        + ", ".join(f"({hex(v)}, {d})" for v, d in cases)
        + " (covering d = 0, ties with v[d] = 0 and 1, above/below half, exact, d = SEW-1), vssrl.vx returns "
        "(v >> d) + r. vmv.x.s sign-extends the 16-bit result.",
    )
    vset(t, "x0", 1, 16, "m1")
    for mode in range(4):
        t.emit(f"csrwi vxrm, {mode}")
        for v, d in cases:
            t.li("x6", v)
            t.emit("vmv.s.x v1, x6")
            t.li("x7", d)
            lab = mark(t)
            t.emit("vssrl.vx v2, v1, x7")
            t.emit("vmv.x.s x8, v2")
            m = mode
            if mut("rne_as_rnu") and mode == 1:
                m = 0
            if mut("rod_as_rdn") and mode == 3:
                m = 2
            t.check("x8", sext(roundoff(v, d, m) & 0xFFFF, 16), lab, f"vxrm={mode}: vssrl {hex(v)} >> {d}")
    t.emit("csrwi vxrm, 0")
    return t


# ======================================================================== mstatus.VS
OFF_INSNS = [
    ("vsetvli x7, x0, e8, m1, tu, mu", "vsetvli"),
    ("vsetivli x7, 1, e8, m1, tu, mu", "vsetivli"),
    ("vsetvl x7, x0, x0", "vsetvl"),
    ("vadd.vv v1, v2, v3", "vadd.vv"),
    ("vle8.v v1, (x6)", "vle8.v"),
    ("vl1re8.v v1, (x6)", "vl1re8.v (whole register)"),
    ("vmv.x.s x7, v1", "vmv.x.s"),
    ("csrr x7, vstart", "read vstart"),
    ("csrr x7, vxsat", "read vxsat"),
    ("csrr x7, vxrm", "read vxrm"),
    ("csrr x7, vcsr", "read vcsr"),
    ("csrr x7, vl", "read vl"),
    ("csrr x7, vtype", "read vtype"),
    ("csrr x7, vlenb", "read vlenb"),
    ("csrw vstart, x0", "write vstart"),
    ("csrwi vxrm, 1", "write vxrm"),
    ("csrwi vcsr, 0", "write vcsr"),
]


def vs_off_body(t: TestFile, modes: list[str], setter: Callable[[TestFile, int], None]) -> None:
    for mode in modes:
        t.comment(f"VS = Off, instructions in {mode}-mode")
        setter(t, VS_OFF)
        t.la("x6", BUF)
        for asm, d in OFF_INSNS:
            exp = ILLEGAL
            if mut("vs_off_csr_ok") and asm.startswith("csrr"):
                exp = "ok"
            if mut("vs_off_vset_ok") and asm.startswith("vset"):
                exp = "ok"
            vwin(t, [asm], exp, f"{d} with VS=Off", mode=mode)
        t.comment("control: with VS = Initial the same vsetvli executes")
        setter(t, VS_INIT)
        vwin(t, [OFF_INSNS[0][0]], "ok", "vsetvli with VS=Initial", mode=mode)
    setter(t, VS_DIRTY)


@rule
def g_mstatus_vs_op_off() -> list[TestFile]:
    text = (
        "Attempts to execute any vector instruction, or to access the vector CSRs, raise an illegal-instruction "
        "exception when mstatus[vs] is set to Off."
    )
    ctx = (
        "sstatus.VS is mstatus.VS (norm:mstatus_vs_sstatus_vs_op). The vector CSRs are vstart, vxsat, vxrm, vcsr, "
        "vl, vtype and vlenb. xtval of the trap is 0 or the instruction bits."
    )
    t = snew("mstatus_vs_op_off")
    t.describe(
        rule_text=text,
        source=VC,
        context=ctx,
        plan="In S-mode and in U-mode, with sstatus.VS = Off: vsetvli, vsetivli, vsetvl, vadd.vv, vle8.v, "
        "vl1re8.v, vmv.x.s, a read of each vector CSR and writes of vstart, vxrm and vcsr each raise "
        "illegal-instruction. Control: with VS = Initial the vsetvli executes. M-mode is in the _Sm file.",
    )
    vs_off_body(t, ["S", "U"], lambda tt, v: set_vs(tt, v))
    m = mnew("mstatus_vs_op_off")
    m.describe(
        rule_text=text,
        source=VC,
        context=ctx,
        plan="M-mode part: with mstatus.VS = Off the same instructions raise illegal-instruction in M-mode, and "
        "in U-mode when U is implemented. Control: VS = Initial lets vsetvli execute.",
    )
    vs_off_body(m, ["M"], lambda tt, v: set_mvs(tt, v))
    with m.only_if("defined(U_SUPPORTED)"):
        vs_off_body(m, ["U"], lambda tt, v: set_mvs(tt, v))
    return [t, m]


CHANGES = [
    ("vsetvli x7, x0, e8, m1, tu, mu", "vsetvli (vl and vtype change)"),
    ("vadd.vi v1, v1, 1", "vadd.vi (vector register changes)"),
    ("vle8.v v1, (x6)", "vle8.v (vector register changes)"),
    ("csrwi vxrm, 2", "csrwi vxrm"),
    ("csrwi vxsat, 1", "csrwi vxsat"),
    ("csrwi vcsr, 5", "csrwi vcsr"),
    ("csrwi vstart, 1", "csrwi vstart"),
    ("vmv.s.x v1, x7", "vmv.s.x"),
]


def prep_vstate(t: TestFile) -> None:
    """A known vector state that every CHANGES instruction alters: vl = 2, e16 m1, vxrm = vxsat = vstart = 0,
    v1 = 0, and BUF holds nonzero bytes. Needs VS != Off."""
    vset(t, "x0", 2, 16, "m1")
    t.emit("vmv.v.i v1, 0")
    t.emit("csrwi vcsr, 0")
    t.emit("csrw vstart, x0")
    t.la("x6", BUF)
    t.li("x7", 0x5A)
    t.emit("sb x7, 0(x6)")
    t.emit("sb x7, 1(x6)")


def vs_change_case(
    t: TestFile,
    vs0: int,
    asm: str,
    d: str,
    mode: str,
    setter: Callable[[TestFile, int], None],
    reader: Callable[[TestFile, str], None],
) -> None:
    setter(t, VS_DIRTY)
    prep_vstate(t)
    setter(t, vs0)
    t.la("x6", BUF)
    lab = vwin(t, [asm], "ok", f"{d} from VS={vs0 >> 9}", mode=mode)
    reader(t, "x7")
    exp = 3
    if mut("vs_clean_stays") and vs0 == VS_CLEAN:
        exp = 2
    if mut("vs_initial_stays") and vs0 == VS_INIT:
        exp = 1
    t.check("x7", exp, lab, f"VS after {d} in {mode}-mode from VS={vs0 >> 9}")
    if "vstart" in asm:
        t.emit("csrw vstart, x0")


@rule
def g_mstatus_vs_op_initial_clean() -> list[TestFile]:
    text = (
        "When mstatus[vs] is set to Initial or Clean, executing any instruction that changes vector state, "
        "including the vector CSRs, will change mstatus[vs] to Dirty. Implementations may also change "
        "mstatus[vs] from Initial or Clean to Dirty at any time, even when there is no change in vector state."
    )
    ctx = (
        "Each instruction changes the state it writes: the state is reset before each case (vl = 2, e16, vxrm = "
        "vxsat = vstart = 0, v1 = 0, the loaded bytes nonzero), so machine.adoc norm:mstatus_vs_no_change_dirty "
        "(writes that do not alter the contents) does not apply. The only legal VS afterwards is Dirty (3)."
    )
    plan = (
        "For VS = Initial and Clean, in {modes}: vsetvli, vadd.vi, vle8.v, csrwi vxrm, csrwi vxsat, csrwi vcsr, "
        "csrwi vstart and vmv.s.x each leave VS = Dirty."
    )
    t = snew("mstatus_vs_op_initial_clean")
    t.describe(
        rule_text=text, source=VC, context=ctx, plan=plan.format(modes="S-mode and U-mode (sstatus.VS read in S-mode)")
    )
    for mode in ("S", "U"):
        for vs0 in (VS_INIT, VS_CLEAN):
            for asm, d in CHANGES:
                vs_change_case(t, vs0, asm, d, mode, lambda tt, v: set_vs(tt, v), lambda tt, r: read_vs(tt, r))
    set_vs(t, VS_DIRTY)
    m = mnew("mstatus_vs_op_initial_clean")
    m.describe(rule_text=text, source=VC, context=ctx, plan=plan.format(modes="M-mode"))
    for vs0 in (VS_INIT, VS_CLEAN):
        for asm, d in CHANGES:
            vs_change_case(m, vs0, asm, d, "M", lambda tt, v: set_mvs(tt, v), lambda tt, r: read_vs(tt, r, "mstatus"))
    set_mvs(m, VS_DIRTY)
    return [t, m]


@rule
def g_mstatus_vs_op() -> TestFile:
    t = snew("mstatus_vs_op")
    t.describe(
        rule_text="The vs field encodes the status of the vector extension state, including the vector registers "
        "v0-v31 and the CSRs vcsr, vxrm, vxsat, vstart, vl, vtype, and vlenb.",
        source=MAC,
        context="Each listed piece of state is changed on its own from VS = Clean; the change must make VS Dirty "
        "(norm:mstatus_vs_op_initial_clean). vlenb is read-only and cannot change.",
        plan="S-mode, VS = Clean before each case, state reset first: v0 (vmv.v.i), v31 (vmv.v.i), vcsr (csrwi), "
        "vxrm, vxsat, vstart, vl only (vsetivli with the same vtype and another AVL) and vtype only (vsetvli x0, x0 "
        "with the same SEW/LMUL ratio, which keeps vl) each leave VS = Dirty.",
    )
    pieces = [
        ("vmv.v.i v0, 7", "v0"),
        ("vmv.v.i v31, 7", "v31"),
        ("csrwi vcsr, 3", "vcsr"),
        ("csrwi vxrm, 3", "vxrm"),
        ("csrwi vxsat, 1", "vxsat"),
        ("csrwi vstart, 1", "vstart"),
        ("vsetivli x0, 1, e16, m1, tu, mu", "vl only"),
        ("vsetvli x0, x0, e8, mf2, tu, mu", "vtype only"),
    ]
    for asm, d in pieces:
        set_vs(t, VS_DIRTY)
        prep_vstate(t)
        t.emit("vmv.v.i v0, 0")
        t.emit("vmv.v.i v31, 0")
        set_vs(t, VS_CLEAN)
        lab = mark(t)
        t.emit(asm)
        read_vs(t, "x7")
        t.check("x7", 3 if not mut("vs_clean_stays") else 2, lab, f"VS after changing {d} from Clean")
        if "vstart" in asm:
            t.emit("csrw vstart, x0")
    set_vs(t, VS_DIRTY)
    return t


@rule
def g_mstatus_sd_vs_dirty_op() -> TestFile:
    t = snew("mstatus_sd_vs_dirty_op")
    t.describe(
        rule_text="If mstatus[vs] is Dirty, mstatus[sd] is 1; otherwise, mstatus[sd] is set in accordance with "
        "existing specifications.",
        source=VC,
        context="Otherwise SD = (FS == Dirty) | (XS == Dirty) (machine.adoc norm:mstatus_sd_formula). FS is set to "
        "Off where writable (it may be read-only 0 without F), and FS/XS are read back to compute the expected SD. "
        "sstatus.SD shadows mstatus.SD.",
        plan="1. FS = Off. VS = Dirty: sstatus.SD = 1 and mstatus.SD (T-SBI read) = 1.\n"
        "2. VS = Clean: sstatus.SD = (FS == 3) | (XS == 3) from the value read.\n"
        "3. From VS = Clean, vsetvli makes VS Dirty and sstatus.SD = 1.\n"
        "FS and VS are restored to Dirty.",
    )
    t.li("x6", 3 << 13)
    t.emit("csrc sstatus, x6  // FS = Off")
    set_vs(t, VS_DIRTY)
    lab = mark(t)
    t.emit("csrr x7, sstatus")
    t.emit("srli x7, x7, __riscv_xlen - 1" if False else "slt x7, x7, x0  // SD (sign bit)")
    t.check("x7", 1 if not mut("sd_ignores_vs") else 0, lab, "sstatus.SD with VS=Dirty")
    t.tsbi_csr("READ", "mstatus")
    t.emit("slt x7, a0, x0")
    t.check("x7", 1 if not mut("sd_ignores_vs") else 0, lab, "mstatus.SD with VS=Dirty")
    set_vs(t, VS_CLEAN)
    lab = mark(t)
    t.emit("csrr x7, sstatus")
    t.emit("slt x8, x7, x0  // SD")
    t.emit("srli x9, x7, 13")
    t.emit("andi x9, x9, 3")
    t.emit("addi x9, x9, -3")
    t.emit("seqz x9, x9  // FS == Dirty")
    t.emit("srli x1, x7, 15")
    t.emit("andi x1, x1, 3")
    t.emit("addi x1, x1, -3")
    t.emit("seqz x1, x1  // XS == Dirty")
    t.emit("or x9, x9, x1")
    t.emit("xor x8, x8, x9")
    t.check("x8", 0, lab, "VS=Clean: SD == (FS == Dirty | XS == Dirty)")
    lab = mark(t)
    t.emit("vsetvli x7, x0, e8, m1, tu, mu")
    t.emit("csrr x7, sstatus")
    t.emit("slt x7, x7, x0")
    t.check(
        "x7", 1 if not (mut("sd_ignores_vs") or mut("vs_clean_stays")) else 0, lab, "SD after vsetvli from VS=Clean"
    )
    t.li("x6", 3 << 13)
    t.emit("csrs sstatus, x6  // FS = Dirty")
    set_vs(t, VS_DIRTY)
    return t


@rule
def g_mstatus_vs_sstatus_vs_op() -> TestFile:
    t = snew("mstatus_vs_sstatus_vs_op")
    t.describe(
        rule_text="A vector context status field, vs, is added to mstatus[10:9] and shadowed in sstatus[10:9]. It is "
        "defined analogously to the floating-point context status field, fs.",
        source=VC,
        context="machine.adoc norm:mstatus_vs_imprecise lets a write of Initial or Clean read back as Dirty; Off and "
        "Dirty read back exactly (the field is not read-only zero with vector registers, norm:mstatus_vs_acc1).",
        plan="1. For each VS value 0-3 written through sstatus[10:9]: sstatus.VS reads the value (Initial/Clean may "
        "read Dirty), and mstatus.VS (T-SBI read) equals sstatus.VS.\n"
        "2. For each value written to mstatus[10:9] through T-SBI (clear then set): sstatus.VS equals mstatus.VS "
        "read back.\nVS is restored to Dirty.",
    )
    for v in range(4):
        set_vs(t, v << 9)
        lab = mark(t)
        read_vs(t, "x7")
        t.check("x7", [v, 3] if v in (1, 2) else v, lab, f"sstatus.VS written with {v}")
        t.tsbi_csr("READ", "mstatus")
        t.emit("srli x8, a0, 9")
        t.emit("andi x8, x8, 3")
        if mut("sstatus_vs_independent"):
            t.check("x8", 3, lab, "mstatus.VS unchanged by sstatus")
        else:
            eq_reg(t, "x7", "x8", lab, f"mstatus.VS == sstatus.VS after sstatus.VS = {v}")
    for v in range(4):
        t.tsbi_csr("CLEAR", "mstatus", imm=VS_MASK)
        if v:
            t.tsbi_csr("SET", "mstatus", imm=v << 9)
        t.tsbi_csr("READ", "mstatus")
        t.emit("srli x8, a0, 9")
        t.emit("andi x8, x8, 3")
        lab = mark(t)
        read_vs(t, "x7")
        eq_reg(t, "x7", "x8", lab, f"sstatus.VS == mstatus.VS after mstatus.VS = {v}")
        t.check("x7", [v, 3] if v in (1, 2) else v, lab, f"VS written with {v} through mstatus")
    set_vs(t, VS_DIRTY)
    return t


@rule
def g_misa_v_op() -> TestFile:
    t = mnew("misa_v_op", required=["I", "Sm", "V"], suffix="")
    t.describe(
        rule_text="The misa[v] bit is set for implementations providing misa and supporting V.",
        source=VST,
        context="misa may be read-only zero (not implemented); then the rule does not apply. machine.adoc lets misa.V "
        "be writable, but its reset value with V implemented has V set and the framework does not clear it.",
        plan="M-mode: read misa. If misa != 0, bit 21 (V) is 1.",
    )
    t.emit("csrr x7, misa")
    t.emit("snez x8, x7")

    def chk() -> None:
        lab = mark(t)
        t.emit("srli x9, x7, 21")
        t.emit("andi x9, x9, 1")
        t.check("x9", 1 if not mut("vector_misa_v_clear") else 0, lab, "misa.V")

    t.either("x8", chk, lambda: None)
    return t


# ======================================================================== vtype fields and VLMAX
def vill_chk(t: TestFile, lab: str, d: str, exp_vill: int, vti: int | None = None) -> None:
    """vtype read: vill (sign bit) == exp_vill; when 0 and vti given, vtype == vti."""
    t.emit("csrr x8, vtype")
    t.emit("slt x9, x8, x0  // vill")
    t.check("x9", exp_vill, lab, f"{d}: vill")
    if vti is not None and not exp_vill:
        t.check("x8", vti, lab, f"{d}: vtype value")


def vlmax_chk(t: TestFile, rd: str, sew: int, lmul: str, lab: str, d: str) -> None:
    vlmax(t, "x9", sew, lmul)
    eq_reg(t, rd, "x9", lab, f"{d}: VLMAX = LMUL*VLEN/SEW", tmp="x1")


@rule
def g_vtype_vsew_op() -> TestFile:
    t = new("vtype_vsew_op")
    t.describe(
        rule_text="The value in vsew sets the dynamic selected element width (SEW). By default, a vector register is "
        "viewed as being divided into VLEN/SEW elements.",
        source=VC,
        context="SEW 8, 16 and 32 are supported with Zve32x and 64 with Zve64x (ELEN = 64). vid.v writes element i = "
        "i, so the stored register shows its division into elements.",
        plan="For each supported SEW at LMUL=1: vsetvli rd, x0 returns VLEN/SEW and vtype.vsew holds the code; vid.v "
        "at VLMAX, stored with vs1r.v: element 1 is at byte SEW/8 (SEW <= 16, where VLMAX >= 2) and the last element, at byte vlenb - SEW/8, holds "
        "VLEN/SEW - 1 (SEW <= 32; at SEW = 64 the low word is read).",
    )
    for sew in (8, 16, 32, 64):
        ctx = t.only_if(E64) if sew == 64 else None
        if ctx:
            ctx.__enter__()
        lab = mark(t)
        t.emit(f"vsetvli x7, x0, e{sew}, m1, tu, mu")
        vill_chk(t, lab, f"e{sew}, m1", 0, vtypei(sew))
        if mut("vsew_ignored"):
            vlmax_chk(t, "x7", 8, "m1", lab, f"e{sew}")
        else:
            vlmax_chk(t, "x7", sew, "m1", lab, f"e{sew}")
        t.emit("vid.v v4")
        store(t, "v4")
        es = min(sew, 32)
        if sew <= 16:  # VLMAX(e32, m1) may be 1 (VLEN = 32), and VLMAX(e64, m1) may be 1 (VLEN = 64)
            ld_elem(t, "x8", es, sew // 8)
            t.check("x8", 1, lab, f"e{sew}: element 1 at byte {sew // 8}")
        t.emit("csrr x9, vlenb")
        t.emit(f"addi x9, x9, -{sew // 8}")
        ld_elem(t, "x8", es, "x9")
        t.emit("addi x7, x7, -1  // VLMAX - 1")
        if sew == 8:
            t.emit("andi x7, x7, 0xff")
        if sew == 16:
            t.li("x1", 0xFFFF)
            t.emit("and x7, x7, x1")
        eq_reg(t, "x8", "x7", lab, f"e{sew}: last element holds VLEN/SEW - 1")
        if ctx:
            ctx.__exit__(None, None, None)
    return t


def sew_lmul_case(t: TestFile, sew: int, lmul: str, need: bool, d: str, check_vlmax: bool = True) -> None:
    """vsetvli at (sew, lmul): when need, vill must be 0 (and VLMAX right); otherwise vill may be set, and if it is
    not, VLMAX must be right."""
    lab = mark(t)
    t.emit(f"vsetvli x7, x0, e{sew}, {lmul}, tu, mu")
    if need:
        exp = 0
        if mut("frac_lmul_unsupported") and lmul == "mf2":
            exp = 1
        vill_chk(t, lab, f"{d} e{sew}, {lmul}", exp, vtypei(sew, lmul))
        if check_vlmax:
            vlmax_chk(t, "x7", sew, lmul, lab, f"{d} e{sew}, {lmul}")
    else:
        t.emit("csrr x8, vtype")
        t.emit("slt x8, x8, x0")
        t.emit("seqz x8, x8")
        if check_vlmax:
            t.either("x8", lambda: vlmax_chk(t, "x7", sew, lmul, lab, f"{d} e{sew}, {lmul} (supported)"), lambda: None)


@rule
def g_vtype_lmul_val() -> TestFile:
    t = new("vtype_lmul_val")
    t.describe(
        rule_text="Implementations must support LMUL integer values of 1, 2, 4, and 8.",
        source=VC,
        context="For every supported SEW (8, 16, 32; 64 with Zve64x).",
        plan="For each SEW and LMUL 1, 2, 4, 8: vsetvli rd, x0 leaves vill = 0 with the requested vtype, and rd = "
        "LMUL*VLEN/SEW.",
    )
    for sew in (8, 16, 32, 64):
        for lm in ("m1", "m2", "m4", "m8"):
            if sew == 64:
                with t.only_if(E64):
                    sew_lmul_case(t, sew, lm, True, "integer LMUL")
            else:
                sew_lmul_case(t, sew, lm, True, "integer LMUL")
    return t


@rule
def g_vtype_lmul_fval() -> TestFile:
    t = new("vtype_lmul_fval")
    t.describe(
        rule_text="Implementations must provide fractional LMUL settings that allow the narrowest supported type to "
        "occupy a fraction of a vector register corresponding to the ratio of the narrowest supported type's width to "
        "the smaller of VLEN and the largest supported type's width. In general, the requirement is to support LMUL >= "
        "SEW_MIN/min(ELEN, VLEN), where SEW_MIN is the narrowest supported SEW value, ELEN is the widest supported SEW "
        "value and VLEN is the number of bits in a vector register. In the standard extensions, SEW_MIN=8. For vector "
        "extensions with ELEN=32, fractional LMULs of 1/2 and 1/4 must be supported. For vector extensions with "
        "ELEN=64 and ELEN <= VLEN, fractional LMULs of 1/2, 1/4, and 1/8 must be supported. For vector extensions with "
        "SEW_MIN=8, ELEN=64 and VLEN=32, fractional LMULs of 1/2 and 1/4 must be supported.",
        source=VC,
        context="ELEN = 64 with Zve64x, else 32. Zve64x requires VLEN >= 64 = ELEN, so LMUL = 1/8 is required whenever "
        "Zve64x is present. LMUL = 1/8 with ELEN = 32 is reserved and may set vill "
        "(norm:vtype_lmul_fval_rsv).",
        plan="SEW = 8: LMUL 1/2 and 1/4 leave vill = 0 with VLMAX = VLEN/16 and VLEN/32; with Zve64x LMUL 1/8 too "
        "(VLEN/64). Without Zve64x, LMUL 1/8 may set vill; if it does not, VLMAX = VLEN/64.",
    )
    sew_lmul_case(t, 8, "mf2", True, "")
    sew_lmul_case(t, 8, "mf4", True, "")
    with t.only_if(E64):
        sew_lmul_case(t, 8, "mf8", True, "ELEN=64:")
    with t.only_if("!" + E64):
        sew_lmul_case(t, 8, "mf8", False, "ELEN=32:")
    return t


@rule
def g_vtype_sew_val() -> TestFile:
    t = new("vtype_sew_val")
    t.describe(
        rule_text="For a given supported fractional LMUL setting, implementations must support SEW settings between "
        "SEW_MIN and LMUL * min(ELEN, VLEN), inclusive.",
        source=VC,
        context="VLEN >= ELEN for Zve* (zve32x.adoc), so the bound is LMUL*ELEN. ELEN = 64 with Zve64x, else 32. "
        "Larger SEW at a fractional LMUL may be supported or set vill (#2353, #2359: implementations may support "
        "more).",
        issues=f"{ISSUE}2353 (closed): 'the spec is stating what must be supported. It does not say that "
        "implementations must only support SEW settings within the specified range.' "
        f"{ISSUE}2359: 'Implementations are allowed, but not required, to support SEW > LMUL * ELEN.'",
        plan="ELEN = 32: LMUL 1/2 with SEW 8, 16 and LMUL 1/4 with SEW 8 leave vill = 0 (VLMAX = LMUL*VLEN/SEW). "
        "ELEN = 64: LMUL 1/2 with SEW 8, 16, 32; 1/4 with 8, 16; 1/8 with 8. One SEW above the bound per LMUL (e32 "
        "mf2 / e64 mf2 etc.) may set vill or not (not checked further).",
    )
    with t.only_if("!" + E64):
        for sew, lm in ((8, "mf2"), (16, "mf2"), (8, "mf4")):
            sew_lmul_case(t, sew, lm, True, "ELEN=32:")
        for sew, lm in ((32, "mf2"), (16, "mf4")):
            sew_lmul_case(t, sew, lm, False, "ELEN=32 above bound:", check_vlmax=False)
    with t.only_if(E64):
        for sew, lm in ((8, "mf2"), (16, "mf2"), (32, "mf2"), (8, "mf4"), (16, "mf4"), (8, "mf8")):
            sew_lmul_case(t, sew, lm, True, "ELEN=64:")
        for sew, lm in ((64, "mf2"), (32, "mf4"), (16, "mf8")):
            sew_lmul_case(t, sew, lm, False, "ELEN=64 above bound:", check_vlmax=False)
    return t


@rule
def g_lmul() -> TestFile:
    t = new("lmul")
    t.describe(
        rule_text="LMUL is set by the signed vlmul field in vtype (i.e., LMUL = 2^vlmul).",
        source=VC,
        context="vlmul 0-3 = LMUL 1-8; 7, 6, 5 = 1/2, 1/4, 1/8 (two's complement). VLMAX = LMUL*VLEN/SEW "
        "(norm:vlmax) makes LMUL visible. LMUL 1/8 is used at SEW 8 only with Zve64x (always supported there).",
        plan="SEW = 8, for each vlmul code written by vsetvl from a register (rs2 = vsew/vlmul fields): vill = 0 and "
        "vl (AVL = ~0) = VLEN*2^vlmul/8, i.e. vlenb shifted by the signed field.",
    )
    for lm, code in LMUL_CODE.items():
        cm = t.only_if(E64) if lm == "mf8" else None
        if cm:
            cm.__enter__()
        lab = mark(t)
        t.li("x6", code)
        t.emit("li x8, -1")
        t.emit(f"vsetvl x7, x8, x6  // vlmul = {code} ({lm})")
        vill_chk(t, lab, f"vlmul={code}", 0)
        if mut("lmul_unsigned") and code >= 5:
            vlmax_chk(t, "x7", 8, "m8", lab, f"vlmul={code}")
        else:
            vlmax_chk(t, "x7", 8, lm, lab, f"vlmul={code}")
        if cm:
            cm.__exit__(None, None, None)
    return t


@rule
def g_vlmax() -> TestFile:
    t = new("vlmax")
    pairs = [(8, "m1"), (16, "m4"), (32, "m8"), (8, "mf4"), (16, "mf2"), (8, "mf2"), (16, "m2"), (32, "m1")]
    p64 = [(64, "m1"), (64, "m8"), (64, "m2"), (8, "mf8"), (32, "mf2"), (16, "mf4")]
    t.describe(
        rule_text="The derived value VLMAX = LMUL*VLEN/SEW represents the maximum number of elements that can be "
        "operated on with a single vector instruction given the current SEW and LMUL settings as shown in the table "
        "below.",
        source=VC,
        context="Pairs inside the required range (norm:vtype_lmul_val, norm:vtype_sew_val; with ELEN = 32 a "
        "fractional LMUL allows SEW <= LMUL*32). VLMAX is observed as vsetvli rd, x0 (AVL = ~0, "
        "norm:vsetvl_op_rs1_x0_rd_nx0) and as the vl for AVL = 2^(XLEN-2) >= 2*VLMAX.",
        plan="For (SEW, LMUL) in "
        + ", ".join(f"e{s} {lm}" for s, lm in pairs)
        + " and, with Zve64x, "
        + ", ".join(f"e{s} {lm}" for s, lm in p64)
        + ": vsetvli rd, x0 and vsetvli with AVL = 2^(XLEN-2) both give LMUL*VLEN/SEW (from vlenb).",
    )

    def case(sew: int, lm: str) -> None:
        lab = mark(t)
        t.emit(f"vsetvli x7, x0, {vt(sew, lm)}")
        vlmax_chk(t, "x7", sew, lm, lab, f"e{sew} {lm} (rs1=x0)")
        t.load("x6", X(1 << 30, 1 << 62), "AVL = 2^(XLEN-2)")
        t.emit(f"vsetvli x7, x6, {vt(sew, lm)}")
        vlmax_chk(t, "x7", sew if not mut("vsew_ignored") else 8, lm, lab, f"e{sew} {lm} (large AVL)")

    for s, lm in pairs:
        case(s, lm)
    with t.only_if(E64):
        for s, lm in p64:
            case(s, lm)
    return t


@rule
def g_vtype_vta_vma_val() -> TestFile:
    t = new("vtype_vta_vma_val")
    t.describe(
        rule_text="All systems must support all four options: (vta, vma) = undisturbed/agnostic combinations.",
        source=VC,
        context="vtype.vta is bit 6 and vtype.vma bit 7.",
        plan="For each of tu/ta x mu/ma at e8 m1 and e32 m2, by vsetvli and by vsetvl (rs2): vill = 0 and vtype "
        "reads back exactly, including the vta/vma bits.",
    )
    for sew, lm in ((8, "m1"), (32, "m2")):
        for ta in (0, 1):
            for ma in (0, 1):
                v = vtypei(sew, lm, ta, ma)
                lab = mark(t)
                t.emit(f"vsetvli x7, x0, {vt(sew, lm, ta, ma)}")
                ev = v
                if mut("vtype_vta_vma_swapped"):
                    ev = vtypei(sew, lm, ma, ta)
                vill_chk(t, lab, f"vsetvli {vt(sew, lm, ta, ma)}", 0, ev)
                t.li("x6", v)
                t.emit("vsetvl x7, x0, x6")
                vill_chk(t, lab, f"vsetvl {hex(v)}", 0, ev)
    return t


# ======================================================================== vset* instructions
@rule
def g_vset_op() -> TestFile:
    t = new("vset_op")
    t.describe(
        rule_text="The vsetvli, vsetivli, and vsetvl instructions set the vtype and vl CSRs based on their "
        "arguments, and write the new value of vl into rd.",
        source=VC,
        context="AVL <= VLMAX gives vl = AVL (norm:vl_val_list); VLMAX(e16, m1) >= 2 for VLEN >= 32.",
        plan="vsetvli (AVL 2, e16 m1 ta mu), vsetivli (AVL 3, e8 m2 tu ma) and vsetvl (AVL 1, rs2 = e32 mf2 ta ma, "
        "only with Zve64x where e32 mf2 is required; else e32 m1): rd = vl CSR = AVL and vtype = the encoded value. "
        "rd = rs1 aliasing (vsetvli x7, x7) works too. AVL = ~0 at e16 m2: rd = vl = VLMAX (not the AVL).",
    )
    cases = [
        ("li x6, 2", "vsetvli x7, x6, e16, m1, ta, mu", 2, vtypei(16, "m1", 1, 0)),
        ("", "vsetivli x7, 3, e8, m2, tu, ma", 3, vtypei(8, "m2", 0, 1)),
        ("li x7, 2", "vsetvli x7, x7, e8, m1, ta, ma", 2, vtypei(8, "m1", 1, 1)),
    ]
    t.li("x6", -1)
    lab = mark(t)
    t.emit("vsetvli x7, x6, e16, m2, tu, mu")
    if mut("vset_rd_avl"):
        t.check("x7", -1, lab, "vsetvli AVL=~0: rd = AVL")
    else:
        vlmax_chk(t, "x7", 16, "m2", lab, "vsetvli AVL=~0: rd = vl = VLMAX")
    t.emit("csrr x8, vl")
    eq_reg(t, "x7", "x8", lab, "vsetvli AVL=~0: rd == vl")
    for pre, asm, avl, vti in cases:
        if pre:
            t.emit(pre)
        lab = mark(t)
        t.emit(asm)
        t.check("x7", avl, lab, f"{asm}: rd")
        t.emit("csrr x8, vl")
        t.check("x8", avl, lab, f"{asm}: vl")
        t.emit("csrr x8, vtype")
        t.check("x8", vti, lab, f"{asm}: vtype")
    for cond, vti in ((E64, vtypei(32, "mf2", 1, 1)), ("!" + E64, vtypei(32, "m1", 1, 1))):
        with t.only_if(cond):
            t.li("x6", 1)
            t.li("x8", vti)
            lab = mark(t)
            t.emit("vsetvl x7, x6, x8")
            t.check("x7", 1, lab, "vsetvl: rd")
            t.emit("csrr x9, vl")
            t.check("x9", 1, lab, "vsetvl: vl")
            t.emit("csrr x9, vtype")
            t.check("x9", vti, lab, "vsetvl: vtype")
    return t


@rule
def g_vtype_acc() -> TestFile:
    t = new("vtype_acc")
    t.describe(
        rule_text="The new vtype value is encoded in the immediate fields of vsetvli and vsetivli, and in the rs2 "
        "register for vsetvl.",
        source=VC,
        context="vsetvli zimm[10:0] and vsetivli zimm[9:0] hold vtype[10:0]/[9:0]; vsetvl takes all XLEN bits of "
        "x[rs2]. A wrong decode (e.g. vsetvl reading its own instruction bits, or a field shifted) changes vtype.",
        plan="1. vsetvli and vsetivli with each field set alone (vlmul 2, vsew 1 (e16), vta, vma) and with all of "
        "them: vtype reads the immediate.\n"
        "2. vsetvl x7, x6, x8 with x8 = e16 m4 ta ma and x8 = e8 m1 tu mu: vtype reads x8, not the instruction's own "
        "rs2 field bits.",
    )
    for vti in (
        vtypei(8, "m4"),
        vtypei(16, "m1"),
        vtypei(8, "m1", 1, 0),
        vtypei(8, "m1", 0, 1),
        vtypei(16, "m4", 1, 1),
    ):
        lab = mark(t)
        t.emit(f"vsetvli x7, x0, {hex(vti)}")
        t.emit("csrr x8, vtype")
        t.check("x8", vti, lab, f"vsetvli zimm {hex(vti)}")
        lab = mark(t)
        t.emit(f"vsetivli x7, 1, {hex(vti)}")
        t.emit("csrr x8, vtype")
        t.check("x8", vti, lab, f"vsetivli zimm {hex(vti)}")
    for vti in (vtypei(16, "m4", 1, 1), vtypei(8, "m1")):
        t.li("x8", vti)
        t.li("x6", 1)
        lab = mark(t)
        t.emit("vsetvl x7, x6, x8")
        t.emit("csrr x9, vtype")
        exp = vti
        if mut("vsetvl_imm_vtype"):
            exp = 8  # instruction bits 30:20 hold the rs2 field, x8
        t.check("x9", exp, lab, f"vsetvl rs2 = {hex(vti)}")
    return t


@rule
def g_vset_vstart() -> TestFile:
    t = new("vset_vstart")
    t.describe(
        rule_text="The configuration-setting instructions do not depend on vstart; they reset vstart to zero.",
        source=VC,
        issues=f"{ISSUE}3408 (closed): 'the clause that allows trapping certain vector instructions on nonzero vstart "
        "was meant to apply to vector computation and memory-access instructions, not to the vset instructions'; the "
        "intent 'was that configuration instructions ignore vstart and reset vstart to zero' (added as this rule by "
        "#3412).",
        plan="Under e8 m8 (so VLEN-1 is an element index), for vsetvli, vsetivli and vsetvl, with vstart = 2 and with "
        "vstart = VLEN-1: no trap (the trap log fails "
        "the test on any trap), vstart reads 0 afterwards, and vl = AVL = 3 as with vstart = 0.",
    )
    t.emit("csrr x9, vlenb")
    t.emit("slli x9, x9, 3")
    t.emit("addi x9, x9, -1  // VLEN-1")
    t.li("x6", 3)
    t.li("x8", vtypei(8, "m1"))
    for vs_src, d in (("li x1, 2", "2"), ("mv x1, x9", "VLEN-1")):
        for asm in ("vsetvli x7, x6, e8, m1, tu, mu", "vsetivli x7, 3, e8, m1, tu, mu", "vsetvl x7, x6, x8"):
            t.emit("vsetvli x1, x0, e8, m8, tu, mu  // VLMAX = VLEN")
            t.emit(vs_src)
            t.emit("csrw vstart, x1")
            if mut("vset_vstart_traps"):
                vwin(t, [asm], ILLEGAL, f"{asm} with vstart={d}")
                t.emit("csrw vstart, x0")
                continue
            lab = mark(t)
            t.emit(asm)
            t.emit("csrr x1, vstart")
            if mut("vset_keeps_vstart"):
                t.check("x1", 2 if d == "2" else 0, lab, f"{asm} with vstart={d}: vstart")
            else:
                t.check("x1", 0, lab, f"{asm} with vstart={d}: vstart reset to 0")
            t.check("x7", 3, lab, f"{asm} with vstart={d}: vl")
    t.emit("csrw vstart, x0")
    return t


def avl_case(t: TestFile, asm: str, lab: str, d: str, exp: str) -> None:
    """exp: 'vlmax' (VLMAX(e8, m1) = vlenb) or an int."""
    if exp == "vlmax":
        t.emit("csrr x9, vlenb")
        eq_reg(t, "x7", "x9", lab, f"{d}: vl = VLMAX", tmp="x1")
    else:
        t.check("x7", int(exp), lab, f"{d}: vl")


@rule
def g_vsetvl_op() -> TestFile:
    t = new("vsetvl_op")
    t.describe(
        rule_text="When rs1 is not x0, the AVL is an unsigned integer held in the x register specified by rs1, and the "
        "new vl value is also written to the x register specified by rd.",
        source=VC,
        context="vl = AVL when AVL <= VLMAX and vl = VLMAX when AVL >= 2*VLMAX (norm:vl_val_list). VLMAX(e8, m1) = "
        "vlenb. Unsigned: AVL = -1 or 2^(XLEN-1) is huge (>= 2*VLMAX). On RV64, AVL = 2^32 and 2^32+1 are huge too "
        "(a 32-bit AVL would give 0 or 1).",
        plan="e8 m1, with vsetvli and vsetvl: AVL 0 -> 0, 1 -> 1, VLMAX -> VLMAX, all ones -> VLMAX, 2^(XLEN-1) -> "
        "VLMAX, 2^(XLEN-1)-1 -> VLMAX, RV64 2^32 -> VLMAX and 2^32+1 -> VLMAX; rd and vl agree. rd = x0 with rs1 != x0 "
        "still sets vl (AVL 2 -> vl 2).",
    )
    t.li("x8", vtypei(8, "m1"))
    cases: list[tuple[str, str, str, str | None]] = [
        ("li x6, 0", "0", "0", None),
        ("li x6, 1", "1", "1", None),
        ("csrr x6, vlenb", "VLMAX", "vlmax", None),
        ("li x6, -1", "~0", "vlmax", "avl_signed"),
    ]
    for setsrc, d, exp, mname in cases:
        for asm in ("vsetvli x7, x6, e8, m1, tu, mu", "vsetvl x7, x6, x8"):
            t.emit(setsrc)
            lab = mark(t)
            t.emit(asm)
            e = exp
            if mname and mut(mname):
                e = "0"
            avl_case(t, asm, lab, f"{asm} AVL={d}", e)
            t.emit("csrr x9, vl")
            eq_reg(t, "x7", "x9", lab, f"{asm} AVL={d}: rd == vl", tmp="x1")
    for val, d, mname in (
        (X(1 << 31, 1 << 63), "2^(XLEN-1)", "avl_signed"),
        (X((1 << 31) - 1, (1 << 63) - 1), "2^(XLEN-1)-1", None),
    ):
        t.load("x6", val, d)
        lab = mark(t)
        t.emit("vsetvli x7, x6, e8, m1, tu, mu")
        avl_case(t, "", lab, f"vsetvli AVL={d}", "0" if (mname and mut(mname)) else "vlmax")
    with t.rv64_only():
        for val, d, trunc in ((1 << 32, "2^32", 0), ((1 << 32) + 1, "2^32+1", 1)):
            t.load("x6", X(0, val), d)
            lab = mark(t)
            t.emit("vsetvli x7, x6, e8, m1, tu, mu")
            avl_case(t, "", lab, f"vsetvli AVL={d}", str(trunc) if mut("avl_32bit") else "vlmax")
            t.emit("vsetvl x7, x6, x8")
            avl_case(t, "", lab, f"vsetvl AVL={d}", str(trunc) if mut("avl_32bit") else "vlmax")
    t.li("x6", 2)
    lab = mark(t)
    t.emit("vsetvli x0, x6, e8, m1, tu, mu")
    t.emit("csrr x7, vl")
    t.check("x7", 2, lab, "rd=x0, rs1 != x0: vl = AVL = 2")
    return t


@rule
def g_vsetvl_op_rs1_x0_rd_nx0() -> TestFile:
    t = new("vsetvl_op_rs1_x0_rd_nx0")
    t.describe(
        rule_text="When rs1=x0 but rd!=x0, the maximum unsigned integer value (~0) is used as the AVL, and the "
        "resulting VLMAX is written to vl and also to the x register specified by rd.",
        source=VC,
        context="~0 >= 2*VLMAX, so vl = VLMAX exactly. The form is legal from any previous state, including vill = 1.",
        plan="From vl = 1 each time: vsetvli rd, x0 at e8 m2, e32 m1, e16 mf2 and vsetvl rd, x0, rs2 (e8 m4): rd = "
        "vl = LMUL*VLEN/SEW. From vill = 1 (vsetvl with rs2 = vill bit): vsetvli rd, x0, e8, m1 gives VLMAX and "
        "vill = 0.",
    )
    for asm, sew, lm in (
        ("vsetvli x7, x0, e8, m2, tu, mu", 8, "m2"),
        ("vsetvli x7, x0, e32, m1, tu, mu", 32, "m1"),
        ("vsetvli x7, x0, e16, mf2, tu, mu", 16, "mf2"),
        ("vsetvl x7, x0, x8", 8, "m4"),
    ):
        vset(t, "x0", 1, 8, "m1")
        t.li("x8", vtypei(8, "m4"))
        lab = mark(t)
        t.emit(asm)
        if mut("rs1x0_keeps_vl"):
            t.check("x7", 1, lab, f"{asm}: rd")
            continue
        vlmax_chk(t, "x7", sew, lm, lab, f"{asm}: rd")
        t.emit("csrr x8, vl")
        vlmax_chk(t, "x8", sew, lm, lab, f"{asm}: vl")
    t.load("x8", VILL, "vill")
    t.li("x6", 1)
    t.emit("vsetvl x0, x6, x8  // vill = 1, vl = 0 (rs1 != x0: not the reserved keep-vl form)")
    lab = mark(t)
    t.emit("vsetvli x7, x0, e8, m1, tu, mu")
    vlmax_chk(t, "x7", 8, "m1", lab, "from vill=1: rd")
    vill_chk(t, lab, "from vill=1", 0, vtypei(8, "m1"))
    return t


@rule
def g_vsetvl_op_rs1_x0_rd_x0() -> TestFile:
    t = new("vsetvl_op_rs1_x0_rd_x0")
    t.describe(
        rule_text="When rs1=x0 and rd=x0, the instructions operate as if the current vector length in vl is used as "
        "the AVL, and the resulting value is written to vl, but not to a destination register. This form can only be "
        "used when VLMAX and hence vl is not actually changed by the new SEW/LMUL ratio.",
        source=VC,
        context="Only ratio-preserving changes are used (others are reserved, norm:vtype_vset_rsv), from vill = 0.",
        plan="1. vl = 3 at e8 m1: vsetvli x0, x0, e16, m2 keeps vl = 3 and sets vtype = e16 m2; vsetvl x0, x0, rs2 = "
        "e32 m4 ta keeps vl = 3; vsetvli x0, x0, e8, m1, ta, ma keeps 3.\n"
        "2. vl = VLMAX(e8, m1): vsetvli x0, x0, e16, m2 keeps vl = VLMAX.",
    )
    vset(t, "x0", 3, 8, "m1")
    for asm, vti in (
        ("vsetvli x0, x0, e16, m2, tu, mu", vtypei(16, "m2")),
        ("vsetvl x0, x0, x8", vtypei(32, "m4", 1, 0)),
        ("vsetvli x0, x0, e8, m1, ta, ma", vtypei(8, "m1", 1, 1)),
    ):
        t.li("x8", vtypei(32, "m4", 1, 0))
        lab = mark(t)
        t.emit(asm)
        t.emit("csrr x7, vl")
        if mut("keep_vl_uses_vlmax"):
            vlmax_chk(t, "x7", 8, "m1", lab, f"{asm}: vl")
        else:
            t.check("x7", 3, lab, f"{asm}: vl kept")
        t.emit("csrr x7, vtype")
        t.check("x7", vti, lab, f"{asm}: vtype")
    vset_max(t, 8, "m1")
    lab = mark(t)
    t.emit("vsetvli x0, x0, e16, m2, tu, mu")
    t.emit("csrr x7, vl")
    vlmax_chk(t, "x7", 8, "m1", lab, "vl = VLMAX kept")
    return t


@rule
def g_vsetivli_op() -> TestFile:
    t = new("vsetivli_op")
    t.describe(
        rule_text="For the vsetivli instruction, the AVL is encoded as a 5-bit zero-extended immediate (0--31) in "
        "the rs1 field.",
        source=VC,
        context="At e8 m8 VLMAX = VLEN >= 32, so every AVL 0-31 gives vl = AVL. A sign-extended immediate would give "
        "AVL = -16..-1 (huge, vl = VLMAX) for 16-31.",
        plan="e8 m8: vsetivli with uimm 0, 1, 15, 16, 17, 30, 31: rd = vl = uimm.",
    )
    for u in (0, 1, 15, 16, 17, 30, 31):
        lab = mark(t)
        t.emit(f"vsetivli x7, {u}, e8, m8, tu, mu")
        if mut("vsetivli_sext") and u >= 16:
            vlmax_chk(t, "x7", 8, "m8", lab, f"vsetivli {u}")
        else:
            t.check("x7", u, lab, f"vsetivli uimm={u}: rd")
        t.emit("csrr x8, vl")
        eq_reg(t, "x7", "x8", lab, f"vsetivli uimm={u}: vl == rd")
    return t


@rule
def g_vl_val_lead_in() -> TestFile:
    t = new("vl_val_lead_in")
    t.describe(
        rule_text="The vset* instructions first set VLMAX according to their vtype argument, then set vl obeying the "
        "following constraints:",
        source=VC,
        context="The constraints are norm:vl_val_list. Using the old VLMAX would give a vl above the new VLMAX.",
        plan="1. From e8 m8 with vl = VLEN: vsetvli with AVL = VLEN (old vl, >= 2*new VLMAX) at e32 m1 gives vl = "
        "VLEN/32; vsetvl with the same AVL and rs2 = e16 m2 gives VLEN/8.\n"
        "2. From e32 m1 (VLMAX VLEN/32), vsetivli 31 at e8 m8 gives 31 (the new, larger VLMAX = VLEN >= 32).",
    )
    vset_max(t, 8, "m8", rd="x6")
    lab = mark(t)
    t.emit("vsetvli x7, x6, e32, m1, tu, mu")
    vlmax_chk(t, "x7", 32, "m1", lab, "AVL = VLEN at e32 m1")
    if mut("vl_old_vlmax"):
        eq_reg(t, "x7", "x6", lab, "old VLMAX bound")
    vset_max(t, 8, "m8", rd="x6")
    t.li("x8", vtypei(16, "m2"))
    lab = mark(t)
    t.emit("vsetvl x7, x6, x8")
    vlmax_chk(t, "x7", 16, "m2", lab, "AVL = VLEN, vsetvl e16 m2")
    vset_max(t, 32, "m1")
    lab = mark(t)
    t.emit("vsetivli x7, 31, e8, m8, tu, mu")
    t.check("x7", 31, lab, "vsetivli 31 at e8 m8 from e32 m1")
    return t


def vl_pred(t: TestFile, avl: str, vl: str, vlmax_r: str, lab: str, d: str) -> None:
    """Check ceil(AVL/2) <= vl <= VLMAX (and vl <= AVL, vl > 0)."""
    t.emit(f"addi x1, {avl}, 1")
    t.emit("srli x1, x1, 1  // ceil(AVL/2)")
    t.emit(f"sltu x1, {vl}, x1  // vl < ceil(AVL/2)")
    t.emit(f"sltu x5, {vlmax_r}, {vl}  // vl > VLMAX")
    t.emit("or x1, x1, x5")
    t.emit(f"sltu x5, {avl}, {vl}  // vl > AVL")
    t.emit("or x1, x1, x5")
    t.emit(f"seqz x5, {vl}")
    t.emit("or x1, x1, x5")
    t.emit("seqz x1, x1")
    t.check_bool("x1", lab, f"{d}: ceil(AVL/2) <= vl <= VLMAX, 0 < vl <= AVL")


@rule
def g_vl_val_list() -> TestFile:
    t = new("vl_val_list")
    t.describe(
        rule_text=". vl = AVL if AVL <= VLMAX . ceil(AVL / 2) <= vl <= VLMAX if AVL < (2 * VLMAX) . vl = VLMAX if "
        "AVL >= (2 * VLMAX) . Deterministic on any given implementation for same input AVL and VLMAX values . These "
        "specific properties follow from the prior rules: .. vl = 0 if AVL = 0 .. vl > 0 if AVL > 0 .. vl <= VLMAX "
        ".. vl <= AVL .. a value read from vl when used as the AVL argument to vset* results in the same value in "
        "vl, provided the resultant VLMAX equals the value of VLMAX at the time that vl was read",
        source=VC,
        context="VLMAX is read with vsetvli rd, x0. For AVL = 2*VLMAX-1, ceil(AVL/2) = VLMAX, so vl = VLMAX exactly.",
        plan="At e8 m1 and at e32 m2 (VLMAX = V): AVL 0 -> 0; 1 -> 1; V-1 -> V-1; V -> V; V+1 and 3V/2 -> ceil(AVL/2) "
        "<= vl <= V (and 0 < vl <= AVL); 2V-1 -> V; 2V -> V; 2V+1 -> V; ~0 -> V. For V+1 and 3V/2 the same AVL again gives "
        "the same vl, and vl read back as AVL gives the same vl again.",
    )
    for sew, lm in ((8, "m1"), (32, "m2")):
        t.emit(f"vsetvli x8, x0, {vt(sew, lm)}  // x8 = VLMAX")
        exacts = [
            ("li x6, 0", "0", "li x9, 0"),
            ("li x6, 1", "1", "li x9, 1"),
            ("addi x6, x8, -1", "V-1", "addi x9, x8, -1"),
            ("mv x6, x8", "V", "mv x9, x8"),
            ("slli x6, x8, 1\n  addi x6, x6, -1", "2V-1", "mv x9, x8"),
            ("slli x6, x8, 1", "2V", "mv x9, x8"),
            ("slli x6, x8, 1\n  addi x6, x6, 1", "2V+1", "mv x9, x8"),
            ("li x6, -1", "~0", "mv x9, x8"),
        ]
        for setsrc, d, exp in exacts:
            for ln in setsrc.split("\n"):
                t.emit(ln.strip())
            lab = mark(t)
            t.emit(f"vsetvli x7, x6, {vt(sew, lm)}")
            t.emit(exp)
            eq_reg(t, "x7", "x9", lab, f"e{sew} {lm} AVL={d}", tmp="x1")
        for setsrc, d in (("addi x6, x8, 1", "V+1"), ("srli x6, x8, 1\n  add x6, x6, x8", "3V/2")):
            for ln in setsrc.split("\n"):
                t.emit(ln.strip())
            lab = mark(t)
            t.emit(f"vsetvli x7, x6, {vt(sew, lm)}")
            if mut("vl_no_clamp"):
                eq_reg(t, "x7", "x6", lab, f"AVL={d}: vl = AVL")
                continue
            vl_pred(t, "x6", "x7", "x8", lab, f"e{sew} {lm} AVL={d}")
            t.emit(f"vsetvli x9, x6, {vt(sew, lm)}")
            eq_reg(t, "x7", "x9", lab, f"AVL={d} again: same vl (deterministic)", tmp="x1")
            t.emit("csrr x9, vl")
            t.emit(f"vsetvli x9, x9, {vt(sew, lm)}")
            eq_reg(t, "x7", "x9", lab, f"AVL={d}: vl reused as AVL gives the same vl", tmp="x1")
    return t


# ======================================================================== vill
def vill_case(t: TestFile, asm: str, d: str, pre: list[str] | None = None) -> None:
    """Run asm (writes x7 = new vl) from a valid vl = 3 state: vtype = vill only, vl = 0, rd = 0."""
    vset(t, "x0", 3, 8, "m1")
    for ln in pre or []:
        t.emit(ln)
    lab = mark(t)
    t.emit(asm)
    t.emit("csrr x8, vtype")
    exp_vt: object = VILL
    if mut("reserved_bits_ignored") and "reserved" in d:
        exp_vt = "nochk"
    if mut("vill_bit_ignored") and "vill bit" in d:
        exp_vt = "nochk"
    if exp_vt == "nochk":
        t.emit("slt x8, x8, x0")
        t.check("x8", 0, lab, f"{d}: vill")
        return
    if mut("vill_keeps_vtype"):
        t.check("x8", X((1 << 31) | 1, (1 << 63) | 1), lab, f"{d}: vtype keeps its other bits")
        return
    t.check("x8", VILL, lab, f"{d}: vtype = vill only (other bits 0)")
    t.emit("csrr x8, vl")
    t.check("x8", 0 if not mut("vill_keeps_vl") else 3, lab, f"{d}: vl = 0")
    t.check("x7", 0 if not mut("vill_keeps_vl") else 3, lab, f"{d}: rd = 0")


@rule
def g_vtype_vill_val() -> TestFile:
    t = new("vtype_vill_val")
    t.describe(
        rule_text="If the vtype value is not supported by the implementation, then the vill bit is set in vtype, the "
        "remaining bits in vtype are set to zero",
        source=VC,
        context="vsew = 4-7 (SEW >= 128) and vlmul = 4 are reserved encodings no standard implementation supports. "
        "When vill is set, the other XLEN-1 bits of vtype are zero (Vector Type Illegal section). vl = 0 is "
        "norm:vtype_vstart_op.",
        plan="From vl = 3, e8 m1: vsetvli with vsew = 4 (immediate 0x20), vsetivli with vlmul = 4 (0x04) and vsetvl "
        "with rs2 = vsew 5 + ta ma (0xe8): vtype reads exactly the vill bit, and vl and rd are 0.",
    )
    t.li("x6", 16)
    vill_case(t, "vsetvli x7, x6, 0x20", "vsetvli vsew=4")
    vill_case(t, "vsetivli x7, 7, 0x04", "vsetivli vlmul=4")
    vill_case(t, "vsetvl x7, x6, x8", "vsetvl vsew=5 ta ma", ["li x8, 0xe8", "li x6, 16"])
    return t


@rule
def g_vtype_vstart_op() -> TestFile:
    t = new("vtype_vstart_op")
    t.describe(
        rule_text="the vl register is also set to zero.",
        source=VC,
        context="Continuation of norm:vtype_vill_val: when a vset* writes an unsupported vtype, vl is set to 0. The new "
        "vl is also what vset* writes to rd (norm:vset_op).",
        plan="From vl = 3 (e8 m1), for AVL = 5 (vsetvli and vsetivli), AVL = ~0 (vsetvl) and rs1 = x0, rd != x0: an "
        "unsupported vtype (vsew = 7, vlmul = 4, vill bit) makes vl = 0 and rd = 0.",
    )
    t.li("x6", 5)
    vill_case(t, "vsetvli x7, x6, 0x38", "vsetvli AVL=5 vsew=7")
    vill_case(t, "vsetivli x7, 5, 0x04", "vsetivli AVL=5 vlmul=4")
    t.load("x8", VILL, "vill")
    vill_case(t, "vsetvl x7, x6, x8", "vsetvl AVL=~0 vill bit", ["li x6, -1"])
    vill_case(t, "vsetvli x7, x0, 0x3b", "vsetvli rs1=x0 vsew=7 m8")
    return t


@rule
def g_vtype_vill_val_vill() -> TestFile:
    t = new("vtype_vill_val_vill")
    t.describe(
        rule_text="A vtype value with vill set is treated as an unsupported configuration.",
        source=VC,
        context="Unsupported configurations set vill, clear the other bits and set vl = 0 (norm:vtype_vill_val).",
        plan="vsetvl from vl = 3 with rs2 = vill | (e8 m1), vill | (e16 m2 ta ma) and vill alone: vtype = vill only, "
        "vl = rd = 0.",
    )
    for low, d in ((vtypei(8, "m1"), "e8 m1"), (vtypei(16, "m2", 1, 1), "e16 m2 ta ma"), (0, "alone")):
        t.load("x8", X((1 << 31) | low, (1 << 63) | low), f"vill | {d}")
        vill_case(t, "vsetvl x7, x6, x8", f"vsetvl vill bit with {d}", ["li x6, 4"])
    return t


@rule
def g_vtype_vill_all_bits() -> TestFile:
    t = new("vtype_vill_all_bits")
    bits32 = [9, 10, 15, 16, 23, 30]
    bits64 = [31, 32, 47, 62]
    t.describe(
        rule_text="Implementations must consider all bits of the vtype value to determine if the configuration is "
        "supported. An unsupported value in any location within the vtype value must result in vill being set.",
        source=VC,
        context="Bits XLEN-2:8 are reserved when nonzero (norm:vtype_fields_sz), so a standard implementation does not "
        "support them; vsew = 4-7 and vlmul = 4 are reserved encodings; SEW = 64 is unsupported without Zve64x "
        "(ELEN = 32). Bit 8 is vtype.altfmt in the Zvfbfa extension (not in the ratified manual), so it is tested only "
        "when Zvfbfa is not implemented.",
        plan="From vl = 3, e8 m1, vsetvl with rs2 = e8 m1 plus one reserved bit: bit 8 (without Zvfbfa), "
        + ", ".join(map(str, bits32))
        + " (and on RV64 "
        + ", ".join(map(str, bits64))
        + "); vsew = 4, 5, 6, 7; vlmul = 4; vsetvli immediates with bit 8 (without Zvfbfa), 9 or 10 set; vsetivli "
        "with bit 9 set; without Zve64x, SEW = 64: each gives vtype = vill only, vl = rd = 0.",
    )
    t.li("x6", 4)
    with t.only_if(NO_ALTFMT):
        t.li("x8", 1 << 8)
        vill_case(t, "vsetvl x7, x6, x8", "reserved bit 8", ["li x6, 4"])
        vill_case(t, "vsetvli x7, x6, 0x100", "vsetvli reserved bit 8", ["li x6, 4"])
    for b in bits32:
        t.li("x8", 1 << b)
        vill_case(t, "vsetvl x7, x6, x8", f"reserved bit {b}", ["li x6, 4"])
    with t.rv64_only():
        for b in bits64:
            t.load("x8", X(0, 1 << b), f"bit {b}")
            vill_case(t, "vsetvl x7, x6, x8", f"reserved bit {b}", ["li x6, 4"])
    for vsew in (4, 5, 6, 7):
        t.li("x8", vsew << 3)
        vill_case(t, "vsetvl x7, x6, x8", f"vsew={vsew}", ["li x6, 4"])
    t.li("x8", 4)
    vill_case(t, "vsetvl x7, x6, x8", "vlmul=4", ["li x6, 4"])
    for b in (9, 10):
        vill_case(t, f"vsetvli x7, x6, {hex(1 << b)}", f"vsetvli reserved bit {b}", ["li x6, 4"])
    vill_case(t, f"vsetivli x7, 4, {hex(1 << 9)}", "vsetivli reserved bit 9")
    with t.only_if("!" + E64):
        vill_case(t, "vsetvli x7, x6, e64, m1, tu, mu", "SEW=64 without Zve64x", ["li x6, 4"])
    return t


@rule
def g_vtype_vill_op() -> TestFile:
    t = new("vtype_vill_op")
    t.describe(
        rule_text="If the vill bit is set, then any attempt to execute a vector instruction that depends upon vtype "
        "will raise an illegal-instruction exception.",
        source=VC,
        context="NOTE in the spec: vset* and whole register loads and stores do not depend upon vtype; vlm.v/vsm.v "
        "respect vill (they depend on vl). xtval of the trap is 0 or the instruction bits.",
        issues=f"{ISSUE}3067 (closed): 'By omission, whole register loads/stores mustn't trap when vill=1' "
        "(aswaterman); 'these instructions should not cause an illegal instruction trap when vill=1, but they might "
        "trap for other reasons' (kasanovic). Whether vmv<nr>r.v depends on vtype was left open in that thread, so it "
        "may trap or execute.",
        plan="vill = 1 (vsetvl rs2 = vill bit). Illegal-instruction: vadd.vv, vadd.vi, vle8.v, vse8.v, vlm.v, vsm.v, "
        "vmv.x.s, vmv.s.x, vmv.v.x, vmseq.vv, vredsum.vs, vcpop.m, vid.v, vsext.vf2. Allowed: vl1re8.v, vs1r.v, vl2re8.v "
        "(no trap); vmv1r.v may trap or not. Then vsetivli clears vill and vadd.vv executes.",
    )
    t.load("x8", VILL, "vill")
    t.li("x6", 1)
    t.emit("vsetvl x0, x6, x8  // vill = 1 (rs1 != x0: not the reserved keep-vl form)")
    t.la("x6", BUF)
    traps = [
        "vadd.vv v1, v2, v3",
        "vadd.vi v1, v2, 1",
        "vle8.v v1, (x6)",
        "vse8.v v1, (x6)",
        "vlm.v v1, (x6)",
        "vsm.v v1, (x6)",
        "vmv.x.s x7, v1",
        "vmv.s.x v1, x7",
        "vmv.v.x v1, x7",
        "vmseq.vv v1, v2, v3",
        "vredsum.vs v1, v2, v3",
        "vcpop.m x7, v1",
        "vid.v v1",
        "vsext.vf2 v1, v2",
    ]
    for asm in traps:
        vwin(t, [asm], ILLEGAL if not (mut("vill_vadd_ok") and asm.startswith("vadd")) else "ok", f"{asm} with vill=1")
    for asm in ("vl1re8.v v1, (x6)", "vs1r.v v1, (x6)", "vl2re8.v v2, (x6)"):
        vwin(t, [asm], "ok" if not mut("vill_whole_reg_traps") else ILLEGAL, f"{asm} with vill=1")
    vwin(t, ["vmv1r.v v1, v2"], ["ok", ILLEGAL], "vmv1r.v with vill=1")
    vset(t, "x0", 1, 8, "m1")
    vwin(t, ["vadd.vv v1, v2, v3"], "ok", "vadd.vv after vsetivli cleared vill")
    return t


# ======================================================================== element mapping
@rule
def g_vreg_lmul1_op() -> TestFile:
    t = new("vreg_lmul1_op")
    t.describe(
        rule_text="When LMUL=1, elements are simply packed in order from the least-significant to most-significant "
        "bits of the vector register.",
        source=VC,
        context="A whole-register store writes the register's bytes in order (byte k = bits 8k+7:8k), so element i of "
        "SEW bits occupies bytes i*SEW/8 .. (i+1)*SEW/8-1, little-endian.",
        plan="For SEW 8, 16, 32 (and 64 with Zve64x) at LMUL = 1: vid.v + 0x0100 (so elements are wider than a "
        "byte where SEW >= 16), vs1r.v: the low bytes of elements 0 and (SEW <= 16) 1 are at bytes 0 and SEW/8, "
        "and the last element (VLMAX-1) is at byte vlenb - SEW/8.",
    )
    for sew in (8, 16, 32, 64):
        cm = t.only_if(E64) if sew == 64 else None
        if cm:
            cm.__enter__()
        add = 0x100 if sew > 8 else 0x10
        iota(t, "v4", sew, "m1", add)
        store(t, "v4")
        nb = sew // 8
        for i in range(2 if sew <= 16 else 1):  # VLMAX(e32/e64, m1) may be 1
            v = i + add
            if mut("pack_msb_first"):
                v = (1 - i) + add
            lab = mark(t)
            ld_elem(t, "x7", 8, i * nb)
            t.check("x7", v & 0xFF, lab, f"e{sew}: byte {i * nb} = low byte of element {i}")
            if sew > 8:
                ld_elem(t, "x7", 8, i * nb + 1)
                t.check("x7", (v >> 8) & 0xFF, lab, f"e{sew}: byte {i * nb + 1} = byte 1 of element {i}")
        lab = mark(t)
        t.emit("csrr x8, vlenb")
        t.emit(f"addi x8, x8, -{nb}")
        ld_elem(t, "x7", 16 if sew > 8 else 8, "x8")
        vlmax(t, "x9", sew, "m1")
        t.emit(f"addi x9, x9, {add - 1}")
        t.li("x1", 0xFFFF if sew > 8 else 0xFF)
        t.emit("and x9, x9, x1")
        eq_reg(t, "x7", "x9", lab, f"e{sew}: last element (VLMAX-1) at the top of the register", tmp="x1")
        if cm:
            cm.__exit__(None, None, None)
    return t


@rule
def g_vreg_lmulge2_op() -> TestFile:
    t = new("vreg_lmulge2_op")
    t.describe(
        rule_text="When vector registers are grouped, the elements of the vector register group are packed "
        "contiguously in element order beginning with the lowest-numbered vector register and moving to the "
        "next-highest-numbered vector register in the group once each vector register is filled.",
        source=VC,
        context="Each register holds VLEN/SEW elements, so register v(n+j) of a group starts with element j*VLEN/SEW.",
        plan="e16: vid.v at LMUL 2 (v8-v9), 4 (v8-v11) and 8 (v8-v15) at VLMAX. Register v(8+j) starts with element "
        "j*vlenb/2 and ends with (j+1)*vlenb/2 - 1, for j = 0, 1 and the last register of each group.",
    )
    for lm, n in (("m2", 2), ("m4", 4), ("m8", 8)):
        iota(t, "v8", 16, lm)
        for j in sorted({0, 1, n - 1}):
            store(t, f"v{8 + j}")
            lab = mark(t)
            ld_elem(t, "x7", 16, 0)
            t.emit("csrr x8, vlenb")
            t.emit("srli x8, x8, 1  // elements per register")
            t.emit("li x9, 0")
            for _ in range(j):
                t.emit("add x9, x9, x8  // x9 = j * elements per register")
            if mut("group_interleaved"):
                t.emit(f"li x9, {j}")
            eq_reg(t, "x7", "x9", lab, f"{lm}: v{8 + j} element 0 = {j}*VLEN/16", tmp="x1")
            t.emit("csrr x8, vlenb")
            t.emit("addi x8, x8, -2")
            ld_elem(t, "x7", 16, "x8")
            t.emit("csrr x8, vlenb")
            t.emit("srli x8, x8, 1")
            t.emit("add x9, x9, x8")
            t.emit("addi x9, x9, -1")
            eq_reg(t, "x7", "x9", lab, f"{lm}: v{8 + j} last element = ({j}+1)*VLEN/16 - 1", tmp="x1")
    return t


@rule
def g_vreg_flmul_op() -> TestFile:
    t = new("vreg_flmul_op")
    t.describe(
        rule_text="When LMUL < 1, only the first LMUL*VLEN/SEW elements in the vector register are used. The "
        "remaining space in the vector register is treated as part of the tail, and hence must obey the vta "
        "setting.",
        source=VC,
        context="Tail-undisturbed keeps those bytes; tail-agnostic may keep them or write all 1s, per element "
        "(norm:vreg_agnostic_op).",
        plan="v4 = 0xA5 bytes. e8 mf2 (VLMAX = vlenb/2) tu, vl = VLMAX: vadd.vi v4, v2, 1 (v2 = iota) writes bytes "
        "0..vlenb/2-1; bytes vlenb/2 and vlenb-1 keep 0xA5. The same with ta: those bytes are 0xA5 or 0xFF. e8 mf4: "
        "byte vlenb/4 likewise. Body bytes 0 and VLMAX-1 hold their results.",
    )
    for lm, sh in (("mf2", 1), ("mf4", 2)):
        for ta in (0, 1):
            iota(t, "v2", 8, "m1")
            fill(t, "v4", 0xA5)
            t.emit(f"vsetvli x7, x0, {vt(8, lm, ta, 0)}")
            lab = mark(t)
            t.emit("vadd.vi v4, v2, 1")
            store(t, "v4")
            ld_elem(t, "x8", 8, 0)
            t.check("x8", 1, lab, f"{lm}: body element 0")
            t.emit("addi x9, x7, -1")
            ld_elem(t, "x8", 8, "x9")
            t.emit("andi x9, x7, 0xff")  # element VLMAX-1 + 1 = VLMAX
            eq_reg(t, "x8", "x9", lab, f"{lm}: body element VLMAX-1 = VLMAX (mod 256)", tmp="x1")
            t.emit("csrr x9, vlenb")
            t.emit(f"srli x9, x9, {sh}")
            ld_elem(t, "x8", 8, "x9")
            exp_ta = ta
            if ta == 0 and not mut("flmul_tail_written"):
                t.check("x8", 0xA5, lab, f"{lm} tu: byte VLMAX (past VLMAX in the register) kept")
            elif ta == 0:
                t.emit("andi x9, x9, 0xff")
                t.emit("addi x9, x9, 1")
                eq_reg(t, "x8", "x9", lab, "tail written")
            else:
                check_agn(t, "x8", 0xA5, 8, lab, f"{lm} ta: byte VLMAX")
            t.emit("csrr x9, vlenb")
            t.emit("addi x9, x9, -1")
            ld_elem(t, "x8", 8, "x9")
            if exp_ta:
                check_agn(t, "x8", 0xA5, 8, lab, f"{lm} ta: last byte")
            else:
                t.check("x8", 0xA5, lab, f"{lm} tu: last byte kept")
    return t


def mask_setup(t: TestFile, sew: int, lm: str) -> None:
    """v16.. group = vid at (sew, lm), VLMAX."""
    iota(t, "v16", sew, lm)


@rule
def g_vreg_mask_lmul_indp() -> TestFile:
    t = new("vreg_mask_lmul_indp")
    t.describe(
        rule_text="Mask registers are always contained in a single vector register, regardless of LMUL.",
        source=VC,
        context="A mask has one bit per element (norm:vreg_mask_sz); VLMAX <= VLEN at SEW >= 8, LMUL <= 8, so it fits "
        "one register. The destination of a compare is a single register even when it is not a group-aligned "
        "number.",
        plan="e8, LMUL 2, 4, 8 at VLMAX: v1 and v2 = 0xA5 bytes; vmseq.vx v1, v16 (group), x6 with x6 = 3 sets only "
        "bit 3 of the body: byte 0 = 0x08 (VLMAX >= 8); at LMUL 8 (VLMAX = VLEN, no tail bits) the last byte is 0; "
        "v2 keeps 0xA5 (the mask is not a group).",
    )
    for lm in ("m2", "m4", "m8"):
        mask_setup(t, 8, lm)
        fill(t, "v1", 0xA5)
        fill(t, "v2", 0xA5)
        vset_max(t, 8, lm)
        t.li("x6", 3)
        lab = mark(t)
        t.emit("vmseq.vx v1, v16, x6")
        store(t, "v1")
        ld_elem(t, "x7", 8, 0)
        t.check("x7", 0x08, lab, f"{lm}: mask byte 0 (bit 3 only)")
        if lm == "m8":
            t.emit("csrr x9, vlenb")
            t.emit("addi x9, x9, -1")
            ld_elem(t, "x7", 8, "x9")
            t.check("x7", 0, lab, f"{lm}: mask last byte (body)")
        store(t, "v2")
        ld_elem(t, "x7", 8, 0)
        t.check("x7", 0xA5 if not mut("mask_spans_group") else 0, lab, f"{lm}: v2 not written by the mask result")
    return t


@rule
def g_vreg_mask_vtype_indp() -> TestFile:
    t = new("vreg_mask_vtype_indp")
    t.describe(
        rule_text="A vector mask occupies only one vector register regardless of SEW and LMUL.",
        source=VC,
        context="Mask bit i is bit i of the register for any SEW/LMUL (norm:vreg_mask_sz). Tail mask bits (i >= vl) are "
        "agnostic, so only body bits and the next register are checked.",
        plan="For e16 m4, e16 m8, e32 m8 at VLMAX (>= 8 for VLEN >= 32): v1 and v2 = 0xA5; vmsne.vi v1, v16, 0 (v16 = iota) gives bits "
        "1..VLMAX-1 set and bit 0 clear: byte 0 = 0xFE; v2 keeps 0xA5.",
    )
    for sew, lm in ((16, "m4"), (16, "m8"), (32, "m8")):
        mask_setup(t, sew, lm)
        fill(t, "v1", 0xA5)
        fill(t, "v2", 0xA5)
        vset_max(t, sew, lm)
        lab = mark(t)
        t.emit("vmsne.vi v1, v16, 0")
        store(t, "v1")
        ld_elem(t, "x7", 8, 0)
        t.check("x7", 0xFE, lab, f"e{sew} {lm}: mask byte 0")
        store(t, "v2")
        ld_elem(t, "x7", 8, 0)
        t.check("x7", 0xA5 if not mut("mask_spans_group") else 0, lab, f"e{sew} {lm}: v2 not written")
    return t


@rule
def g_vreg_mask_sz() -> TestFile:
    t = new("vreg_mask_sz")
    t.describe(
        rule_text="Each element is allocated a single mask bit in a mask vector register. The mask bit for element i "
        "is located in bit i of the mask register, independent of SEW or LMUL.",
        source=VC,
        context="Body bits only (tail mask bits are agnostic).",
        plan="SEW >= 16 so that iota values do not wrap. For e16 m8 (VLMAX >= 16): vmseq.vx v1, v16, x6 (v16 = "
        "iota) with x6 = 9: byte 1 = 0x02, byte 0 = 0. For e16 m4, e16 m8 and e32 m8, with x6 = VLMAX-1: the byte "
        "holding bit VLMAX-1 is exactly 1 << ((VLMAX-1) % 8).",
    )
    for sew, lm in ((16, "m4"), (16, "m8"), (32, "m8")):
        mask_setup(t, sew, lm)
        vset_max(t, sew, lm, rd="x8")
        if lm == "m8" and sew == 16:
            t.li("x6", 9)
            lab = mark(t)
            t.emit("vmseq.vx v1, v16, x6")
            store(t, "v1")
            ld_elem(t, "x7", 8, 1)
            t.check("x7", 0x02 if not mut("mask_bit_per_byte") else 0, lab, f"e{sew} {lm}: element 9 -> byte 1 bit 1")
            ld_elem(t, "x7", 8, 0)
            t.check("x7", 0, lab, f"e{sew} {lm}: byte 0 = 0")
        t.emit("addi x8, x8, -1  // k = VLMAX-1")
        lab = mark(t)
        t.emit("vmseq.vx v1, v16, x8")
        store(t, "v1")
        t.emit("srli x9, x8, 3")
        ld_elem(t, "x7", 8, "x9")
        t.emit("andi x9, x8, 7")
        t.emit("li x1, 1")
        t.emit("sll x1, x1, x9")
        t.emit("xor x7, x7, x1")
        t.check("x7", 0, lab, f"e{sew} {lm}: element VLMAX-1 -> byte (VLMAX-1)/8, bit (VLMAX-1)%8 only")
    return t


@rule
def g_vreg_scalar_lmul_indp() -> TestFile:
    t = new("vreg_scalar_lmul_indp")
    t.describe(
        rule_text="Any vector register can be used to hold a scalar regardless of the current LMUL setting.",
        source=VC,
        context="Reduction scalar operands (vs1[0]) and results (vd[0]) are single registers (norm:vreduction_scalar_def), "
        "and vmv.s.x/vmv.x.s ignore LMUL.",
        plan="e8 m8, vl = 4: v8-v15 = iota; vmv.s.x v3, 100 (an odd register inside no group); vredsum.vs v5, v8, v3 "
        "gives 100 + 0+1+2+3 = 106 in v5[0] (read by vmv.x.s v5); vmv.s.x v7 / vmv.x.s v7 round-trip 0x5A.",
    )
    iota(t, "v8", 8, "m8")
    vset(t, "x0", 4, 8, "m8")
    t.li("x6", 100)
    t.emit("vmv.s.x v3, x6")
    lab = mark(t)
    t.emit("vredsum.vs v5, v8, v3")
    t.emit("vmv.x.s x7, v5")
    t.check("x7", 106 if not mut("scalar_needs_group") else 6, lab, "vredsum.vs v5, v8, v3 at m8")
    t.li("x6", 0x5A)
    lab = mark(t)
    t.emit("vmv.s.x v7, x6")
    t.emit("vmv.x.s x7, v7")
    t.check("x7", 0x5A, lab, "vmv.s.x/vmv.x.s v7 at m8")
    return t


# ======================================================================== policies
VL3 = 3
MASKBYTE = 0xFD  # elements 0 and 2 active, 1 inactive, tail bits set


def policy_run(t: TestFile, insn: str, ta: int, ma: int, masked: bool = True) -> None:
    """v8 = 0xA5 bytes (old), v2 = iota, v3 = 0x10 bytes, v0 = MASKBYTE; e8 m1, vl = 3 with (ta, ma); insn."""
    iota(t, "v2", 8, "m1")
    fill(t, "v3", 0x10)
    fill(t, "v8", 0xA5)
    vset(t, "x0", 1, 8, "m1")
    t.li("x6", MASKBYTE)
    t.emit("vmv.s.x v0, x6")
    t.la("x6", BUF2)
    vset(t, "x0", VL3, 8, "m1", ta, ma)


def policy_checks(
    t: TestFile, lab: str, d: str, ta: int, ma: int, act: dict[int, int], tail_old: int = 0xA5, inact_old: int = 0xA5
) -> None:
    """Element checks after policy_run: active elements exact, inactive 1 and tail 3 and VLMAX-1."""
    store(t, "v8")
    for i, v in act.items():
        ld_elem(t, "x7", 8, i)
        t.check("x7", v, lab, f"{d}: active element {i}")
    ld_elem(t, "x7", 8, 1)
    if ma:
        check_agn(t, "x7", inact_old, 8, lab, f"{d}: inactive element 1 (ma)")
    else:
        t.check("x7", inact_old if not mut("inactive_ones_under_mu") else 0xFF, lab, f"{d}: inactive element 1 (mu)")
    for off in (3, "last"):
        if off == "last":
            t.emit("csrr x9, vlenb")
            t.emit("addi x9, x9, -1")
            ld_elem(t, "x7", 8, "x9")
        else:
            ld_elem(t, "x7", 8, off)
        if ta:
            if mut("agnostic_zero"):
                t.check("x7", 0, lab, f"{d}: tail element {off} (ta)")
            else:
                check_agn(t, "x7", tail_old, 8, lab, f"{d}: tail element {off} (ta)")
        else:
            t.check("x7", tail_old if not mut("tail_ones_under_tu") else 0xFF, lab, f"{d}: tail element {off} (tu)")


def policy_rule(
    name: str,
    text: str,
    ctx: str,
    plan: str,
    combos: list[tuple[int, int]],
    insns: list[tuple[str, str, dict[int, int]]],
) -> TestFile:
    t = new(name)
    t.describe(rule_text=text, source=VC, context=ctx, plan=plan)
    # BUF2 bytes 0..3 = 0x31..0x34 for the load cases
    t.la("x6", BUF2)
    for i in range(4):
        t.li("x7", 0x31 + i)
        t.emit(f"sb x7, {i}(x6)")
    for ta, ma in combos:
        for insn, d, act in insns:
            policy_run(t, insn, ta, ma)
            lab = mark(t)
            t.emit(insn)
            policy_checks(t, lab, f"{d} ta={ta} ma={ma}", ta, ma, act)
    return t


POLICY_CTX = (
    "e8, m1, vl = 3, v0 = 0xfd: elements 0 and 2 are active, element 1 is inactive, and elements 3 to "
    "VLMAX-1 are the tail (their mask bits are 1, which must not matter). The destination v8 holds 0xA5 "
    "bytes before the instruction. Agnostic elements may each keep their value or become all 1s "
    "(norm:vreg_agnostic_op)."
)
VADD = ("vadd.vv v8, v2, v3, v0.t", "vadd.vv", {0: 0x10, 2: 0x12})
VLE = ("vle8.v v8, (x6), v0.t", "vle8.v", {0: 0x31, 2: 0x33})


@rule
def g_vreg_mask_op() -> TestFile:
    return policy_rule(
        "vreg_mask_op",
        "When a set is marked undisturbed, the corresponding set of destination elements in a vector register group "
        "retain the value they previously held.",
        POLICY_CTX,
        "tu, mu: masked vadd.vv and masked vle8.v: active elements 0 and 2 get their results; inactive element 1 and "
        "tail elements 3 and VLMAX-1 keep 0xA5 exactly.",
        [(0, 0)],
        [VADD, VLE],
    )


@rule
def g_vreg_agnostic_op() -> TestFile:
    return policy_rule(
        "vreg_agnostic_op",
        "When a set is marked agnostic, the corresponding set of destination elements in any vector destination "
        "operand can either retain the value they previously held, or are overwritten with 1s. Within a single vector "
        "instruction, each destination element can be either left undisturbed or overwritten with 1s, in any "
        "combination, and the pattern of undisturbed or overwritten with 1s is not required to be deterministic when "
        "the instruction is executed with the same inputs.",
        POLICY_CTX,
        "ta, ma: masked vadd.vv and masked vle8.v: active elements exact; inactive element 1 and tail elements 3 and "
        "VLMAX-1 are each 0xA5 or 0xFF (checked independently, so any combination passes).",
        [(1, 1)],
        [VADD, VLE],
    )


@rule
def g_vtype_vta_vma_op() -> TestFile:
    return policy_rule(
        "vtype_vta_vma_op",
        "These two bits modify the behavior of destination tail elements and destination inactive masked-off elements "
        "respectively during the execution of vector instructions. The tail and inactive sets contain element "
        "positions that are not receiving new results during a vector operation, as defined in "
        "<<sec-inactive-defs>>.",
        POLICY_CTX + " vta governs only the tail and vma only inactive elements.",
        "ta, mu: inactive element 1 keeps 0xA5 exactly, tail may be 0xFF. tu, ma: tail keeps 0xA5 exactly, inactive "
        "may be 0xFF. For masked vadd.vv and vle8.v.",
        [(1, 0), (0, 1)],
        [VADD, VLE],
    )


@rule
def g_vmask_agn_op() -> TestFile:
    return policy_rule(
        "vmask_agn_op",
        "The destination vector register elements corresponding to masked-off elements are handled with either a "
        "mask-undisturbed or mask-agnostic policy depending on the setting of the vma bit in vtype",
        POLICY_CTX,
        "vma = 0 (with vta = 0 and 1): inactive element 1 keeps 0xA5; vma = 1: 0xA5 or 0xFF. Masked vadd.vv, vle8.v "
        "and vrsub.vi (v8 = 5 - v2 on active elements).",
        [(0, 0), (1, 0), (0, 1), (1, 1)],
        [VADD, VLE, ("vrsub.vi v8, v2, 5, v0.t", "vrsub.vi", {0: 5, 2: 3})],
    )


@rule
def g_vreg_vmask() -> TestFile:
    t = new("vreg_vmask")
    t.describe(
        rule_text="The mask value used to control execution of a masked vector instruction is always supplied by "
        "vector register v0.",
        source=VC,
        context="e8, m1, vl = 4, tu mu.",
        plan="v0 = 0x05 (elements 0, 2 active), v1 = 0x0A (the complement) and v9 = 0x0A: vadd.vv v8, v2, v3, v0.t "
        "updates elements 0 and 2 only. Then v0 = 0x0A: elements 1 and 3 only. Old v8 = 0xA5, v2 = iota, v3 = 0x10.",
    )
    for m0 in (0x05, 0x0A):
        iota(t, "v2", 8, "m1")
        fill(t, "v3", 0x10)
        fill(t, "v8", 0xA5)
        vset(t, "x0", 1, 8, "m1")
        t.li("x6", m0)
        t.emit("vmv.s.x v0, x6")
        t.li("x6", m0 ^ 0xF)
        t.emit("vmv.s.x v1, x6")
        t.emit("vmv.s.x v9, x6")
        vset(t, "x0", 4, 8, "m1")
        lab = mark(t)
        t.emit("vadd.vv v8, v2, v3, v0.t")
        store(t, "v8")
        src = m0 if not mut("mask_from_v1") else m0 ^ 0xF
        for i in range(4):
            ld_elem(t, "x7", 8, i)
            t.check("x7", (0x10 + i) if (src >> i) & 1 else 0xA5, lab, f"v0={hex(m0)}: element {i}")
    return t


def vadd_vv(vd: int, vs2: int, vs1: int, vm: int) -> int:
    return (vm << 25) | (vs2 << 20) | (vs1 << 15) | (vd << 7) | 0x57


@rule
def g_vmask_vm_enc() -> TestFile:
    t = new("vmask_vm_enc")
    t.describe(
        rule_text="Where available, masking is encoded in a single-bit vm field in the instruction (inst[25]).",
        source=VC,
        context="vm = 0: masked by v0.t; vm = 1: unmasked. vadd.vv is encoded here as .word with only bit 25 "
        "differing.",
        plan="e8, m1, vl = 4, tu mu, v0 = 0x05, old v8 = 0xA5, v2 = iota, v3 = 0x10: vadd.vv with inst[25] = 1 "
        "updates all four elements; with inst[25] = 0 only elements 0 and 2. v0 = 0 with inst[25] = 1 still "
        "updates all four.",
    )
    for vm, m0 in ((1, 0x05), (0, 0x05), (1, 0x00)):
        iota(t, "v2", 8, "m1")
        fill(t, "v3", 0x10)
        fill(t, "v8", 0xA5)
        vset(t, "x0", 1, 8, "m1")
        t.li("x6", m0)
        t.emit("vmv.s.x v0, x6")
        vset(t, "x0", 4, 8, "m1")
        lab = mark(t)
        t.emit(f".word {hex(vadd_vv(8, 2, 3, vm))}  // vadd.vv v8, v2, v3 with vm={vm}")
        store(t, "v8")
        eff = vm if not mut("vm_inverted") else 1 - vm
        for i in range(4):
            ld_elem(t, "x7", 8, i)
            active = eff == 1 or (m0 >> i) & 1
            t.check("x7", (0x10 + i) if active else 0xA5, lab, f"vm={vm} v0={hex(m0)}: element {i}")
    return t


def mask_tail_case(
    t: TestFile, insn: str, d: str, ta: int, body: list[tuple[int, int]], must1: int, setup: Callable[[], None]
) -> None:
    """Mask destination v8 (old all 1s) with vl = 3 (e8 m1): body bits 0..2 exact (body list of (bit, value)),
    tail bits in must1 (a byte pattern) must be 1 (old = 1 and computed = 1), checked in byte 0 (bits 3-7), byte 1
    and the last byte."""
    setup()
    fill(t, "v8", 0xFF)
    vset(t, "x0", VL3, 8, "m1", ta, 0)
    lab = mark(t)
    t.emit(insn)
    store(t, "v8")
    ld_elem(t, "x7", 8, 0)
    bmask = 0
    bval = 0
    for bit, v in body:
        bmask |= 1 << bit
        bval |= v << bit
    t.check_masked("x7", bmask, bval, lab, f"{d}: body bits 0-2")
    m0 = must1 & 0xF8
    zero = mut("mask_tail_zeroed")
    t.check_masked("x7", m0, m0 if not zero else 0, lab, f"{d}: tail bits of byte 0 where old = computed = 1")
    ld_elem(t, "x7", 8, 1)
    t.check_masked("x7", must1, must1 if not zero else 0, lab, f"{d}: byte 1 bits where old = computed = 1")
    t.emit("csrr x9, vlenb")
    t.emit("addi x9, x9, -1")
    ld_elem(t, "x7", 8, "x9")
    t.check_masked("x7", must1, must1 if not zero else 0, lab, f"{d}: last byte bits where old = computed = 1")


def even_setup(t: TestFile) -> Callable[[], None]:
    def f() -> None:
        iota(t, "v2", 8, "m1")
        t.emit("vand.vi v3, v2, -2  // element i: i & ~1")

    return f


@rule
def g_vreg_mask_tail_agn() -> TestFile:
    t = new("vreg_mask_tail_agn")
    t.describe(
        rule_text="Mask destination tail elements are always treated as tail-agnostic, regardless of the setting of "
        "vta.",
        source=VC,
        context="A tail mask bit may keep its value, become 1, or (norm:vreg_mask_tail_op) take the value computed "
        "with vl = VLMAX, in any combination. Where the old bit and the computed bit are both 1, every legal outcome "
        "is 1, so only those bits are constrained; body bits are exact. A design that clears or corrupts mask tails "
        "under tu fails.",
        plan="e8 m1, vl = 3, old v8 = all 1s. vmseq.vv v8, v2, v3 with v3[i] = v2[i] & ~1 (true for even i): body bits "
        "0-2 = 1, 0, 1; tail even bits (0x55 pattern) stay 1 in bytes 0, 1 and the last; with vta = 0 and vta = 1. "
        "The same for vmand.mm v8, v4 (0xAA), v5 (0xFF): body bits = 0, 1, 0, and the odd tail bits stay 1.",
    )

    def mand() -> None:
        fill(t, "v4", 0xAA)
        fill(t, "v5", 0xFF)

    for ta in (0, 1):
        mask_tail_case(t, "vmseq.vv v8, v2, v3", f"vmseq vta={ta}", ta, [(0, 1), (1, 0), (2, 1)], 0x55, even_setup(t))
        mask_tail_case(t, "vmand.mm v8, v4, v5", f"vmand vta={ta}", ta, [(0, 0), (1, 1), (2, 0)], 0xAA, mand)
    return t


@rule
def g_vreg_mask_tail_op() -> TestFile:
    t = new("vreg_mask_tail_op")
    t.describe(
        rule_text="In addition, except for mask load instructions, any element in the tail of a mask result can also "
        "be written with the value the mask-producing operation would have calculated with vl=VLMAX. Furthermore, for "
        "mask-logical instructions and vmsbf.m, vmsif.m, vmsof.m mask-manipulation instructions, any element in the "
        "tail of the result can be written with the value the mask-producing operation would have calculated with "
        "vl=VLEN, SEW=8, and LMUL=8 (i.e., all bits of the mask register can be overwritten).",
        source=VC,
        context="Mask loads are excluded: vlm.v loads ceil(vl/8) bytes (evl); its tail bytes may only keep their value "
        "or become 1s, never the loaded data. Old destination bits are all 1s, so a tail bit may be 0 only where the "
        "computed value is 0.",
        plan="1. vlm.v v8 after vsetivli 8 (vl = min(8, VLMAX) >= 4, evl = 1) from bytes 0x00: byte 0 = 0x00, bytes 1 and vlenb-1 stay 0xFF (memory "
        "holds 0x00 there).\n"
        "2. vmsbf.m v8, v4 (v4 = 0x10 bytes: first set bit 4), vl = 3, tu: body bits 0-2 = 1; tail bits where the "
        "VLEN-wide result is 1 (bit 3 only) stay 1.\n"
        "3. vmsleu.vi v8, v2, 15 (v2 = iota, vl = 3): computed bits 0..15 = 1, so the tail bits of bytes 0 and 1 "
        "and of the last byte stay 1.",
    )
    t.la("x6", BUF2)
    t.emit("sw x0, 0(x6)")
    fill(t, "v8", 0xFF)
    vset(t, "x0", 8, 8, "m1")
    t.la("x6", BUF2)
    lab = mark(t)
    t.emit("vlm.v v8, (x6)")
    store(t, "v8")
    ld_elem(t, "x7", 8, 0)
    t.check("x7", 0, lab, "vlm.v vl=8: byte 0 loaded")
    ld_elem(t, "x7", 8, 1)
    t.check("x7", 0xFF if not mut("vlm_tail_loaded") else 0, lab, "vlm.v vl=8: byte 1 (tail) not loaded")
    t.emit("csrr x9, vlenb")
    t.emit("addi x9, x9, -1")
    ld_elem(t, "x7", 8, "x9")
    t.check("x7", 0xFF if not mut("vlm_tail_loaded") else 0, lab, "vlm.v vl=8: last byte (tail) not loaded")

    def msbf() -> None:
        fill(t, "v4", 0x10)

    mask_tail_case(t, "vmsbf.m v8, v4", "vmsbf.m", 0, [(0, 1), (1, 1), (2, 1)], 0x00, msbf)
    store(t, "v8")
    lab = mark(t)
    ld_elem(t, "x7", 8, 0)
    t.check_masked(
        "x7", 0x08, 0x08 if not mut("mask_tail_zeroed") else 0, lab, "vmsbf.m: tail bit 3 (computed 1) stays 1"
    )
    mask_tail_case(
        t, "vmsleu.vi v8, v2, 15", "vmsleu.vi 15", 0, [(0, 1), (1, 1), (2, 1)], 0xFF, lambda: iota(t, "v2", 8, "m1")
    )
    return t


@rule
def g_vreg_overlap_agn() -> TestFile:
    t = new("vreg_overlap_agn")
    t.describe(
        rule_text="When source and destination registers overlap and have different EEW, the instruction is mask- and "
        "tail-agnostic, regardless of the setting of the vta and vma bits in vtype.",
        source=VC,
        context="Legal overlaps (norm:vreg_overlap_legal): a narrowing destination in the lowest-numbered part of the "
        "source group (vnsrl.wi v8, v8), and a widening destination whose highest-numbered part is an EEW=SEW source "
        "with EMUL >= 1 (vwaddu.vv v8, v9, v9). Agnostic elements keep their value or become all 1s.",
        plan="1. e8 m1 tu mu, vl = 3, v8-v9 = 16-bit iota + 0x0500 (old tail byte 3 = 0x05, the narrowed value would be 3): vnsrl.wi v8, v8, 0: body bytes 0-2 = 0x00, 0x01, "
        "0x02; tail bytes 3 and vlenb-1 of v8 are their old value or 0xFF.\n"
        "2. e8 m1 tu, vl = 1, v9 = 0x07 bytes, v8 = 0xA5: vwaddu.vv v8, v9, v9 writes 14 to 16-bit element 0; the "
        "last halfword of v8 (tail element vlenb/2-1 >= 1) is 0xA5A5 or 0xFFFF.\n"
        "3. The same narrowing case with a mask (v0 = 0x5, mu): inactive element 1 is old or 0xFF.",
    )
    for masked in (False, True):
        iota(t, "v8", 16, "m2", 0x0500)
        store(t, "v8", BUF2)
        if masked:
            vset(t, "x0", 1, 8, "m1")
            t.li("x6", 5)
            t.emit("vmv.s.x v0, x6")
        vset(t, "x0", 3, 8, "m1", 0, 0)
        lab = mark(t)
        t.emit("vnsrl.wi v8, v8, 0" + (", v0.t" if masked else ""))
        store(t, "v8")
        for i in range(3):
            ld_elem(t, "x7", 8, i)
            if masked and i == 1:
                ld_elem(t, "x8", 8, 1, BUF2)
                check_agn(t, "x7", "x8", 8, lab, "masked vnsrl overlap: inactive element 1")
            else:
                t.check("x7", i, lab, f"vnsrl overlap: element {i}")
        for off in (3, "last"):
            if off == "last":
                t.emit("csrr x9, vlenb")
                t.emit("addi x9, x9, -1")
                ld_elem(t, "x7", 8, "x9")
                ld_elem(t, "x8", 8, "x9", BUF2)
            else:
                ld_elem(t, "x7", 8, off)
                ld_elem(t, "x8", 8, off, BUF2)
            if mut("overlap_result_in_tail") and off == 3:
                t.check("x7", 3, lab, "tail gets result")
            else:
                check_agn(t, "x7", "x8", 8, lab, f"vnsrl overlap (tu): tail byte {off}")
    fill(t, "v9", 0x07)
    fill(t, "v8", 0xA5)
    vset(t, "x0", 1, 8, "m1", 0, 0)
    lab = mark(t)
    t.emit("vwaddu.vv v8, v9, v9")
    store(t, "v8")
    ld_elem(t, "x7", 16, 0)
    t.check("x7", 14, lab, "vwaddu overlap: element 0")
    t.emit("csrr x9, vlenb")
    t.emit("addi x9, x9, -2")
    ld_elem(t, "x7", 16, "x9")
    check_agn(t, "x7", 0xA5A5, 16, lab, "vwaddu overlap (tu): last halfword of v8 (tail element vlenb/2-1)")
    return t


@rule
def g_vwop_vd_eew_emul() -> TestFile:
    t = new("vwop_vd_eew_emul")
    t.describe(
        rule_text="A few vector arithmetic instructions are defined to be widening operations where the destination "
        "vector register group has EEW=2*SEW and EMUL=2*LMUL.",
        source=VC,
        context="At e8 m1, vwaddu.vv writes a 2-register group of 16-bit elements: element j is in v(d) for j < "
        "vlenb/2 and in v(d+1) after.",
        plan="e8 m1 at VLMAX: v2 = iota, v3 = 0xF0 bytes; vwaddu.vv v8, v2, v3: v8 halfword 0 = 0xF0 (16-bit), "
        "halfword 1 = 0xF1, v9 halfword 0 = element vlenb/2 = (vlenb/2 mod 256) + 0xF0 (a carry into bit 8 shows "
        "EEW = 16).",
    )
    iota(t, "v2", 8, "m1")
    fill(t, "v3", 0xF0)
    vset_max(t, 8, "m1")
    lab = mark(t)
    t.emit("vwaddu.vv v8, v2, v3")
    store(t, "v8")
    ld_elem(t, "x7", 16, 0)
    t.check("x7", 0xF0, lab, "v8 halfword 0 (element 0)")
    ld_elem(t, "x7", 16, 2)
    t.check("x7", 0xF1, lab, "v8 halfword 1 (element 1)")
    store(t, "v9")
    ld_elem(t, "x7", 16, 0)
    t.emit("csrr x8, vlenb")
    t.emit("srli x8, x8, 1")
    t.emit("andi x8, x8, 0xff")
    t.emit("addi x8, x8, 0xf0")
    if mut("widen_dest_one_reg"):
        t.emit("li x8, 0xf0")
    eq_reg(t, "x7", "x8", lab, "v9 halfword 0 = element vlenb/2 (second register of the group)")
    return t


@rule
def g_vnop_vd_vs2_eew_emul() -> TestFile:
    t = new("vnop_vd_vs2_eew_emul")
    t.describe(
        rule_text="A few instructions are provided to convert double-width source vectors into single-width "
        "destination vectors. These instructions convert a vector register group specified by vs2 with EEW/EMUL="
        "2*SEW/2*LMUL to a vector register group with the current SEW/LMUL setting.",
        source=VC,
        context="At e8 m1, vnsrl.wi reads vs2 as a 2-register group of 16-bit elements.",
        plan="v16-v17 = 16-bit iota + 0x1200 (e16 m2); at e8 m1 VLMAX: vnsrl.wi v8, v16, 8 gives byte j = (j + 0x1200) "
        ">> 8: 0x12 for small j; vnsrl.wi v8, v16, 0 gives j mod 256: byte 1 = 1, byte vlenb/2 = vlenb/2 mod 256 (from "
        "v17), last byte = (vlenb-1) mod 256.",
    )
    iota(t, "v16", 16, "m2", 0x1200)
    vset_max(t, 8, "m1")
    lab = mark(t)
    t.emit("vnsrl.wi v8, v16, 8")
    store(t, "v8")
    ld_elem(t, "x7", 8, 0)
    t.check("x7", 0x12, lab, "vnsrl.wi 8: byte 0")
    lab = mark(t)
    t.emit("vnsrl.wi v8, v16, 0")
    store(t, "v8")
    ld_elem(t, "x7", 8, 1)
    t.check("x7", 1, lab, "vnsrl.wi 0: byte 1")
    t.emit("csrr x9, vlenb")
    t.emit("srli x9, x9, 1")
    ld_elem(t, "x7", 8, "x9")
    t.emit("andi x9, x9, 0xff")
    eq_reg(t, "x7", "x9", lab, "vnsrl.wi 0: byte vlenb/2 comes from v17", tmp="x1")
    t.emit("csrr x9, vlenb")
    t.emit("addi x9, x9, -1")
    ld_elem(t, "x7", 8, "x9")
    t.emit("andi x9, x9, 0xff")
    eq_reg(t, "x7", "x9", lab, "vnsrl.wi 0: last byte", tmp="x1")
    return t


@rule
def g_vnop_vs1_eew_emul() -> TestFile:
    t = new("vnop_vs1_eew_emul")
    t.describe(
        rule_text="Where there is a second source vector register group (specified by vs1), this has the same "
        "(narrower) width as the result (i.e., EEW=SEW).",
        source=VC,
        context="vnsrl.wv shifts each 2*SEW element of vs2 by the low log2(2*SEW) bits of the SEW-wide element of vs1.",
        plan="e8 m1, vl = 4: v16-v17 = 0x0180 halfwords (e16 m2); v1 bytes = 0, 1, 2, 3 (iota); vnsrl.wv v8, v16, "
        "v1: byte j = (0x0180 >> j) & 0xff = 0x80, 0xC0, 0x60, 0x30. Reading vs1 with EEW = 16 would give shifts 0, 2, "
        "4, 6 instead.",
    )
    vset_max(t, 16, "m2")
    t.li("x6", 0x0180)
    t.emit("vmv.v.x v16, x6")
    iota(t, "v1", 8, "m1")
    vset(t, "x0", 4, 8, "m1")
    lab = mark(t)
    t.emit("vnsrl.wv v8, v16, v1")
    store(t, "v8")
    for j in range(4):
        sh = j if not mut("narrow_vs1_wide") else ((2 * j) | ((2 * j + 1) << 8)) & 15
        ld_elem(t, "x7", 8, j)
        t.check("x7", (0x0180 >> sh) & 0xFF, lab, f"vnsrl.wv element {j}: shift {j} from vs1 byte {j}")
    return t


# ======================================================================== vstart, prestart/body/tail
def vstart_arith(t: TestFile, k: str, ta: int, d: str, vlreg: str | None = None) -> None:
    """e8 m1, vl = 4 (or vlreg), v8 = 0xA5, v2 = iota; vstart = k (asm source), vadd.vi v8, v2, 1 (ta): accept
    illegal (norm:vstart_vtype_dep); if executed, elements < k keep 0xA5 and k..vl-1 hold i+1, vstart = 0."""


@rule
def g_vstart_op() -> TestFile:
    t = new("vstart_op")
    t.describe(
        rule_text="All vector instructions are defined to begin execution with the element number given in the vstart "
        "CSR, leaving earlier elements in the destination vector undisturbed",
        source=VC,
        context="norm:vstart_vtype_dep lets an implementation raise illegal-instruction for a vstart it can never "
        "produce for that instruction; vadd.vi cannot trap mid-way, so it may trap here (then vstart is unchanged, "
        "norm:vstart_unmodified). A unit-stride load can fault at any element, so vle8.v must execute. Prestart "
        "elements are undisturbed even with ta, ma.",
        plan="e8 m1, vl = 4, v8 = 0xA5 bytes, v2 = iota. For vstart = 1 and 3, with tu and ta: vadd.vi v8, v2, 1 "
        "(may raise illegal-instruction, then vstart reads back k) and vle8.v v8 (bytes 0x31-0x34): elements below "
        "vstart keep 0xA5, elements vstart..3 get their results, vstart reads 0 afterwards.",
    )
    t.la("x6", BUF2)
    for i in range(4):
        t.li("x7", 0x31 + i)
        t.emit(f"sb x7, {i}(x6)")
    for k in (1, 3):
        for ta in (0, 1):
            for insn, res, may_trap in (
                ("vadd.vi v8, v2, 1", lambda i: i + 1, True),
                ("vle8.v v8, (x6)", lambda i: 0x31 + i, False),
            ):
                iota(t, "v2", 8, "m1")
                fill(t, "v8", 0xA5)
                vset(t, "x0", 4, 8, "m1", ta, ta)
                t.la("x6", BUF2)
                t.emit(f"csrwi vstart, {k}")
                d = f"{insn.split()[0]} vstart={k} ta={ta}"

                def body(insn: str = insn, res: Callable[[int], int] = res, k: int = k, d: str = d) -> None:
                    store(t, "v8")
                    lab = mark(t)
                    for i in range(4):
                        ld_elem(t, "x7", 8, i)
                        if i < k and not mut("prestart_updated"):
                            t.check("x7", 0xA5, lab, f"{d}: prestart element {i} undisturbed")
                        else:
                            t.check("x7", res(i), lab, f"{d}: element {i}")
                    t.emit("csrr x7, vstart")
                    t.check("x7", 0, lab, f"{d}: vstart reset")

                if may_trap:
                    vwin(t, [insn], ["ok", ILLEGAL], d, flag="x1")

                    def trapped(k: int = k, d: str = d) -> None:
                        lab = mark(t)
                        t.emit("csrr x7, vstart")
                        t.check("x7", k, lab, f"{d}: trapped, vstart unchanged")
                        t.emit("csrw vstart, x0")

                    t.either("x1", trapped, body)
                else:
                    t.emit(insn)
                    body()
    return t


@rule
def g_vstart_update() -> TestFile:
    t = new("vstart_update")
    t.describe(
        rule_text="reset the vstart CSR to zero at the end of execution.",
        source=VC,
        context="Continuation of norm:vstart_op: all vector instructions reset vstart to zero at the end of "
        "execution. Instructions that may raise illegal-instruction for a nonzero vstart (norm:vstart_vtype_dep: "
        "arithmetic, permutations) are accepted either way; a trap leaves vstart unchanged. Loads and stores can "
        "fault at any element and must execute. CSR instructions are not vector instructions (vstart_acc_sz).",
        plan="e8 m1, vl = 4, vstart = 2 before each: vle8.v, vse8.v (stores elements 2-3), vlse8.v, vluxei8.v must "
        "execute and leave vstart = 0; vadd.vv, vmv.v.x, vslidedown.vi, vmseq.vv, vmv.x.s and vmv.s.x either trap "
        "(vstart still 2) or leave vstart = 0. Also with vstart = 3 >= vl = 2: vle8.v leaves vstart = 0.",
    )
    t.la("x6", BUF2)
    t.emit("vsetivli x0, 4, e8, m1, tu, mu")
    t.emit("vmv.v.i v4, 0  // indices")
    must = ["vle8.v v8, (x6)", "vse8.v v8, (x6)", "vlse8.v v8, (x6), x0", "vluxei8.v v8, (x6), v4"]
    may = [
        "vadd.vv v8, v2, v3",
        "vmv.v.x v8, x7",
        "vslidedown.vi v8, v2, 1",
        "vmseq.vv v8, v2, v3",
        "vmv.x.s x7, v2",
        "vmv.s.x v8, x7",
    ]
    for insn in must:
        vset(t, "x0", 4, 8, "m1")
        t.la("x6", BUF2)
        t.emit("csrwi vstart, 2")
        lab = mark(t)
        t.emit(insn)
        t.emit("csrr x7, vstart")
        t.check("x7", 0 if not mut("vstart_not_reset") else 2, lab, f"{insn}: vstart reset to 0")
    for insn in may:
        vset(t, "x0", 4, 8, "m1")
        t.emit("csrwi vstart, 2")
        lab = vwin(t, [insn], ["ok", ILLEGAL], f"{insn} with vstart=2", flag="x1")
        t.emit("csrr x7, vstart")
        t.emit("slli x8, x1, 1  // expected: 2 if trapped, else 0")
        if mut("vstart_not_reset"):
            t.emit("li x8, 2")
        eq_reg(t, "x7", "x8", lab, f"{insn}: vstart 0 after execution (2 after a trap)")
        t.emit("csrw vstart, x0")
    vset(t, "x0", 2, 8, "m1")
    t.la("x6", BUF2)
    t.emit("csrwi vstart, 3")
    lab = mark(t)
    t.emit("vle8.v v8, (x6)")
    t.emit("csrr x7, vstart")
    t.check("x7", 0 if not mut("vstart_not_reset") else 3, lab, "vle8.v with vstart=3 >= vl=2: vstart reset")
    return t


@rule
def g_vstart_unmodified() -> TestFile:
    t = new("vstart_unmodified")
    t.describe(
        rule_text="vstart is not modified by vector instructions that raise illegal-instruction exceptions.",
        source=VC,
        context="Instructions that must raise illegal-instruction with vstart != 0: reductions "
        "(norm:vreduction_vstart_n0_ill), vcpop.m, vfirst.m, vmsbf.m, viota.m, vcompress.vm. With vill = 1, vector "
        "instructions raise illegal-instruction too (norm:vtype_vill_op).",
        plan="e8 m1, vl = 4: vstart = 1, then 3, then VLMAX-1 (vl = VLMAX for that case): vredsum.vs, vcpop.m, "
        "vfirst.m, vmsbf.m, viota.m and vcompress.vm each raise illegal-instruction and vstart reads the value written. "
        "vill = 1 with vstart = 0 and then vstart = 2: vadd.vv raises illegal-instruction and vstart is unchanged.",
    )
    insns = [
        "vredsum.vs v8, v2, v3",
        "vcpop.m x7, v2",
        "vfirst.m x7, v2",
        "vmsbf.m v8, v2",
        "viota.m v8, v2",
        "vcompress.vm v8, v2, v3",
    ]
    for k in ("1", "3", "big"):
        for insn in insns:
            if k == "big":
                vset_max(t, 8, "m1", rd="x9")
                t.emit("addi x9, x9, -1")
                t.emit("csrw vstart, x9")
            else:
                vset(t, "x0", 4, 8, "m1")
                t.emit(f"csrwi vstart, {k}")
                t.li("x9", int(k))
            lab = vwin(t, [insn], ILLEGAL, f"{insn} with vstart={k}")
            t.emit("csrr x7, vstart")
            if mut("vstart_cleared_on_illegal"):
                t.emit("li x9, 0")
            eq_reg(t, "x7", "x9", lab, f"{insn}: vstart unchanged by the trap", tmp="x1")
            t.emit("csrw vstart, x0")
    t.load("x8", VILL, "vill")
    t.li("x6", 1)
    t.emit("vsetvl x0, x6, x8  // vill = 1 (rs1 != x0: not the reserved keep-vl form)")
    for k in (0, 2):
        t.emit(f"csrwi vstart, {k}")
        lab = vwin(t, ["vadd.vv v8, v2, v3"], ILLEGAL, f"vadd.vv with vill=1, vstart={k}")
        t.emit("csrr x7, vstart")
        t.check("x7", k if not mut("vstart_cleared_on_illegal") else 0, lab, "vstart unchanged by the vill trap")
    t.emit("csrw vstart, x0")
    return t


@rule
def g_vstart_vl_dep() -> TestFile:
    t = new("vstart_vl_dep")
    t.describe(
        rule_text="When vstart >= vl, there are no body elements, and no elements are updated in any destination "
        "vector register group, including that no tail elements are updated with agnostic values.",
        source=VC,
        context="vl = 0 (vstart = 0) is the common case. With vstart > 0, arithmetic may raise illegal-instruction "
        "(norm:vstart_vtype_dep); loads must execute. The destination must keep every byte, also with ta, ma.",
        issues=f"{ISSUE}3311: the vstart >= vl property gives 'well-defined semantics for the vstart >= vl corner "
        "case'; allowing agnostic behavior there 'that ship has sailed'.",
        plan="v8 = 0xA5 bytes, e8 m1 ta ma. 1. vl = 0: vadd.vi v8, v2, 1, vle8.v v8, vmseq.vv v8 (mask result) and "
        "vmerge.vim v8 leave bytes 0, 1 and vlenb-1 = 0xA5. 2. vl = 2, vstart = 3: vle8.v v8 leaves them 0xA5; "
        "vadd.vi v8 either traps or leaves them. vstart is 0 after each executed instruction.",
    )
    t.la("x6", BUF2)

    def chk(lab: str, d: str) -> None:
        store(t, "v8")
        for off in (0, 1, "last"):
            if off == "last":
                t.emit("csrr x9, vlenb")
                t.emit("addi x9, x9, -1")
                ld_elem(t, "x7", 8, "x9")
            else:
                ld_elem(t, "x7", 8, off)
            t.check("x7", 0xA5 if not mut("vstart_ge_vl_tail_ones") else 0xFF, lab, f"{d}: byte {off} not updated")
        t.emit("csrr x7, vstart")
        t.check("x7", 0, lab, f"{d}: vstart = 0")

    for insn in ("vadd.vi v8, v2, 1", "vle8.v v8, (x6)", "vmseq.vv v8, v2, v2", "vmerge.vim v8, v2, 3, v0"):
        iota(t, "v2", 8, "m1")
        fill(t, "v8", 0xA5)
        t.la("x6", BUF2)
        vset(t, "x0", 0, 8, "m1", 1, 1)
        lab = mark(t)
        t.emit(insn)
        chk(lab, f"{insn} vl=0")
    iota(t, "v2", 8, "m1")
    fill(t, "v8", 0xA5)
    t.la("x6", BUF2)
    vset(t, "x0", 2, 8, "m1", 1, 1)
    t.emit("csrwi vstart, 3")
    lab = mark(t)
    t.emit("vle8.v v8, (x6)")
    chk(lab, "vle8.v vl=2 vstart=3")
    fill(t, "v8", 0xA5)
    vset(t, "x0", 2, 8, "m1", 1, 1)
    t.emit("csrwi vstart, 3")
    vwin(t, ["vadd.vi v8, v2, 1"], ["ok", ILLEGAL], "vadd.vi vl=2 vstart=3", flag="x1")
    t.emit("csrw vstart, x0")
    lab = mark(t)
    chk(lab, "vadd.vi vl=2 vstart=3 (trapped or not)")
    return t


@rule
def g_vstart_vl_scalar_indp() -> TestFile:
    t = new("vstart_vl_scalar_indp")
    t.describe(
        rule_text="Instructions that write an x register or f register do so even when vstart >= vl, including when "
        "vl=0.",
        source=VC,
        context="vmv.x.s copies element 0 regardless of vl; vcpop.m gives 0 and vfirst.m -1 when vl = 0 "
        "(norm:vcpop_vl0, norm:vfirst_vl0). With vstart > 0, vmv.x.s may raise illegal-instruction "
        "(norm:vstart_vtype_dep), vcpop/vfirst must (they need vstart = 0).",
        plan="v2 element 0 = 0x5A (e8). 1. vl = 0: vmv.x.s x7, v2 writes 0x5A (x7 preset 0x77); vcpop.m x7 writes 0; "
        "vfirst.m x7 writes -1. 2. vl = 1, vstart = 2: vmv.x.s either traps (x7 unchanged) or writes 0x5A.",
    )
    vset(t, "x0", 1, 8, "m1")
    t.li("x6", 0x5A)
    t.emit("vmv.s.x v2, x6")
    vset(t, "x0", 0, 8, "m1")
    for insn, exp in (("vmv.x.s x7, v2", 0x5A), ("vcpop.m x7, v2", 0), ("vfirst.m x7, v2", -1)):
        t.li("x7", 0x77)
        lab = mark(t)
        t.emit(insn)
        t.check("x7", exp if not mut("vl0_scalar_skip") else 0x77, lab, f"{insn} with vl=0 writes rd")
    vset(t, "x0", 1, 8, "m1")
    t.emit("csrwi vstart, 2")
    t.li("x7", 0x77)
    vwin(t, ["vmv.x.s x7, v2"], ["ok", ILLEGAL], "vmv.x.s with vstart=2 >= vl=1", flag="x1")
    t.emit("csrw vstart, x0")
    lab = mark(t)
    t.either(
        "x1",
        lambda: t.check("x7", 0x77, lab, "trapped: rd unchanged"),
        lambda: t.check("x7", 0x5A if not mut("vl0_scalar_skip") else 0x77, lab, "vmv.x.s with vstart >= vl writes rd"),
    )
    return t


# ======================================================================== paging-based element and trap tests
class VMemTest(hmem.MemTest):
    """MemTest (page tables, data pages) plus the vctl scratch buffers."""

    def render(self) -> str:
        self.extra_data = [
            "  .p2align 6",
            f"{BUF}:",
            "  .fill 8192, 1, 0",
            f"{BUF2}:",
            "  .fill 8192, 1, 0",
            "  // page tables and data pages (hmem.py)",
            *self._extra_data(),
        ]
        return TestFile.render(self)


PGBYTES = {0xFF8 + i: (1, 0x11 + i) for i in range(8)}  # last 8 bytes of the data page: 0x11..0x18
SV_COND = {64: "defined(SV39_SUPPORTED)", 32: "defined(SV32_SUPPORTED)"}
SCHEME = {64: "sv39", 32: "sv32"}


def pnew(rule: str, required: list | None = None) -> VMemTest:
    return VMemTest(
        out(),
        rule,
        required=required or ["I", "S", "Zve32x"],
        boot="S",
        march=MARCH,
        pool=["x1", "x6", "x7", "x8", "x9"],
    )


def paging_on(t: VMemTest, xlen: int) -> int:
    """S-mode paging: identity-map the image (root superpages, S-only), map VA P0 to a data page whose last 8 bytes
    are 0x11..0x18, and leave P1 = P0 + 4 KiB invalid. Returns P1 (the first invalid byte)."""
    pt = hmem.PT(t, "s", SCHEME[xlen], xlen)
    pt.identity(hmem.LEAF)
    pg = t.page("vdata", {o: v for o, v in PGBYTES.items()})
    va = hmem.VA_BASE[xlen]
    pt.leaf(va, pg, hmem.LEAF, note="data page P0")
    pt.atp("x6")
    t.emit("csrw satp, x6")
    t.emit("sfence.vma x0, x0")
    return va + 0x1000


def paging_off(t: TestFile) -> None:
    t.emit("csrw satp, x0")
    t.emit("sfence.vma x0, x0")


def paged(t: VMemTest, body: Callable[[int], None]) -> None:
    for xlen in (64, 32):
        with t.only_if(f"__riscv_xlen == {xlen}"), t.only_if(SV_COND[xlen]):
            p1 = paging_on(t, xlen)
            body(p1)
            paging_off(t)


@rule
def g_epc_vstart_op_V_trap() -> TestFile:
    t = pnew("epc_vstart_op_V_trap")
    t.describe(
        rule_text="On a trap during a vector instruction (caused by either a synchronous exception or an asynchronous "
        "interrupt), the existing *epc CSR is written with a pointer to the trapping vector instruction, while the "
        "vstart CSR contains the element index on which the trap was taken.",
        source=VC,
        context="S-mode with Sv39 (RV64) or Sv32 (RV32): VA page P0 is mapped, P1 = P0 + 4 KiB is invalid. A unit-"
        "stride access starting k bytes below P1 faults at element k (page fault; stval is 0 or P1, the first faulting "
        "byte). Interrupts cannot be placed inside an instruction, so only exceptions are tested.",
        plan="e8 m1 tu mu. For k = 1, 2, 3 with vl = 4: vle8.v v8, (P1-k) raises a load page fault (13) with sepc = "
        "the vle8.v, stval 0 or P1, and vstart = k afterwards. vse8.v (P1-2) raises a store page fault (15) with "
        "vstart = 2. vstart is cleared after each case.",
    )

    def body(p1: int) -> None:
        for k in (1, 2, 3):
            vset(t, "x0", 4, 8, "m1")
            t.li("x6", p1 - k)
            lab = vwin(t, ["vle8.v v8, (x6)"], LOAD_PF, f"vle8.v from P1-{k}", tval=[0, p1])
            t.emit("csrr x7, vstart")
            t.check("x7", k if not mut("vstart_not_recorded") else 0, lab, f"vle8.v from P1-{k}: vstart = {k}")
            t.emit("csrw vstart, x0")
        vset(t, "x0", 4, 8, "m1")
        t.li("x6", p1 - 2)
        lab = vwin(t, ["vse8.v v8, (x6)"], STORE_PF, "vse8.v to P1-2", tval=[0, p1])
        t.emit("csrr x7, vstart")
        t.check("x7", 2 if not mut("vstart_not_recorded") else 0, lab, "vse8.v to P1-2: vstart = 2")
        t.emit("csrw vstart, x0")

    paged(t, body)
    return t


def precise(name: str, req: list, src: str, text: str) -> TestFile:
    t = pnew(name, req)
    t.describe(
        rule_text=text,
        source=src,
        context="Precise vector traps (Exception Handling): older instructions have committed, no newer instruction "
        "has changed state, elements below vstart have committed; elements at or after vstart may have been changed "
        "only if restarting reproduces the result (so they are not checked). Same paging setup as "
        "epc_vstart_op_V_trap: P1 is invalid.",
        plan="e8 m1, vl = 4. 1. sb 0x6B to the data page (older), then vle8.v v8, (P1-2) faults at element 2 (13); "
        "the handler resumes after the following li x9, 1 (rvtest_trap_resume), so x9 = 0 shows the younger "
        "instruction did not run; vstart = 2; v8 bytes 0, 1 = 0x17, 0x18 (loaded before the fault); the older store "
        "is visible.\n2. v9 = 0x5C bytes: vse8.v v9, (P1-2) faults at element 2 (15); data-page bytes 0xFFE, 0xFFF "
        "hold 0x5C (elements 0, 1 committed); vstart = 2; the following li x9, 1 is skipped by the resume address and "
        "x9 stays 0.",
    )

    def body(p1: int) -> None:
        fill(t, "v8", 0xA5)
        vset(t, "x0", 4, 8, "m1")
        t.li("x6", p1 - 0x1000 + 0x100)
        t.li("x7", 0x6B)
        t.emit("sb x7, 0(x6)  // older store")
        t.li("x6", p1 - 2)
        t.li("x9", 0)
        skip = t.label("resume")
        t.la("x7", skip)
        t.la("x8", "rvtest_trap_resume")
        t.emit("SREG x7, 0(x8)")
        lab = vwin(
            t,
            ["vle8.v v8, (x6)", "li x9, 1  // younger: must not run", f"{skip}:"],
            LOAD_PF,
            "vle8.v from P1-2",
            tval=[0, p1],
        )
        t.check("x9", 0 if not mut("precise_younger_ran") else 1, lab, "the younger li did not execute")
        t.emit("csrr x7, vstart")
        t.check("x7", 2, lab, "vstart = 2")
        t.emit("csrw vstart, x0")
        store(t, "v8")
        ld_elem(t, "x7", 8, 0)
        t.check("x7", 0x17, lab, "v8 element 0 committed")
        ld_elem(t, "x7", 8, 1)
        t.check("x7", 0x18, lab, "v8 element 1 committed")
        t.li("x6", p1 - 0x1000 + 0x100)
        t.emit("lbu x7, 0(x6)")
        t.check("x7", 0x6B, lab, "the older store committed")
        fill(t, "v9", 0x5C)
        vset(t, "x0", 4, 8, "m1")
        t.li("x6", p1 - 2)
        t.li("x9", 0)
        skip2 = t.label("resume")
        t.la("x7", skip2)
        t.la("x8", "rvtest_trap_resume")
        t.emit("SREG x7, 0(x8)")
        lab = vwin(
            t,
            ["vse8.v v9, (x6)", "li x9, 1  // younger: must not run", f"{skip2}:"],
            STORE_PF,
            "vse8.v to P1-2",
            tval=[0, p1],
        )
        t.check("x9", 0 if not mut("precise_younger_ran") else 1, lab, "vse8.v: the younger li did not execute")
        t.emit("csrr x7, vstart")
        t.check("x7", 2, lab, "vse8.v: vstart = 2")
        t.emit("csrw vstart, x0")
        t.li("x6", p1 - 2)
        t.emit("lbu x7, 0(x6)")
        t.check("x7", 0x5C if not mut("precise_store_lost") else 0x17, lab, "vse8.v element 0 committed")
        t.emit("lbu x7, 1(x6)")
        t.check("x7", 0x5C if not mut("precise_store_lost") else 0x18, lab, "vse8.v element 1 committed")

    paged(t, body)
    return t


@rule
def g_V_precise_traps() -> TestFile:
    return precise("V_precise_traps", ["I", "S", "V"], VST, "The V vector extension has precise traps.")


@rule
def g_Zve_precise_traps() -> TestFile:
    return precise("Zve_precise_traps", ["I", "S", "Zve32x"], ZVE32X, "The zve32x extension has precise traps.")


def elem_rule(name: str, text: str, ctx: str, plan: str, body: Callable[[VMemTest, int], None]) -> TestFile:
    t = pnew(name)
    t.describe(
        rule_text=text,
        source=VC,
        context=ctx + " Paging: VA page P0 mapped (bytes 0, 1 = 0x11, 0x01; last 8 bytes "
        "0x11..0x18), P1 = P0 + 4 KiB invalid, the page below P0 unmapped; S-mode with Sv39 (RV64) or Sv32 (RV32), "
        "the test image identity-mapped by root-level superpages.",
        plan=plan,
    )
    paged(t, lambda p1: body(t, p1))
    return t


@rule
def g_vmask_inactive_op() -> TestFile:
    def body(t: VMemTest, p1: int) -> None:
        for ma in (0, 1):
            fill(t, "v8", 0xA5)
            vset(t, "x0", 1, 8, "m1")
            t.li("x6", 0x03)
            t.emit("vmv.s.x v0, x6")
            vset(t, "x0", 4, 8, "m1", 0, ma)
            t.li("x6", p1 - 2)
            lab = vwin(
                t,
                ["vle8.v v8, (x6), v0.t"],
                "ok" if not mut("inactive_faults") else LOAD_PF,
                f"masked vle8.v from P1-2, elements 2-3 inactive, ma={ma}",
                tval=[0, p1],
            )
            store(t, "v8")
            ld_elem(t, "x7", 8, 0)
            t.check("x7", 0x17, lab, "active element 0")
            ld_elem(t, "x7", 8, 3)
            if ma:
                check_agn(t, "x7", 0xA5, 8, lab, "inactive element 3")
            else:
                t.check("x7", 0xA5, lab, "inactive element 3 undisturbed")
        fill(t, "v8", 0x5C)
        vset(t, "x0", 1, 8, "m1")
        t.li("x6", 0x01)
        t.emit("vmv.s.x v0, x6")
        vset(t, "x0", 4, 8, "m1")
        t.li("x6", p1 - 1)
        lab = vwin(
            t,
            ["vse8.v v8, (x6), v0.t"],
            "ok" if not mut("inactive_faults") else STORE_PF,
            "masked vse8.v to P1-1, elements 1-3 inactive",
            tval=[0, p1],
        )
        t.li("x6", p1 - 1)
        t.emit("lbu x7, 0(x6)")
        t.check("x7", 0x5C, lab, "active element 0 stored at P1-1")

    return elem_rule(
        "vmask_inactive_op",
        "Element operations that are masked off (inactive) never generate exceptions.",
        "Inactive elements whose address is in the invalid page must not fault.",
        "e8 m1, vl = 4. 1. v0 = 0x3: vle8.v v8, (P1-2), v0.t (elements 2, 3 inactive and in P1) does not trap, with "
        "mu and ma; element 0 = 0x17; element 3 is undisturbed (mu) or 0xA5/0xFF (ma). 2. v0 = 0x1: vse8.v to P1-1 "
        "(elements 1-3 inactive in P1) does not trap and stores element 0 (0x5C).",
        body,
    )


@rule
def g_vector_inactive_element() -> TestFile:
    def body(t: VMemTest, p1: int) -> None:
        for ma in (0, 1):
            fill(t, "v8", 0xA5)
            vset(t, "x0", 1, 8, "m1")
            t.li("x6", 0x05)
            t.emit("vmv.s.x v0, x6")
            vset(t, "x0", 4, 8, "m1", 1, ma)
            t.li("x6", p1 - 3)
            lab = vwin(
                t,
                ["vle8.v v8, (x6), v0.t"],
                "ok" if not mut("inactive_faults") else LOAD_PF,
                f"masked vle8.v from P1-3, element 3 inactive in P1, ma={ma}",
                tval=[0, p1],
            )
            store(t, "v8")
            for i, v in ((0, 0x16), (2, 0x18)):
                ld_elem(t, "x7", 8, i)
                t.check("x7", v, lab, f"active element {i}")
            for i in (1, 3):
                ld_elem(t, "x7", 8, i)
                if ma:
                    check_agn(t, "x7", 0xA5, 8, lab, f"inactive element {i} (ma)")
                else:
                    t.check(
                        "x7",
                        0xA5 if not mut("inactive_ones_under_mu") else 0xFF,
                        lab,
                        f"inactive element {i} undisturbed (mu)",
                    )

    return elem_rule(
        "vector_inactive_element",
        "The inactive elements do not raise exceptions and do not update any destination vector register group unless "
        "masked agnostic is specified (vtype[vma]=1), in which case inactive elements may be overwritten with 1s.",
        "",
        "e8 m1 ta, vl = 4, v0 = 0x5 (elements 0, 2 active; 1 and 3 inactive), base P1-3 so element 3 is in P1: "
        "vle8.v v8, (P1-3), v0.t does not trap, with mu and ma; elements 0, 2 = 0x16, 0x18; inactive elements 1, 3 "
        "keep 0xA5 (mu) or are each 0xA5 or 0xFF (ma).",
        body,
    )


@rule
def g_vector_tail_element() -> TestFile:
    def body(t: VMemTest, p1: int) -> None:
        for ta in (0, 1):
            fill(t, "v8", 0xA5)
            vset(t, "x0", 2, 8, "m1", ta, 0)
            t.li("x6", p1 - 2)
            lab = vwin(
                t,
                ["vle8.v v8, (x6)"],
                "ok" if not mut("tail_faults") else LOAD_PF,
                f"vle8.v vl=2 from P1-2 (tail elements in P1), ta={ta}",
                tval=[0, p1],
            )
            store(t, "v8")
            ld_elem(t, "x7", 8, 0)
            t.check("x7", 0x17, lab, "body element 0")
            ld_elem(t, "x7", 8, 1)
            t.check("x7", 0x18, lab, "body element 1")
            for off in (2, 3):
                ld_elem(t, "x7", 8, off)
                if ta:
                    check_agn(t, "x7", 0xA5, 8, lab, f"tail element {off} (ta)")
                else:
                    t.check("x7", 0xA5 if not mut("tail_ones_under_tu") else 0xFF, lab, f"tail element {off} (tu)")
        fill(t, "v8", 0xA5)
        t.emit("vsetvli x7, x0, e8, mf2, tu, mu")
        t.li("x6", p1 - 2)
        vset(t, "x0", 2, 8, "mf2", 0, 0)
        lab = vwin(
            t,
            ["vle8.v v8, (x6)"],
            "ok" if not mut("tail_faults") else LOAD_PF,
            "vle8.v mf2 vl=2 from P1-2",
            tval=[0, p1],
        )
        store(t, "v8")
        t.emit("csrr x9, vlenb")
        t.emit("addi x9, x9, -1")
        ld_elem(t, "x7", 8, "x9")
        t.check("x7", 0xA5, lab, "mf2: byte vlenb-1 (past VLMAX, tail) undisturbed with tu")

    return elem_rule(
        "vector_tail_element",
        "The tail elements do not raise exceptions, and do not update any destination vector register group unless "
        "tail agnostic is specified (vtype[vta]=1), in which case tail elements may be overwritten with 1s, or with "
        "the result of the instruction in the case of mask-producing instructions except for mask loads. When LMUL < "
        "1, the tail includes the elements past VLMAX that are held in the same vector register.",
        "Mask-producing tails are vreg_mask_tail_op.",
        "1. e8 m1, vl = 2, with tu and ta: vle8.v v8, (P1-2) does not trap although elements 2.. would be in P1; "
        "elements 0, 1 = 0x17, 0x18; tail elements 2, 3 keep 0xA5 (tu) or are 0xA5/0xFF (ta). 2. e8 mf2 tu, vl = 2: "
        "the same load does not trap and the last byte of v8 (past VLMAX) keeps 0xA5.",
        body,
    )


@rule
def g_vector_prestart_element() -> TestFile:
    def body(t: VMemTest, p1: int) -> None:
        for ta in (0, 1):
            fill(t, "v8", 0xA5)
            vset(t, "x0", 4, 8, "m1", ta, ta)
            t.li("x6", p1 + 0x1000 - 2 if False else p1 - 0x1000 - 2)
            t.emit("csrwi vstart, 2")
            lab = vwin(
                t,
                ["vle8.v v8, (x6)"],
                "ok" if not mut("prestart_faults") else LOAD_PF,
                f"vle8.v vstart=2 from P0-2 (prestart elements below P0), ta={ta}",
                tval=[0, p1 - 0x1000 - 2],
            )
            t.emit("csrr x7, vstart")
            t.check("x7", 0, lab, "vstart = 0 after the load")
            store(t, "v8")
            for i in (0, 1):
                ld_elem(t, "x7", 8, i)
                t.check("x7", 0xA5 if not mut("prestart_updated") else 0, lab, f"prestart element {i} not updated")
            for i, v in ((2, 0x11), (3, 0x01)):  # P0 bytes 0, 1: low bytes of hmem's page signature 0x5a5a0111
                ld_elem(t, "x7", 8, i)
                t.check("x7", v, lab, f"body element {i} loaded from P0 byte {i - 2}")

    return elem_rule(
        "vector_prestart_element",
        "The prestart elements do not raise exceptions and do not update the destination vector register.",
        "The page below P0 is unmapped too (its root-level entry is empty), so prestart elements there would fault.",
        "e8 m1, vl = 4, vstart = 2, with tu mu and ta ma: vle8.v v8, (P0-2): elements 0, 1 (prestart) are in the "
        "unmapped page below P0 and must not fault; elements 2, 3 load P0 bytes 0, 1; prestart elements keep 0xA5 "
        "(even with ta ma); elements 2, 3 = 0x11, 0x01; vstart = 0 afterwards.",
        body,
    )


@rule
def g_vector_active_element() -> TestFile:
    def body(t: VMemTest, p1: int) -> None:
        fill(t, "v8", 0xA5)
        vset(t, "x0", 1, 8, "m1")
        t.li("x6", 0x0B)
        t.emit("vmv.s.x v0, x6")
        vset(t, "x0", 4, 8, "m1")
        t.li("x6", p1 - 3)
        lab = vwin(
            t,
            ["vle8.v v8, (x6), v0.t"],
            LOAD_PF if not mut("active_no_fault") else "ok",
            "masked vle8.v from P1-3, element 3 active in P1",
            tval=[0, p1],
        )
        t.emit("csrr x7, vstart")
        t.check("x7", 3, lab, "vstart = 3 (the faulting active element)")
        t.emit("csrw vstart, x0")
        store(t, "v8")
        ld_elem(t, "x7", 8, 0)
        t.check("x7", 0x16, lab, "active element 0 updated")
        ld_elem(t, "x7", 8, 1)
        t.check("x7", 0x17, lab, "active element 1 updated")
        vset(t, "x0", 4, 8, "m1")
        t.li("x6", p1 - 4)
        lab = mark(t)
        t.emit("vle8.v v8, (x6)")
        store(t, "v8")
        for i in range(4):
            ld_elem(t, "x7", 8, i)
            t.check("x7", 0x15 + i, lab, f"unmasked load in P0: active element {i} updated")

    return elem_rule(
        "vector_active_element",
        "The active elements can raise exceptions and update the destination vector register group.",
        "",
        "e8 m1, vl = 4. 1. v0 = 0xb (elements 0, 1, 3 active, 2 inactive): vle8.v v8, (P1-3), v0.t raises a load "
        "page fault at element 3 (vstart = 3; stval 0 or P1); elements 0, 1 hold 0x16, 0x17. 2. vle8.v v8, (P1-4) "
        "(all in P0) updates elements 0-3 with 0x15-0x18.",
        body,
    )


# ======================================================================== V / Zve subsets
@rule
def g_Zve_eew() -> TestFile:
    t = new("Zve_eew")
    t.describe(
        rule_text="zve32x provides support for EEW of 8, 16, and 32.",
        source=ZVE32X,
        context="Without Zve64x, ELEN = 32 and SEW = 64 is unsupported (vill, norm:vtype_vill_val).",
        plan="For EEW 8, 16, 32: vsetvli e<EEW> m1 leaves vill = 0; vle<EEW>.v, vadd.vv and vse<EEW>.v execute with "
        "vl = 2, and the stored elements equal the loaded ones plus the added ones. Without Zve64x, vsetvli e64 sets "
        "vill.",
    )
    for eew in (8, 16, 32):
        lab = mark(t)
        t.emit(f"vsetvli x7, x0, e{eew}, m1, tu, mu")
        vill_chk(t, lab, f"e{eew}", 0, vtypei(eew))
        vset(t, "x0", 2, eew, "m1")
        t.la("x6", BUF2)
        t.li("x7", 0x01020304)
        t.emit("sw x7, 0(x6)")
        t.emit("sw x7, 4(x6)")
        t.emit(f"vle{eew}.v v1, (x6)")
        t.emit("vadd.vv v2, v1, v1")
        t.la("x6", BUF)
        t.emit(f"vse{eew}.v v2, (x6)")
        ld_elem(t, "x7", 8, 0)
        t.check("x7", 0x08, lab, f"EEW={eew}: element 0 low byte doubled")
    with t.only_if("!" + E64):
        lab = mark(t)
        t.emit("vsetvli x7, x0, e64, m1, tu, mu")
        vill_chk(t, lab, "e64 without Zve64x", 1)
    return t


@rule
def g_V_supported_eew() -> TestFile:
    t = new("V_supported_eew", required=["I", "V"], march=MARCH_V)
    t.describe(
        rule_text="The V extension supports EEW of 8, 16, 32, and 64.",
        source=VST,
        plan="For EEW 8, 16, 32, 64: vsetvli e<EEW> m1 leaves vill = 0 with VLMAX = VLEN/EEW; vle<EEW>.v and "
        "vse<EEW>.v with vl = 1 copy an element (memory round trip of 0x0102030405060708 bytes).",
    )
    t.la("x6", BUF2)
    t.li("x7", 0x05060708)
    t.emit("sw x7, 0(x6)")
    t.li("x7", 0x01020304)
    t.emit("sw x7, 4(x6)")
    for eew in (8, 16, 32, 64):
        lab = mark(t)
        t.emit(f"vsetvli x7, x0, e{eew}, m1, tu, mu")
        vill_chk(t, lab, f"e{eew}", 0 if not (mut("e64_on_v_unsupported") and eew == 64) else 1, vtypei(eew))
        vlmax_chk(t, "x7", eew, "m1", lab, f"e{eew}")
        vset(t, "x0", 1, eew, "m1")
        t.la("x6", BUF2)
        t.emit(f"vle{eew}.v v1, (x6)")
        t.la("x6", BUF)
        t.emit("sw x0, 0(x6)")
        t.emit("sw x0, 4(x6)")
        t.emit(f"vse{eew}.v v1, (x6)")
        ld_elem(t, "x7", 32, 0)
        t.check("x7", 0x05060708 & ((1 << min(eew, 32)) - 1), lab, f"EEW={eew}: low word copied")
        ld_elem(t, "x7", 32, 4)
        t.check("x7", 0x01020304 if eew == 64 else 0, lab, f"EEW={eew}: high word")
    return t


@rule
def g_V_dependent_Zvl128b_Zve64d() -> TestFile:
    t = new("V_dependent_Zvl128b_Zve64d", required=["I", "F", "D", "V"], march=MARCH_D)
    t.describe(
        rule_text="The V vector extension depends upon the Zvl128b and Zve64d extensions.",
        source=VST,
        context="Zvl128b: VLEN >= 128. Zve64d: ELEN = 64 with FP64 vector operations.",
        plan="vlenb >= 16; vsetvli e64 m1 leaves vill = 0 with VLMAX >= 2; vfadd.vv at e64 (1.5 + 2.25 = 3.75) and at "
        "e32 execute and give the IEEE sums.",
    )
    lab = mark(t)
    t.emit("csrr x7, vlenb")
    t.emit("sltiu x8, x7, 16")
    t.check("x8", 0 if not mut("vlenb_lt_16") else 1, lab, "vlenb >= 16 (VLEN >= 128)")
    t.emit("vsetvli x7, x0, e64, m1, tu, mu")
    vill_chk(t, lab, "e64 m1", 0, vtypei(64))
    with t.rv64_only():
        vset(t, "x0", 1, 64, "m1")
        t.load("x6", X(0, 0x3FF8000000000000), "1.5")
        t.emit("vmv.s.x v1, x6")
        t.load("x6", X(0, 0x4002000000000000), "2.25")
        t.emit("vmv.s.x v2, x6")
        lab = mark(t)
        t.emit("vfadd.vv v3, v1, v2")
        t.emit("vmv.x.s x7, v3")
        t.check("x7", X(0, 0x400E000000000000), lab, "vfadd.vv e64 1.5 + 2.25")
    vset(t, "x0", 1, 32, "m1")
    t.li("x6", 0x3FC00000)
    t.emit("vmv.s.x v1, x6")
    t.li("x6", 0x40100000)
    t.emit("vmv.s.x v2, x6")
    lab = mark(t)
    t.emit("vfadd.vv v3, v1, v2")
    t.emit("vmv.x.s x7, v3")
    t.check("x7", 0x40700000, lab, "vfadd.vv e32 1.5 + 2.25")
    return t


@rule
def g_V_instr_int() -> TestFile:
    t = new("V_instr_int", required=["I", "V"], march=MARCH_V)
    t.describe(
        rule_text="The V extension supports all vector integer instructions (<<sec-vector-integer>>).",
        source=VST,
        context="The distinguishing case is SEW = 64: Zve64x omits vmulh, vmulhu, vmulhsu (.vv and .vx) at EEW = 64 "
        "(norm:Zve64_eew64_nsupport_vmulh), but V includes them. Their results are the high 64 bits of the 128-bit "
        "product.",
        plan="e64, vl = 1 (RV64 scalar operands; on RV32 vmv.v.x sign-extends): a = 2^62, b = 4 (via vmv.v.i/vsll): "
        "vmulh.vv, vmulh.vx, vmulhu.vv, vmulhu.vx, vmulhsu.vv, vmulhsu.vx all give 1; vdivu.vv of a by 4 gives "
        "2^60 (high word on RV32 checked through vsrl).",
    )
    vset(t, "x0", 1, 64, "m1")
    t.emit("vmv.v.i v1, 1")
    t.li("x6", 62)
    t.emit("vsll.vx v1, v1, x6  // a = 2^62")
    t.emit("vmv.v.i v2, 4  // b = 4")
    t.li("x7", 4)
    for insn in (
        "vmulh.vv v3, v1, v2",
        "vmulh.vx v3, v1, x7",
        "vmulhu.vv v3, v1, v2",
        "vmulhu.vx v3, v1, x7",
        "vmulhsu.vv v3, v1, v2",
        "vmulhsu.vx v3, v1, x7",
    ):
        lab = vwin(t, [insn], "ok" if not mut("vmulh_e64_illegal") else ILLEGAL, f"{insn} at e64")
        t.emit("vmv.x.s x8, v3")
        t.check("x8", 1, lab, f"{insn} at e64: high half of 2^62*4")
    lab = mark(t)
    t.emit("vdivu.vv v3, v1, v2")
    t.li("x6", 60)
    t.emit("vsrl.vx v3, v3, x6")
    t.emit("vmv.x.s x8, v3")
    t.check("x8", 1, lab, "vdivu.vv at e64: 2^62/4 = 2^60")
    return t


@rule
def g_V_instr_fixedpt() -> TestFile:
    t = new("V_instr_fixedpt", required=["I", "V"], march=MARCH_V)
    t.describe(
        rule_text="The V extension supports all vector fixed-point arithmetic instructions "
        "(<<sec-vector-fixed-point>>).",
        source=VST,
        context="The distinguishing case: Zve64x omits vsmul.vv/vx at EEW = 64 (norm:Zve64_eew64_nsupport_vsmul), V "
        "includes them. vsmul: (a*b) >> (SEW-1) with vxrm rounding, saturating.",
        plan="e64, vl = 1, vxrm = rnu: a = b = 2^62 (0.5 in Q63): vsmul.vv and vsmul.vx give 2^61 (0.25), read as "
        "vsrl 61 = 1; vxsat stays 0. vsadd.vv at e64 of 2^62 + 2^62 saturates to 2^63-1 and sets vxsat.",
    )
    t.emit("csrwi vcsr, 0")
    vset(t, "x0", 1, 64, "m1")
    t.emit("vmv.v.i v1, 1")
    t.li("x6", 62)
    t.emit("vsll.vx v1, v1, x6")
    t.emit("vmv.v.i v2, 1")
    t.emit("vsll.vx v2, v2, x6")
    with t.rv64_only():
        t.load("x7", X(0, 1 << 62), "2^62")
    with t.rv32_only():
        t.emit("li x7, 0x40000000  // vsmul.vx sign-extends x7: 2^30 at e64")
    for insn in ("vsmul.vv v3, v1, v2", "vsmul.vx v3, v1, x7"):
        lab = vwin(t, [insn], "ok" if not mut("vsmul_e64_illegal") else ILLEGAL, f"{insn} at e64")
        t.li("x6", 61 if "vv" in insn else 0)
        if "vx" in insn:
            with t.rv64_only():
                t.li("x6", 61)
            with t.rv32_only():
                t.li("x6", 29)  # 2^62 * 2^30 >> 63 = 2^29
        t.emit("vsrl.vx v4, v3, x6")
        t.emit("vmv.x.s x8, v4")
        t.check("x8", 1, lab, f"{insn}: product")
    t.emit("csrr x8, vxsat")
    lab = mark(t)
    t.check_masked("x8", 1, 0, lab, "vsmul did not saturate")
    t.emit("vsadd.vv v3, v1, v1")
    t.emit("csrr x8, vxsat")
    t.check_masked("x8", 1, 1, lab, "vsadd e64 saturates and sets vxsat")
    t.emit("csrwi vcsr, 0")
    return t


@rule
def g_egs_vl_avl() -> TestFile:
    zvk = ["Zvkg", "Zvkned", "Zvknha", "Zvknhb", "Zvksed", "Zvksh"]
    t = new("egs_vl_avl", required=["I", "Zve32x", zvk])
    t.describe(
        rule_text="When element group instructions are present, an additional constraint is placed on the setting of "
        "vl based on an AVL value (augmenting <<constraints-on-setting-vl>>). EGSMAX is the largest EGS supported by "
        "the implementation. When AVL > VLMAX, the value of vl must be set to either VLMAX or a positive integer "
        "multiple of EGSMAX.",
        source=VC,
        context="EGS is 4 for Zvkg, Zvkned, Zvknh[ab] and Zvksed, and 8 for Zvksh, so EGSMAX = 8 with Zvksh and 4 "
        "otherwise among these. VLMAX < AVL < 2*VLMAX leaves vl in [ceil(AVL/2), VLMAX] (norm:vl_val_list); the "
        "added constraint is vl == VLMAX or vl % EGSMAX == 0.",
        plan="At e32 m1, e32 m4 and e8 m1 (VLMAX = V): AVL = V+1, V+3, 3V/2+1, 2V-2: vl satisfies the base range and "
        "(vl == V or vl mod EGSMAX == 0).",
    )
    for sew, lm in ((32, "m1"), (32, "m4"), (8, "m1")):
        t.emit(f"vsetvli x8, x0, {vt(sew, lm)}")
        for setsrc, d in (
            ("addi x6, x8, 1", "V+1"),
            ("addi x6, x8, 3", "V+3"),
            ("srli x6, x8, 1;add x6, x6, x8;addi x6, x6, 1", "3V/2+1"),
            ("slli x6, x8, 1;addi x6, x6, -2", "2V-2"),
        ):
            for ln in setsrc.split(";"):
                t.emit(ln)
            lab = mark(t)
            t.emit(f"vsetvli x7, x6, {vt(sew, lm)}")
            vl_pred(t, "x6", "x7", "x8", lab, f"e{sew} {lm} AVL={d}")
            t.emit("#ifdef ZVKSH_SUPPORTED", 0)
            t.emit("andi x9, x7, 7")
            t.emit("#else", 0)
            t.emit("andi x9, x7, 3")
            t.emit("#endif", 0)
            t.emit("seqz x9, x9  // vl multiple of EGSMAX")
            t.emit("xor x1, x7, x8")
            t.emit("seqz x1, x1  // vl == VLMAX")
            t.emit("or x9, x9, x1")
            if mut("egs_any_vl"):
                t.emit("li x9, 1")
                t.emit("addi x1, x6, -1")
                t.emit("xor x1, x1, x7")
                t.emit("seqz x9, x1")
            t.check_bool("x9", lab, f"e{sew} {lm} AVL={d}: vl == VLMAX or a multiple of EGSMAX")
    return t


# ======================================================================== main
def gen(names: list[str] | None = None) -> list[TestFile]:
    tests: list[TestFile] = []
    for name, fn in ALL.items():
        if names and name not in names:
            continue
        tests += fn()
    return tests


if __name__ == "__main__":
    ts = gen(sys.argv[1:] or None)
    for tf in ts:
        tf.write()
    print(f"wrote {len(ts)} tests to {Path(__file__).resolve().parents[1] / out()}")
