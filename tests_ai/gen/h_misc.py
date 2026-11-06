# SPDX-License-Identifier: Apache-2.0
"""H suite: CSR field rules (hstatus, VSXL/UXL, henvcfg, trap-value CSRs), VS CSR value sets, and the rules
that VS CSRs do not act while V=0 and HS-level CSRs are kept but idle while V=1."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aigen import X
from hlib import (
    BREAKPOINT,
    HSTATUS,
    HYP,
    MUT,
    csr_num,
    hs_bits,
    hs_read,
    new,
)

if TYPE_CHECKING:
    from aigen import TestFile

MUTANTS = {
    "hstatus_field_ro": "hstatus.VTW is read-only zero",
    "vsxl_reserved_kept": "hstatus.VSXL keeps the reserved value 0 when written",
    "henvcfg_wpri_writable": "henvcfg bit 8 (WPRI) is writable",
    "henvcfgh_alias_low": "RV32 henvcfgh reads the low half of henvcfg",
    "htval_cannot_hold_zero": "htval reads back nonzero after a write of 0",
    "vsepc_bit0_kept": "vsepc keeps bit 0",
    "vstval_truncated": "vstval keeps only 32 bits on RV64",
    "vstvec_used_v0": "a trap into HS-mode while V=0 vectors through vstvec",
    "mtval_ro0": "mtval is read-only zero",
    "misa_h_reads_0": "misa.H reads 0 on a hart with H",
    "dte0_sdt_writable": "vsstatus.SDT is writable while henvcfg.DTE=0",
}


def m_csrw(t: TestFile, name: str, value_reg: str) -> None:
    t.tsbi_csr("WRITE", name.upper(), value_reg)


def eq(t: TestFile, a: str, b: str, lab: str, desc: str) -> None:
    t.emit(f"xor x5, {a}, {b}")
    t.emit("seqz x5, x5")
    t.check_bool("x5", lab, desc)


def gen() -> list[TestFile]:
    tests: list[TestFile] = []
    tests.append(hstatus_sz_acc_op())
    tests.append(hstatus_vsxl_64())
    tests.append(vsstatus_uxl_op())
    tests.append(vsstatus_uxl_change())
    tests += henvcfg_tests()
    tests += tval_csrs()
    tests += vs_value_sets()
    tests.append(h_vscsrs_v0())
    tests.append(h_vscsrs_v1())
    tests.append(h_mtval_nrz())
    tests.append(misa_h_op())
    tests.append(h_requires_i())
    return tests


# ---------------------------------------------------------------- hstatus
def hstatus_sz_acc_op() -> TestFile:
    t = new("hstatus_sz_acc_op")
    fields = ["GVA", "SPV", "SPVP", "HU", "VTVM", "VTW", "VTSR"]
    t.describe(
        source=HYP,
        rule_text="The hstatus register is an HSXLEN-bit read/write register formatted as shown in "
        "<<hstatusreg-rv32>> when HSXLEN=32 and <<hstatusreg>> when HSXLEN=64. The hstatus register provides "
        "facilities analogous to the mstatus register for tracking and controlling the exception behavior of a "
        "VS-mode guest.",
        context="In the register figures, " + ", ".join(fields) + " are plain read/write fields (not WARL); VSBE "
        "and VSXL are WARL, VGEIN is WLRL and HUPMM depends on Ssnpm (their tests are hstatus_vsbe_*, "
        "hstatus_vsxl_*, hstatus_vgein_* and hstatus_hupmm_*). Setting these fields in HS-mode has no effect "
        "until VS-mode runs or SRET executes, and the test runs neither while they are set.",
        plan="1. Each of " + ", ".join(fields) + " is set alone with csrrs and read back as 1, then cleared with "
        "csrrc and read back as 0; the other fields keep their values.\n"
        "2. csrrw of the read value with all seven fields set reads them all back as 1; csrrw with them clear "
        "reads them all as 0.\n"
        "3. HSXLEN: on RV64, hstatus holds bits above 31 (VSXL reads as a legal nonzero encoding, so hstatus is "
        "wider than 32 bits).",
    )
    allm = sum(HSTATUS[f] for f in fields)
    t.li("x7", allm)
    t.emit(f"csrc {hex(csr_num('hstatus'))}, x7  // all seven fields clear")
    for f in fields:
        bit = HSTATUS[f]
        exp = 0 if (MUT == "hstatus_field_ro" and f == "VTW") else bit
        lab = t.label(f"set{f}")
        t.li("x7", bit)
        t.emit(f"{lab}:", 0)
        t.emit(f"csrrs x0, {hex(csr_num('hstatus'))}, x7  // set {f}")
        hs_read(t, "x8", "hstatus")
        t.check_masked("x8", allm, exp, lab, f"hstatus.{f} reads 1 after csrrs, the other fields 0")
        lab = t.label(f"clr{f}")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrrc x0, {hex(csr_num('hstatus'))}, x7  // clear {f}")
        hs_read(t, "x8", "hstatus")
        t.check_masked("x8", allm, 0, lab, f"hstatus.{f} reads 0 after csrrc")
    lab = t.label("rw")
    hs_read(t, "x8", "hstatus")
    t.li("x7", allm)
    t.emit("or x8, x8, x7")
    t.emit(f"{lab}:", 0)
    t.emit(f"csrw {hex(csr_num('hstatus'))}, x8")
    hs_read(t, "x9", "hstatus")
    t.check_masked("x9", allm, 0 if MUT == "hstatus_field_ro" else allm, lab, "csrrw with all seven fields set")
    t.emit("not x7, x7")
    t.emit("and x8, x8, x7")
    t.emit(f"csrw {hex(csr_num('hstatus'))}, x8")
    hs_read(t, "x9", "hstatus")
    t.check_masked("x9", allm, 0, lab, "csrrw with all seven fields clear")
    with t.rv64_only():
        t.emit("srli x9, x9, 32")
        t.emit("andi x9, x9, 3")
        t.check("x9", [1, 2], lab, "RV64: hstatus.VSXL (bits 33:32) reads a legal encoding (1 or 2)")
    return t


def hstatus_vsxl_64() -> TestFile:
    t = new("hstatus_vsxl_64", rv64=True)
    t.describe(
        source=HYP,
        rule_text="When HSXLEN=64, VSXL is a WARL field that is encoded the same as the MXL field of misa, shown "
        "in <<norm:misa_mxl_enc>>.",
        context="MXL encodings: 1 = 32, 2 = 64, 3 = 128 (reserved for RV128, not a legal VSXLEN on an RV64 hart, "
        "where VSXLEN may not exceed HSXLEN), 0 = reserved. vsxl_ro allows VSXL to be read-only 2 "
        "(VSXLEN=HSXLEN). The test therefore accepts 1 or 2 after every write and restores 2. RV32 has no VSXL "
        "field (hstatus_vsxl_32); this file passes trivially there.",
        plan="1. VSXL reads 2 (the framework writes 2 at boot).\n"
        "2. Writes of 0, 1, 3 and 2 each leave VSXL holding 1 or 2, and the other hstatus bits unchanged.\n"
        "3. A write of 2 reads back 2 (64 is HSXLEN, always legal).",
    )
    lab = t.label("vsxl")
    t.emit(f"{lab}:", 0)
    hs_read(t, "x8", "hstatus")
    t.emit("srli x9, x8, 32")
    t.emit("andi x9, x9, 3")
    t.check("x9", 2, lab, "VSXL reads 2 after boot")
    for v in (0, 1, 3, 2):
        lab = t.label(f"w{v}")
        hs_read(t, "x8", "hstatus")
        t.li("x7", 3)
        t.emit("slli x7, x7, 32")
        t.emit("not x7, x7")
        t.emit("and x8, x8, x7")
        t.li("x7", v)
        t.emit("slli x7, x7, 32")
        t.emit("or x8, x8, x7")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrw {hex(csr_num('hstatus'))}, x8  // VSXL = {v}")
        hs_read(t, "x9", "hstatus")
        t.emit("srli x6, x9, 32")
        t.emit("andi x6, x6, 3")
        if v == 2:
            t.check("x6", 2, lab, "VSXL reads 2 after a write of 2")
        elif MUT == "vsxl_reserved_kept" and v == 0:
            t.check("x6", 0, lab, "VSXL after a write of 0")
        else:
            t.check("x6", [1, 2], lab, f"VSXL holds a legal encoding (1 or 2) after a write of {v}")
        t.emit("xor x9, x9, x8")
        t.li("x7", 3)
        t.emit("slli x7, x7, 32")
        t.emit("not x7, x7")
        t.emit("and x9, x9, x7")
        t.check_masked("x9", 0xFFFFFFFF, 0, lab, "the write leaves hstatus bits 31:0 as written")
    return t


def vsstatus_uxl_op() -> TestFile:
    t = new("vsstatus_uxl_op", rv64=True)
    t.describe(
        source=HYP,
        rule_text="The UXL field controls the effective XLEN for VU-mode, which may differ from the XLEN for "
        "VS-mode (VSXLEN). When VSXLEN=32, the UXL field does not exist, and VU-mode XLEN=32. When VSXLEN=64, "
        "UXL is a WARL field that is encoded the same as the MXL field of misa, shown in <<norm:misa_mxl_enc>>. "
        "In particular, an implementation may make UXL be a read-only copy of field VSXL of hstatus, forcing "
        "VU-mode XLEN=VSXLEN.",
        context="With VSXLEN=64 (hstatus.VSXL=2, set at boot), legal UXL values are 1 and 2. VU-mode is not "
        "run with UXL=1: entering a 32-bit mode from code above 2^31 depends on how the pc is narrowed, which "
        "is outside this rule. RV32 has no UXL; the file passes trivially there.",
        plan="1. vsstatus.UXL (bits 33:32) reads 2 after boot.\n"
        "2. HS-mode writes of 0, 1, 3 and 2 to vsstatus.UXL each leave 1 or 2; the write of 2 reads 2.",
    )
    num = csr_num("vsstatus")
    for v in (None, 0, 1, 3, 2):
        lab = t.label("uxl")
        if v is not None:
            hs_read(t, "x8", "vsstatus")
            t.li("x7", 3)
            t.emit("slli x7, x7, 32")
            t.emit("not x7, x7")
            t.emit("and x8, x8, x7")
            t.li("x7", v)
            t.emit("slli x7, x7, 32")
            t.emit("or x8, x8, x7")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {hex(num)}, x8  // vsstatus.UXL = {v}")
        else:
            t.emit(f"{lab}:", 0)
        hs_read(t, "x9", "vsstatus")
        t.emit("srli x9, x9, 32")
        t.emit("andi x9, x9, 3")
        if v in (None, 2):
            t.check("x9", 2, lab, "vsstatus.UXL reads 2" + (" after boot" if v is None else " after a write of 2"))
        else:
            t.check("x9", [1, 2], lab, f"vsstatus.UXL holds a legal encoding (1 or 2) after a write of {v}")
    return t


def vsstatus_uxl_change() -> TestFile:
    t = new("vsstatus_uxl_change", rv64=True)
    t.describe(
        source=HYP,
        rule_text="If VSXLEN is changed from 32 to a wider width, and if field UXL is not restricted to a single "
        "value, it gets the value corresponding to the widest supported width not wider than the new VSXLEN.",
        context="Observable only when both hstatus.VSXL and vsstatus.UXL can hold 1; the test probes both and "
        "otherwise passes. With VSXLEN back at 64 the widest supported width not wider than 64 is 64, so UXL "
        "must read 2, whatever it held before.",
        plan="1. Probe: write vsstatus.UXL=1; if it reads 1, write hstatus.VSXL=1; if that reads 1, the case "
        "applies.\n"
        "2. Write hstatus.VSXL=2: vsstatus.UXL must read 2.\n"
        "3. Restore VSXL=2 and UXL=2.",
    )

    def set_field(csr: str, v: int) -> None:
        hs_read(t, "x8", csr)
        t.li("x7", 3)
        t.emit("slli x7, x7, 32")
        t.emit("not x7, x7")
        t.emit("and x8, x8, x7")
        t.li("x7", v)
        t.emit("slli x7, x7, 32")
        t.emit("or x8, x8, x7")
        t.emit(f"csrw {hex(csr_num(csr))}, x8  // {csr} bits 33:32 = {v}")

    def get_field(reg: str, csr: str) -> None:
        hs_read(t, reg, csr)
        t.emit(f"srli {reg}, {reg}, 32")
        t.emit(f"andi {reg}, {reg}, 3")

    set_field("vsstatus", 1)
    get_field("x1", "vsstatus")
    t.emit("addi x1, x1, -1")
    t.emit("seqz x1, x1  // x1 = UXL can hold 1")

    def uxl_ok() -> None:
        set_field("hstatus", 1)
        get_field("x6", "hstatus")
        t.emit("addi x6, x6, -1")
        t.emit("seqz x6, x6  // x6 = VSXL can hold 1")

        def change() -> None:
            lab = t.label("chg")
            t.emit(f"{lab}:", 0)
            set_field("hstatus", 2)
            get_field("x9", "vsstatus")
            t.check("x9", 2, lab, "vsstatus.UXL after VSXLEN changes from 32 to 64")

        t.either("x6", change, lambda: None)

    t.either("x1", uxl_ok, lambda: None)
    set_field("hstatus", 2)
    set_field("vsstatus", 2)
    return t


# ---------------------------------------------------------------- henvcfg
HENVCFG_FIELDS = {  # name: (mask, condition under which it may be nonzero)
    "FIOM": (1 << 0, None),
    "LPE": (1 << 2, "defined(ZICFILP_SUPPORTED)"),
    "SSE": (1 << 3, "defined(ZICFISS_SUPPORTED)"),
    "CBIE": (3 << 4, "defined(ZICBOM_SUPPORTED)"),
    "CBCFE": (1 << 6, "defined(ZICBOM_SUPPORTED)"),
    "CBZE": (1 << 7, "defined(ZICBOZ_SUPPORTED)"),
    "PMM": (3 << 32, "defined(SSNPM_SUPPORTED) && __riscv_xlen == 64"),
    "DTE": (1 << 59, "defined(SSDBLTRP_SUPPORTED)"),
    "ADUE": (1 << 61, "defined(SVADU_SUPPORTED)"),
    "PBMTE": (1 << 62, "defined(SVPBMT_SUPPORTED)"),
    "STCE": (1 << 63, "defined(SSTC_SUPPORTED)"),
}
DEFINED = sum(m for m, _ in HENVCFG_FIELDS.values())
WPRI = ((1 << 64) - 1) & ~DEFINED


def henvcfg_write(t: TestFile, v: int, note: str) -> None:
    with t.rv64_only():
        t.load("x7", v, note)
        t.emit(f"csrw {hex(csr_num('henvcfg'))}, x7")
    with t.rv32_only():
        t.load("x7", v & 0xFFFFFFFF, f"{note} (low half)")
        t.emit(f"csrw {hex(csr_num('henvcfg'))}, x7")
        t.load("x7", v >> 32, f"{note} (high half)")
        t.emit(f"csrw {hex(csr_num('henvcfgh'))}, x7")


def henvcfg_check(t: TestFile, mask: int, exp: int, lab: str, desc: str) -> None:
    """Check the bits of henvcfg (64-bit view) in mask."""
    lo, hi = mask & 0xFFFFFFFF, mask >> 32
    with t.rv64_only():
        hs_read(t, "x8", "henvcfg")
        t.check_masked("x8", mask, exp & mask, lab, desc)
    with t.rv32_only():
        if lo:
            hs_read(t, "x8", "henvcfg")
            t.check_masked("x8", X(lo, lo), exp & lo, lab, f"{desc} (henvcfg, bits 31:0)")
        if hi:
            hs_read(t, "x8", "henvcfgh")
            t.check_masked("x8", X(hi, hi), (exp >> 32) & hi, lab, f"{desc} (henvcfgh, bits 63:32)")


def henvcfg_tests() -> list[TestFile]:
    tests = []
    t = new("henvcfg_sz_acc_op")
    t.describe(
        source=HYP,
        rule_text="The henvcfg CSR is a 64-bit read/write register, formatted as shown in <<henvcfg>>, that "
        "controls certain characteristics of the execution environment when virtualization mode V=1.",
        context="Fields: FIOM (0), LPE (2), SSE (3), CBIE (5:4), CBCFE (6), CBZE (7), PMM (33:32), DTE (59), ADUE "
        "(61), PBMTE (62), STCE (63); the rest is WPRI, which a hart without those future fields holds "
        "read-only zero. A field of an extension the hart does not implement is read-only zero (henvcfg_*_op, "
        "henvcfg_cb*, henvcfg_stce_rdonly0). On RV32 the high half is henvcfgh. The framework's value is saved "
        "and restored.",
        plan="1. 64 bits: on RV64 a write of all ones and a read of henvcfg exercise bits 63:32 (STCE, PBMTE, "
        "ADUE, DTE, PMM); on RV32 the same through henvcfgh.\n"
        "2. After writing all ones: the WPRI bits read 0, and the fields of unimplemented extensions read 0. "
        "FIOM, which every hart has, reads 1.\n"
        "3. A write of zero reads back zero in every bit (every field can hold 0).",
    )
    t.emit(f"csrr x1, {hex(csr_num('henvcfg'))}  // save henvcfg")
    with t.rv32_only():
        t.emit(f"csrr x9, {hex(csr_num('henvcfgh'))}  // save henvcfgh")
    lab = t.label("ones")
    t.emit(f"{lab}:", 0)
    henvcfg_write(t, (1 << 64) - 1, "all ones")
    henvcfg_check(t, WPRI, (1 << 8) if MUT == "henvcfg_wpri_writable" else 0, lab,
                  "WPRI bits of henvcfg read 0 after a write of all ones")
    henvcfg_check(t, 1, 1, lab, "henvcfg.FIOM reads 1 after a write of all ones")
    for name, (m, cond) in HENVCFG_FIELDS.items():
        if cond is None:
            continue
        with t.only_if(f"!({cond})"):
            henvcfg_check(t, m, 0, lab, f"henvcfg.{name} is read-only zero without its extension")
    lab = t.label("zero")
    t.emit(f"{lab}:", 0)
    henvcfg_write(t, 0, "zero")
    henvcfg_check(t, (1 << 64) - 1, 0, lab, "henvcfg reads 0 after a write of 0")
    t.emit(f"csrw {hex(csr_num('henvcfg'))}, x1  // restore henvcfg")
    with t.rv32_only():
        t.emit(f"csrw {hex(csr_num('henvcfgh'))}, x9  // restore henvcfgh")
    tests.append(t)

    t = new("henvcfgh_sz_acc_op")
    t.describe(
        source=HYP,
        rule_text="When XLEN=32, henvcfgh is a 32-bit read/write register that aliases bits 63:32 of henvcfg. "
        "Register henvcfgh does not exist when XLEN=64.",
        context="On RV32 the fields in bits 63:32 are STCE, PBMTE, ADUE, DTE (PMM is read-only zero on RV32). "
        "Some of them may be read-only zero (absent extension, or the menvcfg bit clear); the test only compares "
        "the two halves, so it does not depend on which bits exist. "
        "RV64 access to 0x61A is H_virtinst_vu_vs32_high_allowedhs_tvm0.",
        plan="1. RV32: henvcfg low-half writes of all ones and zero leave henvcfgh unchanged.\n"
        "2. RV32: henvcfgh writes of all ones and zero leave henvcfg (bits 31:0) unchanged, and henvcfgh reads "
        "back a value with no bits outside STCE, PBMTE, ADUE and DTE.\n"
        "3. Restore both halves.",
    )
    with t.rv32_only():
        t.emit(f"csrr x1, {hex(csr_num('henvcfg'))}  // save henvcfg")
        t.emit(f"csrr x9, {hex(csr_num('henvcfgh'))}  // save henvcfgh")
        lab = t.label("hi")
        t.emit(f"{lab}:", 0)
        t.li("x7", -1)
        t.emit(f"csrw {hex(csr_num('henvcfgh'))}, x7")
        t.emit(f"csrr x6, {hex(csr_num('henvcfgh'))}  // x6 = henvcfgh after all ones")
        t.load("x5", 0xFFFFFFFF & ~((1 << 31) | (1 << 30) | (1 << 29) | (1 << 27)), "non-field bits of 63:32")
        t.emit("and x5, x5, x6")
        t.check("x5", 0, lab, "henvcfgh has no bits set outside STCE, PBMTE, ADUE and DTE")
        for lowv in (0, -1):
            lab = t.label("lo")
            t.li("x7", lowv)
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {hex(csr_num('henvcfg'))}, x7  // low half = {lowv}")
            t.emit(f"csrr x8, {hex(csr_num('henvcfgh'))}")
            if MUT == "henvcfgh_alias_low":
                t.emit(f"csrr x8, {hex(csr_num('henvcfg'))}")
            eq(t, "x8", "x6", lab, f"a write of {lowv} to henvcfg leaves henvcfgh")
        t.emit(f"csrr x6, {hex(csr_num('henvcfg'))}  // x6 = henvcfg low half")
        for hiv in (0, -1):
            lab = t.label("hi")
            t.li("x7", hiv)
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {hex(csr_num('henvcfgh'))}, x7  // high half = {hiv}")
            t.emit(f"csrr x8, {hex(csr_num('henvcfg'))}")
            eq(t, "x8", "x6", lab, f"a write of {hiv} to henvcfgh leaves henvcfg")
        t.emit(f"csrw {hex(csr_num('henvcfg'))}, x1  // restore henvcfg")
        t.emit(f"csrw {hex(csr_num('henvcfgh'))}, x9  // restore henvcfgh")
    tests.append(t)

    t = new("henvcfg_stce_rdonly0", forbidden=["Sstc"])
    t.describe(
        source=HYP,
        rule_text="When the Sstc extension is not implemented, STCE is read-only zero.",
        context="STCE is henvcfg bit 63 (henvcfgh bit 31 on RV32). The file requires a hart without Sstc.",
        plan="1. Write henvcfg (henvcfgh on RV32) with STCE=1: it reads 0.\n2. Restore.",
    )
    t.emit(f"csrr x1, {hex(csr_num('henvcfg'))}")
    with t.rv32_only():
        t.emit(f"csrr x9, {hex(csr_num('henvcfgh'))}")
    lab = t.label("stce")
    t.emit(f"{lab}:", 0)
    henvcfg_write(t, 1 << 63, "STCE only")
    henvcfg_check(t, 1 << 63, 0, lab, "henvcfg.STCE is read-only zero without Sstc")
    t.emit(f"csrw {hex(csr_num('henvcfg'))}, x1")
    with t.rv32_only():
        t.emit(f"csrw {hex(csr_num('henvcfgh'))}, x9")
    tests.append(t)

    # henvcfg.DTE=0 makes vsstatus.SDT read-only zero (Ssdbltrp)
    t = new("henvcfg_dte_op", required=["I", "S", "H", "Ssdbltrp"])
    t.describe(
        source=HYP,
        rule_text="The Ssdbltrp extension adds the double-trap-enable (DTE) field in henvcfg. When henvcfg.DTE "
        "is zero, the implementation behaves as though Ssdbltrp is not implemented for VS-mode and the "
        "vsstatus.SDT bit is read-only zero.",
        context="DTE is henvcfg bit 59 (henvcfgh bit 27). henvcfg.DTE is read-only zero when menvcfg.DTE=0, so "
        "M-mode sets menvcfg.DTE first. vsstatus.SDT is bit 24. SDT=1 in vsstatus only affects traps into "
        "VS-mode, which this test does not take.",
        plan="1. menvcfg.DTE=1, henvcfg.DTE=1: HS-mode writes vsstatus.SDT=1 and reads 1, then clears it.\n"
        "2. henvcfg.DTE=0: writes of vsstatus.SDT=1 (csrs and csrw) read 0.\n"
        "3. Restore henvcfg.DTE=0, vsstatus.SDT=0.",
    )
    sdt = 1 << 24
    with t.rv64_only():
        t.li("a1", 1)
        t.emit("slli a1, a1, 59")
        t.tsbi_csr("SET", "MENVCFG", "a1")
        t.li("x7", 1)
        t.emit("slli x7, x7, 59")
        t.emit(f"csrs {hex(csr_num('henvcfg'))}, x7  // henvcfg.DTE = 1")
    with t.rv32_only():
        t.tsbi_csr("SET", "MENVCFGH", imm=1 << 27)
        t.li("x7", 1 << 27)
        t.emit(f"csrs {hex(csr_num('henvcfgh'))}, x7  // henvcfg.DTE = 1")
    lab = t.label("dte1")
    t.li("x7", sdt)
    t.emit(f"{lab}:", 0)
    t.emit(f"csrs {hex(csr_num('vsstatus'))}, x7  // vsstatus.SDT = 1")
    hs_read(t, "x8", "vsstatus")
    t.check_masked("x8", sdt, sdt, lab, "vsstatus.SDT is writable with henvcfg.DTE=1")
    t.emit(f"csrc {hex(csr_num('vsstatus'))}, x7")
    with t.rv64_only():
        t.li("x7", 1)
        t.emit("slli x7, x7, 59")
        t.emit(f"csrc {hex(csr_num('henvcfg'))}, x7  // henvcfg.DTE = 0")
    with t.rv32_only():
        t.li("x7", 1 << 27)
        t.emit(f"csrc {hex(csr_num('henvcfgh'))}, x7  // henvcfg.DTE = 0")
    lab = t.label("dte0")
    t.li("x7", sdt)
    t.emit(f"{lab}:", 0)
    t.emit(f"csrs {hex(csr_num('vsstatus'))}, x7  // try vsstatus.SDT = 1")
    hs_read(t, "x8", "vsstatus")
    t.check_masked("x8", sdt, sdt if MUT == "dte0_sdt_writable" else 0, lab,
                   "vsstatus.SDT is read-only zero with henvcfg.DTE=0 (csrs)")
    hs_read(t, "x8", "vsstatus")
    t.li("x7", sdt)
    t.emit("or x8, x8, x7")
    t.emit(f"csrw {hex(csr_num('vsstatus'))}, x8  // try vsstatus.SDT = 1")
    hs_read(t, "x8", "vsstatus")
    t.check_masked("x8", sdt, sdt if MUT == "dte0_sdt_writable" else 0, lab,
                   "vsstatus.SDT is read-only zero with henvcfg.DTE=0 (csrw)")
    t.li("x7", sdt)
    t.emit(f"csrc {hex(csr_num('vsstatus'))}, x7")
    with t.rv64_only():
        t.li("a1", 1)
        t.emit("slli a1, a1, 59")
        t.tsbi_csr("CLEAR", "MENVCFG", "a1")
    with t.rv32_only():
        t.tsbi_csr("CLEAR", "MENVCFGH", imm=1 << 27)
    tests.append(t)
    return tests


# ---------------------------------------------------------------- trap-value CSRs
def tval_csrs() -> list[TestFile]:
    tests = []
    specs = [
        ("htval_sz_acc_op", "htval", "HS", "The htval register is an HSXLEN-bit read/write register formatted as "
         "shown in <<htvalreg>>. When a trap is taken into HS-mode, htval is written with additional "
         "exception-specific information, alongside stval, to assist software in handling the trap."),
        ("htval_val", "htval", "HS", "htval is a WARL register that must be able to hold zero and may be capable "
         "of holding only an arbitrary subset of other 2-bit-shifted guest physical addresses, if any."),
        ("htinst_sz_acc_op", "htinst", "HS", "The htinst register is an HSXLEN-bit read/write register formatted "
         "as shown in <<htinstreg>>. When a trap is taken into HS-mode, htinst is written with a value that, if "
         "nonzero, provides information about the instruction that trapped, to assist software in handling the "
         "trap. The values that may be written to htinst on a trap are documented in <<tinst-vals>>."),
        ("htinst_val", "htinst", "HS", "htinst is a WARL register that need only be able to hold the values that "
         "the implementation may automatically write to it on a trap."),
        ("mtval2_sz_acc_op", "mtval2", "M", "The mtval2 register is an MXLEN-bit read/write register formatted as "
         "shown in <<mtval2reg>>. When a trap is taken into M-mode, mtval2 is written with additional "
         "exception-specific information, alongside mtval, to assist software in handling the trap."),
        ("mtval2_val", "mtval2", "M", "mtval2 is a WARL register that must be able to hold zero and may be "
         "capable of holding only an arbitrary subset of other 2-bit-shifted guest physical addresses, if any."),
        ("mtinst_sz_acc_op", "mtinst", "M", "The mtinst register is an MXLEN-bit read/write register formatted as "
         "shown in <<mtinstreg>>. When a trap is taken into M-mode, mtinst is written with a value that, if "
         "nonzero, provides information about the instruction that trapped, to assist software in handling the "
         "trap. The values that may be written to mtinst on a trap are documented in <<tinst-vals>>."),
        ("mtinst_val", "mtinst", "M", "mtinst is a WARL register that need only be able to hold the values that "
         "the implementation may automatically write to it on a trap."),
        ("mtval2_Ssdbltrp", "mtval2", "M", "The Ssdbltrp extension (See <<ssdbltrp>>) requires the implementation "
         "of the mtval2 CSR."),
    ]
    for rule, csr, lvl, text in specs:
        req = ["I", "S", "H"] + (["Ssdbltrp"] if rule == "mtval2_Ssdbltrp" else [])
        if lvl == "M":
            t = new(rule, required=req + ["Sm"], boot="M", suffix="_Sm")
        else:
            t = new(rule, required=req)
        is_val = rule.endswith("_val")
        tinst = "tinst" in csr
        t.describe(
            source=HYP,
            rule_text=text,
            context=(f"{csr} is an M-level CSR, so the file boots to M-mode and requires Sm. " if lvl == "M" else "")
            + ("Every implementation may write zero on any trap (H_trap_xtinst_zero_ok), so zero is a value the "
               "register must hold; other values are implementation-specific. " if tinst else
               "Zero is the one value every implementation must hold; other values are implementation-specific. ")
            + "The trap behavior is tested with the traps (h_trap, h_gstage).",
            plan=f"1. Read {csr} without a trap.\n"
            f"2. Write all ones to {csr} without a trap (any value may be written to a WARL register), then a "
            "write of zero reads back zero.\n"
            "3. A write of zero after a random value also reads back zero.",
        )
        for v in ((1 << 64) - 1, t.rand(32) << 2):
            lab = t.label("rt")
            t.emit(f"{lab}:", 0)
            if True:
                t.load("x7", v, "value written first")
                t.emit(f"csrw {hex(csr_num(csr))}, x7  // {csr}")
                hs_read(t, "x8", csr)
                t.emit(f"csrw {hex(csr_num(csr))}, x0  // {csr} = 0")
                hs_read(t, "x8", csr)
                exp = 1 if MUT == "htval_cannot_hold_zero" and csr == "htval" else 0
                if exp:
                    t.emit("snez x8, x8")
                t.check("x8", exp, lab, f"{csr} reads 0 after a write of 0")
        tests.append(t)
    return tests


# ---------------------------------------------------------------- VS CSR value sets
def vs_value_sets() -> list[TestFile]:
    tests = []
    MAXV = X(0xFFFFFFFF, (1 << 64) - 1)
    sets = {
        "vsepc_warl": ("vsepc", "sepc", "vsepc is a WARL register that must be able to hold the same set of "
                       "values that sepc can hold, with VSXLEN substituting for SXLEN.",
                       [0, 1, 2, 3, 0x7FFFFFFE, MAXV, X(0x80000002, 0xFFFFFFFF80000002), X(0x55555555, 0x5555555555555554)]),
        "vscause_wlrl": ("vscause", "scause", "vscause is a WLRL register that must be able to hold the same set of "
                         "values that scause can hold, with VSXLEN substituting for SXLEN.",
                         [0, 2, 3, 5, 7, 8, 12, 13, 15, 20, 21, 22, 23, X((1 << 31) | 1, (1 << 63) | 1),
                          X((1 << 31) | 5, (1 << 63) | 5), X((1 << 31) | 9, (1 << 63) | 9)]),
        "vstval_warl": ("vstval", "stval", "vstval is a WARL register that must be able to hold the same set of "
                        "values that stval can hold, with VSXLEN substituting for SXLEN.",
                        [0, 0x1000, 0x7FFFF000, X(0xFFFFF000, 0xFFFFFFFFFFFFF000), X(0x12345678, 0x3FFFFFF000),
                         MAXV]),
    }
    for rule, (vcsr, scsr, text, vals) in sets.items():
        t = new(rule)
        t.describe(
            source=HYP,
            rule_text=text,
            context=f"HS-mode writes each value to {scsr} and reads it back at once (no trap occurs in between, so "
            f"the framework's use of {scsr} is not disturbed), then writes it to {vcsr} and reads it back. A value "
            f"{scsr} holds must be held by {vcsr} the same way; values {scsr} cannot hold must be converted the "
            "same way. For vscause (WLRL) only legal values are written: the exception and interrupt codes a "
            "trap can write to scause with H."
            + (" For vsepc, bit 0 always reads 0, and bit 1 reads 0 when IALIGN=32." if vcsr == "vsepc" else ""),
            plan=f"1. For each value: the {scsr} read-back equals the {vcsr} read-back.\n"
            + (f"2. Each legal value reads back exactly from {vcsr}." if vcsr == "vscause" else
               f"2. Values {scsr} must hold (small addresses, 0) read back exactly from {vcsr}."),
        )
        for v in vals:
            lab = t.label("val")
            t.load("x6", v, "value")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {hex(csr_num(scsr))}, x6")
            hs_read(t, "x7", scsr)
            t.emit(f"csrw {hex(csr_num(vcsr))}, x6")
            hs_read(t, "x8", vcsr)
            if MUT == "vsepc_bit0_kept" and vcsr == "vsepc":
                t.emit("andi x7, x7, -2")
                t.emit("andi x5, x6, 1")
                t.emit("or x7, x7, x5")
            if MUT == "vstval_truncated" and vcsr == "vstval":
                with t.rv64_only():
                    t.emit("slli x7, x7, 32")
                    t.emit("srli x7, x7, 32")
            eq(t, "x7", "x8", lab, f"{vcsr} holds the value as {scsr} does")
            exact = vcsr == "vscause" or (isinstance(v, int) and v in (0, 0x1000, 0x7FFFF000))
            if exact:
                t.check("x8", v, lab, f"{vcsr} holds {v if isinstance(v, int) else 'the value'} exactly")
        tests.append(t)
    return tests


# ---------------------------------------------------------------- V=0 / V=1 isolation
def h_vscsrs_v0() -> TestFile:
    t = new("H_vscsrs_v0")
    t.describe(
        source=HYP,
        rule_text="when V=0, the VS CSRs do not ordinarily affect the behavior of the machine other than being "
        "readable and writable by CSR instructions.",
        context="The exceptions (HLV/HSV/HLVX and MPRV with MPV=1) are in h_hlsv. vsscratch and vstvec hold the "
        "framework's VS handler state, so the test saves and restores them; VS-mode is not entered while they "
        "hold other values.",
        plan="1. HS-mode sets vstvec, vsepc, vscause, vstval and vsscratch to unrelated values, vsatp to a "
        "paged mode with a meaningless root, and vsstatus.SIE/SUM/MXR=1.\n"
        "2. An EBREAK in HS-mode traps to HS-mode through stvec (handler mode 1, scause 3, sepc the EBREAK).\n"
        "3. HS-mode loads and stores reach memory untranslated (a store and load-back of a data word).\n"
        "4. An SRET from HS-mode into U-mode returns to sepc, not vsepc, and an EBREAK in U-mode traps to "
        "HS-mode with xPP recording U.\n"
        "5. Restore the VS CSRs.",
    )
    for name in ("vstvec", "vsscratch", "vsatp", "vsstatus", "vsepc", "vscause", "vstval"):
        reg = {"vstvec": "x1", "vsscratch": "x9"}.get(name)
        if reg:
            hs_read(t, reg, name)
    for name, v in (("vstvec", 0x400), ("vsscratch", 0x800), ("vsepc", 0x1230), ("vscause", 13),
                    ("vstval", 0x4560)):
        t.load("x7", v, f"{name} value")
        t.emit(f"csrw {hex(csr_num(name))}, x7  // {name}")
    with t.rv64_only():
        t.load("x7", (8 << 60) | 0x12345, "vsatp = Sv39, root PPN 0x12345")
    with t.rv32_only():
        t.load("x7", (1 << 31) | 0x12345, "vsatp = Sv32, root PPN 0x12345")
    t.emit(f"csrw {hex(csr_num('vsatp'))}, x7  // vsatp (paged)")
    t.li("x7", 0xC0002)
    t.emit(f"csrs {hex(csr_num('vsstatus'))}, x7  // vsstatus.SIE = SUM = MXR = 1")
    lab = t.label("in_S")
    t.allow(1)
    t.emit(f"{lab}:", 0)
    t.emit("ebreak")
    t.outcome(BREAKPOINT, lab, "EBREAK in HS-mode with VS CSRs set", tval=[0, lab], origin="S")
    t.emit("AI_LOG(x15, TRAPLOG_VECT)", 10)
    t.emit("andi x15, x15, 3")
    t.check("x15", 2 if MUT == "vstvec_used_v0" else 1, lab, "the EBREAK is handled by the HS-mode handler "
            "(handler mode 1 HS, 2 VS)")
    lab = t.label("mem")
    t.la("x6", "h_vscsrs_v0_word")
    t.load("x7", 0x5A5A1234, "data value")
    t.emit(f"{lab}:", 0)
    t.emit("sw x7, 0(x6)")
    t.emit("lw x8, 0(x6)")
    t.check("x8", 0x5A5A1234, lab, "an HS-mode store and load reach memory untranslated")
    lab = t.label("in_U")
    t.allow(1)
    t.enter("U")
    t.emit(f"{lab}:", 0)
    t.emit("ebreak")
    t.leave()
    t.outcome(BREAKPOINT, lab, "SRET into U-mode then EBREAK", tval=[0, lab], origin="U")
    t.li("x7", 0xC0002)
    t.emit(f"csrc {hex(csr_num('vsstatus'))}, x7")
    t.emit(f"csrw {hex(csr_num('vsatp'))}, x0")
    t.emit(f"csrw {hex(csr_num('vstvec'))}, x1  // restore vstvec")
    t.emit(f"csrw {hex(csr_num('vsscratch'))}, x9  // restore vsscratch")
    t.extra_data = ["  .p2align 3", "h_vscsrs_v0_word: .dword 0"]
    return t


def h_vscsrs_v1() -> TestFile:
    t = new("H_vscsrs_v1")
    t.describe(
        source=HYP,
        rule_text="While V=1, the normal HS-level supervisor CSRs that are replaced by VS CSRs retain their values "
        "but do not affect the behavior of the machine unless specifically documented to do so.",
        context="Documented exceptions: HS-level sstatus.MXR (two-stage translation) and the HS-level interrupt "
        "state (sie/sip, sstatus.SIE is ignored while V=1). sepc, scause and stval are rewritten by the trap that "
        "ends a VS-mode window, so retention is checked on sstatus.SUM, sstatus.FS (with F), stvec, sscratch and "
        "sie.SSIE.",
        plan="1. HS-mode sets sstatus.SUM=1 and sie.SSIE=1 (sip.SSIP stays 0).\n"
        "2. VS-mode writes sstatus.SUM=0, sie=0, and writes stvec and sscratch with the values it reads (its "
        "own VS CSRs).\n"
        "3. Back in HS-mode: sstatus.SUM, sie.SSIE, stvec and sscratch hold the values HS-mode set.\n"
        "4. Do not affect: with HS-level sstatus.SUM=1 and vsstatus.SUM=0, nothing in VS-mode changes (vsatp is "
        "Bare); an EBREAK in VS-mode (not delegated) still traps to HS-mode through stvec, with hstatus.SPV=1 "
        "recorded.",
    )
    hs_read(t, "x1", "stvec")
    hs_read(t, "x9", "sscratch")
    t.li("x7", 0x40000)
    t.emit(f"csrs {hex(csr_num('sstatus'))}, x7  // HS sstatus.SUM = 1")
    t.li("x7", 2)
    t.emit(f"csrc {hex(csr_num('sip'))}, x7  // sip.SSIP = 0")
    t.emit(f"csrs {hex(csr_num('sie'))}, x7  // sie.SSIE = 1")
    lab = t.window("VS", [
        "li x7, 0x40000",
        f"csrc {hex(csr_num('sstatus'))}, x7  // VS: sstatus.SUM = 0 (vsstatus)",
        f"csrw {hex(csr_num('sie'))}, x0  // VS: sie = 0 (vsie)",
        f"csrr x6, {hex(csr_num('stvec'))}",
        f"csrw {hex(csr_num('stvec'))}, x6  // VS: stvec (vstvec)",
        f"csrr x6, {hex(csr_num('sscratch'))}",
        f"csrw {hex(csr_num('sscratch'))}, x6  // VS: sscratch (vsscratch)",
    ], "ok", "VS-mode writes of its supervisor CSRs")
    hs_read(t, "x8", "sstatus")
    t.check_masked("x8", 0x40000, 0x40000, lab, "HS-level sstatus.SUM keeps 1 across VS-mode execution")
    hs_read(t, "x8", "sie")
    t.check_masked("x8", 2, 2, lab, "HS-level sie.SSIE keeps 1 across VS-mode execution")
    hs_read(t, "x8", "stvec")
    eq(t, "x8", "x1", lab, "HS-level stvec keeps its value across VS-mode execution")
    hs_read(t, "x8", "sscratch")
    eq(t, "x8", "x9", lab, "HS-level sscratch keeps its value across VS-mode execution")
    lab = t.label("in_VS")
    t.allow(1)
    t.enter("VS")
    t.emit(f"{lab}:", 0)
    t.emit("ebreak")
    t.leave()
    t.outcome(BREAKPOINT, lab, "EBREAK in VS-mode, not delegated", tval=[0, lab], origin="VS")
    t.emit("AI_LOG(x15, TRAPLOG_VECT)", 10)
    t.emit("andi x15, x15, 3")
    t.check("x15", 1, lab, "a non-delegated VS-mode EBREAK is handled in HS-mode (handler mode 1)")
    t.li("x7", 2)
    t.emit(f"csrc {hex(csr_num('sie'))}, x7")
    t.li("x7", 0x40000)
    t.emit(f"csrc {hex(csr_num('sstatus'))}, x7")
    return t


# ---------------------------------------------------------------- M-level and misa
def h_mtval_nrz() -> TestFile:
    t = new("H_mtval_nrz", required=["I", "S", "H", "Sm"], boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="CSR mtval must not be read-only zero",
        context="With H, mtval must be able to hold nonzero values. M-mode writes an address that is valid on "
        "every hart (the test's own code address). mtval is M-level, so the file boots to M-mode and requires "
        "Sm.",
        plan="1. M-mode writes mtval = the address of a code label and reads it back nonzero.\n"
        "2. An EBREAK in M-mode traps with mtval = 0 or its address (the trap log); restore mtval = 0.",
    )
    lab = t.label("mtval")
    t.emit(f"{lab}:", 0)
    t.la("x7", lab)
    t.emit("csrw mtval, x7")
    t.emit("csrr x8, mtval")
    if MUT == "mtval_ro0":
        t.emit("li x8, 0")
    t.emit("snez x8, x8")
    t.check_bool("x8", lab, "mtval holds a nonzero value written by M-mode")
    lab = t.label("in_M")
    t.allow(1)
    t.emit(f"{lab}:", 0)
    t.emit("ebreak")
    t.outcome(BREAKPOINT, lab, "EBREAK in M-mode", tval=[0, lab], origin="M")
    t.emit("csrw mtval, x0")
    return t


def misa_h_op() -> TestFile:
    t = new("misa_H_op", required=["I", "S", "H", "Sm"], boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="The hypervisor extension is enabled by setting bit 7 in the misa CSR",
        context="misa.H may be read-only one or writable (WARL). The test does not access a hypervisor CSR while "
        "misa.H is clear: the framework's M-mode trap handler reads mtval2 and mtinst, which exist only with H, "
        "so a trap in that state could not be reported. The file needs M-mode, so it requires Sm.",
        plan="1. misa bit 7 reads 1 on a hart with H.\n"
        "2. M-mode clears misa bit 7 (it may stay 1), then sets it again: it reads 1, and the other misa bits "
        "are unchanged by the round trip.\n"
        "3. With bit 7 set again, M-mode reads hstatus without a trap.",
    )
    lab = t.label("misa")
    t.emit(f"{lab}:", 0)
    t.emit("csrr x1, misa")
    t.emit("srli x8, x1, 7")
    t.emit("andi x8, x8, 1")
    t.check("x8", 0 if MUT == "misa_h_reads_0" else 1, lab, "misa.H reads 1 on a hart with H")
    lab = t.label("rt")
    t.li("x7", 0x80)
    t.emit(f"{lab}:", 0)
    t.emit("csrc misa, x7")
    t.emit("csrs misa, x7")
    t.emit("csrr x8, misa")
    eq(t, "x8", "x1", lab, "clearing and setting misa.H restores misa")
    t.window("M", [f"csrr x8, {hex(csr_num('hstatus'))}  // hstatus"], "ok", "hstatus read, misa.H=1")
    return t


def h_requires_i() -> TestFile:
    t = new("H_requires_i")
    t.describe(
        source=HYP,
        rule_text="The hypervisor extension depends on an I base integer ISA with 32 x registers (RV32I or "
        "RV64I), not RV32E or RV64E, which have only 16 x registers.",
        context="A hart with H therefore has x16-x31 in every mode. This is the one H test that uses registers "
        "above x15: it can only run on an I hart. x16-x31 are not used by the framework.",
        plan="1. VS-mode writes distinct values to x16-x31 and sums them into x7.\n"
        "2. HS-mode checks the sum and that x16 and x31 still hold their values after the trap that ends the "
        "window.",
    )
    lines = []
    for r in range(16, 32):
        lines.append(f"li x{r}, {r * 3 + 1}")
    lines.append("li x7, 0")
    for r in range(16, 32):
        lines.append(f"add x7, x7, x{r}")
    lab = t.window("VS", lines, "ok", "VS-mode use of x16-x31")
    t.check("x7", sum(r * 3 + 1 for r in range(16, 32)), lab, "the sum of x16-x31 written in VS-mode")
    t.check("x16", 49, lab, "x16 keeps its value")
    t.check("x31", 94, lab, "x31 keeps its value")
    return t
