#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate the supervisor virtual-memory rule-derived suites: tests_ai/Sv (satp, Sv32/39/48/57, PTE format,
translation, SUM/MXR, SFENCE.VMA), tests_ai/Svade, Svadu, Svnapot, Svpbmt and Svinval.

Rules are the norm: tags in src/priv/supervisor.adoc (virtual-memory sections), svadu.adoc, svnapot.adoc,
svpbmt.adoc and svinval.adoc, plus the menvcfg.ADUE/PBMTE rules in machine.adoc that define Svadu/Svpbmt
behavior. Tests boot to S-mode and build page tables at run time (svlib.py). Scheme-independent rules use Sv39
(RV64) or Sv32 (RV32), probed at run time; scheme-specific rules require the scheme's extension.

Usage: gen_Sv.py [rule ...]   (default: every rule)
"""

from __future__ import annotations

import os
import sys
import zlib
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import POOL_TRAP
from svlib import (
    ADUE_BIT,
    AF,
    BASE,
    EXEC_OFF,
    EXT,
    GEO,
    ILLEGAL,
    ISSUE,
    LEAF,
    LOAD_PF,
    MAC,
    MARCH,
    MODE,
    MXR,
    N_BIT,
    PBMT_IO,
    PBMT_NC,
    PBMT_RSV,
    PBMTE_BIT,
    PF,
    RWX,
    SFENCE,
    SFENCE_INVAL_IR,
    SFENCE_W_INVAL,
    STORE_AF,
    STORE_PF,
    SUM,
    SUP,
    ULEAF,
    VA_T,
    VABITS,
    VIRTUAL,
    XP,
    A,
    D,
    G,
    R,
    SvPT,
    SvTest,
    U,
    V,
    W,
    amoadd_w,
    both,
    canon,
    cbo,
    guard,
    hinval_gvma,
    hinval_vvma,
    lr_w,
    lsig,
    menvcfg_bit,
    menvcfg_get,
    probe,
    register_alias,
    satp_off,
    sc_w,
    sfence_vma,
    sinval_vma,
    sstatus_bits,
    unregister_alias,
    win,
    word,
)

if TYPE_CHECKING:
    from collections.abc import Callable

SUITE = "Sv"
MUT = os.environ.get("AI_MUTANT", "")  # mutate.py: model a plausible bug in the expectations

MUTANTS = {
    "adue0_updates": "with ADUE=0 the hart still updates A/D (no Svade fault)",
    "adue_faults": "with ADUE=1 an access to an A=0 page still faults",
    "adue_fence_ignored": "a change of menvcfg.ADUE is not seen after SFENCE.VMA x0, x0",
    "adue_store_faults": "with ADUE=1, stores to D=0 pages fault (only A is updated by hardware)",
    "adue_ro0": "menvcfg.ADUE is read-only 0 with Svadu",
    "asid_fence_ignored": "SFENCE.VMA x0, rs2 does not invalidate the ASID's entries",
    "asid_none": "no ASID bits are implemented (the all-ones probe reads 0)",
    "asid_ignored": "translation caches ignore the ASID (ASID 2 uses ASID 1's translation)",
    "asid_write_ignored": "writes of satp.ASID are ignored (it reads 0)",
    "asid_needs_fence": "a satp.ASID change takes effect only after a fence",
    "d_set_on_fault": "a faulting store sets D",
    "fence_current_asid_only": "SFENCE.VMA x0, x0 invalidates only the current ASID",
    "fence_leaf_only": "SFENCE.VMA x0, x0 does not order non-leaf PTE changes",
    "fence_noop": "SFENCE.VMA x0, x0 does not invalidate",
    "high_ppn_page_fault": "PPN bits above 32-bit physical addresses are treated as reserved (page fault)",
    "hinval_illegal_in_v": "HINVAL.* in VS/VU raise illegal instead of virtual instruction",
    "implicit_access_fault": "an invalid pointer PTE is followed (access fault instead of page fault)",
    "invalid_kept": "a fenced V=0 PTE still translates",
    "invalid_va_traps": "SFENCE.VMA with a non-canonical rs1 raises a page fault",
    "ir_orders_last_only": "SFENCE.INVAL.IR orders only the last SINVAL.VMA",
    "load_sets_d": "a load sets D",
    "misaligned_superpage_ok": "a superpage with nonzero low PPN bits translates",
    "mode_needs_fence": "satp.MODE -> Bare takes effect only after a fence (VA still translated)",
    "napot_any_low": "N=1 with ppn[3:0]=0000 is treated as a 64 KiB page",
    "napot_fence_by_base": "SFENCE.VMA of page 5 does not remove a NAPOT entry created from page 0",
    "napot_no_subst": "the NAPOT PPN low bits are used as written (no vpn substitution)",
    "napot_ppn_used": "every page of a NAPOT range maps to page 8 (ppn[3:0] used)",
    "napot_range_128k": "a NAPOT range covers 128 KiB",
    "napot_rsv_ok": "reserved NAPOT encodings translate",
    "napot_superpage_ok": "N=1 is accepted in superpage leaves",
    "no_top_leaf": "a leaf in the root table faults",
    "nonleaf_adu_ignored": "D/A/U set in a pointer PTE are ignored",
    "offset_11bit": "only 11 page-offset bits are untranslated",
    "only_latest_two": "an unfenced read returns only the last two translations",
    "pbmt3_ok": "PBMT=3 translates",
    "pbmt_nonleaf_ok": "PBMT in a pointer PTE is ignored",
    "pbmte_fence_ignored": "a change of PBMTE is not seen after SFENCE.VMA x0, x0",
    "pbmte_ignored": "PBMT is honored with menvcfg.PBMTE=0",
    "pte_index_8bit": "only 8 bits of VPN index the leaf table (entry 256 aliases 0)",
    "pte_low_word_only": "reserved bits in the upper PTE word are ignored",
    "reserved_mode_written": "a reserved satp.MODE value is written",
    "rs2_unmasked": "SFENCE.VMA compares rs2 unmasked with the ASID (the stale translation survives)",
    "rsv_bit58_ignored": "PTE bit 58 is ignored",
    "rsw_faults": "RSW bits cause a page fault",
    "satp_active_m": "satp translates M-mode loads",
    "sfence_illegal": "SFENCE.VMA raises illegal instruction although paging is supported",
    "sinval_noop": "the SINVAL.VMA sequence does not invalidate",
    "sinval_skips_global": "SINVAL.VMA x0, x0 skips global entries",
    "superpage_double_size": "a superpage maps twice its size",
    "sv32_misaligned_ok": "a misaligned Sv32 megapage translates",
    "sv39_wide_va": "Sv39 accepts VAs with bit 38 set and bits 63:39 clear",
    "sv48_as_sv39": "MODE 9 walks the table as Sv39",
    "svade_sets_a": "with Svade the hart sets A instead of faulting",
    "svade_sets_d": "with Svade the hart sets D on a store instead of faulting",
    "tvm_ignored": "SINVAL.VMA ignores mstatus.TVM",
    "u_inval_ok": "Svinval fences execute in U-mode",
    "v_ignored_at_root": "V=0 in the root PTE is ignored",
    "va_fence_ignored": "SFENCE.VMA with rs1 = VA does not invalidate that VA",
    "va_fence_skips_global": "SFENCE.VMA VA, x0 skips global entries",
    "va_space_short": "the lowest negative page aliases the top page",
    "va_upper_ignored": "VA bits above the scheme's width are ignored",
    "vpn_top_bit_ignored": "the top VPN bit is ignored",
    "vtvm_ignored": "SINVAL.VMA in VS-mode ignores hstatus.VTVM",
    "w_inval_after_orders": "a PTE store after SFENCE.W.INVAL is never seen (old translation kept)",
    "winval_tvm_traps": "SFENCE.W.INVAL/INVAL.IR trap with mstatus.TVM=1",
    "winval_vu_illegal": "SFENCE.W.INVAL/INVAL.IR in VU-mode raise illegal instruction",
    "w_only_writable": "a W=1, R=0 (reserved) leaf is treated as a read-write page",
    "x_implies_r": "loads from execute-only pages succeed without MXR",
    "mxr_ignored": "sstatus.MXR does not make execute-only pages readable",
    "mxr_s_only": "MXR applies to S-mode loads only, not U-mode loads",
    "sum_ignored": "sstatus.SUM does not let S-mode access user pages",
    "sum_grants_exec": "with SUM=1, S-mode may execute from user pages",
    "sum_in_umode": "with SUM=1, U-mode may access supervisor pages",
    "s_user_ok": "S-mode may access user pages with SUM=0",
    "u_super_ok": "U-mode may load from supervisor pages",
    "fetch_needs_r": "instruction fetch also requires R=1",
    "store_fault_as_load": "store page faults are reported as load page faults (13)",
    "cbm_xonly_always_ok": "CBM instructions may always access execute-only pages",
    "sum_needs_fence": "a SUM/MXR change takes effect only after SFENCE.VMA (the stale permission is used)",
    "fetch_fault_as_access": "instruction page faults are reported as instruction access faults (1)",
}


def out(suite: str) -> str:
    """The directory a test is written to: its suite, or the mutant directory."""
    return suite if SUITE == "Sv" else SUITE


def new(suite: str, rule: str, required: list | None = None, **kw: object) -> SvTest:
    kw.setdefault("boot", "S")
    kw.setdefault("pool", POOL_TRAP)
    kw.setdefault("march", MARCH)
    return SvTest(out(suite), rule, required=required or ["I", "S"], **kw)


# ---------------------------------------------------------------- reference semantics (spec)
def allowed(pte: int, mode: str, kind: str, sum_: int, mxr: int, level0_pointer: bool = True) -> bool:
    """Does a 4 KiB-level PTE `pte` (A=D=1) permit `kind` (load/store/fetch/amo) from `mode`?
    supervisor.adoc: translation steps 3-8, pte_u_op, pte_u_no_s_exec, sstatus_sum, sstatus_mxr."""
    v, r, w, x, u = (pte & b != 0 for b in (V, R, W, XP, U))
    if not v:
        return False
    if not (r or w or x):  # a pointer at the last level (step 4: i < 0)
        return False
    if w and not r:  # reserved encoding (step 3)
        if MUT == "w_only_writable":
            r = True
        else:
            return False
    if mode == "U":
        if not u and not (MUT == "sum_in_umode" and sum_) and not (MUT == "u_super_ok" and kind == "load"):
            return False
    elif u:
        if kind == "fetch":
            if not (MUT == "sum_grants_exec" and sum_):
                return False
        elif not (sum_ and MUT != "sum_ignored") and MUT != "s_user_ok":
            return False
    if kind == "load":
        mx = mxr and MUT != "mxr_ignored" and not (MUT == "mxr_s_only" and mode == "U")
        return r or (x and (mx or MUT == "x_implies_r"))
    if kind in ("store", "amo"):
        return w and (kind == "store" or r)
    return x and (r or MUT != "fetch_needs_r")


def pf(kind: str) -> int:
    if MUT == "store_fault_as_load" and kind in ("store", "amo"):
        return 13
    if MUT == "fetch_fault_as_access" and kind == "fetch":
        return AF["fetch"]
    return PF[kind]


# ---------------------------------------------------------------- common structure
def with_vm(
    t: SvTest,
    xlen: int,
    inner: Callable[[SvPT], None],
    *,
    user: bool = False,
    scheme: str | None = None,
    guarded: bool = True,
    name: str | None = None,
) -> SvPT:
    """Build a table identity-mapping the image (and its user alias if `user`), then run inner(pt) with the
    table built but satp still Bare; inner maps its pages and calls pt.on(). satp is Bare again afterwards.
    With guarded, the whole thing runs only if satp accepts the scheme (probe)."""
    pt = SvPT(t, name or f"p{xlen}{scheme or ''}", scheme or BASE[xlen])
    pt.identity()
    if user:
        pt.user_alias()

    def run() -> None:
        if user:
            register_alias(t, pt)
        inner(pt)
        satp_off(t)
        if user:
            unregister_alias(t)

    if guarded:
        probe(t, pt)
        guard(t, "x1", run)
    else:
        run()
    return pt


class SState:
    """Tracks sstatus.SUM/MXR as emitted, to write only changes."""

    def __init__(self, t: SvTest) -> None:
        self.t, self.sum, self.mxr = t, 0, 0

    def set(self, sum_: int, mxr: int) -> None:
        if sum_ != self.sum:
            sstatus_bits(self.t, SUM, bool(sum_), "SUM")
            self.sum = sum_
        if mxr != self.mxr:
            sstatus_bits(self.t, MXR, bool(mxr), "MXR")
            self.mxr = mxr

    def clear(self) -> None:
        self.set(0, 0)


def access(
    t: SvTest,
    pt: SvPT | None,
    mode: str,
    kind: str,
    va: int,
    ok: bool | list,
    desc: str,
    page: str | None = None,
    off: int = 16,
    level: int = 0,
) -> str:
    """One access of `kind` to va from `mode`; ok: True (must succeed), False (page fault), or a list of
    legal outcomes. A load must read page's signature, a fetch must run page's stub (x7 = id), and a store must
    land at page+off (or leave it untouched when it faults). With level > 0, va is a superpage's base and the
    access goes to page's offset within the superpage (computed at run time; xtval is checked against it)."""
    exp = ok if isinstance(ok, list) else ("ok" if ok else pf(kind))
    certain = isinstance(ok, bool)
    val = 0
    if level:
        assert pt is not None and page is not None, "superpage accesses need the table and the target page"
        size = sp_size(pt.scheme, level)
        t.la("x6", page)
        t.emit(f"li x7, {hex(size - 1)}")
        t.emit("and x6, x6, x7")
        t.emit(f"li x7, {hex(va)}")
        t.emit("add x6, x6, x7  // the page's address inside the superpage")
    else:
        t.emit(f"li x6, {hex(va)}")
    t.emit("li x7, 0")
    epc: object = "insn"
    if kind == "load":
        lines, tval, toff = ["lw x7, 0(x6)"], [0, va], 0
    elif kind == "store":
        val = (zlib.crc32(f"{t.rule}{desc}{len(t.table)}".encode()) & 0x7FFFFFFF) | 1
        if page:
            t.la("x9", f"{page}+{off}")
            t.emit("sw x0, 0(x9)  // clear the target word")
        t.load("x8", val, "store value")
        lines, tval, toff = [f"sw x8, {off}(x6)"], [0, va + off], off
    elif kind == "fetch":
        lines, tval, toff = [f"jalr x1, {EXEC_OFF}(x6)"], [0, va + EXEC_OFF], EXEC_OFF
        epc = va + EXEC_OFF if not level else None
    else:
        raise ValueError(kind)
    if level:
        tval = None
    lab = win(t, pt, mode, lines, exp, desc, tval=tval if exp != "ok" else None, epc=epc)
    if level and exp != "ok" and certain:
        # xtval (and, for a fetch, xepc) is 0 / the run-time address
        t.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
        t.emit(f"addi x9, x6, {toff}")
        t.emit("xor x9, x9, x15")
        t.emit("seqz x9, x9")
        t.emit("seqz x15, x15")
        t.emit("or x15, x15, x9")
        t.check_bool("x15", lab, f"{desc}: xtval is 0 or the faulting address")
        if kind == "fetch":
            t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
            t.emit(f"addi x9, x6, {toff}")
            t.emit("xor x9, x9, x15")
            t.emit("seqz x15, x9")
            t.check_bool("x15", lab, f"{desc}: xepc is the fetch target")
    if page and certain:
        pid = t.page_id(page.removeprefix("ai_pg_"))
        if kind == "load" and ok:
            t.check("x7", lsig(pid), lab, f"{desc}: lw reads the mapped page")
        elif kind == "fetch" and ok:
            t.check("x7", pid, lab, f"{desc}: the fetch ran the mapped page's code")
        elif kind == "store":
            t.la("x9", f"{page}+{off}")
            t.emit("lw x7, 0(x9)")
            t.check(
                "x7",
                val if ok else 0,
                lab,
                f"{desc}: the store {'landed in' if ok else 'did not write'} the mapped page",
            )
    return lab


def rwx_name(p: int) -> str:
    return "".join(c if p & b else "-" for c, b in (("R", R), ("W", W), ("X", XP), ("U", U))) or "----"


# ---------------------------------------------------------------- permission sweeps
def perm_sweep(t: SvTest, kind: str, us: tuple = (0, U)) -> None:
    """Every R/W/X/U encoding x mode (S, U) x SUM x MXR for one access kind."""
    t.page("P")

    def body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = VA_T[xlen]
            pt.on()
            st = SState(t)
            for u in us:
                for rwx in range(8):
                    perms = V | A | D | (rwx << 1) | u
                    pt.leaf(va, t.page("P"), perms)
                    t.emit(SFENCE)
                    for mode in ("S", "U"):
                        for sum_ in (0, 1):
                            for mxr in (0, 1):
                                st.set(sum_, mxr)
                                ok = allowed(perms, mode, kind, sum_, mxr)
                                access(
                                    t,
                                    pt,
                                    mode,
                                    kind,
                                    va,
                                    ok,
                                    f"{kind} PTE {rwx_name(perms)} SUM={sum_} MXR={mxr}",
                                    page="ai_pg_P",
                                )
            st.clear()

        with_vm(t, xlen, inner, user=True)

    both(t, body)


def gen_perm() -> list[SvTest]:
    tests = []
    plan_common = (
        "The page is mapped at a constant VA by a 4 KiB leaf with A=D=1 and each of the 16 R/W/X/U encodings "
        "(R=W=X=0 is a pointer at the last level, which must fault; W=1 R=0 is reserved, so it must fault for "
        "every access). For each, the access runs from S-mode and from U-mode (code in the user alias), with "
        "every SUM x MXR combination. Expected: allowed iff the encoding is valid, the U bit matches the mode "
        "(S-mode may access U=1 pages only with SUM=1, and never fetch from them), and the type permission "
        "holds (loads: R, or X with MXR=1). A fault is a page fault with xepc at the access, xtval 0 or the "
        "address, and SPP recording the mode."
    )

    t = new("Sv", "load_page_fault_no_r")
    t.describe(
        source=SUP,
        rule_text="Attempting to execute a load or load-reserved instruction whose effective address lies within "
        "a page without read permissions raises a load page-fault exception.",
        context="Sv39 on RV64 and Sv32 on RV32, probed at run time (the rule is scheme-independent). <<pteperm>>: "
        "W=1 R=0 encodings are reserved (step 3 of the translation algorithm faults). MXR makes execute-only "
        "pages readable (sstatus_mxr).",
        plan="1. lw: "
        + plan_common.replace(", and never fetch from them", "")
        + " A successful lw reads the page's signature.\n"
        "2. With Zalrsc: lr.w from S-mode (U=0 page) and U-mode (U=1 page), MXR 0 and 1, over the 7 leaf R/W/X "
        "encodings: a load page fault (13) exactly when lw would fault.",
    )
    perm_sweep(t, "load", (0,))

    def lr_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = VA_T[xlen] + 0x1000
            pt.on()
            st = SState(t)
            for rwx in range(1, 8):
                for mode, u in (("S", 0), ("U", U)):
                    perms = V | A | D | (rwx << 1) | u
                    pt.leaf(va, t.page("P"), perms)
                    t.emit(SFENCE)
                    for mxr in (0, 1):
                        st.set(0, mxr)
                        ok = allowed(perms, mode, "load", 0, mxr)
                        t.emit(f"li x6, {hex(va)}")
                        t.emit("li x7, 0")
                        lab = win(
                            t,
                            pt,
                            mode,
                            [word(lr_w(7, 6), "lr.w x7, (x6)")],
                            "ok" if ok else pf("load"),
                            f"lr.w PTE {rwx_name(perms)} MXR={mxr}",
                            tval=None if ok else [0, va],
                        )
                        if ok:
                            t.check("x7", lsig(t.page_id("P")), lab, "lr.w reads the mapped page")
            st.clear()

        with t.only_if("defined(ZALRSC_SUPPORTED)"):
            with_vm(t, xlen, inner, user=True, name=f"lr{xlen}")

    both(t, lr_body)
    tests.append(t)

    t = new("Sv", "store_page_fault_no_w")
    t.describe(
        source=SUP,
        rule_text="Attempting to execute a store, store-conditional, AMO, or cache-block zero instruction whose "
        "effective address lies within a page without write permissions raises a store page-fault exception.",
        context="Sv39 on RV64 and Sv32 on RV32, probed at run time. MXR and SUM never grant write permission to a "
        "supervisor page from U-mode or to a non-writable page.",
        plan="1. sw: " + plan_common + " A successful store lands in the page; a faulting one leaves the "
        "target word unchanged.\n"
        "2. With Zalrsc: sc.w after an lr.w of the same physical word (through a readable alias) on the 7 leaf "
        "encodings, S-mode U=0 and U-mode U=1: store page fault (15) without W; with W the SC may succeed or "
        "fail.\n"
        "3. With Zaamo: amoadd.w on the same sweep: store page fault without W, success with R+W.\n"
        "4. With Zicboz (S-mode, menvcfg.CBZE=1 at boot): cbo.zero on the sweep: store page fault without W.",
    )
    perm_sweep(t, "store", (0,))
    store_extras(t)
    tests.append(t)

    t = new("Sv", "fetch_page_fault_no_x")
    t.describe(
        source=SUP,
        rule_text="Attempting to fetch an instruction from a page that does not have execute permissions raises a "
        "fetch page-fault exception.",
        context="Sv39 on RV64 and Sv32 on RV32, probed at run time. The fetch is a jalr x1 to the page's stub at "
        "offset 0x100 (addi x7, x0, id; jalr x0, 0(x1)); on a fault the handler resumes at x1.",
        plan="1. jalr to the page: "
        + plan_common.replace("the access", "the fetch")
        + " xepc and xtval (or 0) are the target address. MXR and SUM never grant execute permission.",
    )
    perm_sweep(t, "fetch", (0,))
    tests.append(t)
    for t0 in list(tests):
        tests.append(u1_twin(t0))
        t0.doc["plan"] = "This file: the U=0 encodings of item 1 (the U=1 ones are in the _U1 file).\n" + t0.doc["plan"]
    return tests


def u1_twin(t0: SvTest) -> SvTest:
    """The U=1 half of a permission sweep, in <rule>_U1.S (keeps each file under the size limit)."""
    kind = {"load_page_fault_no_r": "load", "store_page_fault_no_w": "store", "fetch_page_fault_no_x": "fetch"}[t0.rule]
    t = new("Sv", t0.rule, suffix="_U1")
    plan = t0.doc["plan"].split("\n")[0]
    t.describe(
        source=t0.doc["source"],
        rule_text=t0.doc["rule_text"],
        context=t0.doc["context"],
        plan="This file: the U=1 encodings of the sweep (the U=0 ones and the other instructions are in "
        f"{t0.rule}.S).\n" + plan,
    )
    perm_sweep(t, kind, (U,))
    return t


def store_extras(t: SvTest) -> None:
    """SC, AMO and CBO.ZERO sweeps of store_page_fault_no_w."""

    def sweep(xlen: int, kind: str, cond: str) -> None:
        def inner(pt: SvPT) -> None:
            va = VA_T[xlen] + 0x2000
            pt.on()
            modes = (("S", 0), ("U", U)) if kind != "cbo.zero" else (("S", 0),)
            page = "Z" if kind == "cbo.zero" else "P"
            for rwx in range(1, 8):
                for mode, u in modes:
                    perms = V | A | D | (rwx << 1) | u
                    pt.leaf(va, t.page(page), perms)
                    t.emit(SFENCE)
                    ok = allowed(perms, mode, "amo" if kind == "amo" else "store", 0, 0)
                    t.emit(f"li x6, {hex(va)}")
                    t.load("x8", 0x1234, "store value")
                    pre: list[str] = []
                    if kind == "sc":
                        # reserve the same physical word through a readable view (identity in S, user alias in U)
                        t.la("x9", t.page("P"))
                        if mode == "U":
                            t.emit(f"li x5, {hex(pt.delta)}")
                            t.emit("add x9, x9, x5")
                        pre = [word(lr_w(7, 9), "lr.w x7, (x9): reserve the physical word")]
                        line = word(sc_w(7, 6, 8), "sc.w x7, x8, (x6)")
                    elif kind == "amo":
                        line = word(amoadd_w(7, 6, 8), "amoadd.w x7, x8, (x6)")
                    else:
                        line = word(cbo("zero", 6), "cbo.zero (x6)")
                    win(
                        t,
                        pt,
                        mode,
                        [line],
                        "ok" if ok else pf("store"),
                        f"{kind} PTE {rwx_name(perms)}",
                        tval=None if ok else [0, va],
                        pre=pre,
                    )

        with t.only_if(cond):
            with_vm(t, xlen, inner, user=kind != "cbo.zero", name=f"{kind.replace('.', '')}{xlen}")

    t.page("Z")
    for kind, cond in (
        ("sc", "defined(ZALRSC_SUPPORTED)"),
        ("amo", "defined(ZAAMO_SUPPORTED)"),
        ("cbo.zero", "defined(ZICBOZ_SUPPORTED)"),
    ):
        both(t, lambda xlen, kind=kind, cond=cond: sweep(xlen, kind, cond))


def s_load(t: SvTest, va: int, pid: int, desc: str) -> str:
    """S-mode lw of va that must succeed (no trap window: a trap fails the test) and read page pid."""
    lab = t.label("ld")
    t.emit(f"li x6, {hex(va)}")
    t.emit(f"{lab}:", 0)
    t.emit("lw x7, 0(x6)")
    t.check("x7", lsig(pid), lab, desc)
    return lab


def s_load_any(t: SvTest, va: int, pids: list, desc: str) -> str:
    """S-mode lw of va that may read any of pids' pages, or page-fault when "fault" is in pids."""
    vals = [lsig(p) for p in pids if p != "fault"]
    exp = ["ok", LOAD_PF] if "fault" in pids else "ok"
    t.load("x7", vals[0], "preset: a fault leaves a legal value")
    t.emit(f"li x6, {hex(va)}")
    lab = win(t, None, "S", ["lw x7, 0(x6)"], exp, desc, tval=[0, va] if "fault" in pids else None)
    t.check("x7", vals if len(vals) > 1 else vals[0], lab, f"{desc}: the old or the new translation")
    return lab


def gen_perm2() -> list[SvTest]:
    tests = []

    # ---- cbm_page_fault
    t = new("Sv", "cbm_page_fault", ["I", "S", "Zicbom"])
    t.describe(
        source=SUP,
        rule_text="The permissions required for a cache-block management instruction are defined in <<cmo>>; when "
        "address translation does not permit any access, the instruction raises a store page-fault exception.",
        context="cmo.adoc (cbm_access, cbm_unperm_fault): a CBM instruction may access the block whenever a load or "
        "a store may; if only a fetch may, whether it may is UNSPECIFIED, and if it may not, translation permits "
        'some access, so the fault is a store access fault (7). Whether "does not permit any access" counts a '
        "fetch permission is not explicit (" + ISSUE + "3405 and #3407 settled only that CBM page faults are store "
        "page faults), and Sail raises a store page fault, so 15 is also accepted. menvcfg.CBCFE and CBIE are WARL "
        "(set at boot): they are read back through T-SBI, and cbo.clean/cbo.flush run only when CBCFE=1, cbo.inval "
        "only when CBIE != 00 (01 makes it a flush). xtval is 0 or rs1.",
        plan="S-mode cbo.clean, cbo.flush and cbo.inval on a page mapped as: invalid (V=0) -> store page fault; "
        "a U=1 RW page with SUM=0 -> store page fault, with SUM=1 -> no trap; U=0 read-only, read-write and "
        "read-execute pages -> no trap; execute-only with MXR=0 -> no trap, store access fault or store page fault; "
        "execute-only with "
        "MXR=1 (loads permitted) -> no trap; W-only (reserved) -> store page fault.",
    )
    t.page("C")

    def cbm_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = VA_T[xlen] + 0x3000
            pt.on()
            cases = [
                (A | D, 0, 0, False, "V=0"),
                (V | A | D | R | W | U, 0, 0, False, "U=1, SUM=0"),
                (V | A | D | R | W | U, 1, 0, True, "U=1, SUM=1"),
                (V | A | D | R, 0, 0, True, "read-only"),
                (V | A | D | R | W, 0, 0, True, "read-write"),
                (V | A | D | R | XP, 0, 0, True, "read-execute"),
                (V | A | D | XP, 0, 0, ["ok", STORE_PF, STORE_AF], "execute-only, MXR=0"),
                (V | A | D | XP, 0, 1, True, "execute-only, MXR=1"),
                (V | A | D | W, 0, 0, False, "W-only (reserved)"),
            ]

            def run(ops: tuple) -> None:
                st = SState(t)
                for perms, sum_, mxr, ok, note in cases:
                    if MUT == "cbm_xonly_always_ok" and note == "execute-only, MXR=0":
                        ok = True
                    pt.leaf(va, t.page("C"), perms)
                    t.emit(SFENCE)
                    st.set(sum_, mxr)
                    for op in ops:
                        t.emit(f"li x6, {hex(va)}")
                        exp = ok if isinstance(ok, list) else ("ok" if ok else pf("store"))
                        win(
                            t,
                            pt,
                            "S",
                            [word(cbo(op, 6), f"cbo.{op} (x6)")],
                            exp,
                            f"cbo.{op}, {note}",
                            tval=None if exp == "ok" else [0, va],
                        )
                st.clear()

            menvcfg_get(t, xlen, 6, "x1")
            guard(t, "x1", lambda: run(("clean", "flush")))
            t.tsbi_csr("READ", "MENVCFG")
            t.emit("andi x1, a0, 0x30  // CBIE")
            guard(t, "x1", lambda: run(("inval",)))

        with_vm(t, xlen, inner)

    both(t, cbm_body)
    tests.append(t)

    # ---- pte_u_op
    t = new("Sv", "pte_u_op")
    t.describe(
        source=SUP,
        rule_text="The U bit indicates whether the page is accessible to user mode. U-mode software may only access "
        "the page when U=1. If the SUM bit in the sstatus register is set, supervisor mode software may also "
        "access pages with U=1.",
        context="Sv39 (RV64) or Sv32 (RV32), probed. Leaves are RWX with A=D=1, at the 4 KiB level and as a "
        "superpage (2 MiB / 4 MiB), so a U check done only for one page size is caught.",
        plan="For a 4 KiB leaf and a superpage leaf, each with U=0 and U=1:\n"
        "1. U-mode load, store and fetch: allowed iff U=1 (page fault 13/15/12 otherwise), with SUM 0 and 1.\n"
        "2. S-mode load and store with SUM=1: allowed for U=1 and U=0. S-mode fetch from U=1 faults.",
    )
    t.page("P")

    def u_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            pt.on()
            st = SState(t)
            for level in (0, 1):
                va = VA_T[xlen] + 0x4000 if level == 0 else sp_va(BASE[xlen], 1)
                for u in (0, U):
                    perms = LEAF | u
                    pt.leaf(va, t.page("P"), perms, level=level)
                    t.emit(SFENCE)
                    pg = "ai_pg_P"
                    for sum_ in (0, 1):
                        st.set(sum_, 0)
                        for kind in ("load", "store", "fetch"):
                            access(
                                t,
                                pt,
                                "U",
                                kind,
                                va,
                                allowed(perms, "U", kind, sum_, 0),
                                f"{kind}, level {level}, U={int(bool(u))}, SUM={sum_}",
                                page=pg,
                                level=level,
                            )
                    st.set(1, 0)
                    for kind in ("load", "store", "fetch"):
                        access(
                            t,
                            pt,
                            "S",
                            kind,
                            va,
                            allowed(perms, "S", kind, 1, 0),
                            f"{kind}, level {level}, U={int(bool(u))}, SUM=1",
                            page=pg,
                            level=level,
                        )
            st.clear()

        with_vm(t, xlen, inner, user=True)

    both(t, u_body)
    tests.append(t)

    # ---- pte_u_no_s_exec
    t = new("Sv", "pte_u_no_s_exec")
    t.describe(
        source=SUP,
        rule_text="Irrespective of SUM, the supervisor may not execute code on pages with U=1.",
        context="Sv39 (RV64) or Sv32 (RV32), probed. The fetch is a jalr to the page's stub.",
        plan="S-mode fetch from a U=1 page (RX, X-only and RWX; 4 KiB and superpage leaves) with SUM=0 and SUM=1, "
        "and MXR=1: instruction page fault (12), xepc = xtval (or 0) = the target. The same pages with U=0 "
        "execute (x7 = page id).",
    )
    t.page("P")

    def nx_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            pt.on()
            st = SState(t)
            for level in (0, 1):
                va = VA_T[xlen] + 0x5000 if level == 0 else sp_va(BASE[xlen], 1)
                for rwx in (R | XP, XP, RWX):
                    for u in (U, 0):
                        perms = V | A | D | rwx | u
                        pt.leaf(va, t.page("P"), perms, level=level)
                        t.emit(SFENCE)
                        for sum_, mxr in ((0, 0), (1, 0), (1, 1)):
                            st.set(sum_, mxr)
                            access(
                                t,
                                pt,
                                "S",
                                "fetch",
                                va,
                                allowed(perms, "S", "fetch", sum_, mxr),
                                f"fetch, level {level}, PTE {rwx_name(perms)}, SUM={sum_} MXR={mxr}",
                                page="ai_pg_P",
                                level=level,
                            )
            st.clear()

        with_vm(t, xlen, inner)

    both(t, nx_body)
    tests.append(t)

    # ---- sstatus_sum
    t = new("Sv", "sstatus_sum")
    t.describe(
        source=SUP,
        rule_text="The SUM (permit Supervisor User Memory access) bit modifies the privilege with which S-mode loads "
        "and stores access virtual memory. When SUM=0, S-mode memory accesses to pages that are accessible by "
        "U-mode (U=1 in <<sv32pte>>) will fault. When SUM=1, these accesses are permitted. SUM has no effect when "
        "page-based virtual memory is not in effect, nor when executing in U-mode. Note that S-mode can never "
        "execute instructions from user pages, regardless of the state of SUM.",
        context="Sv39 (RV64) or Sv32 (RV32), probed. sstatus.SUM is writable when satp.MODE is not read-only 0.",
        plan="1. SUM reads back as written (0, 1).\n"
        "2. S-mode lw/sw to a U=1 RW page: page fault with SUM=0, success with SUM=1 (the load reads the page, "
        "the store lands); MXR=1 does not change this.\n"
        "3. S-mode fetch from a U=1 RWX page faults with SUM=1.\n"
        "4. U-mode with SUM=1: a U=0 page still faults for lw and sw; a U=1 page works with SUM=0.\n"
        "5. satp Bare, SUM=0: S-mode lw/sw of the page's physical address work (no effect without paging).",
    )
    t.page("P")

    def sum_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = VA_T[xlen] + 0x6000
            lab = t.label("sumrb")
            for v in (1, 0):
                sstatus_bits(t, SUM, bool(v), "SUM")
                t.emit(f"{lab}_{v}:", 0)
                t.emit("csrr x7, sstatus")
                t.emit("srli x7, x7, 18")
                t.emit("andi x7, x7, 1")
                t.check("x7", v, f"{lab}_{v}", f"sstatus.SUM reads back {v}")
            pt.leaf(va, t.page("P"), V | A | D | R | W | XP | U)
            pt.on()
            st = SState(t)
            for sum_, mxr in ((0, 0), (1, 0), (0, 1), (1, 1)):
                st.set(sum_, mxr)
                for kind in ("load", "store"):
                    ok = allowed(V | R | W | XP | U, "S", kind, sum_, mxr)
                    access(
                        t, pt, "S", kind, va, ok, f"S-mode {kind} of a U=1 page, SUM={sum_} MXR={mxr}", page="ai_pg_P"
                    )
            st.set(1, 0)
            access(
                t,
                pt,
                "S",
                "fetch",
                va,
                allowed(V | R | W | XP | U, "S", "fetch", 1, 0),
                "S-mode fetch from a U=1 page, SUM=1",
                page="ai_pg_P",
            )
            # U-mode: SUM has no effect
            pt.leaf(va + 0x1000, t.page("P"), LEAF)
            t.emit(SFENCE)
            for kind in ("load", "store"):
                access(
                    t,
                    pt,
                    "U",
                    kind,
                    va + 0x1000,
                    allowed(LEAF, "U", kind, 1, 0),
                    f"U-mode {kind} of a U=0 page, SUM=1",
                    page="ai_pg_P",
                )
            st.set(0, 0)
            for kind in ("load", "store"):
                access(
                    t,
                    pt,
                    "U",
                    kind,
                    va,
                    allowed(V | R | W | XP | U, "U", kind, 0, 0),
                    f"U-mode {kind} of a U=1 page, SUM=0",
                    page="ai_pg_P",
                )
            satp_off(t)
            for kind in ("load", "store"):
                bare_access(t, kind, "P", f"satp Bare, SUM=0: S-mode {kind} of the physical address")

        with_vm(t, xlen, inner, user=True)

    both(t, sum_body)
    tests.append(t)

    # ---- sstatus_mxr
    t = new("Sv", "sstatus_mxr")
    t.describe(
        source=SUP,
        rule_text="The MXR (Make eXecutable Readable) bit modifies the privilege with which loads access virtual "
        "memory. When MXR=0, only loads from pages marked readable (R=1 in <<sv32pte>>) will succeed. When MXR=1, "
        "loads from pages marked either readable or executable (R=1 or X=1) will succeed. MXR has no effect when "
        "page-based virtual memory is not in effect.",
        context="Sv39 (RV64) or Sv32 (RV32), probed. The rule covers every load, from S-mode and U-mode.",
        plan="1. MXR reads back as written.\n"
        "2. lw from S-mode (U=0 pages) and U-mode (U=1 pages) of execute-only, read-only, read-execute and "
        "invalid-W-only pages, MXR 0 and 1: execute-only loads succeed only with MXR=1 (reading the page); "
        "R pages always; W-only always faults.\n"
        "3. MXR=1 grants nothing else: sw to an execute-only page faults.\n"
        "4. satp Bare, MXR=1: S-mode and U-mode lw of the physical address work.",
    )
    t.page("P")

    def mxr_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = VA_T[xlen] + 0x7000
            lab = t.label("mxrrb")
            for v in (1, 0):
                sstatus_bits(t, MXR, bool(v), "MXR")
                t.emit(f"{lab}_{v}:", 0)
                t.emit("csrr x7, sstatus")
                t.emit("srli x7, x7, 19")
                t.emit("andi x7, x7, 1")
                t.check("x7", v, f"{lab}_{v}", f"sstatus.MXR reads back {v}")
            pt.on()
            st = SState(t)
            for rwx in (XP, R, R | XP, W):
                for mode, u in (("S", 0), ("U", U)):
                    perms = V | A | D | rwx | u
                    pt.leaf(va, t.page("P"), perms)
                    t.emit(SFENCE)
                    for mxr in (0, 1):
                        st.set(0, mxr)
                        access(
                            t,
                            pt,
                            mode,
                            "load",
                            va,
                            allowed(perms, mode, "load", 0, mxr),
                            f"lw, PTE {rwx_name(perms)}, MXR={mxr}",
                            page="ai_pg_P",
                        )
                        if rwx == XP:
                            access(
                                t,
                                pt,
                                mode,
                                "store",
                                va,
                                allowed(perms, mode, "store", 0, mxr),
                                f"sw, PTE {rwx_name(perms)}, MXR={mxr}",
                                page="ai_pg_P",
                            )
            st.set(0, 1)
            satp_off(t)
            bare_access(t, "load", "P", "satp Bare, MXR=1: S-mode lw of the physical address")
            bare_access(t, "load", "P", "satp Bare, MXR=1: U-mode lw of the physical address", mode="U")
            st.clear()

        with_vm(t, xlen, inner, user=True)

    both(t, mxr_body)
    tests.append(t)

    # ---- sfence_vma_sum_mxr_effect
    t = new("Sv", "sfence_vma_sum_mxr_effect")
    t.describe(
        source=SUP,
        rule_text="Changes to the sstatus fields SUM and MXR take effect immediately, without the need to execute "
        "an SFENCE.VMA instruction.",
        context="Sv39 (RV64) or Sv32 (RV32), probed. A first access warms any address-translation cache; then only "
        "sstatus changes, with no fence.",
        plan="1. U=1 RW page: S-mode lw with SUM=1 succeeds; clear SUM: the next lw faults; set SUM: the next lw "
        "succeeds. Same for sw.\n"
        "2. Execute-only page: S-mode lw with MXR=1 succeeds; clear MXR: faults; set MXR: succeeds. Same from "
        "U-mode on a U=1 execute-only page.",
    )
    t.page("P")

    def eff_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va, vx, vux = VA_T[xlen] + 0x8000, VA_T[xlen] + 0x9000, VA_T[xlen] + 0xA000
            pt.leaf(va, t.page("P"), V | A | D | R | W | U)
            pt.leaf(vx, t.page("P"), V | A | D | XP)
            pt.leaf(vux, t.page("P"), V | A | D | XP | U)
            pt.on()
            st = SState(t)
            stale = MUT == "sum_needs_fence"
            for kind in ("load", "store"):
                for s_ in (1, 0, 1):
                    st.set(s_, 0)
                    ok = allowed(V | R | W | U, "S", kind, s_, 0)
                    access(
                        t,
                        pt,
                        "S",
                        kind,
                        va,
                        (not ok) if (stale and s_ == 0) else ok,
                        f"S-mode {kind} of a U=1 page right after SUM={s_}",
                        page="ai_pg_P",
                    )
            for mode, vv, u in (("S", vx, 0), ("U", vux, U)):
                for m_ in (1, 0, 1):
                    st.set(0, m_)
                    ok = allowed(V | XP | u, mode, "load", 0, m_)
                    access(
                        t,
                        pt,
                        mode,
                        "load",
                        vv,
                        (not ok) if (stale and m_ == 0) else ok,
                        f"lw of an execute-only page right after MXR={m_}",
                        page="ai_pg_P",
                    )
            st.clear()

        with_vm(t, xlen, inner, user=True)

    both(t, eff_body)
    tests.append(t)

    tests += gen_pte_bits()
    return tests


def bare_access(t: SvTest, kind: str, page: str, desc: str, mode: str = "S") -> None:
    """With satp Bare: lw (must read the page) or sw (must land) at the page's physical address."""
    t.la("x6", f"ai_pg_{page}")
    if kind == "load":
        lab = win(t, None, mode, ["lw x7, 0(x6)"], "ok", desc)
        t.check("x7", lsig(t.page_id(page)), lab, f"{desc}: reads the page")
    else:
        val = (zlib.crc32(f"{t.rule}{desc}{len(t.table)}".encode()) & 0x7FFFFFFF) | 1
        t.load("x8", val, "store value")
        lab = win(t, None, mode, ["sw x8, 24(x6)"], "ok", desc)
        t.la("x9", f"ai_pg_{page}+24")
        t.emit("lw x7, 0(x9)")
        t.check("x7", val, lab, f"{desc}: lands in the page")


def sp_va(scheme: str, level: int) -> int:
    """Test VA for a superpage leaf at `level` (1 = 2 MiB / 4 MiB)."""
    if scheme == "sv32":
        return {1: 0x2040_0000}[level]
    return {1: 0x4020_0000, 2: 0x1_4000_0000, 3: 1 << 39, 4: 1 << 48}[level]


def sp_size(scheme: str, level: int) -> int:
    return 1 << GEO[scheme][len(GEO[scheme]) - 1 - level][0]


def asid_probe(t: SvTest, pt: SvPT, reg: str) -> None:
    """reg = the ASID bits satp holds when written with all ones in ASID (pt's root, identity map); satp is left
    Bare. Clobbers x6, x7."""
    t.comment("ASIDLEN probe: write all ones to satp.ASID")
    pt.atp("x6", 0xFFFF if pt.xlen == 64 else 0x1FF)
    t.emit("csrw satp, x6")
    t.emit(f"csrr {reg}, satp")
    t.emit("csrw satp, x0")
    t.emit(SFENCE)
    if pt.xlen == 64:
        t.emit(f"slli {reg}, {reg}, 4")
        t.emit(f"srli {reg}, {reg}, 48")
    else:
        t.emit(f"srli {reg}, {reg}, 22")
        t.emit(f"andi {reg}, {reg}, 0x1FF")


def asids_distinct(t: SvTest, pt: SvPT, reg: str = "x1") -> None:
    """reg = 1 if ASIDs 1 and 2 are both representable (ASIDLEN >= 2)."""
    asid_probe(t, pt, reg)
    t.emit(f"andi {reg}, {reg}, 3")
    t.emit(f"addi {reg}, {reg}, -3")
    t.emit(f"seqz {reg}, {reg}")


def scratch(t: SvTest, off: int, reg: str, store: bool) -> None:
    """Store reg to / load reg from a scratch word in page SCR (identity view, S-mode)."""
    t.page("SCR")
    t.la("x5", f"ai_pg_SCR+{off}")
    t.emit(f"{'SREG' if store else 'LREG'} {reg}, 0(x5)")


def gen_pte_bits() -> list[SvTest]:
    tests = []

    # ---- pte_g_op
    t = new("Sv", "pte_g_op")
    t.describe(
        source=SUP,
        rule_text="The G bit designates a _global_ mapping. Global mappings are those that exist in all address "
        "spaces. For non-leaf PTEs, the global setting implies that all mappings in the subsequent levels of the "
        "page table are global.",
        context="Two root tables, used with ASID 1 and ASID 2, both map the global pages the same way, as software "
        "must. Global mappings are exempt from ASID-specific fences (sfence_vma_asid_only), so after a change to a "
        "global PTE an ASID fence leaves the old or the new translation; SFENCE.VMA x0, x0 must expose the new "
        "one. Distinct-ASID checks run only when ASIDLEN >= 2.",
        plan="1. ASID 1: lw of a G=1 leaf page reads G1, of a page below a G=1 pointer (leaf G=0) reads G2, of a "
        "non-global page reads A.\n"
        "2. Switch satp to the second root with ASID 2 (no fence): the global pages read G1 and G2; the "
        "non-global page reads B (that root's mapping).\n"
        "3. Remap the G=1 leaf to G3 in both roots: after SFENCE.VMA x0, rs2=ASID 2 it reads G1 or G3; after "
        "SFENCE.VMA x0, x0 it reads G3.",
    )
    for n in ("G1", "G2", "G3", "A", "B"):
        t.page(n)

    def g_body(xlen: int) -> None:
        def inner(pa: SvPT) -> None:
            pb = SvPT(t, f"q{xlen}", pa.scheme)
            pb.identity()
            vg, vn = VA_T[xlen] + 0xB000, VA_T[xlen] + 0xC000
            vg2 = sp_va(pa.scheme, 1) + 0x5000  # its own level-0 table, reached through a G=1 pointer
            for pt in (pa, pb):
                pt.leaf(vg, t.page("G1"), LEAF | G)
                pt.leaf(vg2, t.page("G2"), LEAF)
                pt.modify(vg2, pt.levels - 2, set_bits=G, note="G=1 on the pointer")
            pa.leaf(vn, t.page("A"), LEAF)
            pb.leaf(vn, t.page("B"), LEAF)
            pa.on(asid=1)
            gid = {n: t.page_id(n) for n in ("G1", "G2", "G3", "A", "B")}
            s_load(t, vg, gid["G1"], "ASID 1: G=1 leaf")
            s_load(t, vg2, gid["G2"], "ASID 1: below a G=1 pointer")
            s_load(t, vn, gid["A"], "ASID 1: non-global page")

            def distinct() -> None:
                pb.on(asid=2, fence=False)
                s_load(t, vg, gid["G1"], "ASID 2: G=1 leaf")
                s_load(t, vg2, gid["G2"], "ASID 2: below a G=1 pointer")
                s_load(
                    t,
                    vn,
                    gid["A" if MUT == "asid_ignored" else "B"],
                    "ASID 2 (no fence): the non-global page uses this root's mapping",
                )
                for pt in (pa, pb):
                    pt.leaf(vg, t.page("G3"), LEAF | G)
                t.emit("li x9, 2")
                t.emit("sfence.vma x0, x9")
                s_load_any(t, vg, [gid["G1"], gid["G3"]], "global page after SFENCE.VMA x0, rs2=2")
                t.emit(SFENCE)
                s_load(t, vg, gid["G3"], "global page after SFENCE.VMA x0, x0")

            asids_distinct(t, pa, "x9")
            pa.on(asid=1)
            t.emit("mv x1, x9")
            guard(t, "x1", distinct)

        with_vm(t, xlen, inner)

    both(t, g_body)
    tests.append(t)

    # ---- pte_rsw_ignored
    t = new("Sv", "pte_rsw_ignored")
    t.describe(
        source=SUP,
        rule_text="The RSW field is reserved for use by supervisor software; the implementation shall ignore this "
        "field.",
        context="RSW is PTE bits 9:8. Sv39 (RV64) or Sv32 (RV32), probed.",
        plan="RSW = 1, 2, 3 in a 4 KiB leaf, in a superpage leaf, and in the pointer PTEs above a 4 KiB leaf: "
        "S-mode lw reads the page, sw lands, and a fetch runs the page's code.",
    )
    t.page("P")

    def rsw_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = VA_T[xlen] + 0xD000
            vb = bva(pt.scheme)
            pt.leaf(vb, t.page("P"), LEAF)
            pt.on()
            for rsw in (1, 2, 3):
                bits = rsw << 8
                pt.leaf(va, t.page("P"), LEAF | bits)
                pt.leaf(sp_va(pt.scheme, 1), t.page("P"), LEAF | bits, level=1)
                for d in range(pt.levels - 1):
                    pt.modify(vb, d, set_bits=bits, clear_bits=0x300)
                t.emit(SFENCE)
                for kind in ("load", "store", "fetch"):
                    access(
                        t,
                        pt,
                        "S",
                        kind,
                        va,
                        MUT != "rsw_faults",
                        f"{kind}, RSW={rsw} in the 4 KiB leaf",
                        page="ai_pg_P",
                    )
                    access(
                        t,
                        pt,
                        "S",
                        kind,
                        sp_va(pt.scheme, 1),
                        True,
                        f"{kind}, RSW={rsw} in the superpage leaf",
                        page="ai_pg_P",
                        level=1,
                    )
                    access(t, pt, "S", kind, vb, True, f"{kind}, RSW={rsw} in the pointers", page="ai_pg_P")

        with_vm(t, xlen, inner)

    both(t, rsw_body)
    tests.append(t)

    # ---- pte_a_def / pte_d_def
    for rule, text in (
        (
            "pte_a_def",
            (
                "Each leaf PTE contains an accessed (A) and dirty (D) bit. The A bit indicates the virtual "
                "page has been read, written, or fetched from since the last time the A bit was cleared."
            ),
        ),
        (
            "pte_d_def",
            ("The D bit indicates the virtual page has been written since the last time the D bit was cleared."),
        ),
    ):
        t = new("Sv", rule)
        is_a = rule == "pte_a_def"
        t.describe(
            source=SUP,
            rule_text=text,
            context="Two A/D schemes exist (<<svade>>): Svade raises a page fault when A (or D, for a store) must be "
            "set; otherwise the hart sets the bit in the PTE. menvcfg.ADUE selects hardware updating when Svadu is "
            "implemented (menvcfg_adue_op); it is set through T-SBI and read back. With ADUE=1 the update is "
            "required. If ADUE could be set (Svadu), ADUE=0 selects Svade, so the access must fault. If ADUE is "
            "read-only 0, either scheme is accepted. In every case the outcome must match the PTE: "
            "a fault leaves the bit clear, a completed access leaves it set. D updates must be exact, so a "
            "faulting store never sets D. The implementation never clears A or D. "
            f"{ISSUE}3450: there are exactly two schemes; Svadu only selects between them (aswaterman).",
            plan=(
                "For ADUE = 1 then 0, S-mode (and one U-mode) load, store and fetch of a page whose leaf has A=0: "
                "if ADUE reads 1, no trap and A=1 afterwards; with ADUE=0 a page fault and A=0 when ADUE was "
                "writable, otherwise either that or no trap and A=1. The store case has D=1, so only A is under "
                "test. Loads and fetches leave D (0) unchanged. A load of an A=1, D=1 page leaves both set."
                if is_a
                else "For ADUE = 1 then 0, S-mode (and U-mode) sw to an A=1, D=0 RW page: if ADUE reads 1, no trap "
                "and D=1; with ADUE=0 a store page fault and D=0 when ADUE was writable, otherwise either that or "
                "no trap and D=1. A lw of an A=1, D=0 page "
                "never sets D, and a sw to an A=1, D=0 read-only page faults and leaves D=0."
            ),
        )
        t.page("P")
        t.page("SCR")

        def ad_body(xlen: int, is_a: bool = is_a, t: SvTest = t) -> None:
            def inner(pt: SvPT) -> None:
                va = VA_T[xlen] + 0xE000
                pt.on()
                for adue in (1, 0):
                    menvcfg_bit(t, xlen, ADUE_BIT, bool(adue))
                    menvcfg_get(t, xlen, ADUE_BIT, "x9")
                    t.emit(SFENCE)
                    scratch(t, 64, "x9", True)
                    if adue:
                        scratch(t, 80, "x9", True)  # ADUE writable: Svadu, so ADUE=0 selects Svade
                    if is_a:
                        cases = [
                            (m, k, V | RWX | (U if m == "U" else 0), A, A | D)
                            for m, k in (("S", "load"), ("S", "store"), ("S", "fetch"), ("U", "load"))
                        ]
                    else:
                        cases = [(m, "store", V | RWX | A | (U if m == "U" else 0), D, D) for m in ("S", "U")]
                        cases += [("S", "load", V | RWX | A, D, 0), ("S", "store_ro", V | R | A, D, 0)]
                    for mode, kind, base, bit, after_mask in cases:
                        k = "store" if kind == "store_ro" else kind
                        pte = base | (D if (is_a and k == "store") else 0)
                        pt.leaf(va, t.page("P"), pte)
                        t.emit(SFENCE)
                        if kind == "store_ro":
                            exp = pf("store")
                        elif is_a or k == "store":
                            exp = ["ok", pf(k)]
                        else:
                            exp = "ok"
                        t.la("x9", "rvtest_trap_count")
                        t.emit("LREG x9, 0(x9)")
                        scratch(t, 72, "x9", True)
                        lab = access(
                            t,
                            pt,
                            mode,
                            k,
                            va,
                            False if kind == "store_ro" else (exp if isinstance(exp, list) else exp == "ok"),
                            f"ADUE={adue}: {mode}-mode {kind}, PTE {hex(pte)}",
                            page=None,
                        )
                        t.la("x13", "rvtest_trap_count")
                        t.emit("LREG x13, 0(x13)")
                        scratch(t, 72, "x9", False)
                        t.emit("sub x13, x13, x9  // traps taken by the access (0/1)")
                        pt.read_pte(va, pt.depth(0), "x9")
                        t.emit(f"srli x6, x9, {bit.bit_length() - 1}")
                        t.emit("andi x6, x6, 1  // the bit under test")
                        if exp == "ok" or exp == pf("store"):
                            want = 1 if (exp == "ok" and (bit == A or k == "store")) else 0
                            if MUT == "d_set_on_fault" and kind == "store_ro":
                                want = 1
                            if MUT == "load_sets_d" and kind == "load" and not is_a:
                                want = 1
                            t.check("x6", want, lab, f"{kind}: {'D' if bit == D else 'A'} afterwards")
                        else:
                            t.emit("xor x6, x6, x13")
                            t.check_bool("x6", lab, "A/D: set iff the access completed (no fault)")
                            scratch(t, 64, "x7", False)
                            t.emit("and x7, x7, x13")
                            t.check("x7", int(MUT == "adue_faults"), lab, "with ADUE=1 the access does not fault")
                            if not adue:
                                scratch(t, 80, "x7", False)
                                t.emit("xori x8, x13, 1")
                                t.emit("and x7, x7, x8")
                                t.check("x7", 0, lab, "ADUE was writable (Svadu), so with ADUE=0 the access faults")
                        if is_a and k != "store":
                            t.emit("srli x6, x9, 7")
                            t.emit("andi x6, x6, 1")
                            t.check("x6", 0 if MUT != "load_sets_d" else 1, lab, f"{kind} leaves D=0")
                if is_a:
                    pt.leaf(va, t.page("P"), LEAF)
                    t.emit(SFENCE)
                    s_load(t, va, t.page_id("P"), "load of an A=1, D=1 page")
                    pt.read_pte(va, pt.depth(0), "x9")
                    t.emit("andi x9, x9, 0xC0")
                    lab = t.label("adkeep")
                    t.emit(f"{lab}:", 0)
                    t.check("x9", 0xC0, lab, "A and D are never cleared by the implementation")

            with_vm(t, xlen, inner, user=True)

        both(t, ad_body)
        tests.append(t)

    # ---- lr_sc_rsrv_set_page
    t = new("Sv", "lr_sc_rsrv_set_page", ["I", "S", "Zalrsc"])
    t.describe(
        source=SUP,
        rule_text="For implementations with both page-based virtual memory and the A standard extension, the LR/SC "
        "reservation set must lie completely within a single base physical page (i.e., a naturally aligned 4 KiB "
        "physical-memory region).",
        context="Two virtually adjacent pages map to different physical pages. An SC to an address outside the "
        "reservation set must fail (Zalrsc), so an SC to the other physical page fails whatever the reservation "
        "granule is.",
        plan="lr.w at the last word of virtual page 1 (physical page A), then sc.w to the first word of virtual page 2 "
        "(physical page B): the SC fails (rd != 0) and B's word is unchanged. Same with the pages swapped "
        "(lr.w at the start of page 2, sc.w at the end of page 1).",
    )
    t.page("A", {0xFFC: (4, 0x1111)})
    t.page("B", {0xFFC: (4, 0x2222)})

    def lrsc_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = VA_T[xlen] + 0x10000
            pt.leaf(va, t.page("A"), LEAF)
            pt.leaf(va + 0x1000, t.page("B"), LEAF)
            pt.on()
            for lr_off, sc_off, pg, off in ((0xFFC, 0x1000, "B", 0), (0x1000, 0xFFC, "A", 0xFFC)):
                lab = t.label("sc")
                t.emit(f"li x6, {hex(va + lr_off)}")
                t.emit(f"li x9, {hex(va + sc_off)}")
                t.emit("li x8, 0x7777")
                t.emit(word(lr_w(7, 6), "lr.w x7, (x6)"))
                t.emit(f"{lab}:", 0)
                t.emit(word(sc_w(7, 9, 8), "sc.w x7, x8, (x9)"))
                t.emit("snez x7, x7")
                t.check_bool("x7", lab, f"sc.w to the other physical page ({pg}) fails")
                t.la("x6", f"ai_pg_{pg}+{off}")
                t.emit("lw x7, 0(x6)")
                old = {"B": lsig(t.page_id("B")), "A": 0x1111}[pg]
                t.check("x7", old, lab, f"page {pg} is unchanged")

        with_vm(t, xlen, inner)

    both(t, lrsc_body)
    tests.append(t)
    return tests


def bva(scheme: str) -> int:
    """A VA whose page-table path is used by nothing else: index 0x88 at every level (0xC8 at the Sv32 root)."""
    va = 0
    for d, (shift, _) in enumerate(GEO[scheme]):
        va |= (0xC8 if (scheme == "sv32" and d == 0) else 0x88) << shift
    return va


def satp_val(pt: SvPT, asid: int = 0, mode: int | None = None) -> None:
    """x6 = satp for pt (root PPN, asid) with MODE `mode` (default: pt's). Clobbers x7."""
    t = pt.t
    t.la("x6", pt.root)
    t.emit("srli x6, x6, 12")
    m = MODE[pt.scheme] if mode is None else mode
    if pt.xlen == 64:
        t.emit(f"li x7, {hex((m << 60) | (asid << 44))}")
    else:
        t.emit(f"li x7, {hex((m << 31) | (asid << 22))}")
    t.emit("or x6, x6, x7")


def eq_pred(t: SvTest, a: str, b: str, out: str) -> None:
    t.emit(f"xor {out}, {a}, {b}")
    t.emit(f"seqz {out}, {out}")


def gen_satp() -> list[SvTest]:
    tests = []

    # ---- satp (CSR format)
    t = new("Sv", "satp")
    t.describe(
        source=SUP,
        rule_text="The satp CSR is an SXLEN-bit read/write register, formatted as shown in <<rv32satp>> for "
        "SXLEN=32 and <<rv64satp>> for SXLEN=64, which controls supervisor-mode address translation and "
        "protection. This register holds the physical page number (PPN) of the root page table, i.e., its "
        "supervisor physical address divided by 4 KiB; an address space identifier (ASID), which facilitates "
        "address-translation fences on a per-address-space basis; and the MODE field, which selects the current "
        "address-translation scheme.",
        context="RV64: MODE 63:60, ASID 59:44, PPN 43:0; RV32: MODE 31, ASID 30:22, PPN 21:0. Sv39/Sv32 is probed. "
        "ASID bits may be unimplemented (asidlen), so ASID bit 0 reads 1 or 0.",
        plan="1. Write satp = MODE | ASID 1 | PPN(root) (csrw), read it back: MODE and PPN exactly as written, ASID "
        "1 or 0.\n"
        "2. The PPN is the root's physical address / 4 KiB: lw of a VA mapped only by that root reads its page.\n"
        "3. csrrw returns the old value while writing a new one (satp with ASID 0); csrrs/csrrc with rs1=x0 "
        "read without writing.\n"
        "4. Write 0: satp reads 0.",
    )
    t.page("P")

    def satp_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            pt.leaf(VA_T[xlen], t.page("P"), LEAF)
            satp_val(pt, asid=1)
            lab = t.label("rt")
            t.emit(f"{lab}:", 0)
            t.emit("csrw satp, x6")
            t.emit("csrr x9, satp")
            t.emit(SFENCE)
            abit = (1 << 44) if xlen == 64 else (1 << 22)
            t.load("x8", ~abit & ((1 << xlen) - 1), "all but ASID bit 0")
            t.emit("and x7, x9, x8")
            t.emit("and x8, x6, x8")
            t.emit("xor x7, x7, x8")
            t.check("x7", 0, lab, "satp MODE, PPN and the other ASID bits read back as written")
            t.load("x8", abit, "ASID bit 0")
            t.emit("and x7, x9, x8")
            t.check("x7", [abit, 0], lab, "satp ASID bit 0 reads 1, or 0 when not implemented")
            s_load(t, VA_T[xlen], t.page_id("P"), "lw through the root whose PPN satp holds")
            satp_val(pt, asid=0)
            lab = t.label("swap")
            t.emit(f"{lab}:", 0)
            t.emit("csrrw x7, satp, x6")
            t.emit("xor x7, x7, x9")
            t.check("x7", 0, lab, "csrrw satp returns the old value")
            t.emit("csrrs x7, satp, x0")
            t.emit("csrrc x8, satp, x0")
            t.emit("xor x7, x7, x6")
            t.emit("xor x8, x8, x6")
            t.emit("or x7, x7, x8")
            t.check("x7", 0, lab, "csrrw wrote the new value; csrrs/csrrc x0 read it without writing")
            t.emit(SFENCE)
            lab = t.label("zero")
            t.emit(f"{lab}:", 0)
            t.emit("csrw satp, x0")
            t.emit("csrr x7, satp")
            t.check("x7", 0, lab, "satp reads 0 after writing 0")

        with_vm(t, xlen, inner)

    both(t, satp_body)
    tests.append(t)

    # ---- satp_mode: read-back legality of every MODE value
    t = new("Sv", "satp_mode")
    t.describe(
        source=SUP,
        rule_text="<<norm:satp_mode_enc>> shows the encodings of the MODE field when SXLEN=32 and SXLEN=64.",
        context="satp_mode_enc: SXLEN=32: 0 Bare, 1 Sv32. SXLEN=64: 0 Bare, 1-7 reserved, 8 Sv39, 9 Sv48, 10 Sv57, "
        "11 reserved for Sv64, 12-13 reserved, 14-15 custom. A write with an unsupported (or reserved) MODE has "
        "no effect (satp_mode_op_unsupported). Custom values are not written: a custom mode may legally exist.",
        plan="Starting from a supported paged value S0 (Sv39 / Sv32, probed), write each non-custom MODE with the "
        "PPN of a table built for that scheme (any table for reserved values), read satp back, and restore S0:\n"
        "- reserved values (RV64 1-7, 11, 12, 13): satp still reads S0;\n"
        "- Sv39/Sv48/Sv57 (RV64), Sv32 (RV32): satp reads the written value or S0 (unsupported);\n"
        "- Bare (0): satp reads 0 or S0.",
    )

    def mode_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            others = {}
            if xlen == 64:
                for sch in ("sv48", "sv57"):
                    others[sch] = SvPT(t, f"m{sch}", sch)
                    others[sch].identity()
            satp_val(pt)
            t.emit("mv x9, x6  // S0")
            t.emit("csrw satp, x9")
            t.emit(SFENCE)
            vals = list(range(14)) if xlen == 64 else [0, 1]
            for m in vals:
                tab = pt
                if xlen == 64 and m in (9, 10):
                    tab = others["sv48" if m == 9 else "sv57"]
                satp_val(tab, mode=m)
                lab = t.label(f"m{m}")
                t.emit(f"{lab}:", 0)
                t.emit("csrw satp, x6")
                t.emit("csrr x7, satp")
                t.emit("csrw satp, x9  // restore S0")
                t.emit(SFENCE)
                reserved = xlen == 64 and m not in (0, 8, 9, 10)
                if reserved and MUT != "reserved_mode_written":
                    eq_pred(t, "x7", "x9", "x8")
                    t.check_bool("x8", lab, f"MODE {m} is reserved: the write has no effect")
                elif reserved:  # mutant: the reserved value is written
                    eq_pred(t, "x7", "x6", "x8")
                    t.check_bool("x8", lab, f"MODE {m}: (mutant) written")
                else:
                    eq_pred(t, "x7", "x9", "x8")
                    t.emit("xor x7, x7, x6")
                    t.emit("seqz x7, x7")
                    t.emit("or x8, x8, x7")
                    t.check_bool("x8", lab, f"MODE {m}: satp reads the written value, or is unchanged")

        with_vm(t, xlen, inner)

    both(t, mode_body)
    tests.append(t)

    # ---- satp_mode_enc: each value selects its scheme
    t = new("Sv", "satp_mode_enc")
    t.describe(
        source=SUP,
        rule_text="Encoding of satp MODE field: SXLEN=32: 0 Bare (no translation or protection), 1 Sv32 (page-based "
        "32-bit virtual addressing). SXLEN=64: 0 Bare, 1-7 reserved for standard use, 8 Sv39, 9 Sv48, 10 Sv57, 11 "
        "Sv64 (reserved), 12-13 reserved for standard use, 14-15 designated for custom use.",
        context="Each scheme's table maps the same VA to a different page, and the walks differ in depth (2, 3, 4, "
        "5 levels), so a MODE decoded as the wrong scheme reads the wrong page or faults.",
        plan="For each paged MODE the hart accepts (probed): satp = that MODE with its own table; lw of the common "
        "VA reads that table's page. Then MODE=0: no translation (the VA is not mapped to any of the pages: the "
        "lw either faults with an access fault or reads something else).",
    )
    for n in ("P32", "P39", "P48", "P57"):
        t.page(n)

    def enc_body(xlen: int) -> None:
        schemes = ["sv32"] if xlen == 32 else ["sv39", "sv48", "sv57"]
        va = VA_T[xlen] + 0x11000
        for sch in schemes:
            pt = SvPT(t, f"e{sch}", sch)
            pt.identity()
            pt.leaf(va, t.page("P" + sch[2:]), LEAF)
            probe(t, pt)

            def run(pt: SvPT = pt, sch: str = sch) -> None:
                pt.on()
                pid = t.page_id("P" + sch[2:])
                if MUT == "sv48_as_sv39" and sch == "sv48":
                    pid = t.page_id("P39")
                s_load(t, va, pid, f"MODE {MODE[sch]} translates with the {sch} table")
                satp_off(t)

            guard(t, "x1", run)
        bare_not(t, va, [t.page_id("P" + s[2:]) for s in schemes], "MODE=0: no translation")

    both(t, enc_body)
    tests.append(t)

    # ---- satp_mode_bare_op
    t = new("Sv", "satp_mode_bare_op")
    t.describe(
        source=SUP,
        rule_text="When MODE=Bare, supervisor virtual addresses are equal to supervisor physical addresses, and "
        "there is no additional memory protection beyond the physical memory protection scheme described in "
        "<<pmp>>.",
        context="After running with a table that maps the data page as a supervisor page and leaves the rest of "
        "the address space unmapped, satp is written with 0 (no fence).",
        plan="With satp=0: S-mode lw/sw of the page's physical address read and write it; U-mode lw, sw and a "
        "fetch (the page's stub) at the physical address work although no PTE grants U access; S-mode fetch "
        "from the page works.",
    )
    t.page("P")

    def bare_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            pt.on()
            satp_off(t)
            for mode in ("S", "U"):
                bare_access(t, "load", "P", f"Bare: {mode}-mode lw of the physical address", mode=mode)
                bare_access(t, "store", "P", f"Bare: {mode}-mode sw to the physical address", mode=mode)
                t.la("x6", "ai_pg_P")
                t.emit("li x7, 0")
                lab = win(t, None, mode, [f"jalr x1, {EXEC_OFF}(x6)"], "ok", f"Bare: {mode}-mode fetch")
                t.check("x7", t.page_id("P"), lab, f"Bare: {mode}-mode fetch runs the page")

        with_vm(t, xlen, inner)

    both(t, bare_body)
    tests.append(t)

    # ---- satp_mode_bare_zero_fields
    t = new("Sv", "satp_mode_bare_zero_fields")
    t.describe(
        source=SUP,
        rule_text="To select MODE=Bare, software must write zero to the remaining fields of satp (bits 30-0 when "
        "SXLEN=32, or bits 59-0 when SXLEN=64).",
        context="A software obligation; what is observable is that the conforming write (all zeros) selects Bare "
        "with all fields zero, from any previous value.",
        plan="From satp = Sv39/Sv32 | ASID all ones | PPN(root) (probed), csrw satp, x0: satp reads 0 and the next "
        "lw of a VA mapped only by the table is not translated (it faults with an access fault or reads other "
        "data).",
    )
    t.page("P")

    def bz_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = pt.va_t + 0x12000
            pt.leaf(va, t.page("P"), LEAF)
            pt.on(asid=0xFFFF if xlen == 64 else 0x1FF)
            s_load(t, va, t.page_id("P"), "translated before")
            lab = t.label("z")
            t.emit(f"{lab}:", 0)
            t.emit("csrw satp, x0")
            t.emit("csrr x7, satp")
            t.check("x7", 0, lab, "satp reads 0")
            bare_not(t, va, [t.page_id("P")], "after writing 0")

        with_vm(t, xlen, inner)

    both(t, bz_body)
    tests.append(t)

    # ---- svbare_satp_mode_bare
    t = new("Sv", "svbare_satp_mode_bare", ["I", "S", "Svbare"])
    t.describe(
        source=SUP,
        rule_text="If an implementation supports the Svbare extension, then the satp register's MODE field must be "
        "capable of holding the value Bare.",
        context="Requires Svbare. Bare is written after a paged mode (probed) and from reset state.",
        plan="1. satp = 0: reads MODE 0.\n2. From Sv39/Sv32 with a table: write 0, satp.MODE reads 0, and a VA mapped "
        "only by the table is no longer translated.",
    )
    t.page("P")

    def sb_body(xlen: int) -> None:
        lab = t.label("b0")
        t.emit(f"{lab}:", 0)
        t.emit("csrw satp, x0")
        t.emit("csrr x7, satp")
        t.emit(f"srli x7, x7, {60 if xlen == 64 else 31}")
        t.check("x7", 0, lab, "satp.MODE holds Bare")

        def inner(pt: SvPT) -> None:
            va = pt.va_t + 0x12000
            pt.leaf(va, t.page("P"), LEAF)
            pt.on()
            s_load(t, va, t.page_id("P"), "translated in the paged mode")
            lab = t.label("b1")
            t.emit(f"{lab}:", 0)
            t.emit("csrw satp, x0")
            t.emit("csrr x7, satp")
            t.emit(f"srli x7, x7, {60 if xlen == 64 else 31}")
            t.check("x7", 0, lab, "satp.MODE holds Bare after a paged mode")
            bare_not(t, va, [t.page_id("P")], "after selecting Bare")

        with_vm(t, xlen, inner)

    both(t, sb_body)
    tests.append(t)

    # ---- satp_mode_sxlen32 (Sv32 scheme)
    t = new("Sv", "satp_mode_sxlen32", ["I", "S", "Sv32"])
    t.describe(
        source=SUP,
        rule_text="When SXLEN=32, the only other valid setting for MODE is Sv32, a paged virtual-memory scheme "
        "described in <<sv32>>.",
        context="RV32 only (the file passes trivially on RV64). Sv32: 32-bit VA, two levels of 1024 4-byte PTEs, "
        "4 MiB megapages that must be 4 MiB-aligned physically (else page fault), a pointer at the last level "
        "faults, V=0 faults at either level, W=1 R=0 is reserved (<<sv32algorithm>>).",
        plan="With satp.MODE = 1 (required by Sv32): 1. satp reads MODE=1. 2. A 4 KiB page through two levels "
        "(VPN[1] and VPN[0] index the 4-byte PTEs) reads its page; root index 1023 and leaf index 1023 are used. "
        "3. A 4 MiB megapage reads the page at its offset. 4. Page faults (13, xtval 0 or the VA): megapage with "
        "PPN[0] != 0 (bit 0 or bit 9), V=0 at the root and at the leaf, a pointer at the leaf level, and a W-only "
        "leaf.",
    )
    for n in ("P", "Q"):
        t.page(n)

    with t.rv32_only():
        pt = SvPT(t, "s32", "sv32")
        pt.identity()
        va = VA_T[32] + 0x13000
        vtop = 0xFFFF_F000
        vmeg = sp_va("sv32", 1)
        pt.leaf(va, t.page("P"), LEAF)
        pt.leaf(vtop, t.page("Q"), LEAF)
        pt.leaf(vmeg, t.page("P"), LEAF, level=1)
        pt.on()
        lab = t.label("m")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, satp")
        t.emit("srli x7, x7, 31")
        t.check("x7", 1, lab, "satp.MODE reads Sv32")
        s_load(t, va, t.page_id("P"), "4 KiB page through two levels")
        s_load(t, vtop, t.page_id("Q"), "root and leaf index 1023")
        access(t, pt, "S", "load", vmeg, True, "4 MiB megapage", page="ai_pg_P", level=1)
        cases = [
            (vmeg, "ppn", 1, 1, "megapage with PPN[0] bit 0 set"),
            (vmeg, "ppn", 1 << 9, 1, "megapage with PPN[0] bit 9 set"),
            (va + 0x1000, "raw0", LEAF & ~V, 0, "leaf V=0"),
            (va + 0x2000, "ptr", 0, 0, "pointer at the leaf level"),
            (va + 0x3000, "perm", V | W | A | D, 0, "W-only leaf (reserved)"),
            (0x6040_0000, "rootinv", 0, 1, "root PTE V=0"),
        ]
        for v, kind, x, level, note in cases:
            if kind == "ppn":
                pt.leaf(v, t.page("P"), LEAF, level=1, ppn_add=x)
            elif kind == "raw0":
                pt.leaf(v, t.page("P"), x)
            elif kind == "ptr":
                pt.leaf(v, t.page("P"), V)
            elif kind == "perm":
                pt.leaf(v, t.page("P"), x)
            else:
                pt.raw(v, 0x2000_0000 | RWX, level=1, note="V=0")
            t.emit(SFENCE)
            ok = MUT == "sv32_misaligned_ok" and kind == "ppn"
            access(t, pt, "S", "load", v, ok, note)
        satp_off(t)
    tests.append(t)

    # ---- satp_mode_sxlen64
    t = new("Sv", "satp_mode_sxlen64", rv64=True)
    t.describe(
        source=SUP,
        rule_text="When SXLEN=64, three paged virtual-memory schemes are defined: Sv39, Sv48, and Sv57, described in "
        "<<sv39>>, <<sv48>>, and <<sv57>>, respectively. One additional scheme, Sv64, will be defined in a later "
        "version of this specification. The remaining MODE settings are reserved for future use and may define "
        "different interpretations of the other fields in satp.",
        context="RV64 only. Each accepted scheme (probed) translates VAs of its own width: a VA with bit 47 set is "
        "canonical only under Sv57 (with bits 63:48 zero, bit 47 = 1 needs Sv57's 57-bit VA); a VA with bit 38 "
        "set and bits 63:39 zero is canonical under Sv48 and Sv57 but not Sv39. Sv64 (11) is not yet defined, so "
        "no hart accepts it.",
        plan="1. Sv39 (8): the 2^38+ VA page-faults (13). Sv48 (9) and Sv57 (10), when accepted: it reads its page. "
        "The 2^47+ VA faults under Sv39 and Sv48 and reads its page under Sv57.\n"
        "2. MODE=11 (Sv64) is not accepted: satp is unchanged.",
    )
    t.page("P")
    t.page("Q")
    va38, va47 = 1 << 38, 1 << 47
    for sch in ("sv39", "sv48", "sv57"):
        pt = SvPT(t, f"x{sch}", sch)
        pt.identity()
        if sch != "sv39":
            pt.leaf(va38, t.page("P"), LEAF)
        if sch == "sv57":
            pt.leaf(va47, t.page("Q"), LEAF)
        probe(t, pt)

        def run(pt: SvPT = pt, sch: str = sch) -> None:
            pt.on()
            for v, pg, ok in ((va38, "P", sch != "sv39"), (va47, "Q", sch == "sv57")):
                if MUT == "sv39_wide_va" and sch == "sv39" and v == va38:
                    ok = True
                access(t, pt, "S", "load", v, ok, f"{sch}: lw of {hex(v)}", page=f"ai_pg_{pg}")
            if sch == "sv39":
                lab = t.label("sv64")
                satp_val(pt)
                t.emit("mv x9, x6")
                satp_val(pt, mode=11)
                t.emit(f"{lab}:", 0)
                t.emit("csrw satp, x6")
                t.emit("csrr x7, satp")
                t.emit("csrw satp, x9")
                eq_pred(t, "x7", "x9", "x8")
                t.check_bool("x8", lab, "MODE=11 (Sv64, not defined) is not accepted: satp unchanged")
            satp_off(t)

        guard(t, "x1", run)
    tests.append(t)

    # ---- satp_mode_op_unsupported
    t = new("Sv", "satp_mode_op_unsupported")
    t.describe(
        source=SUP,
        rule_text="Implementations are not required to support all MODE settings, and if satp is written with an "
        "unsupported MODE, the entire write has no effect; no fields in satp are modified.",
        context="The previous value S0 has a paged MODE, ASID all ones (as implemented) and the PPN of table 1; "
        "the rejected write has a different ASID (0x2A5) and table 2's PPN, so a write that changes only some "
        "fields is caught.",
        plan="RV64: write each reserved MODE (1-7, 11, 12, 13), and Sv48 / Sv57 when the probe shows them "
        "unsupported: satp still reads S0. On a Bare-only RV64 hart (Sv39 rejected), writes of MODE 1, 7, 8-13 with "
        "ASID 0x2A5 and a nonzero PPN leave satp = 0. RV32: if Sv32 is unsupported, writing it leaves satp = 0.",
    )

    def uns_body(xlen: int) -> None:
        if xlen == 32:
            pt = SvPT(t, "u32", "sv32")
            pt.identity()
            probe(t, pt)
            t.emit("xori x1, x1, 1")

            def run32() -> None:
                satp_val(pt, asid=0x2A5 & 0x1FF)
                lab = t.label("u")
                t.emit("csrw satp, x0")
                t.emit(f"{lab}:", 0)
                t.emit("csrw satp, x6")
                t.emit("csrr x7, satp")
                t.check("x7", 0, lab, "unsupported Sv32: the write has no effect")

            guard(t, "x1", run32)
            return

        bo = SvPT(t, "ubare", "sv39")
        bo.identity()
        probe(t, bo)
        t.emit("xori x1, x1, 1  // 1: Sv39 not accepted (and so no paged mode)")

        def bare_only() -> None:
            t.emit("csrw satp, x0")
            for m in (1, 7, 8, 9, 10, 11, 12, 13):
                satp_val(bo, asid=0x2A5, mode=m)
                lab = t.label(f"b{m}")
                t.emit(f"{lab}:", 0)
                t.emit("csrw satp, x6")
                t.emit("csrr x7, satp")
                t.emit("csrw satp, x0")
                t.check("x7", 0, lab, f"Bare-only hart: MODE {m} write has no effect")

        guard(t, "x1", bare_only)

        def inner(pt: SvPT) -> None:
            p2 = SvPT(t, "u2", "sv39")
            p2.identity()
            others = {s: SvPT(t, f"u{s}", s) for s in ("sv48", "sv57")}
            for o in others.values():
                o.identity()
            satp_val(pt, asid=0xFFFF)
            t.emit("csrw satp, x6")
            t.emit("csrr x9, satp  // S0")
            t.emit(SFENCE)
            for m in (1, 2, 3, 4, 5, 6, 7, 11, 12, 13):
                satp_val(p2, asid=0x2A5, mode=m)
                lab = t.label(f"r{m}")
                t.emit(f"{lab}:", 0)
                t.emit("csrw satp, x6")
                t.emit("csrr x7, satp")
                t.emit("csrw satp, x9")
                eq_pred(t, "x7", "x9", "x8")
                t.check_bool("x8", lab, f"MODE {m}: no field of satp changes")
            for sch, o in others.items():
                probe(t, o, "x8")
                t.emit("csrw satp, x9")
                t.emit(SFENCE)
                t.emit("xori x1, x8, 1")

                def unsup(o: SvPT = o, sch: str = sch) -> None:
                    satp_val(o, asid=0x2A5)
                    lab = t.label("ru")
                    t.emit(f"{lab}:", 0)
                    t.emit("csrw satp, x6")
                    t.emit("csrr x7, satp")
                    t.emit("csrw satp, x9")
                    eq_pred(t, "x7", "x9", "x8")
                    t.check_bool("x8", lab, f"unsupported {sch}: no field of satp changes")

                guard(t, "x1", unsup)

        with_vm(t, xlen, inner)

    both(t, uns_body)
    tests.append(t)

    # ---- asidlen / asid_lsb_first / asidmax
    t = new("Sv", "asidlen")
    t.describe(
        source=SUP,
        rule_text="The number of ASID bits is UNSPECIFIED and may be zero.",
        context="ASIDLEN is found by writing ones to every ASID bit and reading satp back. Constrained: the "
        "implemented bits are the low ASIDLEN bits (asid_lsb_first) and ASIDLEN <= ASIDMAX (9 / 16).",
        plan="For Sv39/Sv32 (probed), and Sv48/Sv57 when accepted: write ASID all ones; the ASID read back has the "
        "form 2^n - 1 (n >= 0). A second all-ones write reads the same value, and the MODE/PPN fields are "
        "unaffected.",
    )

    def asid_cases(xlen: int, rule: str) -> None:
        schemes = ["sv32"] if xlen == 32 else ["sv39", "sv48", "sv57"]
        for sch in schemes:
            pt = SvPT(t, f"a{sch}", sch)
            pt.identity()
            probe(t, pt)

            def run(pt: SvPT = pt, sch: str = sch) -> None:
                amax = 0xFFFF if xlen == 64 else 0x1FF
                asid_probe(t, pt, "x9")
                lab = t.label("al")
                t.emit(f"{lab}:", 0)
                if rule == "asidlen":
                    t.emit("addi x7, x9, 1")
                    t.emit("and x7, x7, x9")
                    t.emit("seqz x7, x7")
                    if MUT == "asid_none":
                        t.emit("seqz x7, x9")
                    t.check_bool("x7", lab, f"{sch}: the implemented ASID bits are 2^n - 1")
                    asid_probe(t, pt, "x8")
                    eq_pred(t, "x8", "x9", "x7")
                    t.check_bool("x7", lab, f"{sch}: the probe is repeatable")
                elif rule == "asid_lsb_first":
                    for pat in (0x5555, 0xAAAA, 1, 0x8000) if xlen == 64 else (0x155, 0xAA, 1, 0x100):
                        pt.on(asid=pat)
                        t.emit("csrr x7, satp")
                        t.emit("csrw satp, x0")
                        t.emit(SFENCE)
                        if xlen == 64:
                            t.emit("slli x7, x7, 4")
                            t.emit("srli x7, x7, 48")
                        else:
                            t.emit("srli x7, x7, 22")
                            t.emit("andi x7, x7, 0x1FF")
                        t.emit(f"li x8, {hex(pat)}")
                        t.emit("and x8, x8, x9" if MUT != "asid_write_ignored" else "and x8, x8, x0")
                        eq_pred(t, "x7", "x8", "x8")
                        t.check_bool("x8", lab, f"{sch}: ASID {hex(pat)} reads back as its low ASIDLEN bits")
                else:  # asidmax
                    satp_val(pt, asid=amax)
                    t.emit("csrw satp, x6")
                    t.emit("csrr x7, satp")
                    t.emit("csrw satp, x0")
                    t.emit(SFENCE)
                    t.emit(f"li x8, {hex(amax)}")
                    t.emit("and x8, x8, x9")
                    eq_pred(t, "x8", "x9", "x8")
                    t.check_bool("x8", lab, f"{sch}: ASIDLEN <= {16 if xlen == 64 else 9}")
                    # MODE and PPN unaffected by the all-ones ASID
                    mask = ((1 << 64) - 1) ^ (0xFFFF << 44) if xlen == 64 else 0xFFFF_FFFF ^ (0x1FF << 22)
                    t.load("x8", mask, "MODE and PPN fields")
                    t.emit("and x7, x7, x8")
                    t.emit("and x6, x6, x8")
                    eq_pred(t, "x7", "x6", "x7")
                    t.check_bool("x7", lab, f"{sch}: an all-ones ASID does not spill into MODE or PPN")

            guard(t, "x1", run)

    both(t, lambda x: asid_cases(x, "asidlen"))
    tests.append(t)

    t = new("Sv", "asid_lsb_first")
    t.describe(
        source=SUP,
        rule_text="The least-significant bits of ASID are implemented first: that is, if ASIDLEN > 0, "
        "ASID[ASIDLEN-1:0] is writable.",
        context="ASIDLEN comes from an all-ones write (mask m = 2^ASIDLEN - 1). Every scheme the hart accepts is "
        "checked.",
        plan="Write ASID = 0x5555, 0xAAAA, 1, 0x8000 (RV32: 0x155, 0xAA, 1, 0x100): satp.ASID reads pattern & m.",
    )
    both(t, lambda x: asid_cases(x, "asid_lsb_first"))
    tests.append(t)

    t = new("Sv", "asidmax")
    t.describe(
        source=SUP,
        rule_text="The maximal value of ASIDLEN, termed ASIDMAX, is 9 for Sv32 or 16 for Sv39, Sv48, and Sv57.",
        context="The ASID field is 9 bits (RV32) or 16 bits (RV64) wide, so ASIDLEN <= ASIDMAX means the all-ones "
        "probe stays inside the field.",
        plan="For each accepted scheme: an all-ones ASID write reads back within ASIDMAX bits, and MODE and PPN read "
        "back unchanged.",
    )
    both(t, lambda x: asid_cases(x, "asidmax"))
    tests.append(t)

    # ---- satp_op_active (M-mode file)
    t = new("Sv", "satp_op_active", ["I", "S", "Sm"], boot="M", suffix="_Sm")
    t.describe(
        source=SUP,
        rule_text="The satp CSR is considered _active_ when the effective privilege mode is S-mode or U-mode. "
        "Executions of the address-translation algorithm may only begin using a given value of satp when satp is "
        "active.",
        context="Boots to M-mode. satp selects Sv39/Sv32 (probed) with a root table that maps nothing but one 4 KiB "
        "page: the VA equal to page B's physical address maps to page A. M-mode code and data are not mapped, so "
        "any translation in M-mode would fault. MPRV=1 makes the effective privilege of loads and stores MPP.",
        plan="1. With satp set, M-mode (MPRV=0) runs, loads B's address (reads B) and stores to it (lands in B).\n"
        "2. MPRV=1, MPP=S: lw of B's address reads A (satp active for the load).\n"
        "3. MPRV=1, MPP=M: lw reads B (effective privilege M).\n"
        "MPRV is cleared before satp is reset.",
    )
    t.page("A")
    t.page("B")

    def act_body(xlen: int) -> None:
        pt = SvPT(t, f"act{xlen}", BASE[xlen])
        pt.leaf_rt("ai_pg_B", "ai_pg_A", LEAF)
        satp_val(pt)
        t.emit("csrw satp, x6")
        t.emit("csrr x1, satp")
        t.emit(SFENCE)
        t.emit(f"srli x1, x1, {60 if xlen == 64 else 31}")

        def run() -> None:
            lab = t.label("m")
            t.la("x6", "ai_pg_B")
            t.emit(f"{lab}:", 0)
            t.emit("lw x7, 0(x6)")
            t.check(
                "x7",
                lsig(t.page_id("B")) if MUT != "satp_active_m" else lsig(t.page_id("A")),
                lab,
                "M-mode, MPRV=0: not translated",
            )
            t.emit("li x8, 0x3C3C")
            t.emit("sw x8, 32(x6)")
            t.emit("lw x7, 32(x6)")
            t.check("x7", 0x3C3C, lab, "M-mode store not translated")
            for mpp, pid, note in ((1, "A", "MPP=S: translated"), (3, "B", "MPP=M: not translated")):
                t.emit("li x8, 0x1800")
                t.emit("csrc mstatus, x8")
                t.emit(f"li x8, {hex(mpp << 11)}")
                t.emit("csrs mstatus, x8")
                t.emit("li x8, 0x20000  // MPRV")
                t.emit("csrs mstatus, x8")
                t.emit("lw x7, 0(x6)")
                t.emit("csrc mstatus, x8")
                t.check("x7", lsig(t.page_id(pid)), lab, f"MPRV=1, {note}")
            t.emit("li x8, 0x1800")
            t.emit("csrs mstatus, x8  // MPP = M")

        guard(t, "x1", run)
        t.emit("csrw satp, x0")
        t.emit(SFENCE)

    both(t, act_body)
    tests.append(t)

    # ---- satp_op_sfence_vma
    t = new("Sv", "satp_op_sfence_vma")
    t.describe(
        source=SUP,
        rule_text="Note that writing satp does not imply any ordering constraints between page-table updates and "
        "subsequent address translations, nor does it imply any invalidation of address-translation caches.",
        context="A permission, so the old and the new translation are both legal after a satp write without a "
        "fence; nothing else is. SFENCE.VMA then exposes the new one.",
        plan="VA -> A (read once). Change the leaf to B, rewrite satp with the same value: lw reads A or B. Rewrite "
        "satp with Bare and back: A or B. SFENCE.VMA: B.",
    )
    t.page("A")
    t.page("B")

    def osf_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = pt.va_t + 0x14000
            pt.leaf(va, t.page("A"), LEAF)
            pt.on()
            a, b = t.page_id("A"), t.page_id("B")
            s_load(t, va, a, "before the change")
            pt.leaf(va, t.page("B"), LEAF)
            pt.on(fence=False)
            s_load_any(t, va, [a, b], "after rewriting satp")
            t.emit("csrw satp, x0")
            pt.on(fence=False)
            s_load_any(t, va, [a, b], "after Bare and back")
            t.emit(SFENCE)
            s_load(t, va, b, "after SFENCE.VMA")

        with_vm(t, xlen, inner)

    both(t, osf_body)
    tests.append(t)

    # ---- satp_mode_roz_sfence_illegal
    t = new("Sv", "satp_mode_roz_sfence_illegal")
    t.describe(
        source=SUP,
        rule_text="For implementations that make satp.MODE read-only zero (always Bare), attempts to execute an "
        "SFENCE.VMA instruction might raise an illegal-instruction exception.",
        context="satp.MODE is read-only zero iff the hart accepts no Sv39 (RV64) / Sv32 (RV32) (probed). Otherwise "
        "SFENCE.VMA is a normal S-mode instruction (mstatus.TVM=0).",
        plan="S-mode sfence.vma x0,x0 and sfence.vma x6,x7: if a paged mode is accepted, no trap; otherwise no trap "
        "or illegal instruction (xtval 0 or the encoding).",
    )

    def roz_body(xlen: int) -> None:
        pt = SvPT(t, f"z{xlen}", BASE[xlen])
        pt.identity()
        probe(t, pt)
        t.emit("mv x9, x1")

        def paged() -> None:
            for e in (sfence_vma(0, 0), sfence_vma(6, 7)):
                t.emit("li x6, 0")
                t.emit("li x7, 0")
                win(
                    t,
                    None,
                    "S",
                    [word(e, "sfence.vma")],
                    "ok" if MUT != "sfence_illegal" else ILLEGAL,
                    "sfence.vma with paging",
                    tval=[0, e],
                )

        def roz() -> None:
            for e in (sfence_vma(0, 0), sfence_vma(6, 7)):
                win(
                    t,
                    None,
                    "S",
                    [word(e, "sfence.vma")],
                    ["ok", ILLEGAL],
                    "sfence.vma, satp.MODE read-only 0",
                    tval=[0, e],
                )

        t.emit("mv x1, x9")
        guard(t, "x1", paged)
        t.emit("xori x1, x9, 1")
        guard(t, "x1", roz)

    both(t, roz_body)
    tests.append(t)

    # ---- satp_ppn_Sv32_sz
    t = new("Sv", "satp_ppn_Sv32_sz", ["I", "S", "Sv32"])
    t.describe(
        source=SUP,
        rule_text="[the 20-bit VPN] is translated into a 22-bit physical page number (PPN)",
        context="RV32 only. Sv32 physical addresses are 34 bits: PTE.PPN[1] is 12 bits (PTE bits 31:20), so PPN bits "
        "21:20 select physical addresses at and above 4 GiB. The algorithm never ignores high PPN bits "
        "(<<sv32algorithm>> note), so such a PTE is not a page fault and does not alias page P below 4 GiB.",
        plan="Leaves whose PPN is P's plus 2^20 or 2^21 (PA + 4 GiB, + 8 GiB): lw raises no page fault: it either "
        "raises a load access fault or reads data other than P's signature. P's own mapping reads P.",
    )
    t.page("P")
    with t.rv32_only():
        pt = SvPT(t, "pp32", "sv32")
        pt.identity()
        va = VA_T[32] + 0x15000
        pt.leaf(va, t.page("P"), LEAF)
        pt.leaf(va + 0x1000, t.page("P"), LEAF, ppn_add=1 << 20)
        pt.leaf(va + 0x2000, t.page("P"), LEAF, ppn_add=1 << 21)
        pt.on()
        s_load(t, va, t.page_id("P"), "P's own mapping")
        for k, note in ((1, "PPN bit 20 (PA bit 32)"), (2, "PPN bit 21 (PA bit 33)")):
            high_ppn_load(t, va + k * 0x1000, t.page_id("P"), note)
        satp_off(t)
    tests.append(t)
    return tests


def high_ppn_load(t: SvTest, va: int, pid: int, note: str) -> None:
    """lw through a leaf whose PPN has a high bit added: an access fault, or data that is not page pid's
    signature; never a page fault."""
    t.load("x7", lsig(pid) ^ 1, "preset: not P's signature")
    t.emit(f"li x6, {hex(va)}")
    exp = ["ok", AF["load"]] if MUT != "high_ppn_page_fault" else LOAD_PF
    lab = win(t, None, "S", ["lw x7, 0(x6)"], exp, f"lw with {note}", tval=[0, va])
    t.load("x8", lsig(pid), "P's signature")
    t.emit("xor x8, x8, x7")
    t.emit("snez x8, x8")
    t.check_bool("x8", lab, f"{note}: does not alias the page below")


def bare_not(t: SvTest, va: int, pids: list, desc: str) -> None:
    """With translation off, lw of va (a VA mapped only by page tables) must not be translated: an access fault,
    or data other than the mapped pages' signatures."""
    t.load("x7", 0, "preset")
    t.emit(f"li x6, {hex(va)}")
    lab = win(t, None, "S", ["lw x7, 0(x6)"], ["ok", AF["load"]], f"{desc}: lw of {hex(va)}", tval=[0, va])
    t.emit("li x9, 1")
    for p in pids:
        t.load("x8", lsig(p), "a page's signature")
        t.emit("xor x8, x8, x7")
        t.emit("snez x8, x8")
        t.emit("and x9, x9, x8")
    t.check_bool("x9", lab, f"{desc}: not translated")


def alt_table(t: SvTest, pt: SvPT, va: int, page: str, name: str) -> str:
    """A spare leaf-level table whose entry for va maps page (LEAF); returns its label."""
    lab = t.pt_table(name)
    t.comment(f"spare leaf table {lab}: {hex(va)} -> {page}")
    t.la("x8", lab)
    t.emit(f"li x7, {pt.idx(va, pt.levels - 1) * pt.pte}")
    t.emit("add x8, x8, x7")
    t.la("x6", page)
    t.emit("srli x6, x6, 12")
    t.emit("slli x6, x6, 10")
    t.emit(f"li x7, {hex(LEAF)}")
    t.emit("or x6, x6, x7")
    t.emit("SREG x6, 0(x8)")
    return lab


def repoint(t: SvTest, pt: SvPT, va: int, table: str) -> None:
    """Point va's last pointer PTE (the one selecting its leaf table) at `table`."""
    t.comment(f"{pt.name}: the pointer for {hex(va)} now selects {table}")
    t.la("x6", table)
    t.emit("srli x6, x6, 12")
    t.emit("slli x6, x6, 10")
    t.emit("ori x6, x6, 1")
    t.emit("mv x9, x6")
    pt.pte_addr(va, pt.levels - 2)
    t.emit("SREG x9, 0(x8)")


def cur_asid(t: SvTest, xlen: int, reg: str) -> None:
    """reg = satp.ASID."""
    t.emit(f"csrr {reg}, satp")
    if xlen == 64:
        t.emit(f"slli {reg}, {reg}, 4")
        t.emit(f"srli {reg}, {reg}, 48")
    else:
        t.emit(f"srli {reg}, {reg}, 22")
        t.emit(f"andi {reg}, {reg}, 0x1FF")


SFENCE_FORMS = {
    "x0,x0": "sfence.vma x0, x0",
    "va,x0": "sfence.vma x6, x0",
    "x0,asid": "sfence.vma x0, x9",
    "va,asid": "sfence.vma x6, x9",
}


def fence_form(t: SvTest, xlen: int, form: str, va: int, asid_reg: str = "x9") -> None:
    """Emit SFENCE.VMA of `form`; x6 = va and x9 = the current ASID when used."""
    if "va" in form:
        t.emit(f"li x6, {hex(va)}")
    if "asid" in form and asid_reg == "x9":
        cur_asid(t, xlen, "x9")
    t.emit(SFENCE_FORMS[form])


def gen_sfence() -> list[SvTest]:
    tests = []
    pages = ("A", "B", "C", "D")

    def mk(rule: str, text: str, context: str, plan: str) -> SvTest:
        t = new("Sv", rule)
        t.describe(source=SUP, rule_text=text, context=context, plan=plan)
        for n in pages:
            t.page(n)
        return t

    def ids(t: SvTest) -> dict:
        return {n: t.page_id(n) for n in pages}

    stale_note = (
        "Without a fence an address-translation cache may still hold the old translation, so a read "
        "between the PTE change and the fence may return the old or the new page; after the fence only "
        "the new one is legal. "
    )

    # ---- sfence_vma_op
    t = mk(
        "sfence_vma_op",
        "The supervisor memory-management fence instruction SFENCE.VMA is used to synchronize updates to in-memory "
        "memory-management data structures with current execution. Instruction execution causes implicit reads "
        "and writes to these data structures; however, these implicit references are ordinarily not ordered with "
        "respect to explicit loads and stores.",
        stale_note + "Sv39 (RV64) or Sv32 (RV32), probed.",
        "VA -> A, read A. Store a new leaf VA -> B: lw reads A or B. SFENCE.VMA x0, x0: lw reads B, a sw lands in B, "
        "and a fetch runs B's stub.",
    )

    def op_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = pt.va_t + 0x20000
            p = ids(t)
            pt.leaf(va, t.page("A"), LEAF)
            pt.on()
            s_load(t, va, p["A"], "before the change")
            pt.leaf(va, t.page("B"), LEAF)
            s_load_any(t, va, [p["A"], p["B"]], "after the PTE store, no fence")
            t.emit(SFENCE)
            s_load(t, va, p["B"] if MUT != "fence_noop" else p["A"], "after SFENCE.VMA x0, x0")
            access(t, pt, "S", "store", va, True, "sw after the fence", page="ai_pg_B")
            access(t, pt, "S", "fetch", va, True, "fetch after the fence", page="ai_pg_B")

        with_vm(t, xlen, inner)

    both(t, op_body)
    tests.append(t)

    # ---- sfence_vma_ordering
    t = mk(
        "sfence_vma_ordering",
        "Executing an SFENCE.VMA instruction guarantees that any previous stores already visible to the current "
        "RISC-V hart are ordered before certain implicit references by subsequent instructions in that hart to the "
        "memory-management data structures. The specific set of operations ordered by SFENCE.VMA is determined by "
        "rs1 and rs2, as described below.",
        stale_note + "Each form covers a leaf PTE of the current address space (non-global): rs1 = the VA, rs2 = "
        "the current ASID (as read from satp).",
        "For each of the four rs1/rs2 forms: change the leaf of VA to the next page, read (old or new), fence with "
        "that form, read: the new page.",
    )

    def ord_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = pt.va_t + 0x21000
            p = ids(t)
            pt.leaf(va, t.page("A"), LEAF)
            pt.on(asid=1)
            s_load(t, va, p["A"], "initial")
            prev = "A"
            for i, form in enumerate(SFENCE_FORMS):
                nxt = pages[(i + 1) % 4]
                pt.leaf(va, t.page(nxt), LEAF)
                s_load_any(t, va, [p[prev], p[nxt]], f"before SFENCE.VMA {form}")
                fence_form(t, xlen, form, va)
                exp = p[nxt] if not (MUT == "va_fence_ignored" and "va" in form) else p[prev]
                s_load(t, va, exp, f"after SFENCE.VMA {form}")
                prev = nxt

        with_vm(t, xlen, inner)

    both(t, ord_body)
    tests.append(t)

    # ---- sfence_vma_invalidation
    t = mk(
        "sfence_vma_invalidation",
        "SFENCE.VMA is also used to invalidate entries in the address-translation cache associated with a hart "
        "(see <<sv32algorithm>>).",
        stale_note + "Valid-to-invalid and invalid-to-valid changes both need the fence.",
        "1. VA -> A, read. Clear V: lw reads A or faults; after SFENCE.VMA x0,x0: page fault (13, xtval 0 or VA).\n"
        "2. Set V again: lw reads A or faults; after SFENCE.VMA x6 (=VA), x0: reads A.\n"
        "3. Same with a superpage leaf and SFENCE.VMA x0, x0.",
    )

    def inv_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            p = ids(t)
            for level, va in ((0, pt.va_t + 0x22000), (1, sp_va(pt.scheme, 1))):
                pt.leaf(va, t.page("A"), LEAF, level=level)
                pt.on()
                lab = access(t, pt, "S", "load", va, True, f"level {level}: valid", page="ai_pg_A", level=level)
                pt.modify(va, pt.depth(level), clear_bits=V, note="V=0")
                if level == 0:
                    s_load_any(t, va, [p["A"], "fault"], "V cleared, no fence")
                t.emit(SFENCE)
                access(
                    t,
                    pt,
                    "S",
                    "load",
                    va,
                    MUT == "invalid_kept",
                    f"level {level}: invalid after the fence",
                    page="ai_pg_A",
                    level=level,
                )
                pt.modify(va, pt.depth(level), set_bits=V, note="V=1")
                if level == 0:
                    s_load_any(t, va, [p["A"], "fault"], "V set, no fence")
                t.emit(f"li x6, {hex(va)}")
                t.emit("sfence.vma x6, x0")
                access(
                    t,
                    pt,
                    "S",
                    "load",
                    va,
                    True,
                    f"level {level}: valid again after the fence",
                    page="ai_pg_A",
                    level=level,
                )
                satp_off(t)
            del lab

        with_vm(t, xlen, inner)

    both(t, inv_body)
    tests.append(t)

    # ---- two-ASID helpers
    def two_roots(t: SvTest, pa: SvPT) -> SvPT:
        pb = SvPT(t, f"b{pa.xlen}", pa.scheme)
        pb.identity()
        return pb

    # ---- sfence_vma_all_asid_va
    t = mk(
        "sfence_vma_all_asid_va",
        "If rs1=x0 and rs2=x0, the fence orders all reads and writes made to any level of the page tables, for all "
        "address spaces. The fence also invalidates all address-translation cache entries, for all address "
        "spaces.",
        stale_note + "A second root (ASID 2) is used only when ASIDLEN >= 2. Non-leaf changes repoint a pointer PTE "
        "at a spare leaf table.",
        "1. Non-leaf: VA -> A through leaf table T1; repoint to T2 (VA -> B): old or new; SFENCE.VMA x0,x0: B.\n"
        "2. Global leaf VA_G -> A (G=1) changed to B: after the fence, B.\n"
        "3. Other address space: with ASID 2 read VA2 -> A; switch to ASID 1; change ASID 2's leaf to B; "
        "SFENCE.VMA x0,x0 in ASID 1; switch to ASID 2 without a fence: B.",
    )

    def all_body(xlen: int) -> None:
        def inner(pa: SvPT) -> None:
            p = ids(t)
            vb = bva(pa.scheme)
            vg = pa.va_t + 0x23000
            v2 = pa.va_t + 0x24000
            pa.leaf(vb, t.page("A"), LEAF)
            t2 = alt_table(t, pa, vb, "ai_pg_B", f"alt{xlen}")
            pa.leaf(vg, t.page("A"), LEAF | G)
            pb = two_roots(t, pa)
            pb.leaf(v2, t.page("A"), LEAF)
            asids_distinct(t, pa, "x9")
            scratch(t, 0, "x9", True)
            pa.on(asid=1)
            s_load(t, vb, p["A"], "non-leaf: before")
            repoint(t, pa, vb, t2)
            s_load_any(t, vb, [p["A"], p["B"]], "non-leaf changed, no fence")
            t.emit(SFENCE)
            s_load(t, vb, p["B"] if MUT != "fence_leaf_only" else p["A"], "non-leaf changed, after x0,x0")
            s_load(t, vg, p["A"], "global: before")
            pa.leaf(vg, t.page("B"), LEAF | G)
            t.emit(SFENCE)
            s_load(t, vg, p["B"], "global changed, after x0,x0")

            def other() -> None:
                pb.on(asid=2, fence=False)
                s_load(t, v2, p["A"], "ASID 2: before")
                pa.on(asid=1, fence=False)
                pb.leaf(v2, t.page("B"), LEAF)
                t.emit(SFENCE)
                pb.on(asid=2, fence=False)
                s_load(
                    t,
                    v2,
                    p["B"] if MUT != "fence_current_asid_only" else p["A"],
                    "ASID 2's leaf changed, fenced from ASID 1",
                )

            scratch(t, 0, "x1", False)
            guard(t, "x1", other)

        with_vm(t, xlen, inner)

    both(t, all_body)
    tests.append(t)

    # ---- sfence_vma_asid_only
    t = mk(
        "sfence_vma_asid_only",
        "If rs1=x0 and rs2!=x0, the fence orders all reads and writes made to any level of the page tables, but "
        "only for the address space identified by integer register rs2. Accesses to _global_ mappings (see "
        "<<translation>>) are not ordered. The fence also invalidates all address-translation cache entries "
        "matching the address space identified by integer register rs2, except for entries containing global "
        "mappings.",
        stale_note + "rs2 holds the current ASID as read from satp (ASID 1, or 0 if ASIDLEN = 0).",
        "1. Leaf change of a non-global page: after SFENCE.VMA x0, rs2: new page.\n"
        "2. Non-leaf change (repointed leaf table), an executable page remapped (fetch), and a superpage leaf "
        "changed: after the same fence, the new pages.\n"
        "3. Global leaf change: after SFENCE.VMA x0, rs2: old or new; after SFENCE.VMA x0, x0: new.",
    )

    def asid_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            p = ids(t)
            va, vg, vb = pt.va_t + 0x25000, pt.va_t + 0x26000, bva(pt.scheme)
            pt.leaf(va, t.page("A"), LEAF)
            pt.leaf(vg, t.page("A"), LEAF | G)
            pt.leaf(vb, t.page("A"), LEAF)
            t2 = alt_table(t, pt, vb, "ai_pg_C", f"alt{xlen}")
            vx, vs = pt.va_t + 0x33000, sp_va(pt.scheme, 1)
            pt.leaf(vx, t.page("A"), LEAF)
            pt.leaf(vs, t.page("A"), LEAF, level=1)
            pt.on(asid=1)
            for v in (va, vg, vb):
                s_load(t, v, p["A"], "before")
            access(t, pt, "S", "fetch", vx, True, "fetch before", page="ai_pg_A")
            access(t, pt, "S", "load", vs, True, "superpage before", page="ai_pg_A", level=1)
            pt.leaf(va, t.page("B"), LEAF)
            pt.leaf(vg, t.page("B"), LEAF | G)
            pt.leaf(vx, t.page("D"), LEAF)
            pt.leaf(vs, t.page("B"), LEAF, level=1)
            repoint(t, pt, vb, t2)
            fence_form(t, xlen, "x0,asid", 0)
            s_load(t, va, p["B"] if MUT != "asid_fence_ignored" else p["A"], "leaf, after SFENCE.VMA x0, asid")
            s_load(t, vb, p["C"], "non-leaf, after SFENCE.VMA x0, asid")
            access(t, pt, "S", "fetch", vx, True, "fetch after SFENCE.VMA x0, asid", page="ai_pg_D")
            access(t, pt, "S", "load", vs, True, "superpage after SFENCE.VMA x0, asid", page="ai_pg_B", level=1)
            s_load_any(t, vg, [p["A"], p["B"]], "global, after SFENCE.VMA x0, asid")
            t.emit(SFENCE)
            s_load(t, vg, p["B"], "global, after SFENCE.VMA x0, x0")

        with_vm(t, xlen, inner)

    both(t, asid_body)
    tests.append(t)

    # ---- sfence_vma_va_all_asid
    t = mk(
        "sfence_vma_va_all_asid",
        "If rs1!=x0 and rs2=x0, the fence orders only reads and writes made to leaf page table entries "
        "corresponding to the virtual address in rs1, for all address spaces. The fence also invalidates all "
        "address-translation cache entries that contain leaf page table entries corresponding to the virtual "
        "address in rs1, for all address spaces.",
        stale_note + "rs1 is an address inside the page (offset 0x123). Another address space (ASID 2) is used "
        "when ASIDLEN >= 2.",
        "1. Leaf change of VA1 and VA2: after SFENCE.VMA VA1, x0: VA1 reads the new page, VA2 old or new.\n"
        "2. Global leaf change: after SFENCE.VMA VA, x0: new.\n"
        "3. Superpage leaf change: after SFENCE.VMA (an address inside it), x0: new.\n"
        "4. ASID 2's leaf for VA3 changed while in ASID 1, SFENCE.VMA VA3, x0, switch to ASID 2 (no fence): new.",
    )

    def vaall_body(xlen: int) -> None:
        def inner(pa: SvPT) -> None:
            p = ids(t)
            v1, v2, vg, v3 = (pa.va_t + o for o in (0x27000, 0x28000, 0x29000, 0x2A000))
            vs = sp_va(pa.scheme, 1)
            for v in (v1, v2):
                pa.leaf(v, t.page("A"), LEAF)
            pa.leaf(vg, t.page("A"), LEAF | G)
            pa.leaf(vs, t.page("A"), LEAF, level=1)
            pb = two_roots(t, pa)
            pb.leaf(v3, t.page("A"), LEAF)
            asids_distinct(t, pa, "x9")
            scratch(t, 0, "x9", True)
            pa.on(asid=1)
            for v in (v1, v2, vg):
                s_load(t, v, p["A"], "before")
            access(t, pa, "S", "load", vs, True, "superpage before", page="ai_pg_A", level=1)
            for v in (v1, v2):
                pa.leaf(v, t.page("B"), LEAF)
            t.emit(f"li x6, {hex(v1 + 0x123)}")
            t.emit("sfence.vma x6, x0")
            s_load(t, v1, p["B"] if MUT != "va_fence_ignored" else p["A"], "fenced VA")
            s_load_any(t, v2, [p["A"], p["B"]], "other VA (not fenced)")
            pa.leaf(vg, t.page("B"), LEAF | G)
            t.emit(f"li x6, {hex(vg + 0x123)}")
            t.emit("sfence.vma x6, x0")
            s_load(t, vg, p["B"] if MUT != "va_fence_skips_global" else p["A"], "global, fenced VA")
            pa.leaf(vs, t.page("B"), LEAF, level=1)
            t.la("x6", "ai_pg_B")
            t.emit(f"li x7, {hex(sp_size(pa.scheme, 1) - 1)}")
            t.emit("and x6, x6, x7")
            t.emit(f"li x7, {hex(vs)}")
            t.emit("add x6, x6, x7")
            t.emit("sfence.vma x6, x0")
            access(
                t, pa, "S", "load", vs, True, "superpage changed, fenced by an inner address", page="ai_pg_B", level=1
            )

            def other() -> None:
                pb.on(asid=2, fence=False)
                s_load(t, v3, p["A"], "ASID 2: before")
                pa.on(asid=1, fence=False)
                pb.leaf(v3, t.page("B"), LEAF)
                t.emit(f"li x6, {hex(v3)}")
                t.emit("sfence.vma x6, x0")
                pb.on(asid=2, fence=False)
                s_load(t, v3, p["B"], "ASID 2's leaf changed, SFENCE.VMA VA, x0 from ASID 1")

            scratch(t, 0, "x1", False)
            guard(t, "x1", other)

        with_vm(t, xlen, inner)

    both(t, vaall_body)
    tests.append(t)

    # ---- sfence_vma_va_asid
    t = mk(
        "sfence_vma_va_asid",
        "If rs1!=x0 and rs2!=x0, the fence orders only reads and writes made to leaf page table entries "
        "corresponding to the virtual address in rs1, for the address space identified by integer register rs2. "
        "Accesses to global mappings are not ordered. The fence also invalidates all address-translation cache "
        "entries that contain leaf page table entries corresponding to the virtual address in rs1 and that match "
        "the address space identified by integer register rs2, except for entries containing global mappings.",
        stale_note + "rs2 holds the current ASID read from satp.",
        "1. Leaf change of VA1 and VA2: after SFENCE.VMA VA1, asid: VA1 new, VA2 old or new.\n"
        "2. Global leaf change: after SFENCE.VMA VA, asid: old or new; after SFENCE.VMA x0, x0: new.",
    )

    def vaasid_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            p = ids(t)
            v1, v2, vg = (pt.va_t + o for o in (0x2B000, 0x2C000, 0x2D000))
            for v in (v1, v2):
                pt.leaf(v, t.page("A"), LEAF)
            pt.leaf(vg, t.page("A"), LEAF | G)
            pt.on(asid=1)
            for v in (v1, v2, vg):
                s_load(t, v, p["A"], "before")
            for v in (v1, v2):
                pt.leaf(v, t.page("B"), LEAF)
            pt.leaf(vg, t.page("B"), LEAF | G)
            fence_form(t, xlen, "va,asid", v1 + 0x10)
            s_load(t, v1, p["B"] if MUT != "va_fence_ignored" else p["A"], "fenced VA")
            s_load_any(t, v2, [p["A"], p["B"]], "other VA")
            fence_form(t, xlen, "va,asid", vg)
            s_load_any(t, vg, [p["A"], p["B"]], "global, SFENCE.VMA VA, asid")
            t.emit(SFENCE)
            s_load(t, vg, p["B"], "global after SFENCE.VMA x0, x0")

        with_vm(t, xlen, inner)

    both(t, vaasid_body)
    tests.append(t)

    # ---- sfence_vma_invalid_va
    t = mk(
        "sfence_vma_invalid_va",
        "If the value held in rs1 is not a valid virtual address, then the SFENCE.VMA instruction has no effect. No "
        "exception is raised in this case.",
        "RV64, Sv39 active (probed): values whose bits 63:39 do not all equal bit 38 are not valid Sv39 VAs. "
        "Over-fencing is always legal, so only the absence of an exception is observable. On RV32 every value is a "
        "valid Sv32 VA, so the file checks RV64 only.",
        "SFENCE.VMA with rs1 = 2^63 | VA, 2^39 | VA and ~2^38 (non-canonical), rs2 = x0 and rs2 = ASID: no trap; "
        "afterwards the mapped page still reads correctly.",
    )

    def invva_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = pt.va_t + 0x2E000
            pt.leaf(va, t.page("A"), LEAF)
            pt.on(asid=1)
            for bad in ((1 << 63) | va, (1 << 39) | va, ((1 << 64) - 1) ^ (1 << 38)):
                for rs2 in ("x0", "x9"):
                    t.emit(f"li x6, {hex(bad)}")
                    t.emit("li x9, 1")
                    win(
                        t,
                        None,
                        "S",
                        [f"sfence.vma x6, {rs2}"],
                        "ok" if MUT != "invalid_va_traps" else LOAD_PF,
                        f"sfence.vma {hex(bad)}, {rs2}",
                        tval=[0, bad],
                    )
            s_load(t, va, t.page_id("A"), "translation still works")

        with_vm(t, xlen, inner)

    with t.rv64_only():
        invva_body(64)
    tests.append(t)

    # ---- sfence_vma_rs2_bits
    t = mk(
        "sfence_vma_rs2_bits",
        "When rs2!=x0, bits SXLEN-1:ASIDMAX of the value held in rs2 are reserved for future standard use. Until "
        "their use is defined by a standard extension, they should be zeroed by software and ignored by current "
        "implementations. Furthermore, if ASIDLEN<ASIDMAX, the implementation shall ignore bits "
        "ASIDMAX-1:ASIDLEN of the value held in rs2.",
        stale_note + "satp.ASID = 1 (or 0 if ASIDLEN = 0); m = the implemented ASID bits (all-ones probe). A fence "
        "whose rs2 is compared unmasked would not match the current ASID and would leave the stale translation. "
        'Ignoring bits ASIDMAX-1:ASIDLEN is required ("shall"); ignoring bits SXLEN-1:ASIDMAX is worded as a '
        'recommendation ("should be zeroed by software and ignored by current implementations"), so with '
        "those bits set the old translation is also accepted.",
        "For each rs2 = ASID | extra, with extra = the unimplemented bits ASIDMAX-1:ASIDLEN, the reserved bits "
        "SXLEN-1:ASIDMAX, and both (= ~m): change VA's non-global leaf to the next page (read: old or new), "
        "SFENCE.VMA x0, rs2 and again with SFENCE.VMA VA, rs2: with only unimplemented bits set, the new page; "
        "with reserved bits set, the new page or (by the recommendation's latitude) the old one, then the new "
        "page after SFENCE.VMA x0, x0.",
    )

    def rs2_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            p = ids(t)
            va = pt.va_t + 0x2F000
            amax = 0xFFFF if xlen == 64 else 0x1FF
            pt.leaf(va, t.page("A"), LEAF)
            asid_probe(t, pt, "x9")
            scratch(t, 8, "x9", True)  # m
            pt.on(asid=1)
            s_load(t, va, p["A"], "before")
            prev = "A"
            i = 0
            for extra in ("reserved", "unimplemented", "both"):
                for form in ("x0", "va"):
                    i += 1
                    nxt = pages[i % 4]
                    pt.leaf(va, t.page(nxt), LEAF)
                    s_load_any(t, va, [p[prev], p[nxt]], f"before SFENCE.VMA {form}, ASID|{extra}")
                    cur_asid(t, xlen, "x9")
                    scratch(t, 8, "x7", False)
                    t.emit("not x7, x7  // ~m")
                    if extra == "reserved":
                        t.emit(f"li x8, {hex(amax)}")
                        t.emit("not x8, x8")
                        t.emit("and x7, x7, x8")
                    elif extra == "unimplemented":
                        t.emit(f"li x8, {hex(amax)}")
                        t.emit("and x7, x7, x8")
                    t.emit("or x9, x9, x7  // ASID | extra")
                    t.emit(f"li x6, {hex(va)}")
                    t.emit(f"sfence.vma {'x0' if form == 'x0' else 'x6'}, x9")
                    if extra == "unimplemented":
                        exp = p[nxt] if MUT != "rs2_unmasked" else p[prev]
                        s_load(t, va, exp, f"after SFENCE.VMA {form}, ASID|{extra} bits")
                    else:
                        # "should be ... ignored by current implementations": a recommendation, so a hart that
                        # compares them may keep the stale translation
                        s_load_any(t, va, [p[nxt], p[prev]], f"after SFENCE.VMA {form}, ASID|{extra} bits")
                        t.emit(SFENCE)
                        s_load(t, va, p[nxt], "after SFENCE.VMA x0, x0")
                    prev = nxt

        with_vm(t, xlen, inner)

    both(t, rs2_body)
    tests.append(t)

    # ---- sfence_vma_ordering_semantics
    t = mk(
        "sfence_vma_ordering_semantics",
        "An implicit read of the memory-management data structures may return any translation for an address that "
        "was valid at any time since the most recent SFENCE.VMA that subsumes that address. The ordering implied "
        "by SFENCE.VMA does not place implicit reads and writes to the memory-management data structures into the "
        "global memory order in a way that interacts cleanly with the standard RVWMO ordering rules. In "
        "particular, even though an SFENCE.VMA orders prior explicit accesses before subsequent implicit "
        "accesses, and those implicit accesses are ordered before their associated explicit accesses, "
        "SFENCE.VMA does not necessarily place prior explicit accesses before subsequent explicit accesses in the "
        "global memory order. These implicit loads also need not otherwise obey normal program order semantics "
        "with respect to prior loads or stores to the same address.",
        "The legal results are exactly the translations valid since the last subsuming fence: never a page that "
        "was not mapped in that interval.",
        "1. VA -> A (fenced, read), then -> B, then -> C without a fence: lw reads A, B or C. SFENCE.VMA VA: C.\n"
        "2. VA invalid (fenced), then -> A, then -> B: lw faults or reads A or B. SFENCE.VMA x0, x0: B.",
    )

    def sem_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            p = ids(t)
            va = pt.va_t + 0x30000
            pt.leaf(va, t.page("A"), LEAF)
            pt.on()
            s_load(t, va, p["A"], "fenced")
            pt.leaf(va, t.page("B"), LEAF)
            s_load_any(t, va, [p["A"], p["B"]], "after the first change")
            pt.leaf(va, t.page("C"), LEAF)
            vals = [p["A"], p["B"], p["C"]] if MUT != "only_latest_two" else [p["B"], p["C"]]
            s_load_any(t, va, vals, "after the second change")
            t.emit(f"li x6, {hex(va)}")
            t.emit("sfence.vma x6, x0")
            s_load(t, va, p["C"], "after the fence")
            pt.leaf(va, t.page("A"), LEAF & ~V)
            t.emit(SFENCE)
            pt.leaf(va, t.page("A"), LEAF)
            pt.leaf(va, t.page("B"), LEAF)
            s_load_any(t, va, [p["A"], p["B"], "fault"], "invalid, then A, then B")
            t.emit(SFENCE)
            s_load(t, va, p["B"], "after the fence")

        with_vm(t, xlen, inner)

    both(t, sem_body)
    tests.append(t)

    # ---- sfence_vma_implicit_access
    t = mk(
        "sfence_vma_implicit_access",
        "Implementations must only perform implicit reads of the translation data structures pointed to by the "
        "current contents of the satp register or a subsequent valid (V=1) translation data structure entry, and "
        "must only raise exceptions for implicit accesses that are generated as a result of instruction "
        "execution, not those that are performed speculatively.",
        "An invalid pointer PTE holds a PPN outside physical memory (2^50 on RV64, 2^33 on RV32): reading through "
        "it would raise an access fault; following only valid entries raises a page fault. Instructions that are "
        "skipped by a branch or jump never trap, whatever their address would do.",
        "1. Pointer PTE with V=0 and an out-of-memory PPN: lw, sw and a fetch raise page faults (13, 15, 12), not "
        "access faults.\n"
        "2. A taken branch skips a lw, a sw and a jalr to that unmapped VA, and a jump skips the same: no trap.\n"
        "3. A valid mapping beside it still reads its page.",
    )

    def imp_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            vb = bva(pt.scheme)
            far = (1 << 50) if xlen == 64 else (1 << 33)
            vb2 = vb + sp_size(pt.scheme, 1)
            pt.leaf(vb2, t.page("A"), LEAF)
            pt.raw(vb, ((far >> 12) << 10) | RWX, level=1, note="V=0 pointer slot with an out-of-memory PPN")
            pt.on()
            for kind in ("load", "store", "fetch"):
                access(
                    t,
                    pt,
                    "S",
                    kind,
                    vb,
                    [AF[kind]] if MUT == "implicit_access_fault" else False,
                    f"{kind} through an invalid pointer",
                )
            t.emit(f"li x6, {hex(vb)}")
            win(
                t,
                None,
                "S",
                [
                    "li x7, 1",
                    "bnez x7, 1f",
                    "lw x8, 0(x6)",
                    "sw x8, 0(x6)",
                    "jalr x1, 0(x6)",
                    "1:",
                    "j 2f",
                    "lw x8, 0(x6)",
                    "jalr x1, 0(x6)",
                    "2:",
                ],
                "ok",
                "skipped accesses to an unmapped VA",
            )
            s_load(t, vb2, t.page_id("A"), "valid mapping beside it")

        with_vm(t, xlen, inner)

    both(t, imp_body)
    tests.append(t)

    # ---- sfence_vma_mode_effect
    t = mk(
        "sfence_vma_mode_effect",
        "Changing satp.MODE from Bare to other modes and vice versa also takes effect immediately, without the need "
        "to execute an SFENCE.VMA instruction.",
        "The VA is mapped only by the table; as a physical address it is not page A (bare_not: access fault or "
        "other data).",
        "1. Bare -> Sv39/Sv32 (no fence): the next lw of the VA reads A.\n"
        "2. -> Bare (no fence): the next lw of the VA is not translated.\n"
        "3. -> Sv39/Sv32 again (no fence): A.",
    )

    def mode_eff_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = pt.va_t + 0x31000
            pt.leaf(va, t.page("A"), LEAF)
            t.emit(SFENCE)
            for i in range(2):
                pt.on(fence=False)
                s_load(t, va, t.page_id("A"), f"Bare -> paged ({i + 1})")
                if i == 0:
                    t.emit("csrw satp, x0")
                    if MUT == "mode_needs_fence":
                        s_load(t, va, t.page_id("A"), "paged -> Bare (mutant: still translated)")
                    else:
                        bare_not(t, va, [t.page_id("A")], "paged -> Bare")

        with_vm(t, xlen, inner)

    both(t, mode_eff_body)
    tests.append(t)

    # ---- sfence_vma_asid_effect
    t = mk(
        "sfence_vma_asid_effect",
        "Likewise, changes to satp.ASID take effect immediately.",
        "Two roots map the same VA to A (ASID 1) and B (ASID 2). Checked when ASIDLEN >= 2. The fence after the "
        "tables were built is the last one.",
        "satp = root 1, ASID 1: A. satp = root 2, ASID 2 (no fence): B. Back to ASID 1 (no fence): A. Again ASID 2: B.",
    )

    def asid_eff_body(xlen: int) -> None:
        def inner(pa: SvPT) -> None:
            va = pa.va_t + 0x32000
            pb = two_roots(t, pa)
            pa.leaf(va, t.page("A"), LEAF)
            pb.leaf(va, t.page("B"), LEAF)
            asids_distinct(t, pa, "x1")

            def run() -> None:
                pa.on(asid=1)
                s_load(t, va, t.page_id("A"), "ASID 1")
                for pt, asid, pg in ((pb, 2, "B"), (pa, 1, "A"), (pb, 2, "B")):
                    pt.on(asid=asid, fence=False)
                    want = pg if MUT != "asid_needs_fence" else ("B" if pg == "A" else "A")
                    s_load(t, va, t.page_id(want), f"right after switching to ASID {asid}")

            guard(t, "x1", run)

        with_vm(t, xlen, inner)

    both(t, asid_eff_body)
    tests.append(t)
    return tests


def sch_test(rule: str, scheme: str, text: str, context: str, plan: str, req: list | None = None) -> SvTest:
    t = new("Sv", rule, req or ["I", "S", EXT[scheme]], rv64=True)
    t.describe(source=SUP, rule_text=text, context=context, plan=plan)
    return t


def sch_run(t: SvTest, scheme: str, inner, user: bool = False) -> None:  # noqa: ANN001
    """Run inner(pt) with an identity table of `scheme` (required by the file, so not probed)."""
    with_vm(t, 64, inner, user=user, scheme=scheme, guarded=False, name=f"s{scheme}")


def gen_schemes() -> list[SvTest]:
    tests = []
    for sch in ("sv39", "sv48", "sv57"):
        tests += gen_scheme(sch)
    tests += gen_sv39_rsv()
    return tests


def gen_scheme(sch: str) -> list[SvTest]:
    tests = []
    S = EXT[sch]
    N = VABITS[sch]
    levels = len(GEO[sch])
    ctx = f"RV64 only (the file passes trivially on RV32); requires {S}, so satp.MODE={MODE[sch]} is used without a probe. "

    # ---- va sign extension
    t = sch_test(
        f"{S}_va_signext",
        sch,
        f"[Instruction fetch addresses and load and store effective addresses, which are 64 bits,] must have "
        f"bits 63-{N} all equal to bit {N - 1}, or else a page-fault exception will occur",
        ctx + "The canonical pages are mapped (VA_T and the top page 2^64-4 KiB), so a check that looks only "
        "at the mapping would succeed on the non-canonical aliases.",
        f"Non-canonical VAs: VA_T with bit {N}, {N + 1 if N < 63 else N}, 62 or 63 set; the top page with "
        f"bit {N - 1}, bit {N} or bit 63 cleared. Each: S-mode lw, sw and fetch and U-mode lw raise page "
        "faults (13, 15, 12) with xtval 0 or the full address. The canonical VA_T and top page read their "
        "pages from S-mode (and the top page from U-mode).",
    )
    t.page("P")
    t.page("Q")

    def se_body(pt: SvPT) -> None:
        va, top = pt.va_t + 0x40000, (1 << 64) - 0x1000
        pt.leaf(va, t.page("P"), LEAF)
        pt.leaf(top, t.page("Q"), ULEAF)
        pt.on()
        s_load(t, va, t.page_id("P"), "canonical VA_T")
        access(t, pt, "U", "load", top, True, "canonical top page", page="ai_pg_Q")
        bad = [va | (1 << b) for b in sorted({N, min(N + 1, 63), 62, 63})]
        bad += [top & ~(1 << b) for b in (N - 1, N, 63)]
        for v in bad:
            ok = MUT == "va_upper_ignored" and v & ((1 << 64) - (1 << N)) not in (0, (1 << 64) - (1 << N))
            for mode, kind in (("S", "load"), ("S", "store"), ("S", "fetch"), ("U", "load")):
                access(t, pt, mode, kind, v, ok, f"non-canonical {hex(v)}")

    sch_run(t, sch, se_body, user=True)
    tests.append(t)

    # ---- vpn width
    t = sch_test(
        f"{S}_vpn_sz",
        sch,
        f"[the] {N - 12}-bit VPN [is translated into a 44-bit PPN]",
        ctx + "Every VPN bit selects a different PTE: VAs that differ from a base VA in one VPN bit map to "
        "other pages. The base VA uses index 0x88 at every level, away from the image's paths.",
        f"Map the base VA to V0 and each VA = base XOR 2^b (b = 12..{N - 1}, sign-extended) to V1/V2/V3 in "
        "turn; lw of every VA reads its own page.",
    )
    for n in ("V0", "V1", "V2", "V3"):
        t.page(n)

    def vpn_body(pt: SvPT) -> None:
        base = canon(bva(sch), N)
        pt.leaf(base, t.page("V0"), LEAF)
        flips = []
        for b in range(12, N):
            v = canon(bva(sch) ^ (1 << b), N)
            pg = f"V{1 + (b % 3)}"
            pt.leaf(v, t.page(pg), LEAF)
            flips.append((b, v, pg))
        pt.on()
        s_load(t, base, t.page_id("V0"), "base VA")
        for b, v, pg in flips:
            want = pg if not (MUT == "vpn_top_bit_ignored" and b == N - 1) else "V0"
            s_load(t, v, t.page_id(want), f"VPN bit {b} flipped")

    sch_run(t, sch, vpn_body)
    tests.append(t)

    # ---- PPN width
    t = sch_test(
        f"satp_ppn_{S}_sz",
        sch,
        "44-bit PPN",
        ctx + f"{S} physical addresses are 56 bits: PTE.PPN is PTE bits 53:10. High PPN bits select physical "
        "addresses far beyond memory, which raise access faults; the algorithm never ignores high PPN bits "
        "(<<sv32algorithm>> note), so these leaves neither page-fault nor alias the page below.",
        "Leaves with P's PPN plus 2^43, 2^38, 2^30 and 2^20 (PA bits 55, 50, 42, 32): lw raises a load access "
        "fault or reads data other than P's signature, never a page fault. P's own leaf reads P.",
    )
    t.page("P")

    def ppn_body(pt: SvPT) -> None:
        va = pt.va_t + 0x41000
        pt.leaf(va, t.page("P"), LEAF)
        for k, bit in enumerate((43, 38, 30, 20), 1):
            pt.leaf(va + k * 0x1000, t.page("P"), LEAF, ppn_add=1 << bit)
        pt.on()
        s_load(t, va, t.page_id("P"), "P's own mapping")
        for k, bit in enumerate((43, 38, 30, 20), 1):
            high_ppn_load(t, va + k * 0x1000, t.page_id("P"), f"PPN bit {bit} (PA bit {bit + 12})")

    sch_run(t, sch, ppn_body)
    tests.append(t)

    # ---- levels
    t = sch_test(
        f"{S}_levels",
        sch,
        {"sv39": "three-level page table", "sv48": "four-level page table", "sv57": "five-level page table"}[sch],
        ctx + "<<sv32algorithm>> with LEVELS = " + str(levels) + ": a walk takes at most LEVELS steps; V=0 at "
        "any level faults; a pointer at the last level faults (i < 0); and in a pointer PTE the D, A and U "
        "bits are reserved, so step 3 faults on them. The path of the base VA is used by nothing else.",
        f"1. A 4 KiB page through all {levels} levels reads its page.\n"
        f"2. V=0 in the PTE at each depth 0..{levels - 1}: lw page-faults (13); restored, it reads again.\n"
        "3. A pointer (R=W=X=0, V=1) at the last level: lw, sw, fetch page-fault.\n"
        "4. A pointer with D, A or U set (each alone, at each non-leaf depth): lw page-faults.",
    )
    t.page("P")

    def lev_body(pt: SvPT) -> None:
        vb = bva(sch)
        vlast = vb + 0x1000
        pt.leaf(vb, t.page("P"), LEAF)
        pt.leaf(vlast, t.page("P"), V)
        pt.on()
        s_load(t, vb, t.page_id("P"), f"{levels}-level walk")
        for d in range(levels):
            pt.modify(vb, d, clear_bits=V, note="V=0")
            t.emit(SFENCE)
            access(t, pt, "S", "load", vb, MUT == "v_ignored_at_root" and d == 0, f"V=0 at depth {d}")
            pt.modify(vb, d, set_bits=V, note="V=1")
            t.emit(SFENCE)
            s_load(t, vb, t.page_id("P"), f"V restored at depth {d}")
        for kind in ("load", "store", "fetch"):
            access(t, pt, "S", kind, vlast, False, "pointer at the last level")
        for d in range(levels - 1):
            for bit, name in ((D, "D"), (A, "A"), (U, "U")):
                pt.modify(vb, d, set_bits=bit, note=f"{name}=1 in a pointer")
                t.emit(SFENCE)
                access(t, pt, "S", "load", vb, MUT == "nonleaf_adu_ignored", f"pointer at depth {d} with {name}=1")
                pt.modify(vb, d, clear_bits=bit)
        t.emit(SFENCE)

    sch_run(t, sch, lev_body)
    tests.append(t)

    # ---- page offset
    t = sch_test(
        f"{S}_page_offset_sz",
        sch,
        "12-bit page offset is untranslated",
        ctx + "The page holds distinct words at offsets 0x8, 0x554, 0xAA8 and 0xFF8.",
        "lw at VA + each offset reads that word of the page; sw at VA + 0x7FC lands at the page's offset 0x7FC.",
    )
    words = {0x8: 0x0BAD_0008, 0x554: 0x0BAD_0554, 0xAA8: 0x0BAD_0AA8, 0xFF8: 0x0BAD_0FF8}
    t.page("P", {o: (4, v) for o, v in words.items()})

    def off_body(pt: SvPT) -> None:
        va = pt.va_t + 0x42000
        pt.leaf(va, t.page("P"), LEAF)
        pt.on()
        for o, v in words.items():
            lab = t.label("off")
            t.emit(f"li x6, {hex(va + o)}")
            t.emit(f"{lab}:", 0)
            t.emit("lw x7, 0(x6)")
            want = v if not (MUT == "offset_11bit" and o >= 0x800) else 0
            t.check("x7", want, lab, f"lw at page offset {hex(o)}")
        access(t, pt, "S", "store", va, True, "sw at offset 0x7FC", page="ai_pg_P", off=0x7FC)

    sch_run(t, sch, off_body)
    tests.append(t)

    # ---- superpages: leaf at any level, page sizes, alignment, misalignment
    sizes = {1: "2 MiB megapage", 2: "1 GiB gigapage", 3: "512 GiB terapage", 4: "256 TiB petapage"}
    sp_levels = range(1, levels)
    t = sch_test(
        f"{S}_leaf_any_level",
        sch,
        "Any level of PTE may be a leaf PTE",
        ctx + "A leaf at level l maps 2^(12+9l) bytes; the access goes to page P's offset inside the "
        "superpage, computed at run time.",
        "A leaf at every level (4 KiB, " + ", ".join(sizes[l] for l in sp_levels) + "): S-mode lw reads P, "
        "sw lands in P, and a fetch runs P's stub.",
    )
    t.page("P")

    def any_body(pt: SvPT) -> None:
        pt.leaf(pt.va_t + 0x43000, t.page("P"), LEAF)
        for lv in sp_levels:
            pt.leaf(sp_va(sch, lv), t.page("P"), LEAF, level=lv)
        pt.on()
        for kind in ("load", "store", "fetch"):
            access(t, pt, "S", kind, pt.va_t + 0x43000, True, f"{kind}: 4 KiB leaf", page="ai_pg_P")
            for lv in sp_levels:
                ok = not (MUT == "no_top_leaf" and lv == levels - 1)
                access(t, pt, "S", kind, sp_va(sch, lv), ok, f"{kind}: leaf at level {lv}", page="ai_pg_P", level=lv)

    sch_run(t, sch, any_body)
    tests.append(t)

    t = sch_test(
        f"{S}_page_sizes",
        sch,
        ", ".join(sizes[l] for l in sp_levels) + " [are supported]",
        ctx + "Two pages P and Q inside the superpage are reached through it at their own offsets; the next "
        "superpage-sized region is not mapped.",
        "For each superpage level: lw at the superpage base + P's offset reads P, + Q's offset reads Q; lw at "
        "base + size page-faults (13).",
    )
    t.page("P")
    t.page("Q")

    def size_body(pt: SvPT) -> None:
        for lv in sp_levels:
            pt.leaf(sp_va(sch, lv), t.page("P"), LEAF, level=lv)
        pt.on()
        for lv in sp_levels:
            for pg in ("P", "Q"):
                access(t, pt, "S", "load", sp_va(sch, lv), True, f"level {lv}: page {pg}", page=f"ai_pg_{pg}", level=lv)
            nxt = sp_va(sch, lv) + sp_size(sch, lv)
            access(t, pt, "S", "load", nxt, MUT == "superpage_double_size", f"level {lv}: base + size is not mapped")

    sch_run(t, sch, size_body)
    tests.append(t)

    t = sch_test(
        f"{S}_superpage_align",
        sch,
        "[superpages] must be virtually and physically aligned to a boundary equal to [their] size",
        ctx + "The leaf's PPN is P's, aligned down to the superpage size, so the physical address is that "
        "boundary plus the VA's offset in the superpage (step 10: pa.ppn[i-1:0] = va.vpn[i-1:0]). The 4 KiB "
        "page just below the superpage's VA is outside it.",
        "For each superpage level: a store through the superpage to P's offset lands in P (physical "
        "alignment); lw of base - 4 KiB page-faults (virtual alignment: it is not part of the superpage).",
    )
    t.page("P")

    def al_body(pt: SvPT) -> None:
        for lv in sp_levels:
            pt.leaf(sp_va(sch, lv), t.page("P"), LEAF, level=lv)
        pt.on()
        for lv in sp_levels:
            access(
                t, pt, "S", "store", sp_va(sch, lv), True, f"level {lv}: store at P's offset", page="ai_pg_P", level=lv
            )
            access(t, pt, "S", "load", sp_va(sch, lv) - 0x1000, False, f"level {lv}: the page below the base")

    sch_run(t, sch, al_body)
    tests.append(t)

    t = sch_test(
        f"{S}_superpage_align_fault",
        sch,
        "A page-fault exception is raised if the physical address is insufficiently aligned",
        ctx + "Step 5: a leaf at level i > 0 with pte.ppn[i-1:0] != 0 is a misaligned superpage. The PPN is "
        "P's aligned PPN plus 1 (ppn[0] bit 0) or 2^(9(i-1)) (the lowest bit of ppn[i-1]).",
        "For each superpage level and each misalignment: S-mode lw, sw and fetch, and U-mode lw (U=1 leaf) "
        "raise page faults (13, 15, 12) with xtval 0 or the address; the store does not write P.",
    )
    t.page("P")

    def mis_body(pt: SvPT) -> None:
        pt.on()
        for lv in sp_levels:
            adds = sorted({1, 1 << (9 * (lv - 1))})
            for add in adds:
                pt.leaf(sp_va(sch, lv), t.page("P"), ULEAF, level=lv, ppn_add=add)
                t.emit(SFENCE)
                ok = MUT == "misaligned_superpage_ok"
                sstatus_bits(t, SUM, True, "SUM")
                for kind in ("load", "store", "fetch"):
                    if kind == "fetch":
                        pt.leaf(sp_va(sch, lv), t.page("P"), LEAF, level=lv, ppn_add=add)
                        t.emit(SFENCE)
                    access(
                        t,
                        pt,
                        "S",
                        kind,
                        sp_va(sch, lv),
                        ok,
                        f"level {lv}, PPN + {hex(add)}: {kind}",
                        page="ai_pg_P",
                        level=lv,
                    )
                pt.leaf(sp_va(sch, lv), t.page("P"), ULEAF, level=lv, ppn_add=add)
                t.emit(SFENCE)
                access(
                    t,
                    pt,
                    "U",
                    "load",
                    sp_va(sch, lv),
                    ok,
                    f"level {lv}, PPN + {hex(add)}: U-mode lw",
                    page="ai_pg_P",
                    level=lv,
                )
                sstatus_bits(t, SUM, False, "SUM")

    sch_run(t, sch, mis_body, user=True)
    tests.append(t)

    # ---- PTESIZE
    t = sch_test(
        f"{S}_ptesize",
        sch,
        "PTESIZE equals 8",
        ctx + "Adjacent entries of one leaf table map adjacent VAs; a reserved bit in the upper half of one "
        "PTE (bit 54) affects only that PTE, and only if the walker reads all 8 bytes.",
        "Map VA+1/+2/+3 pages (entries k, k+1, k+2) to P1, P2, P3: each reads its page. Set bit 54 in the "
        "middle PTE: its lw page-faults; the other two still read their pages.",
    )
    for n in ("P1", "P2", "P3"):
        t.page(n)

    def psz_body(pt: SvPT) -> None:
        vb = bva(sch)
        for k in (1, 2, 3):
            pt.leaf(vb + k * 0x1000, t.page(f"P{k}"), LEAF)
        pt.on()
        for k in (1, 2, 3):
            s_load(t, vb + k * 0x1000, t.page_id(f"P{k}"), f"entry +{k}")
        pt.modify(vb + 0x2000, levels - 1, set_bits=1 << 54, note="reserved bit 54")
        t.emit(SFENCE)
        access(t, pt, "S", "load", vb + 0x2000, MUT == "pte_low_word_only", "bit 54 set in this PTE")
        for k in (1, 3):
            s_load(t, vb + k * 0x1000, t.page_id(f"P{k}"), f"entry +{k} unaffected")

    sch_run(t, sch, psz_body)
    tests.append(t)

    # ---- VA space size (Sv39_sxlen_va_sz, Sv48_va_sz, Sv57_sxlen_va_sz)
    rule = {"sv39": "Sv39_sxlen_va_sz", "sv48": "Sv48_va_sz", "sv57": "Sv57_sxlen_va_sz"}[sch]
    text = {
        "sv39": "This section describes a simple paged virtual-memory system for SXLEN=64, which supports 39-bit "
        "virtual address spaces.",
        "sv48": "48-bit virtual address spaces",
        "sv57": "This section describes a simple paged virtual-memory system designed for RV64 systems, which "
        "supports 57-bit virtual address spaces.",
    }[sch]
    t = sch_test(
        rule,
        sch,
        text,
        ctx + f"The {N}-bit space spans the canonical VAs 0 .. 2^{N - 1}-1 and 2^64-2^{N - 1} .. 2^64-1.",
        "Map the lowest page (VA 0), the highest positive page, the lowest negative page and the highest page "
        "to four pages: each lw reads its page (S-mode).",
    )
    for n in ("L", "H", "NL", "NH"):
        t.page(n)

    def vas_body(pt: SvPT) -> None:
        vaddrs = {"L": 0, "H": (1 << (N - 1)) - 0x1000, "NL": canon(1 << (N - 1), N), "NH": (1 << 64) - 0x1000}
        for n, v in vaddrs.items():
            pt.leaf(v, t.page(n), LEAF)
        pt.on()
        for n, v in vaddrs.items():
            s_load(t, v, t.page_id(n if not (MUT == "va_space_short" and n == "NL") else "NH"), f"VA {hex(v)}")

    sch_run(t, sch, vas_body)
    tests.append(t)

    # ---- dependencies / SXLEN
    if sch in ("sv48", "sv57"):
        dep = "sv39" if sch == "sv48" else "sv48"
        rule = f"{S}_requires_{EXT[dep]}"
        t = sch_test(
            rule,
            sch,
            f"Implementations that support {S} must also support {EXT[dep]}",
            ctx + f"satp is written with MODE={MODE[dep]} and a {EXT[dep]} table that identity-maps the image.",
            f"satp accepts MODE={MODE[dep]} (reads it back), and the {EXT[dep]} table translates a test VA.",
        )
        t.page("P")
        pt = SvPT(t, f"d{dep}", dep)
        pt.identity()
        pt.leaf(pt.va_t + 0x44000, t.page("P"), LEAF)
        satp_val(pt)
        lab = t.label("dep")
        t.emit(f"{lab}:", 0)
        t.emit("csrw satp, x6")
        t.emit("csrr x7, satp")
        t.emit(SFENCE)
        t.emit("srli x7, x7, 60")
        t.check("x7", MODE[dep], lab, f"satp holds MODE={MODE[dep]}")
        s_load(t, pt.va_t + 0x44000, t.page_id("P"), f"{EXT[dep]} translation")
        satp_off(t)
        tests.append(t)
    if sch == "sv48":
        t = sch_test(
            "Sv48_sxlen",
            sch,
            "SXLEN=64",
            ctx + "Sv48 is an SXLEN=64 scheme: satp is MODE[63:60]=9, ASID[59:44], PPN[43:0].",
            "Write satp = 9<<60 | ASID 1 | PPN(root): MODE and PPN read back exactly, ASID 1 or 0; a 4-level "
            "translation through that root reads its page.",
        )
        t.page("P")

        def sx_body(pt: SvPT) -> None:
            pt.leaf(pt.va_t + 0x45000, t.page("P"), LEAF)
            satp_val(pt, asid=1)
            lab = t.label("rt")
            t.emit(f"{lab}:", 0)
            t.emit("csrw satp, x6")
            t.emit("csrr x9, satp")
            t.emit(SFENCE)
            t.load("x8", ~(1 << 44) & ((1 << 64) - 1), "all but ASID bit 0")
            t.emit("and x7, x9, x8")
            t.emit("and x8, x6, x8")
            t.emit("xor x7, x7, x8")
            t.check("x7", 0, lab, "satp MODE=9 and PPN read back")
            s_load(t, pt.va_t + 0x45000, t.page_id("P"), "Sv48 translation")

        sch_run(t, sch, sx_body)
        tests.append(t)
    return tests


def gen_sv39_rsv() -> list[SvTest]:
    tests = []
    ctx = "RV64 only; requires Sv39. "

    def rsv_cases(
        t: SvTest, pt: SvPT, bits: int, note: str, ok: bool = False, pointer: bool = True, leaf4k: bool = True
    ) -> None:
        """Positive control (bits clear), then bits set in a 4 KiB leaf (load/store/fetch), a megapage leaf (load)
        and each pointer on a 4 KiB path (load): page faults."""
        va, vs, vb = pt.va_t + 0x46000, sp_va("sv39", 1), bva("sv39")
        pt.leaf(va, t.page("P"), LEAF)
        pt.leaf(vs, t.page("P"), LEAF, level=1)
        pt.leaf(vb, t.page("P"), LEAF)
        t.emit(SFENCE)
        if leaf4k:
            s_load(t, va, t.page_id("P"), f"{note}: control, 4 KiB leaf with the bits clear")
        access(t, pt, "S", "load", vs, True, f"{note}: control, megapage leaf", page="ai_pg_P", level=1)
        if pointer:
            s_load(t, vb, t.page_id("P"), f"{note}: control, pointer path")
        if leaf4k:
            pt.leaf(va, t.page("P"), LEAF | bits)
        pt.leaf(vs, t.page("P"), LEAF | bits, level=1)
        t.emit(SFENCE)
        for kind in ("load", "store", "fetch") if leaf4k else ():
            access(t, pt, "S", kind, va, ok, f"{note}: 4 KiB leaf, {kind}", page="ai_pg_P")
        access(t, pt, "S", "load", vs, ok, f"{note}: megapage leaf", page="ai_pg_P", level=1)
        if pointer:
            for d in (0, 1):
                pt.modify(vb, d, set_bits=bits, note=f"in the depth-{d} pointer")
                t.emit(SFENCE)
                access(t, pt, "S", "load", vb, ok, f"{note}: depth-{d} pointer", page="ai_pg_P")
                pt.modify(vb, d, clear_bits=bits)
        t.emit(SFENCE)

    t = sch_test(
        "Sv39_pte_future_rsv",
        "sv39",
        "[Bits 60-54 are reserved for future standard use and, until their use is defined by some standard "
        "extension,] must be zeroed by software for forward compatibility. If any of these bits are set, a "
        "page-fault exception is raised",
        ctx + "Svrsw60t59b, when implemented, gives bits 60-59 to software (they are then ignored), so those "
        "two bits are checked only when SVRSW60T59B_SUPPORTED is not defined.",
        "Each of bits 54-58 (and 59, 60 without Svrsw60t59b), alone, in a 4 KiB leaf (lw, sw, fetch), a "
        "megapage leaf, and the root and level-1 pointers of a 4 KiB path: page fault (13/15/12, xtval 0 or "
        "the VA); a faulting sw leaves the page unchanged. Each mapping is first read with the bits clear.",
    )
    t.page("P")

    def fr_body(pt: SvPT) -> None:
        pt.on()
        for b in range(54, 61):
            ok = MUT == "rsv_bit58_ignored" and b == 58
            if b >= 59:
                with t.only_if("!defined(SVRSW60T59B_SUPPORTED)"):
                    rsv_cases(t, pt, 1 << b, f"bit {b}", ok)
            else:
                rsv_cases(t, pt, 1 << b, f"bit {b}", ok)

    sch_run(t, "sv39", fr_body)
    tests.append(t)

    t = sch_test(
        "Sv39_pte_Svpbmt_rsv",
        "sv39",
        "If Svpbmt is not implemented, bits 62-61 remain reserved and must be zeroed by software for forward "
        "compatibility, or else a page-fault exception is raised",
        ctx + "With menvcfg.PBMTE=0 the hart behaves as though Svpbmt were not implemented "
        "(menvcfg_pbmte_op), so the rule applies on every hart once PBMTE is cleared (T-SBI).",
        "menvcfg.PBMTE = 0 and SFENCE.VMA. PBMT = 1, 2, 3 in a 4 KiB leaf (lw, sw, fetch), a megapage leaf "
        "and a pointer: page fault.",
    )
    t.page("P")

    def pb_body(pt: SvPT) -> None:
        menvcfg_bit(t, 64, PBMTE_BIT, False)
        pt.on()
        for v in (1, 2, 3):
            rsv_cases(t, pt, v << 61, f"PBMT={v}, PBMTE=0", MUT == "pbmte_ignored" and v != 3)

    sch_run(t, "sv39", pb_body)
    tests.append(t)

    t = sch_test(
        "Sv39_pte_Svnapot_rsv",
        "sv39",
        "If Svnapot is not implemented, bit 63 remains reserved and must be zeroed by software for forward "
        "compatibility, or else a page-fault exception is raised",
        ctx + "With Svnapot, N=1 is still reserved in pointers and superpage leaves, and in 4 KiB leaves "
        "unless ppn[3:0] = 1000 (Svnapot_enc_tbl), so those cases fault on every hart. The 64 KiB encoding "
        f"must fault only without Svnapot (SVNAPOT_SUPPORTED undefined). {ISSUE}823: N=1 is reserved in "
        "non-leaf PTEs.",
        "1. N=1 in a 4 KiB leaf with ppn[3:0] = 0000 and 0001, a megapage leaf and a pointer: page fault.\n"
        "2. Without Svnapot: N=1, ppn[3:0] = 1000 in a 4 KiB leaf: page fault for lw, sw and fetch.",
    )
    t.page("P")

    def np_body(pt: SvPT) -> None:
        pt.on()
        va = pt.va_t + 0x47000
        for low in (0, 1):
            pt.leaf_napot(va, "ai_pg_P", LEAF | N_BIT, low)
            t.emit(SFENCE)
            access(t, pt, "S", "load", va, False, f"N=1, ppn[3:0]={low:04b}")
        rsv_cases(t, pt, N_BIT, "N=1 (superpage/pointer)", pointer=True, leaf4k=False)
        with t.only_if("!defined(SVNAPOT_SUPPORTED)"):
            pt.leaf_napot(va, "ai_pg_P", LEAF | N_BIT, 0b1000)
            t.emit(SFENCE)
            for kind in ("load", "store", "fetch"):
                access(t, pt, "S", kind, va, False, f"no Svnapot: N=1, ppn[3:0]=1000, {kind}")

    sch_run(t, "sv39", np_body)
    tests.append(t)

    t = sch_test(
        "Sv39_pte_count_sz",
        "sv39",
        "Sv39 page tables contain 2^9 page table entries (PTEs), eight bytes each.",
        ctx + "Entries 0, 1, 255, 256, 510 and 511 of one leaf table, and the paths of VA 0 (entry 0 at every "
        "level) and the top page (entry 511 at every level), map different pages.",
        "lw through each of those entries reads its own page.",
    )
    for n in ("E0", "E1", "E255", "E256", "E510", "E511", "Z", "T"):
        t.page(n)

    def cnt_body(pt: SvPT) -> None:
        base = bva("sv39") & ~(0x1FF << 12)
        vaddrs = {f"E{k}": base | (k << 12) for k in (0, 1, 255, 256, 510, 511)}
        vaddrs["Z"] = 0
        vaddrs["T"] = (1 << 64) - 0x1000
        for n, v in vaddrs.items():
            pt.leaf(v, t.page(n), LEAF)
        pt.on()
        for n, v in vaddrs.items():
            want = n if not (MUT == "pte_index_8bit" and n == "E256") else "E0"
            s_load(t, v, t.page_id(want), f"{n}: VA {hex(v)}")

    sch_run(t, "sv39", cnt_body)
    tests.append(t)
    return tests


ADUE_CTX = (
    f"{ISSUE}3450: there are exactly two A/D schemes, Svade and hardware updating; Svadu only adds "
    'menvcfg.ADUE to choose between them, and ADUE=0 means Svade (aswaterman: "!Svade && Svadu && ADUE=0 '
    '... is actually not legal" as a third behavior).'
)


def adue_set(t: SvTest, xlen: int, on: bool) -> None:
    menvcfg_bit(t, xlen, ADUE_BIT, on)
    t.emit(SFENCE)


def pte_bit_check(t: SvTest, pt: SvPT, va: int, bit: int, want: int, lab: str, desc: str, level: int = 0) -> None:
    pt.read_pte(va, pt.depth(level), "x9")
    t.emit(f"srli x9, x9, {bit.bit_length() - 1}")
    t.emit("andi x9, x9, 1")
    t.check("x9", want, lab, desc)


def gen_ad() -> list[SvTest]:
    tests = []

    # ---- Svade
    t = new("Svade", "Svade_access_ad_bit_clear", ["I", "S", "Svade"])
    t.describe(
        source=SUP,
        rule_text="The _Svade_ extension: when a virtual page is accessed and the A bit is clear, or is written and "
        "the D bit is clear, a page-fault exception is raised.",
        context="Requires Svade. menvcfg.ADUE is cleared first (T-SBI; read-only 0 without Svadu), since with Svadu "
        "and ADUE=1 hardware updating is selected instead. " + ADUE_CTX + " Sv39 (RV64) or Sv32 (RV32), probed.",
        plan="1. A=0 leaf (D=1): S-mode lw, sw, fetch and U-mode lw, sw: page fault (13/15/12, xtval 0 or the VA); "
        "the PTE is unchanged (A stays 0) and the store does not write.\n"
        "2. A=1, D=0 leaf: lw and fetch succeed and D stays 0; sw page-faults (15) and D stays 0.\n"
        "3. A=0 superpage leaf: lw page-faults.",
    )
    t.page("P")

    def ade_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = pt.va_t + 0x50000
            adue_set(t, xlen, False)
            pt.on()
            for mode, kind in (("S", "load"), ("S", "store"), ("S", "fetch"), ("U", "load"), ("U", "store")):
                pt.leaf(va, t.page("P"), (LEAF & ~A) | (U if mode == "U" else 0))
                t.emit(SFENCE)
                ok = MUT == "svade_sets_a"
                lab = access(t, pt, mode, kind, va, ok, f"{mode}-mode {kind}, A=0", page="ai_pg_P")
                pte_bit_check(t, pt, va, A, int(ok), lab, "A unchanged after the fault")
            for kind in ("load", "fetch", "store"):
                pt.leaf(va, t.page("P"), LEAF & ~D)
                t.emit(SFENCE)
                ok = kind != "store" or MUT == "svade_sets_d"
                lab = access(t, pt, "S", kind, va, ok, f"S-mode {kind}, A=1 D=0", page="ai_pg_P")
                pte_bit_check(t, pt, va, D, int(MUT == "svade_sets_d" and kind == "store"), lab, "D stays 0")
            vs = sp_va(pt.scheme, 1)
            pt.leaf(vs, t.page("P"), LEAF & ~A, level=1)
            t.emit(SFENCE)
            access(t, pt, "S", "load", vs, False, "superpage, A=0", page="ai_pg_P", level=1)

        with_vm(t, xlen, inner, user=True)

    both(t, ade_body)
    tests.append(t)

    # ---- Svadu: ADUE writable
    t = new("Svadu", "Svadu_hw_update_a_d_bits", ["I", "S", "Svadu"])
    t.describe(
        source="src/priv/svadu.adoc",
        rule_text="If the Svadu extension is implemented, the menvcfg.ADUE field is writable.",
        context="menvcfg.ADUE is bit 61 (RV32: menvcfgh bit 29), reached through T-SBI.",
        plan="Set ADUE: reads 1. Clear it: reads 0. Set again: reads 1 (then cleared).",
    )

    def adw_body(xlen: int) -> None:
        for v in (1, 0, 1, 0):
            menvcfg_bit(t, xlen, ADUE_BIT, bool(v))
            menvcfg_get(t, xlen, ADUE_BIT, "x7")
            lab = t.label("adue")
            t.emit(f"{lab}:", 0)
            t.check("x7", v if MUT != "adue_ro0" else 0, lab, f"menvcfg.ADUE reads {v}")

    both(t, adw_body)
    tests.append(t)

    t = new("Svadu", "Svadu_hypervisor_adue_writable", ["I", "S", "Svadu", "H"])
    t.describe(
        source="src/priv/svadu.adoc",
        rule_text="If the hypervisor extension is additionally implemented, the henvcfg.ADUE field is also writable.",
        context="Requires H. henvcfg.ADUE (bit 61; RV32 henvcfgh bit 29) is read-only 0 while menvcfg.ADUE=0 "
        "(menvcfg_adue_henvcfg_adue_rdonly0), so menvcfg.ADUE is set first. HS-mode writes henvcfg directly. Known: "
        "QEMU rv32 traps on henvcfgh writes (qemu#4611).",
        plan="menvcfg.ADUE=1. Set henvcfg.ADUE: reads 1; clear: reads 0.",
    )

    def had_body(xlen: int) -> None:
        menvcfg_bit(t, xlen, ADUE_BIT, True)
        csr, b = (0x60A, 61) if xlen == 64 else (0x61A, 29)
        for v in (1, 0):
            t.emit(f"li x6, {hex(1 << b)}")
            t.emit(f"{'csrs' if v else 'csrc'} {hex(csr)}, x6  // henvcfg{'h' if xlen == 32 else ''}.ADUE")
            lab = t.label("hadue")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrr x7, {hex(csr)}")
            t.emit(f"srli x7, x7, {b}")
            t.emit("andi x7, x7, 1")
            t.check("x7", v, lab, f"henvcfg.ADUE reads {v}")
        menvcfg_bit(t, xlen, ADUE_BIT, False)

    both(t, had_body)
    tests.append(t)

    # ---- ADUE behavior
    def upd_cases(t: SvTest, pt: SvPT, va: int, hw: bool, tag: str) -> None:
        """hw: hardware updating expected (ADUE=1); else Svade faults."""
        pg = "ai_pg_P"
        cases = [
            ("S", "load", LEAF & ~(A | D), A, 1),
            ("S", "load", LEAF & ~(A | D), D, 0),
            ("S", "fetch", LEAF & ~(A | D), A, 1),
            ("S", "store", LEAF & ~(A | D), D, 1),
            ("S", "store", LEAF & ~D, D, 1),
            ("U", "load", ULEAF & ~A, A, 1),
            ("U", "store", ULEAF & ~(A | D), D, 1),
        ]
        for mode, kind, pte, bit, set_ in cases:
            pt.leaf(va, t.page("P"), pte)
            t.emit(SFENCE)
            ok = hw if MUT != "adue_store_faults" or kind != "store" else False
            lab = access(t, pt, mode, kind, va, ok, f"{tag}: {mode}-mode {kind}, PTE {hex(pte)}", page=pg)
            want = set_ if ok else 0
            if MUT == "load_sets_d" and kind == "load" and bit == D and ok:
                want = 1
            pte_bit_check(t, pt, va, bit, want, lab, f"{tag}: {'A' if bit == A else 'D'} afterwards")
            if ok and kind == "store":
                pte_bit_check(t, pt, va, A, 1, lab, f"{tag}: a store also sets A")

    t = new("Svadu", "menvcfg_adue_op", ["I", "S", "Svadu"])
    t.describe(
        source=MAC,
        rule_text="If the Svadu extension is implemented, the ADUE bit controls whether hardware updating of PTE A/D "
        "bits is enabled for S-mode and G-stage address translations. When ADUE=1, hardware updating of PTE A/D "
        "bits is enabled during S-mode address translation, and the implementation behaves as though the Svade "
        "extension were not implemented for S-mode address translation. When the hypervisor extension is "
        "implemented, if ADUE=1, hardware updating of PTE A/D bits is enabled during G-stage address translation, "
        "and the implementation behaves as though the Svade extension were not implemented for G-stage address "
        "translation. When ADUE=0, the implementation behaves as though Svade were implemented for S-mode and "
        "G-stage address translation.",
        context="Tested in the Svadu suite because it defines Svadu's behavior. G-stage updating is in the H suite "
        "(henvcfg_adue_op and the G-stage tests). The update scheme (<<translation>>, step 9): A is set by any "
        "access, D by a store; D updates are exact, so a faulting store never sets D; A and D are never cleared. "
        "S-mode translation covers S- and U-mode accesses through satp. " + ADUE_CTX,
        plan="ADUE=1: lw / fetch of an A=0 page succeed and set A (not D); sw of an A=0, D=0 page and of an A=1, D=0 "
        "page succeed and set D and A; U-mode lw and sw likewise; a superpage leaf's A is set; sw to an A=0, D=0 "
        "read-only page page-faults and leaves D=0.\n"
        "ADUE=0: each of the S/U lw, fetch and sw cases page-faults (Svade) and the PTE is unchanged.",
    )
    t.page("P")

    def aduo_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = pt.va_t + 0x51000
            pt.on()
            adue_set(t, xlen, True)
            upd_cases(t, pt, va, True, "ADUE=1")
            vs = sp_va(pt.scheme, 1)
            pt.leaf(vs, t.page("P"), LEAF & ~A, level=1)
            t.emit(SFENCE)
            lab = access(t, pt, "S", "load", vs, True, "ADUE=1: superpage A=0", page="ai_pg_P", level=1)
            pte_bit_check(t, pt, vs, A, 1, lab, "superpage A set", level=1)
            pt.leaf(va, t.page("P"), V | R | U * 0)
            t.emit(SFENCE)
            lab = access(t, pt, "S", "store", va, False, "ADUE=1: sw to a read-only A=0 D=0 page", page="ai_pg_P")
            pte_bit_check(t, pt, va, D, int(MUT == "d_set_on_fault"), lab, "a faulting store does not set D")
            adue_set(t, xlen, False)
            upd_cases(t, pt, va, MUT == "adue0_updates", "ADUE=0")

        with_vm(t, xlen, inner, user=True)

    both(t, aduo_body)
    tests.append(t)

    t = new("Svadu", "Svadu_disabled_hw_update_falls_back_to_Svade", ["I", "S", "Svadu"])
    t.describe(
        source="src/priv/svadu.adoc",
        rule_text="When hardware updating of A/D bits is disabled, the Svade extension, which mandates exceptions "
        "when A/D bits need be set, instead takes effect.",
        context="Hardware updating is disabled by menvcfg.ADUE=0 (T-SBI). " + ADUE_CTX,
        plan="After ADUE=1 has been used (A/D updated), ADUE=0 and SFENCE.VMA: lw, sw and fetch of A=0 pages and sw "
        "of a D=0 page page-fault from S- and U-mode, leaving the PTE unchanged.",
    )
    t.page("P")

    def fb_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = pt.va_t + 0x52000
            pt.on()
            adue_set(t, xlen, True)
            pt.leaf(va, t.page("P"), LEAF & ~A)
            t.emit(SFENCE)
            s_load(t, va, t.page_id("P"), "ADUE=1: updated")
            adue_set(t, xlen, False)
            upd_cases(t, pt, va, MUT == "adue0_updates", "ADUE=0")

        with_vm(t, xlen, inner, user=True)

    both(t, fb_body)
    tests.append(t)

    t = new("Svadu", "menvcfg_adue_fence", ["I", "S", "Svadu"])
    t.describe(
        source=MAC,
        rule_text="After changing menvcfg.ADUE, executing an SFENCE.VMA instruction with rs1=x0 and rs2=x0 suffices "
        "to synchronize address-translation caches with respect to the altered interpretation of page-table "
        "entries' A/D bits.",
        context="The A=0 page is first accessed under the old setting (cached, possibly as a fault), then ADUE flips "
        "and only SFENCE.VMA x0, x0 is executed.",
        plan="1. ADUE=0: lw of an A=0 page faults. ADUE=1 + SFENCE.VMA x0,x0: lw succeeds and sets A.\n"
        "2. With ADUE=1, an A=0, D=0 PTE is written, fenced and read (translation cached). The PTE is reset to "
        "A=0, D=0 and fenced; then ADUE=0 + SFENCE.VMA x0,x0: lw and sw of the page fault.",
    )
    t.page("P")

    def af_body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = pt.va_t + 0x53000
            pt.on()
            adue_set(t, xlen, False)
            pt.leaf(va, t.page("P"), LEAF & ~A)
            t.emit(SFENCE)
            access(t, pt, "S", "load", va, False, "ADUE=0, A=0", page="ai_pg_P")
            menvcfg_bit(t, xlen, ADUE_BIT, True)
            t.emit(SFENCE)
            lab = access(t, pt, "S", "load", va, MUT != "adue_fence_ignored", "ADUE=1 after SFENCE.VMA", page="ai_pg_P")
            pte_bit_check(t, pt, va, A, int(MUT != "adue_fence_ignored"), lab, "A set")
            pt.leaf(va, t.page("P"), LEAF & ~(A | D))
            t.emit(SFENCE)
            s_load(t, va, t.page_id("P"), "ADUE=1 again: warms the translation")
            pt.leaf(va, t.page("P"), LEAF & ~(A | D))
            t.emit(SFENCE)
            menvcfg_bit(t, xlen, ADUE_BIT, False)
            t.emit(SFENCE)
            for kind in ("load", "store"):
                access(t, pt, "S", kind, va, False, f"ADUE=0 after SFENCE.VMA: {kind}", page="ai_pg_P")

        with_vm(t, xlen, inner)

    both(t, af_body)
    tests.append(t)
    return tests


# ---------------------------------------------------------------- Svnapot
def napot_map(
    t: SvTest, pt: SvPT, va: int, block: str, perms: int = LEAF, low: int = 0b1000, js: range | list = range(16)
) -> None:
    for j in js:
        pt.leaf_napot(va + j * 0x1000, block, perms | N_BIT, low)


def blk_load(t: SvTest, va: int, block: str, j: int, desc: str) -> str:
    return s_load(t, va, t.block_id(block, j), desc)


def gen_napot() -> list[SvTest]:
    tests = []
    req = ["I", "S", "Svnapot"]
    VN = 0x4010_0000  # 64 KiB-aligned
    ctx = (
        "RV64 only; requires Svnapot (and so Sv39). A 64 KiB naturally aligned block of 16 pages (ids "
        "block_id) is mapped by 16 NAPOT PTEs (N=1, ppn[3:0]=1000) at a 64 KiB-aligned VA, as software must "
        "write them. "
    )

    def mk(rule: str, text: str, context: str, plan: str) -> SvTest:
        t = new("Svnapot", rule, req, rv64=True)
        t.describe(source="src/priv/svnapot.adoc", rule_text=text, context=ctx + context, plan=plan)
        t.block("N", 16, 16)
        t.block("M", 16, 16)
        return t

    def run(t: SvTest, inner) -> None:  # noqa: ANN001
        with_vm(t, 64, inner, scheme="sv39", guarded=False, name="n39")

    t = mk(
        "Svnapot_pte_n",
        "In Sv39, Sv48, and Sv57, when a PTE has N=1, the PTE represents a translation that is part of a range of "
        "contiguous virtual-to-physical translations with the same values for PTE bits 5-0.",
        "",
        "lw of every page j of the range reads block page j; a sw to page 9 lands in block page 9; a fetch from "
        "page 5 runs block page 5's stub.",
    )

    def pn(pt: SvPT) -> None:
        napot_map(t, pt, VN, "ai_blk_N")
        pt.on()
        for j in range(16):
            want = j if MUT != "napot_ppn_used" else 8
            blk_load(t, VN + j * 0x1000, "N", want, f"page {j} of the 64 KiB range")
        lab = t.label("st")
        t.emit(f"li x6, {hex(VN + 9 * 0x1000)}")
        t.emit("li x8, 0x4B1D")
        t.emit(f"{lab}:", 0)
        t.emit("sw x8, 64(x6)")
        t.la("x9", "ai_blk_N+0x9040")
        t.emit("lw x7, 0(x9)")
        t.check("x7", 0x4B1D, lab, "sw to page 9 lands in block page 9")
        lab = t.label("fx")
        t.emit(f"li x6, {hex(VN + 5 * 0x1000)}")
        t.emit(f"{lab}:", 0)
        t.emit(f"jalr x1, {EXEC_OFF}(x6)")
        t.check("x7", t.block_id("N", 5), lab, "fetch from page 5 runs block page 5")

    run(t, pn)
    tests.append(t)

    t = mk(
        "Svnapot_range_napot",
        "Such ranges must be of a naturally aligned power-of-2 (NAPOT) granularity larger than the base page size",
        "The 64 KiB range ends at its natural boundaries: the pages just below and just above it are not mapped. "
        "With only PTE 0 written (the other 15 invalid), a NAPOT translation cached from PTE 0 may serve the other "
        "pages (Svnapot_cache_entries), or their own invalid PTEs fault; nothing else is legal.",
        "1. All 16 PTEs: VA-4K and VA+64K page-fault; pages 0 and 15 read block pages 0 and 15.\n"
        "2. A second range at VA+128K with only PTE 0 set: page 0 reads block M page 0; pages 1, 7, 15 read "
        "their block M page or fault.",
    )

    def rn(pt: SvPT) -> None:
        napot_map(t, pt, VN, "ai_blk_N")
        napot_map(t, pt, VN + 0x20000, "ai_blk_M", js=[0])
        pt.on()
        for v in (VN - 0x1000, VN + 0x10000):
            access(t, pt, "S", "load", v, MUT == "napot_range_128k" and v > VN, f"outside the range: {hex(v)}")
        blk_load(t, VN, "N", 0, "page 0")
        blk_load(t, VN + 0xF000, "N", 15, "page 15")
        blk_load(t, VN + 0x20000, "M", 0, "single-PTE range, page 0")
        for j in (1, 7, 15):
            s_load_any(t, VN + 0x20000 + j * 0x1000, [t.block_id("M", j), "fault"], f"single-PTE range, page {j}")

    run(t, rn)
    tests.append(t)

    t = mk(
        "Svnapot_depends_Sv39",
        "The Svnapot extension depends on the Sv39 extension",
        "satp is written with MODE=8 (Sv39) and an identity-mapping table.",
        "satp reads back MODE=8 and a NAPOT range translates under it.",
    )

    def dp(pt: SvPT) -> None:
        napot_map(t, pt, VN, "ai_blk_N", js=range(16))
        pt.on()
        lab = t.label("m")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, satp")
        t.emit("srli x7, x7, 60")
        t.check("x7", 8, lab, "satp holds Sv39")
        blk_load(t, VN + 0x3000, "N", 3, "NAPOT page 3 under Sv39")

    run(t, dp)
    tests.append(t)

    rsv_lows = [0b0001, 0b0010, 0b0100, 0b0000, 0b1001, 0b0011, 0b1100]

    t = mk(
        "Svnapot_enc_tbl",
        "Page table entry encodings when pte.N=1: i=0: pte.ppn[i] = x xxxx xxx1 reserved; x xxxx xx1x reserved; "
        "x xxxx x1xx reserved; x xxxx 1000 64 KiB contiguous region (napot_bits 4); x xxxx 0xxx reserved. i>=1: "
        "reserved.",
        f"{ISSUE}823: for i >= 1 (megapage leaves and every non-leaf PTE, which sits at level >= 1) N=1 is reserved.",
        "1. ppn[3:0] = 1000: the 64 KiB range translates.\n"
        f"2. ppn[3:0] = {', '.join(f'{x:04b}' for x in rsv_lows)} (all 16 PTEs): lw page-faults.\n"
        "3. N=1 in a megapage leaf, a gigapage leaf and a pointer PTE: lw page-faults.",
    )

    def enc(pt: SvPT) -> None:
        napot_map(t, pt, VN, "ai_blk_N")
        vs, vg, vb = sp_va("sv39", 1), sp_va("sv39", 2), bva("sv39")
        pt.leaf(vs, "ai_blk_N", LEAF | N_BIT, level=1)
        pt.leaf(vg, "ai_blk_N", LEAF | N_BIT, level=2)
        pt.leaf(vb, "ai_blk_N", LEAF)
        pt.modify(vb, 1, set_bits=N_BIT, note="N=1 in the pointer")
        pt.on()
        blk_load(t, VN + 0x2000, "N", 2, "1000: 64 KiB range")
        for low in rsv_lows:
            napot_map(t, pt, VN + 0x20000, "ai_blk_M", low=low)
            t.emit(SFENCE)
            access(
                t, pt, "S", "load", VN + 0x20000 + 0x5000, MUT == "napot_any_low" and low == 0, f"ppn[3:0]={low:04b}"
            )
        for v, note in ((vs, "megapage leaf"), (vg, "gigapage leaf"), (vb, "pointer")):
            access(t, pt, "S", "load", v, MUT == "napot_superpage_ok" and v != vb, f"N=1 in a {note}")

    run(t, enc)
    tests.append(t)

    t = mk(
        "Svnapot_valid_encoding_ppn_subst",
        "If the encoding in pte is valid according to <<norm:Svnapot_enc_tbl>>, then instead of returning the "
        "original value of pte, implicit reads of a NAPOT PTE return a copy of pte in which "
        "pte.ppn[i][pte.napot_bits-1:0] is replaced by vpn[i][pte.napot_bits-1:0].",
        "Every PTE holds ppn[3:0]=1000; the physical page comes from the VA's vpn[0][3:0]. Pages other than 8 "
        "would read block page 8 if the substitution were missing; a store shows the write side.",
        "lw of pages 0, 3, 7, 8, 12, 15 reads the block page with the same index (not page 8); sw to page 3 lands in "
        "block page 3; with Svadu and ADUE=1, an A=0 range is updated and the PTE in memory keeps ppn[3:0]=1000 "
        "(only the A bit changes).",
    )

    def subst(pt: SvPT) -> None:
        napot_map(t, pt, VN, "ai_blk_N")
        pt.on()
        for j in (0, 3, 7, 8, 12, 15):
            blk_load(t, VN + j * 0x1000, "N", j if MUT != "napot_no_subst" else 8, f"page {j}")
        lab = t.label("st")
        t.emit(f"li x6, {hex(VN + 0x3000)}")
        t.emit("li x8, 0x5B57")
        t.emit(f"{lab}:", 0)
        t.emit("sw x8, 72(x6)")
        t.la("x9", "ai_blk_N+0x3048")
        t.emit("lw x7, 0(x9)")
        t.check("x7", 0x5B57, lab, "sw to page 3 lands in block page 3")

        def adu() -> None:
            adue_set(t, 64, True)
            napot_map(t, pt, VN, "ai_blk_N", perms=LEAF & ~A)
            t.emit(SFENCE)
            blk_load(t, VN + 0x6000, "N", 6, "A=0 range with ADUE=1")
            pt.read_pte(VN + 0x6000, 2, "x9")
            t.emit("srli x7, x9, 10")
            t.emit("andi x7, x7, 0xF")
            lab = t.label("ad")
            t.emit(f"{lab}:", 0)
            t.check("x7", 0b1000, lab, "the updated PTE keeps ppn[3:0]=1000")
            adue_set(t, 64, False)

        with t.only_if("defined(SVADU_SUPPORTED)"):
            adu()

    run(t, subst)
    tests.append(t)

    t = mk(
        "Svnapot_reserved_encoding_fault",
        "[If the encoding in pte is] reserved according to <<norm:Svnapot_enc_tbl>>, then a page-fault exception "
        "must be raised",
        "Reserved ppn[3:0] patterns in all 16 PTEs of a range, accessed from S-mode (load, store, fetch) and U-mode "
        "(U=1 PTEs).",
        "ppn[3:0] = 0000, 0001, 0110, 1010: S-mode lw, sw and fetch and U-mode lw page-fault (13/15/12, xtval 0 or "
        "the VA); the store does not write.",
    )

    def rsvf(pt: SvPT) -> None:
        pt.on()
        for low in (0b0000, 0b0001, 0b0110, 0b1010):
            napot_map(t, pt, VN, "ai_blk_M", perms=ULEAF, low=low)
            t.emit(SFENCE)
            sstatus_bits(t, SUM, True, "SUM")
            for kind in ("load", "store"):
                access(t, pt, "S", kind, VN + 0x4000, MUT == "napot_rsv_ok", f"ppn[3:0]={low:04b}: {kind}")
            sstatus_bits(t, SUM, False, "SUM")
            access(t, pt, "U", "load", VN + 0x4000, MUT == "napot_rsv_ok", f"ppn[3:0]={low:04b}: U-mode lw")
            napot_map(t, pt, VN, "ai_blk_M", perms=LEAF, low=low)
            t.emit(SFENCE)
            access(t, pt, "S", "fetch", VN + 0x4000, MUT == "napot_rsv_ok", f"ppn[3:0]={low:04b}: fetch")

    with_vm(t, 64, rsvf, scheme="sv39", guarded=False, name="n39", user=True)
    tests.append(t)

    t = mk(
        "Svnapot_cache_entries",
        "Implicit reads of NAPOT page table entries may create address-translation cache entries mapping a + "
        "j×PTESIZE to a copy of pte in which pte.ppn[i][pte.napot_bits-1:0] is replaced by "
        "vpn[i][pte.napot_bits-1:0], for any or all j such that j >> napot_bits = vpn[i] >> napot_bits, all for "
        "the address space identified in satp as loaded by step 1",
        "A read of page 0 may cache translations for every page of the range. All 16 PTEs are then rewritten to "
        "map block M (consistently, as software must). SFENCE.VMA with rs1 = page 5 must remove every cached "
        "entry for page 5, including one created from PTE 0; page 3 (not fenced) may still use block N. The "
        "entries belong to satp's ASID: after switching to ASID 2 with a table that maps the range "
        "non-NAPOT to block M, page 0's ASID-1 NAPOT entries are not used (when ASIDLEN >= 2).",
        "1. Read page 0 (N0). Rewrite the range to block M. SFENCE.VMA page5, x0: page 5 reads M5; page 3 reads N3 "
        "or M3; after SFENCE.VMA x0,x0 page 3 reads M3.\n"
        "2. ASIDLEN >= 2: ASID 1 maps the range NAPOT to N (read page 0); ASID 2's root maps page 4 with a plain "
        "leaf to M4: in ASID 2 (no fence) page 4 reads M4.",
    )

    def cache(pt: SvPT) -> None:
        napot_map(t, pt, VN, "ai_blk_N")
        pt.on(asid=1)
        blk_load(t, VN, "N", 0, "page 0 (fills the cache)")
        napot_map(t, pt, VN, "ai_blk_M")
        t.emit(f"li x6, {hex(VN + 0x5000)}")
        t.emit("sfence.vma x6, x0")
        blk_load(t, VN + 0x5000, "M" if MUT != "napot_fence_by_base" else "N", 5, "page 5 after SFENCE.VMA page 5")
        s_load_any(t, VN + 0x3000, [t.block_id("N", 3), t.block_id("M", 3)], "page 3, not fenced")
        t.emit(SFENCE)
        blk_load(t, VN + 0x3000, "M", 3, "page 3 after SFENCE.VMA x0, x0")
        napot_map(t, pt, VN, "ai_blk_N")
        t.emit(SFENCE)
        pb = SvPT(t, "nb", "sv39")
        pb.identity()
        pb.leaf(VN + 0x4000, "ai_blk_M", LEAF, ppn_add=4)
        asids_distinct(t, pt, "x1")
        pt.on(asid=1)

        def other() -> None:
            blk_load(t, VN + 0x4000, "N", 4, "ASID 1: NAPOT page 4")
            blk_load(t, VN, "N", 0, "ASID 1: NAPOT page 0")
            pb.on(asid=2, fence=False)
            blk_load(t, VN + 0x4000, "M", 4, "ASID 2: plain leaf, not ASID 1's NAPOT entry")
            pt.on(asid=1)

        guard(t, "x1", other)

    run(t, cache)
    tests.append(t)
    return tests


# ---------------------------------------------------------------- Svpbmt
def gen_pbmt() -> list[SvTest]:
    tests = []
    req = ["I", "S", "Svpbmt"]
    ctx = (
        "RV64 only; requires Svpbmt (and Sv39). menvcfg.PBMTE is set through T-SBI (cleared at boot) and "
        "followed by SFENCE.VMA x0, x0 (menvcfg_pbmte_fence). Pages reached with NC or IO attributes are accessed "
        "only through those mappings (aliasing with cacheable accesses may lose coherence, "
        "Svpbmt_aliasing_attribute). "
    )
    PB = {0: 0, 1: PBMT_NC, 2: PBMT_IO, 3: PBMT_RSV}

    def mk(
        rule: str, text: str, context: str, plan: str, source: str = "src/priv/svpbmt.adoc", r: list | None = None
    ) -> SvTest:
        t = new("Svpbmt", rule, r or req, rv64=True)
        t.describe(source=source, rule_text=text, context=ctx + context, plan=plan)
        return t

    def run(t: SvTest, inner, user: bool = False) -> None:  # noqa: ANN001
        def wrapped(pt: SvPT) -> None:
            menvcfg_bit(t, 64, PBMTE_BIT, True)
            inner(pt)
            menvcfg_bit(t, 64, PBMTE_BIT, False)
            t.emit(SFENCE)

        with_vm(t, 64, wrapped, scheme="sv39", guarded=False, name="b39", user=user)

    def own_rw(t: SvTest, va: int, pid: int, desc: str, val: int) -> None:
        """Through one mapping: lw reads the page's signature, sw then lw at +32 returns the value."""
        s_load(t, va, pid, f"{desc}: lw")
        lab = t.label("rw")
        t.emit(f"li x6, {hex(va)}")
        t.load("x8", val, "value")
        t.emit(f"{lab}:", 0)
        t.emit("sw x8, 32(x6)")
        t.emit("lw x7, 32(x6)")
        t.check("x7", val, lab, f"{desc}: sw then lw through the same mapping")

    t = mk(
        "Svpbmt_pte_bits",
        "In Sv39, Sv48, and Sv57, bits 62-61 of a leaf page table entry indicate the use of page-based memory "
        "types that override the PMA(s) for the associated memory pages.",
        "The pages are main memory; PMA (0), NC (1) and IO (2) all permit aligned word loads and stores. An "
        "implementation may override additional PMAs for nonzero PBMT (Svpbmt_impl_may_override_pmas), so a "
        "fetch through an NC page may raise an instruction access fault, and IO pages are not fetched from.",
        "1. PBMT = 0, 1, 2 in 4 KiB leaves (pages P0, P1, P2): lw reads the page, sw then lw returns the value.\n"
        "2. Fetch through the PMA page runs its stub; through the NC page: no trap or an instruction access fault.\n"
        "3. PBMT = 0, 1, 2 in a megapage leaf: lw reads the page.",
    )
    for n in ("P0", "P1", "P2"):
        t.page(n)

    def pbits(pt: SvPT) -> None:
        va = pt.va_t + 0x60000
        for v in (0, 1, 2):
            pt.leaf(va + v * 0x1000, t.page(f"P{v}"), LEAF | PB[v])
        pt.on()
        for v in (0, 1, 2):
            own_rw(t, va + v * 0x1000, t.page_id(f"P{v}"), f"PBMT={v}", 0x600D0 + v)
        access(t, pt, "S", "fetch", va, True, "PBMT=0: fetch", page="ai_pg_P0")
        access(
            t,
            pt,
            "S",
            "fetch",
            va + 0x1000,
            ["ok", AF["fetch"]],
            "PBMT=1: fetch (NC may refuse execution)",
            page="ai_pg_P1",
        )
        for v in (0, 1, 2):
            pt.leaf(sp_va("sv39", 1), t.page(f"P{v}"), LEAF | PB[v], level=1)
            t.emit(SFENCE)
            access(t, pt, "S", "load", sp_va("sv39", 1), True, f"PBMT={v} megapage: lw", page=f"ai_pg_P{v}", level=1)

    run(t, pbits)
    tests.append(t)

    t = mk(
        "Svpbmt_depends_Sv39",
        "The Svpbmt extension depends on the Sv39 extension",
        "",
        "satp holds MODE=8, and an NC leaf translates under Sv39.",
    )
    t.page("P")

    def dep(pt: SvPT) -> None:
        pt.leaf(pt.va_t + 0x61000, t.page("P"), LEAF | PBMT_NC)
        pt.on()
        lab = t.label("m")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, satp")
        t.emit("srli x7, x7, 60")
        t.check("x7", 8, lab, "satp holds Sv39")
        s_load(t, pt.va_t + 0x61000, t.page_id("P"), "NC page under Sv39")

    run(t, dep)
    tests.append(t)

    t = mk(
        "Svpbmt_enc_tbl",
        "Encodings for PBMT field in Sv39, Sv48, and Sv57 PTEs: 0 PMA (none); 1 NC (non-cacheable, idempotent, "
        "weakly-ordered (RVWMO), main memory); 2 IO (non-cacheable, non-idempotent, strongly-ordered (I/O "
        "ordering), I/O); 3 reserved for future standard use.",
        "Value 3 is reserved: a leaf using it page-faults (Svpbmt_leaf_pte_pbmt_reserved_3_fault).",
        "PBMT 0, 1, 2: lw reads the page; PBMT 3: lw page-faults. In 4 KiB and gigapage leaves.",
    )
    for n in ("P0", "P1", "P2", "P3"):
        t.page(n)

    def enc(pt: SvPT) -> None:
        va = pt.va_t + 0x62000
        for v in range(4):
            pt.leaf(va + v * 0x1000, t.page(f"P{v}"), LEAF | PB[v])
        pt.on()
        for v in range(4):
            ok = v != 3 or MUT == "pbmt3_ok"
            access(t, pt, "S", "load", va + v * 0x1000, ok, f"PBMT={v}", page=f"ai_pg_P{v}")
        for v in range(4):
            pt.leaf(sp_va("sv39", 2), t.page(f"P{v}"), LEAF | PB[v], level=2)
            t.emit(SFENCE)
            access(
                t,
                pt,
                "S",
                "load",
                sp_va("sv39", 2),
                v != 3 or MUT == "pbmt3_ok",
                f"PBMT={v} gigapage",
                page=f"ai_pg_P{v}",
                level=2,
            )

    run(t, enc)
    tests.append(t)

    t = mk(
        "Svpbmt_leaf_pte_pbmt_reserved_3_fault",
        "Until this value is defined by a standard extension, using this reserved value in a leaf PTE raises a "
        "page-fault exception.",
        "",
        "PBMT=3 in a 4 KiB, megapage and gigapage leaf: S-mode lw, sw, fetch and U-mode lw (U=1) page-fault "
        "(13/15/12, xtval 0 or the address); the store does not write.",
    )
    t.page("P")

    def r3(pt: SvPT) -> None:
        pt.on()
        for lv in (0, 1, 2):
            va = pt.va_t + 0x63000 if lv == 0 else sp_va("sv39", lv)
            for mode, kinds in (("S", ("load", "store", "fetch")), ("U", ("load",))):
                pt.leaf(va, t.page("P"), LEAF | PBMT_RSV | (U if mode == "U" else 0), level=lv)
                t.emit(SFENCE)
                for kind in kinds:
                    access(
                        t,
                        pt,
                        mode,
                        kind,
                        va,
                        MUT == "pbmt3_ok",
                        f"level {lv}: {mode}-mode {kind}",
                        page="ai_pg_P",
                        level=lv,
                    )

    run(t, r3, user=True)
    tests.append(t)

    t = mk(
        "Svpbmt_nonleaf_pte_pbmt_must_be_zero",
        "Until their use is defined by a standard extension, they must be cleared by software for forward "
        "compatibility, or else a page-fault exception is raised.",
        "For non-leaf PTEs, bits 62-61 are reserved. Each pointer on the path of a 4 KiB page is set in turn.",
        "PBMT = 1, 2, 3 in the root pointer and in the level-1 pointer: lw page-faults; cleared again, lw reads the "
        "page.",
    )
    t.page("P")

    def nl(pt: SvPT) -> None:
        vb = bva("sv39")
        pt.leaf(vb, t.page("P"), LEAF)
        pt.on()
        for d in (0, 1):
            for v in (1, 2, 3):
                pt.modify(vb, d, set_bits=PB[v], note=f"PBMT={v} in a pointer")
                t.emit(SFENCE)
                access(t, pt, "S", "load", vb, MUT == "pbmt_nonleaf_ok" and v != 3, f"depth {d}: pointer PBMT={v}")
                pt.modify(vb, d, clear_bits=PB[3])
            t.emit(SFENCE)
            s_load(t, vb, t.page_id("P"), f"depth {d}: cleared again")

    run(t, nl)
    tests.append(t)

    t = mk(
        "Svpbmt_noncacheable_aliasing_no_coherence_loss",
        "Accessing the same location using different attributes that are both non-cacheable (e.g., NC and IO) "
        "does not cause loss of coherence,",
        "Page X is mapped twice: VA1 with NC, VA2 with IO. It is never accessed with a cacheable attribute.",
        "sw through NC, lw through IO: the value; sw through IO, lw through NC: the value; the signature reads the "
        "same through both.",
    )
    t.page("X")

    def nc(pt: SvPT) -> None:
        v1, v2 = pt.va_t + 0x64000, pt.va_t + 0x65000
        pt.leaf(v1, t.page("X"), LEAF | PBMT_NC)
        pt.leaf(v2, t.page("X"), LEAF | PBMT_IO)
        pt.on()
        s_load(t, v1, t.page_id("X"), "NC view")
        s_load(t, v2, t.page_id("X"), "IO view")
        for a, b, val, note in ((v1, v2, 0x11C0, "NC -> IO"), (v2, v1, 0x22C0, "IO -> NC")):
            lab = t.label("al")
            t.emit(f"li x6, {hex(a)}")
            t.emit(f"li x9, {hex(b)}")
            t.load("x8", val, "value")
            t.emit(f"{lab}:", 0)
            t.emit("sw x8, 40(x6)")
            t.emit("lw x7, 40(x9)")
            t.check("x7", val, lab, f"{note}: the store is visible through the other attribute")

    run(t, nc)
    tests.append(t)

    t = mk(
        "Svpbmt_cacheable_aliasing_fence_flush_fence_required",
        "[Executing the following sequence between such accesses] prevents both loss of coherence and loss of "
        "memory ordering: fence iorw, iorw, followed by cbo.flush to an address of that location, followed by a "
        "fence iorw, iorw.",
        "Requires Zicbom (in the file's condition; menvcfg.CBCFE=1 at boot). Page Y is mapped with PMA (cacheable) "
        "at VA1 and NC at VA2.",
        "1. sw through PMA; fence iorw,iorw; cbo.flush VA1; fence iorw,iorw; lw through NC: the value.\n"
        "2. sw through NC; fence; cbo.flush VA1; fence; lw through PMA: the new value.",
    )
    t.page("Y")

    def ff(pt: SvPT) -> None:
        v1, v2 = pt.va_t + 0x66000, pt.va_t + 0x67000
        pt.leaf(v1, t.page("Y"), LEAF)
        pt.leaf(v2, t.page("Y"), LEAF | PBMT_NC)
        pt.on()
        for a, b, val, note in ((v1, v2, 0x33C0, "PMA -> NC"), (v2, v1, 0x44C0, "NC -> PMA")):
            lab = t.label("ff")
            t.emit(f"li x6, {hex(a)}")
            t.emit(f"li x9, {hex(b)}")
            t.emit(f"li x7, {hex(v1)}")
            t.load("x8", val, "value")
            t.emit("sw x8, 48(x6)")
            t.emit("fence iorw, iorw")
            t.emit(word(cbo("flush", 7), "cbo.flush (x7)"))
            t.emit("fence iorw, iorw")
            t.emit(f"{lab}:", 0)
            t.emit("lw x7, 48(x9)")
            t.check("x7", val, lab, f"{note}: visible after fence; cbo.flush; fence")

    with t.only_if("defined(ZICBOM_SUPPORTED)"):
        run(t, ff)
    tests.append(t)

    t = mk(
        "menvcfg_pbmte_op",
        "The PBMTE bit controls whether the Svpbmt extension is available for use in S-mode and G-stage address "
        "translation (i.e., for page tables pointed to by satp or hgatp). When PBMTE=1, Svpbmt is available for "
        "S-mode and G-stage address translation. When PBMTE=0, the implementation behaves as though Svpbmt were "
        "not implemented.",
        "In the Svpbmt suite because it gates Svpbmt; G-stage is in the H suite (henvcfg_pbmte_op and G-stage "
        "tests). Without Svpbmt, PTE bits 62-61 are reserved (Sv39_pte_Svpbmt_rsv). PBMTE is read back.",
        "1. PBMTE=1 (reads 1): NC and IO leaves translate (S- and U-mode lw).\n"
        "2. PBMTE=0 (reads 0) and SFENCE.VMA: the same leaves page-fault, and a PBMT=1 pointer page-faults; a "
        "PBMT=0 leaf still translates.",
        source=MAC,
    )
    for n in ("P0", "P1", "P2"):
        t.page(n)

    def pbo(pt: SvPT) -> None:
        va = pt.va_t + 0x68000
        for v in (0, 1, 2):
            pt.leaf(va + v * 0x1000, t.page(f"P{v}"), ULEAF | PB[v])
        for on in (1, 0):
            menvcfg_bit(t, 64, PBMTE_BIT, bool(on))
            menvcfg_get(t, 64, PBMTE_BIT, "x7")
            lab = t.label("pbmte")
            t.emit(f"{lab}:", 0)
            t.check("x7", on, lab, f"menvcfg.PBMTE reads {on}")
            pt.on()
            for v in (0, 1, 2):
                ok = bool(on) or v == 0 or MUT == "pbmte_ignored"
                sstatus_bits(t, SUM, True, "SUM")
                access(t, pt, "S", "load", va + v * 0x1000, ok, f"PBMTE={on}, PBMT={v}", page=f"ai_pg_P{v}")
                sstatus_bits(t, SUM, False, "SUM")
                access(t, pt, "U", "load", va + v * 0x1000, ok, f"PBMTE={on}, PBMT={v}", page=f"ai_pg_P{v}")

    run(t, pbo, user=True)
    tests.append(t)

    t = mk(
        "menvcfg_pbmte_fence",
        "After changing menvcfg.PBMTE, executing an SFENCE.VMA instruction with rs1=x0 and rs2=x0 suffices to "
        "synchronize address-translation caches with respect to the altered interpretation of page-table entries' "
        "PBMT fields.",
        "The NC page is read under one setting (cached), PBMTE flips, and only SFENCE.VMA x0, x0 follows.",
        "PBMTE=1: lw of the NC page succeeds. PBMTE=0 + SFENCE.VMA x0,x0: page fault. PBMTE=1 + SFENCE.VMA x0,x0: "
        "succeeds again.",
        source=MAC,
    )
    t.page("P")

    def pbf(pt: SvPT) -> None:
        va = pt.va_t + 0x69000
        pt.leaf(va, t.page("P"), LEAF | PBMT_NC)
        pt.on()
        s_load(t, va, t.page_id("P"), "PBMTE=1")
        for on in (0, 1):
            menvcfg_bit(t, 64, PBMTE_BIT, bool(on))
            t.emit(SFENCE)
            access(
                t,
                pt,
                "S",
                "load",
                va,
                bool(on) or MUT == "pbmte_fence_ignored",
                f"PBMTE={on} after SFENCE.VMA",
                page="ai_pg_P",
            )

    run(t, pbf)
    tests.append(t)
    return tests


# ---------------------------------------------------------------- Svinval
def gen_inval() -> list[SvTest]:
    tests = []
    req = ["I", "S", "Svinval"]
    H = "defined(H_SUPPORTED)"
    W_INV = word(SFENCE_W_INVAL, "sfence.w.inval")
    IR = word(SFENCE_INVAL_IR, "sfence.inval.ir")

    def mk(rule: str, text: str, context: str, plan: str) -> SvTest:
        t = new("Svinval", rule, req)
        t.describe(source="src/priv/svinval.adoc", rule_text=text, context=context, plan=plan)
        for n in ("A", "B", "C", "D"):
            t.page(n)
        return t

    def ids(t: SvTest) -> dict:
        return {n: t.page_id(n) for n in "ABCD"}

    stale = (
        "Without the full SFENCE.W.INVAL / SINVAL.VMA / SFENCE.INVAL.IR sequence, a read may use the old or the "
        "new translation; nothing else is legal (" + ISSUE + "1936, aswaterman). Sv39 (RV64) or Sv32 (RV32), "
        "probed. "
    )

    def seq(t: SvTest, rs1: int, rs2: int, note: str = "") -> None:
        t.emit(W_INV)
        t.emit(word(sinval_vma(rs1, rs2), f"sinval.vma x{rs1}, x{rs2} {note}"))
        t.emit(IR)

    t = mk(
        "Svinval_sinval_vma_invalidates_same_as_sfence_vma",
        "However, unlike SFENCE.VMA, SINVAL.VMA instructions are only ordered with respect to SFENCE.VMA, "
        "SFENCE.W.INVAL, and SFENCE.INVAL.IR instructions as defined below.",
        stale + "SINVAL.VMA invalidates what SFENCE.VMA with the same rs1/rs2 would; ordered by the surrounding "
        "SFENCE.W.INVAL and SFENCE.INVAL.IR.",
        "For each rs1/rs2 form (x0/x0, VA/x0, x0/ASID, VA/ASID): change VA's leaf to the next page; SFENCE.W.INVAL; "
        "SINVAL.VMA; read (old or new); SFENCE.INVAL.IR; read: the new page. Then SINVAL.VMA ordered by "
        "SFENCE.VMA: change, SINVAL.VMA VA, SFENCE.VMA x0, x0: new.",
    )

    def same(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            p = ids(t)
            va = pt.va_t + 0x70000
            pt.leaf(va, t.page("A"), LEAF)
            pt.on(asid=1)
            s_load(t, va, p["A"], "initial")
            prev = "A"
            for i, (r1, r2) in enumerate(((0, 0), (6, 0), (0, 9), (6, 9))):
                nxt = "ABCD"[(i + 1) % 4]
                pt.leaf(va, t.page(nxt), LEAF)
                t.emit(f"li x6, {hex(va)}")
                cur_asid(t, xlen, "x9")
                t.emit(W_INV)
                t.emit(word(sinval_vma(r1, r2), f"sinval.vma x{r1}, x{r2}"))
                s_load_any(t, va, [p[prev], p[nxt]], f"before SFENCE.INVAL.IR (rs1=x{r1}, rs2=x{r2})")
                t.emit(IR)
                s_load(t, va, p[nxt] if MUT != "sinval_noop" else p[prev], f"after the sequence (rs1=x{r1}, rs2=x{r2})")
                prev = nxt
            pt.leaf(va, t.page("A"), LEAF)
            t.emit(f"li x6, {hex(va)}")
            t.emit(word(sinval_vma(6, 0), "sinval.vma x6, x0"))
            t.emit(SFENCE)
            s_load(t, va, p["A"], "SINVAL.VMA followed by SFENCE.VMA")

        with_vm(t, xlen, inner)

    both(t, same)
    tests.append(t)

    t = mk(
        "Svinval_sfence_w_inval_orders_before_sinval_vma",
        "The SFENCE.INVAL.IR instruction guarantees that any previous SINVAL.VMA instructions executed by the current "
        "hart are ordered before subsequent implicit references by that hart to the memory-management data "
        "structures.",
        stale + "Several SINVAL.VMAs are batched before one SFENCE.INVAL.IR.",
        "Change three VAs' leaves; SFENCE.W.INVAL; SINVAL.VMA for each VA; SFENCE.INVAL.IR: all three read their new "
        "pages.",
    )

    def batch(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            p = ids(t)
            vaddrs = [pt.va_t + 0x71000 + k * 0x1000 for k in range(3)]
            for v in vaddrs:
                pt.leaf(v, t.page("A"), LEAF)
            pt.on()
            for v in vaddrs:
                s_load(t, v, p["A"], "before")
            for k, v in enumerate(vaddrs):
                pt.leaf(v, t.page("BCD"[k]), LEAF)
            t.emit(W_INV)
            for v in vaddrs:
                t.emit(f"li x6, {hex(v)}")
                t.emit(word(sinval_vma(6, 0), "sinval.vma x6, x0"))
            t.emit(IR)
            for k, v in enumerate(vaddrs):
                s_load(
                    t,
                    v,
                    p["BCD"[k]] if not (MUT == "ir_orders_last_only" and k < 2) else p["A"],
                    f"VA {k} after the batch",
                )

        with_vm(t, xlen, inner)

    both(t, batch)
    tests.append(t)

    t = mk(
        "Svinval_sequence_rs1_rs2",
        "[the sequence has the same effect as a hypothetical SFENCE.VMA in which] the values of rs1 and rs2 for the "
        "SFENCE.VMA are the same as those used in the SINVAL.VMA,",
        stale + "The scope follows SFENCE.VMA: rs1 limits it to leaf PTEs of that VA; rs2 to the ASID, excluding "
        "global mappings.",
        "1. Change VA1 and VA2; sequence with rs1=VA1, rs2=x0: VA1 new, VA2 old or new.\n"
        "2. Change a global leaf; sequence with rs1=x0, rs2=ASID: old or new; sequence with x0, x0: new.\n"
        "3. Change VA3; sequence with rs1=VA3, rs2=ASID: new.",
    )

    def scope(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            p = ids(t)
            v1, v2, vg, v3 = (pt.va_t + 0x74000 + k * 0x1000 for k in range(4))
            for v in (v1, v2, v3):
                pt.leaf(v, t.page("A"), LEAF)
            pt.leaf(vg, t.page("A"), LEAF | G)
            pt.on(asid=1)
            for v in (v1, v2, v3, vg):
                s_load(t, v, p["A"], "before")
            for v in (v1, v2):
                pt.leaf(v, t.page("B"), LEAF)
            t.emit(f"li x6, {hex(v1)}")
            seq(t, 6, 0)
            s_load(t, v1, p["B"], "VA1 after the VA1-scoped sequence")
            s_load_any(t, v2, [p["A"], p["B"]], "VA2 (outside the scope)")
            pt.leaf(vg, t.page("B"), LEAF | G)
            cur_asid(t, xlen, "x9")
            seq(t, 0, 9)
            s_load_any(t, vg, [p["A"], p["B"]], "global after an ASID-scoped sequence")
            seq(t, 0, 0)
            s_load(t, vg, p["B"] if MUT != "sinval_skips_global" else p["A"], "global after x0, x0")
            pt.leaf(v3, t.page("C"), LEAF)
            t.emit(f"li x6, {hex(v3)}")
            cur_asid(t, xlen, "x9")
            seq(t, 6, 9)
            s_load(t, v3, p["C"], "VA3 after the VA3/ASID sequence")

        with_vm(t, xlen, inner)

    both(t, scope)
    tests.append(t)

    t = mk(
        "Svinval_sequence_reads_writes_before",
        "[the sequence has the same effect as a hypothetical SFENCE.VMA in which] reads and writes prior to the "
        "SFENCE.W.INVAL are considered to be those prior to the SFENCE.VMA,",
        stale + "A PTE store before SFENCE.W.INVAL is ordered before the invalidation; one made after it (before "
        "SINVAL.VMA) is not guaranteed to be.",
        "1. Change VA1 before SFENCE.W.INVAL; SINVAL.VMA VA1; SFENCE.INVAL.IR: new.\n"
        "2. SFENCE.W.INVAL; change VA2; SINVAL.VMA VA2; SFENCE.INVAL.IR: old or new; SFENCE.VMA x0,x0: new.",
    )

    def before(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            p = ids(t)
            v1, v2 = pt.va_t + 0x78000, pt.va_t + 0x79000
            for v in (v1, v2):
                pt.leaf(v, t.page("A"), LEAF)
            pt.on()
            for v in (v1, v2):
                s_load(t, v, p["A"], "before")
            pt.leaf(v1, t.page("B"), LEAF)
            t.emit(f"li x6, {hex(v1)}")
            seq(t, 6, 0)
            s_load(t, v1, p["B"], "store before SFENCE.W.INVAL")
            t.emit(W_INV)
            pt.leaf(v2, t.page("B"), LEAF)
            t.emit(f"li x6, {hex(v2)}")
            t.emit(word(sinval_vma(6, 0), "sinval.vma x6, x0"))
            t.emit(IR)
            vals = [p["A"], p["B"]] if MUT != "w_inval_after_orders" else [p["A"]]
            s_load_any(t, v2, vals, "store after SFENCE.W.INVAL")
            t.emit(SFENCE)
            s_load(t, v2, p["B"], "after SFENCE.VMA")

        with_vm(t, xlen, inner)

    both(t, before)
    tests.append(t)

    t = mk(
        "Svinval_sequence_reads_writes_after",
        "[the sequence has the same effect as a hypothetical SFENCE.VMA in which] reads and writes following the "
        "SFENCE.INVAL.IR are considered to be those subsequent to the SFENCE.VMA.",
        stale + "Explicit and implicit accesses after SFENCE.INVAL.IR see the new translation: a load, a store and a "
        "fetch.",
        "Change VA's leaf from A to B; sequence (VA, x0): lw reads B, sw lands in B, fetch runs B's stub.",
    )

    def after(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            p = ids(t)
            va = pt.va_t + 0x7A000
            pt.leaf(va, t.page("A"), LEAF)
            pt.on()
            s_load(t, va, p["A"], "before")
            access(t, pt, "S", "fetch", va, True, "fetch before", page="ai_pg_A")
            pt.leaf(va, t.page("B"), LEAF)
            t.emit(f"li x6, {hex(va)}")
            seq(t, 6, 0)
            s_load(t, va, p["B"] if MUT != "sinval_noop" else p["A"], "lw after SFENCE.INVAL.IR")
            access(t, pt, "S", "store", va, True, "sw after SFENCE.INVAL.IR", page="ai_pg_B")
            access(t, pt, "S", "fetch", va, True, "fetch after SFENCE.INVAL.IR", page="ai_pg_B")

        with_vm(t, xlen, inner)

    both(t, after)
    tests.append(t)

    # ---- validity
    INSNS = {"sinval.vma": sinval_vma(6, 7), "sfence.w.inval": SFENCE_W_INVAL, "sfence.inval.ir": SFENCE_INVAL_IR}
    HINSNS = {"hinval.vvma": hinval_vvma(6, 7), "hinval.gvma": hinval_gvma(6, 7)}

    def iwin(t: SvTest, mode: str, name: str, e: int, exp, desc: str) -> None:  # noqa: ANN001
        t.emit("li x6, 0")
        t.emit("li x7, 0")
        tv = [0, e] if exp in (ILLEGAL, VIRTUAL) else None
        if mode in ("VS", "VU"):
            t.window(mode, [word(e, name)], exp, f"{name} ({desc})", tv)
        else:
            win(t, None, mode, [word(e, name)], exp, f"{name} ({desc})", tval=tv)

    def vmk(rule: str, text: str, context: str, plan: str, body, h: bool = False) -> None:  # noqa: ANN001
        t = new("Svinval", rule, req + (["H"] if h else []))
        t.describe(source="src/priv/svinval.adoc", rule_text=text, context=context, plan=plan)
        body(t)
        tests.append(t)

    def u_mode(t: SvTest) -> None:
        for n, e in INSNS.items():
            iwin(t, "U", n, e, ILLEGAL if MUT != "u_inval_ok" else "ok", "U-mode")
        with t.only_if(H):
            for n, e in HINSNS.items():
                iwin(t, "U", n, e, ILLEGAL, "U-mode")

    vmk(
        "Svinval_illegal_instruction_u_mode",
        "In particular, an attempt to execute any of these instructions in U-mode always raises an illegal-instruction "
        "exception.",
        "These are SINVAL.VMA, HINVAL.VVMA and HINVAL.GVMA (the H ones only with H). Executed from U-mode with satp "
        "Bare and every trap control clear; xtval is 0 or the encoding.",
        "U-mode sinval.vma, sfence.w.inval, sfence.inval.ir and (with H) hinval.vvma, hinval.gvma: illegal "
        "instruction (2), xepc at the instruction, SPP = U.",
        u_mode,
    )

    def tvm(t: SvTest) -> None:
        t.tsbi_csr("SET", "MSTATUS", imm=1 << 20)
        t.tsbi_csr("READ", "MSTATUS")
        t.emit("srli x1, a0, 20")
        t.emit("andi x1, x1, 1  // TVM is WARL: run the TVM=1 cases only if it reads 1")
        guard(
            t,
            "x1",
            lambda: iwin(
                t, "S", "sinval.vma", INSNS["sinval.vma"], ILLEGAL if MUT != "tvm_ignored" else "ok", "S-mode, TVM=1"
            ),
        )
        with t.only_if(H):

            def h1() -> None:
                iwin(t, "S", "hinval.gvma", HINSNS["hinval.gvma"], ILLEGAL, "HS-mode, TVM=1")
                iwin(t, "S", "hinval.vvma", HINSNS["hinval.vvma"], "ok", "HS-mode, TVM=1 (not trapped by TVM)")

            guard(t, "x1", h1)
        t.tsbi_csr("CLEAR", "MSTATUS", imm=1 << 20)
        iwin(t, "S", "sinval.vma", INSNS["sinval.vma"], "ok", "S-mode, TVM=0")
        with t.only_if(H):
            iwin(t, "S", "hinval.gvma", HINSNS["hinval.gvma"], "ok", "HS-mode, TVM=0")

    vmk(
        "Svinval_illegal_instruction_tvm",
        "An attempt to execute SINVAL.VMA or HINVAL.GVMA in S-mode or HS-mode when mstatus.TVM=1 also raises an "
        "illegal-instruction exception.",
        "mstatus.TVM is set and cleared through T-SBI. TVM is WARL, so the TVM=1 cases run only when it reads back 1. "
        "HINVAL.VVMA is not affected by TVM (HFENCE.VVMA is not).",
        "TVM=1: S-mode sinval.vma and (with H) hinval.gvma raise illegal instruction; hinval.vvma does not. TVM=0: "
        "all execute.",
        tvm,
    )

    def vuvs(t: SvTest) -> None:
        with t.only_if(H):
            for mode in ("VS", "VU"):
                for n, e in HINSNS.items():
                    iwin(t, mode, n, e, VIRTUAL if MUT != "hinval_illegal_in_v" else ILLEGAL, f"{mode}-mode")
            iwin(t, "VU", "sinval.vma", INSNS["sinval.vma"], VIRTUAL, "VU-mode")
            iwin(t, "VS", "sinval.vma", INSNS["sinval.vma"], "ok", "VS-mode, VTVM=0")

    vmk(
        "Svinval_virtual_instruction_vu_vs",
        "An attempt to execute HINVAL.VVMA or HINVAL.GVMA in VS-mode or VU-mode, or to execute SINVAL.VMA in VU-mode, "
        "raises a virtual-instruction exception.",
        "Requires H. VS and VU are entered with sret (hstatus.SPV); vsatp and hgatp are Bare. hstatus.VTVM=0, "
        "mstatus.TVM=0.",
        "VS and VU: hinval.vvma and hinval.gvma raise virtual instruction (22, xtval 0 or the encoding); VU: "
        "sinval.vma raises virtual instruction; VS: sinval.vma executes (VTVM=0).",
        vuvs,
        h=True,
    )

    def vtvm(t: SvTest) -> None:
        with t.only_if(H):
            t.emit("li x7, 0x100000")
            t.emit("csrs 0x600, x7  // hstatus.VTVM = 1")
            iwin(
                t,
                "VS",
                "sinval.vma",
                INSNS["sinval.vma"],
                VIRTUAL if MUT != "vtvm_ignored" else "ok",
                "VS-mode, VTVM=1",
            )
            t.emit("li x7, 0x100000")
            t.emit("csrc 0x600, x7  // hstatus.VTVM = 0")
            iwin(t, "VS", "sinval.vma", INSNS["sinval.vma"], "ok", "VS-mode, VTVM=0")

    vmk(
        "Svinval_virtual_instruction_vtvms",
        "When hstatus.VTVM=1, an attempt to execute SINVAL.VMA in VS-mode also raises a virtual-instruction exception.",
        "Requires H. hstatus.VTVM is written from HS-mode.",
        "VTVM=1: VS-mode sinval.vma raises virtual instruction (22). VTVM=0: it executes.",
        vtvm,
        h=True,
    )

    def wu(t: SvTest) -> None:
        for n in ("sfence.w.inval", "sfence.inval.ir"):
            iwin(t, "U", n, INSNS[n], ILLEGAL, "U-mode")
        t.tsbi_csr("SET", "MSTATUS", imm=1 << 20)
        for n in ("sfence.w.inval", "sfence.inval.ir"):
            iwin(t, "U", n, INSNS[n], ILLEGAL, "U-mode, TVM=1")
        t.tsbi_csr("CLEAR", "MSTATUS", imm=1 << 20)

    vmk(
        "Svinval_sfence_w_inval_inval_u_mode",
        "[Attempting to execute SFENCE.W.INVAL or SFENCE.INVAL.IR in U-mode] raises an illegal-instruction exception.",
        "U-mode with mstatus.TVM 0 and 1.",
        "U-mode sfence.w.inval and sfence.inval.ir raise illegal instruction (2), with TVM=0 and TVM=1.",
        wu,
    )

    def wvu(t: SvTest) -> None:
        with t.only_if(H):
            for n in ("sfence.w.inval", "sfence.inval.ir"):
                iwin(t, "VU", n, INSNS[n], VIRTUAL if MUT != "winval_vu_illegal" else ILLEGAL, "VU-mode")

    vmk(
        "Svinval_sfence_w_inval_inval_vu_mode",
        "Doing so in VU-mode raises a virtual-instruction exception.",
        "Requires H. VU is entered with sret (SPV=1, SPP=0).",
        "VU-mode sfence.w.inval and sfence.inval.ir raise virtual instruction (22).",
        wvu,
        h=True,
    )

    def wsvs(t: SvTest) -> None:
        t.tsbi_csr("SET", "MSTATUS", imm=1 << 20)
        for n in ("sfence.w.inval", "sfence.inval.ir"):
            iwin(t, "S", n, INSNS[n], "ok" if MUT != "winval_tvm_traps" else ILLEGAL, "S-mode, TVM=1")
        t.tsbi_csr("CLEAR", "MSTATUS", imm=1 << 20)
        for n in ("sfence.w.inval", "sfence.inval.ir"):
            iwin(t, "S", n, INSNS[n], "ok", "S-mode, TVM=0")
        with t.only_if(H):
            t.emit("li x7, 0x100000")
            t.emit("csrs 0x600, x7  // hstatus.VTVM = 1")
            for n in ("sfence.w.inval", "sfence.inval.ir"):
                iwin(t, "VS", n, INSNS[n], "ok", "VS-mode, VTVM=1")
            t.emit("li x7, 0x100000")
            t.emit("csrc 0x600, x7  // hstatus.VTVM = 0")

    vmk(
        "Svinval_sfence_w_inval_inval_s_vs_mode",
        "SFENCE.W.INVAL and SFENCE.INVAL.IR are unaffected by the mstatus.TVM and hstatus.VTVM fields and hence are "
        "always permitted in S-mode and VS-mode.",
        "mstatus.TVM through T-SBI; hstatus.VTVM from HS-mode (with H).",
        "S-mode with TVM=1 and TVM=0, and VS-mode with VTVM=1 (H): sfence.w.inval and sfence.inval.ir execute.",
        wsvs,
    )
    return tests


def gen() -> list[SvTest]:
    tests = []
    tests += gen_perm()
    tests += gen_perm2()
    tests += gen_satp()
    tests += gen_sfence()
    tests += gen_schemes()
    tests += gen_ad()
    tests += gen_napot()
    tests += gen_pbmt()
    tests += gen_inval()
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
