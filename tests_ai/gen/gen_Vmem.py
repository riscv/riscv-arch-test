#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate the vector memory rule-derived tests in tests_ai/V (vector loads and stores, alignment, memory order).

Rules are the norm: tags in src/unpriv/vector-common.adoc sections "Vector Loads and Stores", "Vector Memory
Alignment Constraints" and "Vector Memory Consistency Model". Tests use integer vector instructions only. Rules
about faults mid-instruction (vstart, fault-only-first, masked-off elements, segment faults) boot to S-mode and
place a page fault at a chosen element with a page table (vmemlib.Pages); the others run unprivileged.

Usage: gen_Vmem.py [rule ...]   (default: every rule)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from svlib import guard
from vmemlib import (
    FILL,
    ILLEGAL,
    LEAF,
    LOAD_AF,
    LOAD_MIS,
    LOAD_PF,
    MARCH,
    POOL_TRAP,
    REQ,
    REQ_S,
    RO,
    STORE_AF,
    STORE_MIS,
    STORE_PF,
    VEC,
    Pages,
    VTest,
    both,
    elems,
    fill_elem,
    le,
    lmul_for,
    ones,
    pat,
    sx,
)

SUITE = "Vmem"
MUT = os.environ.get("AI_MUTANT", "")  # mutate.py: model a plausible bug in the expectations

MUTANTS = {
    "eew_from_sew": "unit-stride and strided loads use SEW instead of the encoded EEW",
    "emul_is_lmul": "a unit-stride load whose EMUL exceeds LMUL writes only the first LMUL registers",
    "index_scaled": "indexed offsets are scaled by the data element size",
    "index_sign_extended": "narrow index offsets are sign-extended",
    "index_emul_is_lmul": "index elements are read from a group of LMUL registers (EMUL ignored)",
    "stride_ignored": "a constant-stride access uses unit stride",
    "zero_stride_unit": "stride 0 (or rs2=x0) is treated as unit stride",
    "mask_evl_vl": "vlm.v/vsm.v transfer vl bytes instead of ceil(vl/8)",
    "vlm_lmul_aligned": "vlm.v requires its destination to be LMUL-aligned (illegal-instruction)",
    "wholereg_vl": "whole-register loads transfer only vl elements",
    "wholereg_vill_illegal": "whole-register loads raise illegal-instruction when vtype.vill=1",
    "wholereg_vstart_bytes": "whole-register loads count vstart in bytes whatever the encoded EEW",
    "wholereg_nf_minus1": "vl<n>r loads n-1 registers",
    "wholereg_aligned_traps": "an EEW-aligned whole-register base still raises address-misaligned",
    "vstart_restart_0": "a load resumed with vstart > 0 reloads the prestart elements",
    "vstart_plus1": "a trap mid-instruction reports vstart = faulting element + 1",
    "vstore_restart_0": "a store resumed with vstart > 0 rewrites the prestart elements",
    "xtval_base": "a page fault mid-instruction reports the instruction's base address in stval",
    "masked_off_faults": "inactive elements on an absent page raise the page fault",
    "inactive_written_mu": "masked loads with vma=0 overwrite inactive elements with memory data",
    "ff_traps_late": "fault-only-first loads trap on a fault at element > 0",
    "ff_vl_unchanged": "a fault-only-first load that suppresses a fault at element > 0 leaves vl unchanged",
    "ff_elem0_trims": "a fault-only-first fault on element 0 sets vl = 0 instead of trapping",
    "ff_vl_plus1": "fault-only-first trims vl to the faulting index + 1",
    "ff_zero_progress": "a fault-only-first load without a fault may set vl = 0",
    "ff_tail_clobbered": "fault-only-first writes ones into elements past the original vl",
    "seg_vstart_fields": "segment accesses report vstart in fields (segment * NFIELDS + field)",
    "seg_fields_reversed": "segment loads and stores put the last field in vd/vs3",
    "seg_mask_ignored": "masked segment accesses transfer the fields of inactive segments",
    "seg_stride_is_size": "strided segment accesses use the segment size as stride",
    "nfields_minus1": "a segment load moves nf fields (NFIELDS - 1)",
    "ordered_first_wins": "indexed-ordered stores to one address leave the first element's value",
    "unordered_last_vstart": "an indexed-unordered store fault reports vstart = vl - 1",
    "program_order_stale": "a vector load after a scalar store to the same bytes reads the old value",
    "misaligned_e8_traps": "an EEW=8 load at an odd address raises address-misaligned",
    "seg_partial_garbage": "a faulting segment store writes zeros into its partially stored segment",
}


def out() -> str:
    """The directory tests are written to: V, or the mutant directory."""
    return "V" if SUITE == "Vmem" else SUITE


def new(rule: str, *, s: bool = False, **kw: object) -> VTest:
    """A test for rule: unprivileged (lowest mode), or booted to S-mode with s=True (page-table tests)."""
    kw.setdefault("march", MARCH)
    kw.setdefault("pool", POOL_TRAP)
    if s:
        kw.setdefault("boot", "S")
    return VTest(out(), rule, required=REQ_S if s else REQ, **kw)


def describe(t: VTest, text: str, plan: str, context: str = "", issues: str = "") -> None:
    t.describe(rule_text=text, source=VEC, context=context, issues=issues, plan=plan)


PRECISE = (
    "vector-common.adoc Exception Handling (epc_vstart_op_V_trap): on a trap during a vector instruction, xepc points "
    "to the instruction and vstart holds the element index on which the trap was taken. Precise traps commit every "
    "element before vstart; elements at or after vstart may have been updated. The current standard extensions have "
    "no imprecise traps."
)
PRESTART = (
    "Prestart elements (index < vstart) raise no exceptions and do not update the destination "
    "(vector_prestart_element)."
)
STVAL = "stval is 0 or the faulting element's virtual address (supervisor.adoc stval_op_faulting_addr)."
SPACE = "Fault tests run in S-mode under Sv39 (RV64) or Sv32 (RV32), probed; they pass trivially without it."
F = FILL
M5C = 0x5C5C5C5C


def fe(eew: int) -> int:
    return fill_elem(eew)


def store_vals(eew: int, n: int, seed: int) -> list[int]:
    """n distinct EEW-bit values for store sources (pattern bytes, so never all ones or the fill)."""
    return elems(pat(seed, n * eew // 8), 0, eew, n)


def words(img: bytes | bytearray, lo: int, hi: int) -> list[int]:
    return [le(img[a : a + 4]) for a in range(lo, hi, 4)]


def restore(t: VTest, lab: str, data: bytes, lo: int, hi: int) -> None:
    """Rewrite lab[lo:hi) (word aligned) with data's bytes. Clobbers x7, x9."""
    t.la("x9", f"{lab}+{lo}")
    for a in range(lo, hi, 4):
        w = le(data[a : a + 4])
        t.li("x7", w - (1 << 32) if w >> 31 else w)
        t.emit(f"sw x7, {a - lo}(x9)")


def marker(t: VTest, lab: str, offs: list[int], value: int = 0x0BADF00D) -> None:
    """Store a marker word at lab+off for each off (physical, through the identity map). Clobbers x7, x9."""
    t.la("x9", lab)
    t.li("x7", value)
    for o in offs:
        t.emit(f"li x8, {o}")
        t.emit("add x8, x8, x9")
        t.emit("sw x7, 0(x8)")


def trapped(t: VTest, reg: str = "x1") -> None:
    """reg = 1 if the window just closed took a trap (x14 = cause), else 0."""
    t.emit(f"addi {reg}, x14, 1")
    t.emit(f"snez {reg}, {reg}")


def set_vstart(t: VTest, v: int) -> None:
    t.emit(f"li x7, {v}")
    t.emit("csrw vstart, x7")


# ================================================================ basic transfer
def t_load_store_semantics() -> VTest:
    t = new("vector_load_store_semantics")
    describe(
        t,
        "Vector loads and stores move values between vector registers and memory.",
        "The register image of a load is the memory image: vle8.v of 16 bytes then vse32.v of the same register "
        "as 4 words writes the same 16 bytes; vle64.v of 2 doublewords then vse16.v as 8 halfwords likewise. "
        "Every byte of each register and of the destination is checked, and the word after the stores is "
        "unchanged.",
    )
    src = pat(2, 64)
    s = t.buf("src", src)
    d0 = bytes([0x5C]) * 64
    d = t.buf("dst", d0)
    t.vfill(8, 2)
    t.vset(16, 8)
    t.la("x6", s)
    t.mark("vle8")
    t.emit("vle8.v v8, (x6)")
    t.ck_reg(8, 8, list(src[:16]), "vle8.v loads 16 bytes")
    t.vset(4, 32)
    t.la("x6", d)
    t.mark("vse32")
    t.emit("vse32.v v8, (x6)")
    t.ck_mem(d, 0, [*words(src, 0, 16), M5C], "vse32.v writes the bytes vle8.v loaded")
    t.vset(2, 64)
    t.la("x6", f"{s}+16")
    t.mark("vle64")
    t.emit("vle64.v v9, (x6)")
    t.ck_reg(9, 32, words(src, 16, 32), "vle64.v loads 2 doublewords (read as words)")
    t.vset(8, 16)
    t.la("x6", f"{d}+16")
    t.mark("vse16")
    t.emit("vse16.v v9, (x6)")
    t.ck_mem(d, 16, [*words(src, 16, 32), M5C], "vse16.v writes the bytes vle64.v loaded")
    return t


def t_unit_stride_op() -> VTest:
    t = new("vector_ls_unit_stride_op")
    describe(
        t,
        "Vector unit-stride operations access elements stored contiguously in memory starting from the base "
        "effective address.",
        "For each EEW (8, 16, 32, 64; SEW = EEW, LMUL = 1): vle<EEW>.v with vl = 4 (2 for EEW=64) from a base that "
        "is element aligned but not 16-byte aligned loads element i from base + i*EEW/8 (every loaded element "
        "checked; the next element is a tail element and stays undisturbed with tu). vse<EEW>.v of that register "
        "writes the elements contiguously from another base and leaves the words around them unchanged.",
    )
    src = pat(1, 128)
    s = t.buf("src", src)
    d0 = bytes([0x5C]) * 128
    d = t.buf("dst", d0)
    for eew in (8, 16, 32, 64):
        eb = eew // 8
        nel = min(4, 128 // eew)
        off = 3 * eb if eew < 64 else 8
        t.vfill(8)
        t.vset(nel, eew)
        t.la("x6", f"{s}+{off}")
        t.mark(f"vle{eew}")
        t.emit(f"vle{eew}.v v8, (x6)")
        exp = elems(src, off, eew, nel)
        n = min(16 // eb, nel + 1)
        t.ck_reg(8, eew, [*exp, fe(eew)][:n], f"vle{eew}.v loads element i from base + i*{eb}")
        off2 = 5 * eb if eew < 64 else 24
        t.vset(nel, eew)
        t.la("x6", f"{d}+{off2}")
        t.mark(f"vse{eew}")
        t.emit(f"vse{eew}.v v8, (x6)")
        img = bytearray(d0)
        img[off2 : off2 + nel * eb] = src[off : off + nel * eb]
        lo, hi = off2 // 4 * 4 - 4, (off2 + nel * eb + 3) // 4 * 4 + 4
        t.ck_mem(d, lo, words(img, lo, hi), f"vse{eew}.v writes contiguous elements")
        restore(t, d, d0, 0, 64)
    return t


def t_strided_eew() -> VTest:
    t = new("vector_ls_strided_eew")
    describe(
        t,
        "Vector memory unit-stride and constant-stride operations directly encode EEW of the data to be "
        "transferred statically in the instruction to reduce the number of vtype changes when accessing memory "
        "in a mixed-width routine.",
        "The data width is the encoded EEW, not SEW, and vl counts EEW elements:\n"
        "- SEW=8, LMUL=1, vl=3: vle32.v v8 (EMUL=4) loads 3 words; word 3 (tail, tu) stays undisturbed.\n"
        "- SEW=64, LMUL=1, vl=2: vle8.v (EMUL=1/8) loads 2 bytes; byte 2 (tail) stays undisturbed.\n"
        "- SEW=32, LMUL=1, vl=3: vlse16.v with stride 6 loads 3 halfwords; halfword 3 stays undisturbed.\n"
        "- SEW=8, LMUL=1, vl=3: vsse64.v with stride 16 writes 3 doublewords and nothing between them; vse16.v "
        "writes 6 bytes and leaves byte 6 onward unchanged.",
    )
    src = pat(3, 128)
    s = t.buf("src", src)
    d0 = bytes([0x5C]) * 64
    d = t.buf("dst", d0)
    bad = MUT == "eew_from_sew"
    t.vfill(8, 4)
    t.vset(3, 8)
    t.la("x6", s)
    t.mark("vle32_sew8")
    t.emit("vle32.v v8, (x6)")
    exp = [le(src[0:3] + bytes([F])), fe(32), fe(32), fe(32)] if bad else [*elems(src, 0, 32, 3), fe(32)]
    t.ck_reg(8, 32, exp, "vle32.v at SEW=8: 3 words")
    t.vfill(8)
    t.vset(2, 64)
    t.la("x6", f"{s}+5")
    t.mark("vle8_sew64")
    t.emit("vle8.v v8, (x6)")
    t.ck_reg(8, 8, list(src[5:8]) if bad else [*src[5:7], F], "vle8.v at SEW=64: 2 bytes")
    t.vfill(8)
    t.vset(3, 32)
    t.la("x6", s)
    t.li("x1", 6)
    t.mark("vlse16_sew32")
    t.emit("vlse16.v v8, (x6), x1")
    t.ck_reg(8, 16, [*elems(src, 0, 16, 3, 6), fe(16)], "vlse16.v at SEW=32: 3 halfwords")
    vals = store_vals(64, 3, 31)
    t.vload(16, 64, vals, "sv64")
    t.vset(3, 8)
    t.la("x6", d)
    t.li("x1", 16)
    t.mark("vsse64_sew8")
    t.emit("vsse64.v v16, (x6), x1")
    img = bytearray(d0)
    for i, v in enumerate(vals):
        img[16 * i : 16 * i + 8] = v.to_bytes(8, "little")
    t.ck_mem(d, 0, words(img, 0, 48), "vsse64.v at SEW=8 writes 3 doublewords")
    restore(t, d, d0, 0, 48)
    hv = store_vals(16, 3, 32)
    t.vload(16, 16, hv, "sv16")
    t.vset(3, 8)
    t.la("x6", d)
    t.mark("vse16_sew8")
    t.emit("vse16.v v16, (x6)")
    img = bytearray(d0)
    for i, v in enumerate(hv):
        img[2 * i : 2 * i + 2] = v.to_bytes(2, "little")
    t.ck_mem(d, 0, words(img, 0, 12), "vse16.v at SEW=8 writes 6 bytes")
    return t


# ================================================================ indexed
def indexed_case(
    t: VTest,
    src: bytes,
    s: str,
    sew: int,
    lmul: str,
    ieew: int,
    idx: list[int],
    insn: str,
    desc: str,
    name: str,
) -> None:
    """Indexed load v8 <- src at s + idx[i] (index group v16), data SEW/LMUL, index EEW ieew."""
    n = len(idx)
    t.vload(16, ieew, idx, f"idx{name}")
    t.vfill(8, 2)
    t.vset(n, sew, lmul)
    t.la("x6", s)
    t.mark(insn.split(".")[0])
    t.emit(f"{insn} v8, (x6), v16")
    sc = (sew // 8) if MUT == "index_scaled" else 1
    exp = [le(src[i * sc : i * sc + sew // 8]) for i in idx]
    tail = [fe(sew)] if (n + 1) * sew // 8 <= 16 else []
    t.ck_reg(8, sew, exp + tail, desc)


def t_indexed_eew() -> VTest:
    t = new("vector_ls_indexed_eew")
    describe(
        t,
        "Indexed operations use the explicit EEW encoding in the instruction to set the size of the indices used, "
        "and use SEW/LMUL to specify the data width.",
        "Index width from the instruction, data width from SEW:\n"
        "- SEW=32: vluxei8.v with byte offsets {12, 0, 8, 4} loads 4 words.\n"
        "- SEW=8: vluxei32.v with offsets {5, 0, 3, 7} (32-bit indices) loads 4 bytes (byte 4, tail, undisturbed).\n"
        "- SEW=64: vloxei16.v with offsets {8, 0} loads 2 doublewords.\n"
        "- SEW=16: vsuxei8.v with offsets {6, 0, 2} stores 3 halfwords there and nothing else.",
    )
    src = pat(4, 128)
    s = t.buf("src", src)
    indexed_case(t, src, s, 32, "m1", 8, [12, 0, 8, 4], "vluxei8.v", "vluxei8.v at SEW=32", "a")
    indexed_case(t, src, s, 8, "m1", 32, [5, 0, 3, 7], "vluxei32.v", "vluxei32.v at SEW=8", "b")
    indexed_case(t, src, s, 64, "m1", 16, [8, 0], "vloxei16.v", "vloxei16.v at SEW=64", "c")
    d0 = bytes([0x5C]) * 32
    d = t.buf("dst", d0)
    vals = store_vals(16, 3, 41)
    t.vload(12, 16, vals, "sv")
    t.vload(16, 8, [6, 0, 2], "idxd")
    t.vset(3, 16)
    t.la("x6", d)
    t.mark("vsuxei8")
    t.emit("vsuxei8.v v12, (x6), v16")
    img = bytearray(d0)
    for o, v in zip([6, 0, 2], vals):
        o2 = o * 2 if MUT == "index_scaled" else o
        img[o2 : o2 + 2] = v.to_bytes(2, "little")
    t.ck_mem(d, 0, words(img, 0, 16), "vsuxei8.v at SEW=16")
    return t


def t_indexed_op() -> VTest:
    t = new("vector_ls_indexed_op")
    describe(
        t,
        "Vector indexed operations add the contents of each element of the vector offset operand specified by "
        "`vs2` to the base effective address to give the effective address of each element. The data vector "
        "register group has EEW=SEW, EMUL=LMUL, while the offset vector register group has EEW encoded in the "
        "instruction and EMUL=(EEW/SEW)*LMUL.",
        "- SEW=32, LMUL=1, index EEW=16 (EMUL=1/2): vluxei16.v and vloxei16.v with offsets {16, 4, 28, 0} load the "
        "words at base + offset.\n"
        "- SEW=8, LMUL=1, index EEW=32 (EMUL=4, v16-v19), vl=16: vloxei32.v loads 16 bytes, each at base + its "
        "offset; at VLEN=128 the offsets come from all four index registers.\n"
        "- SEW=32, LMUL=2 (data group v12-v13), index EEW=16 (EMUL=1), vl=6: vsoxei16.v stores 6 words, each at "
        "base + its offset (at VLEN=128 elements 4-5 come from v13).",
    )
    src = pat(5, 160)
    s = t.buf("src", src)
    for insn in ("vluxei16.v", "vloxei16.v"):
        indexed_case(t, src, s, 32, "m1", 16, [16, 4, 28, 0], insn, f"{insn} at SEW=32", insn[:5])
    idx = [(i * 37) % 128 for i in range(16)]
    t.vload(16, 32, idx, "idxw", "m4")
    t.vfill(8)
    t.vset(16, 8)
    t.la("x6", s)
    t.mark("vloxei32")
    t.emit("vloxei32.v v8, (x6), v16")
    exp = [src[idx[i % 4]] for i in range(16)] if MUT == "index_emul_is_lmul" else [src[i] for i in idx]
    t.ck_reg(8, 8, exp, "vloxei32.v at SEW=8 (index EMUL=4)")
    d0 = bytes([0x5C]) * 64
    d = t.buf("dst", d0)
    vals = store_vals(32, 6, 51)
    t.vload(12, 32, vals, "sv", "m2")
    offs = [20, 0, 8, 4, 16, 12]
    t.vload(16, 16, offs, "idxs")
    t.vset(6, 32, "m2")
    t.la("x6", d)
    t.mark("vsoxei16")
    t.emit("vsoxei16.v v12, (x6), v16")
    img = bytearray(d0)
    for o, v in zip(offs, vals):
        img[o : o + 4] = v.to_bytes(4, "little")
    t.ck_mem(d, 0, words(img, 0, 28), "vsoxei16.v at SEW=32, LMUL=2")
    return t


def t_bytewise() -> VTest:
    t = new("vector_ls_bytewise")
    describe(
        t,
        "The vector offset operand is treated as a vector of byte-address offsets.",
        "Offsets are not scaled by the element size: SEW=32 with offsets {4, 8, 0, 12} (vluxei8.v); SEW=16 with "
        "{2, 6, 0, 14} (vluxei16.v); SEW=8 with {1, 3, 2, 0} (vloxei8.v); SEW=64 with {8, 0} (vluxei32.v). A "
        "scaled offset would read a different (distinct) location. A store, vsuxei8.v at SEW=32 with offsets "
        "{8, 0}, writes at those byte offsets.",
    )
    src = pat(6, 160)
    s = t.buf("src", src)
    indexed_case(t, src, s, 32, "m1", 8, [4, 8, 0, 12], "vluxei8.v", "SEW=32 byte offsets", "a")
    indexed_case(t, src, s, 16, "m1", 16, [2, 6, 0, 14], "vluxei16.v", "SEW=16 byte offsets", "b")
    indexed_case(t, src, s, 8, "m1", 8, [1, 3, 2, 0], "vloxei8.v", "SEW=8 byte offsets", "c")
    indexed_case(t, src, s, 64, "m1", 32, [8, 0], "vluxei32.v", "SEW=64 byte offsets", "d")
    d0 = bytes([0x5C]) * 80
    d = t.buf("dst", d0)
    vals = store_vals(32, 2, 61)
    t.vload(12, 32, vals, "sv")
    t.vload(16, 8, [8, 0], "idxs")
    t.vset(2, 32)
    t.la("x6", d)
    t.mark("vsuxei8")
    t.emit("vsuxei8.v v12, (x6), v16")
    img = bytearray(d0)
    sc = 4 if MUT == "index_scaled" else 1
    for o, v in zip([8, 0], vals):
        img[o * sc : o * sc + 4] = v.to_bytes(4, "little")
    t.ck_mem(d, 0, words(img, 0, 36), "vsuxei8.v at SEW=32")
    return t


def t_xlen_dep() -> VTest:
    t = new("vector_ls_xlen_dep")
    describe(
        t,
        "If the vector offset elements are narrower than XLEN, they are zero-extended to XLEN before adding to the "
        "base effective address. If the vector offset elements are wider than XLEN, the least-significant XLEN "
        "bits are used in the address calculation.",
        "Zero extension of narrow offsets:\n"
        "- index EEW=8, SEW=8: offsets {0xff, 0x80, 0x01} read base+255, base+128, base+1 (not base-1, base-128).\n"
        "- index EEW=16, SEW=32: base = L - 0x8000, offsets {0x8000, 0x8004} read L and L+4.\n"
        "- RV64, index EEW=32: base = L - 0x80000000, offsets {0x80000000, 0x80000004} read L and L+4.\n"
        "Offsets as wide as XLEN wrap modulo 2^XLEN: RV32 index EEW=32 and RV64 index EEW=64 with base = L+16 and "
        "offsets {-16, -12} read L and L+4. A sign-extending design reads elsewhere (a different value, or an "
        "access fault that fails the test).",
        context="Offsets wider than XLEN (EEW=64 on RV32) are not supported by V (v-st-ext.adoc "
        "V_instr_ls_eew64_nsupported_xlen32; such encodings are reserved, vector_ls_eew_rsv), so the truncation "
        "half of the rule has no legal instance on V harts.",
    )
    big = pat(7, 256)
    b = t.buf("big", big)
    sxt = MUT == "index_sign_extended"
    t.vload(16, 8, [0xFF, 0x80, 0x01], "i8")
    t.vfill(8)
    t.vset(3, 8)
    t.la("x6", f"{b}+0")
    t.mark("vluxei8")
    t.emit("vluxei8.v v8, (x6), v16")
    t.ck_reg(8, 8, [F, F, big[1]] if sxt else [big[255], big[128], big[1]], "8-bit offsets zero-extended")
    t.vload(16, 16, [0x8000, 0x8004], "i16")
    t.vfill(8)
    t.vset(2, 32)
    t.la("x6", b)
    t.li("x7", 0x8000)
    t.emit("sub x6, x6, x7")
    t.mark("vluxei16")
    t.emit("vluxei16.v v8, (x6), v16")
    t.ck_reg(8, 32, [fe(32), fe(32)] if sxt else elems(big, 0, 32, 2), "16-bit offsets zero-extended")
    with t.rv64_only():
        t.vload(16, 32, [0x80000000, 0x80000004], "i32")
        t.vfill(8)
        t.vset(2, 32)
        t.la("x6", b)
        t.emit("li x7, 0x80000000")
        t.emit("sub x6, x6, x7")
        t.mark("vluxei32")
        t.emit("vluxei32.v v8, (x6), v16")
        t.ck_reg(8, 32, elems(big, 0, 32, 2), "RV64: 32-bit offsets zero-extended")
        t.vload(16, 64, [(1 << 64) - 16, (1 << 64) - 12], "i64")
        t.vfill(8)
        t.vset(2, 32)
        t.la("x6", f"{b}+16")
        t.mark("vluxei64")
        t.emit("vluxei64.v v8, (x6), v16")
        t.ck_reg(8, 32, elems(big, 0, 32, 2), "RV64: 64-bit offsets wrap modulo 2^64")
    with t.rv32_only():
        t.vload(16, 32, [(1 << 32) - 16, (1 << 32) - 12], "i32w")
        t.vfill(8)
        t.vset(2, 32)
        t.la("x6", f"{b}+16")
        t.mark("vluxei32w")
        t.emit("vluxei32.v v8, (x6), v16")
        t.ck_reg(8, 32, elems(big, 0, 32, 2), "RV32: 32-bit offsets wrap modulo 2^32")
    return t


def t_indexed_eew_emul() -> VTest:
    t = new("vector_ls_indexed_eew_emul")
    describe(
        t,
        "Vector unit-stride and constant-stride use the EEW/EMUL encoded in the instruction for the data values, "
        "while vector indexed loads and stores use the EEW/EMUL encoded in the instruction for the index values "
        "and the SEW/LMUL encoded in vtype for the data values.",
        "- SEW=32, LMUL=2, vl=8: vluxei8.v (index EMUL=1/2) fills the data group v8-v9 with 8 words (at VLEN=128 "
        "words 4-7 land in v9).\n"
        "- SEW=32, LMUL=2, vl=8: vle16.v and vlse16.v (stride 2) have data EMUL=1: 8 halfwords in v8, and v9 is not "
        "written.\n"
        "- SEW=8, LMUL=1, vl=4: vsuxei64.v (RV64) / vsuxei32.v (RV32) store bytes (data EEW = SEW) at the offsets.",
    )
    src = pat(8, 128)
    s = t.buf("src", src)
    idx = [28, 0, 4, 24, 8, 20, 12, 16]
    t.vload(20, 8, idx, "i8")
    t.vfill(8, 2)
    t.vset(8, 32, "m2")
    t.la("x6", s)
    t.mark("vluxei8")
    t.emit("vluxei8.v v8, (x6), v20")
    t.ck_reg(8, 32, [le(src[i : i + 4]) for i in idx], "vluxei8.v data group v8-v9")
    bad = MUT == "eew_from_sew"
    for insn in ("vle16.v v8, (x6)", "vlse16.v v8, (x6), x1"):
        t.vfill(8, 2)
        t.vset(8, 32, "m2")
        t.la("x6", s)
        t.li("x1", 2)
        t.mark(insn.split(".")[0])
        t.emit(insn)
        t.ck_reg(8, 16, elems(src, 0, 16, 8, 4 if bad else 2), f"{insn.split()[0]} data EMUL=1")
        t.ck_elem(9, 0, 32, fe(32), f"{insn.split()[0]}: v9 not written")
    d0 = bytes([0x5C]) * 32
    d = t.buf("dst", d0)
    vals = list(pat(81, 4))
    t.vload(12, 8, vals, "sv")
    offs = [9, 0, 3, 17]
    for xl in (64, 32):
        with t.only_if(f"__riscv_xlen == {xl}"):
            t.vload(16, xl, offs, f"io{xl}")
            t.vset(4, 8)
            t.la("x6", d)
            t.mark(f"vsuxei{xl}")
            t.emit(f"vsuxei{xl}.v v12, (x6), v16")
            img = bytearray(d0)
            for o, v in zip(offs, vals):
                img[o] = v
            t.ck_mem(d, 0, words(img, 0, 24), f"vsuxei{xl}.v stores SEW=8 bytes")
    return t


def t_eew_emul() -> VTest:
    t = new("vector_ls_eew_emul")
    describe(
        t,
        "Vector loads and stores have an EEW encoded directly in the instruction. The corresponding EMUL is "
        "calculated as EMUL = (EEW/SEW)*LMUL.",
        "- SEW=8, LMUL=1, vl=16: vle64.v v8 has EMUL=8 and loads 16 doublewords into v8-v15 (elements 0, 1, 7 and "
        "15 checked; at VLEN=128 element 15 is in v15).\n"
        "- SEW=16, LMUL=2, vl=8: vle32.v v8 has EMUL=4 (8 words); vse32.v of that group writes 32 bytes.\n"
        "- SEW=32, LMUL=1/2, vl=2: vle8.v has EMUL=1/8 and loads 2 bytes; byte 2 (tail) undisturbed.\n"
        "- SEW=8, LMUL=1, vl=16: vse64.v v16 (EMUL=8) writes 128 bytes and not byte 128.",
    )
    src = pat(9, 160)
    s = t.buf("src", src)
    t.vfill(8, 8)
    t.vset(16, 8)
    t.la("x6", s)
    t.mark("vle64_emul8")
    t.emit("vle64.v v8, (x6)")
    e = elems(src, 0, 64, 16)
    for i in (0, 1, 7, 15):
        t.ck_elem(8, i, 64, fe(64) if (MUT == "emul_is_lmul" and i >= 2) else e[i], "vle64.v at SEW=8 (EMUL=8)")
    t.vfill(8, 4)
    t.vset(8, 16, "m2")
    t.la("x6", s)
    t.mark("vle32_emul4")
    t.emit("vle32.v v8, (x6)")
    w = elems(src, 0, 32, 8)
    t.ck_reg(8, 32, w, "vle32.v at SEW=16, LMUL=2 (EMUL=4)")
    d0 = bytes([0x5C]) * 160
    d = t.buf("dst", d0)
    t.la("x6", d)
    t.vset(8, 16, "m2")
    t.mark("vse32_emul4")
    t.emit("vse32.v v8, (x6)")
    t.ck_mem(d, 0, [*w, M5C], "vse32.v at SEW=16, LMUL=2 writes 8 words")
    restore(t, d, d0, 0, 36)
    t.vfill(8)
    t.vset(2, 32, "mf2")
    t.la("x6", f"{s}+3")
    t.mark("vle8_emul_f8")
    t.emit("vle8.v v8, (x6)")
    t.ck_reg(8, 8, [src[3], src[4], F], "vle8.v at SEW=32, LMUL=1/2 (EMUL=1/8)")
    t.vset(16, 8)
    t.la("x6", s)
    t.emit("vle64.v v16, (x6)")
    t.la("x6", d)
    t.mark("vse64_emul8")
    t.emit("vse64.v v16, (x6)")
    t.ck_mem(d, 0, words(src, 0, 8), "vse64.v at SEW=8 (EMUL=8): first doubleword")
    t.ck_mem(d, 120, [*words(src, 120, 128), M5C], "vse64.v at SEW=8 (EMUL=8): last doubleword, then nothing")
    return t


def t_ins_req() -> VTest:
    t = new("vector_ls_ins_req")
    describe(
        t,
        "Implementations must provide vector loads and stores with EEWs corresponding to all supported SEW settings.",
        "For each SEW (8, 16, 32, 64; all supported by V): vsetivli with LMUL=1 sets vtype (vill=0), then the "
        "loads vle, vlse (stride EEW/8), vluxei/vloxei with index EEW = SEW (not EEW=64 on RV32, which V excludes) "
        "and vlseg2e of that EEW load the expected first element, and vse, vsse, vsuxei and vsseg2e store it. Any "
        "illegal-instruction trap fails the test.",
    )
    src = pat(10, 128)
    s = t.buf("src", src)
    d0 = bytes([0x5C]) * 64
    d = t.buf("dst", d0)
    for sew in (8, 16, 32, 64):
        eb = sew // 8
        enc = {8: 0, 16: 1, 32: 2, 64: 3}[sew] << 3
        t.vset(2, sew)
        t.mark(f"vset{sew}")
        t.ck_csr("vtype", enc, f"SEW={sew}, LMUL=1, tu, mu is supported")
        e0 = le(src[eb : 2 * eb])
        loads = [
            ("vle", f"vle{sew}.v v8, (x6)"),
            ("vlse", f"vlse{sew}.v v8, (x6), x1"),
            ("vluxei", f"vluxei{sew}.v v8, (x9), v16"),
            ("vloxei", f"vloxei{sew}.v v8, (x9), v16"),
            ("vlseg2", f"vlseg2e{sew}.v v8, (x6)"),
        ]
        stores = [
            ("vse", f"vse{sew}.v v8, (x6)"),
            ("vsse", f"vsse{sew}.v v8, (x6), x1"),
            ("vsuxei", f"vsuxei{sew}.v v8, (x6), v16"),
            ("vsseg2", f"vsseg2e{sew}.v v8, (x6)"),
        ]

        def one(nm: str, ins: str, store: bool, sew: int = sew, eb: int = eb, e0: int = e0) -> None:
            if not store:
                if "xei" in nm:
                    t.vload(16, sew, [eb, 0], f"ix{nm}{sew}")
                t.vfill(8, 2)
                t.vset(2, sew)
                t.la("x6", f"{s}+{eb}")
                t.la("x9", s)
                t.li("x1", eb)
                t.mark(f"{nm}{sew}")
                t.emit(ins)
                t.ck_elem(8, 0, sew, e0, ins.split()[0])
                return
            if "xei" in nm:
                t.vload(16, sew, [0], f"ixs{sew}")
            t.vset(1, sew)
            t.la("x6", f"{s}+{eb}")
            t.emit(f"vlseg2e{sew}.v v8, (x6)")
            t.vset(1, sew)
            t.la("x6", d)
            t.li("x1", eb)
            t.mark(f"{nm}{sew}")
            t.emit(ins)
            img = bytearray(d0)
            n = 2 if "seg" in nm else 1
            img[0 : n * eb] = src[eb : (n + 1) * eb]
            t.ck_mem(d, 0, words(img, 0, 20), ins.split()[0])
            restore(t, d, d0, 0, 20)

        for store, lst in ((False, loads), (True, stores)):
            for nm, ins in lst:
                if "xei" in nm and sew == 64:
                    with t.rv64_only():
                        one(nm, ins, store)
                else:
                    one(nm, ins, store)
    return t


# ================================================================ base and strides
def t_base_stride_regtype() -> VTest:
    t = new("vector_ls_base_stride_regtype")
    describe(
        t,
        "Vector load/store base registers and strides are taken from the `x` registers.",
        "vlse32.v and vsse32.v with the base and stride in different x registers (x9/x1, x1/x9, x6/x8) and strides "
        "8, -4 and 12 access base + i*stride, and leave the base and stride registers unchanged.",
    )
    src = pat(11, 64)
    s = t.buf("src", src)
    d0 = bytes([0x5C]) * 64
    d = t.buf("dst", d0)
    t.vfill(8)
    t.vset(3, 32)
    t.la("x9", s)
    t.li("x1", 8)
    t.mark("rs1_x9_rs2_x1")
    t.emit("vlse32.v v8, (x9), x1")
    t.check("x1", 8, t.lab, "the stride register is unchanged")
    t.ck_reg(8, 32, elems(src, 0, 32, 3, 8), "base x9, stride x1 = 8")
    t.vfill(8)
    t.vset(3, 32)
    t.la("x1", f"{s}+12")
    t.li("x9", -4)
    t.mark("rs1_x1_rs2_x9")
    t.emit("vlse32.v v8, (x1), x9")
    t.check("x9", -4, t.lab, "the stride register is unchanged")
    t.la("x7", f"{s}+12")
    t.emit("sub x6, x1, x7")
    t.emit("seqz x6, x6")
    t.check_bool("x6", t.lab, "the base register is unchanged")
    t.ck_reg(8, 32, [le(src[o : o + 4]) for o in (12, 8, 4)], "base x1, stride x9 = -4")
    vals = store_vals(32, 3, 111)
    t.vload(16, 32, vals, "sv")
    t.vset(3, 32)
    t.la("x6", d)
    t.li("x8", 12)
    t.mark("rs1_x6_rs2_x8")
    t.emit("vsse32.v v16, (x6), x8")
    t.check("x8", 12, t.lab, "the stride register is unchanged")
    img = bytearray(d0)
    for i, v in enumerate(vals):
        img[12 * i : 12 * i + 4] = v.to_bytes(4, "little")
    t.ck_mem(d, 0, words(img, 0, 40), "vsse32.v base x6, stride x8 = 12")
    return t


def t_base() -> VTest:
    t = new("vector_ls_base")
    describe(
        t,
        "The base effective address for all vector accesses is given by the contents of the `x` register named in "
        "`rs1`.",
        "Unit-stride (vle8.v at base+1 and base+7, vle32.v at base+20), strided (vlse16.v at base+6, stride 4), "
        "indexed (vluxei8.v at base+3, offsets 0 and 2), whole-register (vl1re8.v at base+9) and segment "
        "(vlseg2e8.v at base+5) loads, and a unit-stride store (vse8.v at dst+3), all start at the address held "
        "in rs1; rs1 is unchanged after each load.",
    )
    src = pat(12, 96)
    s = t.buf("src", src)
    cases = [
        ("vle8.v v8, (x6)", 1, 8, 5, None),
        ("vle8.v v8, (x6)", 7, 8, 5, None),
        ("vle32.v v8, (x6)", 20, 32, 3, None),
        ("vlse16.v v8, (x6), x1", 6, 16, 3, 4),
        ("vluxei8.v v8, (x6), v16", 3, 8, 2, "idx"),
        ("vl1re8.v v8, (x6)", 9, 8, 16, None),
    ]
    for ins, off, eew, n, st in cases:
        if st == "idx":
            t.vload(16, 8, [0, 2], f"ix{off}")
        t.vfill(8, 2)
        t.vset(n if not ins.startswith("vl1r") else 1, eew)
        t.la("x6", f"{s}+{off}")
        if isinstance(st, int):
            t.li("x1", st)
        t.mark(ins.split(".")[0] + f"_{off}")
        t.emit(ins)
        t.emit("mv x9, x6")
        exp = [src[off], src[off + 2]] if st == "idx" else elems(src, off, eew, n, st if isinstance(st, int) else None)
        t.ck_reg(8, eew, exp, f"{ins.split()[0]} from rs1 = base+{off}")
        t.la("x7", f"{s}+{off}")
        t.emit("sub x9, x9, x7")
        t.emit("seqz x9, x9")
        t.check_bool("x9", t.lab, "rs1 unchanged")
    t.vfill(8, 2)
    t.vset(3, 8)
    t.la("x6", f"{s}+5")
    t.mark("vlseg2e8")
    t.emit("vlseg2e8.v v8, (x6)")
    t.ck_reg(8, 8, [src[5], src[7], src[9]], "vlseg2e8.v field 0")
    t.ck_reg(9, 8, [src[6], src[8], src[10]], "vlseg2e8.v field 1")
    d0 = bytes([0x5C]) * 16
    d = t.buf("dst", d0)
    t.vset(4, 8)
    t.la("x6", f"{d}+3")
    t.mark("vse8")
    t.emit("vse8.v v8, (x6)")
    img = bytearray(d0)
    img[3:7] = bytes([src[5], src[7], src[9], F])
    t.ck_mem(d, 0, words(img, 0, 12), "vse8.v at rs1 = dst+3")
    return t


def t_constant_stride_op() -> VTest:
    t = new("vector_ls_constant_stride_op")
    describe(
        t,
        "Vector constant-stride operations access the first memory element at the base effective address, and "
        "then access subsequent elements at address increments given by the byte offset contained in the `x` "
        "register specified by `rs2`.",
        "Loads: vlse8.v stride 3 (vl=5), vlse32.v stride 12 (vl=4), vlse64.v stride 24 (vl=2), vlse16.v stride 2 "
        "(equal to the element size), vlse32.v stride 4100 (vl=2, the second element on another page). Stores: "
        "vsse32.v stride 8 (vl=3) writes words 0, 2 and 4 and leaves words 1, 3 and 5 unchanged; vsse8.v stride 5 "
        "(vl=3).",
    )
    src = pat(13, 4160)
    s = t.buf("src", src, 12)
    ig = MUT == "stride_ignored"
    for eew, stride, n in ((8, 3, 5), (32, 12, 4), (64, 24, 2), (16, 2, 4), (32, 4100, 2)):
        t.vfill(8)
        t.vset(n, eew)
        t.la("x6", f"{s}+16")
        t.li("x1", stride)
        t.mark(f"vlse{eew}_{stride}")
        t.emit(f"vlse{eew}.v v8, (x6), x1")
        t.ck_reg(8, eew, elems(src, 16, eew, n, eew // 8 if ig else stride), f"vlse{eew}.v stride {stride}")
    d0 = bytes([0x5C]) * 64
    d = t.buf("dst", d0)
    for eew, stride, n, seed in ((32, 8, 3, 131), (8, 5, 3, 132)):
        vals = store_vals(eew, n, seed)
        t.vload(16, eew, vals, f"sv{eew}")
        t.vset(n, eew)
        t.la("x6", d)
        t.li("x1", stride)
        t.mark(f"vsse{eew}")
        t.emit(f"vsse{eew}.v v16, (x6), x1")
        img = bytearray(d0)
        st = eew // 8 if ig else stride
        for i, v in enumerate(vals):
            img[st * i : st * i + eew // 8] = v.to_bytes(eew // 8, "little")
        t.ck_mem(d, 0, words(img, 0, 24), f"vsse{eew}.v stride {stride}")
        restore(t, d, d0, 0, 24)
    return t


def t_neg_zero_stride() -> VTest:
    t = new("vector_ls_neg_zero_stride")
    describe(
        t,
        "Negative and zero strides are supported.",
        "Loads: vlse32.v stride -4 from base+12 reads words 3, 2, 1, 0; stride -12 (vl=3) from base+40; vlse8.v "
        "stride -1 (vl=8) reads bytes in reverse; stride 0 in a register (vl=4) reads the same word into every "
        "element. Stores: vsse32.v stride -8 (vl=3) from dst+32 writes words at 32, 24 and 16 and nothing between; "
        "vsse16.v stride 0 in a register (vl=4) leaves one of the four elements (any: the accesses are unordered) "
        "and writes no other byte.",
    )
    src = pat(14, 64)
    s = t.buf("src", src)
    zu = MUT == "zero_stride_unit"
    for eew, stride, base, n in ((32, -4, 12, 4), (32, -12, 40, 3), (8, -1, 20, 8), (32, 0, 8, 4)):
        t.vfill(8)
        t.vset(n, eew)
        t.la("x6", f"{s}+{base}")
        t.li("x1", stride)
        t.mark(f"vlse{eew}_{'m' if stride < 0 else ''}{abs(stride)}")
        t.emit(f"vlse{eew}.v v8, (x6), x1")
        st = eew // 8 if (zu and stride == 0) else stride
        t.ck_reg(8, eew, [le(src[base + i * st : base + i * st + eew // 8]) for i in range(n)], f"stride {stride}")
    d0 = bytes([0x5C]) * 64
    d = t.buf("dst", d0)
    vals = store_vals(32, 3, 141)
    t.vload(16, 32, vals, "sv")
    t.vset(3, 32)
    t.la("x6", f"{d}+32")
    t.li("x1", -8)
    t.mark("vsse32_m8")
    t.emit("vsse32.v v16, (x6), x1")
    img = bytearray(d0)
    for i, v in enumerate(vals):
        img[32 - 8 * i : 36 - 8 * i] = v.to_bytes(4, "little")
    t.ck_mem(d, 0, words(img, 0, 40), "vsse32.v stride -8")
    restore(t, d, d0, 0, 40)
    hv = store_vals(16, 4, 142)
    t.vload(16, 16, hv, "sh")
    t.vset(4, 16)
    t.la("x6", f"{d}+8")
    t.li("x1", 0)
    t.mark("vsse16_0")
    t.emit("vsse16.v v16, (x6), x1")
    t.ck_mem(d, 8, [[hv[0]] if zu else hv], "vsse16.v stride 0: one of the elements", unit=2)
    t.ck_mem(d, 4, [M5C], "vsse16.v stride 0: bytes before unchanged")
    t.ck_mem(d, 10, [0x5C5C, 0x5C5C], "vsse16.v stride 0: bytes after unchanged", unit=2)
    return t


def t_constant_stride_x0() -> VTest:
    t = new("vector_ls_constant_stride_x0")
    describe(
        t,
        "When _rs2_=`x0`, then an implementation is allowed, but not required, to perform fewer memory operations "
        "than the number of active elements, and may perform different numbers of memory operations across "
        "different dynamic executions of the same static instruction.",
        "The result is still that of stride 0: vlse32.v rs2=x0 (vl=4) puts the word at base in every element; "
        "masked (v0=0b0101, mu) it does so for elements 0 and 2 and leaves 1 and 3 undisturbed. vsse32.v rs2=x0 "
        "(vl=4) leaves one of the four elements at base; masked with v0=0b0110 one of elements 1 or 2; with every "
        "element masked off memory is unchanged; nothing around base is written.",
    )
    src = pat(15, 32)
    s = t.buf("src", src)
    zu = MUT == "zero_stride_unit"
    w = le(src[8:12])
    for mask in (None, 0b0101):
        t.vfill(8)
        if mask:
            t.vmask(mask)
        t.vset(4, 32)
        t.la("x6", f"{s}+8")
        t.mark("vlse32_x0" + ("_m" if mask else ""))
        t.emit("vlse32.v v8, (x6), x0" + (", v0.t" if mask else ""))
        exp = [le(src[8 + 4 * i : 12 + 4 * i]) for i in range(4)] if zu else [w] * 4
        if mask:
            exp = [e if mask >> i & 1 else fe(32) for i, e in enumerate(exp)]
        t.ck_reg(8, 32, exp, "vlse32.v rs2=x0" + (" masked" if mask else ""))
    d0 = bytes([0x5C]) * 32
    d = t.buf("dst", d0)
    vals = store_vals(32, 4, 151)
    t.vload(16, 32, vals, "sv")
    for mask, legal in ((None, vals), (0b0110, vals[1:3]), (0, [M5C])):
        if mask is not None:
            t.vmask(mask)
        t.vset(4, 32)
        t.la("x6", f"{d}+8")
        t.mark("vsse32_x0" + ("" if mask is None else f"_m{mask}"))
        t.emit("vsse32.v v16, (x6), x0" + ("" if mask is None else ", v0.t"))
        lg = [vals[0]] if (zu and mask is None) else legal
        t.ck_mem(d, 4, [M5C, lg, M5C], f"vsse32.v rs2=x0 mask {mask}")
        restore(t, d, d0, 0, 16)
    return t


def t_constant_stride_unordered() -> VTest:
    t = new("vector_ls_constant_stride_unordered")
    describe(
        t,
        "Element accesses within a constant-stride instruction are unordered with respect to each other.",
        "Stores with stride 0 in a register (not x0) write every element to the same bytes in some order, so the "
        "final value is any one element: vsse8.v (vl=8, one of 8 bytes), vsse32.v (vl=4, one of 4 words), "
        "vsse64.v (vl=2, one of 2 doublewords, checked as words). The neighboring bytes are unchanged.",
    )
    d0 = bytes([0x5C]) * 32
    d = t.buf("dst", d0)
    one = MUT == "ordered_first_wins"
    for eew, n, seed in ((8, 8, 161), (32, 4, 162), (64, 2, 163)):
        vals = store_vals(eew, n, seed)
        lg = [vals[0]] if one else vals
        t.vload(16, eew, vals, f"sv{eew}")
        t.vset(n, eew)
        t.la("x6", f"{d}+8")
        t.li("x1", 0)
        t.mark(f"vsse{eew}_0")
        t.emit(f"vsse{eew}.v v16, (x6), x1")
        if eew == 8:
            t.ck_mem(d, 7, [0x5C, lg, 0x5C, 0x5C, 0x5C], "vsse8.v stride 0", unit=1)
        elif eew == 32:
            t.ck_mem(d, 4, [M5C, lg, M5C], "vsse32.v stride 0")
        else:
            t.ck_mem(d, 4, [M5C], "vsse64.v stride 0: word before unchanged")
            t.ck_mem(d, 16, [M5C], "vsse64.v stride 0: word after unchanged")
            t.comment("the doubleword is one whole element (not halves of two)")
            t.la("x6", f"{d}+8")
            t.emit("lw x7, 0(x6)")
            t.emit("lw x6, 4(x6)")
            t.emit("li x9, 0")
            for v in lg:
                t.load("x8", sx(v, 32))
                t.emit("sub x8, x8, x7")
                t.emit("seqz x1, x8")
                t.load("x8", sx(v >> 32, 32))
                t.emit("sub x8, x8, x6")
                t.emit("seqz x8, x8")
                t.emit("and x8, x8, x1")
                t.emit("or x9, x9, x8")
            t.check_bool("x9", t.lab, "vsse64.v stride 0: the doubleword is one of the elements")
        restore(t, d, d0, 0, 24)
    return t


# ================================================================ mask loads/stores
def t_unit_stride_mask() -> VTest:
    t = new("vector_ls_unit_stride_mask")
    describe(
        t,
        "Additional unit-stride mask load and store instructions are provided to transfer mask values to/from "
        "memory. These operate similarly to unmasked byte loads or stores (EEW=8), except that the effective "
        "vector length is ``evl`` = ceil(vl/8) (i.e. EMUL=1), and the destination register is always written with "
        "a tail-agnostic policy.",
        "vlm.v loads ceil(vl/8) bytes and the rest of the register is tail (each byte undisturbed or all ones, even "
        "with vta=0): vl=17 at SEW=8/LMUL=2 (3 bytes), vl=9 at SEW=32/LMUL=4 into v9 (2 bytes; EMUL=1, so an odd "
        "register is legal with LMUL=4), vl=8 (1 byte), vl=1 at SEW=64 (1 byte), vl=0 (no byte written). vsm.v "
        "stores ceil(vl/8) bytes and no more: vl=17 (3 bytes), vl=9 at SEW=16/LMUL=2 from v13 (2 bytes), vl=0 "
        "(none).",
        context="With vl=0 no element is updated, including tail elements (vstart_vl_dep).",
    )
    src = pat(16, 32)
    s = t.buf("src", src)

    def ev(vl: int) -> int:
        return vl if MUT == "mask_evl_vl" else (vl + 7) // 8

    for vl, sew, lm, vd, off in (
        (17, 8, "m2", 8, 0),
        (9, 32, "m4", 9, 3),
        (8, 8, "m1", 10, 5),
        (1, 64, "m1", 11, 7),
        (0, 8, "m1", 12, 2),
    ):
        t.vfill(vd)
        t.vset(vl, sew, lm)
        t.la("x6", f"{s}+{off}")
        if MUT == "vlm_lmul_aligned" and lm == "m4":
            t.win(["vlm.v v9, (x6)"], ILLEGAL, "vlm.v v9 with LMUL=4")
            continue
        t.mark(f"vlm_vl{vl}")
        t.emit(f"vlm.v v{vd}, (x6)")
        n = ev(vl)
        exp = [src[off + i] if i < n else ([F] if vl == 0 else [F, 0xFF]) for i in range(16)]
        t.ck_reg(vd, 8, exp, f"vlm.v vl={vl} SEW={sew} LMUL={lm}: evl={(vl + 7) // 8}")
    d0 = bytes([0x5C]) * 32
    d = t.buf("dst", d0)
    mv = list(pat(161, 16))
    for vl, sew, lm, vs in ((17, 8, "m2", 14), (9, 16, "m2", 13), (0, 8, "m1", 14)):
        t.vload(vs, 8, mv, f"m{vs}{vl}")
        t.vset(vl, sew, lm)
        t.la("x6", f"{d}+4")
        t.mark(f"vsm_vl{vl}")
        t.emit(f"vsm.v v{vs}, (x6)")
        img = bytearray(d0)
        n = ev(vl)
        img[4 : 4 + n] = bytes(mv[:n])
        t.ck_mem(d, 0, words(img, 0, 24), f"vsm.v vl={vl}: evl={(vl + 7) // 8} bytes")
        restore(t, d, d0, 0, 24)
    return t


# ================================================================ whole-register
def vlenb_mul(t: VTest, reg: str, k: int) -> None:
    """reg = k * vlenb (k < 16). Clobbers x8."""
    t.emit(f"li {reg}, 0")
    if k:
        t.emit("csrr x8, vlenb")
        for b in range(4):
            if k >> b & 1:
                t.emit(f"slli x8, x8, {b}")
                t.emit(f"add {reg}, {reg}, x8")
                t.emit(f"srli x8, x8, {b}")


def mem_word_rt(t: VTest, reg: str, lab: str, k: int, off: int) -> None:
    """reg = the word at lab + k*vlenb + off (run time). Clobbers x1, x8."""
    vlenb_mul(t, reg, k)
    t.la("x1", lab)
    t.emit(f"add {reg}, {reg}, x1")
    t.emit(f"lw {reg}, {off}({reg})")


def ck_reg_vs_mem(t: VTest, vreg: int, word: int, lab: str, k: int, off: int, desc: str) -> None:
    """Check word `word` of register v[vreg] equals the word at lab + k*vlenb + off + 4*word. Clobbers x1, x7-x9."""
    mem_word_rt(t, "x9", lab, k, off + 4 * word)
    t.vel("x7", vreg, word, 32)
    t.emit("sub x9, x9, x7")
    t.emit("seqz x9, x9")
    t.check_bool("x9", t.lab, f"{desc}: v{vreg} word {word} = memory word at +{k}*VLENB+{off + 4 * word}")


def vlenb_guard(t: VTest, body: object) -> None:
    """Run body only when VLEN <= 4096 (buffers hold 8 registers of up to 512 bytes)."""
    t.emit("csrr x1, vlenb")
    t.emit("sltiu x1, x1, 513")
    guard(t, "x1", body)  # type: ignore[arg-type]


def t_wholels_nf_op() -> VTest:
    t = new("vector_wholels_nf_op")
    describe(
        t,
        "The `nf[2:0]` field also encodes the number of whole vector registers to transfer for the whole vector "
        "register load/store instructions.",
        "vl1re8.v v1, vl2re16.v v2, vl4re32.v v4 and vl8re64.v v8 load 1, 2, 4 and 8 registers: the first and "
        "last register of each group hold the memory at k*VLENB (k = register index in the group), and the "
        "register after the group stays undisturbed. vs1r.v, vs2r.v, vs4r.v and vs8r.v write n*VLENB bytes: the "
        "last word written is the last register's last word, and the word after it is unchanged. VLEN <= 4096 is "
        "assumed for the buffer sizes (the test passes trivially above).",
    )
    src = pat(17, 4096 + 64)
    s = t.buf("src", src, 12)
    d = t.buf("dst", bytes([0x5C]) * (4096 + 64), 12)
    minus = MUT == "wholereg_nf_minus1"

    def body() -> None:
        t.vfill(1, 23)
        for n, eew, vd in ((1, 8, 1), (2, 16, 2), (4, 32, 4), (8, 64, 8)):
            t.la("x6", s)
            t.mark(f"vl{n}re{eew}")
            t.emit(f"vl{n}re{eew}.v v{vd}, (x6)")
            ck_reg_vs_mem(t, vd, 0, s, 0, 0, f"vl{n}re{eew}.v first register")
            if n > 1:
                if minus:
                    t.ck_elem(vd + n - 1, 0, 32, fe(32), f"vl{n}re{eew}.v (mutant: last register not loaded)")
                else:
                    ck_reg_vs_mem(t, vd + n - 1, 3, s, n - 1, 0, f"vl{n}re{eew}.v last register")
            t.ck_elem(vd + n, 0, 32, fe(32), f"vl{n}re{eew}.v: v{vd + n} after the group undisturbed")
        for n in (1, 2, 4, 8):
            t.la("x6", d)
            t.mark(f"vs{n}r")
            t.emit(f"vs{n}r.v v{n}, (x6)")
            vlenb_mul(t, "x9", n)
            t.la("x1", d)
            t.emit("add x9, x9, x1")
            t.emit("lw x7, -4(x9)")
            t.emit("lw x9, 0(x9)")
            t.check("x9", sx(M5C, 32), t.lab, f"vs{n}r.v: the word after {n}*VLENB bytes is unchanged")
            mem_word_rt(t, "x9", s, n, -4)
            t.emit("sub x9, x9, x7")
            t.emit("seqz x9, x9")
            t.check_bool("x9", t.lab, f"vs{n}r.v: the last word written is the last register's last word")

    vlenb_guard(t, body)
    return t


def t_seg_wholereg_op() -> VTest:
    t = new("vector_ls_seg_wholereg_op")
    describe(
        t,
        "NFIELDS indicates the number of vector registers to transfer, numbered successively after the base.",
        "vl4re32.v v12 loads v12-v15 (register k of the group holds memory at k*VLENB) and leaves v11 and v16 "
        "undisturbed; vl2re16.v v6 loads v6-v7 and leaves v5 and v8; vl2re8.v v30 loads v30 and v31 (the last "
        "registers), checked by storing them with vs2r.v v30 (v30 at +0, v31 at +VLENB).",
    )
    src = pat(18, 4096 + 64)
    s = t.buf("src", src, 12)
    d = t.buf("dst", bytes([0x5C]) * (4096 + 64), 12)
    minus = MUT == "wholereg_nf_minus1"

    def body() -> None:
        t.vfill(1, 23)
        t.la("x6", s)
        t.mark("vl4re32_v12")
        t.emit("vl4re32.v v12, (x6)")
        for k in range(4):
            if minus and k == 3:
                t.ck_elem(15, 0, 32, fe(32), "vl4re32.v v12 (mutant: v15 not loaded)")
            else:
                ck_reg_vs_mem(t, 12 + k, 0, s, k, 0, "vl4re32.v v12")
        t.ck_elem(11, 0, 32, fe(32), "v11 undisturbed")
        t.ck_elem(16, 0, 32, fe(32), "v16 undisturbed")
        t.la("x6", f"{s}+64")
        t.mark("vl2re16_v6")
        t.emit("vl2re16.v v6, (x6)")
        ck_reg_vs_mem(t, 6, 0, s, 0, 64, "vl2re16.v v6")
        ck_reg_vs_mem(t, 7, 1, s, 1, 64, "vl2re16.v v6")
        t.ck_elem(5, 0, 32, fe(32), "v5 undisturbed")
        t.ck_elem(8, 0, 32, fe(32), "v8 undisturbed")
        t.la("x6", f"{s}+32")
        t.mark("vl2re8_v30")
        t.emit("vl2re8.v v30, (x6)")
        t.la("x6", d)
        t.emit("vs2r.v v30, (x6)")
        for k in range(2):
            vlenb_mul(t, "x9", k)
            t.la("x1", d)
            t.emit("add x9, x9, x1")
            t.emit("lw x7, 0(x9)")
            mem_word_rt(t, "x9", s, k, 32)
            t.emit("sub x9, x9, x7")
            t.emit("seqz x9, x9")
            t.check_bool("x9", t.lab, f"vl2re8.v v30 then vs2r.v v30: v{30 + k} at +{k}*VLENB")

    vlenb_guard(t, body)
    return t


def t_seg_wholereg_op_cont() -> VTest:
    t = new("vector_ls_seg_wholereg_op_cont")
    describe(
        t,
        "When multiple registers are transferred, the lowest-numbered vector register is held in the "
        "lowest-numbered memory addresses and successive vector register numbers are placed contiguously in "
        "memory.",
        "v8 and v9 are loaded separately (vl1re8.v from two different buffers); vs2r.v v8 writes v8 at dst and "
        "v9 at dst+VLENB with no gap (dst+VLENB-4 holds v8's last word). vl8re8.v v8 reads register k from "
        "src+k*VLENB, for k = 0, 3 and 7.",
    )
    sa = pat(19, 4096 + 64)
    sb = pat(20, 512)
    a = t.buf("sa", sa, 12)
    b = t.buf("sb", sb, 6)
    d = t.buf("dst", bytes([0x5C]) * (4096 + 64), 12)

    def body() -> None:
        t.la("x6", a)
        t.emit("vl1re8.v v8, (x6)")
        t.la("x6", b)
        t.emit("vl1re8.v v9, (x6)")
        t.la("x6", d)
        t.mark("vs2r")
        t.emit("vs2r.v v8, (x6)")
        t.ck_mem(d, 0, words(sa, 0, 8), "vs2r.v: v8 at dst")
        mem_word_rt(t, "x7", d, 1, 0)
        t.check("x7", sx(le(sb[0:4]), 32), t.lab, "vs2r.v: v9 starts at dst+VLENB")
        mem_word_rt(t, "x7", d, 1, -4)
        mem_word_rt(t, "x9", a, 1, -4)
        t.emit("sub x9, x9, x7")
        t.emit("seqz x9, x9")
        t.check_bool("x9", t.lab, "vs2r.v: v8's last word at dst+VLENB-4")
        t.la("x6", a)
        t.mark("vl8re8")
        t.emit("vl8re8.v v8, (x6)")
        for k in (0, 3, 7):
            ck_reg_vs_mem(t, 8 + k, 0, a, k, 0, "vl8re8.v")

    vlenb_guard(t, body)
    return t


def t_wholereg_misaligned() -> VTest:
    t = new("vector_ls_wholereg_misaligned_exception")
    describe(
        t,
        "Implementations are allowed to raise a misaligned address exception on whole register loads and stores "
        "if the base address is not naturally aligned to the larger of the size of the encoded EEW in bytes "
        "(EEW/8) or the implementation's smallest supported SEW size in bytes (SEW~MIN~/8).",
        "V supports SEW=8, so SEWMIN/8 = 1 and the bound is EEW/8.\n"
        "Must not raise address-misaligned: vl1re8.v at an odd address, vl1re16.v at 2 mod 4, vl1re32.v at 4 mod 8, "
        "vl1re64.v at 8 mod 16, vs1r.v at an odd address (each checked to transfer the right bytes).\n"
        "vs2r.v at 2 mod 4 must not trap either (vs<n>r.v encodes EEW=8).\n"
        "May raise it: vl1re32.v at 2 mod 4, vl2re64.v at 4 mod 8, vl4re16.v at an odd address. Legal outcomes: "
        "success (the register then holds the right bytes), address-misaligned (4) or access fault (5); on a trap "
        "stval is 0 or an address inside the NFIELDS*VLENB-byte access, and vstart is reset before going on.",
        context="machine.adoc pma_mag_exc: implementations may raise access-fault instead of address-misaligned "
        "for some misaligned accesses.",
    )
    src = pat(21, 4096 + 64)
    s = t.buf("src", src, 12)
    d0 = bytes([0x5C]) * (4096 + 64)
    d = t.buf("dst", d0, 12)

    def body() -> None:
        for ins, off in (("vl1re8.v", 1), ("vl1re16.v", 6), ("vl1re32.v", 12), ("vl1re64.v", 24)):
            t.vfill(8)
            t.la("x6", f"{s}+{off}")
            bad = (MUT == "misaligned_e8_traps" and ins == "vl1re8.v") or (
                MUT == "wholereg_aligned_traps" and ins == "vl1re32.v"
            )
            t.win([f"{ins} v8, (x6)"], LOAD_MIS if bad else "ok", f"{ins} at +{off} (EEW aligned)")
            if bad:
                t.emit("csrw vstart, x0")
                continue
            t.ck_reg(8, 8, list(src[off : off + 16]), f"{ins} at +{off}")
        t.la("x6", f"{d}+3")
        t.win(["vs1r.v v8, (x6)"], "ok", "vs1r.v at an odd address (EEW=8)")
        t.ck_mem(d, 0, [le(bytes([0x5C] * 3) + src[24:25]), *words(src, 25, 37)], "vs1r.v at +3")
        t.vfill(12, 2)
        t.la("x6", f"{d}+0x802")
        t.win(["vs2r.v v12, (x6)"], STORE_MIS if MUT == "misaligned_e8_traps" else "ok", "vs2r.v at 2 mod 4 (EEW=8)")
        t.emit("csrw vstart, x0")
        if MUT != "misaligned_e8_traps":
            t.ck_mem(d, 0x800, [le(bytes([0x5C, 0x5C, F, F])), le(bytes([F]) * 4)], "vs2r.v at +0x802")
        for ins, off, nregs in (("vl1re32.v v8", 2, 1), ("vl2re64.v v8", 4, 2), ("vl4re16.v v8", 1, 4)):
            t.vfill(8, 8)
            t.la("x6", f"{s}+{off}")
            t.win([f"{ins}, (x6)"], ["ok", LOAD_MIS, LOAD_AF], f"{ins.split()[0]} at +{off} (misaligned to EEW)")
            trapped(t)

            def on_trap(ins: str = ins, nregs: int = nregs) -> None:
                t.emit("csrw vstart, x0")
                t.emit("AI_LOG(x7, TRAPLOG_TVAL)", 10)
                t.emit("sub x9, x7, x6")  # tval - base
                t.emit("csrr x8, vlenb")
                if nregs > 1:
                    t.emit(f"slli x8, x8, {nregs.bit_length() - 1}")
                t.emit("sltu x9, x9, x8")  # inside the NFIELDS*VLENB-byte access
                t.emit("seqz x7, x7")
                t.emit("or x9, x9, x7")
                t.check_bool("x9", t.lab, f"{ins.split()[0]}: stval is 0 or inside the access")

            def on_ok(off: int = off) -> None:
                t.ck_reg(8, 8, list(src[off : off + 16]), "the misaligned load succeeded")

            t.either("x1", on_trap, on_ok)

    vlenb_guard(t, body)
    return t


# ================================================================ segments (unprivileged)
def seg_load_case(
    t: VTest,
    src: bytes,
    s: str,
    nf: int,
    eew: int,
    vl: int,
    off: int,
    desc: str,
    vd: int = 8,
    lmul: str = "m1",
    mask: int | None = None,
    ma: bool = False,
    stride: int | None = None,
) -> None:
    """vlseg<nf>e<eew> (or vlsseg with stride) into v[vd].. with SEW = eew; checks each field's first elements and
    the register after the last field."""
    emul = {"m1": 1, "m2": 2, "m4": 4}[lmul]
    nregs = nf * emul
    t.vfill(vd, nregs + 1 if vd + nregs < 24 else nregs)
    if mask is not None:
        t.vmask(mask)
    t.vset(vl, eew, lmul, ma=ma)
    t.la("x6", f"{s}+{off}")
    st = nf * eew // 8 if stride is None else stride
    if stride is not None:
        t.li("x1", stride)
    ins = f"vlseg{nf}e{eew}.v" if stride is None else f"vlsseg{nf}e{eew}.v"
    t.mark(ins.split(".")[0])
    t.emit(f"{ins} v{vd}, (x6)" + (", x1" if stride is not None else "") + (", v0.t" if mask is not None else ""))
    if MUT == "seg_stride_is_size" and stride is not None:
        st = nf * eew // 8
    rev = MUT == "seg_fields_reversed"
    nreach = 16 * emul // (eew // 8)
    for f in range(nf):
        ff = nf - 1 - f if rev else f
        exp: list = []
        for i in range(min(vl + 1, nreach)):
            if i >= vl:
                exp.append(fe(eew))
                continue
            a = off + i * st + ff * eew // 8
            v = le(src[a : a + eew // 8])
            if mask is not None and not (mask >> i & 1) and MUT != "seg_mask_ignored":
                exp.append([fe(eew), ones(eew)] if ma else fe(eew))
            else:
                exp.append(v)
        t.ck_reg(vd + f * emul, eew, exp, f"{desc}: field {f}")
    if vd + nregs < 24:
        t.ck_elem(vd + nregs, 0, 32, fe(32), f"{desc}: register after the last field undisturbed")


def t_nf_op() -> VTest:
    t = new("vector_ls_nf_op")
    describe(
        t,
        "The `nf[2:0]` field encodes the number of fields in each segment. For regular vector loads and stores, "
        "`nf`=0, indicating that a single value is moved between a vector register group and memory at each "
        "element position. Larger values in the `nf` field are used to access multiple contiguous fields within a "
        "segment as described below in <<sec-aos>>.",
        "nf=0: vle32.v v8 (vl=VLMAX, LMUL=1) writes only v8 (v9 undisturbed). nf=1: vlseg2e32.v v8 (vl=3) puts "
        "words 0, 2, 4 in v8 and 1, 3, 5 in v9 (v10 undisturbed); vsseg2e32.v interleaves v8 and v9 in memory "
        "(6 words, the 7th unchanged).",
    )
    src = pat(22, 64)
    s = t.buf("src", src)
    t.vfill(8, 2)
    t.vset("max", 32)
    t.la("x6", s)
    t.mark("vle32")
    t.emit("vle32.v v8, (x6)")
    t.ck_reg(8, 32, elems(src, 0, 32, 4), "vle32.v (nf=0)")
    t.ck_elem(9, 0, 32, fe(32), "vle32.v (nf=0): v9 not written")
    seg_load_case(t, src, s, 2, 32, 3, 0, "vlseg2e32.v (nf=1)")
    d0 = bytes([0x5C]) * 32
    d = t.buf("dst", d0)
    t.vset(3, 32)
    t.la("x6", d)
    t.mark("vsseg2e32")
    t.emit("vsseg2e32.v v8, (x6)")
    t.ck_mem(d, 0, [*words(src, 0, 24), M5C], "vsseg2e32.v (nf=1) interleaves v8 and v9")
    return t


def t_nfields() -> VTest:
    t = new("nfields")
    describe(
        t,
        "The three-bit `nf` field in the vector instruction encoding is an unsigned integer that contains one less "
        "than the number of fields per segment, _NFIELDS_.",
        "For nf = 1..7: vlseg<nf+1>e8.v v8 with vl=2 fills NFIELDS = nf+1 registers v8.. with the fields of 2 "
        "segments of nf+1 bytes (element 2, tail, undisturbed), and register v8+NFIELDS stays undisturbed. "
        "vsseg7e8.v and vsseg8e8.v (vl=2) write 14 and 16 bytes.",
    )
    src = pat(23, 64)
    s = t.buf("src", src)
    for n in range(2, 9):
        k = n - 1 if MUT == "nfields_minus1" else n
        t.vfill(8, 9)
        t.vset(2, 8)
        t.la("x6", s)
        t.mark(f"vlseg{n}")
        t.emit(f"vlseg{n}e8.v v8, (x6)")
        for f in range(n):
            exp = [src[f + i * k] for i in range(2)] if f < k else [F, F]
            t.ck_reg(8 + f, 8, [*exp, F], f"vlseg{n}e8.v field {f}")
        t.ck_elem(8 + n, 0, 8, F, f"vlseg{n}e8.v: v{8 + n} undisturbed")
    d0 = bytes([0x5C]) * 32
    d = t.buf("dst", d0)
    for n in (7, 8):
        t.vset(2, 8)
        t.la("x6", s)
        t.emit(f"vlseg{n}e8.v v8, (x6)")
        t.la("x6", d)
        t.mark(f"vsseg{n}")
        t.emit(f"vsseg{n}e8.v v8, (x6)")
        img = bytearray(d0)
        img[0 : 2 * n] = src[0 : 2 * n]
        t.ck_mem(d, 0, words(img, 0, 20), f"vsseg{n}e8.v writes {2 * n} bytes")
        restore(t, d, d0, 0, 20)
    return t


def t_nfields_op() -> VTest:
    t = new("nfields_op")
    describe(
        t,
        "Each field will be held in successively numbered vector register groups. When EMUL>1, each field will "
        "occupy a vector register group held in multiple successively numbered vector registers, and the vector "
        "register group for each field must follow the usual vector register alignment constraints (e.g., when "
        "EMUL=2 and NFIELDS=4, each field's vector register group must start at an even vector register, but does "
        "not have to start at a multiple of 8 vector register number).",
        "- vlseg2e32.v v8, LMUL=2, vl=8: field 0 in v8-v9, field 1 in v10-v11 (all 8 elements of each checked; at "
        "VLEN=128 elements 4-7 are in the second register).\n"
        "- vlseg3e16.v v10 (not a multiple of 4), LMUL=2, vl=10: fields in v10-v11, v12-v13, v14-v15.\n"
        "- vlseg2e8.v v8, LMUL=4, vl=40: fields in v8-v11 and v12-v15 (elements 0, 15, 16, 39 and the tail "
        "element 40 checked); v16 undisturbed.",
    )
    src = pat(24, 160)
    s = t.buf("src", src)
    seg_load_case(t, src, s, 2, 32, 8, 0, "vlseg2e32.v EMUL=2", lmul="m2")
    seg_load_case(t, src, s, 3, 16, 10, 2, "vlseg3e16.v EMUL=2 at v10", vd=10, lmul="m2")
    t.vfill(8, 9)
    t.vset(40, 8, "m4")
    t.la("x6", s)
    t.mark("vlseg2e8_m4")
    t.emit("vlseg2e8.v v8, (x6)")
    for f in range(2):
        ff = 1 - f if MUT == "seg_fields_reversed" else f
        for i in (0, 15, 16, 39, 40):
            t.ck_elem(8 + 4 * f, i, 8, src[2 * i + ff] if i < 40 else F, f"vlseg2e8.v EMUL=4: field {f}")
    t.ck_elem(16, 0, 8, F, "vlseg2e8.v EMUL=4: v16 undisturbed")
    return t


def t_seg_op() -> VTest:
    t = new("vector_ls_seg_op")
    describe(
        t,
        "The vl register gives the number of segments to move, which is equal to the number of elements "
        "transferred to each vector register group. Masking is also applied at the level of whole segments.",
        "vlseg3e16.v, vl=5, mask 0b10110, mu: segments 1, 2 and 4 load all three fields; segments 0 and 3 leave "
        "all three fields undisturbed; element 5 (tail) is undisturbed. With vl=2 unmasked only 2 segments load. "
        "vsseg3e16.v, vl=5, mask 0b01101 writes segments 0, 2 and 3 and leaves the bytes of segments 1, 4 and 5 "
        "unchanged.",
    )
    src = pat(25, 64)
    s = t.buf("src", src)
    seg_load_case(t, src, s, 3, 16, 5, 0, "vlseg3e16.v masked 0b10110", mask=0b10110)
    seg_load_case(t, src, s, 3, 16, 2, 0, "vlseg3e16.v vl=2")
    d0 = bytes([0x5C]) * 48
    d = t.buf("dst", d0)
    t.vset(6, 16)
    t.la("x6", s)
    t.emit("vlseg3e16.v v8, (x6)")
    t.vmask(0b01101)
    t.vset(5, 16)
    t.la("x6", d)
    t.mark("vsseg3e16_m")
    t.emit("vsseg3e16.v v8, (x6), v0.t")
    img = bytearray(d0)
    for i in range(5):
        if (0b01101 >> i & 1) or MUT == "seg_mask_ignored":
            img[6 * i : 6 * i + 6] = src[6 * i : 6 * i + 6]
    t.ck_mem(d, 0, words(img, 0, 40), "vsseg3e16.v masked 0b01101")
    return t


def t_seg_unit_stride_op() -> VTest:
    t = new("vector_ls_seg_unit_stride_op")
    describe(
        t,
        "The vector unit-stride load and store segment instructions move packed contiguous segments into multiple "
        "destination vector register groups.",
        "Loads (SEW = EEW): vlseg4e16.v vl=3, vlseg8e8.v vl=2 (fields v8-v15), vlseg2e64.v vl=2, vlseg5e32.v "
        "vl=2, each from a base that is not 16-byte aligned: field f of segment i is at base + i*NFIELDS*EEW/8 + "
        "f*EEW/8. Store: vsseg3e8.v vl=4 writes 12 packed bytes and nothing after.",
    )
    src = pat(26, 128)
    s = t.buf("src", src)
    seg_load_case(t, src, s, 4, 16, 3, 2, "vlseg4e16.v")
    seg_load_case(t, src, s, 8, 8, 2, 5, "vlseg8e8.v")
    seg_load_case(t, src, s, 2, 64, 2, 8, "vlseg2e64.v")
    seg_load_case(t, src, s, 5, 32, 2, 4, "vlseg5e32.v")
    d0 = bytes([0x5C]) * 32
    d = t.buf("dst", d0)
    t.vset(4, 8)
    t.la("x6", f"{s}+1")
    t.emit("vlseg3e8.v v8, (x6)")
    t.la("x6", d)
    t.mark("vsseg3e8")
    t.emit("vsseg3e8.v v8, (x6)")
    img = bytearray(d0)
    img[0:12] = src[1:13]
    t.ck_mem(d, 0, words(img, 0, 16), "vsseg3e8.v")
    return t


def t_seg_vd_vs3() -> VTest:
    t = new("vector_ls_seg_unit_stride_vd_vs3")
    describe(
        t,
        "For loads, the _vd_ register will hold the first field loaded from the segment. For stores, the `vs3` "
        "register is read to provide the first field to be stored to each segment.",
        "vlseg2e32.v v13 (vl=3): v13 holds the field at the lowest address of each segment and v14 the second. "
        "vsseg3e16.v v17 with v17, v18, v19 loaded from three different buffers: each segment in memory is "
        "(v17[i], v18[i], v19[i]) in increasing address order.",
    )
    src = pat(27, 64)
    s = t.buf("src", src)
    seg_load_case(t, src, s, 2, 32, 3, 0, "vlseg2e32.v v13", vd=13)
    fl = [store_vals(16, 3, 170 + k) for k in range(3)]
    for k in range(3):
        t.vload(17 + k, 16, fl[k], f"f{k}")
    d0 = bytes([0x5C]) * 32
    d = t.buf("dst", d0)
    t.vset(3, 16)
    t.la("x6", d)
    t.mark("vsseg3e16")
    t.emit("vsseg3e16.v v17, (x6)")
    img = bytearray(d0)
    rev = MUT == "seg_fields_reversed"
    for i in range(3):
        for f in range(3):
            img[6 * i + 2 * f : 6 * i + 2 * f + 2] = fl[2 - f if rev else f][i].to_bytes(2, "little")
    t.ck_mem(d, 0, words(img, 0, 20), "vsseg3e16.v v17")
    return t


def t_seg_constant_stride_op() -> VTest:
    t = new("vector_ls_seg_constant_stride_op")
    describe(
        t,
        "Vector constant-stride segment loads and stores move contiguous segments where each segment is separated "
        "by the byte-stride offset given in the _rs2_ argument.",
        "vlsseg3e8.v stride 5 (vl=4), vlsseg2e32.v stride 12 (vl=3), vlsseg2e16.v stride -8 (vl=3, from base+32): "
        "field f of segment i at base + i*stride + f*EEW/8. vssseg2e16.v stride 12 (vl=3) writes 4-byte segments "
        "12 bytes apart and leaves the gaps unchanged.",
    )
    src = pat(28, 64)
    s = t.buf("src", src)
    seg_load_case(t, src, s, 3, 8, 4, 1, "vlsseg3e8.v stride 5", stride=5)
    seg_load_case(t, src, s, 2, 32, 3, 0, "vlsseg2e32.v stride 12", stride=12)
    seg_load_case(t, src, s, 2, 16, 3, 32, "vlsseg2e16.v stride -8", stride=-8)
    d0 = bytes([0x5C]) * 48
    d = t.buf("dst", d0)
    t.vset(3, 16)
    t.la("x6", s)
    t.emit("vlseg2e16.v v8, (x6)")
    t.la("x6", d)
    t.li("x1", 12)
    t.mark("vssseg2e16")
    t.emit("vssseg2e16.v v8, (x6), x1")
    img = bytearray(d0)
    for i in range(3):
        a = 4 * i if MUT == "seg_stride_is_size" else 12 * i
        img[a : a + 4] = src[4 * i : 4 * i + 4]
    t.ck_mem(d, 0, words(img, 0, 32), "vssseg2e16.v stride 12")
    return t


def t_seg_constant_stride_unordered() -> VTest:
    t = new("vector_ls_seg_constant_stride_unordered")
    describe(
        t,
        "Accesses to the fields within each segment can occur in any order, including the case where the byte "
        "stride is such that segments overlap in memory.",
        "Overlapping segments: vssseg2e8.v with stride 1 (vl=4) leaves byte 0 = field0[0], byte 4 = field1[3], and "
        "each byte j in 1..3 either field0[j] or field1[j-1]; byte 5 is unchanged. vssseg2e16.v with stride 0 in a "
        "register (vl=3): halfword 0 is one of field 0's elements, halfword 1 one of field 1's. Loads: vlsseg2e8.v "
        "with stride 1 reads field0[i] = byte i and field1[i] = byte i+1; vlsseg2e32.v with stride 0 reads the "
        "same segment into every element.",
    )
    src = pat(29, 64)
    s = t.buf("src", src)
    seg_load_case(t, src, s, 2, 8, 4, 3, "vlsseg2e8.v stride 1", stride=1)
    seg_load_case(t, src, s, 2, 32, 3, 8, "vlsseg2e32.v stride 0", stride=0)
    d0 = bytes([0x5C]) * 16
    d = t.buf("dst", d0)
    f0 = list(pat(180, 4))
    f1 = list(pat(181, 4))
    t.vload(8, 8, f0, "f0")
    t.vload(9, 8, f1, "f1")
    t.vset(4, 8)
    t.la("x6", f"{d}+4")
    t.li("x1", 1)
    t.mark("vssseg2e8_s1")
    t.emit("vssseg2e8.v v8, (x6), x1")
    one = MUT == "ordered_first_wins"  # models "field 0 of a later segment never overwrites field 1"
    exp = [f0[0], *[[f1[j - 1]] if one else [f0[j], f1[j - 1]] for j in range(1, 4)], f1[3], 0x5C]
    t.ck_mem(d, 4, exp, "vssseg2e8.v stride 1 (overlapping segments)", unit=1)
    h0 = store_vals(16, 3, 182)
    h1 = store_vals(16, 3, 183)
    t.vload(10, 16, h0, "h0")
    t.vload(11, 16, h1, "h1")
    t.vset(3, 16)
    t.la("x6", f"{d}+12")
    t.li("x1", 0)
    t.mark("vssseg2e16_s0")
    t.emit("vssseg2e16.v v10, (x6), x1")
    t.ck_mem(d, 12, [h0, h1], "vssseg2e16.v stride 0", unit=2)
    return t


def t_seg_indexed_op() -> VTest:
    t = new("vector_ls_seg_indexed_op")
    describe(
        t,
        "Vector indexed segment loads and stores move contiguous segments where each segment is located at an "
        "address given by adding the scalar base address in the _rs1_ field to byte offsets in vector register "
        "_vs2_.",
        "vluxseg2ei8.v at SEW=16 (vl=4, offsets {8, 0, 12, 4}): field f of segment i is the halfword at base + "
        "offset[i] + 2f. vloxseg3ei16.v at SEW=8 (vl=3, offsets {6, 0, 3}). vsuxseg2ei8.v at SEW=32 (vl=3, offsets "
        "{16, 0, 8}) writes the two words of each segment there and nothing else.",
    )
    src = pat(30, 64)
    s = t.buf("src", src)
    for nf, sew, ie, offs, ins in ((2, 16, 8, [8, 0, 12, 4], "vluxseg2ei8.v"), (3, 8, 16, [6, 0, 3], "vloxseg3ei16.v")):
        t.vload(20, ie, offs, f"i{ins[:6]}")
        t.vfill(8, nf + 1)
        t.vset(len(offs), sew)
        t.la("x6", s)
        t.mark(ins.split(".")[0])
        t.emit(f"{ins} v8, (x6), v20")
        sc = sew // 8 if MUT == "index_scaled" else 1
        for f in range(nf):
            ff = nf - 1 - f if MUT == "seg_fields_reversed" else f
            exp = [le(src[o * sc + ff * sew // 8 : o * sc + (ff + 1) * sew // 8]) for o in offs]
            t.ck_reg(8 + f, sew, [*exp, fe(sew)], f"{ins} field {f}")
        t.ck_elem(8 + nf, 0, 32, fe(32), f"{ins}: v{8 + nf} undisturbed")
    d0 = bytes([0x5C]) * 32
    d = t.buf("dst", d0)
    t.vset(3, 32)
    t.la("x6", s)
    t.emit("vlseg2e32.v v8, (x6)")
    offs = [16, 0, 8]
    t.vload(20, 8, offs, "is")
    t.vset(3, 32)
    t.la("x6", d)
    t.mark("vsuxseg2ei8")
    t.emit("vsuxseg2ei8.v v8, (x6), v20")
    img = bytearray(d0)
    for i, o in enumerate(offs):
        img[o : o + 8] = src[8 * i : 8 * i + 8]
    t.ck_mem(d, 0, words(img, 0, 28), "vsuxseg2ei8.v at SEW=32")
    return t


def t_seg_indexed_eew_emul() -> VTest:
    t = new("vector_ls_seg_indexed_eew_emul_op")
    describe(
        t,
        "The data vector register group has EEW=SEW, EMUL=LMUL, while the index vector register group has EEW "
        "encoded in the instruction with EMUL=(EEW/SEW)*LMUL.",
        "- vluxseg2ei32.v at SEW=8, LMUL=1, vl=16: index group v16-v19 (EMUL=4), data fields v8 and v9 (EMUL=1, "
        "all 16 bytes checked), v10 undisturbed.\n"
        "- vloxseg2ei8.v at SEW=32, LMUL=2, vl=8: index EMUL=1/2 in v20, data fields v8-v9 and v10-v11 (8 words "
        "each), v12 undisturbed.",
    )
    src = pat(31, 192)
    s = t.buf("src", src)
    offs = [(i * 11) % 128 for i in range(16)]
    t.vload(16, 32, offs, "iw", "m4")
    t.vfill(8, 3)
    t.vset(16, 8)
    t.la("x6", s)
    t.mark("vluxseg2ei32")
    t.emit("vluxseg2ei32.v v8, (x6), v16")
    ofs = [offs[i % 4] for i in range(16)] if MUT == "index_emul_is_lmul" else offs
    for f in range(2):
        t.ck_reg(8 + f, 8, [src[o + f] for o in ofs], f"vluxseg2ei32.v field {f}")
    t.ck_elem(10, 0, 32, fe(32), "vluxseg2ei32.v: v10 undisturbed")
    offs2 = [40, 0, 16, 8, 32, 24, 56, 48]
    t.vload(20, 8, offs2, "ib")
    t.vfill(8, 5)
    t.vset(8, 32, "m2")
    t.la("x6", s)
    t.mark("vloxseg2ei8")
    t.emit("vloxseg2ei8.v v8, (x6), v20")
    for f in range(2):
        t.ck_reg(8 + 2 * f, 32, [le(src[o + 4 * f : o + 4 * f + 4]) for o in offs2], f"vloxseg2ei8.v field {f}")
    t.ck_elem(12, 0, 32, fe(32), "vloxseg2ei8.v: v12 undisturbed")
    return t


def t_seg_indexed_emul_nfields_val() -> VTest:
    t = new("vector_ls_seg_indexed_emul_nfields_val")
    describe(
        t,
        "The EMUL * NFIELDS {le} 8 constraint applies to the data vector register group.",
        "The index group's EMUL * NFIELDS may exceed 8: vluxseg4ei32.v at SEW=8, LMUL=1, vl=16 (index EMUL=4, "
        "4*4 = 16; data 1*4 = 4) and, on RV64, vluxseg8ei64.v at SEW=8, LMUL=1, vl=16 (index EMUL=8 in v16-v23; "
        "data fields v8-v15) execute without trapping and load every field.",
    )
    src = pat(32, 256)
    s = t.buf("src", src)
    offs = [(i * 13) % 128 for i in range(16)]
    t.vload(16, 32, offs, "iw", "m4")
    t.vfill(8, 5)
    t.vset(16, 8)
    t.la("x6", s)
    t.mark("vluxseg4ei32")
    t.emit("vluxseg4ei32.v v8, (x6), v16")
    ofs = [offs[i % 4] for i in range(16)] if MUT == "index_emul_is_lmul" else offs
    for f in range(4):
        t.ck_reg(8 + f, 8, [src[o + f] for o in ofs], f"vluxseg4ei32.v field {f}")
    t.ck_elem(12, 0, 32, fe(32), "vluxseg4ei32.v: v12 undisturbed")
    with t.rv64_only():
        t.vload(16, 64, offs, "id", "m8")
        t.vfill(8, 8)
        t.vset(16, 8)
        t.la("x6", s)
        t.mark("vluxseg8ei64")
        t.emit("vluxseg8ei64.v v8, (x6), v16")
        for f in (0, 3, 7):
            t.ck_reg(8 + f, 8, [src[o + f] for o in offs], f"vluxseg8ei64.v field {f}")
    return t


# ================================================================ order
def t_program_order() -> VTest:
    t = new("vector_ls_program_order")
    describe(
        t,
        "Vector memory instructions appear to execute in program order on the local hart.",
        "Back-to-back accesses to the same bytes see each other in program order: sw then vle32.v (the load sees "
        "the stored word); vse32.v then lw, and vse32.v then vle8.v (both see the vector store); vle32.v then sw "
        "(the register keeps the old value) then vle32.v (sees the new one); vse8.v then vse32.v over the same "
        "bytes (the later store wins) then sb into the middle then vle16.v (sees the merge); a masked vse32.v "
        "(mask 0b0101) then vle32.v sees new words 0 and 2 and old words 1 and 3.",
    )
    b0 = pat(33, 32)
    b = t.buf("buf", b0)
    stale = MUT == "program_order_stale"
    t.vfill(8)
    t.la("x6", b)
    t.li("x7", 0x13579BDF)
    t.vset(4, 32)
    t.mark("sw_vle32")
    t.emit("sw x7, 4(x6)")
    t.emit("vle32.v v8, (x6)")
    w = elems(b0, 0, 32, 4)
    t.ck_reg(8, 32, [w[0], w[1] if stale else 0x13579BDF, w[2], w[3]], "vle32.v after sw")
    vals = store_vals(32, 4, 191)
    t.vload(16, 32, vals, "sv")
    t.vset(4, 32)
    t.la("x6", b)
    t.mark("vse32_lw")
    t.emit("vse32.v v16, (x6)")
    t.emit("lw x7, 8(x6)")
    t.check("x7", sx(vals[2], 32), t.lab, "lw after vse32.v")
    t.vset(16, 8)
    t.mark("vse32_vle8")
    t.emit("vle8.v v8, (x6)")
    img = b"".join(v.to_bytes(4, "little") for v in vals)
    t.ck_reg(8, 8, list(img[:16]), "vle8.v after vse32.v")
    t.vset(4, 32)
    t.la("x6", b)
    t.mark("vle32_sw")
    t.emit("vle32.v v8, (x6)")
    t.li("x7", 0x2468ACE)
    t.emit("sw x7, 0(x6)")
    t.ck_reg(8, 32, vals, "vle32.v before sw keeps the old word")
    t.vset(4, 32)
    t.la("x6", b)
    t.emit("vle32.v v8, (x6)")
    t.ck_elem(8, 0, 32, vals[0] if stale else 0x2468ACE, "vle32.v after sw sees the new word")
    bv = list(pat(192, 8))
    t.vload(20, 8, bv, "sb8")
    t.vset(8, 8)
    t.la("x6", b)
    t.mark("vse8_vse32")
    t.emit("vse8.v v20, (x6)")
    t.vset(4, 32)
    t.emit("vse32.v v16, (x6)")
    t.li("x7", 0x77)
    t.emit("sb x7, 5(x6)")
    t.vset(8, 16)
    t.emit("vle16.v v8, (x6)")
    m = bytearray(img)
    m[5] = 0x77
    t.ck_reg(8, 16, elems(bytes(m), 0, 16, 8), "vse8.v, vse32.v, sb, vle16.v")
    n2 = store_vals(32, 4, 193)
    t.vload(16, 32, n2, "sv2")
    t.vmask(0b0101)
    t.vset(4, 32)
    t.la("x6", b)
    t.mark("vse32m_vle32")
    t.emit("vse32.v v16, (x6), v0.t")
    t.emit("vle32.v v8, (x6)")
    mw = elems(bytes(m), 0, 32, 4)
    t.ck_reg(8, 32, [n2[0], mw[1], n2[2], mw[3]], "masked vse32.v then vle32.v")
    return t


def dup_store(t: VTest, d: str, ordered: bool, eew: int, offs: list[int], mask: int | None, seed: int) -> list[int]:
    vals = store_vals(eew, len(offs), seed)
    t.vload(16, eew, vals, f"v{seed}")
    t.vload(20, 8, offs, f"o{seed}")
    if mask is not None:
        t.vmask(mask)
    t.vset(len(offs), eew, lmul_for(len(offs), eew))
    t.la("x6", d)
    nm = f"vs{'o' if ordered else 'u'}xei8"
    t.mark(f"{nm}_{seed}")
    t.emit(f"{nm}.v v16, (x6), v20" + (", v0.t" if mask is not None else ""))
    return vals


def ordered_final(vals: list[int], offs: list[int], loc: int, mask: int | None) -> int:
    act = [i for i, o in enumerate(offs) if o == loc and (mask is None or mask >> i & 1)]
    return vals[act[0] if MUT == "ordered_first_wins" else act[-1]]


def unordered_legal(vals: list[int], offs: list[int], loc: int) -> list[int]:
    return [vals[i] for i, o in enumerate(offs) if o == loc]


def t_stride_ordered_op() -> VTest:
    t = new("vector_ls_stride_ordered_op")
    describe(
        t,
        "Vector unit-stride and constant-stride memory accesses do not guarantee ordering between individual "
        "element accesses. The vector indexed load and store memory operations have two forms, ordered and "
        "unordered. The indexed-ordered variants preserve element ordering on memory accesses.",
        "Indexed-ordered: vsoxei8.v at SEW=32 with every offset 0 (vl=4) leaves the last element in memory. "
        "Constant-stride: vsse32.v with stride 0 in a register (vl=4) leaves any one element (no ordering).",
    )
    d0 = bytes([0x5C]) * 16
    d = t.buf("dst", d0)
    offs = [0, 0, 0, 0]
    vals = dup_store(t, d, True, 32, offs, None, 201)
    t.ck_mem(d, 0, [ordered_final(vals, offs, 0, None), M5C], "vsoxei8.v: the last element wins")
    restore(t, d, d0, 0, 8)
    vals = store_vals(32, 4, 202)
    t.vload(16, 32, vals, "sv")
    t.vset(4, 32)
    t.la("x6", d)
    t.li("x1", 0)
    t.mark("vsse32_0")
    t.emit("vsse32.v v16, (x6), x1")
    t.ck_mem(d, 0, [vals, M5C], "vsse32.v stride 0: any element")
    return t


def t_stride_unordered_op() -> VTest:
    t = new("vector_ls_stride_unordered_op")
    describe(
        t,
        "For unordered instructions (`mop[1:0]`!=11) there is no guarantee on element access order. If the "
        "accesses are to a strongly ordered IO region, the element accesses can be initiated in any order.",
        "vsuxei8.v at SEW=32 with offsets {0, 0, 0, 0} leaves any of the 4 elements; with offsets {0, 4, 0, 4} "
        "word 0 is element 0 or 2 and word 1 element 1 or 3. Nothing else is written. (The IO-region part is not "
        "observable without a strongly ordered IO device.)",
    )
    d0 = bytes([0x5C]) * 16
    d = t.buf("dst", d0)
    for offs, seed in (([0, 0, 0, 0], 211), ([0, 4, 0, 4], 212)):
        vals = dup_store(t, d, False, 32, offs, None, seed)
        l0 = unordered_legal(vals, offs, 0)
        l1 = unordered_legal(vals, offs, 4) or [M5C]
        if MUT == "ordered_first_wins":
            l0, l1 = [l0[0]], [l1[0]]
        t.ck_mem(d, 0, [l0, l1, M5C], f"vsuxei8.v offsets {offs}")
        restore(t, d, d0, 0, 12)
    return t


def t_indexed_ordered_ordered() -> VTest:
    t = new("vector_ls_indexed_ordered_ordered")
    describe(
        t,
        "Except for vector indexed-ordered loads and stores, element operations are unordered within the instruction.",
        "SEW=16, offsets {0, 2, 0, 2, 0} (vl=5): vsoxei8.v leaves halfword 0 = element 4 and halfword 1 = element "
        "3; vsuxei8.v leaves halfword 0 = element 0, 2 or 4 and halfword 1 = element 1 or 3; vsse16.v with stride 0 "
        "in a register leaves any of its 5 elements.",
    )
    d0 = bytes([0x5C]) * 16
    d = t.buf("dst", d0)
    offs = [0, 2, 0, 2, 0]
    vals = dup_store(t, d, True, 16, offs, None, 221)
    exp = [ordered_final(vals, offs, 0, None), ordered_final(vals, offs, 2, None), 0x5C5C]
    t.ck_mem(d, 0, exp, "vsoxei8.v", unit=2)
    restore(t, d, d0, 0, 8)
    vals = dup_store(t, d, False, 16, offs, None, 222)
    t.ck_mem(d, 0, [unordered_legal(vals, offs, 0), unordered_legal(vals, offs, 2), 0x5C5C], "vsuxei8.v", unit=2)
    restore(t, d, d0, 0, 8)
    vals = store_vals(16, 5, 223)
    t.vload(16, 16, vals, "sv")
    t.vset(5, 16)
    t.la("x6", d)
    t.li("x1", 0)
    t.mark("vsse16_0")
    t.emit("vsse16.v v16, (x6), x1")
    t.ck_mem(d, 0, [vals, 0x5C5C], "vsse16.v stride 0", unit=2)
    return t


def t_indexed_ordered_rvwmo() -> VTest:
    t = new("vector_ls_indexed_ordered_rvwmo")
    describe(
        t,
        "Vector indexed-ordered loads and stores read and write elements from/to memory in element order "
        "respectively, obeying RVWMO at the element level.",
        "vsoxei8.v at SEW=32 with offsets {4, 0, 4, 8, 0} (vl=5): word 0 = element 4, word 1 = element 2, word 2 "
        "= element 3. Masked with v0=0b01011 (elements 2 and 4 inactive): word 0 = element 1, word 1 = element 0, "
        "word 2 = element 3. vsoxseg2ei8.v at SEW=16 with offsets {0, 0, 0} (vl=3): the segment written last "
        "(segment 2) is in memory.",
    )
    d0 = bytes([0x5C]) * 16
    d = t.buf("dst", d0)
    offs = [4, 0, 4, 8, 0]
    for mask, seed in ((None, 231), (0b01011, 232)):
        vals = dup_store(t, d, True, 32, offs, mask, seed)
        exp = [ordered_final(vals, offs, o, mask) for o in (0, 4, 8)]
        t.ck_mem(d, 0, [*exp, M5C], f"vsoxei8.v mask {mask}")
        restore(t, d, d0, 0, 16)
    f0 = store_vals(16, 3, 233)
    f1 = store_vals(16, 3, 234)
    t.vload(8, 16, f0, "f0")
    t.vload(9, 16, f1, "f1")
    t.vload(20, 8, [0, 0, 0], "z")
    t.vset(3, 16)
    t.la("x6", d)
    t.mark("vsoxseg2ei8")
    t.emit("vsoxseg2ei8.v v8, (x6), v20")
    k = 0 if MUT == "ordered_first_wins" else 2
    t.ck_mem(d, 0, [f0[k], f1[k], 0x5C5C], "vsoxseg2ei8.v: the last segment wins", unit=2)
    return t


# ================================================================ masking (unprivileged)
def t_masked_inactive_behavior() -> VTest:
    t = new("vector_masked_inactive_behavior")
    describe(
        t,
        "Masked vector loads do not update inactive elements in the destination vector register group, unless "
        "masked agnostic is specified (vtype[vma]=1).",
        "Mask 0b01010 (vl=5, LMUL=2, tu; element 5 is tail): vle32.v, vlse32.v (stride 8) and vluxei8.v with "
        "vma=0 leave elements 0, 2 and 4 undisturbed; with vma=1 each of them is undisturbed or all ones. Active "
        "elements are loaded and the tail element is undisturbed. vle32ff.v (no possible fault) with vma=0 leaves "
        "inactive element 0 undisturbed (elements past a trimmed vl are not checked). vlseg2e16.v with vma=1 "
        "accepts, for each field element of an inactive segment, undisturbed or all ones.",
        context="vreg_agnostic_op: agnostic elements either keep their value or are overwritten with 1s, in any "
        "combination. vle32ff.v without a fault may trim vl (vector_ff_no_exception), but at least to 1.",
    )
    src = pat(34, 64)
    s = t.buf("src", src)
    mask = 0b01010
    ix = [12, 0, 4, 8, 20]
    t.vload(20, 8, ix, "ix")
    for ma in (False, True):
        for ins, st in (("vle32.v v8, (x6)", 4), ("vlse32.v v8, (x6), x1", 8), ("vluxei8.v v8, (x6), v20", "ix")):
            t.vfill(8, 2)
            t.vmask(mask)
            t.vset(5, 32, "m2", ma=ma)
            t.la("x6", s)
            t.li("x1", 8)
            t.mark(ins.split(".")[0] + ("_ma" if ma else "_mu"))
            t.emit(ins + ", v0.t")
            offs = ix if isinstance(st, str) else [i * st for i in range(5)]
            exp: list = []
            for i in range(5):
                v = le(src[offs[i] : offs[i] + 4])
                if mask >> i & 1 or (MUT == "inactive_written_mu" and not ma):
                    exp.append(v)
                else:
                    exp.append([fe(32), ones(32)] if ma else fe(32))
            t.ck_reg(8, 32, [*exp, fe(32)], f"{ins.split()[0]} vma={int(ma)}")
    t.vfill(8, 2)
    t.vmask(mask)
    t.vset(5, 32, "m2")
    t.la("x6", s)
    t.mark("vle32ff_mu")
    t.emit("vle32ff.v v8, (x6), v0.t")
    t.ck_elem(8, 0, 32, le(src[0:4]) if MUT == "inactive_written_mu" else fe(32), "vle32ff.v vma=0: element 0")
    seg_load_case(t, src, s, 2, 16, 5, 0, "vlseg2e16.v vma=1", mask=mask, ma=True)
    return t


# ================================================================ misaligned (unprivileged)
def t_misaligned_exception() -> VTest:
    t = new("vector_ls_misaligned_exception")
    describe(
        t,
        "If an element accessed by a vector memory instruction is not naturally aligned to the size of the "
        "element, either the element is transferred successfully or an address-misaligned exception is raised on "
        "that element.",
        "Aligned elements never raise address-misaligned: vle8.v at an odd address, vle16.v at 2 mod 4, vle32.v at "
        "4 mod 8, vle64.v at 8 mod 16, vlse32.v with stride 8 (each checked for the right data).\n"
        "Misaligned elements: vle16.v at +1, vle32.v at +2, vle64.v at +4 (every element misaligned) and vse32.v "
        "at +1. Legal outcomes: no trap with the right data (loads) or bytes (store), address-misaligned (4/6), or "
        "an access fault (5/7). On a trap, vstart = j < vl names the faulting element and stval is 0 or that "
        "element's address (base + j*EEW/8), or for an access fault any address of the element (the faulting "
        "portion).\n"
        "vlse32.v with stride 6 (vl=4): elements 1 and 3 are misaligned, 0 and 2 aligned; a trap must name an odd "
        "element (vstart odd) with stval 0 or base + 6*vstart, and element 0 must have been loaded.",
        context="machine.adoc pma_mag_exc: implementations may raise access-fault instead of address-misaligned "
        "for some misaligned accesses. " + PRECISE,
    )
    src = pat(35, 128)
    s = t.buf("src", src)
    for eew, off, ins in (
        (8, 1, "vle8.v v8, (x6)"),
        (16, 6, "vle16.v v8, (x6)"),
        (32, 12, "vle32.v v8, (x6)"),
        (64, 24, "vle64.v v8, (x6)"),
        (32, 16, "vlse32.v v8, (x6), x1"),
    ):
        n = min(4, 128 // eew)
        t.vfill(8)
        t.vset(n, eew)
        t.la("x6", f"{s}+{off}")
        t.li("x1", 8)
        bad = MUT == "misaligned_e8_traps" and eew == 8
        t.win([ins], LOAD_MIS if bad else "ok", f"{ins.split()[0]} aligned elements")
        if bad:
            t.emit("csrw vstart, x0")
            continue
        t.ck_reg(8, eew, elems(src, off, eew, n, 8 if "vlse" in ins else eew // 8), f"{ins.split()[0]} at +{off}")
    d0 = bytes([0x5C]) * 32
    d = t.buf("dst", d0)
    svals = store_vals(32, 2, 241)
    cases = [
        ("vle16.v v8, (x6)", 16, 1, 2, False, False),
        ("vle32.v v8, (x6)", 32, 2, 4, False, False),
        ("vle64.v v8, (x6)", 64, 4, 8, False, False),
        ("vlse32.v v8, (x6), x1", 32, 0, 6, True, False),
        ("vse32.v v16, (x6)", 32, 1, 4, False, True),
    ]
    for ins, eew, off, step, odd, store in cases:
        n = 2 if store else min(4, 128 // eew)
        if store:
            t.vload(16, 32, svals, "sv")
        t.vfill(8)
        t.vset(n, eew)
        t.la("x6", f"{d if store else s}+{off}")
        t.li("x1", 6)
        misal, af = (STORE_MIS, STORE_AF) if store else (LOAD_MIS, LOAD_AF)
        t.win([ins], ["ok", misal, af], f"{ins.split()[0]} at +{off}{' stride 6' if odd else ''}")
        trapped(t)

        def on_trap(step: int = step, odd: bool = odd, n: int = n, eew: int = eew) -> None:
            t.emit("csrr x8, vstart")
            t.emit("csrw vstart, x0")
            t.emit(f"sltiu x9, x8, {n}")
            t.check_bool("x9", t.lab, "vstart < vl")
            if odd:
                t.emit("andi x9, x8, 1")
                t.check_bool("x9", t.lab, "vstart names a misaligned (odd) element")
            t.emit("AI_LOG(x7, TRAPLOG_TVAL)", 10)
            if step == 6:
                t.emit("slli x9, x8, 1")
                t.emit("slli x8, x8, 2")
                t.emit("add x9, x9, x8")
            else:
                t.emit(f"slli x9, x8, {step.bit_length() - 1}")
            t.emit("add x9, x9, x6")
            t.emit("sub x9, x7, x9")  # stval - element address
            t.emit("seqz x8, x9")
            t.emit("seqz x7, x7")
            t.emit("or x8, x8, x7")
            t.comment("access fault (5/7): stval may be any address of the faulting portion of the element")
            t.emit(f"sltiu x9, x9, {eew // 8}")
            t.emit("andi x7, x14, 1")  # 5 and 7 (access faults) are odd, 4 and 6 even
            t.emit("and x9, x9, x7")
            t.emit("or x9, x9, x8")
            t.check_bool("x9", t.lab, "stval is 0, the faulting element's address, or (access fault) inside it")
            if odd:
                t.ck_elem(8, 0, 32, le(src[0:4]), "element 0 (aligned, before vstart) was loaded")

        def on_ok(eew: int = eew, off: int = off, step: int = step, n: int = n, store: bool = store) -> None:
            if store:
                img = bytearray(d0)
                img[off : off + 8] = b"".join(v.to_bytes(4, "little") for v in svals)
                t.ck_mem(d, 0, words(img, 0, 12), "vse32.v at +1 succeeded")
            else:
                t.ck_reg(8, eew, elems(src, off, eew, n, step), "the misaligned load succeeded")

        t.either("x1", on_trap, on_ok)
    return t


# ================================================================ fault-only-first helpers
def ck_vl_range(t: VTest, lo: int, hi: int, desc: str, reg: str = "x6") -> None:
    """reg = vl; check lo <= vl <= hi."""
    t.emit(f"csrr {reg}, vl")
    t.emit(f"addi x9, {reg}, -{lo}")
    t.emit(f"sltiu x9, x9, {hi - lo + 1}")
    t.check_bool("x9", t.lab, f"{desc}: {lo} <= vl <= {hi}")


def ck_elems_below_vl(
    t: VTest, vreg: int, eew: int, exp: list[int], desc: str, vlreg: str = "x6", start: int = 0
) -> None:
    """For i >= start: element i (eew <= 32) equals exp[i], or i >= vl (vl held in vlreg). Clobbers x7-x9."""
    for i in range(start, len(exp)):
        t.vel("x7", vreg, i, eew)
        t.load("x8", sx(exp[i], eew))
        t.emit("sub x8, x8, x7")
        t.emit("seqz x8, x8")
        t.emit(f"sltiu x9, {vlreg}, {i + 1}")
        t.emit("or x8, x8, x9")
        t.check_bool("x8", t.lab, f"{desc}: element {i} loaded, or past the new vl")


def ff_vl_bounds(k: int) -> tuple[int, int]:
    """Legal trimmed vl after a fault-only-first load whose element k is the first to fault."""
    if MUT == "ff_vl_plus1":
        return (k + 1, k + 1)
    return (1, k)


def t_ff_no_exception() -> VTest:
    t = new("vector_ff_no_exception")
    describe(
        t,
        "Even when an exception is not raised, implementations are permitted to process fewer than vl elements and "
        "reduce vl accordingly, but if vstart=0 and vl>0, then at least one element must be processed.",
        "Fault-only-first loads with no possible fault (all elements in the data section): vle8ff.v (vl=16), "
        "vle32ff.v (vl=4), vle64ff.v (vl=2), vlseg2e16ff.v (vl=4): the new vl is between 1 and the old vl, every "
        "element below the new vl is loaded, and element 0 always is. With vl=0, vle32ff.v leaves vl=0 and v8 "
        "undisturbed.",
    )
    src = pat(36, 64)
    s = t.buf("src", src)
    for eew, n, ins in ((8, 16, "vle8ff.v"), (32, 4, "vle32ff.v"), (64, 2, "vle64ff.v"), (16, 4, "vlseg2e16ff.v")):
        t.vfill(8, 2)
        t.vset(n, eew)
        t.la("x6", s)
        t.mark(ins.split(".")[0])
        t.emit(f"{ins} v8, (x6)")
        if MUT == "ff_zero_progress":
            t.ck_csr("vl", 0, "mutant: no element processed")
            continue
        ck_vl_range(t, 1, n, ins)
        if eew == 64:
            e = elems(src, 0, 64, 2)
            t.ck_elem(8, 0, 64, e[0], f"{ins}: element 0")
            t.emit("csrr x6, vl")
            for h in range(2):
                t.vel("x7", 8, 2 + h, 32)
                t.load("x8", sx(e[1] >> (32 * h), 32))
                t.emit("sub x8, x8, x7")
                t.emit("seqz x8, x8")
                t.emit("sltiu x9, x6, 2")
                t.emit("or x8, x8, x9")
                t.check_bool("x8", t.lab, f"{ins}: element 1 word {h} loaded, or vl = 1")
        else:
            ev, st = (16, 4) if "seg" in ins else (eew, eew // 8)
            ck_elems_below_vl(t, 8, ev, elems(src, 0, ev, n, st), ins)
    t.vfill(8)
    t.vset(0, 32)
    t.la("x6", s)
    t.mark("vle32ff_vl0")
    t.emit("vle32ff.v v8, (x6)")
    t.ck_csr("vl", 0, "vle32ff.v with vl=0")
    t.ck_reg(8, 32, [fe(32)] * 4, "vle32ff.v with vl=0 writes nothing")
    return t


# ================================================================ S-mode fault tests
def t_ls_vstart() -> VTest:
    t = new("vector_ls_vstart", s=True)
    describe(
        t,
        "All vector loads and stores may generate and accept a non-zero vstart value.",
        SPACE + " Page A valid, page B after it. SEW=32, LMUL=1, vl=4, base = VA_B - 8, so elements 0-1 lie in "
        "page A and 2-3 in page B.\n"
        "Generate (load): with B absent, vle32.v takes a load page fault (13) with xepc at the load, stval 0 or "
        "VA_B (element 2's address), vstart = 2, and elements 0-1 loaded (they precede vstart).\n"
        "Accept (load): map B, overwrite elements 0-1 in memory, write vstart = 2 back and re-execute: elements "
        "0-1 keep the values loaded before the trap, 2-3 are loaded from B, and vstart reads 0 afterwards. Then "
        "with page A absent and vstart = 2 the load does not fault (prestart elements are not accessed).\n"
        "Generate/accept (store): with B read-only, vse32.v takes a store page fault (15), stval 0 or VA_B, "
        "vstart = 2, words 0-1 written to A and B unchanged. Make B writable, overwrite A's two words with "
        "markers, write vstart = 2 back and re-execute: the markers stay (prestart elements are not stored), B "
        "gets elements 2-3, vstart reads 0.\n"
        "Strided: vlse32.v with stride 4096 (vl=3) from VA_B - 0x100 faults on element 1 (B absent): vstart = 1, "
        "stval 0 or VA_B + 0xf00, element 0 loaded.",
        context=PRECISE + " " + PRESTART + " " + STVAL + " Other access classes generate and accept vstart in "
        "vector_ls_stride_unordered_precise (indexed), vector_ls_seg_vstart_dep (segments), "
        "vector_ls_seg_wholereg_eew and vector_ls_seg_wholereg_evl (whole-register).",
    )

    def body(p: Pages) -> None:
        win = p.window_bytes()
        ld = elems(win, 248, 32, 4)
        vs = 3 if MUT == "vstart_plus1" else 2
        tv = [p.va(-8)] if MUT == "xtval_base" else [0, p.va_b]
        p.addr("x6", -8)
        t.vfill(8)
        t.vset(4, 32)
        t.win(["vle32.v v8, (x6)"], LOAD_PF, "vle32.v with element 2 on an absent page", tv)
        t.ck_csr("vstart", vs, "vstart is the faulting element")
        t.emit("csrw vstart, x0")
        t.ck_reg(8, 32, ld[:2], "elements before vstart were loaded")
        p.set_b(LEAF)
        marker(t, p.a, [0xFF8, 0xFFC], 0x11223344)
        p.addr("x6", -8)
        t.vset(4, 32)
        set_vstart(t, 2)
        t.mark("resume")
        t.emit("vle32.v v8, (x6)")
        t.ck_csr("vstart", 0, "vstart after the resumed load")
        pre = [0x11223344] * 2 if MUT == "vstart_restart_0" else ld[:2]
        t.ck_reg(8, 32, pre + ld[2:], "resumed load: prestart elements kept, 2-3 loaded")
        t.comment("page A absent: prestart elements are not accessed")
        p.pt.raw(p.va_a, 0, note="page A absent")
        t.emit("sfence.vma x0, x0")
        t.vfill(8)
        p.addr("x6", -8)
        t.vset(4, 32)
        set_vstart(t, 2)
        t.win(
            ["vle32.v v8, (x6)"],
            LOAD_PF if MUT == "vstart_restart_0" else "ok",
            "vle32.v with vstart=2 and prestart elements on an absent page",
        )
        t.emit("csrw vstart, x0")
        t.ck_reg(8, 32, [fe(32)] * 2 + ld[2:], "prestart elements undisturbed, 2-3 loaded")
        p.pt.leaf(p.va_a, p.a, LEAF, note="page A back")
        p.set_b(RO)
        vals = store_vals(32, 4, 251)
        t.vload(16, 32, vals, f"sv{p.xlen}")
        p.addr("x6", -8)
        t.vset(4, 32)
        t.win(["vse32.v v16, (x6)"], STORE_PF, "vse32.v with element 2 on a read-only page", tv)
        t.ck_csr("vstart", vs, "vse32.v: vstart is the faulting element")
        t.emit("csrw vstart, x0")
        t.ck_mem(p.a, 0xFF8, vals[:2], "vse32.v: elements before vstart were stored")
        t.ck_mem(p.b, 0, words(p.b_data, 0, 8), "vse32.v: read-only page B unchanged")
        p.set_b(LEAF)
        marker(t, p.a, [0xFF8, 0xFFC])
        p.addr("x6", -8)
        t.vset(4, 32)
        set_vstart(t, 2)
        t.mark("store_resume")
        t.emit("vse32.v v16, (x6)")
        t.ck_csr("vstart", 0, "vstart after the resumed store")
        t.ck_mem(p.a, 0xFF8, vals[:2] if MUT == "vstore_restart_0" else [0x0BADF00D] * 2, "prestart words not stored")
        t.ck_mem(p.b, 0, vals[2:], "resumed vse32.v: elements 2-3 stored")
        p.set_b(None)
        p.addr("x6", -0x100)
        t.li("x1", 0x1000)
        t.vfill(8)
        t.vset(3, 32)
        tv2 = [p.va(-0x100)] if MUT == "xtval_base" else [0, p.va(0xF00)]
        t.win(["vlse32.v v8, (x6), x1"], LOAD_PF, "vlse32.v stride 4096 with element 1 on an absent page", tv2)
        t.ck_csr("vstart", 2 if MUT == "vstart_plus1" else 1, "vlse32.v: vstart is the faulting element")
        t.emit("csrw vstart, x0")
        t.ck_elem(8, 0, 32, le(win[0:4]), "vlse32.v: element 0 loaded")

    both(t, lambda x: Pages(t, x, None).setup(body))
    return t


def t_unordered_precise() -> VTest:
    t = new("vector_ls_stride_unordered_precise", s=True)
    describe(
        t,
        "For implementations with precise vector traps, exceptions on indexed-unordered stores must also be precise.",
        SPACE + " vsuxei16.v at SEW=32, vl=4, base = VA_B - 0x100, offsets {0x10, 0x20, 0x100, 0x30}: element 2 "
        "is the only one in page B (read-only), so the store page fault (15) has vstart = 2, stval 0 or VA_B, and "
        "elements 0 and 1 are in memory (element 3 may or may not be: the region is idempotent). With B writable, "
        "markers over elements 0-1 and vstart = 2 written back, the re-executed store writes elements 2 and 3 and "
        "leaves the markers. With offsets {0x100, 0x10} (element 0 in B) the trap has vstart = 0.",
        context=PRECISE + " The standard V extension has precise traps only. " + STVAL,
    )

    def body(p: Pages) -> None:
        vals = store_vals(32, 4, 261)
        t.vload(16, 32, vals, f"sv{p.xlen}")
        offs = [0x10, 0x20, 0x100, 0x30]
        t.vload(20, 16, offs, f"ix{p.xlen}")
        p.addr("x6", -0x100)
        t.vset(4, 32)
        t.win(["vsuxei16.v v16, (x6), v20"], STORE_PF, "vsuxei16.v with element 2 on a read-only page", [0, p.va_b])
        t.ck_csr("vstart", 3 if MUT == "unordered_last_vstart" else 2, "vsuxei16.v: vstart is element 2")
        t.emit("csrw vstart, x0")
        t.ck_mem(p.a, 0xF10, [vals[0]], "element 0 stored")
        t.ck_mem(p.a, 0xF20, [vals[1]], "element 1 stored")
        t.ck_mem(p.a, 0xF30, [[le(p.a_data[0x30:0x34]), vals[3]]], "element 3 stored or not")
        p.set_b(LEAF)
        marker(t, p.a, [0xF10, 0xF20])
        t.vload(20, 16, offs, f"ix2{p.xlen}")
        p.addr("x6", -0x100)
        t.vset(4, 32)
        set_vstart(t, 2)
        t.mark("resume")
        t.emit("vsuxei16.v v16, (x6), v20")
        t.ck_csr("vstart", 0, "after the resumed store")
        t.ck_mem(p.a, 0xF10, [0x0BADF00D], "prestart element 0 not stored again")
        t.ck_mem(p.a, 0xF20, [0x0BADF00D], "prestart element 1 not stored again")
        t.ck_mem(p.b, 0, [vals[2]], "element 2 stored")
        t.ck_mem(p.a, 0xF30, [vals[3]], "element 3 stored")
        p.set_b(RO)
        t.vload(20, 16, [0x100, 0x10], f"ix3{p.xlen}")
        p.addr("x6", -0x100)
        t.vset(2, 32)
        t.win(["vsuxei16.v v16, (x6), v20"], STORE_PF, "vsuxei16.v with element 0 on a read-only page", [0, p.va_b])
        t.ck_csr("vstart", 1 if MUT == "unordered_last_vstart" else 0, "vsuxei16.v: vstart is element 0")
        t.emit("csrw vstart, x0")

    both(t, lambda x: Pages(t, x, RO).setup(body))
    return t


def t_masked_memory_access() -> VTest:
    t = new("vector_masked_memory_access", s=True)
    describe(
        t,
        "Vector loads and stores can be masked, and they only access memory or raise exceptions for active elements.",
        SPACE + " Page B absent. Elements on page B that are masked off raise no fault: vle32.v (base VA_B - 8, "
        "vl=4, mask 0b0011), vlse32.v (stride 4096, vl=2, mask 0b01), vluxei16.v (offsets {0x10, 0x180} from "
        "VA_B - 0x100, mask 0b01), vlseg2e32.v (vl=2, base VA_B - 8, mask 0b01) and vse32.v (mask 0b0011) "
        "complete without a trap and load or store the active elements; the masked-off loaded element stays "
        "undisturbed. With mask 0b0111, vle32.v faults (13) on element 2 (vstart = 2). On a valid page, vse32.v "
        "with mask 0b0101 writes words 0 and 2 and leaves 1 and 3 unchanged.",
    )

    def body(p: Pages) -> None:
        win = p.window_bytes()
        mf = MUT == "masked_off_faults"
        cases = [
            ("vle32.v v8, (x6), v0.t", -8, 4, 0b0011, 2),
            ("vlse32.v v8, (x6), x1, v0.t", -0x100, 2, 0b01, 1),
            ("vluxei16.v v8, (x6), v20, v0.t", -0x100, 2, 0b01, 1),
            ("vlseg2e32.v v8, (x6), v0.t", -8, 2, 0b01, 1),
        ]
        for ins, off, n, mask, first_bad in cases:
            if "vluxei" in ins:
                t.vload(20, 16, [0x10, 0x180], f"ix{p.xlen}")
            t.vfill(8, 2)
            t.vmask(mask)
            t.vset(n, 32)
            p.addr("x6", off)
            t.li("x1", 0x1000)
            t.win([ins], LOAD_PF if mf else "ok", f"{ins.split()[0]} with masked-off elements on an absent page")
            if mf:
                t.emit("csrw vstart, x0")
                continue
            if "vluxei" in ins:
                t.ck_elem(8, 0, 32, le(win[0x10:0x14]), "vluxei16.v: active element 0 loaded")
            elif "seg" in ins:
                t.ck_elem(8, 0, 32, le(win[248:252]), "vlseg2e32.v: active segment field 0")
                t.ck_elem(9, 0, 32, le(win[252:256]), "vlseg2e32.v: active segment field 1")
            else:
                t.ck_elem(8, 0, 32, le(win[256 + off : 260 + off]), f"{ins.split()[0]}: element 0 loaded")
            t.ck_elem(8, first_bad, 32, fe(32), f"{ins.split()[0]}: masked-off element undisturbed")
        vals = store_vals(32, 4, 271)
        t.vload(16, 32, vals, f"sv{p.xlen}")
        t.vmask(0b0011)
        t.vset(4, 32)
        p.addr("x6", -8)
        t.win(
            ["vse32.v v16, (x6), v0.t"], STORE_PF if mf else "ok", "vse32.v with masked-off elements on an absent page"
        )
        t.emit("csrw vstart, x0")
        if not mf:
            t.ck_mem(p.a, 0xFF8, vals[:2], "vse32.v masked: active elements stored")
        t.vfill(8)
        t.vmask(0b0111)
        t.vset(4, 32)
        p.addr("x6", -8)
        t.win(["vle32.v v8, (x6), v0.t"], LOAD_PF, "vle32.v with an active element on an absent page", [0, p.va_b])
        t.ck_csr("vstart", 2, "vstart is the active faulting element")
        t.emit("csrw vstart, x0")
        t.vmask(0b0101)
        t.vset(4, 32)
        p.addr("x6", -0x40)
        t.mark("vse32_m0101")
        t.emit("vse32.v v16, (x6), v0.t")
        ow = elems(p.a_data, 0xC0, 32, 4)
        t.ck_mem(p.a, 0xFC0, [vals[0], ow[1], vals[2], ow[3]], "vse32.v mask 0b0101 on a valid page")

    both(t, lambda x: Pages(t, x, None).setup(body))
    return t


def t_ff_trigger() -> VTest:
    t = new("vector_ff_trigger", s=True)
    describe(
        t,
        "The unit-stride fault-only-first load instructions are used to vectorize loops with data-dependent exit "
        'conditions ("`while`" loops). These instructions execute as a regular load except that they will only '
        "take a trap caused by a synchronous exception on element 0.",
        SPACE + " Page B absent. No trap when the first faulting element is > 0: vle32ff.v (base VA_B - 8, vl=4), "
        "vle8ff.v (VA_B - 3, vl=8), vle16ff.v (VA_B - 2, vl=4), vle64ff.v (VA_B - 8, vl=2); element 0 is loaded. "
        "vle32ff.v with element 0 masked off and element 1 the first on page B: no trap, vl becomes 1, element 0 "
        "undisturbed. A trap (13, stval 0 or VA_B) when element 0 faults: vle32ff.v and vle8ff.v at VA_B, with vl "
        "unchanged. No trap with vl=0 at VA_B (there is no element 0).",
    )

    def body(p: Pages) -> None:
        win = p.window_bytes()
        late = MUT == "ff_traps_late"
        for eew, off, n in ((32, -8, 4), (8, -3, 8), (16, -2, 4), (64, -8, 2)):
            t.vfill(8)
            t.vset(n, eew)
            p.addr("x6", off)
            k = -off * 8 // eew
            t.win(
                [f"vle{eew}ff.v v8, (x6)"],
                LOAD_PF if late else "ok",
                f"vle{eew}ff.v with element {k} first on an absent page",
                [0, p.va_b] if late else None,
            )
            t.emit("csrw vstart, x0")
            if not late:
                t.ck_elem(8, 0, eew, le(win[256 + off : 256 + off + eew // 8]), f"vle{eew}ff.v element 0")
        t.vfill(8)
        t.vmask(0b1110)
        t.vset(4, 32)
        p.addr("x6", -4)
        t.win(
            ["vle32ff.v v8, (x6), v0.t"],
            LOAD_PF if late else "ok",
            "vle32ff.v, element 0 masked off, element 1 faults",
            [0, p.va_b] if late else None,
        )
        t.emit("csrw vstart, x0")
        if not late:
            if MUT == "ff_vl_unchanged":
                t.ck_csr("vl", 4, "mutant: vl unchanged")
            else:
                lo, hi = ff_vl_bounds(1)
                ck_vl_range(t, lo, hi, "vle32ff.v masked")
            t.ck_elem(8, 0, 32, fe(32), "masked-off element 0 undisturbed")
        for eew in (32, 8):
            t.vfill(8)
            t.vset(4, eew)
            p.addr("x6", 0)
            trims = MUT == "ff_elem0_trims"
            t.win(
                [f"vle{eew}ff.v v8, (x6)"],
                "ok" if trims else LOAD_PF,
                f"vle{eew}ff.v with element 0 on an absent page",
                None if trims else [0, p.va_b],
            )
            t.ck_csr("vl", 0 if trims else 4, "vl is not modified")
            t.emit("csrw vstart, x0")
        t.vfill(8)
        t.vset(0, 32)
        p.addr("x6", 0)
        t.win(["vle32ff.v v8, (x6)"], "ok", "vle32ff.v with vl=0 at an absent page")
        t.ck_csr("vl", 0, "vl stays 0")

    both(t, lambda x: Pages(t, x, None).setup(body))
    return t


def t_ff_op() -> VTest:
    t = new("vector_ff_op", s=True)
    describe(
        t,
        "If element 0 raises an exception, vl is not modified, and the trap is taken. If an element > 0 raises an "
        "exception, the corresponding trap is not taken, and the vector length vl is reduced to the index of the "
        "element that would have raised an exception.",
        SPACE + " Page B absent.\n"
        "Element 0 faults: vle32ff.v at VA_B (vl=4) and vle16ff.v at VA_B (LMUL=2, vl=12) trap with cause 13, "
        "xepc at the load, stval 0 or VA_B, and vl and vtype unchanged.\n"
        "Element k > 0 faults: vle32ff.v from VA_B - 12 (vl=4, k=3), vle16ff.v from VA_B - 10 (LMUL=2, vl=12, "
        "k=5) and vle8ff.v from VA_B - 1 (vl=16, k=1): no trap, vtype unchanged, and vl reduced to k, or fewer as "
        "vector_ff_no_exception permits, but at least 1; elements below the new vl are loaded.",
        context="vector_ff_no_exception: implementations may process fewer elements than vl even without an "
        "exception, so a trimmed vl anywhere in [1, k] is legal.",
    )

    def body(p: Pages) -> None:
        win = p.window_bytes()
        trims = MUT == "ff_elem0_trims"
        for eew, lm, n, venc in ((32, "m1", 4, 0x10), (16, "m2", 12, 0x09)):
            t.vfill(8, 2)
            t.vset(n, eew, lm)
            p.addr("x6", 0)
            t.win(
                [f"vle{eew}ff.v v8, (x6)"],
                "ok" if trims else LOAD_PF,
                f"vle{eew}ff.v element 0 faults",
                None if trims else [0, p.va_b],
            )
            t.ck_csr("vl", 0 if trims else n, "vl unchanged")
            t.ck_csr("vtype", venc, "vtype unchanged")
            t.ck_csr("vstart", 0, "the trap is on element 0")
            t.emit("csrw vstart, x0")
        for eew, lm, n, k, venc in ((32, "m1", 4, 3, 0x10), (16, "m2", 12, 5, 0x09), (8, "m1", 16, 1, 0x00)):
            off = -k * eew // 8
            t.vfill(8, 2)
            t.vset(n, eew, lm)
            p.addr("x6", off)
            late = MUT == "ff_traps_late"
            t.win(
                [f"vle{eew}ff.v v8, (x6)"],
                LOAD_PF if late else "ok",
                f"vle{eew}ff.v element {k} faults",
                [0, p.va_b] if late else None,
            )
            t.emit("csrw vstart, x0")
            if late:
                continue
            t.ck_csr("vtype", venc, "vtype unchanged")
            if MUT == "ff_vl_unchanged":
                t.ck_csr("vl", n, "mutant: vl unchanged")
                continue
            lo, hi = ff_vl_bounds(k)
            ck_vl_range(t, lo, hi, f"vle{eew}ff.v")
            ck_elems_below_vl(t, 8, eew, elems(win, 256 + off, eew, k), f"vle{eew}ff.v")

    both(t, lambda x: Pages(t, x, None).setup(body))
    return t


def t_overwrite_past_trap() -> VTest:
    t = new("vector_ls_overwrite_past_trap", s=True)
    describe(
        t,
        "Load instructions may overwrite active destination vector register group elements past the element "
        "index at which the trap is reported.",
        SPACE + " Page B absent. Only active elements may be overwritten:\n"
        "- vle32.v, LMUL=2, vl=5, mu/tu, mask 0b11011 (element 2 inactive), base VA_B - 4: element 1 faults (13, "
        "vstart = 1). Element 0 is loaded; active elements 1, 3, 4 may hold anything; inactive element 2 and the "
        "tail elements 5-7 stay undisturbed.\n"
        "- vlse32.v, stride 2048, vl=3, mask 0b101, base VA_B - 0x100: element 1 (inactive) and element 2 "
        "(active, faulting) are in page B; the trap has vstart = 2, stval 0 or VA_B + 0xf00; element 0 is loaded, "
        "inactive element 1 and tail element 3 stay undisturbed.",
        context=PRECISE,
    )

    def body(p: Pages) -> None:
        win = p.window_bytes()
        t.vfill(8, 2)
        t.vmask(0b11011)
        t.vset(5, 32, "m2")
        p.addr("x6", -4)
        t.win(["vle32.v v8, (x6), v0.t"], LOAD_PF, "vle32.v masked, element 1 faults", [0, p.va_b])
        t.ck_csr("vstart", 2 if MUT == "vstart_plus1" else 1, "vstart = 1")
        t.emit("csrw vstart, x0")
        exp = [le(win[252:256]), None, fe(32), None, None, fe(32), fe(32), fe(32)]
        t.ck_reg(8, 32, exp, "element 0 loaded; inactive element 2 and tail 5-7 undisturbed")
        t.vfill(8, 2)
        t.vmask(0b0101)
        t.vset(3, 32)
        p.addr("x6", -0x100)
        t.li("x1", 0x800)
        t.win(["vlse32.v v8, (x6), x1, v0.t"], LOAD_PF, "vlse32.v stride 2048, element 2 faults", [0, p.va(0xF00)])
        t.ck_csr("vstart", 3 if MUT == "vstart_plus1" else 2, "vstart = 2")
        t.emit("csrw vstart, x0")
        t.ck_reg(8, 32, [le(win[0:4]), fe(32), None, fe(32)], "element 0 loaded; inactive 1 and tail 3 undisturbed")

    both(t, lambda x: Pages(t, x, None).setup(body))
    return t


def t_ff_past_trap() -> VTest:
    t = new("vector_ff_past_trap", s=True)
    describe(
        t,
        "Similarly, fault-only-first load instructions may update active destination elements past the element "
        "that causes trimming of the vector length (but not past the original vector length). The values of these "
        "spurious updates do not have to correspond to the values in memory at the addressed memory locations. "
        "Non-idempotent memory locations can only be accessed when it is known the corresponding element load "
        "operation will not be restarted due to a trap or vector-length trimming.",
        SPACE + " Page B absent.\n"
        "- vle32ff.v, LMUL=2, original vl=5, mu/tu, mask 0b11011 (element 2 inactive), base VA_B - 12 (element 3 "
        "would fault): no trap; 1 <= vl <= 3; element 0 loaded, element 1 loaded if below the new vl; inactive "
        "element 2 undisturbed; active elements 3 and 4 (past the trim point, below the original vl) may hold "
        "anything; elements 5-7, past the original vl, stay undisturbed.\n"
        "- vlseg2e32ff.v, vl=3, base VA_B - 16 (segment 2 would fault): 1 <= vl <= 2, segment 0 loaded, element 3 "
        "of each field (past the original vl) undisturbed.",
        context="The non-idempotent clause needs an I/O region with read side effects; not tested.",
    )

    def body(p: Pages) -> None:
        win = p.window_bytes()
        tail = 0xFFFFFFFF if MUT == "ff_tail_clobbered" else fe(32)
        t.vfill(8, 4)
        t.vmask(0b11011)
        t.vset(5, 32, "m2")
        p.addr("x6", -12)
        t.win(["vle32ff.v v8, (x6), v0.t"], "ok", "vle32ff.v masked, element 3 would fault")
        ck_vl_range(t, 1, 3, "vle32ff.v")
        e = elems(win, 244, 32, 2)
        t.ck_elem(8, 0, 32, e[0], "element 0 loaded")
        ck_elems_below_vl(t, 8, 32, e, "vle32ff.v", start=1)
        t.ck_reg(
            8,
            32,
            [None, None, fe(32), None, None, tail, tail, tail],
            "inactive element 2 and elements past the original vl undisturbed",
        )
        t.vfill(8, 4)
        t.vset(3, 32)
        p.addr("x6", -16)
        t.win(["vlseg2e32ff.v v8, (x6)"], "ok", "vlseg2e32ff.v, segment 2 would fault")
        ck_vl_range(t, 1, 2, "vlseg2e32ff.v")
        t.ck_reg(8, 32, [le(win[240:244]), None, None, tail], "field 0: element 3 (past the original vl) undisturbed")
        t.ck_reg(9, 32, [le(win[244:248]), None, None, tail], "field 1: element 3 undisturbed")

    both(t, lambda x: Pages(t, x, None).setup(body))
    return t


def t_seg_ff_op() -> VTest:
    t = new("vector_ls_seg_ff_unit_stride_op", s=True)
    describe(
        t,
        "For fault-only-first segment loads, if an exception is detected partway through accessing the zeroth "
        "segment, the trap is taken. If an exception is detected partway through accessing a subsequent segment, "
        "vl is reduced to the index of that segment.",
        SPACE + " Page B absent. vlseg2e32ff.v (vl=4): from VA_B - 4 segment 0 straddles the page (field 0 valid, "
        "field 1 faults): trap 13 with stval 0 or VA_B and vl unchanged. From VA_B - 12 segment 1 straddles: no "
        "trap, vl = 1 (the segment index; at least 1). From VA_B - 20 segment 2 straddles: no trap, 1 <= vl <= 2. "
        "vlseg3e16ff.v (vl=4) from VA_B - 8: segment 1 (VA_B - 2 .. VA_B + 3) straddles, vl = 1. Segment 0's fields "
        "are loaded whenever no trap is taken.",
        context="vector_ff_no_exception: vl may be trimmed further, but not to 0.",
    )

    def body(p: Pages) -> None:
        win = p.window_bytes()
        trims = MUT == "ff_elem0_trims"
        t.vfill(8, 3)
        t.vset(4, 32)
        p.addr("x6", -4)
        t.win(
            ["vlseg2e32ff.v v8, (x6)"],
            "ok" if trims else LOAD_PF,
            "vlseg2e32ff.v, segment 0 straddles into an absent page",
            None if trims else [0, p.va_b],
        )
        t.ck_csr("vl", 0 if trims else 4, "vl unchanged")
        t.emit("csrw vstart, x0")
        for off, k, nf, eew in ((-12, 1, 2, 32), (-20, 2, 2, 32), (-8, 1, 3, 16)):
            t.vfill(8, 3)
            t.vset(4, eew)
            p.addr("x6", off)
            ins = f"vlseg{nf}e{eew}ff.v"
            late = MUT == "ff_traps_late"
            t.win(
                [f"{ins} v8, (x6)"],
                LOAD_PF if late else "ok",
                f"{ins}, segment {k} straddles",
                [0, p.va_b] if late else None,
            )
            t.emit("csrw vstart, x0")
            if late:
                continue
            if MUT == "ff_vl_unchanged":
                t.ck_csr("vl", 4, "mutant: vl unchanged")
                continue
            lo, hi = ff_vl_bounds(k)
            ck_vl_range(t, lo, hi, ins)
            for f in range(nf):
                a = 256 + off + f * eew // 8
                t.ck_elem(8 + f, 0, eew, le(win[a : a + eew // 8]), f"{ins}: segment 0 field {f}")

    both(t, lambda x: Pages(t, x, None).setup(body))
    return t


def t_seg_ff_overload() -> VTest:
    t = new("vector_ls_seg_ff_overload", s=True)
    describe(
        t,
        "These instructions may overwrite destination vector register group elements past the point at which a "
        "trap is reported or past the point at which vector length is trimmed.",
        SPACE + " Page B absent; base VA_B - 8, SEW=16, LMUL=1, vl=5, mu/tu, mask 0b10111 (segment 3 inactive); "
        "segment 2 is the first in page B. What stays constrained: vlseg2e16ff.v: no trap, 1 <= vl <= 2, segment 0 "
        "loaded, inactive segment 3 and tail elements 5-7 of both fields undisturbed. vlseg2e16.v (not ff): trap 13 "
        "with vstart = 2, segments 0-1 loaded, inactive segment 3 and tail elements 5-7 undisturbed.",
    )

    def body(p: Pages) -> None:
        win = p.window_bytes()
        tail = 0xFFFF if MUT == "ff_tail_clobbered" else fe(16)
        for ff in (True, False):
            t.vfill(8, 3)
            t.vmask(0b10111)
            t.vset(5, 16)
            p.addr("x6", -8)
            ins = "vlseg2e16ff.v" if ff else "vlseg2e16.v"
            t.win(
                [f"{ins} v8, (x6), v0.t"],
                "ok" if ff else LOAD_PF,
                f"{ins}, segment 2 on an absent page",
                None if ff else [0, p.va_b],
            )
            if ff:
                ck_vl_range(t, 1, 2, ins)
            else:
                t.ck_csr("vstart", 3 if MUT == "vstart_plus1" else 2, "vstart = 2")
                t.emit("csrw vstart, x0")
            for f in range(2):
                seg0 = le(win[248 + 2 * f : 250 + 2 * f])
                seg1 = le(win[252 + 2 * f : 254 + 2 * f])
                exp = [seg0, None if ff else seg1, None, fe(16), None, tail if ff else fe(16), fe(16), fe(16)]
                t.ck_reg(8 + f, 16, exp, f"{ins}: field {f}")

    both(t, lambda x: Pages(t, x, None).setup(body))
    return t


def t_seg_vstart_dep() -> VTest:
    t = new("vector_ls_seg_vstart_dep", s=True)
    describe(
        t,
        "The vstart value is in units of whole segments.",
        SPACE + " vlseg2e32.v (vl=4) from VA_B - 12 with B absent: segment 1 straddles the page, so the trap (13) "
        "has vstart = 1 (the segment, not field index 3) and segment 0's two fields are loaded. With B mapped, "
        "segment 0 overwritten in memory and vstart = 1 written back, the re-executed load keeps segment 0's old "
        "fields and loads segments 1-3. vssseg3e16.v (stride 4096, vl=2) from VA_B - 8 with B read-only: segment 1 "
        "is in B, the trap (15) has vstart = 1 and segment 0 is stored; resumed with vstart = 1 after B is made "
        "writable, segment 0's memory (overwritten with a marker) is not stored again and segment 1 is.",
        context=PRECISE + " " + PRESTART,
    )

    def body(p: Pages) -> None:
        win = p.window_bytes()
        vs = 3 if MUT == "seg_vstart_fields" else (2 if MUT == "vstart_plus1" else 1)
        t.vfill(8, 2)
        t.vset(4, 32)
        p.addr("x6", -12)
        t.win(["vlseg2e32.v v8, (x6)"], LOAD_PF, "vlseg2e32.v, segment 1 straddles", [0, p.va_b])
        t.ck_csr("vstart", vs, "vstart counts segments")
        t.emit("csrw vstart, x0")
        t.ck_elem(8, 0, 32, le(win[244:248]), "segment 0 field 0 loaded")
        t.ck_elem(9, 0, 32, le(win[248:252]), "segment 0 field 1 loaded")
        p.set_b(LEAF)
        marker(t, p.a, [0xFF4, 0xFF8])
        p.addr("x6", -12)
        t.vset(4, 32)
        set_vstart(t, 1)
        t.mark("resume")
        t.emit("vlseg2e32.v v8, (x6)")
        t.ck_reg(8, 32, [le(win[244 + 8 * i : 248 + 8 * i]) for i in range(4)], "resumed vlseg2e32.v field 0")
        t.ck_reg(9, 32, [le(win[248 + 8 * i : 252 + 8 * i]) for i in range(4)], "resumed vlseg2e32.v field 1")
        p.set_b(RO)
        vals = [store_vals(16, 2, 281 + k) for k in range(3)]
        for k in range(3):
            t.vload(16 + k, 16, vals[k], f"f{k}{p.xlen}")
        p.addr("x6", -8)
        t.li("x1", 0x1000)
        t.vset(2, 16)
        t.win(["vssseg3e16.v v16, (x6), x1"], STORE_PF, "vssseg3e16.v, segment 1 in a read-only page", [0, p.va(0xFF8)])
        t.ck_csr("vstart", 3 if MUT == "seg_vstart_fields" else (2 if MUT == "vstart_plus1" else 1), "vstart = 1")
        t.emit("csrw vstart, x0")
        t.ck_mem(p.a, 0xFF8, [vals[0][0], vals[1][0], vals[2][0]], "segment 0 stored", unit=2)
        p.set_b(LEAF)
        marker(t, p.a, [0xFF8])
        p.addr("x6", -8)
        t.li("x1", 0x1000)
        t.vset(2, 16)
        set_vstart(t, 1)
        t.mark("store_resume")
        t.emit("vssseg3e16.v v16, (x6), x1")
        t.ck_mem(p.a, 0xFF8, [0x0BADF00D], "resumed: segment 0 not stored again")
        t.ck_mem(p.b, 0xFF8, [vals[0][1], vals[1][1], vals[2][1]], "resumed: segment 1 stored", unit=2)

    both(t, lambda x: Pages(t, x, None).setup(body))
    return t


def t_seg_partial_access() -> VTest:
    t = new("vector_ls_seg_partial_access", s=True)
    describe(
        t,
        "If a trap occurs during access to a segment, it is implementation-defined whether a subset of the "
        "faulting segment's accesses are performed before the trap is taken.",
        SPACE + " vsseg2e32.v (vl=3) from VA_B - 12 with B read-only: segment 1 straddles the page (field 0 at "
        "VA_B - 4 in A, field 1 at VA_B in B). The trap (15) has vstart = 1; segment 0 is stored; segment 1's "
        "field 0 is either still the old memory word or the new value (no other value), and page B is unchanged. "
        "After B is made writable and vstart = 1 written back, the re-executed store writes segments 1 and 2 "
        "completely. vssseg2e16.v (stride 4096, vl=2) from VA_B - 2 (segment 0 straddles: field 0 in A, field 1 in "
        "B): trap with vstart = 0, field 0 old or new.",
        context=PRECISE,
    )

    def body(p: Pages) -> None:
        f0 = store_vals(32, 3, 291)
        f1 = store_vals(32, 3, 292)
        t.vload(16, 32, f0, f"f0{p.xlen}")
        t.vload(17, 32, f1, f"f1{p.xlen}")
        p.addr("x6", -12)
        t.vset(3, 32)
        t.win(
            ["vsseg2e32.v v16, (x6)"], STORE_PF, "vsseg2e32.v, segment 1 straddles into a read-only page", [0, p.va_b]
        )
        t.ck_csr("vstart", 3 if MUT == "seg_vstart_fields" else 1, "vstart = 1")
        t.emit("csrw vstart, x0")
        old = le(p.a_data[0xFC:0x100])
        legal = [0] if MUT == "seg_partial_garbage" else [old, f0[1]]
        t.ck_mem(p.a, 0xFF4, [f0[0], f1[0], legal], "segment 0 stored; segment 1 field 0 old or new")
        t.ck_mem(p.b, 0, words(p.b_data, 0, 8), "page B unchanged")
        p.set_b(LEAF)
        p.addr("x6", -12)
        t.vset(3, 32)
        set_vstart(t, 1)
        t.mark("resume")
        t.emit("vsseg2e32.v v16, (x6)")
        t.ck_csr("vstart", 0, "after the resumed vsseg2e32.v")
        t.ck_mem(p.a, 0xFFC, [f0[1]], "resumed: segment 1 field 0")
        t.ck_mem(p.b, 0, [f1[1], f0[2], f1[2]], "resumed: segment 1 field 1 and segment 2")
        p.set_b(RO)
        h0 = store_vals(16, 2, 293)
        h1 = store_vals(16, 2, 294)
        t.vload(18, 16, h0, f"h0{p.xlen}")
        t.vload(19, 16, h1, f"h1{p.xlen}")
        p.addr("x6", -2)
        t.li("x1", 0x1000)
        t.vset(2, 16)
        t.win(["vssseg2e16.v v18, (x6), x1"], STORE_PF, "vssseg2e16.v, segment 0 straddles", [0, p.va_b])
        t.ck_csr("vstart", 0, "vstart = 0")
        t.emit("csrw vstart, x0")
        oldh = f0[1] >> 16  # the resumed vsseg2e32.v left segment 1 field 0 at VA_B - 4
        t.ck_mem(p.a, 0xFFE, [[0] if MUT == "seg_partial_garbage" else [oldh, h0[0]]], "field 0 old or new", unit=2)

    both(t, lambda x: Pages(t, x, RO).setup(body))
    return t


def t_seg_wholereg_eew() -> VTest:
    t = new("vector_ls_seg_wholereg_eew", s=True)
    describe(
        t,
        "The load instructions have the element width encoded in the `mew` and `width` fields following the "
        "pattern of regular unit-stride loads. EEW is computed as EEW=min(VLEN*NFIELDS, EEW_encoded).",
        SPACE + " VLEN >= 128 > 64, so EEW is the encoded EEW, and it sets the element granularity of vstart. "
        "vl1re8.v, vl1re16.v, vl1re32.v and vl1re64.v from VA_B - 8 with B absent each take a load page fault "
        "(13, stval 0 or VA_B) with vstart = 8, 4, 2 and 1 (the element holding byte 8), and the 8 bytes before "
        "the page boundary loaded. Resuming vl1re16.v with vstart = 4 after B is mapped (and the first 8 bytes "
        "overwritten in memory) keeps the bytes loaded before the trap and loads from byte 8 on.",
        context=PRECISE,
    )

    def body(p: Pages) -> None:
        win = p.window_bytes()
        for eew in (8, 16, 32, 64):
            vs = 8 // (eew // 8)
            if MUT == "wholereg_vstart_bytes":
                vs = 8
            if MUT == "vstart_plus1":
                vs += 1
            t.vfill(8)
            p.addr("x6", -8)
            t.win([f"vl1re{eew}.v v8, (x6)"], LOAD_PF, f"vl1re{eew}.v, byte 8 on an absent page", [0, p.va_b])
            t.ck_csr("vstart", vs, f"vl1re{eew}.v: vstart in EEW={eew} elements")
            t.emit("csrw vstart, x0")
            t.ck_reg(8, 32, words(win, 248, 256), f"vl1re{eew}.v: bytes before vstart loaded")
        p.set_b(LEAF)
        marker(t, p.a, [0xFF8, 0xFFC])
        p.addr("x6", -8)
        set_vstart(t, 4)
        t.mark("resume")
        t.emit("vl1re16.v v8, (x6)")
        t.ck_csr("vstart", 0, "after the resumed vl1re16.v")
        t.ck_reg(8, 32, words(win, 248, 264), "resumed vl1re16.v: prestart bytes kept, the rest loaded")

    both(t, lambda x: Pages(t, x, None).setup(body))
    return t


def t_seg_wholereg_evl() -> VTest:
    t = new("vector_ls_seg_wholereg_evl", s=True)
    describe(
        t,
        "The instructions operate with an effective vector length, `evl`=NFIELDS*VLEN/EEW, regardless of current "
        "settings in vtype and vl. The usual property that no elements are written if vstart {ge} vl does not "
        "apply to these instructions. Similarly, the property that the instructions are reserved if vstart "
        "exceeds the largest element index for the current vtype setting does not apply. Instead, the "
        "instructions are reserved if vstart {ge} `evl`.",
        SPACE + "\n"
        "- vl=0 (SEW=32): vl1re32.v from a data buffer loads the whole register (first 16 bytes checked); vs1r.v stores "
        "it. With vtype.vill=1 (vsetvl with a reserved SEW), vl1re32.v and vs1r.v still execute.\n"
        "- vl=0 (SEW=32): vl1re32.v from "
        "VA_B - 8 with B absent faults at element 2: vstart = 2 >= vl. With B mapped, the first 8 bytes overwritten "
        "in memory and vstart = 2 written back, the re-executed vl1re32.v (vl still 0) keeps the prestart bytes "
        "and loads elements 2 onward.\n"
        "- vs1r.v (EEW=8) from VA_B - 8 with B read-only and vl=0: trap 15 with vstart = 8; resumed with vstart = 8 "
        "after B is made writable, bytes 8 onward are stored and the first 8 (overwritten with markers) are not.",
        context=PRECISE,
    )

    src = pat(37, 4096 + 64)
    sb = t.buf("src", src, 12)
    db = t.buf("dst", bytes([0x5C]) * (4096 + 64), 12)

    def body(p: Pages) -> None:
        win = p.window_bytes()
        wl = MUT == "wholereg_vl"
        vi = MUT == "wholereg_vill_illegal"
        t.vfill(8)
        t.vset(0, 32)
        t.la("x6", sb)
        t.mark("vl1re32_vl0")
        t.emit("vl1re32.v v8, (x6)")
        t.ck_reg(8, 32, [fe(32)] * 4 if wl else words(src, 0, 16), "vl1re32.v with vl=0 loads the whole register")
        t.comment("vtype.vill = 1: vsetvl with SEW=128 (reserved)")
        t.emit("li x7, 0x20")
        t.emit("vsetvl x8, x0, x7")
        t.ck_csr("vl", 0, "vill: vl = 0")
        t.vfill(9)
        t.emit("li x7, 0x20")
        t.emit("vsetvl x8, x0, x7")
        t.la("x6", f"{sb}+0x40")
        t.win(["vl1re32.v v9, (x6)"], ILLEGAL if vi else "ok", "vl1re32.v with vtype.vill=1")
        t.emit("li x7, 0x20")
        t.emit("vsetvl x8, x0, x7")
        t.la("x6", db)
        t.win(["vs1r.v v9, (x6)"], ILLEGAL if vi else "ok", "vs1r.v with vtype.vill=1")
        if not vi:
            t.ck_mem(db, 0, words(src, 0x40, 0x50), "vs1r.v with vill stored the register vl1re32.v loaded")
        # vstart >= vl generated by a fault, then accepted
        t.vfill(8)
        t.vset(0, 32)
        p.addr("x6", -8)
        t.win(["vl1re32.v v8, (x6)"], LOAD_PF, "vl1re32.v with vl=0, element 2 on an absent page", [0, p.va_b])
        t.ck_csr("vstart", 3 if MUT == "vstart_plus1" else 2, "vstart = 2 (>= vl)")
        t.emit("csrw vstart, x0")
        p.set_b(LEAF)
        marker(t, p.a, [0xFF8, 0xFFC])
        p.addr("x6", -8)
        t.vset(0, 32)
        set_vstart(t, 2)
        t.mark("resume")
        t.emit("vl1re32.v v8, (x6)")
        t.ck_csr("vstart", 0, "after the resumed vl1re32.v")
        exp = [*words(win, 248, 256), fe(32), fe(32)] if wl else words(win, 248, 264)
        t.ck_reg(8, 32, exp, "resumed vl1re32.v with vstart=2 >= vl=0: prestart kept, elements 2.. loaded")
        p.set_b(RO)
        t.vset(0, 32)
        p.addr("x6", -8)
        t.win(["vs1r.v v8, (x6)"], STORE_PF, "vs1r.v with vl=0, byte 8 on a read-only page", [0, p.va_b])
        t.ck_csr("vstart", 9 if MUT == "vstart_plus1" else 8, "vs1r.v: vstart = 8 (EEW=8)")
        t.emit("csrw vstart, x0")
        p.set_b(LEAF)
        marker(t, p.a, [0xFF8, 0xFFC], 0x600DF00D)
        marker(t, p.b, [0, 4, 8])
        p.addr("x6", -8)
        t.vset(0, 32)
        set_vstart(t, 8)
        t.mark("store_resume")
        t.emit("vs1r.v v8, (x6)")
        t.ck_mem(p.a, 0xFF8, [0x600DF00D, 0x600DF00D], "vs1r.v resumed: prestart bytes not stored")
        t.ck_mem(p.b, 0, words(win, 256, 264), "vs1r.v resumed: bytes 8.. stored (over markers)")
        t.ck_csr("vstart", 0, "after the resumed vs1r.v")

    both(t, lambda x: Pages(t, x, None).setup(body))
    return t


# ================================================================ driver
def gen() -> list[VTest]:
    makers = [
        t_load_store_semantics,
        t_unit_stride_op,
        t_strided_eew,
        t_indexed_eew,
        t_indexed_op,
        t_bytewise,
        t_xlen_dep,
        t_indexed_eew_emul,
        t_eew_emul,
        t_ins_req,
        t_base_stride_regtype,
        t_base,
        t_constant_stride_op,
        t_neg_zero_stride,
        t_constant_stride_x0,
        t_constant_stride_unordered,
        t_unit_stride_mask,
        t_wholels_nf_op,
        t_seg_wholereg_op,
        t_seg_wholereg_op_cont,
        t_wholereg_misaligned,
        t_nf_op,
        t_nfields,
        t_nfields_op,
        t_seg_op,
        t_seg_unit_stride_op,
        t_seg_vd_vs3,
        t_seg_constant_stride_op,
        t_seg_constant_stride_unordered,
        t_seg_indexed_op,
        t_seg_indexed_eew_emul,
        t_seg_indexed_emul_nfields_val,
        t_program_order,
        t_stride_ordered_op,
        t_stride_unordered_op,
        t_indexed_ordered_ordered,
        t_indexed_ordered_rvwmo,
        t_masked_inactive_behavior,
        t_misaligned_exception,
        t_ff_no_exception,
        t_ls_vstart,
        t_unordered_precise,
        t_masked_memory_access,
        t_ff_trigger,
        t_ff_op,
        t_overwrite_past_trap,
        t_ff_past_trap,
        t_seg_ff_op,
        t_seg_ff_overload,
        t_seg_vstart_dep,
        t_seg_partial_access,
        t_seg_wholereg_eew,
        t_seg_wholereg_evl,
    ]
    tests = [m() for m in makers]
    rules = [t.suite + "/" + t.rule + t.suffix for t in tests]
    dup = {r for r in rules if rules.count(r) > 1}
    assert not dup, f"duplicate rules: {dup}"
    return tests


def main() -> None:
    only = set(sys.argv[1:])
    for t in gen():
        if only and t.rule not in only:
            continue
        p = t.write()
        print(f"{p.relative_to(p.parents[2])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
