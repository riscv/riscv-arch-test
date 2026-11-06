# SPDX-License-Identifier: Apache-2.0
"""H suite: two-stage address translation (hgatp, G-stage, guest-page faults, htval/mtval2, htinst/mtinst
pseudoinstructions, MXR at both levels, hypervisor fences, vsatp WARL and endianness-free CSR behavior).

Accesses are made by HLV/HSV in HS-mode (no guest code runs) or by real VS-/VU-mode code. For guest code the
test image is identity-mapped in both stages by root-level superpages (hmem.PT.identity). G-stage modes are
probed at run time; Sv39x4 (RV64) and Sv32x4 (RV32) are expected but not assumed.
"""

# ruff: noqa: B023  (closures run immediately inside the loop that defines them)
from __future__ import annotations

from aigen import X
from h_hlsv import both, hl, init, tf
from hlib import HYP, ISSUE, MUT, hfence_gvma, hfence_vvma, hlsv
from hmem import (
    G_OF,
    GEO,
    GPA_BASE,
    HFENCE_GVMA,
    HFENCE_VVMA,
    INSN_GPF,
    LEAF,
    LOAD_AF,
    LOAD_GPF,
    LOAD_MIS,
    LOAD_PF,
    MODE,
    PT,
    STORE_AF,
    STORE_GPF,
    STORE_MIS,
    STORE_PF,
    ULEAF,
    VA_BASE,
    VS_OF,
    XP,
    A,
    D,
    G,
    MemTest,
    R,
    U,
    V,
    W,
    atp_off,
    hgatp_on,
    memwin,
    memwin_tsbi,
    new,
    pseudo_required,
    s_mxr,
    sig,
    spvp,
    tval2_consistent,
    vs_mxr,
    vsatp_on,
)

MUTANTS = {
    "x4_ignored": "G-stage drops the two extra GPA bits (root table indexed like a 4 KiB table)",
    "gpa_upper_ignored": "GPA bits above the x4 width are ignored instead of raising a guest-page fault",
    "gpf_as_pf": "G-stage faults are reported as page faults (13/15/12)",
    "htval_va": "htval holds the guest virtual address >> 2 instead of the GPA >> 2",
    "gstage_s_priv": "G-stage checks use the VS privilege (U=0 G-stage pages accessible from VS)",
    "implicit_as_original": "implicit VS page-table reads are checked for the original access type at G-stage",
    "pseudo_zero": "htinst is 0 for an implicit-access guest-page fault with a nonzero htval",
    "vs_mxr_both": "vsstatus.MXR overrides G-stage execute-only for VS-mode loads",
    "gpf_delegable": "guest-page faults can be delegated to VS-mode through hedeleg",
    "vsatp_v1_unsupported_written": "a VS-mode write of satp with an unsupported MODE changes vsatp",
    "vs_satp_is_hs_satp": "a VS-mode write of satp lands in HS-mode's satp",
    "vstage_bypassed": "VS-mode loads skip VS-stage translation",
    "gstage_bypassed_v1": "VS-mode loads skip G-stage translation",
    "henvcfg_adue_gstage": "henvcfg.ADUE (not menvcfg.ADUE) controls G-stage A/D updates",
    "pbmte_ignored": "VS-stage PBMT bits are accepted with henvcfg.PBMTE=0",
    "ppn_low_kept": "hgatp.PPN[1:0] read back as written in an x4 mode",
    "vmid_msb_first": "hgatp.VMID implements the most-significant bits first",
    "gpa_g_bit_global": "a G-stage PTE with G=1 faults (G not ignored)",
}

ISS = ISSUE
PSEUDO_R = X(0x2000, 0x3000)
PSEUDO_W = X(0x2020, 0x3020)
HGATP = 0x680


def g_pt(t: MemTest, xlen: int, scheme: str | None = None, name: str | None = None) -> PT:
    s = scheme or G_OF[xlen]
    g = PT(t, name or f"g{xlen}{s}", s, xlen)
    g.identity(ULEAF)
    return g


def gfail(c: int) -> int:
    """The cause a correct hart raises for G-stage failure c (or the mutant's)."""
    if MUT == "gpf_as_pf":
        return {LOAD_GPF: LOAD_PF, STORE_GPF: STORE_PF, INSN_GPF: 12}[c]
    return c


def probe(t: MemTest, pt: PT) -> None:
    """x1 = 1 if hgatp accepts pt's MODE (written with pt's root); hgatp is left Bare."""
    pt.atp("x6")
    t.emit(f"csrw {hex(HGATP)}, x6  // probe hgatp MODE")
    t.emit(f"csrr x1, {hex(HGATP)}")
    t.emit(f"csrw {hex(HGATP)}, x0")
    t.emit(HFENCE_GVMA)
    if pt.xlen == 64:
        t.emit("srli x1, x1, 60")
        t.emit(f"addi x1, x1, -{MODE[pt.scheme]}")
    else:
        t.emit("srli x1, x1, 31")
        t.emit("addi x1, x1, -1")
    t.emit("seqz x1, x1")


def lw_sig(t: MemTest, name: str) -> int:
    return sig(t.page_id(name)) & 0xFFFFFFFF


def guarded(t: MemTest, pt: PT, body, note: str) -> None:  # noqa: ANN001
    """Run body only if pt's G-stage MODE is supported (probe)."""
    t.comment(f"probe: {note}")
    probe(t, pt)
    t.either("x1", body, lambda: None)


def vs_run(t: MemTest, mode: str, lines: list[str], expect, desc: str, extras=None, epc: bool = True) -> str:  # noqa: ANN001
    return memwin(t, mode, lines, expect, desc, extras, epc=epc)


def gpf_extras(c: int, tval, gpa: int | None, e: int | None = None, gva: int = 1) -> dict:  # noqa: ANN001
    ex = {"tval": tval, "gva": gva}
    if gpa is not None:
        ex["tval2"] = [0, (gpa if MUT != "htval_va" else tval) >> 2] if isinstance(tval, int) else [0, gpa >> 2]
    if e is not None:
        ex["tinst"] = [0, tf(e)]
    return {c: ex}


LW = 0x00032383  # lw x7, 0(x6)
SW = 0x00832023  # sw x8, 0(x6)


# ---------------------------------------------------------------- hgatp CSR rules
def gen_csr() -> list[MemTest]:
    tests = []

    t = new("hgatp_sz_acc_op")
    t.describe(
        source=HYP,
        rule_text="The hgatp register is an HSXLEN-bit read/write register, formatted as shown in <<rv32hgatp>> "
        "for HSXLEN=32 and <<rv64hgatp>> for HSXLEN=64, which controls G-stage address translation and "
        "protection, the second stage of two-stage translation for guest virtual addresses.",
        context="RV64 fields: MODE 63:60, VMID 57:44, PPN 43:0; RV32: MODE 31, VMID 28:22, PPN 21:0. MODE is "
        "probed (Sv39x4 / Sv32x4); VMID may be 0 bits wide. The value written selects a 16 KiB-aligned root.",
        plan="1. Write hgatp = 0 and read 0.\n"
        "2. If the x4 mode is supported: write MODE | VMID=1 | PPN(root) and read back MODE and PPN exactly and "
        "VMID either 1 or 0 (VMIDLEN 0).\n"
        "3. The written hgatp translates: HLV.W through GPA_BASE reads the mapped page.",
    )
    init(t)
    t.page("A")

    def body(xlen: int) -> None:
        lab = t.label("zero")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrw {hex(HGATP)}, x0")
        t.emit(f"csrr x7, {hex(HGATP)}")
        t.check("x7", 0, lab, "hgatp reads 0 after writing 0")
        g = g_pt(t, xlen)
        g.leaf(GPA_BASE[xlen], t.page("A"), ULEAF)

        def sup() -> None:
            g.atp("x6", 1)
            lab2 = t.label("rt")
            t.emit(f"{lab2}:", 0)
            t.emit(f"csrw {hex(HGATP)}, x6")
            t.emit(f"csrr x7, {hex(HGATP)}")
            t.emit(HFENCE_GVMA)
            vm = (1 << 44) if xlen == 64 else (1 << 22)
            t.load("x8", ~vm & ((1 << xlen) - 1), "all but VMID bit 0")
            t.emit("and x9, x7, x8")
            t.emit("and x8, x6, x8")
            t.emit("xor x9, x9, x8")
            t.check("x9", 0, lab2, "hgatp MODE and PPN read back as written")
            t.load("x8", vm, "VMID bit 0")
            t.emit("and x9, x7, x8")
            t.check("x9", [vm, 0], lab2, "hgatp VMID reads 1, or 0 when VMIDLEN=0")
            hl(t, "hlv.w", GPA_BASE[xlen], "through the written hgatp", "ok", lw_sig(t, "A"))
            atp_off(t)

        probe(t, g)
        t.either("x1", sup, lambda: None)

    both(t, body)
    tests.append(t)

    t = new("hgatp_mode_Sv")
    t.describe(
        source=HYP,
        rule_text="When HSXLEN=32, the only other valid setting for MODE is Sv32x4, which is a modification of the "
        "usual Sv32 paged virtual-memory scheme, extended to support 34-bit guest physical addresses. When "
        "HSXLEN=64, modes Sv39x4, Sv48x4, and Sv57x4 are defined as modifications of the Sv39, Sv48, and Sv57 "
        "paged virtual-memory schemes.",
        context="Which modes are supported is not specified here; each mode is written and read back, and every "
        "mode that reads back as written must translate with its own geometry (root index 11 bits for "
        "Sv39x4/48x4/57x4, 12 bits for Sv32x4). The test GPA of each mode uses a root index that the identity "
        "map of the image does not use.",
        plan="1. RV64: write MODE = 8, 9, 10; each read-back MODE is 0, 8, 9 or 10.\n"
        "2. Each mode that reads back as written: HLV.W of a GPA with nonzero bits in every VPN field reads the "
        "page mapped there through a full-depth table.\n"
        "3. RV32: write MODE=1; it reads back 0 or 1; if 1, HLV.W of a 34-bit GPA (through VS-stage Sv32) reads "
        "its page.",
    )
    init(t)
    with t.rv64_only():
        for k, sch in enumerate(("sv39x4", "sv48x4", "sv57x4")):
            pg = t.page(f"m{sch}")
            shift0 = GEO[sch][0][0]
            gpa = (
                (5 << shift0)
                | (0x0AA << 21)
                | (0x0CD << 12)
                | ((0x133 << 30) if shift0 > 30 else 0)
                | ((0x0F1 << 39) if shift0 > 39 else 0)
            )
            g = PT(t, f"gm{sch}", sch, 64)
            g.identity(ULEAF)
            g.leaf(gpa, pg, ULEAF)
            lab = t.label("mode")
            g.atp("x6")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {hex(HGATP)}, x6")
            t.emit(f"csrr x7, {hex(HGATP)}")
            t.emit("srli x7, x7, 60")
            t.emit("li x8, 11")
            t.emit("sltu x8, x7, x8")
            t.emit("li x9, 8")
            t.emit("sltu x9, x7, x9")
            t.emit("xori x9, x9, 1")
            t.emit("and x8, x8, x9  // 8 <= MODE <= 10")
            t.emit("seqz x9, x7")
            t.emit("or x8, x8, x9")
            t.check_bool("x8", lab, f"hgatp MODE after writing {MODE[sch]} ({sch}) is 0, 8, 9 or 10 (WARL)")
            t.emit(f"addi x1, x7, -{MODE[sch]}")
            t.emit("seqz x1, x1")
            t.emit(HFENCE_GVMA)

            def tr(gpa: int = gpa, sch: str = sch) -> None:
                hl(t, "hlv.w", gpa, f"{sch} full-depth mapping", "ok", lw_sig(t, f"m{sch}"))

            t.either("x1", tr, lambda: None)
            atp_off(t)
    with t.rv32_only():
        _sv32x4_hi(t, "hgatp_mode_Sv")
    tests.append(t)

    t = new("hgatp_mode_warl")
    t.describe(
        source=HYP,
        rule_text="A write to hgatp with an unsupported MODE value is not ignored as it is for satp. Instead, "
        "the fields of hgatp are WARL in the normal way, when so indicated.",
        context="RV64 MODE values 1-7 and 11-15 are reserved. A WARL field may map an illegal write to any legal "
        "value, so the written MODE may become any defined mode; but the write is not ignored, so whenever "
        "MODE reads back as a paged mode the PPN field holds the newly written PPN. RV32 has no reserved "
        "MODE value (1 bit), so the RV32 file checks only that writes are not ignored for a supported mode.",
        plan="1. Start from hgatp = x4 mode with root R1 (when supported).\n"
        "2. RV64: for MODE = 1, 7, 11, 15, write MODE | PPN(R2): MODE reads 0, 8, 9 or 10, and if it is not "
        "0, PPN reads R2's PPN (not R1's).\n"
        "3. hgatp = 0 at the end.",
    )
    init(t)
    with t.rv64_only():
        g1 = PT(t, "gw1", "sv39x4", 64)
        g2 = PT(t, "gw2", "sv39x4", 64)
        for m in (1, 7, 11, 15):
            g1.atp("x6")
            t.emit(f"csrw {hex(HGATP)}, x6  // hgatp = Sv39x4, root R1")
            t.la("x8", g2.root)
            t.emit("srli x8, x8, 12  // PPN(R2)")
            t.emit(f"li x7, {hex(m << 60)}")
            t.emit("or x6, x8, x7")
            lab = t.label("warl")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {hex(HGATP)}, x6  // reserved MODE {m}")
            t.emit(f"csrr x7, {hex(HGATP)}")
            t.emit("srli x9, x7, 60")
            t.emit("li x5, 11")
            t.emit("sltu x5, x9, x5")
            t.emit("li x4, 8")
            t.emit("sltu x4, x9, x4")
            t.emit("xori x4, x4, 1")
            t.emit("and x5, x5, x4  // 8 <= MODE <= 10")
            t.emit("seqz x4, x9")
            t.emit("or x5, x5, x4")
            t.check_bool("x5", lab, f"hgatp MODE after writing reserved {m} is 0, 8, 9 or 10")
            t.emit("slli x7, x7, 20")
            t.emit("srli x7, x7, 20  // PPN")
            t.emit("xor x7, x7, x8")
            t.emit("seqz x7, x7")
            t.emit("seqz x9, x9")
            t.emit("or x7, x7, x9")
            t.check_bool(
                "x7",
                lab,
                f"after writing reserved MODE {m}, a paged MODE comes with the new PPN (the write is not ignored)",
            )
        t.emit(f"csrw {hex(HGATP)}, x0")
        t.emit(HFENCE_GVMA)
    tests.append(t)

    for rule in ("hgatp_ppn_op", "hgatp_ppn_acc"):
        t = new(rule)
        t.describe(
            source=HYP,
            rule_text="In these modes, the lowest two bits of the physical page number (PPN) in hgatp always read "
            "as zeros."
            if rule == "hgatp_ppn_op"
            else "An implementation that supports only the defined paged "
            "virtual-memory schemes and/or Bare may make PPN[1:0] read-only zero.",
            context="The root of an x4 mode is 16 KiB aligned; PPN[1:0] select nothing. The root used here is "
            "16 KiB aligned and maps GPA_BASE to page A.",
            plan="1. In the x4 mode (if supported), write PPN = root | 0b11, | 0b01, | 0b10: PPN[1:0] read 0.\n"
            "2. With PPN[1:0] written as 0b11, HLV.W of GPA_BASE still reads page A (the root is not offset)."
            if rule == "hgatp_ppn_op"
            else "1. In the x4 mode (if supported), write PPN = root | 0b11: PPN[1:0] read 0 (read-only zero is "
            "consistent with the PPN rule), and translation uses the aligned root: HLV.W of GPA_BASE reads A.",
        )
        init(t)
        t.page("A")

        def body(xlen: int, t: MemTest = t, rule: str = rule) -> None:
            g = g_pt(t, xlen, name=f"g{xlen}")
            g.leaf(GPA_BASE[xlen], t.page("A"), ULEAF)

            def sup() -> None:
                for lo in (3, 1, 2) if rule == "hgatp_ppn_op" else (3,):
                    g.atp("x6")
                    t.emit(f"ori x6, x6, {lo}")
                    lab = t.label("ppn")
                    t.emit(f"{lab}:", 0)
                    t.emit(f"csrw {hex(HGATP)}, x6")
                    t.emit(f"csrr x7, {hex(HGATP)}")
                    t.emit(HFENCE_GVMA)
                    t.emit("andi x7, x7, 3")
                    t.check(
                        "x7", lo if MUT == "ppn_low_kept" else 0, lab, f"hgatp PPN[1:0] reads 0 after writing {lo:#04b}"
                    )
                hl(t, "hlv.w", GPA_BASE[xlen], "PPN[1:0] written as 0b11", "ok", lw_sig(t, "A"))
                atp_off(t)

            probe(t, g)
            t.either("x1", sup, lambda: None)

        both(t, body)
        tests.append(t)

    for rule in ("hgatp_vmid", "hgatp_vmid_lsbs"):
        t = new(rule)
        t.describe(
            source=HYP,
            rule_text="The number of VMID bits is UNSPECIFIED and may be zero."
            if rule == "hgatp_vmid"
            else "The least-significant bits of VMID are implemented first: that is, if VMIDLEN > 0, "
            "VMID[VMIDLEN-1:0] is writable. The maximal value of VMIDLEN, termed VMIDMAX, is 7 for Sv32x4 or 14 for "
            "Sv39x4, Sv48x4, and Sv57x4.",
            context="VMID is written with a paged MODE (Bare requires the other fields to be zero). Writing all "
            "ones and reading back gives the implemented mask.",
            plan="1. In the x4 mode (if supported), write VMID = all ones: the value read, m, is 2^k - 1 with "
            "0 <= k <= VMIDMAX.\n"
            + (
                "2. Translation works with any VMID: HLV.W through GPA_BASE reads A with VMID = m."
                if rule == "hgatp_vmid"
                else "2. Write VMID = random values v: each reads back v & m (the low bits are the implemented ones)."
            ),
        )
        init(t)
        t.page("A")

        def body(xlen: int, t: MemTest = t, rule: str = rule) -> None:
            g = g_pt(t, xlen, name=f"g{xlen}")
            g.leaf(GPA_BASE[xlen], t.page("A"), ULEAF)
            sh, vmax = (44, 14) if xlen == 64 else (22, 7)

            def sup() -> None:
                g.atp("x6")
                t.load("x7", ((1 << vmax) - 1) << sh, "all-ones VMID")
                t.emit("or x6, x6, x7")
                lab = t.label("vmid")
                t.emit(f"{lab}:", 0)
                t.emit(f"csrw {hex(HGATP)}, x6")
                t.emit(f"csrr x1, {hex(HGATP)}")
                t.emit(f"srli x1, x1, {sh}")
                t.emit(
                    f"andi x1, x1, {(1 << vmax) - 1 if vmax < 12 else 0}"
                    if vmax < 12
                    else f"slli x1, x1, {xlen - vmax}"
                )
                if vmax >= 12:
                    t.emit(f"srli x1, x1, {xlen - vmax}  // x1 = m")
                t.emit("addi x7, x1, 1")
                t.emit("and x7, x7, x1")
                t.emit("seqz x7, x7  // m + 1 is a power of two")
                if MUT == "vmid_msb_first":
                    t.emit("xori x7, x7, 1")
                t.check_bool("x7", lab, "hgatp.VMID all-ones reads back 2^k - 1 (low bits implemented)")
                if rule == "hgatp_vmid":
                    t.emit(HFENCE_GVMA)
                    hl(t, "hlv.w", GPA_BASE[xlen], "VMID = implemented mask", "ok", lw_sig(t, "A"))
                else:
                    for _ in range(3):
                        v = t.rand(vmax)
                        g.atp("x6")
                        t.load("x7", v << sh, f"VMID = {hex(v)}")
                        t.emit("or x6, x6, x7")
                        lab2 = t.label("vmidv")
                        t.emit(f"{lab2}:", 0)
                        t.emit(f"csrw {hex(HGATP)}, x6")
                        t.emit(f"csrr x8, {hex(HGATP)}")
                        t.emit(f"srli x8, x8, {sh}")
                        t.emit(f"slli x8, x8, {xlen - vmax}")
                        t.emit(f"srli x8, x8, {xlen - vmax}")
                        t.load("x9", v, "v")
                        t.emit("and x9, x9, x1")
                        t.emit("xor x8, x8, x9")
                        t.check("x8", 0, lab2, f"hgatp.VMID written {hex(v)} reads {hex(v)} & mask")
                atp_off(t)

            probe(t, g)
            t.either("x1", sup, lambda: None)

        both(t, body)
        tests.append(t)

    for rule in ("hgatp_mode_bare", "hgatp_mode_bare_trans"):
        t = new(rule)
        t.describe(
            source=HYP,
            rule_text="<<hgatp-mode>> shows the encodings of the MODE field when HSXLEN=32 and HSXLEN=64. When "
            "MODE=Bare, guest physical addresses are equal to supervisor physical addresses, and there is no "
            "further memory protection for a guest virtual machine beyond the physical memory protection scheme "
            "described in <<pmp>>. In this case, software must write zero to the remaining fields in hgatp."
            if rule == "hgatp_mode_bare"
            else "When the address translation scheme selected by the MODE field of hgatp is Bare, guest physical "
            "addresses are equal to supervisor physical addresses without modification, and no memory protection "
            "applies in the trivial translation of guest physical addresses to supervisor physical addresses.",
            context="With vsatp Bare too, a guest address equals the physical address. Data page A is read, "
            "written and read for execute (HLVX) through HLV/HSV and by VS-mode and VU-mode code; with Bare "
            "there are no G-stage permissions to deny any of it.",
            plan="1. hgatp = 0 reads 0.\n"
            "2. HLV.W, HLVX.WU (SPVP 0 and 1) and HSV.W at page A's physical address succeed and access page A.\n"
            "3. VS-mode and VU-mode lw/sw at page A's physical address succeed and access page A.",
        )
        init(t)
        pa = t.page("A", {16: (4, 0)})
        lab = t.label("bare")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrr x7, {hex(HGATP)}")
        t.check("x7", 0, lab, "hgatp reads 0 (Bare)")
        sa = lw_sig(t, "A")
        for sp in (0, 1):
            spvp(t, bool(sp))
            hl(t, "hlv.w", pa, f"SPVP={sp}", "ok", sa)
            hl(t, "hlvx.wu", pa, f"SPVP={sp}", "ok", sa)
            t.load("x8", 0x600D0000 + sp, "value")
            lab = hl(t, "hsv.w", f"{pa}+16", f"SPVP={sp}", "ok")
            t.la("x6", f"{pa}+16")
            t.emit("lw x7, 0(x6)")
            t.check("x7", 0x600D0000 + sp, lab, "HSV.W with hgatp Bare writes physical page A")
        spvp(t, False)
        for mode in ("VS", "VU"):
            t.la("x6", pa)
            lab = vs_run(t, mode, ["lw x7, 0(x6)"], "ok", "lw at page A's physical address")
            t.check("x7", sa, lab, f"{mode}-mode lw with hgatp and vsatp Bare reads page A")
            t.la("x6", f"{pa}+16")
            t.load("x8", 0x5EED0000, "value")
            lab = vs_run(t, mode, ["sw x8, 0(x6)"], "ok", "sw at page A's physical address")
            t.emit("lw x7, 0(x6)")
            t.check("x7", 0x5EED0000, lab, f"{mode}-mode sw with hgatp and vsatp Bare writes page A")
        tests.append(t)
    return tests


def _sv32x4_hi(t: MemTest, tag: str, k_list: tuple = (0, 1, 2, 3), top: bool = True, unmapped0: bool = False) -> None:
    """RV32: VS-stage Sv32 maps VA_BASE+k*4K to GPA (k<<32) | 0x4000_0000 + k*4K (34-bit GPAs, root index bits
    33:32 = k), and G-stage Sv32x4 maps each to page P<k>; plus the top root entry (GPA 0x3_FFC0_0000) -> page
    Ptop. HLV.W (SPVP=1) reads each page. unmapped0: GPA for k=0 is left unmapped and must fault."""
    g = PT(t, "g32x4", "sv32x4", 32)
    g.identity(ULEAF)
    v = PT(t, "vs32x4", "sv32", 32)
    gpas = {}
    for k in k_list:
        gpa = (k << 32) | 0x4000_0000 | (k << 12)
        gpas[k] = gpa
        v.leaf(VA_BASE[32] + k * 0x1000, gpa, LEAF)
        if not (unmapped0 and k == 0):
            g.leaf(gpa, t.page(f"P{k}"), ULEAF)
    if top:
        gtop = 0x3_FFC0_0000 | 0x5000
        v.leaf(VA_BASE[32] + 0x8000, gtop, LEAF)
        g.leaf(gtop, t.page("Ptop"), ULEAF)

    def sup() -> None:
        hgatp_on(t, g)
        vsatp_on(t, v)
        spvp(t, True)
        for k in k_list:
            if unmapped0 and k == 0:
                hl(t, "hlv.w", VA_BASE[32], "GPA bits 33:32 = 0, unmapped", gfail(LOAD_GPF), gpa=gpas[0])
                continue
            exp = "ok"
            val = lw_sig(t, f"P{k}")
            if MUT == "x4_ignored" and k:
                val = lw_sig(t, "P0") if not unmapped0 else None
                exp = "ok" if not unmapped0 else gfail(LOAD_GPF)
            hl(t, "hlv.w", VA_BASE[32] + k * 0x1000, f"34-bit GPA {hex(gpas[k])}", exp, val, gpa=gpas[k])
        if top:
            hl(t, "hlv.w", VA_BASE[32] + 0x8000, "GPA 0x3_FFC0_5000 (root entry 4095)", "ok", lw_sig(t, "Ptop"))
        spvp(t, False)
        atp_off(t)

    probe(t, g)
    t.either("x1", sup, lambda: None)


# ---------------------------------------------------------------- x4 geometry
def gen_x4() -> list[MemTest]:
    tests = []
    texts = {
        "hgatp_mode_x4": "When hgatp[mode] specifies a translation scheme of Sv32x4, Sv39x4, Sv48x4, or Sv57x4, "
        "G-stage address translation is a variation on the usual page-based virtual address translation scheme "
        "of Sv32, Sv39, Sv48, or Sv57, respectively. In each case, the size of the incoming address is widened by "
        "2 bits (to 34, 41, 50, or 59 bits). To accommodate the two extra bits, the root page table (only) is "
        "expanded by a factor of 4 to be 16 KiB instead of the usual 4 KiB. Matching its larger size, the root "
        "page table also must be aligned to a 16 KiB boundary instead of the usual 4 KiB page boundary. Except "
        "as noted, all other aspects of Sv32, Sv39, Sv48, or Sv57 are adopted unchanged for G-stage translation. "
        "Non-root page tables and all page table entries (PTEs) have the same formats as documented in <<sv32>>, "
        "<<sv39>>, <<sv48>>, and <<sv57>>.",
        "hgatp_root_pt_sz_align": "As explained in <<guest-addr-translation>>, for the paged virtual-memory "
        "schemes (Sv32x4, Sv39x4, Sv48x4, and Sv57x4), the root page table is 16 KiB and must be aligned to a "
        "16-KiB boundary.",
        "hgatp_mode_sv39x4": "For Sv39x4, an incoming guest physical address is partitioned as shown in "
        "<<sv39x4va>>. This partitioning is identical to that for an Sv39 virtual address as depicted in "
        "<<sv39va>>, except with 2 more bits at the high end in VPN[2]. Address bits 63:41 must all be zeros, or "
        "else a guest-page-fault exception occurs.",
        "hgatp_mode_sv32x4": "For Sv32x4, an incoming guest physical address is partitioned into a virtual page "
        "number (VPN) and page offset as shown in <<sv32x4va>>. This partitioning is identical to that for an "
        "Sv32 virtual address as depicted in <<sv32va>>, except with two more bits at the high end in VPN[1].",
    }
    for rule, text in texts.items():
        t = new(rule)
        plan = {
            "hgatp_mode_x4": "1. Four GPAs that differ only in the two extra bits (RV64 bits 40:39, RV32 bits "
            "33:32; RV32 reaches them through VS-stage Sv32 PTEs with 22-bit PPNs) map to four different pages; "
            "HLV.W reads each page.\n"
            "2. Only the GPA with extra bits 0b11 is then mapped: it still reads its page, and the GPA with extra "
            "bits 0b00 raises a load guest-page fault (a design that drops the extra bits aliases them).",
            "hgatp_root_pt_sz_align": "1. GPAs whose root index is 512 (1024 on RV32), 1024, 1536 and the last "
            "entry 2047 (4095) map through entries in the upper 12 KiB of the 16 KiB root; HLV.W reads each "
            "mapped page.",
            "hgatp_mode_sv39x4": "1. RV64: a GPA with bit 40 set (the top of the 41-bit space) maps and reads.\n"
            "2. GPAs with bit 41, 42, 50, 62 or 63 set, and all ones above bit 40, raise load guest-page faults "
            "for HLV.W and store guest-page faults for HSV.W, with stval 0 or the address, GVA=1 (with a nonzero stval) and htinst 0 or "
            "the transformed instruction (htval is not checked: such a GPA may not fit htval's WARL range).\n"
            "3. The same GPA from VS-mode code (vsatp Bare) raises a load guest-page fault.",
            "hgatp_mode_sv32x4": "1. RV32: GPAs in all four 4 GiB quarters of the 34-bit space, and one in the "
            "same 4 MiB megapage as another (VPN[0] differs), each read their own page through VS-stage Sv32 and "
            "G-stage Sv32x4.",
        }[rule]
        t.describe(
            source=HYP,
            rule_text=text,
            context="hgatp mode support is probed. RV64 uses vsatp Bare (GPA = guest VA); RV32 needs VS-stage "
            "Sv32 to form GPAs above 4 GiB. HLV/HSV run in HS-mode.",
            plan=plan,
        )
        init(t)
        if rule in ("hgatp_mode_x4", "hgatp_root_pt_sz_align"):

            def body64(t: MemTest = t, rule: str = rule) -> None:
                g = g_pt(t, 64, name="g64")
                if rule == "hgatp_mode_x4":
                    gp = {k: (k << 39) | 0x4000_0000 | (k << 12) for k in range(4)}
                else:
                    gp = {k: (k << 30) | 0x5000 for k in (512, 1024, 1536, 2047)}
                for k, a in gp.items():
                    g.leaf(a, t.page(f"P{k}"), ULEAF)

                def sup() -> None:
                    hgatp_on(t, g)
                    for k, a in gp.items():
                        val = lw_sig(t, f"P{k}")
                        exp = "ok"
                        if MUT == "x4_ignored" and (a >> 39) & 3:
                            low = a & ~(3 << 39)
                            if low in gp.values():
                                val = lw_sig(t, f"P{next(kk for kk, aa in gp.items() if aa == low)}")
                            else:
                                exp, val = gfail(LOAD_GPF), None
                        hl(t, "hlv.w", a, f"GPA {hex(a)}", exp, val, gpa=a)
                    if rule == "hgatp_mode_x4":
                        g.raw(gp[0], 0, note="unmap the 0b00 GPA")
                        t.emit(HFENCE_GVMA)
                        hl(
                            t,
                            "hlv.w",
                            gp[3],
                            "extra bits 0b11, 0b00 unmapped",
                            gfail(LOAD_GPF) if MUT == "x4_ignored" else "ok",
                            None if MUT == "x4_ignored" else lw_sig(t, "P3"),
                            gpa=gp[3],
                        )
                        hl(t, "hlv.w", gp[0], "extra bits 0b00, unmapped", gfail(LOAD_GPF), gpa=gp[0])
                    atp_off(t)

                probe(t, g)
                t.either("x1", sup, lambda: None)

            with t.rv64_only():
                body64()
            with t.rv32_only():
                if rule == "hgatp_mode_x4":
                    _sv32x4_hi(t, rule, top=False)
                    _sv32x4_hi_unmap(t)
                else:
                    _sv32x4_root(t)
        elif rule == "hgatp_mode_sv39x4":
            with t.rv64_only():
                g = g_pt(t, 64, name="g64")
                top = (1 << 40) | 0x4000_0000
                g.leaf(top, t.page("T"), ULEAF)

                def sup() -> None:
                    hgatp_on(t, g)
                    hl(t, "hlv.w", top, "GPA bit 40 set", "ok", lw_sig(t, "T"), gpa=top)
                    for b in (41, 42, 50, 62, 63, None):
                        a = (top | ((1 << 64) - (1 << 41))) if b is None else (top | (1 << b))
                        exp = "ok" if MUT == "gpa_upper_ignored" else gfail(LOAD_GPF)
                        hl(t, "hlv.w", a, f"GPA {hex(a)}", exp, lw_sig(t, "T") if exp == "ok" else None)
                        t.emit("li x8, 0")
                        hl(
                            t,
                            "hsv.w",
                            a + 4,
                            f"GPA {hex(a + 4)}",
                            "ok" if MUT == "gpa_upper_ignored" else gfail(STORE_GPF),
                        )
                    a = top | (1 << 45)
                    t.emit(f"li x6, {hex(a)}")
                    ex = {} if MUT == "gpa_upper_ignored" else gpf_extras(gfail(LOAD_GPF), a, None, None)
                    vs_run(
                        t,
                        "VS",
                        ["lw x7, 0(x6)"],
                        "ok" if MUT == "gpa_upper_ignored" else gfail(LOAD_GPF),
                        f"VS-mode lw of GPA {hex(a)}",
                        ex,
                    )
                    atp_off(t)

                probe(t, g)
                t.either("x1", sup, lambda: None)
        else:
            with t.rv32_only():
                _sv32x4_hi(t, rule, k_list=(0, 1, 2, 3), top=True)
                # VPN[0] differs within one megapage
                g = PT(t, "g32b", "sv32x4", 32)
                g.identity(ULEAF)
                v = PT(t, "vs32b", "sv32", 32)
                base = (2 << 32) | 0x4040_0000
                for j in (1, 0x3FF):
                    v.leaf(VA_BASE[32] + 0x10000 + j * 0x1000 % 0x40000, base + j * 0x1000, LEAF)
                    g.leaf(base + j * 0x1000, t.page(f"Q{j}"), ULEAF)

                def sup() -> None:
                    hgatp_on(t, g)
                    vsatp_on(t, v)
                    spvp(t, True)
                    for j in (1, 0x3FF):
                        hl(
                            t,
                            "hlv.w",
                            VA_BASE[32] + 0x10000 + j * 0x1000 % 0x40000,
                            f"GPA VPN[0]={hex(j)}",
                            "ok",
                            lw_sig(t, f"Q{j}"),
                        )
                    spvp(t, False)
                    atp_off(t)

                probe(t, g)
                t.either("x1", sup, lambda: None)
        tests.append(t)

    # Sv48x4 / Sv57x4 upper bits
    for rule, sch, width in (("hgatp_mode_sv48x4", "sv48x4", 50), ("hgatp_mode_Sv57x4", "sv57x4", 59)):
        t = new(rule, rv64=True)
        t.describe(
            source=HYP,
            rule_text=f"For {sch[:2].upper()}{sch[2:]}, an incoming guest physical address is partitioned as "
            f"shown in <<{sch}va>>. This partitioning is identical to that for an {sch[:4].capitalize()} virtual "
            f"address, except with 2 more bits at the high end in VPN[{GEO[sch].__len__() - 1}]. Address bits "
            f"63:{width} must all be zeros, or else a guest-page-fault exception occurs.",
            context=f"RV64 only; runs only if hgatp accepts {sch} (probed). vsatp Bare, HLV in HS-mode.",
            plan=f"1. GPAs that differ only in bits {width - 1}:{width - 2} map to different pages and read them.\n"
            f"2. GPAs with bit {width}, {width + 1} or 63 set raise load guest-page faults (HLV.W) and store "
            "guest-page faults (HSV.W).",
        )
        init(t)
        g = PT(t, f"g{sch}", sch, 64)
        g.identity(ULEAF)
        gp = {k: (k << (width - 2)) | (1 << (width - 4)) | 0x4000_0000 | (k << 12) for k in range(4)}
        for k, a in gp.items():
            g.leaf(a, t.page(f"P{k}"), ULEAF)

        def sup(t: MemTest = t, g: PT = g, gp: dict = gp, width: int = width) -> None:
            hgatp_on(t, g)
            for k, a in gp.items():
                hl(t, "hlv.w", a, f"GPA {hex(a)}", "ok", lw_sig(t, f"P{k}"), gpa=a)
            for b in (width, width + 1, 63):
                a = gp[1] | (1 << b)
                hl(t, "hlv.w", a, f"GPA {hex(a)}", gfail(LOAD_GPF))
                t.emit("li x8, 0")
                hl(t, "hsv.w", a, f"GPA {hex(a)}", gfail(STORE_GPF))
            atp_off(t)

        probe(t, g)
        t.either("x1", sup, lambda: None)
        tests.append(t)
    return tests


def _sv32x4_hi_unmap(t: MemTest) -> None:
    t.comment("only the 0b11 quarter mapped; the 0b00 GPA must fault")
    g = PT(t, "g32u", "sv32x4", 32)
    g.identity(ULEAF)
    v = PT(t, "vs32u", "sv32", 32)
    g0, g3 = 0x4000_0000 | 0x7000, (3 << 32) | 0x4000_0000 | 0x7000
    v.leaf(VA_BASE[32] + 0x20000, g0, LEAF)
    v.leaf(VA_BASE[32] + 0x21000, g3, LEAF)
    g.leaf(g3, t.page("P3"), ULEAF)

    def sup() -> None:
        hgatp_on(t, g)
        vsatp_on(t, v)
        spvp(t, True)
        x4 = MUT == "x4_ignored"
        hl(
            t,
            "hlv.w",
            VA_BASE[32] + 0x21000,
            "GPA bits 33:32 = 0b11",
            gfail(LOAD_GPF) if x4 else "ok",
            None if x4 else lw_sig(t, "P3"),
            gpa=g3,
        )
        hl(t, "hlv.w", VA_BASE[32] + 0x20000, "GPA bits 33:32 = 0b00, unmapped", gfail(LOAD_GPF), gpa=g0)
        spvp(t, False)
        atp_off(t)

    probe(t, g)
    t.either("x1", sup, lambda: None)


def _sv32x4_root(t: MemTest) -> None:
    g = PT(t, "g32r", "sv32x4", 32)
    g.identity(ULEAF)
    v = PT(t, "vs32r", "sv32", 32)
    gp = {k: (k << 22) | 0x6000 for k in (1024, 2048, 3072, 4095)}
    for i, (k, a) in enumerate(gp.items()):
        v.leaf(VA_BASE[32] + i * 0x1000, a, LEAF)
        g.leaf(a, t.page(f"P{k}"), ULEAF)

    def sup() -> None:
        hgatp_on(t, g)
        vsatp_on(t, v)
        spvp(t, True)
        for i, (k, a) in enumerate(gp.items()):
            hl(t, "hlv.w", VA_BASE[32] + i * 0x1000, f"GPA {hex(a)} (root entry {k})", "ok", lw_sig(t, f"P{k}"))
        spvp(t, False)
        atp_off(t)

    probe(t, g)
    t.either("x1", sup, lambda: None)


# ---------------------------------------------------------------- two-stage semantics
def two(
    t: MemTest,
    xlen: int,
    maps: list[tuple],
    vs_identity: int | None = None,
    vs_gpa: int | None = None,
    gtab_perms: int = ULEAF,
) -> tuple[PT, PT]:
    """G identity + VS table. maps: (k, vs_perms, gpa, page or None, g_perms). vs_identity: perms of a VS-stage
    identity map of the image (for guest code). vs_gpa: place the VS tables at GPAs (mapped with gtab_perms)."""
    g = g_pt(t, xlen, name=f"g{xlen}")
    v = PT(t, f"vs{xlen}", VS_OF[xlen], xlen, gpa_base=vs_gpa)
    if vs_identity is not None:
        v.identity(vs_identity)
    for k, vp, gpa, page, gp in maps:
        v.leaf(VA_BASE[xlen] + k * 0x1000, gpa, vp)
        if page and gp:
            g.leaf(gpa, t.page(page), gp)
    if vs_gpa is not None:
        for lab, a in v.gpas.items():
            g.leaf(a, lab, gtab_perms)
    hgatp_on(t, g)
    vsatp_on(t, v)
    return g, v


def gen_twostage() -> list[MemTest]:
    tests = []
    gb = GPA_BASE

    t = new("H_vm_twostage")
    t.describe(
        source=HYP,
        rule_text="Whenever the current virtualization mode V is 1, two-stage address translation and protection "
        "is in effect. For any virtual memory access, the original virtual address is converted in the first "
        "stage by VS-level address translation, as controlled by the vsatp register, into a guest physical "
        "address. The guest physical address is then converted in the second stage by guest physical address "
        "translation, as controlled by the hgatp register, into a supervisor physical address. The two stages "
        "are known also as VS-stage and G-stage translation.",
        context="Guest code runs from the image, identity-mapped in both stages (VS-stage supervisor pages for "
        "VS-mode; a second VS table with user pages for VU-mode). Data pages map crosswise: VA0 -> GPA1 -> B, "
        "VA1 -> GPA0 -> A, so skipping or reordering a stage reads the wrong page.",
        plan="1. VS-mode lw of VA0 reads B and of VA1 reads A; sw to VA0 lands in B.\n"
        "2. VU-mode (user pages) lw of VA0 reads B.\n"
        "3. VS-mode lw of VA2 (VS-stage invalid) raises a load page fault (13) with htval=0; of VA3 (VS-stage "
        "valid, G-stage unmapped) raises a load guest-page fault (21) with htval 0 or GPA3>>2; both with "
        "stval 0 or the VA, and GVA=1 with a nonzero stval.",
    )
    init(t)
    for n in ("A", "B", "C"):
        t.page(n, {16: (4, 0)})

    def body(xlen: int) -> None:
        _g, _v = two(
            t,
            xlen,
            [
                (0, LEAF, gb[xlen] + 0x1000, "B", ULEAF),
                (1, LEAF, gb[xlen], "A", ULEAF),
                (3, LEAF, gb[xlen] + 0x3000, None, 0),
            ],
            vs_identity=LEAF,
        )
        va = VA_BASE[xlen]
        sa, sb = lw_sig(t, "A"), lw_sig(t, "B")
        if MUT == "vstage_bypassed":
            sa = sb = None
        if MUT == "gstage_bypassed_v1":
            sa = sb = None
        for k, s in ((0, sb), (1, sa)):
            t.emit(f"li x6, {hex(va + k * 0x1000)}")
            exp = "ok" if s is not None else [LOAD_PF, LOAD_GPF, LOAD_AF]
            lab = vs_run(t, "VS", ["lw x7, 0(x6)"], exp, f"lw of VA{k}")
            if s is not None:
                t.check("x7", s, lab, f"VS-mode lw of VA{k} goes through both stages")
        t.emit(f"li x6, {hex(va + 16)}")
        t.load("x8", 0x7E57_0001, "value")
        lab = vs_run(t, "VS", ["sw x8, 0(x6)"], "ok", "sw to VA0")
        t.la("x6", f"{t.page('B')}+16")
        t.emit("lw x7, 0(x6)")
        t.check("x7", 0x7E57_0001, lab, "VS-mode sw to VA0 lands in page B")
        t.emit(f"li x6, {hex(va + 0x2000)}")
        vs_run(
            t,
            "VS",
            ["lw x7, 0(x6)"],
            LOAD_PF,
            "lw of VA2 (VS-stage invalid)",
            {LOAD_PF: {"tval": va + 0x2000, "gva": 1, "tval2": 0}},
        )
        t.emit(f"li x6, {hex(va + 0x3000)}")
        vs_run(
            t,
            "VS",
            ["lw x7, 0(x6)"],
            gfail(LOAD_GPF),
            "lw of VA3 (G-stage unmapped)",
            gpf_extras(gfail(LOAD_GPF), va + 0x3000, gb[xlen] + 0x3000, LW),
        )
        atp_off(t)
        # VU: user pages everywhere
        vu = PT(t, f"vu{xlen}", VS_OF[xlen], xlen)
        vu.identity(LEAF | U)
        vu.leaf(va, gb[xlen] + 0x1000, LEAF | U)
        g2 = g_pt(t, xlen, name=f"g{xlen}b")
        g2.leaf(gb[xlen] + 0x1000, t.page("B"), ULEAF)
        hgatp_on(t, g2)
        vsatp_on(t, vu)
        t.emit(f"li x6, {hex(va)}")
        lab = vs_run(
            t,
            "VU",
            ["lw x7, 0(x6)"],
            "ok" if sb is not None else [LOAD_PF, LOAD_GPF, LOAD_AF],
            "lw of VA0 (user pages)",
        )
        if sb is not None:
            t.check("x7", sb, lab, "VU-mode lw of VA0 goes through both stages")
        atp_off(t)

    both(t, body)
    tests.append(t)

    t = new("H_vm_gstagetrans")
    t.describe(
        source=HYP,
        rule_text="When V=1, memory accesses that would normally bypass address translation are subject to "
        "G-stage address translation alone. This includes memory accesses made in support of VS-stage address "
        "translation, such as reads and writes of VS-level page tables.",
        context="vsatp.PPN and every non-leaf VS PTE hold guest physical addresses (GPA_T + i*4K), which "
        "G-stage maps to the real tables. Those GPAs are not RAM as physical addresses, so a design that uses "
        "them untranslated reads garbage or faults.",
        plan="1. HLV.W (SPVP=1) and VS-mode lw of VA0 read page A through the G-stage-mapped VS tables.\n"
        "2. The G-stage mapping of the VS level-1 table GPA is removed: HLV.W of VA0 raises a load guest-page "
        "fault (the implicit read), with htval 0 or the PTE's GPA >> 2, and htinst the read pseudoinstruction "
        "when htval is nonzero.",
    )
    init(t)
    t.page("A")

    def body2(xlen: int) -> None:
        gt = gb[xlen] + 0x10_0000
        g, v = two(t, xlen, [(0, LEAF, gb[xlen], "A", ULEAF)], vs_identity=LEAF, vs_gpa=gt)
        va = VA_BASE[xlen]
        spvp(t, True)
        hl(t, "hlv.w", va, "VS tables at GPAs", "ok", lw_sig(t, "A"))
        t.emit(f"li x6, {hex(va)}")
        lab = vs_run(t, "VS", ["lw x7, 0(x6)"], "ok", "lw of VA0")
        t.check("x7", lw_sig(t, "A"), lab, "VS-mode lw reads A through the G-stage-mapped VS tables")
        # unmap the level-1 table's GPA (second table created)
        l1 = v.pointer(va, 1)
        l1gpa = v.gpas[l1]
        g.raw(l1gpa, 0, note="unmap the VS level-1 table's GPA")
        t.emit(HFENCE_GVMA)
        t.emit(HFENCE_VVMA)
        pte_gpa = l1gpa + v._idx(va, 1) * (xlen // 8)
        lab = hl(
            t, "hlv.w", va, "VS level-1 table unmapped in G-stage", gfail(LOAD_GPF), gpa=pte_gpa, implicit=PSEUDO_R
        )
        if MUT != "gpf_as_pf":
            pseudo_required(t, lab, "implicit read of the level-1 VS PTE", PSEUDO_R)
        spvp(t, False)
        atp_off(t)

    both(t, body2)
    tests.append(t)

    t = new("H_vm_gpatrans")
    t.describe(
        source=HYP,
        rule_text="The conversion of an Sv32x4, Sv39x4, Sv48x4, or Sv57x4 guest physical address is accomplished "
        "with the same algorithm used for Sv32, Sv39, Sv48, or Sv57, as presented in <<sv32algorithm>>, except "
        "that: hgatp substitutes for the usual satp; for the translation to begin, the effective privilege mode "
        "must be VS-mode or VU-mode; when checking the U bit, the current privilege mode is always taken to be "
        "U-mode; and guest-page-fault exceptions are raised instead of regular page-fault exceptions.",
        context="vsatp Bare (GPA = guest VA). The hgatp substitution and the VS/VU-only start of translation are "
        "covered by every G-stage test (HS-mode code runs untranslated beside them); this test checks the U-bit "
        "and fault-type exceptions.",
        plan="1. G-stage leaf with U=0: HLV.W (SPVP=1, VS-level) raises a load guest-page fault (U is checked as "
        "for U-mode), not a page fault, and so does a VS-mode lw.\n"
        "2. G-stage leaf with U=1 and vsstatus.SUM=0, sstatus.SUM=0: a VS-level HLV.W and a VS-mode lw succeed "
        "(SUM plays no role at G-stage).\n"
        "3. Invalid G-stage PTE: load, store and instruction fetch raise guest-page faults 21, 23, 20 (not "
        "13, 15, 12).",
    )
    init(t)
    t.page("S")
    t.page("U")

    def body3(xlen: int) -> None:
        g = g_pt(t, xlen, name=f"g{xlen}")
        s_gpa, u_gpa, n_gpa = gb[xlen], gb[xlen] + 0x1000, gb[xlen] + 0x2000
        g.leaf(s_gpa, t.page("S"), LEAF)
        g.leaf(u_gpa, t.page("U"), ULEAF)
        hgatp_on(t, g)
        spvp(t, True)
        sp = MUT == "gstage_s_priv"
        hl(
            t,
            "hlv.w",
            s_gpa,
            "G-stage U=0, VS-level",
            "ok" if sp else gfail(LOAD_GPF),
            lw_sig(t, "S") if sp else None,
            gpa=s_gpa,
        )
        t.emit(f"li x6, {hex(s_gpa)}")
        vs_run(
            t,
            "VS",
            ["lw x7, 0(x6)"],
            "ok" if sp else gfail(LOAD_GPF),
            "lw, G-stage U=0",
            {} if sp else gpf_extras(gfail(LOAD_GPF), s_gpa, s_gpa, LW),
        )
        hl(
            t,
            "hlv.w",
            u_gpa,
            "G-stage U=1, VS-level, SUM=0",
            gfail(LOAD_GPF) if sp else "ok",
            None if sp else lw_sig(t, "U"),
            gpa=u_gpa,
        )
        t.emit(f"li x6, {hex(u_gpa)}")
        lab = vs_run(
            t,
            "VS",
            ["lw x7, 0(x6)"],
            gfail(LOAD_GPF) if sp else "ok",
            "lw, G-stage U=1, SUM=0",
            gpf_extras(gfail(LOAD_GPF), u_gpa, u_gpa, LW) if sp else {},
        )
        if not sp:
            t.check("x7", lw_sig(t, "U"), lab, "VS-mode lw of a G-stage user page")
        hl(t, "hlv.w", n_gpa, "invalid G-stage PTE", gfail(LOAD_GPF), gpa=n_gpa)
        t.emit("li x8, 0")
        hl(t, "hsv.w", n_gpa, "invalid G-stage PTE", gfail(STORE_GPF), gpa=n_gpa)
        t.emit(f"li x6, {hex(n_gpa)}")
        lab = vs_run(
            t,
            "VS",
            ["jalr ra, 0(x6)"],
            gfail(INSN_GPF),
            "jump to an unmapped GPA",
            {gfail(INSN_GPF): {"tval": n_gpa, "gva": 1, "tval2": [0, n_gpa >> 2], "tinst": 0}},
            epc=False,
        )
        t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
        t.check("x15", n_gpa, lab, "instruction guest-page fault: sepc is the target")
        spvp(t, False)
        atp_off(t)

    both(t, body3)
    tests.append(t)
    return tests


# ---------------------------------------------------------------- helpers for cause-conditional checks
def if_cause(t: MemTest, cause: int, body) -> None:  # noqa: ANN001
    """After a window whose trap is certain: run body's checks only if the logged cause is `cause`."""
    t.emit("AI_LOG(x14, TRAPLOG_CAUSE)", 10)
    t.load("x5", cause, f"cause {cause}")
    skip, done = t.label("notcause"), t.label("causedone")
    t.emit(f"bne x14, x5, {skip}")
    a = len(t.table)
    body()
    t.emit(f"j {done}")
    t.emit(f"{skip}:", 0)
    t.code += t._skip_lines(a, len(t.table))
    t.emit(f"{done}:", 0)


def handler_is(t: MemTest, lab: str, desc: str, mode: int) -> None:
    """The last trap was taken by handler mode (1 HS, 2 VS, 3 M)."""
    t.emit("AI_LOG(x15, TRAPLOG_VECT)", 10)
    t.emit("andi x15, x15, 3")
    t.check("x15", mode, lab, f"{desc}: taken in {({1: 'HS', 2: 'VS', 3: 'M'})[mode]}-mode")


def menvcfg_bit(t: MemTest, xlen: int, bit: int, on: bool) -> None:
    """M-mode (T-SBI) set/clear of menvcfg bit (>= 32): menvcfgh on RV32."""
    if xlen == 64:
        t.emit("li a1, 1")
        t.emit(f"slli a1, a1, {bit}")
        t.tsbi_csr("SET" if on else "CLEAR", "MENVCFG", "a1")
    else:
        t.emit(f"li a1, {hex(1 << (bit - 32))}")
        t.tsbi_csr("SET" if on else "CLEAR", "MENVCFGH", "a1")


def henvcfg_bit(t: MemTest, xlen: int, bit: int, on: bool) -> None:
    if xlen == 64:
        t.emit("li x7, 1")
        t.emit(f"slli x7, x7, {bit}")
        t.emit(f"{'csrs' if on else 'csrc'} 0x60A, x7  // henvcfg bit {bit}")
    else:
        t.emit(f"li x7, {hex(1 << (bit - 32))}")
        t.emit(f"{'csrs' if on else 'csrc'} 0x61A, x7  // henvcfgh bit {bit - 32}")


ADUE, PBMTE = 61, 62


# ---------------------------------------------------------------- permissions, faults, htval/htinst
def gen_faults() -> list[MemTest]:
    tests = []
    gb = GPA_BASE

    t = new("H_vm_gpapriv")
    t.describe(
        source=HYP,
        rule_text="For G-stage address translation, all memory accesses (including those made to access data "
        "structures for VS-stage address translation) are considered to be user-level accesses, as though "
        "executed in U-mode. Access type permissions—readable, writable, or executable—are checked during G-stage "
        "translation the same as for VS-stage translation. For a memory access made to support VS-stage address "
        "translation (such as to read/write a VS-level page table), permissions and the need to set A and/or D "
        "bits at the G-stage level are checked as though for an implicit load or store, not for the original "
        "access type. However, any exception is always reported for the original access type (instruction, "
        "load, or store/AMO).",
        context="HLV/HSV/HLVX in HS-mode with SPVP=1. The VS tables live at GPAs whose G-stage permissions the test "
        "changes. W without R is a reserved PTE encoding, so such a page faults for every access. G-stage A/D "
        "updating follows menvcfg.ADUE with Svadu (Svade otherwise: a fault).",
        plan="1. Final page G-stage read-only: HLV.W reads, HSV.W raises a store guest-page fault, HLVX.WU a load "
        "guest-page fault.\n"
        "2. Final page execute-only: HLV.W faults (21), HLVX.WU reads.\n"
        "3. Final page write-only (reserved): HLV.W faults (21) and HSV.W faults (23).\n"
        "4. VS tables G-stage execute-only (implicit reads need R): HLV.W raises 21, HSV.W raises 23 and "
        "HLVX.WU raises 21, each reported for the original access type, with htinst the read pseudoinstruction "
        "when htval is nonzero.\n"
        "5. VS tables G-stage read-only, final page read-write: HSV.W succeeds (the implicit accesses are "
        "reads; the VS leaf already has A and D).\n"
        "6. Final page G-stage A=0: with Svadu and menvcfg.ADUE=1 HLV.W reads and the G-stage PTE's A becomes 1; "
        "with menvcfg.ADUE=0 (or Svade only) it raises 21.",
    )
    init(t)
    for n in ("R", "X", "W", "T", "Ad"):
        t.page(n)

    def body(xlen: int) -> None:
        gt = gb[xlen] + 0x10_0000
        g, v = two(
            t,
            xlen,
            [
                (0, LEAF, gb[xlen], "R", V | U | R | A),
                (1, LEAF, gb[xlen] + 0x1000, "X", V | U | XP | A),
                (2, LEAF, gb[xlen] + 0x2000, "W", V | U | W | A | D),
                (3, LEAF, gb[xlen] + 0x3000, "T", ULEAF),
                (4, LEAF, gb[xlen] + 0x4000, "Ad", V | U | RWX_ | D),
            ],
            vs_gpa=gt,
        )
        va = VA_BASE[xlen]
        spvp(t, True)
        g_r, g_s, g_l = gfail(LOAD_GPF), gfail(STORE_GPF), gfail(LOAD_GPF)
        hl(t, "hlv.w", va, "G read-only", "ok", lw_sig(t, "R"))
        t.emit("li x8, 0")
        hl(t, "hsv.w", va + 8, "G read-only", g_s, gpa=gb[xlen] + 8)
        hl(t, "hlvx.wu", va, "G read-only", g_r, gpa=gb[xlen])
        hl(t, "hlv.w", va + 0x1000, "G execute-only", g_r, gpa=gb[xlen] + 0x1000)
        hl(t, "hlvx.wu", va + 0x1000, "G execute-only", "ok", lw_sig(t, "X"))
        hl(t, "hlv.w", va + 0x2000, "G write-only (reserved)", g_r, gpa=gb[xlen] + 0x2000)
        hl(t, "hsv.w", va + 0x2008, "G write-only (reserved)", g_s, gpa=gb[xlen] + 0x2008)
        # tables execute-only at G-stage
        for lab_, a in v.gpas.items():
            g.leaf(a, lab_, V | U | XP | A)
        t.emit(HFENCE_GVMA)
        t.emit(HFENCE_VVMA)
        orig = MUT != "implicit_as_original"
        rp = v.gpa_base + v._idx(va + 0x3000, 0) * (xlen // 8)
        for insn, c in (("hlv.w", g_l), ("hsv.w", g_s), ("hlvx.wu", "ok" if not orig else g_l)):
            if insn == "hsv.w":
                t.emit("li x8, 0")
            lab = hl(
                t,
                insn,
                va + 0x3000,
                "VS tables G-stage execute-only",
                c if orig else ("ok" if insn == "hlvx.wu" else c),
                None,
                gpa=rp,
                implicit=PSEUDO_R,
            )
            if c != "ok" and orig and MUT != "gpf_as_pf":
                pseudo_required(
                    t, lab, f"{insn}: implicit read of the VS root PTE", PSEUDO_R if MUT != "pseudo_zero" else X(0, 0)
                )
        for lab_, a in v.gpas.items():
            g.leaf(a, lab_, V | U | R | A)
        t.emit(HFENCE_GVMA)
        t.emit(HFENCE_VVMA)
        t.load("x8", 0x0BAD_F00D, "value")
        lab = hl(t, "hsv.w", va + 0x3010, "VS tables G-stage read-only, page read-write", "ok")
        t.la("x6", f"{t.page('T')}+16")
        t.emit("lw x7, 0(x6)")
        t.check("x7", 0x0BAD_F00D, lab, "HSV.W through read-only VS tables writes the page")
        for lab_, a in v.gpas.items():
            g.leaf(a, lab_, ULEAF)
        t.emit(HFENCE_GVMA)
        t.emit(HFENCE_VVMA)
        with t.only_if("defined(SVADU_SUPPORTED)"):
            menvcfg_bit(t, xlen, ADUE, True)
            hl(t, "hlv.w", va + 0x4000, "G-stage A=0, menvcfg.ADUE=1", "ok", lw_sig(t, "Ad"))
            gtab = g.pte_addr(gb[xlen] + 0x4000, len(g.geo) - 1)
            del gtab
            lab = t.label("gA")
            t.emit(f"{lab}:", 0)
            t.emit("LREG x7, 0(x8)")
            t.emit("andi x7, x7, 0x40")
            t.check("x7", 0x40, lab, "hardware set A in the G-stage PTE")
            g.leaf(gb[xlen] + 0x4000, t.page("Ad"), V | U | RWX_ | D)
            t.emit(HFENCE_GVMA)
            menvcfg_bit(t, xlen, ADUE, False)
            hl(t, "hlv.w", va + 0x4000, "G-stage A=0, menvcfg.ADUE=0", g_l, gpa=gb[xlen] + 0x4000)
            menvcfg_bit(t, xlen, ADUE, True)
        with t.only_if("!defined(SVADU_SUPPORTED) && defined(SVADE_SUPPORTED)"):
            hl(t, "hlv.w", va + 0x4000, "G-stage A=0, Svade", g_l, gpa=gb[xlen] + 0x4000)
        spvp(t, False)
        atp_off(t)

    both(t, body)
    tests.append(t)

    t = new("H_vm_gpa_g")
    t.describe(
        source=HYP,
        rule_text="The G bit in all G-stage PTEs is currently not used. Until its use is defined by a standard "
        "extension, it should be cleared by software for forward compatibility, and must be ignored by hardware.",
        context="Ignoring G means a G-stage PTE with G=1 translates exactly like one with G=0, including in "
        "non-leaf PTEs, and that G=1 does not exempt an entry from an HFENCE.GVMA for one VMID.",
        plan="1. Non-leaf and leaf G-stage PTEs with G=1: HLV.W and HSV.W through the GPA access the page.\n"
        "2. Change the leaf (G=1) to another page and execute HFENCE.GVMA with rs2 = the current VMID: HLV.W reads "
        "the new page.",
    )
    init(t)
    t.page("A")
    t.page("B")

    def body_g(xlen: int) -> None:
        g = g_pt(t, xlen, name=f"g{xlen}")
        a = gb[xlen]
        g.leaf(a, t.page("A"), ULEAF | G)
        # set G on the non-leaf PTEs too
        for (tab, idx), child in list(g.children.items()):
            t.la("x8", tab)
            t.emit(f"li x7, {idx * (xlen // 8)}")
            t.emit("add x8, x8, x7")
            t.emit("LREG x6, 0(x8)")
            t.emit("ori x6, x6, 0x20  // G")
            t.emit("SREG x6, 0(x8)")
        hgatp_on(t, g)
        bad = MUT == "gpa_g_bit_global"
        hl(
            t,
            "hlv.w",
            a,
            "G=1 in every G-stage PTE",
            gfail(LOAD_GPF) if bad else "ok",
            None if bad else lw_sig(t, "A"),
            gpa=a,
        )
        t.load("x8", 0x6B17, "value")
        hl(t, "hsv.w", a + 8, "G=1 in every G-stage PTE", gfail(STORE_GPF) if bad else "ok", gpa=a + 8)
        g.leaf(a, t.page("B"), ULEAF | G)
        t.emit(f"csrr x9, {hex(HGATP)}")
        t.emit(f"srli x9, x9, {44 if xlen == 64 else 22}")
        t.emit(f"slli x9, x9, {xlen - (14 if xlen == 64 else 7)}")
        t.emit(f"srli x9, x9, {xlen - (14 if xlen == 64 else 7)}  // x9 = VMID (no reserved bits)")
        t.emit(word_hfg(0, 9))
        hl(
            t,
            "hlv.w",
            a,
            "after HFENCE.GVMA x0, VMID",
            gfail(LOAD_GPF) if bad else "ok",
            None if bad else lw_sig(t, "B"),
            gpa=a,
        )
        atp_off(t)

    both(t, body_g)
    tests.append(t)

    t = new("H_guest_page_fault")
    t.describe(
        source=HYP,
        rule_text="Guest-page-fault traps may be delegated from M-mode to HS-mode under the control of CSR "
        "medeleg, but cannot be delegated to other privilege modes. On a guest-page fault, CSR mtval or stval is "
        "written with the faulting guest virtual address as usual, and mtval2 or htval is written either with "
        "zero or with the faulting guest physical address, shifted right by 2 bits. CSR mtinst or htinst may "
        "also be written with information about the faulting instruction or other reason for the access, as "
        "explained in <<tinst-vals>>.",
        context="The framework delegates guest-page faults to HS-mode (medeleg). hedeleg bits 20, 21 and 23 are "
        "read-only zero (<<hedeleg-bits>>). The test writes all ones to hedeleg, so any delegable exception from "
        "VS-mode would go to the VS handler; guest-page faults must still reach HS-mode.",
        plan="1. Write hedeleg (and hedelegh) = all ones: bits 20, 21, 23 read 0.\n"
        "2. VS-mode lw, sw and a jump to unmapped GPAs (VS-stage Bare): guest-page faults 21, 23, 20, taken in "
        "HS-mode, with stval 0 or the guest VA, htval 0 or GPA>>2, htinst 0 or the transformed load/store (0 for "
        "the fetch), GVA=1, sepc = the instruction (the target for the fetch).\n"
        "3. VU-mode lw: the same, from VU.\n"
        "4. hedeleg = 0.",
    )
    init(t)

    def body_gpf(xlen: int) -> None:
        g = g_pt(t, xlen, name=f"g{xlen}")
        hgatp_on(t, g)
        lab = t.label("hedeleg")
        t.emit("li x7, -1")
        t.emit(f"{lab}:", 0)
        t.emit("csrw 0x602, x7  // hedeleg = all ones")
        if xlen == 32:
            t.emit("csrw 0x612, x7  // hedelegh = all ones")
        t.emit("csrr x7, 0x602")
        t.check_masked("x7", (1 << 20) | (1 << 21) | (1 << 23), 0, lab, "hedeleg bits 20, 21, 23 read 0")
        n = gb[xlen] + 0x8000
        hmode = 2 if MUT == "gpf_delegable" else 1
        for mode in ("VS", "VU"):
            t.emit(f"li x6, {hex(n)}")
            lab = vs_run(
                t,
                mode,
                ["lw x7, 0(x6)"],
                gfail(LOAD_GPF),
                "lw of an unmapped GPA",
                gpf_extras(gfail(LOAD_GPF), n, n, LW),
            )
            handler_is(t, lab, f"{mode}-mode load guest-page fault", hmode)
        t.emit(f"li x6, {hex(n + 8)}")
        lab = vs_run(
            t,
            "VS",
            ["sw x8, 0(x6)"],
            gfail(STORE_GPF),
            "sw to an unmapped GPA",
            gpf_extras(gfail(STORE_GPF), n + 8, n + 8, SW),
        )
        handler_is(t, lab, "store guest-page fault", hmode)
        t.emit(f"li x6, {hex(n + 0x100)}")
        lab = vs_run(
            t,
            "VS",
            ["jalr ra, 0(x6)"],
            gfail(INSN_GPF),
            "jump to an unmapped GPA",
            {gfail(INSN_GPF): {"tval": n + 0x100, "gva": 1, "tval2": [0, (n + 0x100) >> 2], "tinst": 0}},
            epc=False,
        )
        handler_is(t, lab, "instruction guest-page fault", hmode)
        t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
        t.check("x15", n + 0x100, lab, "instruction guest-page fault: sepc is the target")
        t.emit("csrw 0x602, x0  // hedeleg = 0")
        if xlen == 32:
            t.emit("csrw 0x612, x0")
        atp_off(t)

    both(t, body_gpf)
    tests.append(t)

    # ---- htval / htinst rules (HS-mode)
    t = new("mtval2_htval_virtaddr")
    t.describe(
        source=HYP,
        rule_text="When a guest-page fault is not due to an implicit memory access for VS-stage address "
        "translation, a nonzero guest physical address written to mtval2/htval shall correspond to the exact "
        "virtual address written to mtval/stval.",
        context="VS-stage maps each guest VA page to a GPA page with a different page number, and G-stage leaves "
        "those GPAs unmapped, so htval (if nonzero) must be GPA>>2 of the exact address, not the VA. The page "
        "offset of the GPA equals that of the VA.",
        plan="1. HLV.W at page offsets 0, 0x7F8 and 0xFFC, HSV.W at 0x404, HLVX.HU at 0x2: guest-page fault with "
        "stval 0 or VA and htval 0 or (GPA page + offset)>>2.\n"
        "2. VS-mode lw and sw at the same kind of addresses: the same.\n"
        "3. A VS-mode jump to a VA whose GPA is unmapped: instruction guest-page fault, htval 0 or GPA>>2.",
    )
    init(t)

    def body_va(xlen: int) -> None:
        va = VA_BASE[xlen]
        gp = gb[xlen] + 0x40_0000  # GPA page numbers differ from the VA's
        _g, _v = two(t, xlen, [(k, LEAF, gp + 0x3000 * (k + 1), None, 0) for k in range(4)], vs_identity=LEAF)
        spvp(t, True)
        for k, (insn, off) in enumerate(
            (("hlv.w", 0), ("hlv.w", 0x7F8), ("hlv.w", 0xFFC), ("hsv.w", 0x404), ("hlvx.hu", 2))
        ):
            k %= 4
            c = gfail(STORE_GPF if insn.startswith("hsv") else LOAD_GPF)
            if insn.startswith("hsv"):
                t.emit("li x8, 0")
            hl(
                t,
                insn,
                va + k * 0x1000 + off,
                f"VA page {k}, offset {hex(off)}",
                c,
                gpa=gp + 0x3000 * (k + 1) + off if MUT != "htval_va" else va + k * 0x1000 + off,
            )
        spvp(t, False)
        for k, (ins, off, enc, c) in enumerate(
            (("lw x7, 0(x6)", 0x10, LW, LOAD_GPF), ("sw x8, 0(x6)", 0xFF8, SW, STORE_GPF))
        ):
            a = va + k * 0x1000 + off
            ga = gp + 0x3000 * (k + 1) + off
            t.emit(f"li x6, {hex(a)}")
            vs_run(
                t,
                "VS",
                [ins],
                gfail(c),
                f"{ins.split()[0]} at VA {hex(a)}",
                gpf_extras(gfail(c), a, ga if MUT != "htval_va" else a, enc),
            )
        a, ga = va + 0x3000 + 0x40, gp + 0xC000 + 0x40
        t.emit(f"li x6, {hex(a)}")
        lab = vs_run(
            t,
            "VS",
            ["jalr ra, 0(x6)"],
            gfail(INSN_GPF),
            f"jump to VA {hex(a)}",
            {gfail(INSN_GPF): {"tval": a, "gva": 1, "tval2": [0, (ga if MUT != "htval_va" else a) >> 2]}},
            epc=False,
        )
        del lab
        atp_off(t)

    both(t, body_va)
    tests.append(t)

    t = new("htval_trapval", suffix="_gpf")
    t.describe(
        source=HYP,
        rule_text="When a guest-page-fault trap is taken into HS-mode, htval is written with either zero or the "
        "guest physical address that faulted, shifted right by 2 bits. For other traps, htval is set to zero, "
        "but a future standard or extension may redefine htval's setting for other traps.",
        context="This test covers the address-translation traps; other traps (ebreak, illegal and virtual "
        "instruction, ecall) belong to the trap tests. Each fault follows a trap that left a nonzero htval, so "
        "a stale htval is caught.",
        plan="1. HLV.W and VS-mode lw of a GPA unmapped at G-stage: htval 0 or GPA>>2.\n"
        "2. Then a VS-stage page fault (HLV.W of an invalid VS-stage page, and VS-mode lw): htval = 0.\n"
        "3. Then a misaligned HLV.W that traps (4 or 5, if it traps): htval = 0.",
    )
    init(t)
    t.page("A")

    def body_htv(xlen: int) -> None:
        va = VA_BASE[xlen]
        _g, _v = two(
            t, xlen, [(0, LEAF, gb[xlen] + 0x5000, None, 0), (2, LEAF, gb[xlen] + 0x6000, "A", ULEAF)], vs_identity=LEAF
        )
        spvp(t, True)
        for _ in range(2):
            hl(t, "hlv.w", va, "G-stage unmapped", gfail(LOAD_GPF), gpa=gb[xlen] + 0x5000)
            hl(t, "hlv.w", va + 0x1000, "VS-stage invalid", LOAD_PF)
            t.emit(f"li x6, {hex(va)}")
            vs_run(
                t,
                "VS",
                ["lw x7, 0(x6)"],
                gfail(LOAD_GPF),
                "lw, G-stage unmapped",
                gpf_extras(gfail(LOAD_GPF), va, gb[xlen] + 0x5000, LW),
            )
            t.emit(f"li x6, {hex(va + 0x1000)}")
            vs_run(
                t,
                "VS",
                ["lw x7, 0(x6)"],
                LOAD_PF,
                "lw, VS-stage invalid",
                {LOAD_PF: {"tval": va + 0x1000, "gva": 1, "tval2": 0}},
            )
            hl(t, "hlv.w", va, "G-stage unmapped", gfail(LOAD_GPF), gpa=gb[xlen] + 0x5000)
            hl(t, "hlv.w", va + 0x2002, "misaligned, mapped", ["ok", LOAD_MIS, LOAD_AF])
        spvp(t, False)
        atp_off(t)

    both(t, body_htv)
    tests.append(t)

    for rule in ("H_trap_xtinst_guestpage", "H_trap_xtinst_guestpage_rw"):
        t = new(rule)
        rw = rule.endswith("_rw")
        t.describe(
            source=HYP,
            rule_text="For guest-page faults, the trap instruction register is written with a special "
            "pseudoinstruction value if: (a) the fault is caused by an implicit memory access for VS-stage address "
            "translation, and (b) a nonzero value (the faulting guest physical address) is written to mtval2 or "
            "htval. If both conditions are met, the value written to mtinst or htinst must be taken from "
            "<<pseudoinsts>>; zero is not allowed."
            if not rw
            else "A write pseudoinstruction (0x00002020 or 0x00003020) is used for the case that the machine is "
            "attempting automatically to update bits A and/or D in VS-level page tables. All other implicit memory "
            "accesses for VS-stage address translation will be reads. If a machine never automatically updates bits "
            "A or D in VS-level page tables (leaving this to software), the write case will never arise. The fact "
            "that such a page table update must actually be atomic, not just a simple write, is ignored for the "
            "pseudoinstruction.",
            context="VS tables live at GPAs mapped by G-stage. RV32 (VSXLEN=32) uses 0x2000/0x2020, RV64 "
            "0x3000/0x3020. htval may be 0, in which case htinst may also be 0."
            + (
                " A hardware A/D update happens with Svadu and henvcfg.ADUE=1; the VS leaf has A=D=0 and its table "
                "page is read-only at G-stage, so the update write faults."
                if rw
                else ""
            ),
            plan=(
                "1. Each VS table level in turn unmapped at G-stage: HLV.W, HSV.W (reported as a store "
                "guest-page fault) and a VS-mode lw raise guest-page faults with htval 0 or the PTE's GPA>>2, and "
                "htinst the read pseudoinstruction when htval is nonzero.\n"
                "2. Contrast: a fault on the final GPA (explicit access) leaves htinst 0 or the transformed "
                "instruction, never the pseudoinstruction."
            )
            if not rw
            else (
                "1. With Svadu and henvcfg.ADUE=1: HLV.W raises a load guest-page fault and HSV.W a store guest-page "
                "fault (original access type), with htinst the write pseudoinstruction when htval is nonzero.\n"
                "2. Without Svadu: henvcfg.ADUE is read-only 0, and with Svade the access raises a page fault "
                "(13/15) instead."
            ),
        )
        init(t)
        t.page("A")

        def body_ti(xlen: int, t: MemTest = t, rw: bool = rw) -> None:
            gt = gb[xlen] + 0x10_0000
            va = VA_BASE[xlen]
            ps_r = PSEUDO_R if MUT != "pseudo_zero" else X(0, 0)
            ps_w = PSEUDO_W if MUT != "pseudo_zero" else X(0, 0)
            if not rw:
                g, v = two(
                    t,
                    xlen,
                    [(0, LEAF, gb[xlen], "A", ULEAF), (1, LEAF, gb[xlen] + 0x1000, None, 0)],
                    vs_identity=LEAF,
                    vs_gpa=gt,
                )
                spvp(t, True)
                for depth in range(len(v.geo)):
                    tab = v.root if depth == 0 else v.pointer(va, depth)
                    tg = v.gpas[tab]
                    pte = tg + v._idx(va, depth) * (xlen // 8)
                    g.raw(tg, 0, note=f"unmap VS table level {len(v.geo) - 1 - depth}")
                    t.emit(HFENCE_GVMA)
                    t.emit(HFENCE_VVMA)
                    for insn in ("hlv.w", "hsv.w"):
                        c = gfail(STORE_GPF if insn == "hsv.w" else LOAD_GPF)
                        if insn == "hsv.w":
                            t.emit("li x8, 0")
                        lab = hl(
                            t,
                            insn,
                            va,
                            f"VS table level {len(v.geo) - 1 - depth} unmapped",
                            c,
                            gpa=pte,
                            implicit=PSEUDO_R,
                        )
                        if MUT != "gpf_as_pf":
                            pseudo_required(t, lab, f"{insn}, implicit read", ps_r)
                    if depth:  # VS-mode code is fetched through the root table, so keep it mapped
                        t.emit(f"li x6, {hex(va)}")
                        lab = vs_run(
                            t,
                            "VS",
                            ["lw x7, 0(x6)"],
                            gfail(LOAD_GPF),
                            "lw, VS table unmapped",
                            {
                                gfail(LOAD_GPF): {
                                    "tval": va,
                                    "gva": 1,
                                    "tval2": [0, pte >> 2],
                                    "tinst": [0, tf(LW), PSEUDO_R],
                                }
                            },
                        )
                        if MUT != "gpf_as_pf":
                            pseudo_required(t, lab, "VS-mode lw, implicit read", ps_r)
                    g.leaf(tg, tab, ULEAF)
                    t.emit(HFENCE_GVMA)
                hl(
                    t,
                    "hlv.w",
                    va + 0x1000,
                    "final GPA unmapped (explicit access)",
                    gfail(LOAD_GPF),
                    gpa=gb[xlen] + 0x1000,
                )
                spvp(t, False)
            else:
                with t.only_if("defined(SVADU_SUPPORTED)"):
                    g, v = two(
                        t,
                        xlen,
                        [(0, V | RWX_, gb[xlen], "A", ULEAF)],
                        vs_identity=LEAF,
                        vs_gpa=gt,
                        gtab_perms=V | U | R | A,
                    )
                    t.tsbi_csr("READ", "MENVCFG" if xlen == 64 else "MENVCFGH")
                    t.emit("mv x1, a0  // saved menvcfg(h)")
                    menvcfg_bit(t, xlen, ADUE, True)  # henvcfg.ADUE is read-only 0 while menvcfg.ADUE=0
                    henvcfg_bit(t, xlen, ADUE, True)
                    t.emit(HFENCE_VVMA)
                    spvp(t, True)
                    leaf_tab = v.pointer(va, len(v.geo) - 1)
                    pte = v.gpas[leaf_tab] + v._idx(va, len(v.geo) - 1) * (xlen // 8)
                    for insn in ("hlv.w", "hsv.w"):
                        c = gfail(STORE_GPF if insn == "hsv.w" else LOAD_GPF)
                        if insn == "hsv.w":
                            t.emit("li x8, 0")
                        lab = hl(
                            t, insn, va, "A/D update to a G-stage read-only VS table", c, gpa=pte, implicit=PSEUDO_W
                        )
                        if MUT != "gpf_as_pf":
                            pseudo_required(t, lab, f"{insn}, implicit A/D write", ps_w)
                    spvp(t, False)
                    henvcfg_bit(t, xlen, ADUE, False)
                    t.emit("mv a1, x1")
                    t.tsbi_csr("WRITE", "MENVCFG" if xlen == 64 else "MENVCFGH", "a1")
                with t.only_if("!defined(SVADU_SUPPORTED) && defined(SVADE_SUPPORTED)"):
                    g, v = two(
                        t,
                        xlen,
                        [(0, V | RWX_, gb[xlen], "A", ULEAF)],
                        vs_identity=LEAF,
                        vs_gpa=gt,
                        gtab_perms=V | U | R | A,
                    )
                    spvp(t, True)
                    hl(t, "hlv.w", va, "VS leaf A=0, Svade", LOAD_PF)
                    t.emit("li x8, 0")
                    hl(t, "hsv.w", va, "VS leaf A=0, Svade", STORE_PF)
                    spvp(t, False)
            atp_off(t)

        both(t, body_ti)
        tests.append(t)
    return tests


RWX_ = R | W | XP


def word_hfg(rs1: int, rs2: int) -> str:
    return f".word {hex(hfence_gvma(rs1, rs2))}  // hfence.gvma x{rs1}, x{rs2}"


def word_hfv(rs1: int, rs2: int) -> str:
    return f".word {hex(hfence_vvma(rs1, rs2))}  // hfence.vvma x{rs1}, x{rs2}"


# ---------------------------------------------------------------- straddling accesses
def straddle_win(
    t: MemTest, mode: str, line: str, e: int, va: int, causes: list[int], fault_page_first: bool, desc: str
) -> str:
    """A misaligned 4-byte access at va (= page end - 2) whose second (or first) page faults."""
    bnd = (va + 0x1000) & ~0xFFF
    # a nonzero stval is the address of the portion that faulted (stval_op_load_store_fault)
    tvals = [0, va] if fault_page_first else [0, bnd]
    ex = {}
    for c in causes:
        if c in (LOAD_GPF, STORE_GPF, LOAD_PF, STORE_PF):
            ex[c] = {"tval": tvals, "gva": 1, "tinst": [0, tf(e, 0)] + ([] if fault_page_first else [tf(e, bnd - va)])}
        elif c in (LOAD_MIS, STORE_MIS):
            ex[c] = {"tval": va, "gva": 1, "tval2": 0, "tinst": [0, tf(e, 0)]}
        else:
            ex[c] = {"tval": [0, va, bnd], "gva": 1, "tval2": 0}
    lab = memwin(t, mode, [line], causes, desc, ex)
    for c in causes:
        if c in (LOAD_GPF, STORE_GPF):
            if_cause(t, c, lambda: tval2_consistent(t, lab, desc))
    return lab


def gen_straddle() -> list[MemTest]:
    tests = []
    gb = GPA_BASE
    t = new("H_straddle")
    t.describe(
        source=HYP,
        rule_text="When an instruction fetch or a misaligned memory access straddles a page boundary, two "
        "different address translations are involved. When a guest-page fault occurs in such a circumstance, the "
        "faulting virtual address written to mtval/stval is the same as would be required for a regular page "
        "fault. Thus, the faulting virtual address may be a page-boundary address that is higher than the "
        "instruction's original virtual address, if the byte at that page boundary is among the accessed bytes.",
        context="A misaligned access may also raise an address-misaligned or access-fault exception instead "
        "(htval 0). A nonzero stval is the address of the portion that faulted (supervisor.adoc "
        "stval_op_load_store_fault), so a fault on the second page reports the page boundary and one on the "
        "first page the original address; stval may also be 0 (no Sstvala assumed). htval is 0 or the GPA of the "
        "stval address >> 2 (mtval2_htval_virtaddr), and htinst "
        "is 0 or the transformed instruction with Addr. Offset = stval - original address "
        "(H_tinst_addr_offset). Instruction straddling needs 16-bit instruction alignment (Zca).",
        plan="1. G-stage: HLV.W, HSV.W and a VS-mode lw at page end - 2 with the next GPA page unmapped: guest-page "
        "fault with stval 0 or the boundary, or misaligned/access fault.\n"
        "2. The first page unmapped, the next mapped: a guest-page fault reports stval 0 or the original "
        "address.\n"
        "3. VS-stage: HLV.W at page end - 2 with the next VA page invalid: page fault with stval 0 or the "
        "boundary, or misaligned/access fault.\n"
        "4. With Zca: a VS-mode jump to a c.nop at GPA page end - 4 followed by a 32-bit instruction at "
        "end - 2 whose second half is in an unmapped page: instruction guest-page fault with sepc = end - 2 and "
        "stval = 0 or the boundary, htval consistent with a nonzero stval.",
    )
    init(t)
    t.page("S1")
    t.page("S2")
    t.page("code", {0xFFC: (2, 0x0001), 0xFFE: (2, 0x0013)})

    def body(xlen: int) -> None:
        va = VA_BASE[xlen]
        p, p2, c = gb[xlen] + 0x7000, gb[xlen] + 0x9000, gb[xlen] + 0xB000
        g = g_pt(t, xlen, name=f"g{xlen}")
        g.leaf(p, t.page("S1"), ULEAF)
        g.leaf(p2 + 0x1000, t.page("S2"), ULEAF)
        g.leaf(c, t.page("code"), ULEAF)
        hgatp_on(t, g)
        spvp(t, True)
        for insn, cs in (
            ("hlv.w", [gfail(LOAD_GPF), LOAD_MIS, LOAD_AF]),
            ("hsv.w", [gfail(STORE_GPF), STORE_MIS, STORE_AF]),
        ):
            t.emit(f"li x6, {hex(p + 0xFFE)}")
            t.emit("li x8, 0")
            line, e = hlsv(insn, "x7", "x6", "x8") if insn == "hsv.w" else hlsv(insn, "x7", "x6")
            straddle_win(t, "S", line, e, p + 0xFFE, cs, False, f"{insn} across into an unmapped GPA page")
        t.emit(f"li x6, {hex(p2 + 0xFFE)}")
        line, e = hlsv("hlv.w", "x7", "x6")
        straddle_win(
            t,
            "S",
            line,
            e,
            p2 + 0xFFE,
            [gfail(LOAD_GPF), LOAD_MIS, LOAD_AF],
            True,
            "hlv.w from an unmapped GPA page into a mapped one",
        )
        t.emit(f"li x6, {hex(p + 0xFFE)}")
        straddle_win(
            t,
            "VS",
            "lw x7, 0(x6)",
            LW,
            p + 0xFFE,
            [gfail(LOAD_GPF), LOAD_MIS, LOAD_AF],
            False,
            "VS-mode lw across into an unmapped GPA page",
        )
        with t.only_if("defined(ZCA_SUPPORTED) || defined(C_SUPPORTED)"):
            t.emit(f"li x6, {hex(c + 0xFFC)}")
            bnd = c + 0x1000
            lab = memwin(
                t,
                "VS",
                ["jalr ra, 0(x6)"],
                gfail(INSN_GPF),
                "fetch across into an unmapped GPA page",
                {gfail(INSN_GPF): {"tval": [0, bnd], "gva": 1, "tinst": 0}},
                epc=False,
            )
            t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
            t.check("x15", c + 0xFFE, lab, "straddling fetch: sepc is the 32-bit instruction at page end - 2")
            tval2_consistent(t, lab, "straddling fetch")
        atp_off(t)
        v = PT(t, f"vs{xlen}", VS_OF[xlen], xlen)
        v.leaf(va, t.page("S1"), LEAF)
        vsatp_on(t, v)
        t.emit(f"li x6, {hex(va + 0xFFE)}")
        line, e = hlsv("hlv.w", "x7", "x6")
        straddle_win(
            t,
            "S",
            line,
            e,
            va + 0xFFE,
            [LOAD_PF, LOAD_MIS, LOAD_AF],
            False,
            "hlv.w across into an invalid VS-stage page",
        )
        spvp(t, False)
        atp_off(t)

    both(t, body)
    tests.append(t)
    return tests


# ---------------------------------------------------------------- MXR for guest code
def gen_mxr_vm() -> list[MemTest]:
    tests = []
    for rule in ("vsstatus_mxr_vm", "sstatus_mxr_vm"):
        t = new(rule)
        hs = rule == "sstatus_mxr_vm"
        t.describe(
            source=HYP,
            rule_text="The vsstatus field MXR, which makes execute-only pages readable by explicit loads, only "
            "overrides VS-stage page protection. Setting MXR at VS-level does not override guest-physical page "
            "protections."
            if not hs
            else "Setting MXR at HS-level, however, overrides both VS-stage and G-stage execute-only permissions.",
            context="VS-mode code (identity-mapped in both stages) loads from a VS-stage execute-only page and from "
            "a G-stage execute-only page. HS-mode sets vsstatus.MXR (the VS-level MXR) and sstatus.MXR.",
            plan="For (sstatus.MXR, vsstatus.MXR) = (0,0), (0,1), (1,0), (1,1): VS-mode lw of the VS-stage "
            "execute-only page succeeds if either is set, else a load page fault; of the G-stage execute-only "
            "page succeeds only with sstatus.MXR, else a load guest-page fault (htval 0 or GPA>>2).",
        )
        init(t)
        t.page("vx")
        t.page("gx")

        def body(xlen: int, t: MemTest = t) -> None:
            gb = GPA_BASE[xlen]
            two(
                t,
                xlen,
                [(0, V | XP | A, gb, "vx", ULEAF), (1, LEAF, gb + 0x1000, "gx", V | U | XP | A)],
                vs_identity=LEAF,
            )
            va = VA_BASE[xlen]
            for sm, vm in ((0, 0), (0, 1), (1, 0), (1, 1)):
                s_mxr(t, bool(sm))
                vs_mxr(t, bool(vm))
                ok_v = bool(sm or vm)
                ok_g = bool(sm or (vm and MUT == "vs_mxr_both"))
                for k, okk, c, nm in ((0, ok_v, LOAD_PF, "vx"), (1, ok_g, gfail(LOAD_GPF), "gx")):
                    a = va + k * 0x1000
                    t.emit(f"li x6, {hex(a)}")
                    ex = {c: {"tval": a, "gva": 1, "tval2": [0, (gb + k * 0x1000) >> 2] if k else 0}}
                    lab = vs_run(
                        t,
                        "VS",
                        ["lw x7, 0(x6)"],
                        "ok" if okk else c,
                        f"lw of {nm} page, sstatus.MXR={sm}, vsstatus.MXR={vm}",
                        {} if okk else ex,
                    )
                    if okk:
                        t.check("x7", lw_sig(t, nm), lab, f"VS-mode lw reads the {nm} page")
            s_mxr(t, False)
            vs_mxr(t, False)
            atp_off(t)

        both(t, body)
        tests.append(t)
    return tests


# ---------------------------------------------------------------- fences
def gen_fences() -> list[MemTest]:
    tests = []
    gb = GPA_BASE

    def setup(t: MemTest, xlen: int, ident: bool = False) -> tuple[PT, PT]:
        return two(
            t,
            xlen,
            [
                (0, LEAF, gb[xlen], "A", ULEAF),
                (1, LEAF, gb[xlen] + 0x1000, "B", ULEAF),
                (2, LEAF, gb[xlen] + 0x2000, "C", ULEAF),
            ],
            vs_identity=LEAF if ident else None,
        )

    def pages(t: MemTest) -> None:
        for n in ("A", "B", "C"):
            t.page(n)

    def rd(t: MemTest, a: int, vals: list[str], desc: str) -> None:
        exp = [lw_sig(t, n) for n in vals]
        lab = hl(t, "hlv.w", a, desc, "ok")
        t.check("x7", exp if len(exp) > 1 else exp[0], lab, f"{desc}: reads {' or '.join(vals)}")

    t = new("hfence-vvma_hfence-gvma_op")
    t.describe(
        source=HYP,
        rule_text="The hypervisor memory-management fence instructions, HFENCE.VVMA and HFENCE.GVMA, perform a "
        "function similar to SFENCE.VMA (<<sfence.vma>>), except applying to the VS-level memory-management data "
        "structures controlled by CSR vsatp (HFENCE.VVMA) or the guest-physical memory-management data structures "
        "controlled by CSR hgatp (HFENCE.GVMA). Instruction SFENCE.VMA applies only to the memory-management data "
        "structures controlled by the current satp (either the HS-level satp when V=0 or vsatp when V=1).",
        context="HLV.W in HS-mode (SPVP=1) through VA0. Until a fence, a translation may use the old or the new "
        "PTE; after the right fence it must use the new one.",
        plan="1. VA0 -> GPA_A -> A. Change the VS-stage PTE to GPA_B: HLV.W reads A or B; after HFENCE.VVMA x0, x0 "
        "it reads B.\n"
        "2. Change the G-stage PTE of GPA_B to page C: HLV.W reads B or C; after HFENCE.GVMA x0, x0 it reads C.",
    )
    init(t)
    pages(t)

    def b1(xlen: int) -> None:
        g, v = setup(t, xlen)
        va = VA_BASE[xlen]
        spvp(t, True)
        rd(t, va, ["A"], "VA0 initially")
        v.leaf(va, gb[xlen] + 0x1000, LEAF)
        rd(t, va, ["A", "B"], "VS PTE changed, no fence")
        t.emit(HFENCE_VVMA)
        rd(t, va, ["B"], "after HFENCE.VVMA")
        g.leaf(gb[xlen] + 0x1000, t.page("C"), ULEAF)
        rd(t, va, ["B", "C"], "G PTE changed, no fence")
        t.emit(HFENCE_GVMA)
        rd(t, va, ["C"], "after HFENCE.GVMA")
        spvp(t, False)
        atp_off(t)

    both(t, b1)
    tests.append(t)

    t = new("hfence-vvma_limits")
    t.describe(
        source=HYP,
        rule_text="Implicit reads need not be ordered when hgatp.VMID is different than at the time HFENCE.VVMA "
        "executed. If operand rs1≠x0, it specifies a single guest virtual address, and if operand rs2≠x0, it "
        "specifies a single guest address-space identifier (ASID).",
        context="HLV.W in HS-mode (SPVP=1). vsatp.ASID is written as 1 and read back (it may be 0 if ASIDLEN=0).",
        plan="1. Change VA0's VS PTE; HFENCE.VVMA rs1=VA0: VA0 reads the new page.\n"
        "2. Change VA1's VS PTE; HFENCE.VVMA rs1=VA0 (another address): VA1 reads old or new.\n"
        "3. Change VA0's VS PTE; HFENCE.VVMA x0, rs2=the current ASID: VA0 reads the new page.",
    )
    init(t)
    pages(t)

    def b2(xlen: int) -> None:
        _g, v = setup(t, xlen)
        va = VA_BASE[xlen]
        v.atp("x6", 1)
        t.emit("csrw 0x280, x6  // vsatp ASID 1")
        t.emit(HFENCE_VVMA)
        t.emit("csrr x9, 0x280")
        t.emit(f"srli x9, x9, {44 if xlen == 64 else 22}")
        t.emit(f"slli x9, x9, {xlen - (16 if xlen == 64 else 9)}")
        t.emit(f"srli x9, x9, {xlen - (16 if xlen == 64 else 9)}  // x9 = ASID")
        spvp(t, True)
        rd(t, va, ["A"], "VA0 initially")
        rd(t, va + 0x1000, ["B"], "VA1 initially")
        v.leaf(va, gb[xlen] + 0x2000, LEAF)
        t.emit(f"li x1, {hex(va)}")
        t.emit(word_hfv(1, 0))
        rd(t, va, ["C"], "VA0 after HFENCE.VVMA rs1=VA0")
        v.leaf(va + 0x1000, gb[xlen], LEAF)
        t.emit(word_hfv(1, 0))
        rd(t, va + 0x1000, ["B", "A"], "VA1 after HFENCE.VVMA rs1=VA0")
        v.leaf(va, gb[xlen], LEAF)
        t.emit(word_hfv(0, 9))
        rd(t, va, ["A"], "VA0 after HFENCE.VVMA x0, ASID")
        spvp(t, False)
        atp_off(t)

    both(t, b2)
    tests.append(t)

    t = new("hfence-vvma_asid")
    t.describe(
        source=HYP,
        rule_text="When rs2≠x0, bits XLEN-1:ASIDMAX of the value held in rs2 are reserved for future standard use. "
        "Until their use is defined by a standard extension, they should be zeroed by software and ignored by "
        "current implementations. Furthermore, if ASIDLEN < ASIDMAX, the implementation shall ignore bits "
        "ASIDMAX-1:ASIDLEN of the value held in rs2.",
        context="ASIDMAX is 16 (RV64) or 9 (RV32). The current ASID is read from vsatp after writing 1.",
        plan="1. Change VA0's VS PTE; HFENCE.VVMA x0, rs2 = ASID | bit XLEN-1 | bit 20: the reserved bits are "
        "ignored, so VA0 reads the new page.",
    )
    init(t)
    pages(t)

    def b3(xlen: int) -> None:
        _g, v = setup(t, xlen)
        va = VA_BASE[xlen]
        v.atp("x6", 1)
        t.emit("csrw 0x280, x6")
        t.emit(HFENCE_VVMA)
        t.emit("csrr x9, 0x280")
        sh, am = (44, 16) if xlen == 64 else (22, 9)
        t.emit(f"srli x9, x9, {sh}")
        t.emit(f"slli x9, x9, {xlen - am}")
        t.emit(f"srli x9, x9, {xlen - am}")
        t.load("x8", (1 << (xlen - 1)) | (1 << 20), "reserved rs2 bits")
        t.emit("or x9, x9, x8")
        spvp(t, True)
        rd(t, va, ["A"], "VA0 initially")
        v.leaf(va, gb[xlen] + 0x1000, LEAF)
        t.emit(word_hfv(0, 9))
        rd(t, va, ["B"], "after HFENCE.VVMA with reserved rs2 bits set")
        spvp(t, False)
        atp_off(t)

    both(t, b3)
    tests.append(t)

    t = new("hfence-gvma_vmid")
    t.describe(
        source=HYP,
        rule_text="When rs2≠x0, bits XLEN-1:VMIDMAX of the value held in rs2 are reserved for future standard use. "
        "Until their use is defined by a standard extension, they should be zeroed by software and ignored by "
        "current implementations. Furthermore, if VMIDLEN < VMIDMAX, the implementation shall ignore bits "
        "VMIDMAX-1:VMIDLEN of the value held in rs2.",
        context="VMIDMAX is 14 (RV64) or 7 (RV32). hgatp.VMID is written as 1 and read back. HFENCE.GVMA's rs1, "
        "when not x0, is a guest physical address shifted right by 2.",
        plan="1. Change GPA_A's G-stage PTE; HFENCE.GVMA x0, rs2 = VMID | bit XLEN-1 | bit 30 (RV64) or 20 "
        "(RV32): HLV.W reads the new page.\n"
        "2. Change it again; HFENCE.GVMA rs1 = GPA_A >> 2, x0: HLV.W reads the new page.",
    )
    init(t)
    pages(t)

    def b4(xlen: int) -> None:
        g, _v = setup(t, xlen)
        va = VA_BASE[xlen]
        g.atp("x6", 1)
        t.emit(f"csrw {hex(HGATP)}, x6  // VMID 1")
        t.emit(HFENCE_GVMA)
        t.emit(f"csrr x9, {hex(HGATP)}")
        sh, vm = (44, 14) if xlen == 64 else (22, 7)
        t.emit(f"srli x9, x9, {sh}")
        t.emit(f"slli x9, x9, {xlen - vm}")
        t.emit(f"srli x9, x9, {xlen - vm}")
        t.load("x8", (1 << (xlen - 1)) | (1 << (30 if xlen == 64 else 20)), "reserved rs2 bits")
        t.emit("or x9, x9, x8")
        spvp(t, True)
        rd(t, va, ["A"], "initially")
        g.leaf(gb[xlen], t.page("B"), ULEAF)
        t.emit(word_hfg(0, 9))
        rd(t, va, ["B"], "after HFENCE.GVMA x0, VMID with reserved bits")
        g.leaf(gb[xlen], t.page("C"), ULEAF)
        t.emit(f"li x1, {hex(gb[xlen] >> 2)}")
        t.emit(word_hfg(1, 0))
        rd(t, va, ["C"], "after HFENCE.GVMA GPA>>2, x0")
        spvp(t, False)
        atp_off(t)

    both(t, b4)
    tests.append(t)

    for rule in ("hfence-gvma_mode", "hgatp_op_hfence_gvma"):
        t = new(rule)
        mode = rule == "hfence-gvma_mode"
        t.describe(
            source=HYP,
            rule_text="If hgatp.MODE is changed for a given VMID, an HFENCE.GVMA with rs1=x0 (and rs2 set to either "
            "x0 or the VMID) must be executed to order subsequent guest translations with the MODE change—even if "
            "the old MODE or new MODE is Bare."
            if mode
            else "Note that writing hgatp does not imply any ordering constraints between page-table updates and "
            "subsequent G-stage address translations.",
            context=(
                "A G-stage table (no identity map) maps the GPA equal to page B's physical address to page C, "
                "so Bare reads B and the x4 mode reads C at the same guest address."
            )
            if mode
            else "Rewriting hgatp with the same value is not a fence: a stale G-stage translation may survive it.",
            plan=(
                "1. hgatp Bare: HLV.W of B's address reads B.\n"
                "2. hgatp = x4 mode (if supported), HFENCE.GVMA x0, x0: reads C.\n"
                "3. hgatp = Bare, HFENCE.GVMA x0, x0: reads B again."
            )
            if mode
            else (
                "1. GPA_A -> A, read A. Change the PTE to B and rewrite hgatp with its value: HLV.W reads A or B.\n"
                "2. HFENCE.GVMA x0, x0: reads B."
            ),
        )
        init(t)
        pages(t)

        def b5(xlen: int, t: MemTest = t, mode: bool = mode) -> None:
            if mode:
                g = PT(t, f"gm{xlen}", G_OF[xlen], xlen)
                g.leaf_runtime(t.page("B"), t.page("C"), ULEAF)
                spvp(t, True)

                def sup() -> None:
                    pb = t.page("B")
                    sb, sc = lw_sig(t, "B"), lw_sig(t, "C")
                    hl(t, "hlv.w", pb, "hgatp Bare", "ok", sb)
                    g.atp("x6")
                    t.emit(f"csrw {hex(HGATP)}, x6")
                    t.emit(HFENCE_GVMA)
                    hl(t, "hlv.w", pb, "x4 mode after HFENCE.GVMA", "ok", sc)
                    t.emit(f"csrw {hex(HGATP)}, x0")
                    t.emit(HFENCE_GVMA)
                    hl(t, "hlv.w", pb, "Bare again after HFENCE.GVMA", "ok", sb)

                probe(t, g)
                t.either("x1", sup, lambda: None)
                spvp(t, False)
            else:
                g, _v = setup(t, xlen)
                va = VA_BASE[xlen]
                spvp(t, True)
                rd(t, va, ["A"], "initially")
                g.leaf(gb[xlen], t.page("B"), ULEAF)
                t.emit(f"csrr x6, {hex(HGATP)}")
                t.emit(f"csrw {hex(HGATP)}, x6  // rewrite hgatp, no fence")
                rd(t, va, ["A", "B"], "after rewriting hgatp")
                t.emit(HFENCE_GVMA)
                rd(t, va, ["B"], "after HFENCE.GVMA")
                spvp(t, False)
            atp_off(t)

        both(t, b5)
        tests.append(t)

    t = new("sfence_vma_v1")
    t.describe(
        source=HYP,
        rule_text="When V=1, the virtual-address argument to SFENCE.VMA is a guest virtual address within the "
        "current virtual machine, and the ASID argument is a VS-level ASID within the current virtual machine. "
        "The current virtual machine is identified by the VMID field of CSR hgatp, and the effective ASID is the "
        "combination of this VMID with the VS-level ASID. The SFENCE.VMA instruction orders stores only to the "
        "VS-level address-translation structures with subsequent VS-stage address translations for the same "
        "virtual machine, i.e., only when hgatp.VMID is the same as when the SFENCE.VMA executed.",
        context="VS-mode code (identity-mapped) with hstatus.VTVM=0. HS-mode changes VS-stage PTEs between windows.",
        plan="1. VS-mode lw of VA0 reads A. HS changes VA0's VS PTE to GPA_B; in VS-mode, SFENCE.VMA x0, x0 then "
        "lw reads B.\n"
        "2. HS changes it back to GPA_A; VS-mode SFENCE.VMA rs1=VA0 then lw reads A.\n"
        "3. HS changes it to GPA_C; VS-mode SFENCE.VMA rs1=x0, rs2=the ASID (vsatp's) then lw reads C.",
    )
    init(t)
    pages(t)

    def b6(xlen: int) -> None:
        _g, v = setup(t, xlen, ident=True)
        va = VA_BASE[xlen]
        t.emit(f"li x6, {hex(va)}")
        lab = vs_run(t, "VS", ["lw x7, 0(x6)"], "ok", "lw of VA0")
        t.check("x7", lw_sig(t, "A"), lab, "VA0 reads A")
        for tgt, fence in ((1, "sfence.vma x0, x0"), (0, "sfence.vma x6, x0"), (2, "sfence.vma x0, x9")):
            v.leaf(va, gb[xlen] + tgt * 0x1000, LEAF)
            t.emit(f"li x6, {hex(va)}")
            t.emit("csrr x9, 0x280")
            t.emit(f"srli x9, x9, {44 if xlen == 64 else 22}")
            t.emit(f"slli x9, x9, {xlen - (16 if xlen == 64 else 9)}")
            t.emit(f"srli x9, x9, {xlen - (16 if xlen == 64 else 9)}")
            lab = vs_run(t, "VS", [fence, "lw x7, 0(x6)"], "ok", f"{fence}; lw")
            t.check("x7", lw_sig(t, "ABC"[tgt]), lab, f"VS-mode {fence} orders the VS PTE change")
        atp_off(t)

    both(t, b6)
    tests.append(t)
    return tests


# ---------------------------------------------------------------- vsatp
def gen_vsatp() -> list[MemTest]:
    tests = []
    t = new("vsatp_mode_unsupported_v1", rv64=True)
    t.describe(
        source=HYP,
        rule_text="However, when V=1, a write to satp with an unsupported MODE value is ignored and no write to vsatp "
        "is effected.",
        context="RV64 MODE values 1-7 and 11-15 are reserved. VS-mode writes satp (vsatp) both while vsatp is Bare "
        "and while a VS-stage identity map is active (the guest keeps running only if the write is ignored).",
        plan="1. vsatp = Bare: VS-mode csrw satp with MODE 1, 7, 11, 15 and a nonzero PPN; HS-mode reads vsatp = "
        "0.\n"
        "2. vsatp = Sv39 identity map: the same writes; VS-mode reads satp back unchanged and HS-mode reads the "
        "original vsatp.",
    )
    init(t)
    v = PT(t, "vs64", "sv39", 64)
    v.identity(LEAF)
    g = g_pt(t, 64, name="g64")
    hgatp_on(t, g)
    for active in (False, True):
        if active:
            vsatp_on(t, v)
        t.emit("csrr x9, 0x280  // original vsatp")
        for m in (1, 7, 11, 15):
            t.la("x6", v.root)
            t.emit("srli x6, x6, 12")
            t.emit(f"li x7, {hex(m << 60)}")
            t.emit("or x6, x6, x7")
            lab = vs_run(t, "VS", ["csrw satp, x6", "csrr x7, satp"], "ok", f"csrw satp MODE {m}")
            t.emit("csrr x8, 0x280")
            t.emit("xor x8, x8, x9")
            t.emit("seqz x8, x8")
            if MUT == "vsatp_v1_unsupported_written":
                t.emit("xori x8, x8, 1")
            t.check_bool("x8", lab, f"VS-mode write of satp with MODE {m} leaves vsatp unchanged")
            t.emit("xor x7, x7, x9")
            t.check("x7", 0, lab, f"VS-mode reads satp unchanged after writing MODE {m}")
    atp_off(t)
    tests.append(t)

    t = new("vsatp_mode_unsupported_v0", rv64=True)
    t.describe(
        source=HYP,
        rule_text="When V=0, a write to vsatp with an unsupported MODE value is either ignored as it is for satp, "
        "or the fields of vsatp are treated as WARL in the normal way.",
        context="RV64. Starting from vsatp = Sv39 | PPN P1, HS-mode writes reserved MODE values with PPN P2.",
        plan="1. For MODE 1, 7, 11, 15: the value read is the old vsatp (ignored), or has MODE 0, 8, 9, 10 or 11 "
        "(WARL).",
    )
    init(t)
    v = PT(t, "vs64", "sv39", 64)
    v2 = PT(t, "vs64b", "sv39", 64)
    for m in (1, 7, 11, 15):
        v.atp("x9")
        t.emit("csrw 0x280, x9  // vsatp = Sv39, root P1")
        t.la("x6", v2.root)
        t.emit("srli x6, x6, 12")
        t.emit(f"li x7, {hex(m << 60)}")
        t.emit("or x6, x6, x7")
        lab = t.label("v0")
        t.emit(f"{lab}:", 0)
        t.emit("csrw 0x280, x6")
        t.emit("csrr x7, 0x280")
        t.emit("xor x8, x7, x9")
        t.emit("seqz x8, x8  // ignored")
        t.emit("srli x7, x7, 60")
        t.emit("li x5, 12")
        t.emit("sltu x5, x7, x5")
        t.emit("li x6, 8")
        t.emit("sltu x6, x7, x6")
        t.emit("xori x6, x6, 1")
        t.emit("and x5, x5, x6  // 8 <= MODE <= 11")
        t.emit("seqz x6, x7")
        t.emit("or x5, x5, x6")
        t.emit("or x5, x5, x8")
        t.check_bool("x5", lab, f"vsatp after writing MODE {m} at V=0: unchanged, or a defined MODE")
    t.emit("csrw 0x280, x0")
    tests.append(t)

    t = new("vsatp_asidlen", ["I", "S", "H", "Sm"], boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="The ASID field in the vsatp register has the same number of implemented bits as that of the satp "
        "register, i.e., it is ASIDLEN bits wide.",
        context="M-mode test: satp can be written with a paged MODE without affecting M-mode. Sv39 (RV64) and Sv32 "
        "(RV32) are required with H.",
        plan="1. Write satp and vsatp = paged MODE | ASID all ones | PPN 0; their ASID fields read back equal.\n"
        "2. satp = vsatp = 0, SFENCE.VMA.",
    )
    for xlen, mode, sh, am in ((64, 8 << 60, 44, 16), (32, 1 << 31, 22, 9)):
        with t.rv64_only() if xlen == 64 else t.rv32_only():
            t.load("x6", mode | (((1 << am) - 1) << sh), "paged MODE, ASID all ones")
            lab = t.label("asid")
            t.emit(f"{lab}:", 0)
            t.emit("csrw satp, x6")
            t.emit("csrr x7, satp")
            t.emit("csrw 0x280, x6")
            t.emit("csrr x8, 0x280")
            t.emit("csrw satp, x0")
            t.emit("csrw 0x280, x0")
            t.emit("sfence.vma")
            t.load("x9", ((1 << am) - 1) << sh, "ASID field")
            t.emit("and x7, x7, x9")
            t.emit("and x8, x8, x9")
            t.emit("xor x7, x7, x8")
            t.check("x7", 0, lab, "vsatp.ASID implements the same bits as satp.ASID")
    tests.append(t)

    t = new("vsatp_sz_acc_op")
    t.describe(
        source=HYP,
        rule_text="The vsatp register is a VSXLEN-bit read/write register that is VS-mode's version of supervisor "
        "register satp, formatted as shown in <<rv32vsatpreg>> for VSXLEN=32 and <<rv64vsatpreg>> for VSXLEN=64. "
        "When V=1, vsatp substitutes for the usual satp, so instructions that normally read or modify satp "
        "actually access vsatp instead. vsatp controls VS-stage address translation, the first stage of "
        "two-stage translation for guest virtual addresses (see <<two-stage-translation>>).",
        context="VS-mode code runs with a VS-stage identity map, so every satp value it writes keeps the same MODE "
        "and root and only changes the ASID (which may have no implemented bits). HS-mode's satp stays 0.",
        plan="1. A VS-mode read of satp returns vsatp, not HS-mode's satp (0).\n"
        "2. VS-mode csrw, csrrs and csrrc of satp (ASID bits) land in vsatp: HS-mode reads vsatp equal to what "
        "VS-mode reads back, with MODE and PPN unchanged, and HS-mode's satp still 0.\n"
        "3. VS-stage translation follows vsatp: a VS-mode lw of VA0 reads the page vsatp maps.\n"
        "4. VU-mode (vsatp Bare) access to satp raises virtual-instruction.",
    )
    init(t)
    t.page("A")

    def b7(xlen: int) -> None:
        _g, _v = two(t, xlen, [(0, LEAF, GPA_BASE[xlen], "A", ULEAF)], vs_identity=LEAF)
        sh = 44 if xlen == 64 else 22
        t.emit("csrr x9, 0x280  // vsatp")
        lab = vs_run(t, "VS", ["csrr x7, satp"], "ok", "csrr satp")
        if MUT == "vs_satp_is_hs_satp":
            t.check("x7", 0, lab, "VS-mode reads HS satp")
        else:
            t.emit("xor x7, x7, x9")
            t.check("x7", 0, lab, "a VS-mode read of satp returns vsatp")
        for asm, val in (
            ("csrw satp, x6", None),
            ("csrrs x0, satp, x6", 1 << (sh + 1)),
            ("csrrc x0, satp, x6", 1 << sh),
        ):
            if val is None:
                t.emit(f"li x6, {hex(1 << sh)}")
                t.emit("or x6, x6, x9  // vsatp with ASID 1")
            else:
                t.load("x6", val, "ASID bit")
            lab = vs_run(t, "VS", [asm, "csrr x7, satp"], "ok", asm)
            t.emit("csrr x8, 0x280")
            t.emit("xor x5, x7, x8")
            t.check("x5", 0, lab, f"{asm} in VS-mode: HS-mode reads vsatp equal to the VS-mode read-back")
            t.load("x5", ((1 << 16) - 1) << sh if xlen == 64 else ((1 << 9) - 1) << sh, "ASID field")
            t.emit("not x5, x5")
            t.emit("xor x6, x8, x9")
            t.emit("and x6, x6, x5")
            t.check("x6", 0, lab, f"{asm} in VS-mode leaves vsatp.MODE and PPN")
            t.emit("csrr x6, satp")
            t.check("x6", 0, lab, f"{asm} in VS-mode leaves HS-mode's satp = 0")
        t.emit(f"li x6, {hex(VA_BASE[xlen])}")
        lab = vs_run(t, "VS", ["lw x7, 0(x6)"], "ok", "lw of VA0")
        t.check("x7", lw_sig(t, "A"), lab, "VS-stage translation follows vsatp")
        atp_off(t)
        memwin(t, "VU", ["csrr x7, satp"], 22, "csrr satp", {22: {"tval": [0, 0x180023F3]}})

    both(t, b7)
    tests.append(t)

    t = new("H_vm_supported")
    t.describe(
        source=HYP,
        rule_text="standard page-based address translation must be supported, either Sv32 for RV32, or a minimum of "
        "Sv39 for RV64",
        context="The VS-stage modes are those of satp; vsatp can be written in HS-mode (V=0) without affecting "
        "HS-mode.",
        plan="1. vsatp = Sv39 (RV64) / Sv32 (RV32) | PPN reads back as written.\n"
        "2. HLV.W through it translates a VA to its page.",
    )
    init(t)
    t.page("A")

    def b8(xlen: int) -> None:
        v = PT(t, f"vs{xlen}", VS_OF[xlen], xlen)
        v.leaf(VA_BASE[xlen], t.page("A"), LEAF)
        v.atp("x6")
        lab = t.label("sup")
        t.emit(f"{lab}:", 0)
        t.emit("csrw 0x280, x6")
        t.emit("csrr x7, 0x280")
        t.emit(HFENCE_VVMA)
        t.emit("xor x7, x7, x6")
        t.check("x7", 0, lab, f"vsatp holds {VS_OF[xlen]} with the written PPN")
        spvp(t, True)
        hl(t, "hlv.w", VA_BASE[xlen], f"{VS_OF[xlen]} translation", "ok", lw_sig(t, "A"))
        spvp(t, False)
        atp_off(t)

    both(t, b8)
    tests.append(t)
    return tests


# ---------------------------------------------------------------- henvcfg ADUE / PBMTE
def gen_env() -> list[MemTest]:
    tests = []
    t = new("henvcfg_adue_op")
    t.describe(
        source=HYP,
        rule_text="If the Svadu extension is implemented, the ADUE bit controls whether hardware updating of PTE A/D "
        "bits is enabled for VS-stage address translation. When ADUE=1, hardware updating of PTE A/D bits is "
        "enabled during VS-stage address translation, and the implementation behaves as though the Svade "
        "extension were not implemented for VS-mode address translation. When ADUE=0, the implementation behaves "
        "as though Svade were implemented for VS-stage address translation. If Svadu is not implemented, ADUE is "
        "read-only zero.",
        context="henvcfg.ADUE is bit 61 (henvcfgh bit 29 on RV32), and is read-only 0 while menvcfg.ADUE=0, so "
        "menvcfg.ADUE is set first (and restored). G-stage A/D updates follow menvcfg.ADUE. HLV/HSV with SPVP=1 on "
        "a VS leaf with A=D=0.",
        plan="1. With Svadu: henvcfg.ADUE=1: HLV.W succeeds and sets the VS PTE's A; HSV.W succeeds and sets D.\n"
        "2. henvcfg.ADUE=0 (A=D=0 again): HLV.W raises a load page fault, HSV.W a store page fault.\n"
        "3. menvcfg.ADUE=1, henvcfg.ADUE=0 and a G-stage leaf with A=0: HLV.W succeeds and the G-stage A becomes "
        "1 (G-stage follows menvcfg.ADUE, not henvcfg.ADUE). With menvcfg.ADUE=0, henvcfg.ADUE reads 0 after "
        "writing 1 (machine.adoc, menvcfg_adue_henvcfg_adue_rdonly0).\n"
        "4. Without Svadu: henvcfg.ADUE reads 0 after writing 1, and with Svade HLV.W faults on A=0.",
    )
    init(t)
    t.page("A")

    def b9(xlen: int) -> None:
        gb = GPA_BASE[xlen]
        va = VA_BASE[xlen]
        with t.only_if("defined(SVADU_SUPPORTED)"):
            t.tsbi_csr("READ", "MENVCFG" if xlen == 64 else "MENVCFGH")
            t.emit("mv x1, a0  // saved menvcfg(h)")
            menvcfg_bit(t, xlen, ADUE, True)
            g, v = two(t, xlen, [(0, V | RWX_, gb, "A", ULEAF)])
            spvp(t, True)
            henvcfg_bit(t, xlen, ADUE, True)
            hl(t, "hlv.w", va, "VS leaf A=0, henvcfg.ADUE=1", "ok", lw_sig(t, "A"))
            for bit, insn in ((A, "hlv.w"), (D, "hsv.w")):
                if insn == "hsv.w":
                    t.emit("li x8, 0")
                    hl(t, insn, va + 8, "VS leaf D=0, henvcfg.ADUE=1", "ok")
                v.pte_addr(va, len(v.geo) - 1)
                lab = t.label("ad")
                t.emit(f"{lab}:", 0)
                t.emit("LREG x7, 0(x8)")
                t.emit(f"andi x7, x7, {bit}")
                t.check("x7", bit, lab, f"{insn} with henvcfg.ADUE=1 set {'A' if bit == A else 'D'} in the VS PTE")
            v.leaf(va, gb, V | RWX_)
            t.emit(HFENCE_VVMA)
            henvcfg_bit(t, xlen, ADUE, False)
            hl(t, "hlv.w", va, "VS leaf A=0, henvcfg.ADUE=0", LOAD_PF)
            t.emit("li x8, 0")
            hl(t, "hsv.w", va, "VS leaf A=0, henvcfg.ADUE=0", STORE_PF)
            v.leaf(va, gb, LEAF)
            g.leaf(gb, t.page("A"), V | U | RWX_ | D)
            for f in (HFENCE_GVMA, HFENCE_VVMA):
                t.emit(f)
            bad = MUT == "henvcfg_adue_gstage"
            hl(
                t,
                "hlv.w",
                va,
                "G leaf A=0, menvcfg.ADUE=1, henvcfg.ADUE=0",
                gfail(LOAD_GPF) if bad else "ok",
                None if bad else lw_sig(t, "A"),
                gpa=gb,
            )
            if not bad:
                g.pte_addr(gb, len(g.geo) - 1)
                lab = t.label("gA")
                t.emit(f"{lab}:", 0)
                t.emit("LREG x7, 0(x8)")
                t.emit(f"andi x7, x7, {A}")
                t.check("x7", A, lab, "G-stage A set by hardware: menvcfg.ADUE, not henvcfg.ADUE, governs G-stage")
            menvcfg_bit(t, xlen, ADUE, False)
            henvcfg_bit(t, xlen, ADUE, True)
            lab = t.label("ro0")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrr x7, {'0x60A' if xlen == 64 else '0x61A'}")
            t.emit(f"srli x7, x7, {ADUE if xlen == 64 else ADUE - 32}")
            t.emit("andi x7, x7, 1")
            t.check("x7", 0, lab, "henvcfg.ADUE is read-only 0 while menvcfg.ADUE=0")
            henvcfg_bit(t, xlen, ADUE, False)
            t.emit("mv a1, x1")
            t.tsbi_csr("WRITE", "MENVCFG" if xlen == 64 else "MENVCFGH", "a1")
            spvp(t, False)
            atp_off(t)
        with t.only_if("!defined(SVADU_SUPPORTED)"):
            henvcfg_bit(t, xlen, ADUE, True)
            lab = t.label("ro")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrr x7, {'0x60A' if xlen == 64 else '0x61A'}")
            t.emit(f"srli x7, x7, {ADUE if xlen == 64 else ADUE - 32}")
            t.emit("andi x7, x7, 1")
            t.check("x7", 0, lab, "henvcfg.ADUE is read-only 0 without Svadu")
            with t.only_if("defined(SVADE_SUPPORTED)"):
                g, v = two(t, xlen, [(0, V | RWX_, gb, "A", ULEAF)])
                spvp(t, True)
                hl(t, "hlv.w", va, "VS leaf A=0, Svade", LOAD_PF)
                spvp(t, False)
                atp_off(t)

    both(t, b9)
    tests.append(t)

    t = new("henvcfg_pbmte_op", rv64=True)
    t.describe(
        source=HYP,
        rule_text="The PBMTE bit controls whether the Svpbmt extension is available for use in VS-stage address "
        "translation. When PBMTE=1, Svpbmt is available for VS-stage address translation. When PBMTE=0, the "
        "implementation behaves as though Svpbmt were not implemented for VS-stage address translation. If "
        "Svpbmt is not implemented, PBMTE is read-only zero.",
        context="RV64 (PBMT is bits 62:61 of Sv39 PTEs; henvcfg.PBMTE is bit 62). Without Svpbmt, bits 62:61 of a "
        "leaf PTE are reserved and must raise a page fault. menvcfg.PBMTE is set first (it gates henvcfg.PBMTE). "
        "PBMT=3 is reserved even with Svpbmt.",
        plan="1. With Svpbmt, henvcfg.PBMTE=1: HLV.W through a VS leaf with PBMT=NC reads the page; with PBMT=3 it "
        "raises a load page fault.\n"
        "2. henvcfg.PBMTE=0: PBMT=NC raises a load page fault.\n"
        "3. Without Svpbmt: henvcfg.PBMTE reads 0 after writing 1, and PBMT=NC raises a load page fault.",
    )
    init(t)
    t.page("A")
    va = VA_BASE[64]
    nc, res = 1 << 61, 3 << 61
    with t.only_if("defined(SVPBMT_SUPPORTED)"):
        t.tsbi_csr("READ", "MENVCFG")
        t.emit("mv x1, a0")
        menvcfg_bit(t, 64, PBMTE, True)
        v = PT(t, "vs64", "sv39", 64)
        v.leaf(va, t.page("A"), LEAF | nc)
        vsatp_on(t, v)
        spvp(t, True)
        henvcfg_bit(t, 64, PBMTE, True)
        t.emit(HFENCE_VVMA)
        hl(t, "hlv.w", va, "PBMT=NC, henvcfg.PBMTE=1", "ok", lw_sig(t, "A"))
        v.leaf(va, t.page("A"), LEAF | res)
        t.emit(HFENCE_VVMA)
        hl(t, "hlv.w", va, "PBMT=3 (reserved), henvcfg.PBMTE=1", LOAD_PF)
        v.leaf(va, t.page("A"), LEAF | nc)
        henvcfg_bit(t, 64, PBMTE, False)
        t.emit(HFENCE_VVMA)
        bad = MUT == "pbmte_ignored"
        hl(t, "hlv.w", va, "PBMT=NC, henvcfg.PBMTE=0", "ok" if bad else LOAD_PF, lw_sig(t, "A") if bad else None)
        spvp(t, False)
        atp_off(t)
        t.emit("mv a1, x1")
        t.tsbi_csr("WRITE", "MENVCFG", "a1")
    with t.only_if("!defined(SVPBMT_SUPPORTED)"):
        henvcfg_bit(t, 64, PBMTE, True)
        lab = t.label("ro")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, 0x60A")
        t.emit(f"srli x7, x7, {PBMTE}")
        t.emit("andi x7, x7, 1")
        t.check("x7", 0, lab, "henvcfg.PBMTE is read-only 0 without Svpbmt")
        v = PT(t, "vs64", "sv39", 64)
        v.leaf(va, t.page("A"), LEAF | nc)
        vsatp_on(t, v)
        spvp(t, True)
        hl(t, "hlv.w", va, "PBMT=NC without Svpbmt", LOAD_PF)
        spvp(t, False)
        atp_off(t)
    tests.append(t)
    return tests


# ---------------------------------------------------------------- traps into M-mode (boot M)
MEDELEG_MEM = (
    (1 << 4) | (1 << 5) | (1 << 6) | (1 << 7) | (1 << 12) | (1 << 13) | (1 << 15) | (1 << 20) | (1 << 21) | (1 << 23)
)


def m_start(t: MemTest) -> None:
    t.comment("M-mode: keep address-translation faults in M-mode (medeleg saved in x1)")
    atp_off(t)
    t.emit("csrr x1, medeleg")
    t.emit(f"li x7, {hex(MEDELEG_MEM)}")
    t.emit("csrc medeleg, x7")


def m_end(t: MemTest) -> None:
    t.emit("csrw medeleg, x1")
    atp_off(t)


def gen_m() -> list[MemTest]:
    tests = []
    req = ["I", "S", "H", "Sm"]
    gb = GPA_BASE

    t = new("mtval2_trapval", req, boot="M", suffix="_gpf_Sm")
    t.describe(
        source=HYP,
        rule_text="When a guest-page-fault trap is taken into M-mode, mtval2 is written with either zero or the "
        "guest physical address that faulted, shifted right by 2 bits. For other traps, mtval2 is set to zero, "
        "but a future standard or extension may redefine mtval2's setting for other traps.",
        context="M-mode test: medeleg is cleared for page faults, guest-page faults, misaligned and access faults, "
        "so they reach M-mode. Guest code runs in VS-mode (entered with T-SBI) with a G-stage identity map; VA "
        "page 0 maps to a GPA that G-stage leaves unmapped, page 1 is invalid at VS-stage.",
        plan="1. VS-mode lw of VA0: load guest-page fault in M-mode, mtval 0 or VA0, mtval2 0 or GPA>>2, mstatus.GVA=1 (with a nonzero mtval), "
        "mtinst 0 or the transformed lw.\n"
        "2. Then VS-mode lw of VA1: load page fault, mtval2 = 0.\n"
        "3. HLV.W in M-mode (SPVP=1) of VA0: load guest-page fault with mtval2 0 or GPA>>2; then HLV.W of VA1: "
        "mtval2 = 0.",
    )
    m_start(t)

    def bm1(xlen: int) -> None:
        va = VA_BASE[xlen]
        two(t, xlen, [(0, LEAF, gb[xlen] + 0x5000, None, 0)], vs_identity=LEAF)
        for _ in range(2):
            t.emit(f"li x6, {hex(va)}")
            memwin_tsbi(
                t,
                "VS",
                ["lw x7, 0(x6)"],
                gfail(LOAD_GPF),
                "lw, G-stage unmapped",
                gpf_extras(gfail(LOAD_GPF), va, gb[xlen] + 0x5000, LW),
            )
            t.emit(f"li x6, {hex(va + 0x1000)}")
            memwin_tsbi(
                t,
                "VS",
                ["lw x7, 0(x6)"],
                LOAD_PF,
                "lw, VS-stage invalid",
                {LOAD_PF: {"tval": va + 0x1000, "gva": 1, "tval2": 0}},
            )
        spvp(t, True)
        for a, c, gpa in ((va, gfail(LOAD_GPF), gb[xlen] + 0x5000), (va + 0x1000, LOAD_PF, None)):
            t.emit(f"li x6, {hex(a)}")
            line, e = hlsv("hlv.w", "x7", "x6")
            ex = {c: {"tval": a, "gva": 1, "tinst": [0, tf(e)], "tval2": [0, gpa >> 2] if gpa else 0}}
            memwin(t, "M", [line], c, "hlv.w in M-mode", ex, handler="M")
        spvp(t, False)

    both(t, bm1)
    m_end(t)
    tests.append(t)

    t = new("mtval2_trapval_vstrans", req, boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="If a guest-page fault is due to an implicit memory access during first-stage (VS-stage) address "
        "translation, a guest physical address written to mtval2 is that of the implicit memory access that "
        "faulted. Additional information is provided in CSR mtinst to disambiguate such situations.",
        context="The VS tables live at GPAs; the G-stage mapping of the level-1 table's GPA is removed (VS-mode "
        "code is fetched through the root-level identity map, so it keeps running).",
        plan="1. VS-mode lw of VA0 and HLV.W in M-mode of VA0: load guest-page fault in M-mode with mtval 0 or VA0, "
        "mtval2 0 or (GPA of the level-1 PTE)>>2 (not the final GPA), and mtinst the read pseudoinstruction "
        "(0x2000 RV32, 0x3000 RV64) whenever mtval2 is nonzero.",
    )
    m_start(t)
    t.page("A")

    def bm2(xlen: int) -> None:
        va = VA_BASE[xlen]
        gt = gb[xlen] + 0x10_0000
        g, v = two(t, xlen, [(0, LEAF, gb[xlen], "A", ULEAF)], vs_identity=LEAF, vs_gpa=gt)
        l1 = v.pointer(va, 1)
        pte = v.gpas[l1] + v._idx(va, 1) * (xlen // 8)
        g.raw(v.gpas[l1], 0, note="unmap the VS level-1 table's GPA")
        t.emit(HFENCE_GVMA)
        t.emit(f"li x6, {hex(va)}")
        lab = memwin_tsbi(
            t,
            "VS",
            ["lw x7, 0(x6)"],
            gfail(LOAD_GPF),
            "lw, VS level-1 table unmapped",
            {gfail(LOAD_GPF): {"tval": va, "gva": 1, "tval2": [0, pte >> 2]}},
        )
        if MUT != "gpf_as_pf":
            pseudo_required(t, lab, "implicit read, VS-mode lw", PSEUDO_R if MUT != "pseudo_zero" else X(0, 0))
        spvp(t, True)
        t.emit(f"li x6, {hex(va)}")
        line, _e = hlsv("hlv.w", "x7", "x6")
        lab = memwin(
            t,
            "M",
            [line],
            gfail(LOAD_GPF),
            "hlv.w, VS level-1 table unmapped",
            {gfail(LOAD_GPF): {"tval": va, "gva": 1, "tval2": [0, pte >> 2]}},
            handler="M",
        )
        if MUT != "gpf_as_pf":
            pseudo_required(t, lab, "implicit read, HLV.W", PSEUDO_R if MUT != "pseudo_zero" else X(0, 0))
        spvp(t, False)

    both(t, bm2)
    m_end(t)
    tests.append(t)

    t = new("mtval2_trapval_other", req, boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="Otherwise, for misaligned loads and stores that cause guest-page faults, a nonzero guest physical "
        "address in mtval2 corresponds to the faulting portion of the access as indicated by the virtual address "
        "in mtval. For instruction guest-page faults on systems with variable-length instructions, a nonzero "
        "mtval2 corresponds to the faulting portion of the instruction as indicated by the virtual address in "
        "mtval.",
        context="vsatp Bare, so the GPA of an address equals the address. A misaligned access may instead raise "
        "address-misaligned or access-fault exceptions. Instruction straddling needs Zca.",
        plan="1. VS-mode lw and sw at GPA page end - 2 with the next page unmapped: a guest-page fault has mtval "
        "= 0 or the boundary (the faulting portion) and, with a nonzero mtval, mtval2 = 0 or mtval>>2.\n"
        "2. With Zca, a 32-bit instruction at page end - 2 whose second half is unmapped: instruction guest-page "
        "fault, mtval = 0 or the boundary, and with a nonzero mtval, mtval2 = 0 or mtval>>2.",
    )
    m_start(t)
    t.page("S1", {0xFF8: (8, 0)})
    t.page("code", {0xFFC: (2, 0x0001), 0xFFE: (2, 0x0013)})

    def bm3(xlen: int) -> None:
        p, c = gb[xlen] + 0x7000, gb[xlen] + 0xB000
        g = g_pt(t, xlen, name=f"g{xlen}")
        g.leaf(p, t.page("S1"), ULEAF)
        g.leaf(c, t.page("code"), ULEAF)
        hgatp_on(t, g)
        for ins, enc, cs in (
            ("lw x7, 0(x6)", LW, [gfail(LOAD_GPF), LOAD_MIS, LOAD_AF]),
            ("sw x8, 0(x6)", SW, [gfail(STORE_GPF), STORE_MIS, STORE_AF]),
        ):
            t.emit(f"li x6, {hex(p + 0xFFE)}")
            t.emit("li x8, 0")
            bnd = p + 0x1000
            ex = {
                cs[0]: {"tval": [0, bnd], "gva": 1, "tinst": [0, tf(enc, 0), tf(enc, 2)]},
                cs[1]: {"tval": p + 0xFFE, "gva": 1, "tval2": 0},
                cs[2]: {"tval": [0, p + 0xFFE, bnd], "tval2": 0},
            }
            lab = memwin_tsbi(t, "VS", [ins], cs, f"{ins.split()[0]} across into an unmapped GPA page", ex)
            if_cause(t, cs[0], lambda lab=lab, ins=ins: tval2_consistent(t, lab, f"{ins.split()[0]} straddle"))
        with t.only_if("defined(ZCA_SUPPORTED) || defined(C_SUPPORTED)"):
            t.emit(f"li x6, {hex(c + 0xFFC)}")
            lab = memwin_tsbi(
                t,
                "VS",
                ["jalr ra, 0(x6)"],
                gfail(INSN_GPF),
                "fetch across into an unmapped page",
                {gfail(INSN_GPF): {"tval": [0, c + 0x1000], "gva": 1}},
                epc=False,
            )
            tval2_consistent(t, lab, "straddling fetch")

    both(t, bm3)
    m_end(t)
    tests.append(t)

    t = new("H_pmp", req, boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="Machine-level physical memory protection applies to supervisor physical addresses and is in "
        "effect regardless of virtualization mode.",
        context="M-mode test. PMP entry 0 (NAPOT 4 KiB, no permissions, not locked) covers one page Z, entry 1 "
        "(NAPOT, all of memory) grants RWX; the original PMP configuration is restored at the end. The test runs "
        "only if the hart accepts that configuration (two NAPOT entries). PMP faults are access faults, never "
        "guest-page faults, and keep their cause for implicit accesses.",
        plan="1. G-stage maps GPA_Z to Z: VS-mode lw and HLV.W (in M-mode) of GPA_Z raise load access faults, and "
        "sw/HSV.W store access faults, in M-mode.\n"
        "2. Z is instead a VS page table (the VS root): HLV.W through it raises a load access fault (implicit "
        "access, reported as a load).",
    )
    m_start(t)
    sv = t.page("save", {0: (8, 0), 8: (8, 0), 16: (8, 0)})
    t.page("Z")

    def bm4(xlen: int) -> None:
        gz = gb[xlen]
        t.la("x9", sv)
        t.emit("csrr x7, pmpcfg0")
        t.emit("SREG x7, 0(x9)")
        t.emit("csrr x7, pmpaddr0")
        t.emit(f"SREG x7, {xlen // 8}(x9)")
        t.emit("csrr x7, pmpaddr1")
        t.emit(f"SREG x7, {2 * xlen // 8}(x9)")

        def pmp_on(target: str) -> None:
            t.la("x7", target)
            t.emit("srli x7, x7, 2")
            t.emit("ori x7, x7, 0x1FF  // NAPOT 4 KiB")
            t.emit("csrw pmpaddr0, x7")
            t.emit("li x7, -1")
            t.emit("csrw pmpaddr1, x7")
            t.emit("li x7, 0x1F18  // entry 0 NAPOT ---, entry 1 NAPOT RWX")
            t.emit("csrw pmpcfg0, x7")
            t.emit("sfence.vma")
            t.emit(HFENCE_GVMA)

        def pmp_off() -> None:
            t.la("x9", sv)
            t.emit(f"LREG x7, {2 * xlen // 8}(x9)")
            t.emit("csrw pmpaddr1, x7")
            t.emit(f"LREG x7, {xlen // 8}(x9)")
            t.emit("csrw pmpaddr0, x7")
            t.emit("LREG x7, 0(x9)")
            t.emit("csrw pmpcfg0, x7")
            t.emit("sfence.vma")
            t.emit(HFENCE_GVMA)

        pmp_on(t.page("Z"))
        t.emit("csrr x8, pmpcfg0")
        t.emit("li x7, 0xFFFF")
        t.emit("and x8, x8, x7")
        t.emit("li x7, 0x1F18")
        t.emit("xor x8, x8, x7")
        t.emit("seqz x8, x8  // 1: both entries took")
        pmp_off()

        def run() -> None:
            g = g_pt(t, xlen, name=f"g{xlen}")
            g.leaf(gz, t.page("Z"), ULEAF)
            hgatp_on(t, g)
            pmp_on(t.page("Z"))
            t.emit(f"li x6, {hex(gz)}")
            t.emit("li x8, 0")
            for ins, c in (("lw x7, 0(x6)", LOAD_AF), ("sw x8, 0(x6)", STORE_AF)):
                memwin_tsbi(
                    t,
                    "VS",
                    [ins],
                    c,
                    f"VS-mode {ins.split()[0]} of a PMP-denied page",
                    {c: {"tval": gz, "gva": 1, "tval2": 0}},
                )
            spvp(t, True)
            t.emit(f"li x6, {hex(gz)}")
            for insn, c in (("hlv.w", LOAD_AF), ("hsv.w", STORE_AF)):
                line, _e = hlsv(insn, "x7", "x6", "x8") if insn == "hsv.w" else hlsv(insn, "x7", "x6")
                memwin(
                    t,
                    "M",
                    [line],
                    c,
                    f"{insn} of a PMP-denied page",
                    {c: {"tval": gz, "gva": 1, "tval2": 0}},
                    handler="M",
                )
            pmp_off()
            v = PT(t, f"vsz{xlen}", VS_OF[xlen], xlen)
            v.leaf(VA_BASE[xlen], t.page("A"), LEAF)
            vsatp_on(t, v)
            pmp_on(v.root)
            t.emit(f"li x6, {hex(VA_BASE[xlen])}")
            line, _e = hlsv("hlv.w", "x7", "x6")
            memwin(
                t,
                "M",
                [line],
                LOAD_AF,
                "hlv.w through a PMP-denied VS root table",
                {LOAD_AF: {"tval": VA_BASE[xlen], "gva": 1, "tval2": 0}},
                handler="M",
            )
            pmp_off()
            spvp(t, False)
            atp_off(t)

        t.either("x8", run, lambda: None)

    t.page("A")
    both(t, bm4)
    m_end(t)
    tests.append(t)
    return tests


def gen() -> list[MemTest]:
    tests = gen_csr()
    tests += gen_x4()
    tests += gen_twostage()
    tests += gen_faults()
    tests += gen_straddle()
    tests += gen_mxr_vm()
    tests += gen_fences()
    tests += gen_vsatp()
    tests += gen_env()
    tests += gen_m()
    return tests
