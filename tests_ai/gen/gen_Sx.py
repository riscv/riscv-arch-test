#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate the small privileged-extension rule-derived suites, one directory each:

- Supervisor: tests_ai/Sstvala, Sstvecd, Ssu64xl, Ssccptr, Ssstrict.
- Hypervisor: tests_ai/Shgatpa, Shtvala, Shvsatpa, Shvstvala, Shvstvecd (Sha is an umbrella with no tests).
- Memory: tests_ai/Svvptc, Svrsw60t59b.
- tests_ai/Ssintro: the rules of src/priv/intro.adoc and src/priv/csrs.adoc that no other tests_ai suite uses.

Most of these extensions make an optional behavior of the base privileged architecture mandatory (stval holds the
address, stvec holds Direct with any 4-byte-aligned BASE, ...). Their tests therefore check only the strict outcome,
and run only on configurations that list the extension. Helpers are in sxlib.py; page tables come from svlib.py
(S-stage) and hmem.py (G-stage, VS-stage), imported read-only.

Usage: gen_Sx.py [rule ...]   (default: every rule)
"""

# ruff: noqa: B023  (closures run immediately inside the loop that defines them)
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import POOL_TRAP, TestFile, X
from svlib import LEAF, ULEAF, VA_T, SvPT, SvTest, amoadd_w, enter_u_alias, lr_w
from sxlib import (
    BREAKPOINT,
    C16,
    CSR_FORMS,
    CSRS,
    FA_KIND,
    HAS_FA_KIND,
    HFENCE_GVMA,
    HFENCE_VVMA,
    HGATP,
    ILLEGAL,
    INSN_AF,
    INSN_GPF,
    INSN_MIS,
    INSN_PF,
    INTRO,
    ISSUE,
    LOAD_AF,
    LOAD_GPF,
    LOAD_MIS,
    LOAD_PF,
    MARCH,
    STORE_AF,
    STORE_GPF,
    STORE_MIS,
    STORE_PF,
    SUP,
    VIRTUAL,
    VSATP,
    H,
    atp_probe,
    both,
    check_vect,
    delay,
    enc_csr,
    half,
    icause,
    outcome_at,
    outcome_cases,
    spvp,
    with_vm,
    word,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect, Value

SUITE = "Sx"
MUT = os.environ.get("AI_MUTANT", "")  # mutate.py: model a plausible bug in the expectations

MUTANTS = {
    # Sstvecd / Shvstvecd
    "direct_int_vectored": "Direct-mode interrupts are vectored to BASE + 4*cause",
    "mode0_lost": "stvec.MODE cannot return to Direct after Vectored was written (MODE reads 1)",
    "base_bit2_ro0": "stvec.BASE[0] (address bit 2) is read-only 0 (BASE must be 8-byte aligned)",
    "base_64b": "stvec.BASE ignores address bits 5:2 (64-byte alignment)",
    "vs_direct_int_vectored": "Direct-mode VS interrupts are vectored to vstvec.BASE + 4*cause",
    "vs_base_bit2_ro0": "vstvec.BASE[0] (address bit 2) is read-only 0",
    "vs_mode0_lost": "vstvec.MODE cannot return to Direct after Vectored was written",
    # Sstvala
    "tval_zero_misaligned": "stval is 0 for misaligned loads and stores",
    "tval_aligned_down": "stval holds the faulting address rounded down to the access size",
    "tval_zero_access": "stval is 0 for access faults",
    "tval_zero_pf_u": "stval is 0 for page faults from U-mode",
    "tval_page_base": "stval holds the faulting page's base address for page faults",
    "tval_straddle_start": "a misaligned access whose second page faults reports the access's own address",
    "tval_fetch_start": "a fetch whose second half faults reports the instruction's address",
    "tval_zero_illegal": "stval is 0 for illegal-instruction exceptions",
    "tval_zero_illegal_u": "stval is 0 for illegal-instruction exceptions from U-mode",
    "tval_zero_virtual": "stval is 0 for virtual-instruction exceptions",
    "tval_parcel32": "a 16-bit illegal instruction reports 32 bits (the next parcel too)",
    "tval_zero_trigger": "stval is 0 for address-trigger breakpoints",
    "tval_insn_mis_link": "stval holds the jump's address (not the target) for a misaligned fetch",
    # Ssu64xl
    "uxl_ro1": "sstatus.UXL is read-only 1 (UXLEN=32 only)",
    "u_32bit": "U-mode runs with XLEN=32 although UXL reads 2",
    "uxl_rsv_kept": "reserved UXL values 0 and 3 are stored",
    # Ssccptr
    "walk_af": "page-table reads from main memory raise access faults",
    "stale_pte": "the walker reads a stale PTE after a store and SFENCE.VMA",
    # Svvptc
    "vptc_never": "a PTE made valid without a fence is never seen (the cached invalid entry is kept)",
    # Svrsw60t59b
    "rsw_bits_fault": "PTE bits 60-59 are treated as reserved (page fault)",
    "rsv58_ignored": "PTE bit 58 is ignored too",
    "ad_clears_rsw": "a hardware A/D update clears PTE bits 60-59",
    "no_sv39": "satp does not accept Sv39",
    # Shgatpa / Shvsatpa
    "x4_missing_sv48": "hgatp rejects Sv48x4 although satp accepts Sv48",
    "x4_missing_sv32": "hgatp rejects Sv32x4 although satp accepts Sv32",
    "x4_drops_top": "the SvNNx4 walk ignores the two extra GPA bits",
    "no_bare": "hgatp cannot hold Bare (reads Sv39x4)",
    "vsatp_missing_sv57": "vsatp rejects Sv57 although satp accepts it",
    "vsatp_missing_sv32": "vsatp rejects Sv32 although satp accepts it",
    "vsatp_ignored": "a vsatp mode reads back but HLV does not translate through it",
    # Shtvala
    "htval_zero": "htval is 0 on guest-page faults",
    "htval_unshifted": "htval holds the GPA unshifted",
    "htval_page": "htval holds the faulting GPA's page (offset dropped)",
    "htval_straddle_start": "a misaligned access whose second page faults reports the access's own GPA",
    "htval_implicit_final": "an implicit-access guest-page fault reports the final GPA, not the PTE's",
    "htval_gva": "htval holds the guest virtual address >> 2 instead of the GPA >> 2",
    # Shvstvala
    "vstval_zero_addr": "vstval is 0 for VS-mode page, access and misaligned faults",
    "vstval_zero_ill": "vstval is 0 for VS-mode illegal-instruction exceptions",
    "vstval_straddle_start": "a misaligned VS access whose second page faults reports the access's own address",
    "vstval_fetch_start": "a VS fetch whose second half faults reports the instruction's address",
    # Ssstrict
    "strict_read_forms_ok": "read-only CSR forms (rs1=x0, uimm=0) of an unimplemented CSR do not trap",
    "strict_vs_virtual": "VS/VU accesses to unimplemented CSRs raise virtual instead of illegal instruction",
    "strict_m_handler": "Ssstrict traps from S/U are taken by the M-mode handler (not contained)",
    "strict_ops_execute": "unimplemented opcodes execute as no-ops",
    "strict_tval_other": "xtval holds something other than 0 or the instruction",
    # Ssintro
    "nonpriv_ok": "U-mode privileged operations execute without an exception",
    "mpp_s_is_2": "a trap from S-mode records MPP = 10",
    "mpp_2_held": "mstatus.MPP holds the reserved value 10",
    "s_without_u": "a hart may have S-mode without U-mode",
    "higher_priv_no_write": "a higher mode's write of a lower-level CSR is ignored",
    "read_clears": "reading fflags/xcause clears it",
    "ro_write_ignored": "writes to read-only CSRs are ignored without a trap",
    "ro_read_traps": "read forms of read-only CSRs trap",
    "ro_write_virtual": "VS/VU writes of read-only CSRs raise virtual instead of illegal instruction",
    "rw_class_traps": "writes to csr[11:10] != 11 CSRs trap",
    "access_level_off_by_one": "a CSR one level above the mode is accessible",
    "virtual_as_illegal": "VS/VU accesses HS could make raise illegal instead of virtual instruction",
    "privilege_reads_ok": "read forms of a higher-level CSR do not trap",
    "debug_dcsr_m_ok": "M-mode may read dcsr outside Debug Mode",
    "trigger_csrs_trap": "M-mode access to tselect/tdata1/tinfo traps",
    "ro_bits_writable": "read-only bits in read/write CSRs are writable",
    "wpri_stored": "WPRI bits are stored",
    "warl_traps": "writes of unsupported values to WARL fields trap",
    "wide_write_clears_high": "an RV32 write of the low half clears the high half",
    "high_half_separate": "an RV32 high-half CSR is a separate register (no carry from the low half)",
}


def out(suite: str) -> str:
    """The directory a test is written to: its suite, or the mutant directory."""
    return suite if SUITE == "Sx" else SUITE


def new(suite: str, rule: str, required: list | None = None, **kw: object) -> SvTest:
    """A test of `suite` (default: requires I, S and the suite's extension), booting to S-mode."""
    kw.setdefault("boot", "S")
    kw.setdefault("pool", POOL_TRAP)
    kw.setdefault("march", MARCH)
    return SvTest(out(suite), rule, required=required or ["I", "S", suite], **kw)


# ================================================================ Sstvecd / Shvstvecd
SIP_SSIP = 2
VS_HANDLER_DELEG = 1 << BREAKPOINT  # hedeleg bit that sends ebreak from VS/VU to the VS handler


def tvec_ctx(vs: bool) -> dict:
    if vs:
        return {
            "csr": "0x205",
            "name": "vstvec",
            "tramp": "Vtrampoline",
            "trap_modes": ("VS", "VU"),
            "prefix": "vs_",
        }
    return {"csr": "stvec", "name": "stvec", "tramp": "Strampoline", "trap_modes": ("S", "U"), "prefix": ""}


def mut(name: str, vs: bool) -> bool:
    return (("vs_" if vs else "") + name) == MUT


def base_entry(k: int, vs: bool) -> int:
    """The trampoline entry a trap enters with xtvec = trampoline + 4k (MODE Direct), per the mutants."""
    if mut("base_bit2_ro0", vs):
        return k & ~1
    if mut("base_64b", vs) and not vs:
        return k & ~15
    return k


def base_readback(k: int, tramp: str, vs: bool) -> str:
    return f"{tramp}+{4 * base_entry(k, vs)}"


def ebreak_win(t: SvTest, mode: str, k: int, desc: str) -> None:
    """ebreak in `mode` (entered from HS/S with sret, left with T-SBI) must enter trampoline entry k."""
    lab = t.label(f"ebreak_{mode}")
    t.allow(1)
    if mode != t.cur:
        t.enter(mode)
    t.emit(f"{lab}:", 0)
    t.emit("ebreak")
    if mode != t.cur:
        t.leave()
    outcome_at(t, BREAKPOINT, lab, f"{desc}: ebreak in {mode}-mode", epc=lab, origin=mode)
    check_vect(t, k, lab, f"{desc}: ebreak in {mode}-mode")


def ssi_win(t: SvTest, k: int, desc: str, mode: str = "S") -> None:
    """A supervisor software interrupt taken in S-mode (from S or U) must enter trampoline entry k. The rule is
    not about timing, so the interrupt has a bounded wait to be taken (before Priv-v1.12 it need not be taken
    right after the enabling write or SRET)."""
    t.emit("csrci sstatus, 2  // SIE = 0 while SSIP is raised")
    t.emit(f"li x7, {SIP_SSIP}")
    t.emit("csrs sie, x7  // SSIE = 1")
    t.emit("csrs sip, x7  // SSIP = 1 (pending, masked by SIE)")
    lab = t.label(f"ssi_{mode}")
    t.allow(1)
    if mode == "S":
        t.emit(f"{lab}:", 0)
        t.emit("csrsi sstatus, 2  // SIE = 1: the interrupt is taken here")
        t.emit("nop")
        delay(t, 100)
    else:
        t.enter(mode)
        t.emit(f"{lab}:", 0)
        t.emit("nop")
        delay(t, 100)
        t.leave()
    t.emit(f"li x7, {SIP_SSIP}")
    t.emit("csrc sip, x7")
    t.emit("csrc sie, x7")
    outcome_at(t, icause(1), lab, f"{desc}: supervisor software interrupt from {mode}-mode", origin=mode)
    exp = k + 1 if MUT == "direct_int_vectored" else k
    check_vect(t, exp, lab, f"{desc}: supervisor software interrupt from {mode}-mode")
    t.emit("csrsi sstatus, 2  // SIE = 1 (framework default)")


def vssi_win(t: SvTest, k: int, desc: str, mode: str = "VS") -> None:
    """A VS-level software interrupt (hvip.VSSIP, delegated by hideleg) taken in VS-mode must enter vstvec entry
    k."""
    t.emit("li x7, 4")
    t.emit("csrs 0x603, x7  // hideleg.VSSI = 1")
    t.emit("li x7, 2")
    t.emit("csrs 0x204, x7  // vsie.SSIE = 1")
    t.emit("csrs 0x200, x7  // vsstatus.SIE = 1")
    t.emit("li x7, 4")
    t.emit("csrs 0x645, x7  // hvip.VSSIP = 1: taken as soon as VS/VU runs")
    lab = t.label(f"vssi_{mode}")
    t.allow(1)
    t.enter(mode)
    t.emit(f"{lab}:", 0)
    t.emit("nop")
    t.leave()
    t.emit("li x7, 4")
    t.emit("csrc 0x645, x7  // hvip.VSSIP = 0")
    t.emit("csrc 0x603, x7  // hideleg.VSSI = 0")
    t.emit("li x7, 2")
    t.emit("csrc 0x204, x7  // vsie.SSIE = 0")
    t.emit("csrc 0x200, x7  // vsstatus.SIE = 0")
    outcome_at(t, icause(1), lab, f"{desc}: VS software interrupt from {mode}-mode", origin=mode, handler="VS")
    exp = k + 1 if MUT == "vs_direct_int_vectored" else k
    check_vect(t, exp, lab, f"{desc}: VS software interrupt from {mode}-mode")


def gen_tvec() -> list[TestFile]:
    tests = []
    for vs in (False, True):
        c = tvec_ctx(vs)
        suite = "Shvstvecd" if vs else "Sstvecd"
        req = ["I", "S", "H", suite] if vs else ["I", "S", suite]
        csr, name, tramp = c["csr"], c["name"], c["tramp"]
        src = f"src/priv/{suite.lower()}.adoc"
        ctx_common = (
            f"The framework's {'VS' if vs else 'S'}-mode trap entry ({tramp}) is a spreader of jumps, one per "
            f"4-byte entry, each to its own stub, and the trap log records which entry ran. So with {name} = "
            f"{tramp} + 4k in Direct mode, a trap must run entry k: that shows the hart used every BASE bit and "
            "added no cause offset. "
            + (
                "VS-mode traps are an ebreak in VS/VU with hedeleg[3]=1 (the framework sets hedeleg to 0), and a "
                "VS software interrupt from hvip.VSSIP with hideleg[2]=1, vsie.SSIE=1 and vsstatus.SIE=1. "
                if vs
                else "S-mode traps are ebreak (delegated by medeleg[3]) from S and U, and a supervisor software "
                "interrupt (sip.SSIP). "
            )
            + f"The framework's {name} value is saved in x9 and restored at the end; traps in between use only "
            "the framework's own handler code."
        )

        def setup(t: SvTest, vs: bool = vs) -> None:
            t.emit(f"csrr x9, {csr}  // framework {name}, restored at the end")
            if vs:
                t.emit(f"li x7, {VS_HANDLER_DELEG}")
                t.emit("csrs 0x602, x7  // hedeleg[3] = 1: ebreak in VS/VU goes to the VS handler")

        def teardown(t: SvTest, vs: bool = vs) -> None:
            t.emit(f"csrw {csr}, x9  // restore the framework {name}")
            if vs:
                t.emit(f"li x7, {VS_HANDLER_DELEG}")
                t.emit("csrc 0x602, x7  // hedeleg[3] = 0")

        def traps(t: SvTest, k: int, desc: str, vs: bool = vs) -> None:
            if vs:
                for m in ("VS", "VU"):
                    ebreak_win(t, m, k, desc)
                vssi_win(t, k, desc, "VS")
            else:
                ebreak_win(t, "S", k, desc)
                ebreak_win(t, "U", k, desc)
                ssi_win(t, k, desc, "S")
                with t.only_if(H):
                    ebreak_win(t, "VS", k, desc + " (to HS-mode)")

        # ---- MODE = Direct
        rule = f"{suite}_{name}_mode_direct"
        t = new(suite, rule, req)
        t.describe(
            source=src,
            rule_text=f"If the {suite} extension is implemented, then `{name}.MODE` must be capable of holding the "
            "value 0 (Direct).",
            context=ctx_common
            + f" A {name} write with MODE=1 (Vectored) is WARL: it may read back Vectored or another legal "
            "value, and both cases are followed.",
            plan=f"1. Write {name} = {tramp} (MODE 0): it reads back exactly.\n"
            f"2. Exceptions and the software interrupt enter entry 0 (Direct: every trap goes to BASE).\n"
            f"3. Write {name} = {tramp} | 1. If it reads Vectored, the software interrupt enters entry 1 (the "
            "contrast), and exceptions still enter entry 0.\n"
            f"4. Write {name} = {tramp} again (MODE 0 after Vectored): it reads back exactly, and the software "
            "interrupt enters entry 0 again.",
        )
        setup(t)

        def direct_checks(t: SvTest, tag: str, vs: bool = vs, csr: str = csr, tramp: str = tramp) -> None:
            lab = t.label("direct")
            t.la("x8", tramp)
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {csr}, x8")
            t.emit(f"csrr x7, {csr}")
            exp = f"{tramp}+1" if (tag == "again" and mut("mode0_lost", vs)) else tramp
            t.check("x7", exp, lab, f"{name} = {tramp} with MODE=0 ({tag}) reads back unchanged")
            traps(t, 0, f"Direct mode ({tag})")

        direct_checks(t, "first")
        t.comment(f"Vectored, if {name}.MODE can hold 1")
        t.la("x8", tramp)
        t.emit("ori x8, x8, 1")
        lab = t.label("vec")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrw {csr}, x8")
        t.emit(f"csrr x7, {csr}")
        t.emit("andi x1, x7, 3")
        t.emit("addi x1, x1, -1")
        t.emit("seqz x1, x1  // x1 = MODE reads Vectored")

        def vectored(t: SvTest = t, vs: bool = vs) -> None:
            if vs:
                ebreak_win(t, "VS", 0, "Vectored mode exception")
                vssi_win(t, 1, "Vectored mode (contrast)", "VS")
            else:
                ebreak_win(t, "S", 0, "Vectored mode exception")
                ssi_win(t, 1, "Vectored mode (contrast)", "S")

        t.either("x1", vectored, lambda: None)
        direct_checks(t, "again")
        teardown(t)
        tests.append(t)

        # ---- BASE holds any 4-byte-aligned address (Direct)
        rule = f"{suite}_{name}_base_aligned_address"
        t = new(suite, rule, req)
        ks = [1, 2, 3, 5, 7, 8, 13, 16, 21, 23]
        trap_ks = [3, 21] if not vs else [3, 13]
        t.describe(
            source=src,
            rule_text=f"Furthermore, when `{name}.MODE`=Direct, `{name}.BASE` must be capable of holding any valid "
            "four-byte-aligned address.",
            context=ctx_common + " Only addresses inside the test image are known to be valid "
            f"({ISSUE}3424: checking a small set of known-valid addresses suffices).",
            plan=f"1. For k in {ks}: write {name} = {tramp} + 4k (Direct). It reads back exactly, and an ebreak in "
            f"{'VS' if vs else 'S'}-mode enters entry k (address bits 2-6 all used).\n"
            f"2. For k in {trap_ks}: every trap source of the Direct test "
            f"({'ebreak in VS and VU, VS software interrupt' if vs else 'ebreak in S, U (and VS with H), SSI'}) "
            "enters entry k.\n"
            "3. Read-back only (no trap in between, framework value restored at once): rvtest_code_begin + 4 and "
            "+ 0x24, ai_table + 4 and + 0x1c, rvtest_data_begin + 0xc, and the end of the test code - 4.",
        )
        setup(t)
        for k in ks:
            lab = t.label(f"base{k}")
            t.la("x8", f"{tramp}+{4 * k}")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {csr}, x8")
            t.emit(f"csrr x7, {csr}")
            t.check("x7", base_readback(k, tramp, vs), lab, f"{name} = {tramp} + {4 * k} (Direct) reads back")
            if k in trap_ks:
                traps(t, base_entry(k, vs), f"BASE = {tramp} + {4 * k}")
            else:
                ebreak_win(t, "VS" if vs else "S", base_entry(k, vs), f"BASE = {tramp} + {4 * k}")
        for sym in (
            "rvtest_code_begin+4",
            "rvtest_code_begin+0x24",
            "ai_table+4",
            "ai_table+0x1c",
            "rvtest_data_begin+0xc",
            "rvtest_code_end-4",
        ):
            lab = t.label("rb")
            t.la("x8", sym)
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {csr}, x8")
            t.emit(f"csrr x7, {csr}")
            t.emit(f"csrw {csr}, x9  // restore at once")
            exp = sym
            if mut("base_bit2_ro0", vs) and sym.endswith(("+4", "+0x1c", "+0xc", "-4")):
                exp = sym + "-4"
            t.check("x7", exp, lab, f"{name} = {sym} (Direct) reads back")
        teardown(t)
        tests.append(t)
    return tests


# ================================================================ Sstvala
SSTVALA = "src/priv/sstvala.adoc"


def mwin(
    t: SvTest,
    pt: SvPT | None,
    mode: str,
    lines: list[str],
    expect: Expect,
    desc: str,
    tvals: dict,
    epc: Value | None = "insn",
    tval2s: dict | None = None,
    handler: str | None = None,
) -> str:
    """Run lines in `mode` (S; U through pt's user alias, or at the physical address when pt is None; VS/VU with
    sret) in a trap window and check the outcome with per-cause xtval values. epc="insn": the first line."""
    lab = t.label(f"in_{mode}")
    t.allow(1)
    if mode == "U" and pt is not None:
        enter_u_alias(t, pt, lab)
    elif mode != t.cur:
        t.enter(mode)
    t.emit(f"{lab}:", 0)
    for ln in lines:
        t.emit(ln)
    if mode != t.cur:
        t.leave()
    if epc == "insn":
        epc = f"{lab}+{hex(pt.delta)}" if (mode == "U" and pt is not None) else lab
    outcome_cases(t, expect, lab, f"{desc} in {mode}-mode", tvals, epc=epc, origin=mode, tval2s=tval2s, handler=handler)
    return lab


def addr(base: int | str, off: int) -> int | str:
    if isinstance(base, int):
        return base + off
    return f"{base}+{off}" if off >= 0 else f"{base}{off}"


def tv_mis(base: int | str, off: int, size: int) -> int | str:
    """stval for a misaligned access (or the access fault raised for it) at base+off: the address."""
    if MUT == "tval_zero_misaligned":
        return 0
    if MUT == "tval_aligned_down":
        return addr(base, off & ~(size - 1))
    return addr(base, off)


def tv_amis(base: int | str, off: int, size: int) -> object:
    """stval for an access fault on a misaligned access at base+off: the address of the portion that faulted, so any
    address inside the access (stval_op_load_store_fault)."""
    if MUT == "tval_zero_misaligned":
        return 0
    if MUT == "tval_aligned_down":
        return addr(base, off & ~(size - 1))
    return ("range", addr(base, off), size)


def tv_af(v: int | str) -> int | str:
    return 0 if MUT == "tval_zero_access" else v


def tv_pf(va: int, mode: str) -> int:
    if MUT == "tval_zero_pf_u" and mode == "U":
        return 0
    if MUT == "tval_page_base":
        return va & ~0xFFF
    return va


LOADS = {"lb": 1, "lbu": 1, "lh": 2, "lhu": 2, "lw": 4, "ld": 8}
STORES = {"sb": 1, "sh": 2, "sw": 4, "sd": 8}


def gen_stvala() -> list[TestFile]:
    tests = []
    suite = "Sstvala"

    # ---------------------------------------------------------------- faulting virtual address
    t = new(suite, "Sstvala_stval_faulting_vaddr")
    t.describe(
        source=SSTVALA,
        rule_text="If the Sstvala extension is implemented, then `stval` must be written with the faulting virtual "
        "address for load, store, and instruction page-fault, access-fault, and misaligned exceptions, and for "
        "breakpoint exceptions that are defined to write an address to stval, other than those caused by execution "
        "of the `EBREAK` or `C.EBREAK` instructions.",
        context='Without Sstvala, stval may be 0 for all of these (supervisor.adoc stval_op_faulting_addr: "If '
        'stval is written with a nonzero value ..."). Here 0 is not accepted. Whether a misaligned access traps, and '
        "whether as misaligned or access fault, is still free, so each misaligned access accepts no trap, the "
        "misaligned cause (stval = the access's address) and the access-fault cause (stval = the address of the "
        "portion that faulted, so any address inside the access). For a misaligned "
        "access that crosses into a faulting page, stval_op_load_store_fault fixes the nonzero value: the address "
        "of the portion that faulted (the page boundary when the second page faults). Access faults use "
        "the configuration's access-fault address for each kind of access (RVMODEL_ACCESS_FAULT_ADDRESS_LOAD, "
        "_STORE, _FETCH; check_defines.h derives them from RVMODEL_ACCESS_FAULT_ADDRESS), which is 0 on most "
        "configurations, so the access-fault cases that prove a nonzero stval map a virtual page onto it. Breakpoints that write an address are Sdtrig mcontrol6 "
        "triggers with action 0 (Sdtrig_mcontrol6_faulting_address: the address being accessed); the triggers are "
        "programmed through T-SBI, and the cases run only if tdata1 accepts an mcontrol6 trigger with S=1.",
        plan="1. Bare: misaligned lh/lhu/lw/ld and sh/sw/sd (offsets 1-7) from S, and lw/sw from U: no trap, or "
        "misaligned (stval = the address) or access fault (stval inside the access). With Zalrsc, lr.w at offset 2 (must trap, 4 or 5); with "
        "Zaamo, amoadd.w at offset 2 (no trap, 6 or 7).\n"
        "2. Bare, with RVMODEL_ACCESS_FAULT_ADDRESS: lw, sw and a fetch there raise 5, 7 and 1 with stval = the "
        "address (the fetch also has sepc = the address).\n"
        "3. Without C: jalr to a 2-byte-aligned target raises instruction-address-misaligned with sepc = the jalr "
        "and stval = the target.\n"
        "4. Sv39/Sv32 (probed), from S and U: a load, store, AMO, LR and fetch to an invalid page raise page faults "
        "with stval = the exact address (byte offsets 0x123, 0x10, 0x100); lw/sw at the last two bytes of a valid "
        "page before an invalid one: 4/5/6/7 with stval = the address, or a page fault with stval = the page "
        "boundary; lw/sw at the last two bytes of an invalid page: any of those causes with stval = the address; "
        "a page mapped onto RVMODEL_ACCESS_FAULT_ADDRESS: lw, sw and fetch raise access faults with stval = the "
        "virtual address.\n"
        "5. With H, from VS-mode (taken in HS-mode, hgatp and vsatp Bare): a misaligned lw and an access fault at "
        "RVMODEL_ACCESS_FAULT_ADDRESS, with stval = the guest address.\n"
        "6. With Sdtrig: an execute trigger on a nop (sepc = stval = the nop) and a load-address trigger on an lw "
        "(stval = the load address).",
    )
    t.page("M")
    mbase = "ai_pg_M"

    def bare_ld(mode: str, insn: str, off: int, xlen_cond: str | None = None) -> None:
        size = LOADS[insn]
        t.la("x6", mbase)
        lab = mwin(
            t,
            None,
            mode,
            [f"{insn} x7, {off}(x6)"],
            ["ok", LOAD_MIS, LOAD_AF],
            f"{insn} at page+{off}",
            {LOAD_MIS: tv_mis(mbase, off, size), LOAD_AF: tv_amis(mbase, off, size)},
        )
        del lab

    def bare_st(mode: str, insn: str, off: int) -> None:
        size = STORES[insn]
        t.la("x6", mbase)
        t.emit("li x8, 0x5a")
        mwin(
            t,
            None,
            mode,
            [f"{insn} x8, {off}(x6)"],
            ["ok", STORE_MIS, STORE_AF],
            f"{insn} at page+{off}",
            {STORE_MIS: tv_mis(mbase, off, size), STORE_AF: tv_amis(mbase, off, size)},
        )

    t.comment("1. misaligned accesses, Bare")
    for insn, off in (("lh", 1), ("lhu", 3), ("lw", 1), ("lw", 2), ("lw", 3)):
        bare_ld("S", insn, off)
    with t.rv64_only():
        bare_ld("S", "ld", 4)
        bare_ld("S", "ld", 7)
    for insn, off in (("sh", 1), ("sw", 2), ("sw", 3)):
        bare_st("S", insn, off)
    with t.rv64_only():
        bare_st("S", "sd", 4)
    bare_ld("U", "lw", 1)
    bare_st("U", "sw", 3)
    with t.only_if("defined(ZALRSC_SUPPORTED)"):
        t.la("x6", f"{mbase}+2")
        mwin(
            t,
            None,
            "S",
            [word(lr_w(7, 6), "lr.w x7, (x6)")],
            [LOAD_MIS, LOAD_AF],
            "lr.w at page+2",
            {LOAD_MIS: tv_mis(mbase, 2, 4), LOAD_AF: tv_amis(mbase, 2, 4)},
        )
    with t.only_if("defined(ZAAMO_SUPPORTED)"):
        t.la("x6", f"{mbase}+2")
        t.emit("li x8, 1")
        mwin(
            t,
            None,
            "S",
            [word(amoadd_w(7, 6, 8), "amoadd.w x7, x8, (x6)")],
            ["ok", STORE_MIS, STORE_AF],
            "amoadd.w at page+2",
            {STORE_MIS: tv_mis(mbase, 2, 4), STORE_AF: tv_amis(mbase, 2, 4)},
        )

    t.comment("2. access faults at RVMODEL_ACCESS_FAULT_ADDRESS, Bare")
    for mode in ("S", "U"):
        for kind, ln, c in (("load", "lw x7, 0(x6)", LOAD_AF), ("store", "sw x7, 0(x6)", STORE_AF)):
            fa = FA_KIND[kind]
            with t.only_if(HAS_FA_KIND[kind]):
                t.emit(f"LI(x6, {fa})", 2)
                mwin(t, None, mode, [ln], c, f"{ln.split()[0]} at the access-fault address", {c: tv_af(fa)})
    fa = FA_KIND["fetch"]
    with t.only_if(HAS_FA_KIND["fetch"]):
        t.emit(f"LI(x6, {fa})", 2)
        mwin(
            t, None, "S", ["jalr x1, 0(x6)"], INSN_AF, "fetch at the access-fault address", {INSN_AF: tv_af(fa)}, epc=fa
        )

    t.comment("3. instruction-address-misaligned (no C)")
    with t.only_if("!defined(ZCA_SUPPORTED) && !defined(C_SUPPORTED)"):
        tgt = t.label("mis_tgt")
        t.la("x6", f"{tgt}+2")
        lab = t.label("jalr_mis")
        t.allow(1)
        t.emit(f"{lab}:", 0)
        t.emit("jalr x1, 0(x6)")
        t.emit(f"j {tgt}_after")
        t.emit(f"{tgt}:", 0)
        t.emit("nop")
        t.emit("nop")
        t.emit(f"{tgt}_after:", 0)
        outcome_cases(
            t,
            INSN_MIS,
            lab,
            "jalr to a 2-byte-aligned target",
            {INSN_MIS: lab if MUT == "tval_insn_mis_link" else f"{tgt}+2"},
            epc=lab,
            origin="S",
        )

    t.comment("4. paging")

    def fa_leaf(pt: SvPT, va: int, perms: int, kind: str) -> None:
        """Map va to the page of the access-fault address for `kind` (load, store, fetch)."""
        tab = pt.pointer(va, pt.depth(0))
        t.comment(f"{pt.name}: {hex(va)} -> the page of {FA_KIND[kind]}")
        t.emit(f"LI(x6, {FA_KIND[kind]})", 2)
        t.emit("srli x6, x6, 12")
        t.emit("slli x6, x6, 10")
        t.emit(f"li x7, {hex(perms)}")
        t.emit("or x6, x6, x7")
        pt._store(tab, pt.idx(va, pt.depth(0)))

    def paging(xlen: int, part: str) -> None:
        def inner(pt: SvPT) -> None:
            va = VA_T[xlen]
            for base, perms in ((va, LEAF), (va + 0x8000, ULEAF)):
                pt.raw(base, 0, note="invalid")
                pt.leaf(base + 0x1000, t.page("P"), perms)
                pt.raw(base + 0x2000, 0, note="invalid")
                if part.startswith("fa_"):
                    fa_leaf(pt, base + 0x3000, perms, part[3:])
            pt.on()
            for mode, base in (("S", va), ("U", va + 0x8000)):
                if part == "base":
                    t.emit(f"li x6, {hex(base + 0x123)}")
                    mwin(
                        t, pt, mode, ["lb x7, 0(x6)"], LOAD_PF, "lb, invalid page", {LOAD_PF: tv_pf(base + 0x123, mode)}
                    )
                    t.emit(f"li x6, {hex(base)}")
                    mwin(
                        t,
                        pt,
                        mode,
                        ["sw x7, 16(x6)"],
                        STORE_PF,
                        "sw, invalid page",
                        {STORE_PF: tv_pf(base + 0x10, mode)},
                    )
                    t.emit(f"li x6, {hex(base)}")
                    mwin(
                        t,
                        pt,
                        mode,
                        ["jalr x1, 0x100(x6)"],
                        INSN_PF,
                        "fetch, invalid page",
                        {INSN_PF: tv_pf(base + 0x100, mode)},
                        epc=base + 0x100,
                    )
                    b2 = base + 0x2000
                    strad = b2 if MUT != "tval_straddle_start" else base + 0x1FFE
                    for insn, causes in (
                        ("lw x7, 0(x6)", (LOAD_MIS, LOAD_AF, LOAD_PF)),
                        ("sw x8, 0(x6)", (STORE_MIS, STORE_AF, STORE_PF)),
                    ):
                        misal, af, pf_ = causes
                        t.emit(f"li x6, {hex(base + 0x1FFE)}")
                        t.emit("li x8, 0x77")
                        mwin(
                            t,
                            pt,
                            mode,
                            [insn],
                            list(causes),
                            f"{insn.split()[0]} across a valid page into an invalid one",
                            {misal: tv_mis(base + 0x1FFC, 2, 4), af: tv_amis(base + 0x1FFC, 2, 4), pf_: strad},
                        )
                        t.emit(f"li x6, {hex(base + 0xFFE)}")
                        mwin(
                            t,
                            pt,
                            mode,
                            [insn],
                            list(causes),
                            f"{insn.split()[0]} across an invalid page into a valid one",
                            {
                                misal: tv_mis(base + 0xFFC, 2, 4),
                                af: tv_amis(base + 0xFFC, 2, 4),
                                pf_: tv_pf(base + 0xFFE, mode),
                            },
                        )
                elif part == "amo":
                    t.emit(f"li x6, {hex(base + 0x20)}")
                    mwin(
                        t,
                        pt,
                        mode,
                        [word(amoadd_w(7, 6, 8), "amoadd.w x7, x8, (x6)")],
                        STORE_PF,
                        "amoadd.w, invalid page",
                        {STORE_PF: tv_pf(base + 0x20, mode)},
                    )
                elif part == "lr":
                    t.emit(f"li x6, {hex(base + 0x28)}")
                    mwin(
                        t,
                        pt,
                        mode,
                        [word(lr_w(7, 6), "lr.w x7, (x6)")],
                        LOAD_PF,
                        "lr.w, invalid page",
                        {LOAD_PF: tv_pf(base + 0x28, mode)},
                    )
                else:
                    ln, c = {
                        "fa_load": ("lw x7, 0(x6)", LOAD_AF),
                        "fa_store": ("sw x7, 0(x6)", STORE_AF),
                        "fa_fetch": ("jalr x1, 0(x6)", INSN_AF),
                    }[part]
                    fva = f"{hex(base + 0x3000)}+({FA_KIND[part[3:]]}&0xFFF)"
                    t.emit(f"LI(x6, {fva})", 2)
                    mwin(
                        t,
                        pt,
                        mode,
                        [ln],
                        c,
                        f"{ln.split()[0]} through a page mapped to the access-fault address",
                        {c: tv_af(fva)},
                        epc=fva if c == INSN_AF else "insn",
                    )

        with_vm(t, xlen, inner, user=True, name=f"p{xlen}{part}")

    t.page("P")
    for part, cond in (
        ("base", None),
        ("amo", "defined(ZAAMO_SUPPORTED)"),
        ("lr", "defined(ZALRSC_SUPPORTED)"),
        *((f"fa_{k}", HAS_FA_KIND[k]) for k in FA_KIND),
    ):
        if cond:
            with t.only_if(cond):
                both(t, lambda x, part=part: paging(x, part))
        else:
            both(t, lambda x, part=part: paging(x, part))

    t.comment("5. VS-mode traps taken in HS-mode (hgatp and vsatp Bare)")
    with t.only_if(H):
        t.la("x6", mbase)
        mwin(
            t,
            None,
            "VS",
            ["lw x7, 1(x6)"],
            ["ok", LOAD_MIS, LOAD_AF],
            "lw at page+1",
            {LOAD_MIS: tv_mis(mbase, 1, 4), LOAD_AF: tv_amis(mbase, 1, 4)},
        )
        with t.only_if(HAS_FA_KIND["load"]):
            t.emit(f"LI(x6, {FA_KIND['load']})", 2)
            mwin(
                t,
                None,
                "VS",
                ["lw x7, 0(x6)"],
                LOAD_AF,
                "lw at the access-fault address",
                {LOAD_AF: tv_af(FA_KIND["load"])},
            )

    t.comment("6. Sdtrig mcontrol6 address triggers (action 0)")
    with t.only_if("defined(SDTRIG_SUPPORTED)"):
        for kind in ("execute", "load"):
            tgt = t.label(f"trig_{kind}")
            bits = (1 << 4) | (1 << 2 if kind == "execute" else 1)
            mc6 = X((6 << 28) | bits, (6 << 60) | bits)
            t.tsbi_csr("WRITE", "TSELECT", imm=0)
            t.tsbi_csr("WRITE", "TDATA1", imm=0)
            t.la("a1", tgt if kind == "execute" else f"{mbase}+8")
            t.tsbi_csr("WRITE", "TDATA2", "a1")
            t.load("a1", mc6, f"mcontrol6: {kind}, S=1, match equal, action 0")
            t.tsbi_csr("WRITE", "TDATA1", "a1")
            t.tsbi_csr("READ", "TDATA1")
            t.load("x7", mc6)
            t.emit("xor x1, a0, x7")
            t.emit("seqz x1, x1  // x1 = tdata1 holds the trigger")

            def run(kind: str = kind, tgt: str = tgt) -> None:
                t.la("x6", mbase)
                t.allow(1)
                t.emit(f"{tgt}:", 0)
                t.emit("nop" if kind == "execute" else "lw x7, 8(x6)")
                t.emit("nop")
                tv = 0 if MUT == "tval_zero_trigger" else (tgt if kind == "execute" else f"{mbase}+8")
                outcome_cases(
                    t,
                    BREAKPOINT,
                    tgt,
                    f"{kind} trigger",
                    {BREAKPOINT: tv},
                    epc=tgt if kind == "execute" else None,
                    origin="S",
                )

            t.either("x1", run, lambda: None)
            t.tsbi_csr("WRITE", "TDATA1", imm=0)
    tests.append(t)

    # ---------------------------------------------------------------- faulting instruction
    t = new(suite, "Sstvala_stval_faulting_instruction")
    t.describe(
        source=SSTVALA,
        rule_text="For virtual-instruction and illegal-instruction exceptions, `stval` must be written with the "
        "faulting instruction.",
        context="Without Sstvala, stval may be 0 (stval_op_illegal_instr); here only the instruction bits are "
        "accepted. A 16-bit instruction is reported zero-extended (stval_instr_bits_sz). Instructions are .word "
        "encodings that must trap: privileged instructions and CSR accesses beyond the current mode, writes to "
        "a read-only CSR, SFENCE.VMA with mstatus.TVM=1, and, with C and D, C.FLDSP with sstatus.FS=Off. With H, "
        "virtual-instruction exceptions (VS/VU accesses that HS-mode could make) and illegal-instruction "
        "exceptions from VS-mode are taken in HS-mode, where stval is checked. On configurations that use the "
        "framework's invisible trap handler, S-mode illegal-instruction traps are forwarded by M-mode, which "
        "writes stval itself.",
        plan="1. S-mode: mret, csrrs mstatus, csrrsi x15, mhartid, 31, csrrwi x0, cycle, 31, csrrw mscratch, and "
        "sfence.vma with TVM=1 (if TVM can be set): illegal instruction with stval = the encoding.\n"
        "2. U-mode: sret, mret, csrrs sstatus, csrrw sscratch, csrrsi mstatus, 31, sfence.vma: the same.\n"
        "3. With C and D: C.FLDSP f8 with FS=Off in S and U: stval = 0x2402 (16 bits, zero-extended).\n"
        "4. With H: VS csrrs hstatus and hfence.vvma, VU csrrs sstatus and sret: virtual instruction with "
        "stval = the encoding; VS and VU mret and csrrs mstatus: illegal instruction with stval = the encoding.",
    )

    def ill(mode: str, e: int, note: str, cause: int = ILLEGAL, pre: list | None = None) -> None:
        for ln in pre or []:
            t.emit(ln)
        z = (
            (MUT == "tval_zero_illegal" and mode == "S" and cause == ILLEGAL)
            or (MUT == "tval_zero_illegal_u" and mode == "U")
            or (MUT == "tval_zero_virtual" and cause == VIRTUAL)
        )
        mwin(t, None, mode, [word(e, note)], cause, note, {cause: 0 if z else e})

    t.emit("li x6, 0x55")
    for e, note in (
        (0x30200073, "mret"),
        (enc_csr(0x300, 2, 7, 0), "csrrs x7, mstatus, x0"),
        (enc_csr(0xF14, 6, 15, 31), "csrrsi x15, mhartid, 31"),
        (enc_csr(0xC00, 5, 0, 31), "csrrwi x0, cycle, 31 (read-only CSR)"),
        (enc_csr(0x340, 1, 7, 6), "csrrw x7, mscratch, x6"),
    ):
        ill("S", e, note)
    t.tsbi_csr("SET", "MSTATUS", imm=1 << 20)
    t.tsbi_csr("READ", "MSTATUS")
    t.emit("srli x1, a0, 20")
    t.emit("andi x1, x1, 1  // TVM may be read-only 0 (mstatus_tvm_acc)")
    t.either("x1", lambda: ill("S", 0x12000073, "sfence.vma x0, x0 with mstatus.TVM=1"), lambda: None)
    t.tsbi_csr("CLEAR", "MSTATUS", imm=1 << 20)
    for e, note in (
        (0x10200073, "sret"),
        (0x30200073, "mret"),
        (enc_csr(0x100, 2, 7, 0), "csrrs x7, sstatus, x0"),
        (enc_csr(0x140, 1, 7, 6), "csrrw x7, sscratch, x6"),
        (enc_csr(0x300, 6, 1, 31), "csrrsi x1, mstatus, 31"),
        (0x12000073, "sfence.vma x0, x0"),
    ):
        ill("U", e, note)
    with t.only_if("defined(ZCA_SUPPORTED) && defined(ZCD_SUPPORTED)"):
        t.li("x7", 0x6000)
        t.emit("csrc sstatus, x7  // FS = Off")
        for mode in ("S", "U"):
            z = (MUT == "tval_zero_illegal" and mode == "S") or (MUT == "tval_zero_illegal_u" and mode == "U")
            mwin(
                t,
                None,
                mode,
                [half(0x2402, "c.fldsp f8, 0(sp)"), half(0x0001, "c.nop")],
                ILLEGAL,
                "c.fldsp with FS=Off",
                {ILLEGAL: 0 if z else (0x00012402 if MUT == "tval_parcel32" else 0x2402)},
            )
        t.li("x7", 0x6000)
        t.emit("csrs sstatus, x7  // FS = Dirty (framework default)")
    with t.only_if(H):
        ill("VS", enc_csr(0x600, 2, 7, 0), "csrrs x7, hstatus, x0", VIRTUAL)
        ill("VS", 0x22000073, "hfence.vvma x0, x0", VIRTUAL)
        ill("VU", enc_csr(0x100, 2, 7, 0), "csrrs x7, sstatus, x0", VIRTUAL)
        ill("VU", 0x10200073, "sret", VIRTUAL)
        ill("VS", 0x30200073, "mret")
        ill("VS", enc_csr(0x300, 2, 7, 0), "csrrs x7, mstatus, x0")
        ill("VU", 0x30200073, "mret")
        ill("VU", enc_csr(0x300, 2, 7, 0), "csrrs x7, mstatus, x0")
    tests.append(t)

    # ---------------------------------------------------------------- variable-length instruction fetch faults
    t = new(suite, "stval_faulting_address_variable_instr", ["I", "S", suite, "Zca"])
    t.describe(
        source=SUP,
        rule_text="If `stval` is written with a nonzero value when an instruction access-fault, page-fault, or "
        "hardware-error exception occurs on a hart with variable-length instructions, then `stval` will contain "
        "the virtual address of the portion of the instruction that caused the fault, while `sepc` will point to "
        "the beginning of the instruction.",
        context="The rule is in supervisor.adoc and is conditional on a nonzero stval. Sstvala makes stval "
        "nonzero for these faults, so with Sstvala the rule fixes the value; the test lives in this suite. A "
        "32-bit instruction (addi x7, x0, 1) starts 2 bytes before the end of a valid page; its second half is in "
        "an invalid page (page fault) or in a page mapped onto RVMODEL_ACCESS_FAULT_ADDRESS (access fault, only "
        "when that address is page-aligned, so the second half's physical address is the one known to fault). "
        "The framework resumes a fetch fault at ra.",
        plan="1. Sv39/Sv32 (probed), from S and U: jalr to the last 2 bytes of a valid page followed by an invalid "
        "page: instruction page fault with sepc = the instruction and stval = the page boundary.\n"
        "2. The same with the second page mapped onto RVMODEL_ACCESS_FAULT_ADDRESS (page-aligned only): "
        "instruction access fault, stval = the page boundary.\n"
        "3. Contrast: the instruction starting 2 bytes before the end of an invalid page that precedes a valid one: "
        "page fault with stval = sepc = the instruction.\n"
        "4. The valid page is executable: its stub runs (x7 = its id).",
    )
    page_fa = f"{HAS_FA_KIND['fetch']} && (({FA_KIND['fetch']} & 0xFFF) == 0)"

    def var(xlen: int, fa: bool) -> None:
        def inner(pt: SvPT) -> None:
            va = VA_T[xlen]
            pg = t.page("F", {0xFFE: (2, 0x0393)})
            for base, perms in ((va, LEAF), (va + 0x8000, ULEAF)):
                pt.raw(base, 0, note="invalid")
                pt.leaf(base + 0x1000, pg, perms)
                if fa:
                    fa_leaf(pt, base + 0x2000, perms, "fetch")
                else:
                    pt.raw(base + 0x2000, 0, note="invalid")
            pt.on()
            for mode, base in (("S", va), ("U", va + 0x8000)):
                start = base + 0x1FFE
                if not fa:
                    t.emit(f"li x6, {hex(base + 0x1000)}")
                    t.emit("li x7, 0")
                    lab = mwin(t, pt, mode, ["jalr x1, 0x100(x6)"], "ok", "the valid page's stub", {})
                    t.check("x7", t.page_id("F"), lab, f"{mode}-mode: the valid page is executable")
                    t.emit(f"li x6, {hex(start)}")
                    mwin(
                        t,
                        pt,
                        mode,
                        ["jalr x1, 0(x6)"],
                        INSN_PF,
                        "32-bit instruction whose second half is in an invalid page",
                        {INSN_PF: start if MUT == "tval_fetch_start" else base + 0x2000},
                        epc=start,
                    )
                    t.emit(f"li x6, {hex(base + 0xFFE)}")
                    mwin(
                        t,
                        pt,
                        mode,
                        ["jalr x1, 0(x6)"],
                        INSN_PF,
                        "instruction at the end of an invalid page",
                        {INSN_PF: base + 0xFFE},
                        epc=base + 0xFFE,
                    )
                else:
                    t.emit(f"li x6, {hex(start)}")
                    mwin(
                        t,
                        pt,
                        mode,
                        ["jalr x1, 0(x6)"],
                        INSN_AF,
                        "32-bit instruction whose second half is in a page mapped to the access-fault address",
                        {INSN_AF: start if MUT == "tval_fetch_start" else base + 0x2000},
                        epc=start,
                    )

        with_vm(t, xlen, inner, user=True, name=f"p{xlen}{'fa' if fa else ''}")

    both(t, lambda x: var(x, False))
    with t.only_if(page_fa):
        both(t, lambda x: var(x, True))
    tests.append(t)
    return tests


# ================================================================ Ssu64xl
UXL_SHIFT = 32


def gen_ssu64xl() -> list[TestFile]:
    t = new("Ssu64xl", "Ssu64xl_uxl_sstatus", rv64=True)
    t.describe(
        source="src/priv/ssu64xl.adoc",
        rule_text="If the Ssu64xl extension is implemented, then `sstatus.UXL` must be capable of holding the value "
        "2 (i.e., UXLEN=64 must be supported).",
        context="UXL is sstatus bits 33:32 (RV64 only; the file passes trivially on RV32). It is WARL: 1 (32) is "
        "optional, 0 and 3 are not legal values (mstatus_sxl_uxl_enc: the misa.MXL encoding, where 3 is reserved). "
        "UXL may be read-only 2. UXLEN=64 is checked by running RV64-only behavior in U-mode: a 64-bit shift and "
        "ADDIW. The framework's sstatus is saved in x9 and restored.",
        plan="1. Write UXL=2 with csrrs/csrrc and with csrrw of the whole sstatus: it reads 2, in sstatus and in "
        "mstatus (T-SBI).\n"
        "2. U-mode: li -1; srli 32 gives 0xffffffff, and addiw of it plus 1 gives 0 (RV64 semantics).\n"
        "3. Write UXL=1: it reads 1 or 2. If 1, write 2 again: it reads 2, and U-mode is 64-bit again (U-mode is "
        "never entered with UXL=1).\n"
        "4. Write UXL=0 and UXL=3: each reads back 1 or 2, then UXL=2 reads 2.\n"
        "5. Write mstatus.UXL=2 through T-SBI: sstatus.UXL reads 2.",
    )
    t.emit("csrr x9, sstatus  // framework sstatus, restored at the end")

    def uxl_write(v: int, form: str) -> None:
        t.emit(f"li x6, {3 << UXL_SHIFT:#x}")
        if form == "setclr":
            t.emit("csrc sstatus, x6")
            if v:
                t.emit(f"li x6, {v << UXL_SHIFT:#x}")
                t.emit("csrs sstatus, x6")
        else:
            t.emit("csrr x7, sstatus")
            t.emit("not x6, x6")
            t.emit("and x7, x7, x6")
            t.emit(f"li x6, {v << UXL_SHIFT:#x}")
            t.emit("or x7, x7, x6")
            t.emit("csrw sstatus, x7")

    def uxl_read(reg: str = "x7") -> None:
        t.emit(f"csrr {reg}, sstatus")
        t.emit(f"srli {reg}, {reg}, {UXL_SHIFT}")
        t.emit(f"andi {reg}, {reg}, 3")

    def u64(tag: str) -> None:
        lab = t.label("u64")
        t.window("U", ["li x7, -1", "srli x7, x7, 32", "addiw x8, x7, 1"], "ok", f"RV64 code in U ({tag})")
        exp = 0 if MUT == "u_32bit" else 0xFFFFFFFF
        t.emit(f"{lab}:", 0)
        t.check("x7", exp, lab, f"U-mode ({tag}): srli of -1 by 32 is 0xffffffff (UXLEN=64)")
        t.check("x8", 0, lab, f"U-mode ({tag}): addiw 0xffffffff + 1 = 0")

    want2 = 1 if MUT == "uxl_ro1" else 2
    for form in ("setclr", "csrw"):
        uxl_write(2, form)
        lab = t.label("w2")
        t.emit(f"{lab}:", 0)
        uxl_read()
        t.check("x7", want2, lab, f"sstatus.UXL = 2 written with {form} reads 2")
    t.tsbi_csr("READ", "MSTATUS")
    t.emit(f"srli x7, a0, {UXL_SHIFT}")
    t.emit("andi x7, x7, 3")
    lab = t.label("m")
    t.emit(f"{lab}:", 0)
    t.check("x7", want2, lab, "mstatus.UXL reads 2 (sstatus is a view of mstatus)")
    u64("UXL=2")
    uxl_write(1, "setclr")
    lab = t.label("w1")
    t.emit(f"{lab}:", 0)
    uxl_read()
    t.check("x7", [1, 2], lab, "sstatus.UXL = 1 reads a legal value (1 or 2)")
    uxl_write(2, "setclr")
    uxl_read()
    lab = t.label("back2")
    t.emit(f"{lab}:", 0)
    t.check("x7", want2, lab, "sstatus.UXL = 2 after UXL = 1 reads 2")
    u64("UXL=2 after UXL=1")
    for v in (0, 3):
        uxl_write(v, "csrw")
        lab = t.label(f"w{v}")
        t.emit(f"{lab}:", 0)
        uxl_read()
        t.check("x7", [v, v] if MUT == "uxl_rsv_kept" else [1, 2], lab, f"sstatus.UXL = {v} reads 1 or 2")
        uxl_write(2, "setclr")
        uxl_read()
        lab = t.label(f"after{v}")
        t.emit(f"{lab}:", 0)
        t.check("x7", want2, lab, f"sstatus.UXL = 2 after UXL = {v} reads 2")
    t.emit(f"li a1, {3 << UXL_SHIFT:#x}")
    t.tsbi_csr("CLEAR", "MSTATUS", "a1")
    t.emit(f"li a1, {2 << UXL_SHIFT:#x}")
    t.tsbi_csr("SET", "MSTATUS", "a1")
    uxl_read()
    lab = t.label("mw")
    t.emit(f"{lab}:", 0)
    t.check("x7", want2, lab, "mstatus.UXL = 2 written in M-mode: sstatus.UXL reads 2")
    u64("mstatus.UXL=2")
    t.emit("csrw sstatus, x9  // restore")
    return [t]


# ================================================================ Ssccptr
def gen_ssccptr() -> list[TestFile]:
    t = new("Ssccptr", "Ssccptr_memory_pte_reads")
    t.describe(
        source="src/priv/ssccptr.adoc",
        rule_text="If the Ssccptr extension is implemented, then main memory regions with both the cacheability "
        "and coherence PMAs must support hardware page-table reads.",
        context="The test image is in main memory, which is cacheable and coherent on every configuration, so "
        "page tables in its data section must be readable by the page-table walker: every access through them "
        "must translate (no access fault on the implicit read), and the walker must read what the last explicit "
        "store wrote (after SFENCE.VMA). Hardware page-table writes (A/D updates) are not required by Ssccptr, so "
        "every leaf has A=D=1. machine.adoc pma_vm_hw_tbl_acc only lets a region specify which walks it supports; "
        "it is not tested. Sv39 (RV64) or Sv32 (RV32), and Sv48/Sv57 where satp accepts them, are probed; with "
        "H, VS-stage and G-stage walks (HLV.W from HS-mode) are also made, with the G-stage mode probed.",
        plan="1. For each supported scheme: a 4 KiB leaf (a walk through every level) and a 2 MiB (4 MiB on Sv32) "
        "leaf; lw, sw and a fetch from S-mode, and lw from U-mode through U=1 leaves: all translate, and lw "
        "reads the mapped page's signature.\n"
        "2. Rewrite the 4 KiB leaf to point at another page, SFENCE.VMA, lw: reads the new page.\n"
        "3. With H: HLV.W (SPVP=1) through a VS-stage leaf at GPA_BASE mapped by G-stage: reads the page; the "
        "VS-stage tables are themselves read through G-stage.",
    )
    from svlib import EXEC_OFF, guard, lsig, register_alias, satp_off, unregister_alias
    from svlib import probe as sprobe

    t.page("A")
    t.page("B")
    t.page("C")

    def scheme_body(xlen: int, scheme: str) -> None:
        pt = SvPT(t, f"p{scheme}", scheme)
        pt.identity()
        pt.user_alias()

        def run() -> None:
            register_alias(t, pt)
            va = VA_T[xlen]
            pt.leaf(va, t.page("A"), LEAF)
            pt.leaf(va + 0x1000, t.page("A"), ULEAF)
            sp_lvl = 1
            sp_va = va + (0x40_0000 if xlen == 32 else 0x20_0000) * 2
            pt.leaf(sp_va, t.page("B"), LEAF, level=sp_lvl)
            pt.on()
            for v, page, mode, desc in ((va, "A", "S", "4 KiB leaf"), (va + 0x1000, "A", "U", "4 KiB U leaf")):
                t.emit(f"li x6, {hex(v)}")
                t.emit("li x7, 0")
                lab = mwin(
                    t, pt, mode, ["lw x7, 0(x6)"], "ok" if MUT != "walk_af" else LOAD_AF, f"{scheme} {desc}: lw", {}
                )
                t.check("x7", lsig(t.page_id(page)), lab, f"{scheme} {desc}: lw reads the page ({mode}-mode)")
            t.emit(f"li x6, {hex(va)}")
            t.emit("li x8, 0x3c3c")
            lab = mwin(t, pt, "S", ["sw x8, 0x40(x6)"], "ok", f"{scheme} 4 KiB leaf: sw", {})
            t.la("x6", "ai_pg_A+0x40")
            t.emit("lw x7, 0(x6)")
            t.check("x7", 0x3C3C, lab, f"{scheme} 4 KiB leaf: the store landed in the page")
            t.emit(f"li x6, {hex(va)}")
            t.emit("li x7, 0")
            lab = mwin(t, pt, "S", [f"jalr x1, {EXEC_OFF}(x6)"], "ok", f"{scheme} 4 KiB leaf: fetch", {})
            t.check("x7", t.page_id("A"), lab, f"{scheme} 4 KiB leaf: the fetch ran the page's stub")
            # superpage leaf: the page's offset inside the superpage
            t.la("x6", "ai_pg_B")
            t.emit(f"li x7, {hex((0x40_0000 if xlen == 32 else 0x20_0000) - 1)}")
            t.emit("and x6, x6, x7")
            t.emit(f"li x7, {hex(sp_va)}")
            t.emit("add x6, x6, x7")
            t.emit("li x7, 0")
            lab = mwin(t, pt, "S", ["lw x7, 0(x6)"], "ok", f"{scheme} superpage leaf: lw", {})
            t.check("x7", lsig(t.page_id("B")), lab, f"{scheme} superpage leaf: lw reads the page")
            pt.leaf(va, t.page("C"), LEAF, note="rewritten")
            t.emit("sfence.vma x0, x0")
            t.emit(f"li x6, {hex(va)}")
            t.emit("li x7, 0")
            lab = mwin(t, pt, "S", ["lw x7, 0(x6)"], "ok", f"{scheme} rewritten leaf: lw", {})
            exp = t.page_id("A") if MUT == "stale_pte" else t.page_id("C")
            t.check("x7", lsig(exp), lab, f"{scheme} rewritten 4 KiB leaf: lw reads the new page")
            satp_off(t)
            unregister_alias(t)

        sprobe(t, pt)
        guard(t, "x1", run)

    with t.rv64_only():
        for sch in ("sv39", "sv48", "sv57"):
            scheme_body(64, sch)
    with t.rv32_only():
        scheme_body(32, "sv32")

    with t.only_if(H):
        from hlib import hlsv
        from hmem import G_OF, GPA_BASE, PT, VA_BASE, VS_OF

        def hbody(xlen: int) -> None:
            g = PT(t, f"g{xlen}", G_OF[xlen], xlen)
            g.identity(ULEAF)
            gpa = GPA_BASE[xlen]
            g.leaf(gpa, t.page("A"), ULEAF)
            v = PT(t, f"v{xlen}", VS_OF[xlen], xlen)
            v.leaf(VA_BASE[xlen], gpa, LEAF)
            atp_probe(t, HGATP, g, "x1")
            atp_probe(t, VSATP, v, "x9")
            t.emit("and x1, x1, x9")

            def run() -> None:
                g.atp("x6")
                t.emit(f"csrw {hex(HGATP)}, x6")
                t.emit(HFENCE_GVMA)
                v.atp("x6")
                t.emit(f"csrw {hex(VSATP)}, x6")
                t.emit(HFENCE_VVMA)
                spvp(t, True)
                ln, _ = hlsv("hlv.w", "x7", "x6")
                t.emit(f"li x6, {hex(VA_BASE[xlen])}")
                t.emit("li x7, 0")
                lab = mwin(t, None, "S", [ln], "ok", "HLV.W through VS-stage and G-stage tables", {})
                t.check("x7", lsig(t.page_id("A")), lab, "HLV.W reads the page through two-stage tables")
                spvp(t, False)
                t.emit(f"csrw {hex(HGATP)}, x0")
                t.emit(f"csrw {hex(VSATP)}, x0")
                t.emit(HFENCE_GVMA)
                t.emit(HFENCE_VVMA)

            guard(t, "x1", run)

        both(t, hbody)
    return [t]


# ================================================================ Svvptc
def retry(
    t: SvTest,
    body: list[str],
    cmp: str,
    n: int,
    cause: int,
    desc: str,
    lab: str,
    enter: Callable[[], None] | None = None,
    exp: str = "x1",
) -> None:
    """Repeat body (which may fault; the handler resumes after it) until register cmp equals x1, at most n times,
    in a window that permits n traps. enter() switches to the mode the loop runs in (left with T-SBI). Then: the
    last trap (if any) was `cause`."""
    loop = t.label("retry")
    t.allow(n)
    if enter:
        enter()
    t.emit(f"{lab}:", 0)
    t.emit(f"li x9, {n}")
    t.emit(f"{loop}:", 0)
    for ln in body:
        t.emit(ln, n)
    t.emit(f"beq {cmp}, {exp}, {loop}_done", n)
    t.emit("addi x9, x9, -1", n)
    t.emit(f"bnez x9, {loop}", n)
    t.emit(f"{loop}_done:", 0)
    if enter:
        t.leave()
    t.emit("AI_OUTCOME", 20)
    from aigen import NO_TRAP

    t.check("x14", [NO_TRAP, cause], lab, f"{desc}: retries fault only with cause {cause} (or none)")


def gen_svvptc() -> list[TestFile]:
    t = new("Svvptc", "Svvptc_explicit_stores_update_valid_bit")
    n = 500
    t.describe(
        source="src/priv/svvptc.adoc",
        rule_text="When the Svvptc extension is implemented, explicit stores by a hart that update the Valid bit of "
        "leaf and/or non-leaf PTEs from 0 to 1 and are visible to a hart will eventually become visible within a "
        "bounded timeframe to subsequent implicit accesses by that hart to such PTEs.",
        context="Without Svvptc, a hart may keep using a cached invalid translation until SFENCE.VMA. With "
        f"Svvptc, the store of V=1 must take effect without a fence. Each case first accesses the page while "
        "its PTE is invalid (a page fault, which may cache the invalid entry), stores V=1 with no fence, then "
        f"retries the access up to {n} times; the access must succeed by the last try. The bound is the test's "
        "choice: the rule gives no number, so a hart that takes longer than the loop is not distinguishable from "
        "one that never sees the store, and a hart that needs no time at all passes on the first try. Visibility "
        "to another hart, and that the store is not seen early, are not observable here.",
        plan=f"1. Sv39/Sv32 (probed), S-mode: a leaf PTE with V=0: lw faults (13); store V=1; lw retried up to {n} "
        "times reads the page, with only load page faults in between.\n"
        "2. The same for a non-leaf PTE (the pointer to the leaf table) with V=0.\n"
        "3. Fetch: jalr to a page whose leaf has V=0 faults (12); after V=1 the page's stub runs (x7 = its id).\n"
        "4. Store: sw faults (15); after V=1 the store lands in the page (read through the identity map).\n"
        "5. U-mode: a U=1 leaf with V=0, lw faults; V=1 is stored in S-mode; the retry loop runs in U-mode.\n"
        "6. With H, HLV.W from HS-mode (SPVP=1): a VS-stage leaf with V=0 (load page fault) and a G-stage leaf "
        "with V=0 (load guest-page fault), each made valid with no HFENCE.",
    )
    from svlib import EXEC_OFF, lsig
    from svlib import V as PV

    t.page("A")
    t.page("B")
    t.page("C")
    t.page("D")
    t.page("E")

    def body(xlen: int) -> None:
        def inner(pt: SvPT) -> None:
            va = VA_T[xlen]
            pt.leaf(va, t.page("A"), LEAF & ~PV, note="V=0")
            pt.leaf(va + 0x20_0000 if xlen == 64 else va + 0x40_0000, t.page("B"), LEAF)
            nl_va = va + 0x20_0000 if xlen == 64 else va + 0x40_0000
            pt.leaf(va + 0x2000, t.page("C"), LEAF & ~PV, note="V=0")
            pt.leaf(va + 0x3000, t.page("D"), LEAF & ~PV, note="V=0")
            pt.leaf(va + 0x4000, t.page("E"), ULEAF & ~PV, note="V=0")
            nl_depth = pt.depth(0) - 1  # the pointer PTE to nl_va's leaf table
            pt.modify(nl_va, nl_depth, clear_bits=PV, note="pointer V=0")
            pt.on()
            cases = [
                ("leaf", va, "A", "load", 0),
                ("non-leaf", nl_va, "B", "load", nl_depth),
                ("fetch", va + 0x2000, "C", "fetch", 0),
                ("store", va + 0x3000, "D", "store", 0),
                ("U-mode", va + 0x4000, "E", "loadU", 0),
            ]
            for name, v, page, kind, depth in cases:
                pid = t.page_id(page)
                mode = "U" if kind == "loadU" else "S"
                t.emit(f"li x6, {hex(v)}")
                t.emit("li x7, 0")
                t.la("x15", f"ai_pg_{page}+0x80")
                t.emit("li x8, 0x6b6b")
                ln = {
                    "load": "lw x7, 0(x6)",
                    "loadU": "lw x7, 0(x6)",
                    "fetch": f"jalr x1, {EXEC_OFF}(x6)",
                    "store": "sw x8, 0x80(x6)",
                }[kind]
                c = {"load": LOAD_PF, "loadU": LOAD_PF, "fetch": INSN_PF, "store": STORE_PF}[kind]
                mwin(
                    t,
                    pt,
                    mode,
                    [ln],
                    c,
                    f"{name}: access with V=0",
                    {},
                    epc=(v + EXEC_OFF) if kind == "fetch" else "insn",
                )
                pt.modify(v, pt.depth(0) if name != "non-leaf" else depth, set_bits=PV, note="V=1, no fence")
                t.emit(f"li x6, {hex(v)}")
                t.emit("li x7, 0")
                t.emit("li x8, 0x6b6b")
                t.la("x15", f"ai_pg_{page}+0x80")
                lab = t.label("vis")
                if kind == "store":
                    t.load("x1", 0x6B6B, "the stored value")
                    retry(t, [ln, "lw x7, 0(x15)"], "x7", n, c, f"{name}: store retried after V=1", lab)
                    t.check("x7", 0x6B6B if MUT != "vptc_never" else 0, lab, f"{name}: the store lands once V=1")
                elif kind == "fetch":
                    t.load("x15", pid, "the page's id (jalr writes x1)")
                    retry(t, [ln], "x7", n, c, f"{name}: fetch retried after V=1", lab, exp="x15")
                    t.check("x7", pid if MUT != "vptc_never" else 0, lab, f"{name}: the page's stub runs once V=1")
                else:
                    t.load("x1", lsig(pid), "the page's signature")
                    ent = (lambda v=v, lab=lab: enter_u_alias(t, pt, lab)) if mode == "U" else None
                    if ent:
                        retry_u(t, pt, [ln], "x7", n, c, f"{name}: lw retried after V=1", lab)
                    else:
                        retry(t, [ln], "x7", n, c, f"{name}: lw retried after V=1", lab)
                    t.check("x7", lsig(pid) if MUT != "vptc_never" else 0, lab, f"{name}: lw reads the page once V=1")

        with_vm(t, xlen, inner, user=True)

    both(t, body)

    with t.only_if(H):
        from hlib import hlsv
        from hmem import G_OF, GPA_BASE, PT, VA_BASE, VS_OF

        def hbody(xlen: int) -> None:
            g = PT(t, f"g{xlen}", G_OF[xlen], xlen)
            g.identity(ULEAF)
            gpa = GPA_BASE[xlen]
            g.leaf(gpa, t.page("A"), ULEAF)
            g.leaf(gpa + 0x1000, t.page("B"), ULEAF & ~PV, note="G-stage V=0")
            v = PT(t, f"v{xlen}", VS_OF[xlen], xlen)
            vva = VA_BASE[xlen]
            v.leaf(vva, gpa, LEAF & ~PV, note="VS-stage V=0")
            v.leaf(vva + 0x1000, gpa + 0x1000, LEAF)
            atp_probe(t, HGATP, g, "x1")
            atp_probe(t, VSATP, v, "x9")
            t.emit("and x1, x1, x9")

            def run() -> None:
                g.atp("x6")
                t.emit(f"csrw {hex(HGATP)}, x6")
                t.emit(HFENCE_GVMA)
                v.atp("x6")
                t.emit(f"csrw {hex(VSATP)}, x6")
                t.emit(HFENCE_VVMA)
                spvp(t, True)
                ln, _ = hlsv("hlv.w", "x7", "x6")
                for name, addr_, page, c, ptab, a in (
                    ("VS-stage leaf", vva, "A", LOAD_PF, v, vva),
                    ("G-stage leaf", vva + 0x1000, "B", 21, g, gpa + 0x1000),
                ):
                    t.emit(f"li x6, {hex(addr_)}")
                    mwin(t, None, "S", [ln], c, f"HLV.W, {name} V=0", {})
                    t.comment(f"{name}: V = 1, no fence")
                    ptab.pte_addr(a, len(ptab.geo) - 1)
                    t.emit("LREG x6, 0(x8)")
                    t.emit("ori x6, x6, 1")
                    t.emit("SREG x6, 0(x8)")
                    t.emit(f"li x6, {hex(addr_)}")
                    t.emit("li x7, 0")
                    t.load("x1", lsig(t.page_id(page)), "the page's signature")
                    lab = t.label("hvis")
                    retry(t, [ln], "x7", n, c, f"HLV.W retried after {name} V=1", lab)
                    t.check(
                        "x7",
                        lsig(t.page_id(page)) if MUT != "vptc_never" else 0,
                        lab,
                        f"HLV.W reads the page once the {name} has V=1",
                    )
                spvp(t, False)
                t.emit(f"csrw {hex(HGATP)}, x0")
                t.emit(f"csrw {hex(VSATP)}, x0")
                t.emit(HFENCE_GVMA)
                t.emit(HFENCE_VVMA)

            from svlib import guard

            guard(t, "x1", run)

        both(t, hbody)
    return [t]


def retry_u(t: SvTest, pt: SvPT, body: list[str], cmp: str, n: int, cause: int, desc: str, lab: str) -> None:
    """retry() with the loop in U-mode at pt's user alias."""
    retry(t, body, cmp, n, cause, desc, lab, enter=lambda: enter_u_alias(t, pt, lab))


# ================================================================ Svrsw60t59b
B59, B60, B58 = 1 << 59, 1 << 60, 1 << 58
RSW_SETS = [("bit 59", B59), ("bit 60", B60), ("bits 60-59", B59 | B60)]
SVRSW = "src/priv/svrsw60t59b.adoc"


def rsw_ok() -> int | str:
    return LOAD_PF if MUT == "rsw_bits_fault" else "ok"


def gen_svrsw() -> list[TestFile]:
    from svlib import (
        ADUE_BIT,
        EXEC_OFF,
        guard,
        lsig,
        menvcfg_bit,
        menvcfg_get,
        register_alias,
        satp_off,
        unregister_alias,
    )
    from svlib import A as PA_
    from svlib import probe as sprobe

    tests = []
    suite = "Svrsw60t59b"
    t = new(suite, "Svrsw60t59b_reserved_bits_60_59", rv64=True)
    t.describe(
        source=SVRSW,
        rule_text="If the Svrsw60t59b extension is implemented, then bits 60-59 of the page table entries (PTEs) "
        "are reserved for use by supervisor software and are ignored by the implementation.",
        context="Without the extension, Sv39/Sv48/Sv57 PTE bits 60-54 are reserved and a nonzero value raises a "
        "page fault. With it, bits 60-59 must be ignored in leaf and non-leaf PTEs, and a hardware A/D update "
        "(Svadu, menvcfg.ADUE=1) must leave them unchanged. Bits 58-54 stay reserved (contrast). Each supported "
        "scheme is probed; Svrsw60t59b depends on Sv39, so Sv39 is expected. RV64 only (the file passes trivially "
        "on RV32). With H, VS-stage PTEs (walked for HLV.W) are covered too; G-stage PTEs are "
        "Svrsw60t59b_H_g_stage_reserved_bits.",
        plan="1. For Sv39, Sv48 and Sv57 (probed): 4 KiB leaves with bit 59, bit 60 and both: S-mode lw reads the "
        "page; with both bits, sw lands and a fetch runs the page's stub, a U=1 leaf is read from U-mode, and a "
        "2 MiB leaf is read.\n"
        "2. A pointer PTE with both bits set: lw through it reads the page.\n"
        "3. Contrast: a leaf with bit 58 set raises a load page fault.\n"
        "4. If menvcfg.ADUE can be set (Svadu): a leaf with A=0 and both bits: lw reads the page, and the PTE then "
        "has A=1 and bits 60-59 still set. Otherwise lw raises a load page fault (Svade).\n"
        "5. With H: an HLV.W through a VS-stage leaf and a VS-stage pointer with both bits set reads the page.",
    )
    for p in "ABCDE":
        t.page(p)

    def scheme_body(scheme: str) -> None:
        pt = SvPT(t, f"p{scheme}", scheme)
        pt.identity()
        pt.user_alias()

        def run() -> None:
            register_alias(t, pt)
            va = VA_T[64]
            for i, (_, bits) in enumerate(RSW_SETS):
                pt.leaf(va + 0x1000 * i, t.page("A"), LEAF | bits)
            both_b = B59 | B60
            pt.leaf(va + 0x3000, t.page("B"), ULEAF | both_b)
            pt.leaf(va + 0x4000, t.page("C"), LEAF | B58)
            nl = va + 0x40_0000
            pt.leaf(nl, t.page("D"), LEAF)
            pt.modify(nl, pt.depth(0) - 1, set_bits=both_b, note="pointer PTE with bits 60-59")
            sp = va + 0x80_0000
            pt.leaf(sp, t.page("E"), LEAF | both_b, level=1)
            pt.on()
            for i, (name, _) in enumerate(RSW_SETS):
                t.emit(f"li x6, {hex(va + 0x1000 * i)}")
                t.emit("li x7, 0")
                lab = mwin(t, pt, "S", ["lw x7, 0(x6)"], rsw_ok(), f"{scheme} leaf with {name}: lw", {})
                t.check("x7", lsig(t.page_id("A")), lab, f"{scheme} leaf with {name}: lw reads the page")
            t.emit(f"li x6, {hex(va + 0x2000)}")
            t.emit("li x8, 0x5e5e")
            lab = mwin(
                t,
                pt,
                "S",
                ["sw x8, 0x40(x6)"],
                "ok" if MUT != "rsw_bits_fault" else STORE_PF,
                f"{scheme} leaf with bits 60-59: sw",
                {},
            )
            t.la("x6", "ai_pg_A+0x40")
            t.emit("lw x7, 0(x6)")
            t.check("x7", 0x5E5E, lab, f"{scheme} leaf with bits 60-59: the store landed")
            t.emit(f"li x6, {hex(va + 0x2000)}")
            t.emit("li x7, 0")
            lab = mwin(t, pt, "S", [f"jalr x1, {EXEC_OFF}(x6)"], "ok", f"{scheme} leaf with bits 60-59: fetch", {})
            t.check("x7", t.page_id("A"), lab, f"{scheme} leaf with bits 60-59: the fetch ran the page's stub")
            t.emit(f"li x6, {hex(va + 0x3000)}")
            t.emit("li x7, 0")
            lab = mwin(t, pt, "U", ["lw x7, 0(x6)"], rsw_ok(), f"{scheme} U=1 leaf with bits 60-59: lw", {})
            t.check("x7", lsig(t.page_id("B")), lab, f"{scheme} U=1 leaf with bits 60-59: U-mode lw reads the page")
            t.emit(f"li x6, {hex(va + 0x4000)}")
            mwin(
                t,
                pt,
                "S",
                ["lw x7, 0(x6)"],
                LOAD_PF if MUT != "rsv58_ignored" else "ok",
                f"{scheme} leaf with reserved bit 58: lw",
                {LOAD_PF: [0, va + 0x4000]},
            )
            t.emit(f"li x6, {hex(nl)}")
            t.emit("li x7, 0")
            lab = mwin(t, pt, "S", ["lw x7, 0(x6)"], rsw_ok(), f"{scheme} pointer PTE with bits 60-59: lw", {})
            t.check("x7", lsig(t.page_id("D")), lab, f"{scheme} pointer PTE with bits 60-59: lw reads the page")
            t.la("x6", "ai_pg_E")
            t.emit("li x7, 0x1fffff")
            t.emit("and x6, x6, x7")
            t.emit(f"li x7, {hex(sp)}")
            t.emit("add x6, x6, x7")
            t.emit("li x7, 0")
            lab = mwin(t, pt, "S", ["lw x7, 0(x6)"], rsw_ok(), f"{scheme} 2 MiB leaf with bits 60-59: lw", {})
            t.check("x7", lsig(t.page_id("E")), lab, f"{scheme} 2 MiB leaf with bits 60-59: lw reads the page")
            satp_off(t)
            unregister_alias(t)

        sprobe(t, pt)
        guard(t, "x1", run)

    for sch in ("sv39", "sv48", "sv57"):
        scheme_body(sch)

    # ---- hardware A/D update keeps bits 60-59
    t.comment("hardware A/D update (Svadu with menvcfg.ADUE=1) or a Svade page fault")
    menvcfg_bit(t, 64, ADUE_BIT, True)
    menvcfg_get(t, 64, ADUE_BIT, "x9")

    def ad_body(pt: SvPT) -> None:
        va = VA_T[64] + 0x10000
        both_b = B59 | B60
        pt.leaf(va, t.page("A"), (LEAF & ~PA_) | both_b, note="A=0")
        pt.on()

        def hw() -> None:
            t.emit(f"li x6, {hex(va)}")
            t.emit("li x7, 0")
            lab = mwin(t, pt, "S", ["lw x7, 0(x6)"], "ok", "ADUE=1: lw of an A=0 leaf with bits 60-59", {})
            t.check("x7", lsig(t.page_id("A")), lab, "ADUE=1: lw reads the page")
            pt.read_pte(va, pt.depth(0), "x7")
            t.load("x6", both_b | PA_, "bits 60-59 and A")
            t.emit("and x7, x7, x6")
            exp = PA_ if MUT == "ad_clears_rsw" else both_b | PA_
            t.check("x7", exp, lab, "ADUE=1: the updated PTE has A=1 and bits 60-59 unchanged")

        def svade() -> None:
            t.emit(f"li x6, {hex(va)}")
            mwin(t, pt, "S", ["lw x7, 0(x6)"], LOAD_PF, "ADUE=0 (Svade): lw of an A=0 leaf", {})

        t.either("x9", hw, svade)

    with_vm(t, 64, ad_body, name="pad")
    menvcfg_bit(t, 64, ADUE_BIT, False)

    with t.only_if(H):
        from hlib import hlsv
        from hmem import GPA_BASE, PT, VA_BASE

        v = PT(t, "vrsw", "sv39", 64)
        vva = VA_BASE[64]
        both_b = B59 | B60
        v.leaf(vva, t.page("A"), LEAF | both_b)
        v.leaf(vva + 0x40_0000, t.page("D"), LEAF)
        tab_d = v.pointer(vva + 0x40_0000, 1)
        del tab_d
        v.pte_addr(vva + 0x40_0000, 1)
        t.emit("LREG x6, 0(x8)")
        t.emit("li x7, 0x1800000000000000")
        t.emit("or x6, x6, x7")
        t.emit("SREG x6, 0(x8)  // VS-stage pointer PTE with bits 60-59")
        atp_probe(t, VSATP, v, "x1")
        del GPA_BASE

        def vrun() -> None:
            v.atp("x6")
            t.emit(f"csrw {hex(VSATP)}, x6")
            t.emit(HFENCE_VVMA)
            spvp(t, True)
            ln, _ = hlsv("hlv.w", "x7", "x6")
            for addr_, page, name in ((vva, "A", "VS-stage leaf"), (vva + 0x40_0000, "D", "VS-stage pointer")):
                t.emit(f"li x6, {hex(addr_)}")
                t.emit("li x7, 0")
                lab = mwin(t, None, "S", [ln], rsw_ok(), f"HLV.W, {name} with bits 60-59", {})
                t.check("x7", lsig(t.page_id(page)), lab, f"HLV.W through a {name} with bits 60-59 reads the page")
            spvp(t, False)
            t.emit(f"csrw {hex(VSATP)}, x0")
            t.emit(HFENCE_VVMA)

        guard(t, "x1", vrun)
    tests.append(t)

    # ---- G-stage
    t = new(suite, "Svrsw60t59b_H_g_stage_reserved_bits", ["I", "S", "H", suite], rv64=True)
    t.describe(
        source=SVRSW,
        rule_text="If the Hypervisor (H) extension is also implemented, then bits 60-59 of the G-stage PTEs are "
        "reserved for use by supervisor software and are ignored by the implementation.",
        context="G-stage Sv39x4, Sv48x4 and Sv57x4 are probed through hgatp. Accesses are HLV.W from HS-mode with "
        "vsatp Bare, so the guest physical address is the address in the register. Every G-stage leaf has U=1. "
        "Bit 58 stays reserved: a G-stage leaf with it set raises a load guest-page fault (21) (contrast). RV64 "
        "only.",
        plan="1. For each supported G-stage mode: 4 KiB G-stage leaves with bit 59, bit 60 and both: HLV.W reads "
        "the page.\n"
        "2. A G-stage pointer PTE with both bits: HLV.W through it reads the page.\n"
        "3. A 2 MiB G-stage leaf with both bits: HLV.W reads the page.\n"
        "4. Contrast: a G-stage leaf with bit 58: load guest-page fault, htval 0 or the GPA >> 2.",
    )
    for p in "ABC":
        t.page(p)
    from hlib import hlsv
    from hmem import GPA_BASE, PT

    for gs in ("sv39x4", "sv48x4", "sv57x4"):
        g = PT(t, f"g{gs}", gs, 64)
        g.identity(ULEAF)
        gpa = GPA_BASE[64]
        for i, (_, bits) in enumerate(RSW_SETS):
            g.leaf(gpa + 0x1000 * i, t.page("A"), ULEAF | bits)
        g.leaf(gpa + 0x4000, t.page("A"), ULEAF | B58)
        nl = gpa + 0x40_0000
        g.leaf(nl, t.page("B"), ULEAF)
        g.pte_addr(nl, len(g.geo) - 2)
        t.emit("LREG x6, 0(x8)")
        t.emit("li x7, 0x1800000000000000")
        t.emit("or x6, x6, x7")
        t.emit("SREG x6, 0(x8)  // G-stage pointer PTE with bits 60-59")
        sp = gpa + 0x80_0000
        g.leaf(sp, t.page("C"), ULEAF | B59 | B60, level=1)
        atp_probe(t, HGATP, g, "x1")

        def grun(g: PT = g, gs: str = gs, gpa: int = gpa, nl: int = nl, sp: int = sp) -> None:
            g.atp("x6")
            t.emit(f"csrw {hex(HGATP)}, x6")
            t.emit(HFENCE_GVMA)
            spvp(t, True)
            ln, _ = hlsv("hlv.w", "x7", "x6")
            gok = 21 if MUT == "rsw_bits_fault" else "ok"
            for i, (name, _) in enumerate(RSW_SETS):
                t.emit(f"li x6, {hex(gpa + 0x1000 * i)}")
                t.emit("li x7, 0")
                lab = mwin(t, None, "S", [ln], gok, f"{gs} leaf with {name}: HLV.W", {})
                t.check("x7", lsig(t.page_id("A")), lab, f"{gs} leaf with {name}: HLV.W reads the page")
            t.emit(f"li x6, {hex(nl)}")
            t.emit("li x7, 0")
            lab = mwin(t, None, "S", [ln], gok, f"{gs} pointer with bits 60-59: HLV.W", {})
            t.check("x7", lsig(t.page_id("B")), lab, f"{gs} pointer with bits 60-59: HLV.W reads the page")
            t.la("x6", "ai_pg_C")
            t.emit("li x7, 0x1fffff")
            t.emit("and x6, x6, x7")
            t.emit(f"li x7, {hex(sp)}")
            t.emit("add x6, x6, x7")
            t.emit("li x7, 0")
            lab = mwin(t, None, "S", [ln], gok, f"{gs} 2 MiB leaf with bits 60-59: HLV.W", {})
            t.check("x7", lsig(t.page_id("C")), lab, f"{gs} 2 MiB leaf with bits 60-59: HLV.W reads the page")
            t.emit(f"li x6, {hex(gpa + 0x4000)}")
            mwin(
                t,
                None,
                "S",
                [ln],
                21 if MUT != "rsv58_ignored" else "ok",
                f"{gs} leaf with bit 58: HLV.W",
                {21: [0, gpa + 0x4000]},
                tval2s={21: [0, (gpa + 0x4000) >> 2]},
            )
            spvp(t, False)
            t.emit(f"csrw {hex(HGATP)}, x0")
            t.emit(HFENCE_GVMA)

        guard(t, "x1", grun)
    tests.append(t)

    # ---- depends on Sv39
    t = new(suite, "Svrsw60t59b_depends_on_Sv39", rv64=True)
    t.describe(
        source=SVRSW,
        rule_text="The Svrsw60t59b extension depends on Sv39.",
        context="A hart with Svrsw60t59b must therefore support Sv39: satp must accept MODE=8 and translate. RV64 "
        "only.",
        plan="1. Write satp with MODE=Sv39 and a root that identity-maps the image: it reads MODE 8.\n"
        "2. A 4 KiB Sv39 leaf translates: lw reads the page.",
    )
    t.page("A")
    pt = SvPT(t, "p39", "sv39")
    pt.identity()
    sprobe(t, pt)
    lab = t.label("sv39")
    t.emit(f"{lab}:", 0)
    t.emit("mv x9, x1")
    t.check("x9", 0 if MUT == "no_sv39" else 1, lab, "satp accepts MODE = Sv39")

    def r39() -> None:
        pt.leaf(VA_T[64], t.page("A"), LEAF)
        pt.on()
        t.emit(f"li x6, {hex(VA_T[64])}")
        t.emit("li x7, 0")
        lab = mwin(t, pt, "S", ["lw x7, 0(x6)"], "ok", "Sv39 4 KiB leaf: lw", {})
        t.check("x7", lsig(t.page_id("A")), lab, "Sv39 translates: lw reads the page")
        satp_off(t)

    guard(t, "x1", r39)
    tests.append(t)
    return tests


# ================================================================ Shgatpa / Shvsatpa
GBITS = {"sv32x4": 34, "sv39x4": 41, "sv48x4": 50, "sv57x4": 59}
S_OF_G = {"sv32x4": "sv32", "sv39x4": "sv39", "sv48x4": "sv48", "sv57x4": "sv57"}
SCHEMES = {64: ["sv39", "sv48", "sv57"], 32: ["sv32"]}


def satp_probe(t: SvTest, scheme: str, reg: str) -> None:
    """reg = 1 if satp accepts `scheme` (written with a root that identity-maps the image)."""
    from svlib import probe as sprobe

    pt = SvPT(t, f"id{scheme}", scheme)
    pt.identity()
    sprobe(t, pt, reg)


def gen_atp_modes() -> list[TestFile]:
    from hlib import hlsv
    from hmem import PT
    from svlib import canon, guard, lsig

    tests = []
    ln, _ = hlsv("hlv.w", "x7", "x6")

    # ---- Shgatpa: SvNNx4 for every supported SvNN
    t = new("Shgatpa", "Shgatpa_satp_hgatp_mode_support", ["I", "S", "H", "Shgatpa"])
    t.describe(
        source="src/priv/shgatpa.adoc",
        rule_text="If the Shgatpa extension is implemented, then for each supported virtual memory scheme Sv__NN__ "
        "supported in `satp`, the corresponding hgatp Sv__NN__x4 mode must be supported.",
        context="satp modes are probed in HS-mode with a root that identity-maps the image (satp is active at "
        "once). hgatp modes are probed by writing MODE with a 16 KiB-aligned root and reading MODE back (hgatp "
        'is WARL; an unsupported MODE leaves another legal value). "Supported" is checked functionally too: an '
        "HLV.W (vsatp Bare, SPVP=1) of a guest physical address that sets both of the mode's two extra GPA bits "
        "is translated by the SvNNx4 table and reads the mapped page. On RV32 such a GPA (34 bits) is reached "
        "through a VS-stage Sv32 leaf when vsatp accepts Sv32; a GPA below 4 GiB is used through Bare.",
        plan="1. For each SvNN (Sv32 on RV32; Sv39, Sv48, Sv57 on RV64): if satp accepts it, hgatp must accept "
        "SvNNx4 (MODE reads back).\n"
        "2. If hgatp accepts it: HLV.W of GPA 0x...5000 with GPA bits NN+1 and NN set (RV64; RV32 through "
        "VS-stage), and of GPA_BASE, read the pages mapped there.",
    )
    t.page("A")
    t.page("B")

    def g_body(xlen: int) -> None:
        for s in SCHEMES[xlen]:
            gs = s + "x4"
            g = PT(t, f"g{gs}", gs, xlen)
            g.identity(ULEAF)
            from hmem import GPA_BASE

            hi = (3 << (GBITS[gs] - 2)) | 0x5000
            g.leaf(GPA_BASE[xlen], t.page("A"), ULEAF)
            g.leaf(hi, t.page("B"), ULEAF)
            satp_probe(t, s, "x9")  # after the G-stage table is built: its builder clobbers x9
            atp_probe(t, HGATP, g, "x1")
            lab = t.label(f"p{gs}")
            t.emit(f"{lab}:", 0)
            t.emit("seqz x6, x9  // satp does not accept SvNN ...")
            t.emit("or x6, x6, x1  // ... or hgatp accepts SvNNx4")
            if "x4_missing_" + s == MUT:
                t.emit("seqz x6, x1")
            t.check_bool("x6", lab, f"satp {s} implies hgatp {gs}")

            def run(g: PT = g, gs: str = gs, hi: int = hi, s: str = s) -> None:
                g.atp("x6")
                t.emit(f"csrw {hex(HGATP)}, x6")
                t.emit(HFENCE_GVMA)
                spvp(t, True)
                t.emit(f"li x6, {hex(GPA_BASE[xlen])}")
                t.emit("li x7, 0")
                lab = mwin(t, None, "S", [ln], "ok", f"{gs}: HLV.W of GPA_BASE", {})
                t.check("x7", lsig(t.page_id("A")), lab, f"{gs}: HLV.W of GPA_BASE reads the page")
                if xlen == 64:
                    t.emit(f"li x6, {hex(hi)}")
                    t.emit("li x7, 0")
                    lab = mwin(t, None, "S", [ln], "ok", f"{gs}: HLV.W of GPA {hex(hi)}", {})
                    exp = t.page_id("A") if MUT == "x4_drops_top" else t.page_id("B")
                    t.check("x7", lsig(exp), lab, f"{gs}: HLV.W of GPA {hex(hi)} (both extra GPA bits) reads the page")
                else:
                    v = PT(t, "v32hi", "sv32", 32)
                    v.leaf(0x2000_0000, hi, LEAF)
                    atp_probe(t, VSATP, v, "x9")

                    def vrun(v: PT = v) -> None:
                        v.atp("x6")
                        t.emit(f"csrw {hex(VSATP)}, x6")
                        t.emit(HFENCE_VVMA)
                        t.emit("li x6, 0x20000000")
                        t.emit("li x7, 0")
                        lab = mwin(t, None, "S", [ln], "ok", f"{gs}: HLV.W of GPA {hex(hi)} through VS-stage", {})
                        exp = t.page_id("A") if MUT == "x4_drops_top" else t.page_id("B")
                        t.check("x7", lsig(exp), lab, f"{gs}: HLV.W of GPA {hex(hi)} reads the page")
                        t.emit(f"csrw {hex(VSATP)}, x0")
                        t.emit(HFENCE_VVMA)

                    guard(t, "x9", vrun)
                spvp(t, False)
                t.emit(f"csrw {hex(HGATP)}, x0")
                t.emit(HFENCE_GVMA)

            guard(t, "x1", run)

    both(t, g_body)
    tests.append(t)

    # ---- Shgatpa: Bare
    t = new("Shgatpa", "Shgatpa_hgatp_bare_mode", ["I", "S", "H", "Shgatpa"])
    t.describe(
        source="src/priv/shgatpa.adoc",
        rule_text="Furthermore, the `hgatp` mode Bare must also be supported.",
        context="With MODE=Bare, guest physical addresses are supervisor physical addresses (no G-stage "
        "translation). The test writes hgatp = 0 (Bare with VMID and PPN zero, as software must) after a "
        "translating mode (Sv39x4 / Sv32x4, if accepted) and checks that translation stops.",
        plan="1. hgatp = 0 reads 0, and HLV.W (vsatp Bare) of a page's physical address reads that page.\n"
        "2. If hgatp accepts the x4 mode: map GPA = the physical address of page A onto page B, write the x4 "
        "hgatp: HLV.W of that address reads page B. Write hgatp = 0 and HFENCE.GVMA: it reads 0 and HLV.W reads "
        "page A again.\n"
        "3. VS-mode code runs with hgatp Bare: lw of page A's physical address in VS-mode reads page A.",
    )
    t.page("A")
    t.page("B")

    def bare_check(tag: str) -> None:
        lab = t.label("bare")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrw {hex(HGATP)}, x0")
        t.emit(HFENCE_GVMA)
        t.emit(f"csrr x7, {hex(HGATP)}")
        t.check("x7", 8 << 60 if MUT == "no_bare" else 0, lab, f"hgatp = 0 (Bare) reads 0 ({tag})")
        t.la("x6", "ai_pg_A")
        t.emit("li x7, 0")
        lab = mwin(t, None, "S", [ln], "ok", f"Bare ({tag}): HLV.W of page A's address", {})
        t.check("x7", lsig(t.page_id("A")), lab, f"Bare ({tag}): HLV.W reads page A (GPA = PA)")

    spvp(t, True)
    bare_check("first")

    def bare_body(xlen: int) -> None:
        from hmem import G_OF

        g = PT(t, f"gb{xlen}", G_OF[xlen], xlen)
        g.identity(ULEAF)
        g.leaf_runtime("ai_pg_A", "ai_pg_B", ULEAF)
        atp_probe(t, HGATP, g, "x1")

        def run(g: PT = g) -> None:
            g.atp("x6")
            t.emit(f"csrw {hex(HGATP)}, x6")
            t.emit(HFENCE_GVMA)
            t.la("x6", "ai_pg_A")
            t.emit("li x7, 0")
            lab = mwin(t, None, "S", [ln], "ok", "x4 mode: HLV.W of page A's address", {})
            t.check("x7", lsig(t.page_id("B")), lab, "x4 mode: HLV.W of page A's address reads page B (translated)")
            bare_check("after an x4 mode")

        guard(t, "x1", run)

    both(t, bare_body)
    spvp(t, False)
    t.la("x6", "ai_pg_A")
    t.emit("li x7, 0")
    lab = mwin(t, None, "VS", ["lw x7, 0(x6)"], "ok", "Bare: VS-mode lw of page A", {})
    t.check("x7", lsig(t.page_id("A")), lab, "Bare: VS-mode lw reads page A")
    tests.append(t)

    # ---- Shvsatpa
    t = new("Shvsatpa", "Shvsatpa_satp_vsatp_modes", ["I", "S", "H", "Shvsatpa"])
    t.describe(
        source="src/priv/shvsatpa.adoc",
        rule_text="If the Shvsatpa extension is implemented, all translation modes supported in `satp` must be "
        "supported in `vsatp`.",
        context="satp modes are probed in HS-mode (identity-mapping root). vsatp is written from HS-mode (V=0), "
        "where a write with an unsupported MODE has no effect (vsatp_mode_unsupported_v0), so MODE reads back "
        'only if supported. "Supported" is also checked functionally: with hgatp Bare, HLV.W (SPVP=1) '
        "translates through a VS-stage table of that mode at a virtual address in the upper (negative) half, which "
        "uses the top VPN bits of the mode.",
        plan="1. For each mode (Sv32 on RV32; Sv39, Sv48, Sv57 on RV64): if satp accepts it, vsatp must accept it "
        "(MODE reads back).\n"
        "2. If vsatp accepts it: HLV.W of the mapped upper-half VA reads the page, and HLV.W of the same VA "
        "with the leaf made invalid (and HFENCE.VVMA) raises a load page fault: the table is really used.",
    )
    t.page("A")
    from svlib import VABITS
    from svlib import V as PV

    def vs_body(xlen: int) -> None:
        for s in SCHEMES[xlen]:
            v = SvPT(t, f"v{s}", s)
            va = canon(1 << (VABITS[s] - 1), VABITS[s]) + 0x3000 if xlen == 64 else 0xC000_3000
            v.leaf(va, t.page("A"), LEAF)
            satp_probe(t, s, "x9")  # after the table is built, so no builder clobbers x9
            atp_probe(t, VSATP, v, "x1")
            lab = t.label(f"v{s}")
            t.emit(f"{lab}:", 0)
            t.emit("seqz x6, x9")
            t.emit("or x6, x6, x1")
            if "vsatp_missing_" + s == MUT:
                t.emit("seqz x6, x1")
            t.check_bool("x6", lab, f"satp {s} implies vsatp {s}")

            def run(v: SvPT = v, va: int = va, s: str = s) -> None:
                v.atp("x6")
                t.emit(f"csrw {hex(VSATP)}, x6")
                t.emit(HFENCE_VVMA)
                spvp(t, True)
                t.emit(f"li x6, {hex(va)}")
                t.emit("li x7, 0")
                lab = mwin(t, None, "S", [ln], "ok", f"vsatp {s}: HLV.W of {hex(va)}", {})
                t.check("x7", lsig(t.page_id("A")), lab, f"vsatp {s}: HLV.W reads the mapped page")
                v.modify(va, v.depth(0), clear_bits=PV, note="invalid")
                t.emit(HFENCE_VVMA)
                t.emit(f"li x6, {hex(va)}")
                mwin(
                    t,
                    None,
                    "S",
                    [ln],
                    LOAD_PF if MUT != "vsatp_ignored" else "ok",
                    f"vsatp {s}: HLV.W of an invalid leaf",
                    {},
                )
                spvp(t, False)
                t.emit(f"csrw {hex(VSATP)}, x0")
                t.emit(HFENCE_VVMA)

            guard(t, "x1", run)

    both(t, vs_body)
    tests.append(t)
    return tests


# ================================================================ Shtvala
def gen_shtvala() -> list[TestFile]:
    from hlib import hlsv
    from hmem import G_OF, GPA_BASE, PT, VS_OF
    from svlib import guard

    t = new("Shtvala", "Shtvala_htval_faulting_gpa", ["I", "S", "H", "Shtvala"])
    t.describe(
        source="src/priv/shtvala.adoc",
        rule_text="If the Shtvala extension is implemented, `htval` must be written with the faulting guest "
        "physical address in all circumstances permitted by the ISA.",
        context='Without Shtvala, htval may be 0 on a guest-page fault (hypervisor.adoc htval_trapval: "either '
        'zero or the guest physical address that faulted, shifted right by 2 bits"). Here only GPA >> 2 is '
        "accepted, with the GPA's offset bits above bit 1 included. For a fault on an implicit VS-stage access, "
        "the faulting GPA is the PTE's. For a misaligned access whose second page faults, it is the GPA of the "
        "faulting portion (the page boundary). stval may still be 0 or the guest virtual address (Sstvala is "
        "another extension). For explicit accesses, a nonzero htval must correspond to the address in stval "
        "(mtval2_htval_virtaddr), so when stval is 0 the pair stval = htval = 0 is also accepted; with a nonzero "
        "stval, htval must be the GPA. For implicit accesses htval must be the PTE's GPA. G-stage Sv39x4 (RV64) / Sv32x4 (RV32) is "
        "probed. Guest-page faults go to HS-mode (hedeleg[20,21,23] are read-only 0).",
        plan="1. vsatp Bare: HLV.W, HLVX.WU and HSV.W of GPA_BASE + 0x5004 (unmapped in G-stage): 21/21/23 with "
        "htval = GPA >> 2.\n"
        "2. VS-mode lw, sw (GPA + 0x5008) and VU-mode lw (+ 0x500c): the same; VS-mode fetch of GPA + 0x5100: "
        "20 with htval = GPA >> 2.\n"
        "3. Misaligned HLV.W and VS-mode lw at GPA_BASE + 0x0ffe (page 0 mapped, page 1 not): no trap is "
        "impossible; misaligned, access fault, or guest-page fault with htval = (GPA_BASE + 0x1000) >> 2.\n"
        "4. Implicit accesses: VS-stage tables at GPAs; with the root's GPA unmapped, and then with the leaf "
        "table's GPA unmapped, HLV.W raises a load guest-page fault with htval = (GPA of the PTE read) >> 2.\n"
        "5. A VS-stage leaf maps a guest virtual page to an unmapped GPA: HLV.W raises a load guest-page fault "
        "with htval = that GPA >> 2 (not the guest virtual address).",
    )
    t.page("A")
    t.page("B")
    hlvw, _ = hlsv("hlv.w", "x7", "x6")
    hlvx, _ = hlsv("hlvx.wu", "x7", "x6")
    hsvw, _ = hlsv("hsv.w", "x7", "x6", "x8")

    def ht(gpa: int) -> int:
        if MUT == "htval_zero":
            return 0
        if MUT == "htval_unshifted":
            return gpa
        if MUT == "htval_page":
            return (gpa & ~0xFFF) >> 2
        return gpa >> 2

    def htval_exp(gpa: int) -> object:
        """htval after an explicit access: GPA >> 2, or 0 with stval = 0 (mtval2_htval_virtaddr)."""
        return ("gpa_or_zero", ht(gpa))

    def body(xlen: int) -> None:
        gb = GPA_BASE[xlen]
        g = PT(t, f"g{xlen}", G_OF[xlen], xlen)
        g.identity(ULEAF)
        g.leaf(gb, t.page("A"), ULEAF)
        atp_probe(t, HGATP, g, "x1")

        def run() -> None:
            g.atp("x6")
            t.emit(f"csrw {hex(HGATP)}, x6")
            t.emit(HFENCE_GVMA)
            spvp(t, True)
            for line, c, off, name in (
                (hlvw, LOAD_GPF, 0x5004, "HLV.W"),
                (hlvx, LOAD_GPF, 0x5004, "HLVX.WU"),
                (hsvw, STORE_GPF, 0x5004, "HSV.W"),
            ):
                t.emit(f"li x6, {hex(gb + off)}")
                mwin(
                    t,
                    None,
                    "S",
                    [line],
                    c,
                    f"{name} of an unmapped GPA",
                    {c: [0, gb + off]},
                    tval2s={c: htval_exp(gb + off)},
                )
            for mode, line, c, off in (
                ("VS", "lw x7, 0(x6)", LOAD_GPF, 0x5004),
                ("VS", "sw x7, 4(x6)", STORE_GPF, 0x5004),
                ("VU", "lw x7, 8(x6)", LOAD_GPF, 0x5004),
            ):
                a = gb + off + (4 if "4(" in line else 8 if "8(" in line else 0)
                t.emit(f"li x6, {hex(gb + off)}")
                mwin(
                    t,
                    None,
                    mode,
                    [line],
                    c,
                    f"{line.split()[0]} of an unmapped GPA",
                    {c: [0, a]},
                    tval2s={c: htval_exp(a)},
                )
            t.emit(f"li x6, {hex(gb + 0x5000)}")
            mwin(
                t,
                None,
                "VS",
                ["jalr x1, 0x100(x6)"],
                INSN_GPF,
                "fetch of an unmapped GPA",
                {INSN_GPF: [0, gb + 0x5100]},
                epc=gb + 0x5100,
                tval2s={INSN_GPF: htval_exp(gb + 0x5100)},
            )
            strad = gb + 0x1000 if MUT != "htval_straddle_start" else gb + 0xFFE
            for mode, line in (("S", hlvw), ("VS", "lw x7, 0(x6)")):
                t.emit(f"li x6, {hex(gb + 0xFFE)}")
                mwin(
                    t,
                    None,
                    mode,
                    [line],
                    [LOAD_MIS, LOAD_AF, LOAD_GPF],
                    f"{'HLV.W' if mode == 'S' else 'lw'} across a mapped GPA page into an unmapped one",
                    {LOAD_GPF: [0, gb + 0x1000]},
                    tval2s={LOAD_GPF: htval_exp(strad)},
                )
            # implicit VS-stage accesses: the VS tables live at GPAs gt (root) and gt + 0x1000... (children)
            gt = gb + 0x10_0000
            v = PT(t, f"v{xlen}", VS_OF[xlen], xlen, gpa_base=gt)
            vva = 0x2000_0000 if xlen == 32 else 0x4000_0000
            v.leaf(vva, gb, LEAF)
            v.leaf(vva + 0x1000, gb + 0x7000, LEAF, note="GPA unmapped in G-stage")
            # G-stage maps each VS table's GPA onto the table itself (root first, then the children)
            tabs = list(v.gpas.items())
            for tab, tg in tabs:
                g.leaf(tg, tab, ULEAF)
            v.atp("x6")
            t.emit(f"csrw {hex(VSATP)}, x6")
            t.emit(HFENCE_GVMA)
            t.emit(HFENCE_VVMA)
            t.emit(f"li x6, {hex(vva)}")
            t.emit("li x7, 0")
            from svlib import lsig

            lab = mwin(t, None, "S", [hlvw], "ok", "HLV.W through VS-stage tables at GPAs", {})
            t.check("x7", lsig(t.page_id("A")), lab, "HLV.W through the VS-stage tables reads page A")
            t.emit(f"li x6, {hex(vva + 0x1004)}")
            gexp = htval_exp(gb + 0x7004) if MUT != "htval_gva" else ("gpa_or_zero", (vva + 0x1004) >> 2)
            mwin(
                t,
                None,
                "S",
                [hlvw],
                LOAD_GPF,
                "HLV.W of a VS-stage page whose GPA is unmapped",
                {LOAD_GPF: [0, vva + 0x1004]},
                tval2s={LOAD_GPF: gexp},
            )
            geo = v.geo
            for depth in range(len(geo)):
                tg = tabs[depth][1]
                pte_gpa = tg + v._idx(vva, depth) * (xlen // 8)
                g.raw(tg, 0, note=f"unmap the VS table at depth {depth}")
                t.emit(HFENCE_GVMA)
                t.emit(HFENCE_VVMA)
                t.emit(f"li x6, {hex(vva)}")
                exp = ht(gb) if MUT == "htval_implicit_final" else ht(pte_gpa)
                mwin(
                    t,
                    None,
                    "S",
                    [hlvw],
                    LOAD_GPF,
                    f"HLV.W with the VS table at depth {depth} unmapped",
                    {LOAD_GPF: [0, vva]},
                    tval2s={LOAD_GPF: exp},
                )
                g.leaf(tg, tabs[depth][0], ULEAF)
            spvp(t, False)
            t.emit(f"csrw {hex(VSATP)}, x0")
            t.emit(f"csrw {hex(HGATP)}, x0")
            t.emit(HFENCE_GVMA)
            t.emit(HFENCE_VVMA)

        guard(t, "x1", run)

    both(t, body)
    return [t]


# ================================================================ Shvstvala
VS_DELEG = sum(1 << c for c in (0, 1, 2, 4, 5, 6, 7, 12, 13, 15))


def vt(v: int | str, kind: str = "addr") -> int | str:
    """vstval expectation, per the mutants."""
    if MUT == "vstval_zero_addr" and kind == "addr":
        return 0
    if MUT == "vstval_zero_ill" and kind == "ill":
        return 0
    return v


def gen_shvstvala() -> list[TestFile]:
    from hmem import PT, VA_BASE, VS_OF
    from svlib import guard

    t = new("Shvstvala", "Shvstvala_vstval_written", ["I", "S", "H", "Shvstvala"])
    t.describe(
        source="src/priv/shvstvala.adoc",
        rule_text="If the Shvstvala extension is implemented, `vstval` must be written in all cases described in "
        "<<sstvala>> for `stval`.",
        context="Sstvala's cases, for traps taken in VS-mode: the faulting (guest) virtual address for load, "
        "store and instruction page faults, access faults and misaligned exceptions, and the instruction bits "
        "for illegal-instruction exceptions (virtual-instruction exceptions are never taken in VS-mode). hedeleg "
        "delegates causes 0, 1, 2, 4-7, 12, 13 and 15 to VS-mode for the test; ecalls stay with HS-mode (T-SBI). "
        "hgatp is Bare throughout, so guest physical = supervisor physical addresses. The paging cases run VS-mode "
        "code with vsatp Sv39 (RV64) or Sv32 (RV32), probed, and a VS-stage identity map of the image; misaligned "
        "accesses accept no trap or 4-7, and a misaligned access into a faulting page reports the page "
        "boundary for the page fault. Each trap is checked to be taken by the VS handler.",
        plan="1. Bare: VS lw +1, sw +3 and VU lw +2 of a page: no trap, or 4-7 with vstval = the address.\n"
        "2. Bare, with RVMODEL_ACCESS_FAULT_ADDRESS: VS lw there raises 5 with vstval = the address.\n"
        "3. Illegal instruction: VS mret and csrrs mstatus, VU csrrs mstatus and mret: vstval = the encoding; "
        "with C and D, VS C.FLDSP with vsstatus.FS=Off: vstval = 0x2402.\n"
        "4. vsatp active, VS-mode: lb/sw/fetch of an invalid page (13/15/12, exact vstval); lw/sw across a valid "
        "page into an invalid one (page boundary for 13/15); with RVMODEL_ACCESS_FAULT_ADDRESS, lw through a "
        "page mapped onto it (5, vstval = the virtual address); with C, a 32-bit instruction whose second half "
        "is in an invalid page (12, vstval = the page boundary, vsepc = the instruction).",
    )
    t.page("M")
    t.emit(f"li x7, {hex(VS_DELEG)}")
    t.emit("csrs 0x602, x7  // hedeleg: delegate faults and illegal instruction to VS-mode")
    mbase = "ai_pg_M"
    for mode, line, off, c in (
        ("VS", "lw x7, 1(x6)", 1, LOAD_MIS),
        ("VS", "sw x7, 3(x6)", 3, STORE_MIS),
        ("VU", "lw x7, 2(x6)", 2, LOAD_MIS),
    ):
        t.la("x6", mbase)
        mwin(
            t,
            None,
            mode,
            [line],
            ["ok", c, c + 1],
            f"{line.split()[0]} at page+{off}",
            {c: vt(f"{mbase}+{off}"), c + 1: ("range", f"{mbase}+{off}", 4) if MUT != "vstval_zero_addr" else 0},
            handler="VS",
        )
    fa = FA_KIND["load"]
    with t.only_if(HAS_FA_KIND["load"]):
        t.emit(f"LI(x6, {fa})", 2)
        mwin(
            t, None, "VS", ["lw x7, 0(x6)"], LOAD_AF, "lw at the access-fault address", {LOAD_AF: vt(fa)}, handler="VS"
        )
    for mode, e, note in (
        ("VS", 0x30200073, "mret"),
        ("VS", enc_csr(0x300, 2, 7, 0), "csrrs x7, mstatus, x0"),
        ("VU", enc_csr(0x300, 2, 7, 0), "csrrs x7, mstatus, x0"),
        ("VU", 0x30200073, "mret"),
    ):
        mwin(t, None, mode, [word(e, note)], ILLEGAL, note, {ILLEGAL: vt(e, "ill")}, handler="VS")
    with t.only_if("defined(ZCA_SUPPORTED) && defined(ZCD_SUPPORTED)"):
        t.li("x7", 0x6000)
        t.emit("csrc 0x200, x7  // vsstatus.FS = Off")
        mwin(
            t,
            None,
            "VS",
            [half(0x2402, "c.fldsp f8, 0(sp)"), half(0x0001, "c.nop")],
            ILLEGAL,
            "c.fldsp with vsstatus.FS=Off",
            {ILLEGAL: vt(0x2402, "ill")},
            handler="VS",
        )
        t.li("x7", 0x6000)
        t.emit("csrs 0x200, x7  // vsstatus.FS = Dirty")

    def vs_fa_leaf(v: PT, va: int) -> None:
        depth = len(v.geo) - 1
        tab = v.pointer(va, depth)
        t.comment(f"{v.name}: {hex(va)} -> the page of {FA_KIND['load']}")
        t.emit(f"LI(x6, {FA_KIND['load']})", 2)
        t.emit("srli x6, x6, 12")
        t.emit("slli x6, x6, 10")
        t.emit(f"li x7, {hex(LEAF)}")
        t.emit("or x6, x6, x7")
        v._store(tab, v._idx(va, depth))

    def body(xlen: int, part: str) -> None:
        v = PT(t, f"v{xlen}{part}", VS_OF[xlen], xlen)
        v.identity(LEAF)
        va = VA_BASE[xlen]
        v.raw(va, 0, note="invalid")
        v.leaf(va + 0x1000, t.page("P"), LEAF)
        v.raw(va + 0x2000, 0, note="invalid")
        if part == "fa":
            vs_fa_leaf(v, va + 0x3000)
        if part == "c":
            v.leaf(va + 0x4000, t.page("F", {0xFFE: (2, 0x0393)}), LEAF)
            v.raw(va + 0x5000, 0, note="invalid")
        atp_probe(t, VSATP, v, "x1")

        def run() -> None:
            v.atp("x6")
            t.emit(f"csrw {hex(VSATP)}, x6")
            t.emit(HFENCE_VVMA)
            if part == "base":
                t.emit(f"li x6, {hex(va + 0x123)}")
                mwin(
                    t,
                    None,
                    "VS",
                    ["lb x7, 0(x6)"],
                    LOAD_PF,
                    "lb, invalid page",
                    {LOAD_PF: vt(va + 0x123)},
                    handler="VS",
                )
                t.emit(f"li x6, {hex(va)}")
                mwin(
                    t,
                    None,
                    "VS",
                    ["sw x7, 16(x6)"],
                    STORE_PF,
                    "sw, invalid page",
                    {STORE_PF: vt(va + 0x10)},
                    handler="VS",
                )
                t.emit(f"li x6, {hex(va)}")
                mwin(
                    t,
                    None,
                    "VS",
                    ["jalr x1, 0x100(x6)"],
                    INSN_PF,
                    "fetch, invalid page",
                    {INSN_PF: vt(va + 0x100)},
                    epc=va + 0x100,
                    handler="VS",
                )
                strad = va + 0x2000 if MUT != "vstval_straddle_start" else va + 0x1FFE
                for line, cs in (
                    ("lw x7, 0(x6)", (LOAD_MIS, LOAD_AF, LOAD_PF)),
                    ("sw x7, 0(x6)", (STORE_MIS, STORE_AF, STORE_PF)),
                ):
                    t.emit(f"li x6, {hex(va + 0x1FFE)}")
                    mwin(
                        t,
                        None,
                        "VS",
                        [line],
                        list(cs),
                        f"{line.split()[0]} across a valid page into an invalid one",
                        {cs[0]: vt(va + 0x1FFE), cs[1]: ("range", va + 0x1FFE, 4), cs[2]: vt(strad)},
                        handler="VS",
                    )
            elif part == "fa":
                fva = f"{hex(va + 0x3000)}+({FA_KIND['load']}&0xFFF)"
                t.emit(f"LI(x6, {fva})", 2)
                mwin(
                    t,
                    None,
                    "VS",
                    ["lw x7, 0(x6)"],
                    LOAD_AF,
                    "lw through a page mapped to the access-fault address",
                    {LOAD_AF: vt(fva)},
                    handler="VS",
                )
            else:
                start = va + 0x4FFE
                t.emit(f"li x6, {hex(start)}")
                mwin(
                    t,
                    None,
                    "VS",
                    ["jalr x1, 0(x6)"],
                    INSN_PF,
                    "32-bit instruction whose second half is in an invalid page",
                    {INSN_PF: vt(start if MUT == "vstval_fetch_start" else va + 0x5000)},
                    epc=start,
                    handler="VS",
                )
            t.emit(f"csrw {hex(VSATP)}, x0")
            t.emit(HFENCE_VVMA)

        guard(t, "x1", run)

    t.page("P")
    both(t, lambda x: body(x, "base"))
    with t.only_if(HAS_FA_KIND["load"]):
        both(t, lambda x: body(x, "fa"))
    with t.only_if(C16):
        both(t, lambda x: body(x, "c"))
    with t.only_if("!defined(ZCA_SUPPORTED) && !defined(C_SUPPORTED)"):
        tgt = t.label("vmis_tgt")
        t.la("x6", f"{tgt}+2")
        mwin(
            t,
            None,
            "VS",
            ["jalr x1, 0(x6)", f"j {tgt}_after", f"{tgt}:", "nop", "nop", f"{tgt}_after:"],
            0,
            "jalr to a 2-byte-aligned target (no C)",
            {0: vt(f"{tgt}+2")},
            handler="VS",
        )
    t.emit(f"li x7, {hex(VS_DELEG)}")
    t.emit("csrc 0x602, x7  // hedeleg = 0")
    return [t]


# ================================================================ Ssstrict
SSSTRICT = "src/priv/ssstrict.adoc"


def R(f7: int, rs2: int, rs1: int, f3: int, rd: int, op: int) -> int:
    return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def I_(imm: int, rs1: int, f3: int, rd: int, op: int) -> int:
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


# Instructions of extensions the hart lacks (gated on their *_SUPPORTED macros), and reserved encodings. x6 points at
# a scratch page, x8 is a nonzero source. (condition, encoding, note, run in U-mode too)
UNIMPL_OPS = [
    ("!defined(M_SUPPORTED) && !defined(ZMMUL_SUPPORTED)", R(1, 8, 6, 0, 7, 0x33), "mul x7, x6, x8 (no M/Zmmul)", True),
    ("!defined(M_SUPPORTED)", R(1, 8, 6, 4, 7, 0x33), "div x7, x6, x8 (no M)", False),
    ("!defined(A_SUPPORTED) && !defined(ZAAMO_SUPPORTED)", R(0, 8, 6, 2, 7, 0x2F), "amoadd.w (no Zaamo)", False),
    ("!defined(A_SUPPORTED) && !defined(ZALRSC_SUPPORTED)", R(8, 0, 6, 2, 7, 0x2F), "lr.w (no Zalrsc)", False),
    ("!defined(ZACAS_SUPPORTED)", R(5 << 2, 8, 6, 2, 7, 0x2F), "amocas.w (no Zacas)", False),
    ("!defined(ZABHA_SUPPORTED)", R(0, 8, 6, 0, 7, 0x2F), "amoadd.b (no Zabha)", False),
    ("!defined(ZBA_SUPPORTED)", R(0x10, 8, 6, 2, 7, 0x33), "sh1add (no Zba)", True),
    ("!defined(ZBB_SUPPORTED) && !defined(ZBKB_SUPPORTED)", R(0x20, 8, 6, 7, 7, 0x33), "andn (no Zbb/Zbkb)", False),
    ("!defined(ZBB_SUPPORTED)", I_(0x600, 6, 1, 7, 0x13), "clz (no Zbb)", False),
    ("!defined(ZBS_SUPPORTED)", R(0x14, 8, 6, 1, 7, 0x33), "bset (no Zbs)", False),
    ("!defined(ZBC_SUPPORTED) && !defined(ZBKC_SUPPORTED)", R(5, 8, 6, 1, 7, 0x33), "clmul (no Zbc/Zbkc)", False),
    ("!defined(ZBKB_SUPPORTED)", R(4, 8, 6, 4, 7, 0x33), "pack x7, x6, x8 (no Zbkb)", False),
    ("!defined(ZICOND_SUPPORTED)", R(7, 8, 6, 5, 7, 0x33), "czero.eqz (no Zicond)", False),
    ("!defined(ZICBOM_SUPPORTED)", I_(1, 6, 2, 0, 0x0F), "cbo.clean (no Zicbom)", False),
    ("!defined(ZICBOZ_SUPPORTED)", I_(4, 6, 2, 0, 0x0F), "cbo.zero (no Zicboz)", False),
    ("!defined(ZIFENCEI_SUPPORTED)", 0x0000100F, "fence.i (no Zifencei)", True),
    ("!defined(ZAWRS_SUPPORTED)", 0x00D00073, "wrs.nto (no Zawrs)", False),
    ("!defined(V_SUPPORTED) && !defined(ZVE32X_SUPPORTED)", 0x00007057, "vsetvli x0, x0, e8 (no vector)", False),
    ("!defined(F_SUPPORTED)", I_(0, 6, 2, 0, 0x07), "flw f0, 0(x6) (no F)", True),
    ("defined(F_SUPPORTED) && !defined(D_SUPPORTED)", 0x02007053, "fadd.d (F without D)", False),
    (
        "defined(F_SUPPORTED) && !defined(ZFH_SUPPORTED) && !defined(ZFHMIN_SUPPORTED) && !defined(ZFBFMIN_SUPPORTED)",
        I_(0, 6, 1, 0, 0x07),
        "flh f0, 0(x6) (no Zfh/Zfhmin/Zfbfmin)",
        False,
    ),
    ("defined(D_SUPPORTED) && !defined(Q_SUPPORTED)", I_(0, 6, 4, 0, 0x07), "flq f0, 0(x6) (no Q)", False),
    ("!defined(H_SUPPORTED)", 0x22000073, "hfence.vvma (no H)", False),
    ("!defined(H_SUPPORTED)", R(0x34, 0, 6, 4, 7, 0x73), "hlv.w (no H)", False),
    ("!defined(SVINVAL_SUPPORTED)", 0x16000073, "sinval.vma (no Svinval)", False),
    ("__riscv_xlen == 32", I_(0, 6, 3, 7, 0x03), "ld (reserved on RV32)", True),
    ("__riscv_xlen == 32", I_(0, 6, 6, 7, 0x03), "lwu (reserved on RV32)", False),
    ("__riscv_xlen == 32", (8 << 20) | (6 << 15) | (3 << 12) | 0x23, "sd (reserved on RV32)", False),
    ("__riscv_xlen == 32", I_(1, 6, 0, 7, 0x1B), "addiw (reserved on RV32)", False),
    ("__riscv_xlen == 32", I_(32, 6, 1, 7, 0x13), "slli shamt=32 (reserved on RV32)", True),
    ("__riscv_xlen == 32", I_(0x400 | 33, 6, 5, 7, 0x13), "srai shamt=33 (reserved on RV32)", False),
    ("__riscv_xlen == 64", I_(0, 6, 7, 7, 0x03), "load funct3=111 (reserved on RV64)", True),
    ("__riscv_xlen == 64", (8 << 20) | (6 << 15) | (4 << 12) | 0x23, "store funct3=100 (reserved on RV64)", False),
    ("__riscv_xlen == 64", I_(32, 6, 1, 7, 0x1B), "slliw shamt=32 (reserved)", False),
    ("__riscv_xlen == 64", I_(0x400 | 32, 6, 5, 7, 0x1B), "sraiw shamt=32 (reserved)", False),
]
NO_C = "!defined(ZCA_SUPPORTED) && !defined(C_SUPPORTED)"

# Standard-space CSR addresses no ratified extension allocates (tests/env/encoding.h has none of them), by
# encoding class: (address, lowest privilege that could access it: U, S, H, M)
UNALLOC = [
    (0x0F7, "U"),
    (0x4F3, "U"),
    (0xCB7, "U"),
    (0x1F7, "S"),
    (0x5B7, "S"),
    (0x9B7, "S"),
    (0xDB7, "S"),
    (0x2F7, "H"),
    (0x6B7, "H"),
    (0xAB7, "H"),
    (0xEB7, "H"),
    (0x3F7, "M"),
    (0x77F, "M"),
    (0xBB7, "M"),
    (0xF7F, "M"),
]
ALL_FORMS = {0x0F7, 0x1F7, 0x6B7, 0x3F7}
LEVEL = {"U": 0, "S": 1, "H": 2, "M": 3}
MODE_LEVEL = {"U": 0, "S": 2, "M": 3, "VS": 1, "VU": 0}  # VS reaches S-level (VS CSRs), HS reaches H-level

# CSRs of extensions the hart lacks: (condition, address, name, level)
UNIMPL_CSRS = [
    ("!defined(F_SUPPORTED) && !defined(ZFINX_SUPPORTED)", 0x003, "fcsr", "U"),
    ("!defined(V_SUPPORTED) && !defined(ZVE32X_SUPPORTED)", 0x008, "vstart", "U"),
    ("!defined(V_SUPPORTED) && !defined(ZVE32X_SUPPORTED)", 0xC22, "vlenb", "U"),
    ("!defined(ZKR_SUPPORTED)", 0x015, "seed", "U"),
    ("!defined(ZICFISS_SUPPORTED)", 0x011, "ssp", "U"),
    ("!defined(ZCMT_SUPPORTED)", 0x017, "jvt", "U"),
    ("!defined(ZICNTR_SUPPORTED)", 0xC00, "cycle", "U"),
    ("!defined(SSTC_SUPPORTED)", 0x14D, "stimecmp", "S"),
    ("!defined(SSCOFPMF_SUPPORTED)", 0xDA0, "scountovf", "S"),
    ("!defined(SSSTATEEN_SUPPORTED) && !defined(SMSTATEEN_SUPPORTED)", 0x10C, "sstateen0", "S"),
    (
        "!defined(SSCSRIND_SUPPORTED) && !defined(SSAIA_SUPPORTED) && !defined(SMCSRIND_SUPPORTED) && !defined(SMAIA_SUPPORTED)",
        0x150,
        "siselect",
        "S",
    ),
    ("!defined(SSQOSID_SUPPORTED)", 0x181, "srmcfg", "S"),
    ("!defined(H_SUPPORTED)", 0x600, "hstatus", "H"),
    ("!defined(H_SUPPORTED)", 0x200, "vsstatus", "H"),
]
UNIMPL_CSRS_M = [
    ("!defined(S_SUPPORTED)", 0x100, "sstatus", "S"),
    ("!defined(S_SUPPORTED)", 0x180, "satp", "S"),
    ("!defined(H_SUPPORTED)", 0x34A, "mtinst", "M"),
    ("!defined(H_SUPPORTED)", 0x34B, "mtval2", "M"),
    ("!defined(SMSTATEEN_SUPPORTED)", 0x30C, "mstateen0", "M"),
    ("!defined(SMCSRIND_SUPPORTED) && !defined(SMAIA_SUPPORTED)", 0x350, "miselect", "M"),
    ("!defined(SMRNMI_SUPPORTED)", 0x740, "mnscratch", "M"),
    ("!defined(SDTRIG_SUPPORTED) && !defined(SDEXT_SUPPORTED)", 0x7A0, "tselect", "M"),
]


def strict_tv(e: int, note: str = "") -> list:
    return [0] if MUT == "strict_tval_other" else [0, e]


def csr_win(t: SvTest, mode: str, csr: int, form: tuple, handler: str, desc: str) -> None:
    from sxlib import form_enc

    e = form_enc(csr, form)
    t.emit("li x6, 0x2a")
    note = f"{form[0].replace('rd=x7', '').replace('rs1=x6', 'x6').strip()} {hex(csr)}"
    expect = ILLEGAL
    if MUT == "strict_read_forms_ok" and not form[3]:
        expect = "ok"
    if MUT == "strict_vs_virtual" and mode in ("VS", "VU"):
        expect = VIRTUAL
    mwin(
        t,
        None,
        mode,
        [word(e, note)],
        expect,
        f"{note} ({desc})",
        {ILLEGAL: strict_tv(e)},
        handler="M" if MUT == "strict_m_handler" and handler == "S" else handler,
    )


def op_win(t: SvTest, mode: str, e: int, note: str, handler: str) -> None:
    t.la("x6", "ai_pg_X")
    t.emit("li x8, 3")
    mwin(
        t,
        None,
        mode,
        [word(e, note)],
        ILLEGAL if MUT != "strict_ops_execute" else "ok",
        note,
        {ILLEGAL: strict_tv(e)},
        handler=handler,
    )


def c16_win(t: SvTest, mode: str, handler: str) -> None:
    """Without C, a word whose low bits are not 11 is a reserved encoding: illegal instruction, with xtval 0, the
    16-bit parcel, or the whole word (ACT #2826: parcel-or-exact-word)."""
    w = 0x12340001
    tv = [0, 0x0001, w] if MUT != "strict_tval_other" else [0]
    mwin(
        t,
        None,
        mode,
        [word(w, "16-bit encoding c.nop | 0x1234 << 16, without C")],
        ILLEGAL if MUT != "strict_ops_execute" else "ok",
        "16-bit encoding without C",
        {ILLEGAL: tv},
        handler=handler,
    )


def gen_ssstrict() -> list[TestFile]:
    tests = []
    rule_text = (
        "Furthermore, attempts to execute unimplemented opcodes or access unimplemented CSRs in the standard "
        "or reserved encoding spaces raises an illegal instruction exception that results in a contained "
        "trap to the supervisor-mode trap handler."
    )
    ctx = (
        "Without Ssstrict, these encodings are reserved and their behavior is UNSPECIFIED (csrs.adoc "
        'Zicsr_nonexistent_rsv: "Instructions that access a non-existent CSR address are reserved"). The ACT '
        "Ssstrict suites sweep encoding spaces and every CSR address with four CSR forms, comparing with Sail. "
        "This test adds what they leave out: all twelve CSR instruction forms (including rd=x0, the immediate "
        "forms, and the read-only forms rs1=x0 / uimm=0) on CSR addresses that no ratified extension allocates, "
        "in every encoding class (U/S/H/M level, read-write and read-only); CSRs and instructions of extensions "
        "the configuration does not list (from its *_SUPPORTED macros); RV32/RV64-reserved load, store, "
        "W-form and shift encodings; and the handler that takes the trap. xtval is 0 or the instruction bits "
        "(Sstvala is another extension); a 16-bit encoding on a hart without C may report the parcel or the "
        "whole word (ACT #2826)."
    )
    t = new("Ssstrict", "Ssstrict_unimplemented_opcodes_csr_exception")
    t.describe(
        source=SSSTRICT,
        rule_text=rule_text,
        context=ctx + " This file boots to S-mode: traps from S and U must be taken by the S-mode handler, and "
        "with H, traps from VS/VU by the HS-mode handler (illegal, not virtual: HS-mode could not access the "
        "address either).",
        plan="1. S-mode: each unallocated U-, S- and H-level address (0x0f7, 0x4f3, 0xcb7, 0x1f7, 0x5b7, 0x9b7, "
        "0xdb7, 0x2f7, 0x6b7, 0xab7, 0xeb7): illegal instruction in the S handler, xtval 0 or the encoding; all "
        "twelve forms for 0x0f7, 0x1f7 and 0x6b7, csrrs rs1=x0 / csrrw / csrrci uimm=21 for the others.\n"
        "2. U-mode: the U-level addresses, all forms for 0x0f7.\n"
        "3. With H: VS-mode 0x1f7 and 0x6b7 and VU-mode 0x0f7 (three forms each): illegal instruction (not "
        "virtual) in the HS handler.\n"
        "4. CSRs of extensions not in the configuration (fcsr, vstart, vlenb, seed, ssp, jvt, cycle, stimecmp, "
        "scountovf, sstateen0, siselect, srmcfg, hstatus, vsstatus), from S-mode (and U-mode for the U-level "
        "ones): three forms each.\n"
        "5. Instructions of extensions not in the configuration (M, Zmmul, Zaamo, Zalrsc, Zacas, Zabha, Zba, Zbb, "
        "Zbs, Zbc, Zbkb, Zicond, Zicbom, Zicboz, Zifencei, Zawrs, V, F, D, Zfh, Q, H, Svinval), RV32-reserved "
        "ld/lwu/sd/addiw/slli shamt 32/srai shamt 33, RV64-reserved load/store funct3 and slliw/sraiw shamt 32, "
        "dret and mnret: illegal instruction from S-mode (a subset from U-mode) in the S handler.\n"
        "6. Without C: a 32-bit word whose low bits are 01, from S and U: illegal instruction, xtval 0, the "
        "parcel or the word.",
    )
    t.page("X")
    forms3 = [f for f in CSR_FORMS if f[0] in ("csrrs rs1=x0", "csrrw rd=x7", "csrrci uimm=21")]

    def csr_sweep(mode: str, handler: str, addrs: list) -> None:
        for a, lvl in addrs:
            if LEVEL[lvl] > MODE_LEVEL[mode]:
                continue
            for f in CSR_FORMS if a in ALL_FORMS else forms3:
                csr_win(t, mode, a, f, handler, f"unallocated {lvl}-level address")

    csr_sweep("S", "S", UNALLOC)
    csr_sweep("U", "S", UNALLOC)
    with t.only_if(H):
        for mode, a in (("VS", 0x1F7), ("VS", 0x6B7), ("VU", 0x0F7)):
            for f in forms3:
                csr_win(t, mode, a, f, "S", "unallocated address")
    for cond, a, name, lvl in UNIMPL_CSRS:
        with t.only_if(cond):
            for mode in ("S", "U") if lvl == "U" else ("S",):
                for f in forms3:
                    csr_win(t, mode, a, f, "S", f"{name}, not implemented")
    for cond, e, note, in_u in UNIMPL_OPS:
        with t.only_if(cond):
            for mode in ("S", "U") if in_u else ("S",):
                op_win(t, mode, e, note, "S")
    for e, note in ((0x7B200073, "dret"), (0x70200073, "mnret")):
        op_win(t, "S", e, note, "S")
    with t.only_if(NO_C):
        for mode in ("S", "U"):
            c16_win(t, mode, "S")
    tests.append(t)

    t = new("Ssstrict", "Ssstrict_unimplemented_opcodes_csr_exception", ["I", "Sm", "Ssstrict"], boot="M", suffix="_Sm")
    t.describe(
        source=SSSTRICT,
        rule_text=rule_text,
        context=ctx + " This file is the M-mode part (it also runs on harts without S-mode, where the trap is "
        "taken by the M-mode handler): it boots to M-mode and requires Sm.",
        plan="1. M-mode: every unallocated address of 1 (all levels, M-level 0x3f7, 0x77f, 0xbb7, 0xf7f too): "
        "illegal instruction in the M handler; all twelve forms for 0x0f7, 0x1f7, 0x6b7 and 0x3f7.\n"
        "2. CSRs of extensions not in the configuration, also the M-level ones (sstatus and satp without S, "
        "mtinst and mtval2 without H, mstateen0, miselect, mnscratch, tselect without Sdtrig/Sdext).\n"
        "3. The instruction list of the S-mode file, plus sret without S, and dret and mnret "
        "without the extensions that define them: illegal instruction in the M handler.\n"
        "4. Without C: the 16-bit encoding, xtval 0, the parcel or the word.",
    )
    t.page("X")
    csr_sweep("M", "M", UNALLOC)
    for cond, a, name, _ in UNIMPL_CSRS + UNIMPL_CSRS_M:
        with t.only_if(cond):
            for f in forms3:
                csr_win(t, "M", a, f, "M", f"{name}, not implemented")
    for cond, e, note, _ in UNIMPL_OPS:
        with t.only_if(cond.replace("!defined(H_SUPPORTED)", "!defined(H_SUPPORTED)")):
            op_win(t, "M", e, note, "M")
    for cond, e, note in (
        ("!defined(S_SUPPORTED)", 0x10200073, "sret (no S)"),
        ("!defined(SDEXT_SUPPORTED)", 0x7B200073, "dret (no Sdext)"),
        ("!defined(SMRNMI_SUPPORTED)", 0x70200073, "mnret (no Smrnmi)"),
    ):
        with t.only_if(cond):
            op_win(t, "M", e, note, "M")
    with t.only_if(NO_C):
        c16_win(t, "M", "M")
    tests.append(t)

    # ---- RV64 high-half CSR addresses
    hh_text = (
        "Standard high-half CSRs are accessible only when the base RISC-V instruction set is RV32 (XLEN=32). "
        "For RV64 (when XLEN=64), the addresses of all standard high-half CSRs are reserved, so an attempt "
        "to access a high-half CSR typically raises an illegal-instruction exception."
    )
    hh_ctx = (
        "The rule is in csrs.adoc: on RV64 the high-half addresses are reserved, so without Ssstrict the "
        'outcome is free ("typically"). With Ssstrict, accessing a reserved address must raise '
        "illegal-instruction, so the test is in this suite. RV64 only (the files pass trivially on RV32). "
        "xtval is 0 or the encoding."
    )
    HH_S = [
        (0xC80, "cycleh", "U"),
        (0xC81, "timeh", "U"),
        (0xC82, "instreth", "U"),
        (0xC83, "hpmcounter3h", "U"),
        (0xC9F, "hpmcounter31h", "U"),
        (0x15D, "stimecmph", "S"),
        (0x114, "sieh", "S"),
        (0x154, "siph", "S"),
        (0x612, "hedelegh", "H"),
        (0x615, "htimedeltah", "H"),
        (0x61A, "henvcfgh", "H"),
        (0x25D, "vstimecmph", "H"),
    ]
    HH_M = [
        (0x310, "mstatush", "M"),
        (0x312, "medelegh", "M"),
        (0x313, "midelegh", "M"),
        (0x314, "mieh", "M"),
        (0x31A, "menvcfgh", "M"),
        (0x31C, "mstateen0h", "M"),
        (0x354, "miph", "M"),
        (0x757, "mseccfgh", "M"),
        (0xB80, "mcycleh", "M"),
        (0xB82, "minstreth", "M"),
        (0xB83, "mhpmcounter3h", "M"),
        (0x721, "mhpmevent3h", "M"),
    ]
    t = new("Ssstrict", "Zicsr_high_half_rv64_rsv", ["I", "S", "Ssstrict"], rv64=True)
    t.describe(
        source=CSRS,
        rule_text=hh_text,
        context=hh_ctx + " This file boots to S-mode and covers the U-, S- and H-level high halves; the "
        "M-level ones are in the _Sm file.",
        plan="1. S-mode: cycleh, timeh, instreth, hpmcounter3h, hpmcounter31h, stimecmph, sieh, siph, hedelegh, "
        "htimedeltah, henvcfgh, vstimecmph: csrrs rs1=x0, csrrw and csrrci uimm=21 raise illegal instruction in "
        "the S handler.\n"
        "2. U-mode: the same for the U-level ones.",
    )
    for a, name, lvl in HH_S:
        for mode in ("S", "U") if lvl == "U" else ("S",):
            for f in forms3:
                csr_win(t, mode, a, f, "S", f"{name} on RV64")
    tests.append(t)
    t = new("Ssstrict", "Zicsr_high_half_rv64_rsv", ["I", "Sm", "Ssstrict"], rv64=True, boot="M", suffix="_Sm")
    t.describe(
        source=CSRS,
        rule_text=hh_text,
        context=hh_ctx + " This file is the M-mode part: every high-half address of the S-mode file, and the "
        "M-level ones, accessed from M-mode.",
        plan="1. M-mode: the high halves of the S-mode file, and mstatush, medelegh, midelegh, mieh, menvcfgh, "
        "mstateen0h, miph, mseccfgh, mcycleh, minstreth, mhpmcounter3h, mhpmevent3h: csrrs rs1=x0, csrrw and "
        "csrrci uimm=21 raise illegal instruction in the M handler.",
    )
    for a, name, _ in HH_S + HH_M:
        for f in forms3:
            csr_win(t, "M", a, f, "M", f"{name} on RV64")
    tests.append(t)
    return tests


# ================================================================ Ssintro: intro.adoc and csrs.adoc
SI = "Ssintro"
REQ_S = ["I", "S"]
REQ_M = ["I", "Sm"]
READ_FORMS = [f for f in CSR_FORMS if not f[3]]
WRITE_FORMS = [f for f in CSR_FORMS if f[3]]
F3 = {"csrrw": 1, "csrrs": 2, "csrrc": 3, "csrrwi": 5, "csrrsi": 6, "csrrci": 7}


CNT_BIT = {0xC00: 0, 0xC01: 1, 0xC02: 2}  # cycle, time, instret: their mcounteren/scounteren bits


def cnt_gate(t: SvTest, mode: str, csr: int, body: Callable[[bool], object]) -> None:
    """Run body(enabled) for a counter read from `mode`. The counter-enable bits may be read-only 0
    (mcounteren_flds_rdonly0, scounteren_acc), so they are read back (mcounteren through T-SBI, and scounteren for
    U-mode): a read from S needs mcounteren's bit, from U both. Non-counters and M-mode: body(True)."""
    if csr not in CNT_BIT or mode == "M":
        body(True)
        return
    b = CNT_BIT[csr]
    t.tsbi_csr("READ", "MCOUNTEREN")
    t.emit(f"srli x1, a0, {b}")
    if mode == "U":
        t.emit("csrr x7, scounteren")
        t.emit(f"srli x7, x7, {b}")
        t.emit("and x1, x1, x7")
    t.emit(f"andi x1, x1, 1  // the {mode}-mode read of {hex(csr)} is enabled")
    t.either("x1", lambda: body(True), lambda: body(False))


def acc_win(t: SvTest, mode: str, csr: int, form: tuple, expect: Expect, desc: str, x6: int = 0x2A) -> str:
    """One CSR instruction (form) on csr in `mode`; expect "ok" or a cause (xtval 0 or the encoding)."""
    from sxlib import form_enc

    e = form_enc(csr, form)
    t.emit(f"li x6, {x6}")
    note = f"{form[0]} {hex(csr)}"
    return mwin(t, None, mode, [word(e, note)], expect, f"{note} ({desc})", {ILLEGAL: [0, e], VIRTUAL: [0, e]})


def gen_intro() -> list[TestFile]:
    tests = []

    # ---------------------------------------------------------------- intro.adoc
    t = new(SI, "non_priv_exc", REQ_S)
    t.describe(
        source=INTRO,
        rule_text="attempts to perform operations not permitted by the current privilege mode will cause an "
        "exception to be raised.",
        context="Operations limited to higher privilege: xRET of a higher mode, CSRs of a higher level, "
        "SFENCE.VMA below S, and with H the hypervisor CSRs and instructions from VS/VU. Below HS-mode, an "
        "operation that HS-mode could perform raises virtual-instruction; one that HS-mode could not perform raises "
        "illegal-instruction. xtval is 0 or the encoding.",
        plan="1. U-mode: sret, mret, sfence.vma, csrrs sstatus, csrrs mstatus, csrrw satp: illegal instruction.\n"
        "2. S-mode: mret, csrrs mstatus, csrrw mscratch: illegal instruction.\n"
        "3. With H: VS-mode csrrs hstatus, hfence.gvma: virtual instruction; VS-mode mret, csrrs mstatus: "
        "illegal; VU-mode sret, csrrs sstatus, csrrs hstatus: virtual; VU-mode mret: illegal.\n"
        "4. Contrast: the same CSRs and SRET-free operations that the mode may use do not trap: S-mode csrrs "
        "sstatus and sfence.vma, U-mode csrrs cycle (with Zicntr, counters enabled by the framework).",
    )
    MRET, SRET, SFV = 0x30200073, 0x10200073, 0x12000073

    def op(mode: str, e: int, note: str, cause: Expect) -> None:
        if MUT == "nonpriv_ok" and cause == ILLEGAL and mode == "U":
            cause = "ok"
        mwin(t, None, mode, [word(e, note)], cause, note, {ILLEGAL: [0, e], VIRTUAL: [0, e]})

    for e, note in (
        (SRET, "sret"),
        (MRET, "mret"),
        (SFV, "sfence.vma x0, x0"),
        (enc_csr(0x100, 2, 7, 0), "csrrs x7, sstatus, x0"),
        (enc_csr(0x300, 2, 7, 0), "csrrs x7, mstatus, x0"),
        (enc_csr(0x180, 1, 0, 0), "csrrw x0, satp, x0"),
    ):
        op("U", e, note, ILLEGAL)
    for e, note in (
        (MRET, "mret"),
        (enc_csr(0x300, 2, 7, 0), "csrrs x7, mstatus, x0"),
        (enc_csr(0x340, 1, 7, 7), "csrrw x7, mscratch, x7"),
    ):
        op("S", e, note, ILLEGAL)
    op("S", enc_csr(0x100, 2, 7, 0), "csrrs x7, sstatus, x0", "ok")
    op("S", SFV, "sfence.vma x0, x0", "ok")
    with t.only_if("defined(ZICNTR_SUPPORTED)"):
        cnt_gate(
            t, "U", 0xC00, lambda en: op("U", enc_csr(0xC00, 2, 7, 0), "csrrs x7, cycle, x0", "ok" if en else ILLEGAL)
        )
    with t.only_if(H):
        for mode, e, note, c in (
            ("VS", enc_csr(0x600, 2, 7, 0), "csrrs x7, hstatus, x0", VIRTUAL),
            ("VS", 0x62000073, "hfence.gvma x0, x0", VIRTUAL),
            ("VS", MRET, "mret", ILLEGAL),
            ("VS", enc_csr(0x300, 2, 7, 0), "csrrs x7, mstatus, x0", ILLEGAL),
            ("VU", SRET, "sret", VIRTUAL),
            ("VU", enc_csr(0x100, 2, 7, 0), "csrrs x7, sstatus, x0", VIRTUAL),
            ("VU", enc_csr(0x600, 2, 7, 0), "csrrs x7, hstatus, x0", VIRTUAL),
            ("VU", MRET, "mret", ILLEGAL),
        ):
            op(mode, e, note, c)
    tests.append(t)

    t = new(SI, "priv_levels_tbl", REQ_M, boot="M")
    t.describe(
        source=INTRO,
        rule_text="RISC-V privilege levels: level 0, encoding 00, User/Application (U); level 1, encoding 01, "
        "Supervisor (S); level 2, encoding 10, reserved; level 3, encoding 11, Machine (M).",
        context="The encodings are visible in mstatus.MPP, which a trap into M-mode writes with the privilege the "
        "trap came from. MPP is WARL and may hold only supported modes (mstatus_xpp_warl); 10 is reserved and "
        "never a legal value. The test boots to M-mode, where the framework does not delegate traps.",
        plan="1. ebreak from M, S (with S) and U (with U), taken in M-mode: MPP reads 11, 01 and 00.\n"
        "2. Write MPP = 10: it reads back a value other than 10; the same after writing 11 then 10.",
    )
    for mode, cond in (("M", None), ("S", "defined(S_SUPPORTED)"), ("U", "defined(U_SUPPORTED)")):

        def eb(mode: str = mode) -> None:
            lab = t.label(f"eb{mode}")
            t.allow(1)
            if mode != "M":
                t.enter(mode)
            t.emit(f"{lab}:", 0)
            t.emit("ebreak")
            if mode != "M":
                t.leave()
            outcome_at(t, BREAKPOINT, lab, f"ebreak from {mode}-mode", epc=lab)
            t.emit("AI_LOG(x15, TRAPLOG_STATUS)", 10)
            t.emit("srli x15, x15, 11")
            t.emit("andi x15, x15, 3")
            enc = {"M": 3, "S": 1, "U": 0}[mode]
            if MUT == "mpp_s_is_2" and mode == "S":
                enc = 2
            t.check("x15", enc, lab, f"mstatus.MPP after a trap from {mode}-mode is {enc:02b}")

        if cond:
            with t.only_if(cond):
                eb()
        else:
            eb()
    for pre in (None, 3):
        lab = t.label("mpp2")
        t.emit("li x6, 0x1800")
        if pre:
            t.emit("csrs mstatus, x6  // MPP = 11")
        t.emit("csrc mstatus, x6")
        t.emit("li x6, 0x1000")
        t.emit(f"{lab}:", 0)
        t.emit("csrs mstatus, x6  // MPP = 10 (reserved)")
        t.emit("csrr x7, mstatus")
        t.emit("srli x7, x7, 11")
        t.emit("andi x7, x7, 3")
        t.emit("addi x7, x7, -2")
        t.emit("snez x7, x7  // MPP != 10")
        if MUT == "mpp_2_held":
            t.emit("seqz x7, x7")
        t.check_bool("x7", lab, "mstatus.MPP = 10 (reserved) reads back a legal value")
        t.emit("li x6, 0x1800")
        t.emit("csrs mstatus, x6  // MPP = 11")
    tests.append(t)

    t = new(SI, "priv_combs_tbl", REQ_M, boot="M")
    t.describe(
        source=INTRO,
        rule_text="Supported combination of privilege modes: 1 level: M (simple embedded systems); 2 levels: M, U "
        "(secure embedded systems); 3 levels: M, S, U (systems running Unix-like operating systems).",
        context="So M is always present, and a hart with S-mode also has U-mode (no M+S hart). The supported modes "
        "are seen in misa (S bit 18, U bit 20) and in the legal values of mstatus.MPP (WARL; it holds every "
        "supported mode, mstatus_xpp_warl).",
        plan="1. MPP = 11 reads 11.\n"
        "2. MPP = 01 reads 01 exactly when misa.S = 1; MPP = 00 reads 00 exactly when misa.U = 1.\n"
        "3. misa.S = 1 implies misa.U = 1 (and MPP can hold 01 only if it can hold 00).",
    )

    def mpp(v: int, reg: str) -> None:
        t.emit("li x6, 0x1800")
        t.emit("csrc mstatus, x6")
        if v:
            t.emit(f"li x6, {v << 11:#x}")
            t.emit("csrs mstatus, x6")
        t.emit(f"csrr {reg}, mstatus")
        t.emit(f"srli {reg}, {reg}, 11")
        t.emit(f"andi {reg}, {reg}, 3")

    lab = t.label("combs")
    t.emit(f"{lab}:", 0)
    mpp(3, "x7")
    t.check("x7", 3, lab, "MPP = 11 reads 11 (M-mode is always present)")
    mpp(1, "x8")
    t.emit("addi x8, x8, -1")
    t.emit("seqz x8, x8  // S: MPP holds 01")
    mpp(0, "x9")
    t.emit("seqz x9, x9  // U: MPP holds 00")
    t.emit("csrr x1, misa")
    t.emit("srli x6, x1, 18")
    t.emit("andi x6, x6, 1  // misa.S")
    t.emit("srli x7, x1, 20")
    t.emit("andi x7, x7, 1  // misa.U")
    t.emit("xor x1, x6, x8")
    t.check("x1", 0, lab, "MPP can hold 01 exactly when misa.S = 1")
    t.emit("xor x1, x7, x9")
    t.check("x1", 0, lab, "MPP can hold 00 exactly when misa.U = 1")
    t.emit("seqz x1, x6")
    t.emit("or x1, x1, x7  // !S or U")
    if MUT == "s_without_u":
        t.emit("seqz x1, x1")
    t.check_bool("x1", lab, "misa.S = 1 implies misa.U = 1 (no M+S combination)")
    t.emit("li x6, 0x1800")
    t.emit("csrs mstatus, x6  // MPP = 11")
    tests.append(t)

    # ---------------------------------------------------------------- csrs.adoc
    t = new(SI, "Zicsr_higher_priv", REQ_S)
    t.describe(
        source=CSRS,
        rule_text="although CSRs and instructions are associated with one privilege level, they are also "
        "accessible at all higher privilege levels.",
        context="This file: S-mode (and VS-mode) use U-level CSRs and instructions; HS-mode uses VS-level CSRs "
        "(0x2xx) and VU-mode-level ones. M-mode is in the _Sm file. U-level CSRs used: fflags/frm/fcsr (F, FS on), "
        "cycle/instret (Zicntr; mcounteren is all ones from the framework), vl/vlenb (V). The framework's own "
        "CSRs are only written with their own value.",
        plan="1. S-mode: write fflags = 0x15, frm = 3 and read them (and fcsr = 0x75); read cycle, instret, vl, "
        "vlenb; execute ecall-free U-level instructions (fence, fence.i): no trap.\n"
        "2. With H, HS-mode: write vsepc and vstval and read them back; and VS-mode reads fflags (vsstatus.FS "
        "on): no trap.",
    )
    t.emit("li x7, 0")
    with t.only_if("defined(F_SUPPORTED)"):
        for csr, v, name in ((0x001, 0x15, "fflags"), (0x002, 3, "frm")):
            t.emit(f"li x6, {v}")
            lab = mwin(
                t,
                None,
                "S",
                [f"csrrw x0, {hex(csr)}, x6", f"csrr x7, {hex(csr)}"],
                "ok",
                f"S-mode {name} write/read",
                {},
            )
            t.check("x7", 0 if MUT == "higher_priv_no_write" else v, lab, f"S-mode: {name} = {v:#x} reads back")
        lab = mwin(t, None, "S", ["csrr x7, fcsr"], "ok", "S-mode fcsr read", {})
        t.check("x7", 0x75, lab, "S-mode: fcsr reads frm << 5 | fflags")
    with t.only_if("defined(ZICNTR_SUPPORTED)"):
        for name, a in (("cycle", 0xC00), ("instret", 0xC02)):
            cnt_gate(
                t,
                "S",
                a,
                lambda en, name=name: mwin(
                    t, None, "S", [f"csrr x7, {name}"], "ok" if en else ILLEGAL, f"S-mode {name} read", {}
                ),
            )
    with t.only_if("defined(V_SUPPORTED)"):
        for name in ("0xc20", "0xc22"):
            mwin(t, None, "S", [f"csrr x7, {name}"], "ok", f"S-mode read of {name}", {})
    mwin(t, None, "S", ["fence"], "ok", "S-mode fence", {})
    with t.only_if("defined(ZIFENCEI_SUPPORTED)"):
        mwin(t, None, "S", ["fence.i"], "ok", "S-mode fence.i", {})
    with t.only_if(H):
        for csr, name in ((0x241, "vsepc"), (0x243, "vstval")):
            t.la("x6", "rvtest_code_begin+8")
            lab = mwin(
                t, None, "S", [f"csrw {hex(csr)}, x6", f"csrr x7, {hex(csr)}"], "ok", f"HS-mode {name} write/read", {}
            )
            t.check("x7", "rvtest_code_begin+8", lab, f"HS-mode: {name} reads back")
        with t.only_if("defined(F_SUPPORTED)"):
            mwin(t, None, "VS", ["csrr x7, fflags"], "ok", "VS-mode fflags read", {})
    tests.append(t)

    t = new(SI, "Zicsr_higher_priv", REQ_M, boot="M", suffix="_Sm")
    t.describe(
        source=CSRS,
        rule_text="although CSRs and instructions are associated with one privilege level, they are also "
        "accessible at all higher privilege levels.",
        context="This file is the M-mode part: M-mode uses S-level (sepc, stval, scause, satp), H-level (htval, "
        "vsepc, with H) and U-level (fflags with F, cycle/instret with Zicntr) CSRs, and S-level instructions "
        "(sfence.vma with S). The trap CSRs are written with in-image values and no trap is taken in between.",
        plan="1. M-mode: write sepc, stval and scause (cause 3) and read them back; write satp = 0 and read 0; "
        "sfence.vma: no trap.\n"
        "2. With H: htval and vsepc written and read back.\n"
        "3. fflags written and read (F); cycle and instret read (Zicntr).",
    )
    with t.only_if("defined(S_SUPPORTED)"):
        for csr, name, val in (
            (0x141, "sepc", "rvtest_code_begin+4"),
            (0x143, "stval", "rvtest_code_begin+0x10"),
            (0x142, "scause", 3),
            (0x180, "satp", 0),
        ):
            if isinstance(val, str):
                t.la("x6", val)
            else:
                t.li("x6", val)
            lab = mwin(
                t, None, "M", [f"csrw {hex(csr)}, x6", f"csrr x7, {hex(csr)}"], "ok", f"M-mode {name} write/read", {}
            )
            t.check("x7", val if MUT != "higher_priv_no_write" else 1, lab, f"M-mode: {name} reads back")
        mwin(t, None, "M", ["sfence.vma x0, x0"], "ok", "M-mode sfence.vma", {})
    with t.only_if(H):
        for csr, name in ((0x643, "htval"), (0x241, "vsepc")):
            t.la("x6", "rvtest_code_begin+0x20")
            lab = mwin(
                t, None, "M", [f"csrw {hex(csr)}, x6", f"csrr x7, {hex(csr)}"], "ok", f"M-mode {name} write/read", {}
            )
            t.check("x7", "rvtest_code_begin+0x20", lab, f"M-mode: {name} reads back")
    with t.only_if("defined(F_SUPPORTED)"):
        t.li("x6", 0x0A)
        lab = mwin(t, None, "M", ["csrw fflags, x6", "csrr x7, fflags"], "ok", "M-mode fflags write/read", {})
        t.check("x7", 0x0A, lab, "M-mode: fflags reads back")
    with t.only_if("defined(ZICNTR_SUPPORTED)"):
        for name in ("cycle", "instret"):
            mwin(t, None, "M", [f"csrr x7, {name}"], "ok", f"M-mode {name} read", {})
    tests.append(t)

    # ---- no read side effects
    rd_forms = [("csrrs rd, x0", 2, 0), ("csrrc rd, x0", 3, 0), ("csrrsi rd, 0", 6, 0), ("csrrci rd, 0", 7, 0)]

    def read_twice(t: SvTest, csr: int, name: str, preset: Value | None) -> None:
        """Read csr with every read-only form, twice; every read returns the first value."""
        if preset is not None:
            if isinstance(preset, str):
                t.la("x6", preset)
            else:
                t.load("x6", preset)
            t.emit(f"csrw {hex(csr)}, x6")
        lab = t.label(f"rd{csr:x}")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrr x8, {hex(csr)}  // reference read")
        for _ in range(2):
            for fname, f3, _z in rd_forms:
                t.emit(word(enc_csr(csr, f3, 7, 0), f"{fname} x7, {name}"))
                t.emit("xor x9, x7, x8")
                if MUT == "read_clears" and name in ("fflags", "mcause", "scause"):
                    t.emit("not x9, x9")
                t.check("x9", 0, lab, f"{name}: {fname} reads the same value (no read side effect)")
        t.emit(f"csrr x7, {hex(csr)}")
        t.emit("xor x9, x7, x8")
        t.check("x9", 0, lab, f"{name}: unchanged after the reads")

    t = new(SI, "Zicsr_no_read_side_effects", REQ_S)
    t.describe(
        source=CSRS,
        rule_text="Standard CSRs do not have side effects on reads but may have side effects on writes.",
        context="Every read-only CSR instruction form (CSRRS/CSRRC with rs1=x0, CSRRSI/CSRRCI with uimm=0) is a "
        "read. A read must not change the CSR (no read-to-clear accrued flags, cause or pending bits) or return a "
        "different value next time. Counters and time change on their own and are not used. This file: S-level "
        "CSRs from S-mode; M-level ones are in the _Sm file.",
        plan="1. Preset sepc, stval, scause (3) and sscratch is left as the framework's value; read sepc, stval, "
        "scause, sscratch, sstatus, sie, sip, satp, scounteren with each read form, twice: all reads equal the "
        "first.\n"
        "2. With F: fflags = 0x1f, frm = 2: the same for fflags, frm and fcsr.\n"
        "3. With H: vsepc, vstval, hstatus, hedeleg likewise.",
    )
    for csr, name, pre in (
        (0x141, "sepc", "rvtest_code_begin+0xc"),
        (0x143, "stval", 0x5A5A5),
        (0x142, "scause", 3),
        (0x140, "sscratch", None),
        (0x100, "sstatus", None),
        (0x104, "sie", None),
        (0x144, "sip", None),
        (0x180, "satp", None),
        (0x106, "scounteren", None),
    ):
        read_twice(t, csr, name, pre)
    with t.only_if("defined(F_SUPPORTED)"):
        read_twice(t, 0x001, "fflags", 0x1F)
        read_twice(t, 0x002, "frm", 2)
        read_twice(t, 0x003, "fcsr", None)
    with t.only_if(H):
        for csr, name, pre in (
            (0x241, "vsepc", "rvtest_code_begin+0x14"),
            (0x243, "vstval", 0x1234),
            (0x600, "hstatus", None),
            (0x602, "hedeleg", None),
        ):
            read_twice(t, csr, name, pre)
    tests.append(t)

    t = new(SI, "Zicsr_no_read_side_effects", REQ_M, boot="M", suffix="_Sm")
    t.describe(
        source=CSRS,
        rule_text="Standard CSRs do not have side effects on reads but may have side effects on writes.",
        context="The M-mode part: M-level CSRs read from M-mode with every read-only form, twice. mip is left out: "
        "its timer bit follows mtime on its own.",
        plan="1. Preset mepc, mtval and mcause (3); read mepc, mtval, mcause, mscratch, mstatus, misa, mie, "
        "medeleg (with S), mtvec, mhartid, mvendorid, menvcfg (with U and Sm 1.12+) and mcounteren (with U): every "
        "read equals "
        "the first.",
    )
    for csr, name, pre, cond in (
        (0x341, "mepc", "rvtest_code_begin+0xc", None),
        (0x343, "mtval", 0x77, None),
        (0x342, "mcause", 3, None),
        (0x340, "mscratch", None, None),
        (0x300, "mstatus", None, None),
        (0x301, "misa", None, None),
        (0x304, "mie", None, None),
        (0x302, "medeleg", None, "defined(S_SUPPORTED)"),
        (0x305, "mtvec", None, None),
        (0xF14, "mhartid", None, None),
        (0xF11, "mvendorid", None, None),
        (0x30A, "menvcfg", None, "defined(U_SUPPORTED) && defined(SM1P12P0_OR_LATER_SUPPORTED)"),
        (0x306, "mcounteren", None, "defined(U_SUPPORTED)"),
    ):
        if cond:
            with t.only_if(cond):
                read_twice(t, csr, name, pre)
        else:
            read_twice(t, csr, name, pre)
    tests.append(t)

    # ---- read-only encoding class and writes to read-only CSRs
    RO_S = [
        ("defined(ZICNTR_SUPPORTED)", 0xC00, "cycle"),
        ("defined(ZICNTR_SUPPORTED)", 0xC02, "instret"),
        ("defined(ZICNTR_SUPPORTED)", 0xC01, "time"),
        ("defined(SSCOFPMF_SUPPORTED)", 0xDA0, "scountovf"),
        ("defined(H_SUPPORTED)", 0xE12, "hgeip"),
        ("defined(V_SUPPORTED)", 0xC22, "vlenb"),
    ]
    RO_M = [(None, 0xF11, "mvendorid"), (None, 0xF12, "marchid"), (None, 0xF13, "mimpid"), (None, 0xF14, "mhartid")]

    def ro_class(t: SvTest, mode: str, lst: list, all_forms: bool) -> None:
        for cond, csr, name in lst:

            def forms(en: bool, csr: int = csr, name: str = name) -> None:
                for f in CSR_FORMS if all_forms else [CSR_FORMS[0], CSR_FORMS[3], CSR_FORMS[7], CSR_FORMS[9]]:
                    exp = ILLEGAL if f[3] or not en else "ok"
                    if MUT == "ro_write_ignored" and f[3]:
                        exp = "ok"
                    if MUT == "ro_read_traps" and not f[3]:
                        exp = ILLEGAL
                    acc_win(
                        t,
                        mode,
                        csr,
                        f,
                        exp,
                        f"{name} (read-only, csr[11:10]=11)",
                        x6=0 if f[0] == "csrrs rs1=x6" else 0x2A,
                    )

            def body(csr: int = csr, forms: Callable = forms) -> None:
                cnt_gate(t, mode, csr, forms)

            if cond:
                with t.only_if(cond):
                    body()
            else:
                body()

    t = new(SI, "Zicsr_rw", REQ_S)
    t.describe(
        source=CSRS,
        rule_text="The top two bits (csr[11:10]) indicate whether the register is read/write (`00`,`01`, or `10`) "
        "or read-only (`11`).",
        context="Read-write classes: CSRs with csr[11:10] = 00 (sstatus 0x100, sscratch 0x140), 01 (hstatus "
        "0x600, with H) and 10 (none at S level; mcycle 0xb00 in the _Sm file) accept writes. Read-only class: "
        "cycle/instret/time (Zicntr), scountovf (Sscofpmf), hgeip (H), vlenb (V) accept reads and reject writes "
        "(Zicsr_illegal_acc covers every form). Framework CSRs are written with their own value.",
        plan="1. S-mode: csrrw of sstatus, sscratch and (H) hstatus with their own values, and csrrs x0 of each: no "
        "trap.\n"
        "2. S-mode: csrrw rd=x7 and csrrwi of each implemented read-only CSR raise illegal instruction; csrrs "
        "rs1=x0 and csrrsi uimm=0 do not.",
    )
    for csr, name, cond in ((0x100, "sstatus", None), (0x140, "sscratch", None), (0x600, "hstatus", H)):

        def own(csr: int = csr, name: str = name) -> None:
            t.emit(f"csrr x6, {hex(csr)}")
            mwin(
                t,
                None,
                "S",
                [f"csrrw x7, {hex(csr)}, x6"],
                "ok" if MUT != "rw_class_traps" else ILLEGAL,
                f"csrrw of {name} (csr[11:10]={csr >> 10:02b}) with its own value",
                {},
            )

        if cond:
            with t.only_if(cond):
                own()
        else:
            own()
    ro_class(t, "S", RO_S, False)
    tests.append(t)

    t = new(SI, "Zicsr_rw", REQ_M, boot="M", suffix="_Sm")
    t.describe(
        source=CSRS,
        rule_text="The top two bits (csr[11:10]) indicate whether the register is read/write (`00`,`01`, or `10`) "
        "or read-only (`11`).",
        context="The M-mode part: mstatus (00), mcycle and minstret (10) accept writes in M-mode; mvendorid, "
        "marchid, mimpid and mhartid (11) reject them. mcycle/minstret are written with their current value.",
        plan="1. csrrw of mstatus, mcycle and minstret with their current values: no trap.\n"
        "2. csrrw rd=x7 and csrrwi of mvendorid, marchid, mimpid, mhartid raise illegal instruction; csrrs rs1=x0 "
        "and csrrsi uimm=0 do not.",
    )
    for csr, name in ((0x300, "mstatus"), (0xB00, "mcycle"), (0xB02, "minstret")):
        t.emit(f"csrr x6, {hex(csr)}")
        mwin(
            t,
            None,
            "M",
            [f"csrrw x7, {hex(csr)}, x6"],
            "ok" if MUT != "rw_class_traps" else ILLEGAL,
            f"csrrw of {name} (csr[11:10]={csr >> 10:02b}) with its value",
            {},
        )
    ro_class(t, "M", RO_M, False)
    tests.append(t)

    t = new(SI, "Zicsr_illegal_acc", REQ_S)
    t.describe(
        source=CSRS,
        rule_text="Attempts to write a read-only CSR address raise illegal-instruction exceptions.",
        context="An attempted write is any CSRRW/CSRRWI (even rd=x0 or uimm=0), and CSRRS/CSRRC with rs1 != x0 "
        "(even if the register holds 0) or CSRRSI/CSRRCI with uimm != 0; rs1=x0 and uimm=0 are reads. This file "
        "uses the read-only CSRs an S-level hart may have, from S-mode and U-mode (cycle from U with the "
        "counter enables, read back because they may be read-only 0); the M-level ones are in the _Sm file.",
        plan="1. S-mode: all twelve forms on cycle, instret, time (Zicntr), scountovf (Sscofpmf), hgeip (H) and "
        "vlenb (V): the eight write forms (csrrs rs1=x6 with x6 = 0 too) raise illegal instruction with xtval 0 "
        "or the encoding; the four read forms do not trap, unless the counter-enable bit read back is 0 (then "
        "they raise illegal instruction too).\n"
        "2. U-mode: the same on cycle (Zicntr), with mcounteren.CY and scounteren.CY read back.\n"
        "3. With H and Zicntr: VS and VU csrrw/csrrw x0/csrrs x6 of cycle raise illegal instruction (not virtual: "
        "HS-mode could not write it either).",
    )
    ro_class(t, "S", RO_S, True)
    ro_class(t, "U", RO_S[:1], True)
    with t.only_if(H):
        for mode in ("VS", "VU"):
            for f in [x for x in CSR_FORMS if x[3]][:3]:
                with t.only_if("defined(ZICNTR_SUPPORTED)"):
                    acc_win(
                        t,
                        mode,
                        0xC00,
                        f,
                        ILLEGAL if MUT != "ro_write_virtual" else VIRTUAL,
                        "cycle (read-only) from a virtual mode: illegal, as HS-mode could not write it either",
                    )
    tests.append(t)

    t = new(SI, "Zicsr_illegal_acc", REQ_M, boot="M", suffix="_Sm")
    t.describe(
        source=CSRS,
        rule_text="Attempts to write a read-only CSR address raise illegal-instruction exceptions.",
        context="The M-mode part: mvendorid, marchid, mimpid and mhartid from M-mode.",
        plan="1. All twelve forms on mvendorid, marchid, mimpid, mhartid: write forms (csrrs/csrrc with x6 = 0 "
        "too) raise illegal instruction, read forms do not.",
    )
    ro_class(t, "M", RO_M, True)
    tests.append(t)

    # ---- privilege encoding and insufficient privilege
    t = new(SI, "Zicsr_access", REQ_S)
    t.describe(
        source=CSRS,
        rule_text="The next two bits (csr[9:8]) encode the lowest privilege level that can access the CSR, with "
        "the pattern `10` representing hypervisor CSRs.",
        context="One CSR per level: U (00) cycle (Zicntr) or fflags (F), S (01) sscratch, hypervisor (10) "
        "hstatus (H), M (11) mscratch. Each is read (csrrs rs1=x0) from U-mode and S-mode: allowed exactly when "
        "the mode is at least the CSR's level (HS-mode reaches hypervisor CSRs). VS/VU outcomes are "
        "Zicsr_illegal_mode; M-mode is the _Sm file.",
        plan="1. U-mode: cycle and fflags read; sscratch, hstatus, mscratch raise illegal instruction.\n"
        "2. S-mode: cycle, fflags, sscratch and hstatus read; mscratch raises illegal instruction.",
    )
    LVL = [
        ("defined(ZICNTR_SUPPORTED)", 0xC00, "cycle", 0),
        ("defined(F_SUPPORTED)", 0x001, "fflags", 0),
        (None, 0x140, "sscratch", 1),
        (H, 0x600, "hstatus", 2),
        (None, 0x340, "mscratch", 3),
    ]

    def lvl_case(t: SvTest, mode: str, ml: int) -> None:
        for cond, csr, name, lv in LVL:

            def b(csr: int = csr, name: str = name, lv: int = lv) -> None:
                ok = lv <= ml
                if MUT == "access_level_off_by_one" and lv == ml + 1:
                    ok = True
                cnt_gate(
                    t,
                    mode,
                    csr,
                    lambda en: acc_win(
                        t,
                        mode,
                        csr,
                        CSR_FORMS[3],
                        "ok" if ok and en else ILLEGAL,
                        f"{name} (level {lv:02b}) from {mode}",
                    ),
                )

            if cond:
                with t.only_if(cond):
                    b()
            else:
                b()

    lvl_case(t, "U", 0)
    lvl_case(t, "S", 2)
    tests.append(t)

    t = new(SI, "Zicsr_access", REQ_M, boot="M", suffix="_Sm")
    t.describe(
        source=CSRS,
        rule_text="The next two bits (csr[9:8]) encode the lowest privilege level that can access the CSR, with "
        "the pattern `10` representing hypervisor CSRs.",
        context="The M-mode part: M-mode reads every level's representative CSR (with S: sscratch).",
        plan="1. M-mode: cycle, fflags, sscratch (S), hstatus (H) and mscratch read without a trap.",
    )
    LVL_M = [(c if c else None, a, n, lv) for c, a, n, lv in LVL]
    LVL_M[2] = ("defined(S_SUPPORTED)", 0x140, "sscratch", 1)
    for cond, csr, name, lv in LVL_M:

        def bm(csr: int = csr, name: str = name, lv: int = lv) -> None:
            acc_win(t, "M", csr, CSR_FORMS[3], "ok", f"{name} (level {lv:02b}) from M")

        if cond:
            with t.only_if(cond):
                bm()
        else:
            bm()
    tests.append(t)

    t = new(SI, "Zicsr_illegal_mode", REQ_S)
    t.describe(
        source=CSRS,
        rule_text="Attempts to access a CSR address without sufficient privilege raise illegal-instruction "
        "exceptions or, as described in <<sec:hcauses>>, virtual-instruction exceptions.",
        context="Every CSR instruction form, reads included, is an access. From VS/VU, an access HS-mode could make "
        "(hypervisor and VS CSRs from VS; also supervisor CSRs from VU) raises virtual-instruction; an "
        "M-level CSR raises illegal-instruction. xtval is 0 or the encoding.",
        plan="1. U-mode: all twelve forms on sscratch and sstatus, three forms on mscratch: illegal instruction.\n"
        "2. S-mode: all twelve forms on mscratch, three on mstatus: illegal instruction.\n"
        "3. With H: VS-mode hstatus (three forms), hgatp and vsstatus by its own address 0x200 (csrrs rs1=x0): "
        "virtual; VS-mode mscratch (three forms): illegal; VU-mode sstatus (three forms) and hstatus (csrrs "
        "rs1=x0): virtual; VU-mode mscratch (csrrs rs1=x0): illegal.",
    )
    f3_ = [CSR_FORMS[3], CSR_FORMS[0], CSR_FORMS[10]]

    def bad(mode: str, csr: int, name: str, forms: list, cause: int) -> None:
        for f in forms:
            c = cause
            if MUT == "virtual_as_illegal" and c == VIRTUAL:
                c = ILLEGAL
            if MUT == "privilege_reads_ok" and not f[3]:
                c = "ok"
            acc_win(t, mode, csr, f, c, f"{name} from {mode}")

    bad("U", 0x140, "sscratch", CSR_FORMS, ILLEGAL)
    bad("U", 0x100, "sstatus", CSR_FORMS, ILLEGAL)
    bad("U", 0x340, "mscratch", f3_, ILLEGAL)
    bad("S", 0x340, "mscratch", CSR_FORMS, ILLEGAL)
    bad("S", 0x300, "mstatus", f3_, ILLEGAL)
    with t.only_if(H):
        bad("VS", 0x600, "hstatus", f3_, VIRTUAL)
        bad("VS", 0x680, "hgatp", f3_[:1], VIRTUAL)
        bad("VS", 0x340, "mscratch", f3_, ILLEGAL)
        bad("VU", 0x100, "sstatus", f3_, VIRTUAL)
        bad("VU", 0x600, "hstatus", f3_[:1], VIRTUAL)
        bad("VU", 0x340, "mscratch", f3_[:1], ILLEGAL)
        bad("VS", 0x200, "vsstatus (by its own address)", f3_[:1], VIRTUAL)
    tests.append(t)

    # ---- debug ranges
    t = new(SI, "Zicsr_debug_illegal", REQ_M, boot="M")
    t.describe(
        source=CSRS,
        rule_text="`0x7B0`-`0x7BF` are only visible to debug mode. Implementations must raise illegal-instruction "
        "exceptions on machine-mode access to the latter set of registers.",
        context="The test never enters Debug Mode, so every M-mode access to 0x7b0-0x7bf (dcsr, dpc, dscratch0/1 "
        "and reserved addresses) must trap, with or without Sdext. xtval is 0 or the encoding.",
        plan="1. M-mode: for each address 0x7b0-0x7bf, csrrs rs1=x0, csrrw rd=x7 and csrrsi uimm=21: illegal "
        "instruction.\n"
        "2. S-mode (with S): csrrs rs1=x0 of dcsr and dpc: illegal instruction.",
    )
    for a in range(0x7B0, 0x7C0):
        for f in (CSR_FORMS[3], CSR_FORMS[0], CSR_FORMS[8]):
            c = ILLEGAL
            if MUT == "debug_dcsr_m_ok" and a == 0x7B0 and not f[3]:
                c = "ok"
            acc_win(t, "M", a, f, c, "debug-mode-only address in M-mode")
    with t.only_if("defined(S_SUPPORTED)"):
        for a in (0x7B0, 0x7B1):
            acc_win(t, "S", a, CSR_FORMS[3], ILLEGAL, "debug-mode-only address in S-mode")
    tests.append(t)

    t = new(SI, "Zicsr_debug_range", REQ_M + ["Sdtrig"], boot="M")
    t.describe(
        source=CSRS,
        rule_text="Machine-mode standard read-write CSRs `0x7A0`-`0x7BF` are reserved for use by the debug system. "
        "Of these CSRs, `0x7A0`-`0x7AF` are accessible to machine mode.",
        context="0x7a0-0x7af hold the Sdtrig trigger CSRs (tselect, tdata1-3, tinfo, tcontrol, mcontext, ...). "
        "Which of them exist is a parameter; tselect, tdata1 and tinfo exist whenever Sdtrig does, so the test "
        "requires Sdtrig and reads them from M-mode. tselect is written with 0 (WARL, 0 is always a legal index). "
        "The 0x7b0-0x7bf half is Zicsr_debug_illegal.",
        plan="1. M-mode: csrrs rs1=x0 of tselect (0x7a0), tdata1 (0x7a1) and tinfo (0x7a4); csrrw tselect = 0 then "
        "read 0: no trap.\n"
        "2. S-mode (with S): tselect read raises illegal instruction (an M-level CSR).",
    )
    for a, name in ((0x7A0, "tselect"), (0x7A1, "tdata1"), (0x7A4, "tinfo")):
        acc_win(t, "M", a, CSR_FORMS[3], "ok" if MUT != "trigger_csrs_trap" else ILLEGAL, f"{name} in M-mode")
    lab = mwin(t, None, "M", ["csrw 0x7a0, x0", "csrr x7, 0x7a0"], "ok", "tselect = 0", {})
    t.check("x7", 0, lab, "tselect = 0 reads 0")
    with t.only_if("defined(S_SUPPORTED)"):
        acc_win(t, "S", 0x7A0, CSR_FORMS[3], ILLEGAL, "tselect in S-mode")
    tests.append(t)

    # ---- read-only bits in read/write CSRs
    def ro_bits(t: SvTest, csr: str, mask: int | X, desc: str) -> None:
        lab = t.label("robits")
        t.emit(f"csrr x8, {csr}")
        t.load("x9", mask, f"{desc}")
        t.emit("and x8, x8, x9  // the read-only bits before")
        t.emit(f"{lab}:", 0)
        for op in ("csrs", "csrc"):
            t.emit(f"{op} {csr}, x9")
            t.emit(f"csrr x7, {csr}")
            t.emit("and x7, x7, x9")
            t.emit("xor x7, x7, x8")
            if MUT == "ro_bits_writable":
                t.emit("xor x7, x7, x9")
            t.check("x7", 0, lab, f"{csr}: {op} of the read-only {desc} leaves them unchanged")

    t = new(SI, "Zicsr_write_ro", REQ_S)
    t.describe(
        source=CSRS,
        rule_text="A read/write register might also contain some bits that are read-only, in which case writes to "
        "the read-only bits are ignored.",
        context="Read-only bits used: sstatus.SD (XLEN-1, a summary of FS/VS/XS), sip.STIP and sip.SEIP (bits 5 "
        "and 9: read-only in sip; their sources are M-level). Each is set and cleared through csrs/csrc and "
        "must keep its value. The M-level ones (mip.MSIP/MTIP/MEIP) are in the _Sm file.",
        plan="1. sstatus: csrs and csrc of SD: SD unchanged.\n2. sip: csrs and csrc of STIP and SEIP: unchanged.",
    )
    ro_bits(t, "sstatus", X(1 << 31, 1 << 63), "SD bit")
    ro_bits(t, "sip", 0x220, "STIP and SEIP bits")
    tests.append(t)

    t = new(SI, "Zicsr_write_ro", REQ_M, boot="M", suffix="_Sm")
    t.describe(
        source=CSRS,
        rule_text="A read/write register might also contain some bits that are read-only, in which case writes to "
        "the read-only bits are ignored.",
        context="The M-mode part: mip.MSIP, MTIP and MEIP (bits 3, 7, 11) are read-only in mip (set by the "
        "platform), and mstatus.SD. mstatus.MIE is cleared first so a pending M interrupt is not taken.",
        plan="1. mip: csrs and csrc of MSIP, MTIP and MEIP: unchanged.\n2. mstatus: csrs and csrc of SD: unchanged.",
    )
    t.emit("csrci mstatus, 8  // MIE = 0")
    ro_bits(t, "mip", 0x888, "MSIP, MTIP and MEIP bits")
    ro_bits(t, "mstatus", X(1 << 31, 1 << 63), "SD bit")
    tests.append(t)

    # ---- WPRI
    t = new(SI, "Zicsr_wpri_roz", REQ_M, boot="M")
    t.describe(
        source=CSRS,
        rule_text="For forward compatibility, implementations that do not furnish these fields must make them "
        "read-only zero. These fields are labeled *WPRI* in the register descriptions.",
        context="WPRI fields of mstatus, mstatush and menvcfg (mseccfg is not covered), from the current register figures (machine.adoc): mstatus RV64 "
        "bits 0, 2, 4, 25-31, 40, 43-62; RV32 mstatus bits 0, 2, 4, 25-30 and mstatush bits 0-3, 8, 11-31; "
        "menvcfg bits 1, 8-31, 34-58 (RV32 menvcfgh bits 2-26). No ratified extension furnishes them, so they must "
        f"read zero ({ISSUE}2318: reserved fields must be treated as defined). The S-level views (sstatus, senvcfg) "
        "are in the S suite.",
        plan="1. mstatus: csrs of every WPRI bit: they read 0; csrrw of the value with the WPRI bits set: they read "
        "0.\n"
        "2. RV32 mstatush, menvcfg (with U) and RV32 menvcfgh: csrs of the WPRI bits: they read 0. mstatush and "
        "menvcfg exist from Sm 1.12, so step 2 runs only with SM1P12P0_OR_LATER_SUPPORTED.",
    )
    mst_w = X(0x15 | (0x3F << 25), 0x15 | (0x7F << 25) | (1 << 40) | (((1 << 20) - 1) << 43))
    menv_w = X(0x2 | (0xFFFFFF << 8), 0x2 | (0xFFFFFF << 8) | (((1 << 25) - 1) << 34))

    def wpri(csr: str, mask: Value, desc: str, full: bool = False) -> None:
        lab = t.label("wpri")
        t.load("x9", mask, f"{desc} WPRI bits")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrs {csr}, x9")
        t.emit(f"csrr x7, {csr}")
        t.emit("and x7, x7, x9")
        t.check("x7", mask if MUT == "wpri_stored" else 0, lab, f"{desc}: WPRI bits read 0 after csrs")
        if full:
            t.emit(f"csrr x8, {csr}")
            t.emit("or x8, x8, x9")
            t.emit(f"csrw {csr}, x8")
            t.emit(f"csrr x7, {csr}")
            t.emit("and x7, x7, x9")
            t.check("x7", 0, lab, f"{desc}: WPRI bits read 0 after csrw")
        t.emit(f"csrc {csr}, x9")

    t.emit("csrci mstatus, 8  // MIE = 0")
    wpri("mstatus", mst_w, "mstatus", True)
    with t.rv32_only(), t.only_if("defined(SM1P12P0_OR_LATER_SUPPORTED)"):
        wpri("mstatush", 0xF | 0x100 | (((1 << 21) - 1) << 11), "mstatush")
    with t.only_if("defined(U_SUPPORTED) && defined(SM1P12P0_OR_LATER_SUPPORTED)"):
        wpri("menvcfg", menv_w, "menvcfg")
        with t.rv32_only():
            wpri("menvcfgh", ((1 << 25) - 1) << 2, "menvcfgh")
    tests.append(t)

    # ---- WARL writes never trap
    t = new(SI, "Zicsr_warl", REQ_M, boot="M")
    t.describe(
        source=CSRS,
        rule_text="Implementations will not raise an exception on writes of unsupported values to a *WARL* field.",
        context="WARL CSRs written with values whose fields are mostly unsupported (all ones, 0x55.., 0xaa.., a "
        "random value, 0), each followed by a read and a restore of the saved value, with no trap allowed: "
        "medeleg, mideleg, mie, mcounteren, mcountinhibit (optional, so probed with a read that may trap), menvcfg "
        "(Sm 1.12+), satp, scounteren, senvcfg (S 1.12+), "
        "sie (with S), "
        "hgatp, vsatp, hedeleg, hideleg, hcounteren, henvcfg (with H). mstatus.MIE is 0, so enabling interrupts "
        "in mie takes none in M-mode; no lower mode runs before the restore. Framework-owned CSRs (mtvec, stvec, "
        "mscratch, sscratch), PMP and mseccfg (sticky lock bits) are not written. The legal values read back "
        "are not constrained by this rule.",
        plan="1. For each CSR and each value: csrw, csrr, csrw of the saved value: no trap.",
    )
    vals = [
        X((1 << 32) - 1, (1 << 64) - 1),
        X(0x55555555, 0x5555555555555555),
        X(0xAAAAAAAA, 0xAAAAAAAAAAAAAAAA),
        t.rand_x(),
        0,
    ]
    WARL = [
        (None, "medeleg"),
        (None, "mideleg"),
        (None, "mie"),
        ("defined(U_SUPPORTED)", "mcounteren"),
        ("defined(ZIHPM_SUPPORTED) || defined(ZICNTR_SUPPORTED)", "mcountinhibit"),
        ("defined(U_SUPPORTED) && defined(SM1P12P0_OR_LATER_SUPPORTED)", "menvcfg"),
        ("defined(S_SUPPORTED)", "satp"),
        ("defined(S_SUPPORTED)", "scounteren"),
        ("defined(S_SUPPORTED) && defined(S1P12P0_OR_LATER_SUPPORTED)", "senvcfg"),
        ("defined(S_SUPPORTED)", "sie"),
        (H, "0x680"),
        (H, "0x280"),
        (H, "0x602"),
        (H, "0x603"),
        (H, "0x606"),
        (H, "0x60a"),
    ]
    t.emit("csrci mstatus, 8  // MIE = 0")
    for cond, csr in WARL:

        def w(csr: str = csr) -> None:
            for v in vals:
                t.emit(f"csrr x9, {csr}  // save")
                t.load("x6", v)
                mwin(
                    t,
                    None,
                    "M",
                    [f"csrw {csr}, x6", f"csrr x7, {csr}", f"csrw {csr}, x9"],
                    "ok" if MUT != "warl_traps" else ILLEGAL,
                    f"WARL write of {csr}",
                    {},
                )
            if csr in ("satp", "0x680", "0x280"):
                t.emit("sfence.vma x0, x0")

        if cond in (None,) and csr in ("medeleg", "mideleg"):
            with t.only_if("defined(S_SUPPORTED)"):
                w()
        elif csr == "mcountinhibit" and cond:
            with t.only_if(cond):
                # mcountinhibit is optional (mcountinhibit_not_impl): probe it, x1 = 1 if it reads without a trap
                t.emit("li x1, -1")
                t.window("M", ["csrrs x1, mcountinhibit, x0"], ["ok", ILLEGAL], "mcountinhibit probe", [0, 0x320020F3])
                t.emit("addi x1, x1, 1")
                t.emit("snez x1, x1")
                t.either("x1", w, lambda: None)
        elif cond:
            with t.only_if(cond):
                w()
        else:
            w()
    tests.append(t)

    # ---- wide CSRs and high halves (RV32)
    t = new(SI, "Zicsr_wide_csr_access", REQ_M, boot="M")
    t.describe(
        source=CSRS,
        rule_text="If a standard CSR is wider than XLEN bits, then an explicit read of the CSR returns the "
        "register's least-significant XLEN bits, and an explicit write to the CSR modifies only the register's "
        "least-significant XLEN bits, leaving the upper bits unchanged.",
        context="On RV32, mcycle, minstret, menvcfg and mstatus are 64-bit CSRs whose upper halves are mcycleh, "
        "minstreth, menvcfgh and mstatush. RV64 has no standard CSR wider than 64 bits, so the RV64 build checks "
        "nothing. Counters run, so mcycleh/minstreth are compared with a margin: writing the low half with a small "
        "value cannot carry for thousands of cycles.",
        plan="RV32: 1. mcycleh = 5, then mcycle = 0x10: mcycleh still reads 5; the same for minstret.\n"
        "2. menvcfgh: read it, write menvcfg with all ones and then 0 (its WARL low bits), menvcfgh unchanged (with "
        "U).\n"
        "3. mstatush: read it, write mstatus with its own value: mstatush unchanged.\n"
        "menvcfgh and mstatush exist from Sm 1.12: steps 2 and 3 run only with SM1P12P0_OR_LATER_SUPPORTED.",
    )
    with t.rv32_only():
        for lo, hi in (("mcycle", "mcycleh"), ("minstret", "minstreth")):
            lab = t.label(lo)
            t.emit(f"csrw {lo}, x0")
            t.emit("li x6, 5")
            t.emit(f"csrw {hi}, x6")
            t.emit("li x6, 0x10")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {lo}, x6")
            t.emit(f"csrr x7, {hi}")
            t.check("x7", 0 if MUT == "wide_write_clears_high" else 5, lab, f"a write of {lo} leaves {hi} unchanged")
        with t.only_if("defined(U_SUPPORTED) && defined(SM1P12P0_OR_LATER_SUPPORTED)"):
            lab = t.label("menv")
            t.emit("csrr x8, menvcfgh")
            t.emit("csrr x9, menvcfg")
            t.emit("li x6, -1")
            t.emit(f"{lab}:", 0)
            t.emit("csrw menvcfg, x6")
            t.emit("csrw menvcfg, x0")
            t.emit("csrr x7, menvcfgh")
            t.emit("csrw menvcfg, x9")
            t.emit("xor x7, x7, x8")
            t.check("x7", 0, lab, "writes of menvcfg leave menvcfgh unchanged")
        with t.only_if("defined(SM1P12P0_OR_LATER_SUPPORTED)"):
            lab = t.label("mst")
            t.emit("csrr x8, mstatush")
            t.emit("csrr x6, mstatus")
            t.emit(f"{lab}:", 0)
            t.emit("csrw mstatus, x6")
            t.emit("csrr x7, mstatush")
            t.emit("xor x7, x7, x8")
            t.check("x7", 0, lab, "a write of mstatus leaves mstatush unchanged")
    tests.append(t)

    t = new(SI, "Zicsr_high_half_alias", REQ_M, boot="M")
    t.describe(
        source=CSRS,
        rule_text="The high-half CSR aliases bits 63:32 of its namesake 64-bit CSR, thus providing a way for RV32 "
        "software to read and modify the otherwise-unreachable 32 bits.",
        context="RV32 only (RV64 has no high-half CSRs; the RV64 build checks nothing). If mcycleh is a separate "
        "register rather than bits 63:32 of mcycle, a carry out of mcycle does not reach it. mcountinhibit is "
        "cleared (it is 0 from the framework) so mcycle and minstret count.",
        plan="RV32: 1. mcycle = 0xffffff00, mcycleh = 7, wait 300 iterations: mcycleh reads 8 and mcycle less than "
        "0xffffff00 (the carry reached the high half).\n"
        "2. The same for minstret/minstreth.\n"
        "3. mcycleh written with 0x12345678 reads it back (when mcycle is far from a carry).",
    )
    with t.rv32_only():
        for lo, hi in (("mcycle", "mcycleh"), ("minstret", "minstreth")):
            lab = t.label(lo)
            t.emit(f"csrw {lo}, x0")
            t.emit("li x6, 7")
            t.emit(f"csrw {hi}, x6")
            t.emit("li x6, 0xffffff00")
            t.emit(f"csrw {lo}, x6")
            delay(t, 300)
            t.emit(f"{lab}:", 0)
            t.emit(f"csrr x7, {hi}")
            t.emit(f"csrr x8, {lo}")
            t.check("x7", 7 if MUT == "high_half_separate" else 8, lab, f"{hi} counts the carry out of {lo}")
            t.emit("li x6, 0xffffff00")
            t.emit("sltu x8, x8, x6")
            t.check_bool("x8", lab, f"{lo} wrapped past 2^32")
        lab = t.label("rw")
        t.emit("csrw mcycle, x0")
        t.emit("li x6, 0x12345678")
        t.emit(f"{lab}:", 0)
        t.emit("csrw mcycleh, x6")
        t.emit("csrr x7, mcycleh")
        t.check("x7", 0x12345678, lab, "mcycleh = 0x12345678 reads back")
    tests.append(t)
    return tests


# ================================================================ driver
def gen() -> list[TestFile]:
    tests: list[TestFile] = []
    tests += gen_tvec()
    tests += gen_stvala()
    tests += gen_ssu64xl()
    tests += gen_ssccptr()
    tests += gen_svvptc()
    tests += gen_svrsw()
    tests += gen_atp_modes()
    tests += gen_shtvala()
    tests += gen_shvstvala()
    tests += gen_ssstrict()
    tests += gen_intro()
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
