# SPDX-License-Identifier: Apache-2.0
"""H suite: virtual-machine load/store instructions (HLV, HLVX, HSV), MPRV with MPV, VS endianness and
pointer masking for HLV/HSV.

Most tests run the hypervisor loads and stores in HS-mode, so the code itself is never translated: hgatp and
vsatp only affect the explicit access. Page tables and data pages come from hmem.py.
"""

# ruff: noqa: B023  (closures run immediately inside the loop that defines them)
from __future__ import annotations

from typing import TYPE_CHECKING

from aigen import X
from hlib import HYP, MUT, hlsv
from hmem import (
    G_OF,
    GPA_BASE,
    LEAF,
    LOAD_AF,
    LOAD_GPF,
    LOAD_MIS,
    LOAD_PF,
    MXR,
    PT,
    SPVP,
    STORE_AF,
    STORE_GPF,
    STORE_MIS,
    STORE_PF,
    SUM,
    ULEAF,
    VA_BASE,
    VS_OF,
    XP,
    A,
    MemTest,
    R,
    U,
    V,
    atp_off,
    bits,
    hgatp_on,
    memwin,
    new,
    s_mxr,
    s_sum,
    sig,
    spvp,
    vs_mxr,
    vs_sum,
    vsatp_on,
)

if TYPE_CHECKING:
    from aigen import Expect

MUTANTS = {
    "hlv_b_zext": "HLV.B zero-extends its result",
    "hlv_wu_sext": "HLV.WU / HLVX.WU sign-extend their result",
    "hlvx_needs_r": "HLVX needs read permission (not execute)",
    "hlvx_r_or_x": "HLVX accepts read or execute permission",
    "spvp_ignored": "HLV/HSV always use VS privilege, ignoring SPVP",
    "hs_sum_used": "HLV/HSV use HS-level sstatus.SUM instead of vsstatus.SUM",
    "vs_mxr_gstage": "vsstatus.MXR also overrides G-stage execute-only",
    "hs_mxr_vs_only": "HS-level sstatus.MXR only overrides VS-stage execute-only",
    "gva_zero": "a fault on HLV/HSV leaves hstatus.GVA = 0",
    "mprv_ignores_mpv": "MPRV with MPV=1 translates like HS-level (one stage)",
    "mprv_affects_hlv": "MPRV/MPP override HLV's effective privilege",
    "vsatp_v0_ignored_by_hlv": "HLV ignores vsatp while V=0",
    "hlvx_wu_rv32_illegal": "HLVX.WU is illegal on RV32",
    "hupmm_in_hs": "HLV in HS-mode with SPVP=0 masks pointers by hstatus.HUPMM, not senvcfg.PMM",
}

SAS = {"tval": None}


def tf(e: int, off: int = 0) -> int:
    """Transformed HLV/HLVX/HSV (rs1 field replaced by the address offset)."""
    return (e & ~(0x1F << 15)) | (off << 15)


def page_bytes(t: MemTest, name: str) -> bytearray:
    _, c = t.pages[f"ai_pg_{name}"]
    data = bytearray(4096)
    for o, (s, v) in c.items():
        data[o : o + s] = (v & ((1 << (8 * s)) - 1)).to_bytes(s, "little")
    return data


def ld_val(data: bytes, off: int, size: int, signed: bool, xlen: int) -> int:
    v = int.from_bytes(data[off : off + size], "little")
    if signed and v >> (8 * size - 1):
        v -= 1 << (8 * size)
    return v & ((1 << xlen) - 1)


def pf(cause: int, tval, e: int, gpa: int | None = None, implicit=False) -> dict:  # noqa: ANN001
    """Checks for a fault taken in HS-mode on an HLV/HLVX/HSV: xtval is 0 or the guest VA, GVA=1 when xtval is nonzero, htval is 0 (or
    GPA>>2 for a guest-page fault) and htinst is 0 or the transformed instruction (or, for a guest-page fault on
    an implicit VS-stage access, the pseudoinstruction: hmem.pseudo_required checks when it is mandatory)."""
    tinst = [0, tf(e)]
    if implicit:
        tinst.append(implicit if isinstance(implicit, X) else X(0x2000, 0x3000))
    ex = {"tval": tval, "gva": 0 if MUT == "gva_zero" else 1, "tinst": tinst}
    if cause not in (LOAD_GPF, STORE_GPF, 20):
        ex["tval2"] = 0
    elif gpa is not None:
        ex["tval2"] = [0, gpa >> 2]
    return {cause: ex}


def hl(
    t: MemTest,
    insn: str,
    va: int | str,
    desc: str,
    expect: Expect,
    value: int | None = None,
    rd: str = "x7",
    mode: str = "S",
    gpa: int | None = None,
    store_val: str = "x8",
    implicit: bool | X = False,
) -> str:
    """One HLV/HLVX/HSV in `mode` on address va (a constant, or a label expression whose address is used).
    expect: 'ok', a fault cause or a list. value: expected rd (loads, when no trap)."""
    if isinstance(va, int):
        t.emit(f"li x6, {hex(va)}")
    else:
        t.la("x6", va)
    store = insn.startswith("hsv")
    line, e = hlsv(insn, rd, "x6", store_val) if store else hlsv(insn, rd, "x6")
    alts = expect if isinstance(expect, list) else [expect]
    extras = {}
    for c in alts:
        if c in ("ok",):
            continue
        tval = va if isinstance(va, int) else X(va, va)
        if c in (LOAD_GPF, STORE_GPF):
            extras.update(pf(c, tval, e, gpa, implicit))
        else:
            extras.update(pf(c, tval, e))
    lab = memwin(t, mode, [line], expect, f"{insn} ({desc})", extras)
    if value is not None and alts == ["ok"]:
        t.check(rd, value, lab, f"{insn} ({desc}) loads {value if isinstance(value, str) else hex(value)}")
    return lab


def init(t: MemTest) -> None:
    t.comment("start: hgatp = vsatp = Bare, SPVP = 0, SUM = MXR = 0 at both levels")
    atp_off(t)
    spvp(t, False)
    for f in (s_sum, s_mxr, vs_sum, vs_mxr):
        f(t, False)


def fini(t: MemTest) -> None:
    t.blank()
    init(t)


# ---------------------------------------------------------------- table builders
def vs_only(t: MemTest, xlen: int, pages: list[tuple[int, str, int]]) -> PT:
    """VS-stage table (hgatp Bare): VA_BASE + k*4K -> page, with perms. Turns vsatp on."""
    v = PT(t, f"vs{xlen}", VS_OF[xlen], xlen)
    for k, name, perms in pages:
        v.leaf(VA_BASE[xlen] + k * 0x1000, t.page(name), perms)
    vsatp_on(t, v)
    return v


def g_only(t: MemTest, xlen: int, pages: list[tuple[int, str, int]]) -> PT:
    """G-stage table: image identity mapped, GPA_BASE + k*4K -> page with perms. Turns hgatp on (vsatp Bare)."""
    g = PT(t, f"g{xlen}", G_OF[xlen], xlen)
    g.identity(ULEAF)
    for k, name, perms in pages:
        g.leaf(GPA_BASE[xlen] + k * 0x1000, t.page(name), perms)
    hgatp_on(t, g)
    return g


def two_stage(t: MemTest, xlen: int, maps: list[tuple[int, int, int, str, int]]) -> tuple[PT, PT]:
    """VA_BASE+k*4K -VS perms-> GPA_BASE+j*4K -G perms-> page. maps: (k, vs_perms, j, page, g_perms).
    g_perms 0 leaves the GPA unmapped. The VS tables are in the identity-mapped image."""
    g = PT(t, f"g{xlen}", G_OF[xlen], xlen)
    g.identity(ULEAF)
    v = PT(t, f"vs{xlen}", VS_OF[xlen], xlen)
    for k, vp, j, name, gp in maps:
        gpa = GPA_BASE[xlen] + j * 0x1000
        v.leaf(VA_BASE[xlen] + k * 0x1000, gpa, vp)
        if gp:
            g.leaf(gpa, t.page(name), gp)
    hgatp_on(t, g)
    vsatp_on(t, v)
    return g, v


def both(t: MemTest, body) -> None:  # noqa: ANN001
    with t.rv64_only():
        body(64)
    with t.rv32_only():
        body(32)


# ---------------------------------------------------------------- tests
EXT = {
    0: (1, 0x80),
    1: (1, 0x7F),
    2: (2, 0x8001),
    4: (2, 0x7FFE),
    8: (4, 0x80000001),
    12: (4, 0x7FFFFFFE),
    16: (8, 0x8000000000000001),
    24: (8, 0x7FFFFFFFFFFFFFFE),
    32: (8, 0x0123456789ABCDEF),
    40: (8, 0xFEDCBA9876543210),
}
FILL = {o: (8, 0xAAAAAAAAAAAAAAAA) for o in range(0, 64, 8)}

LOADS = [
    ("hlv.b", 0),
    ("hlv.b", 1),
    ("hlv.bu", 0),
    ("hlv.bu", 1),
    ("hlv.h", 2),
    ("hlv.h", 4),
    ("hlv.hu", 2),
    ("hlv.hu", 4),
    ("hlv.w", 8),
    ("hlv.w", 12),
    ("hlv.wu", 8),
    ("hlv.wu", 12),
    ("hlv.d", 16),
    ("hlv.d", 24),
    ("hlv.d", 32),
    ("hlvx.hu", 2),
    ("hlvx.hu", 4),
    ("hlvx.wu", 8),
    ("hlvx.wu", 12),
    ("hlv.w", 40),
    ("hlv.h", 46),
    ("hlv.b", 47),
]


def gen_hlsv_op() -> MemTest:
    t = new("hlsv_op")
    t.describe(
        source=HYP,
        rule_text="For every RV32I or RV64I load instruction, LB, LBU, LH, LHU, LW, LWU, and LD, there is a "
        "corresponding virtual-machine load instruction: HLV.B, HLV.BU, HLV.H, HLV.HU, HLV.W, HLV.WU, and HLV.D. "
        "For every RV32I or RV64I store instruction, SB, SH, SW, and SD, there is a corresponding virtual-machine "
        "store instruction: HSV.B, HSV.H, HSV.W, and HSV.D. Instructions HLV.WU, HLV.D, and HSV.D are not valid "
        "for RV32, of course.",
        context="hgatp and vsatp are Bare, so guest virtual = guest physical = supervisor physical address, and "
        "the instructions run in HS-mode (valid there, hlsv_mode). HLVX.HU/WU are included: with Bare "
        "translation the page needs only the physical execute and read attributes of RAM. Misaligned accesses "
        "may succeed or raise address-misaligned or access-fault exceptions; a trap writes the guest virtual "
        "address to stval with hstatus.GVA=1 (https://github.com/riscv/riscv-isa-manual/issues/2695).",
        plan="1. Every load at byte offsets holding sign-boundary values (0x80/0x7F bytes, 0x8001/0x7FFE "
        "halves, 0x80000001/0x7FFFFFFE words, 2^63+1 and 2^63-2 doublewords, mixed patterns), with SPVP=0 and "
        "SPVP=1: the result is sign- or zero-extended to XLEN exactly as LB..LD would (HLV.WU and HLV.D RV64 "
        "only).\n"
        "2. rd = rs1 aliasing, and rd = x0 (no write, no trap).\n"
        "3. Each store (HSV.D RV64 only) over a page filled with 0xAA: an ordinary load shows that exactly the "
        "stored bytes changed.\n"
        "4. Misaligned HLV.H/HLV.W/HLV.D and HSV.W: no trap, or address-misaligned / access fault with "
        "stval 0 or the address, GVA=1 (with a nonzero stval), htval=0 and htinst 0 or the transformed instruction.",
    )
    init(t)
    pg = t.page("ext", EXT)
    st = t.page("st", FILL)
    data = page_bytes(t, "ext")
    for sp in (0, 1):
        spvp(t, bool(sp))
        for insn, off in LOADS:
            _, _, size, signed, rv64 = __import__("hlib").HLSV[insn]

            def body(xlen: int, insn: str = insn, off: int = off, size: int = size, signed: bool = signed) -> None:
                sgn = signed
                if MUT == "hlv_b_zext" and insn == "hlv.b":
                    sgn = False
                if MUT == "hlv_wu_sext" and insn in ("hlv.wu", "hlvx.wu"):
                    sgn = True
                hl(t, insn, f"{pg}+{off}", f"offset {off}, SPVP={sp}", "ok", ld_val(data, off, size, sgn, xlen))

            if rv64:
                with t.rv64_only():
                    body(64)
            else:
                both(t, body)
    spvp(t, False)
    # aliasing and x0
    t.comment("rd = rs1")
    t.la("x6", f"{pg}+8")
    line, _ = hlsv("hlv.w", "x6", "x6")
    lab = memwin(t, "S", [line], "ok", "hlv.w x6, (x6)")
    both(t, lambda xlen: t.check("x6", ld_val(data, 8, 4, True, xlen), lab, "hlv.w with rd = rs1"))
    t.la("x6", pg)
    line, _ = hlsv("hlv.w", "x0", "x6")
    memwin(t, "S", [line], "ok", "hlv.w x0, (x6): no write, no trap")
    # stores
    for insn, off, val in (
        ("hsv.b", 3, 0x5C),
        ("hsv.h", 10, 0x1234),
        ("hsv.w", 20, 0x89ABCDEF),
        ("hsv.d", 40, 0x0F1E2D3C4B5A6978),
    ):
        size = __import__("hlib").HLSV[insn][2]

        def sbody(xlen: int, insn: str = insn, off: int = off, val: int = val, size: int = size) -> None:
            t.load("x8", val & ((1 << xlen) - 1), "value to store")
            lab = hl(t, insn, f"{st}+{off}", "aligned", "ok")
            word = off & ~(xlen // 8 - 1)
            new = bytearray(b"\xaa" * 64)
            new[off : off + size] = (val & ((1 << (8 * size)) - 1)).to_bytes(size, "little")
            t.la("x6", f"{st}+{word}")
            t.emit("LREG x7, 0(x6)")
            t.check(
                "x7",
                int.from_bytes(new[word : word + xlen // 8], "little"),
                lab,
                f"{insn}: memory holds exactly the stored bytes",
            )
            t.load("x7", 0xAAAAAAAAAAAAAAAA & ((1 << xlen) - 1), "restore 0xAA fill")
            t.emit("SREG x7, 0(x6)")

        if insn == "hsv.d":
            with t.rv64_only():
                sbody(64)
        else:
            both(t, sbody)
    # misaligned
    for insn, off in (("hlv.h", 1), ("hlv.w", 2), ("hlv.d", 4), ("hsv.w", 1)):
        rv64 = __import__("hlib").HLSV[insn][4]
        cause = [STORE_MIS, STORE_AF] if insn.startswith("hsv") else [LOAD_MIS, LOAD_AF]

        def mbody(xlen: int, insn: str = insn, off: int = off, cause: list = cause) -> None:
            t.emit("li x8, 0")
            hl(t, insn, f"{st}+{off}", "misaligned", ["ok", *cause])

        if rv64:
            with t.rv64_only():
                mbody(64)
        else:
            both(t, mbody)
    fini(t)
    return t


def gen_hlvx() -> MemTest:
    t = new("hlsv_u_op")
    t.describe(
        source=HYP,
        rule_text="Instructions HLVX.HU and HLVX.WU are the same as HLV.HU and HLV.WU, except that execute "
        "permission takes the place of read permission during address translation. That is, the memory being "
        "read must be executable in both stages of address translation, but read permission is not required. "
        "For the supervisor physical address that results from address translation, the supervisor physical "
        "memory attributes must grant both execute and read permissions.",
        context="HLVX is a load: its faults are load page faults (13) and load guest-page faults (21) "
        "(https://github.com/riscv/riscv-isa-manual/issues/682: read permission does not factor into the check "
        "at all). Its transformed htinst keeps bits 24:20 = 00011 "
        "(https://github.com/riscv/riscv-isa-manual/issues/1286). MXR makes executable pages readable for "
        "loads, but never makes a readable page executable, so it does not help HLVX.",
        plan="1. VS-stage (hgatp Bare, SPVP=1): pages execute-only, read-only and read+execute. HLVX.HU/WU "
        "read the execute-only and read+execute pages (zero-extended, including bit 31 of a word on RV64) and "
        "raise a load page fault on the read-only page; HLV.W raises a load page fault on the execute-only page "
        "and reads the read-only page.\n"
        "2. The read-only page with vsstatus.MXR=1 and sstatus.MXR=1: HLVX still faults.\n"
        "3. G-stage (vsatp Bare): the same three page types at G-stage; HLVX reads execute-only and "
        "read+execute, and raises a load guest-page fault (htval 0 or GPA>>2) on read-only; HLV.W raises a load "
        "guest-page fault on execute-only.\n"
        "Every fault checks stval = the guest address, GVA=1 and htinst 0 or the transformed HLVX.",
    )
    init(t)
    word = {8: (4, 0x89ABCDEF)}
    names = [("x", XP), ("r", R), ("rx", R | XP)]
    for n, _ in names:
        t.page(f"hx_{n}", word)
    needs_x = MUT != "hlvx_needs_r"

    def ok_hlvx(p: int) -> bool:
        if MUT == "hlvx_r_or_x":
            return bool(p & (R | XP))
        return bool(p & XP) if needs_x else bool(p & R)

    def body(xlen: int) -> None:
        vs_only(t, xlen, [(k, f"hx_{n}", V | p | A) for k, (n, p) in enumerate(names)])
        spvp(t, True)
        for k, (n, p) in enumerate(names):
            va = VA_BASE[xlen] + k * 0x1000
            for insn, off, val in (("hlvx.hu", 8, 0xCDEF), ("hlvx.wu", 8, 0x89ABCDEF), ("hlv.w", 0, None)):
                okk = ok_hlvx(p) if insn.startswith("hlvx") else bool(p & R)
                if val is None:
                    val = sig(t.page_id(f"hx_{n}")) & 0xFFFFFFFF
                    val = val - (1 << 32) if val >> 31 else val
                if MUT == "hlv_wu_sext" and insn == "hlvx.wu":
                    val = val - (1 << 32)
                hl(
                    t,
                    insn,
                    va + off,
                    f"VS-stage {n} page, SPVP=1",
                    "ok" if okk else LOAD_PF,
                    (val & ((1 << xlen) - 1)) if okk else None,
                )
        vs_mxr(t, True)
        s_mxr(t, True)
        hl(
            t,
            "hlvx.wu",
            VA_BASE[xlen] + 0x1000 + 8,
            "VS-stage read-only page, both MXR=1",
            "ok" if MUT == "hlvx_r_or_x" else LOAD_PF,
        )
        vs_mxr(t, False)
        s_mxr(t, False)
        atp_off(t)
        g_only(t, xlen, [(k, f"hx_{n}", V | U | p | A) for k, (n, p) in enumerate(names)])
        for k, (n, p) in enumerate(names):
            gpa = GPA_BASE[xlen] + k * 0x1000
            for insn, off, val in (("hlvx.wu", 8, 0x89ABCDEF), ("hlv.w", 0, None)):
                okk = ok_hlvx(p) if insn.startswith("hlvx") else bool(p & R)
                if val is None:
                    val = sig(t.page_id(f"hx_{n}")) & 0xFFFFFFFF
                if MUT == "hlv_wu_sext" and insn == "hlvx.wu":
                    val = val - (1 << 32)
                hl(
                    t,
                    insn,
                    gpa + off,
                    f"G-stage {n} page",
                    "ok" if okk else LOAD_GPF,
                    (val & ((1 << xlen) - 1)) if okk else None,
                    gpa=gpa + off,
                )
        atp_off(t)

    both(t, body)
    fini(t)
    return t


def gen_hlvx32() -> MemTest:
    t = new("hlvx-wu_valid32")
    t.describe(
        source=HYP,
        rule_text="HLVX.WU is valid for RV32, even though LWU and HLV.WU are not.",
        context="RV32 only; on RV64 the file has no checks (HLVX.WU there is covered by hlsv_u_op).",
        plan="1. RV32, hgatp and vsatp Bare: HLVX.WU reads a word with bit 31 set, with SPVP=0 and 1.\n"
        "2. RV32: HLV.WU, HLV.D and HSV.D raise illegal-instruction (xtval 0 or the instruction bits).",
    )
    with t.rv32_only():
        init(t)
        pg = t.page("w", {4: (4, 0x89ABCDEF)})
        for sp in (0, 1):
            spvp(t, bool(sp))
            exp = 2 if MUT == "hlvx_wu_rv32_illegal" else "ok"
            if exp == "ok":
                hl(t, "hlvx.wu", f"{pg}+4", f"RV32, SPVP={sp}", "ok", 0x89ABCDEF)
            else:
                t.la("x6", f"{pg}+4")
                line, e = hlsv("hlvx.wu", "x7", "x6")
                memwin(t, "S", [line], 2, "hlvx.wu RV32", {2: {"tval": [0, e]}})
        spvp(t, False)
        for insn in ("hlv.wu", "hlv.d", "hsv.d"):
            t.la("x6", pg)
            line, e = hlsv(insn, "x7", "x6", "x8") if insn.startswith("hsv") else hlsv(insn, "x7", "x6")
            memwin(t, "S", [line], 2, f"{insn} is not valid on RV32", {2: {"tval": [0, e]}})
        fini(t)
    return t


def gen_priv() -> list[MemTest]:
    tests = []
    for rule in ("hlsv_priv", "hstatus_spvp_virtls_op"):
        t = new(rule)
        if rule == "hlsv_priv":
            t.describe(
                source=HYP,
                rule_text="Each instruction performs an explicit memory access with an effective privilege mode "
                "of VS or VU. The effective privilege mode of the explicit memory access is VU when "
                "hstatus.SPVP=0, and VS when hstatus.SPVP=1.",
                context="VS-stage translation (hgatp Bare) with a supervisor page (U=0) and a user page (U=1), "
                "both readable, writable and executable. As for VS-mode and VU-mode, a VU access to a "
                "supervisor page faults, and a VS access to a user page needs vsstatus.SUM=1 (also for HLVX, "
                "a load: https://github.com/riscv/riscv-isa-manual/issues/1480). The effective privilege does "
                "not depend on the mode executing the instruction, so U-mode with hstatus.HU=1 is included.",
                plan="1. HS-mode, SPVP=0: HLV.W/HSV.W/HLVX.WU succeed on the user page and raise load/store page "
                "faults on the supervisor page.\n"
                "2. HS-mode, SPVP=1: they succeed on the supervisor page; on the user page they fault with "
                "vsstatus.SUM=0 and succeed with SUM=1.\n"
                "3. U-mode with hstatus.HU=1: the same split by SPVP (U-mode itself may never touch the "
                "supervisor page, but the HLV runs as VS).\n"
                "Faults check stval, GVA=1, htval=0 and htinst.",
            )
        else:
            t.describe(
                source=HYP,
                rule_text="SPVP controls the effective privilege of explicit memory accesses made by the "
                "virtual-machine load/store instructions, HLV, HLVX, and HSV.",
                context="See hlsv_priv for the page setup. This test sweeps every load width and every store "
                "width over both privileges, and checks that the instructions leave SPVP unchanged.",
                plan="1. For SPVP = 0, 1, 0: each HLV/HLVX/HSV width on the supervisor and the user page "
                "(vsstatus.SUM=0): VU accesses succeed only on the user page and VS accesses only on the "
                "supervisor page; the others raise load or store page faults.\n"
                "2. After each pass, hstatus.SPVP still holds the value written.",
            )
        init(t)
        t.page("sp")
        t.page("up")

        def body(xlen: int, rule: str = rule, t: MemTest = t) -> None:
            vs_only(t, xlen, [(0, "sp", LEAF), (1, "up", LEAF | U)])
            vas, vau = VA_BASE[xlen], VA_BASE[xlen] + 0x1000
            sgs = {vas: sig(t.page_id("sp")), vau: sig(t.page_id("up"))}

            def okp(sp: int, user: bool, sumb: int) -> bool:
                eff = 1 if MUT == "spvp_ignored" else sp
                if eff == 0:
                    return user
                return (not user) or bool(sumb)

            def lv(v: int) -> int:
                w = v & 0xFFFFFFFF
                return (w - (1 << 32) if w >> 31 else w) & ((1 << xlen) - 1)

            if rule == "hlsv_priv":
                for mode in ("S", "U"):
                    if mode == "U":
                        bits(t, 0x600, "hstatus.HU", 1 << 9, True)
                    for sp in (0, 1):
                        spvp(t, bool(sp))
                        for sumb in (0,) if sp == 0 else (0, 1):
                            vs_sum(t, bool(sumb))
                            s_sum(t, bool(1 - sumb))  # the HS-level SUM is the opposite, and ignored
                            eff_sum = (1 - sumb) if MUT == "hs_sum_used" else sumb
                            for va, user in ((vas, False), (vau, True)):
                                okk = okp(sp, user, eff_sum)
                                d = f"SPVP={sp}, vsstatus.SUM={sumb}, {'user' if user else 'supervisor'} page"
                                hl(t, "hlv.w", va, d, "ok" if okk else LOAD_PF, lv(sgs[va]) if okk else None, mode=mode)
                                t.emit("li x8, 0x77")
                                hl(t, "hsv.b", va + 16, d, "ok" if okk else STORE_PF, mode=mode)
                                if mode == "S":
                                    hl(
                                        t,
                                        "hlvx.wu",
                                        va,
                                        d,
                                        "ok" if okk else LOAD_PF,
                                        (sgs[va] & 0xFFFFFFFF) if okk else None,
                                    )
                    if mode == "U":
                        bits(t, 0x600, "hstatus.HU", 1 << 9, False)
                vs_sum(t, False)
                s_sum(t, False)
            else:
                ins = [
                    "hlv.b",
                    "hlv.bu",
                    "hlv.h",
                    "hlv.hu",
                    "hlvx.hu",
                    "hlv.w",
                    "hlvx.wu",
                    "hsv.b",
                    "hsv.h",
                    "hsv.w",
                ] + (["hlv.wu", "hlv.d", "hsv.d"] if xlen == 64 else [])
                for sp in (0, 1, 0):
                    spvp(t, bool(sp))
                    for va, user in ((vas, False), (vau, True)):
                        okk = okp(sp, user, 0)
                        for insn in ins:
                            st = insn.startswith("hsv")
                            if st:
                                t.emit("li x8, 0")
                            exp = "ok" if okk else (STORE_PF if st else LOAD_PF)
                            hl(t, insn, va + 32, f"SPVP={sp}, {'user' if user else 'supervisor'} page", exp)
                    lab = t.label("spvp")
                    t.emit(f"{lab}:", 0)
                    t.emit("csrr x7, 0x600  // hstatus")
                    t.check_masked("x7", SPVP, SPVP * sp, lab, "HLV/HLVX/HSV leave hstatus.SPVP unchanged")
            atp_off(t)

        both(t, body)
        fini(t)
        tests.append(t)
    return tests


def gen_trans() -> MemTest:
    t = new("hlsv_trans")
    t.describe(
        source=HYP,
        rule_text="As usual for VS-mode and VU-mode, two-stage address translation is applied, and the HS-level "
        "sstatus.SUM is ignored.",
        context="VS-stage tables sit in the identity-mapped test image (GPA = PA). Two guest virtual pages map "
        "crosswise through the stages (VA0 -> GPA1 -> page B, VA1 -> GPA0 -> page A), so a design that skips "
        "either stage or applies them in the wrong order reads the wrong page. A third VA maps to a GPA with "
        "no G-stage mapping.",
        plan="1. HLV.W/HLV.D (RV64) read page B through VA0 and page A through VA1; HSV.W through VA0 lands in "
        "page B (checked with an ordinary load).\n"
        "2. VA2 (VS-stage valid, G-stage unmapped): HLV.W raises a load guest-page fault, not a page fault, "
        "with stval 0 or VA2, htval = 0 or GPA2>>2, GVA=1 (with a nonzero stval).\n"
        "3. SPVP=1, user page (U=1): sstatus.SUM=1 with vsstatus.SUM=0 faults; sstatus.SUM=0 with "
        "vsstatus.SUM=1 succeeds.",
    )
    init(t)
    t.page("A")
    t.page("B")
    t.page("C")

    def body(xlen: int) -> None:
        two_stage(
            t,
            xlen,
            [
                (0, LEAF | U, 1, "B", ULEAF),
                (1, LEAF | U, 0, "A", ULEAF),
                (2, LEAF | U, 2, "C", 0),
                (3, LEAF, 3, "C", ULEAF),
            ],
        )
        va = VA_BASE[xlen]
        sa, sb = sig(t.page_id("A")), sig(t.page_id("B"))
        lw = lambda v: (v & 0xFFFFFFFF) - ((v >> 31 & 1) << 32)
        hl(t, "hlv.w", va, "VA0 -> GPA1 -> page B", "ok", lw(sb) & ((1 << xlen) - 1))
        hl(t, "hlv.w", va + 0x1000, "VA1 -> GPA0 -> page A", "ok", lw(sa) & ((1 << xlen) - 1))
        if xlen == 64:
            hl(t, "hlv.d", va, "VA0 -> GPA1 -> page B", "ok", sb)
        t.load("x8", 0x13572468, "value")
        lab = hl(t, "hsv.w", va + 8, "VA0 -> GPA1 -> page B", "ok")
        t.la("x6", f"{t.page('B')}+8")
        t.emit("lw x7, 0(x6)")
        t.check("x7", 0x13572468, lab, "hsv.w through VA0 lands in page B")
        hl(t, "hlv.w", va + 0x2000, "VA2 -> GPA2, no G-stage mapping", LOAD_GPF, gpa=GPA_BASE[xlen] + 0x2000)
        spvp(t, True)
        s_sum(t, True)
        hl(
            t,
            "hlv.w",
            va,
            "user page, SPVP=1, sstatus.SUM=1, vsstatus.SUM=0",
            "ok" if MUT == "hs_sum_used" else LOAD_PF,
        )
        s_sum(t, False)
        vs_sum(t, True)
        hl(
            t,
            "hlv.w",
            va,
            "user page, SPVP=1, sstatus.SUM=0, vsstatus.SUM=1",
            LOAD_PF if MUT == "hs_sum_used" else "ok",
        )
        vs_sum(t, False)
        spvp(t, False)
        atp_off(t)

    both(t, body)
    fini(t)
    return t


def gen_mxr() -> list[MemTest]:
    tests = []
    for rule in ("hlsv_sstatus_mxr", "hlsv_vsstatus_mxr"):
        t = new(rule)
        hs = rule == "hlsv_sstatus_mxr"
        t.describe(
            source=HYP,
            rule_text="HS-level sstatus.MXR makes execute-only pages readable by explicit loads for both stages "
            "of address translation (VS-stage and G-stage)"
            if hs
            else "vsstatus.MXR affects only the first translation stage (VS-stage).",
            context="Three guest pages: execute-only at VS-stage only, execute-only at G-stage only, and "
            "execute-only at both. A VS-stage permission failure is a load page fault (13) and is found before "
            "G-stage translation of the final address; a G-stage failure is a load guest-page fault (21).",
            plan="For (sstatus.MXR, vsstatus.MXR) in "
            + ("(0,0), (1,0), (1,1)" if hs else "(0,0), (0,1), (1,1)")
            + ", HLV.W on each page: VS-only X: readable if either MXR is set, else 13; G-only X: readable only "
            "with sstatus.MXR, else 21; both X: readable with sstatus.MXR, 21 with only vsstatus.MXR, 13 with "
            "neither. Faults check stval, GVA=1, htval (0 or GPA>>2 for 21, 0 for 13) and htinst.",
        )
        init(t)
        for n in ("vx", "gx", "bx"):
            t.page(n)

        def body(xlen: int, t: MemTest = t, hs: bool = hs) -> None:
            two_stage(
                t,
                xlen,
                [
                    (0, V | XP | A, 0, "vx", ULEAF),
                    (1, LEAF, 1, "gx", V | U | XP | A),
                    (2, V | XP | A, 2, "bx", V | U | XP | A),
                ],
            )
            spvp(t, True)  # VS-level accesses (the pages are supervisor pages)
            for sm, vm in ((0, 0), (1, 0), (1, 1)) if hs else ((0, 0), (0, 1), (1, 1)):
                s_mxr(t, bool(sm))
                vs_mxr(t, bool(vm))
                for k, n in enumerate(("vx", "gx", "bx")):
                    vs_x = n in ("vx", "bx")
                    g_x = n in ("gx", "bx")
                    vs_ok = (not vs_x) or sm or vm
                    g_ok = (not g_x) or sm or (MUT == "vs_mxr_gstage" and vm)
                    if MUT == "hs_mxr_vs_only" and g_x and not (MUT == "vs_mxr_gstage" and vm):
                        g_ok = not g_x
                    exp = "ok" if vs_ok and g_ok else (LOAD_PF if not vs_ok else LOAD_GPF)
                    v = sig(t.page_id(n)) & 0xFFFFFFFF
                    hl(
                        t,
                        "hlv.w",
                        VA_BASE[xlen] + k * 0x1000,
                        f"{n} page, sstatus.MXR={sm}, vsstatus.MXR={vm}",
                        exp,
                        v if exp == "ok" else None,
                        gpa=GPA_BASE[xlen] + k * 0x1000,
                    )
            atp_off(t)

        both(t, body)
        fini(t)
        tests.append(t)
    return tests


def gen_v0() -> list[MemTest]:
    tests = []
    t = new("vsstatus_v0")
    t.describe(
        source=HYP,
        rule_text="When V=0, vsstatus does not directly affect the behavior of the machine, unless a "
        "virtual-machine load/store (HLV, HLVX, or HSV) or the MPRV feature in the mstatus register is used to "
        "execute a load or store as though V=1.",
        context="VS-stage translation (hgatp Bare) with a user page. HS-mode's own loads use no translation "
        "(satp Bare), so the observable HS-mode behavior is ordinary loads and stores; the HLV exception is "
        "observable through vsstatus.SUM and vsstatus.MXR. The MPRV exception is covered by "
        "mstatus_mprv_hypervisor.",
        plan="1. vsstatus.SUM=MXR=1 and SIE=1: HS-mode loads and stores to the data pages work as usual and no "
        "interrupt is taken.\n"
        "2. The HLV exception: with SPVP=1, HLV.W on a user page faults with vsstatus.SUM=0 and succeeds with "
        "SUM=1; HLV.W on an execute-only VS page faults with vsstatus.MXR=0 and succeeds with MXR=1.",
    )
    init(t)
    t.page("up")
    t.page("xo")

    def body(xlen: int) -> None:
        vs_only(t, xlen, [(0, "up", LEAF | U), (1, "xo", V | XP | A)])
        bits(t, 0x200, "vsstatus.SUM|MXR|SIE", SUM | MXR | 2, True)
        lab = t.label("hs")
        t.la("x6", t.page("up"))
        t.emit(f"{lab}:", 0)
        t.emit("lw x7, 0(x6)")
        t.check("x7", sig(t.page_id("up")) & 0xFFFFFFFF, lab, "an HS-mode load is unaffected by vsstatus")
        bits(t, 0x200, "vsstatus.SIE", 2, False)
        spvp(t, True)
        u, x = VA_BASE[xlen], VA_BASE[xlen] + 0x1000
        for on in (0, 1):
            vs_sum(t, bool(on))
            vs_mxr(t, bool(on))
            hl(
                t,
                "hlv.w",
                u,
                f"user page, SPVP=1, vsstatus.SUM={on}",
                "ok" if on else LOAD_PF,
                (sig(t.page_id("up")) & 0xFFFFFFFF) if on else None,
            )
            hl(
                t,
                "hlv.w",
                x,
                f"execute-only page, vsstatus.MXR={on}",
                "ok" if on else LOAD_PF,
                (sig(t.page_id("xo")) & 0xFFFFFFFF) if on else None,
            )
        spvp(t, False)
        atp_off(t)

    both(t, body)
    fini(t)
    tests.append(t)

    t = new("vsatp_v0")
    t.describe(
        source=HYP,
        rule_text="When V=0, vsatp does not directly affect the behavior of the machine, unless a virtual-machine "
        "load/store (HLV, HLVX, or HSV) or the MPRV feature in the mstatus register is used to execute a load "
        "or store as though V=1.",
        context="vsatp selects a VS-stage table that maps guest virtual page VA to page B, and VA' to nothing; "
        "the page at physical address A is another data page. HS-mode code and its own accesses keep running "
        "untranslated.",
        plan="1. With vsatp active, HS-mode keeps executing and an HS-mode load of page A's physical address "
        "reads page A.\n"
        "2. HLV.W of VA reads page B, HSV.W of VA writes page B; HLV.W of the unmapped VA' raises a load page "
        "fault.\n"
        "3. With vsatp Bare again, HLV.W of page A's physical address reads page A.",
    )
    init(t)
    t.page("A")
    t.page("B")

    def body2(xlen: int) -> None:
        v = vs_only(t, xlen, [(0, "B", LEAF)])
        del v
        lab = t.label("hs")
        t.la("x6", t.page("A"))
        t.emit(f"{lab}:", 0)
        t.emit("lw x7, 0(x6)")
        t.check("x7", sig(t.page_id("A")) & 0xFFFFFFFF, lab, "HS-mode loads are untranslated with vsatp active")
        spvp(t, True)
        sb = sig(t.page_id("B")) & 0xFFFFFFFF
        hl(t, "hlv.wu" if xlen == 64 else "hlv.w", VA_BASE[xlen], "VA through vsatp", "ok", sb)
        t.load("x8", 0x2468ACE, "value")
        lab = hl(t, "hsv.w", VA_BASE[xlen] + 4, "VA through vsatp", "ok")
        t.la("x6", f"{t.page('B')}+4")
        t.emit("lw x7, 0(x6)")
        t.check("x7", 0x2468ACE, lab, "hsv.w through vsatp lands in page B")
        hl(t, "hlv.w", VA_BASE[xlen] + 0x5000, "unmapped VA'", "ok" if MUT == "vsatp_v0_ignored_by_hlv" else LOAD_PF)
        atp_off(t)
        hl(t, "hlv.w", t.page("A"), "vsatp Bare: physical address of page A", "ok", sig(t.page_id("A")) & 0xFFFFFFFF)
        spvp(t, False)

    both(t, body2)
    fini(t)
    tests.append(t)
    return tests


# ---------------------------------------------------------------- MPRV (M-mode tests)
MPRV = 1 << 17


def mpp_mpv(t: MemTest, mpp: int, mpv: int) -> None:
    t.emit("li x7, 0x1800")
    t.emit("csrc mstatus, x7  // MPP = 0")
    if mpp:
        t.emit(f"li x7, {hex(mpp << 11)}")
        t.emit(f"csrs mstatus, x7  // MPP = {mpp}")
    with t.rv64_only():
        t.emit("li x7, 1")
        t.emit("slli x7, x7, 39")
        t.emit(f"{'csrs' if mpv else 'csrc'} mstatus, x7  // MPV = {mpv}")
    with t.rv32_only():
        t.emit("li x7, 0x80")
        t.emit(f"{'csrs' if mpv else 'csrc'} 0x310, x7  // mstatush.MPV = {mpv}")


def mprv_load(
    t: MemTest,
    va: int | str,
    mpp: int,
    mpv: int,
    expect: Expect,
    desc: str,
    value: int | None = None,
    gpa: int | None = None,
    hlv: bool = False,
) -> None:
    """In M-mode: set MPP/MPV, then MPRV=1, one lw (or HLV.W when hlv), MPRV=0, in a trap window."""
    mpp_mpv(t, mpp, mpv)
    if isinstance(va, int):
        t.emit(f"li x6, {hex(va)}")
    else:
        t.la("x6", va)
    t.emit(f"li x9, {hex(MPRV)}")
    lab = t.label("mprv")
    t.allow(1)
    t.emit("csrs mstatus, x9  // MPRV = 1")
    t.emit(f"{lab}:", 0)
    if hlv:
        line, e = hlsv("hlv.w", "x7", "x6")
        t.emit(line)
    else:
        t.emit("lw x7, 0(x6)")
        e = 0x00032383
    t.emit("csrc mstatus, x9  // MPRV = 0")
    alts = expect if isinstance(expect, list) else [expect]
    tval = va if isinstance(va, int) else X(va, va)
    extras = {}
    for c in alts:
        if c == "ok":
            continue
        extras[c] = {"tval": tval, "gva": 1, "tinst": [0, tf(e)], "tval2": 0 if gpa is None else [0, gpa >> 2]}
    t.outcome2(
        expect,
        lab,
        f"{'hlv.w' if hlv else 'lw'} with MPRV=1, MPP={mpp}, MPV={mpv} ({desc})",
        extras,
        origin="M",
        handler="M",
    )
    if value is not None and alts == ["ok"]:
        t.check("x7", value, lab, f"{desc}: loads {hex(value)}")
    mpp_mpv(t, 0, 0)


def gen_mprv() -> list[MemTest]:
    tests = []
    req = ["I", "S", "H", "Sm"]
    t = new("mstatus_mprv_hypervisor", req, boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="The hypervisor extension changes the behavior of the Modify Privilege field, MPRV, of mstatus. "
        "When MPRV=0, translation and protection behave as normal. When MPRV=1, explicit memory accesses are "
        "translated and protected, and endianness is applied, as though the current virtualization mode were set "
        "to MPV and the current nominal privilege mode were set to MPP. <<h-mprv>> enumerates the cases.",
        context="Per <<h-mprv>>: MPV=1 gives two-stage translation, vsstatus.SUM applies instead of HS-level SUM, "
        "HS-level MXR makes any executable page readable, and vsstatus.MXR does so only for pages readable at "
        "G-stage; MPP=3 means M-level access with no translation, whatever MPV. A load fault taken with MPV=1 "
        "writes a guest virtual address, so mstatus.GVA=1 "
        "(https://github.com/riscv/riscv-isa-manual/issues/2695). The test runs in M-mode; satp is Bare, so "
        "HS-level translation is the identity.",
        plan="1. Pages: VA_S -> supervisor page A, VA_U -> user page B, VA_X -> VS execute-only page X, VA_G -> "
        "page G that is execute-only at G-stage, VA_N -> a GPA with no G-stage mapping. Physical page C is "
        "outside the VS map.\n"
        "2. MPV=1, MPP=1: VA_S reads A; VA_U faults (13) with vsstatus.SUM=0 even with mstatus.SUM=1, and "
        "reads B with vsstatus.SUM=1; VA_N raises 21 with mtval2 0 or GPA>>2 and mtinst 0 or the transformed "
        "lw; VA_X faults with neither MXR, reads with either; VA_G reads with mstatus.MXR=1 and raises 21 with "
        "only vsstatus.MXR=1.\n"
        "3. MPV=1, MPP=0: VA_U reads B, VA_S faults (13).\n"
        "4. MPV=0, MPP=0 and 1: page C's physical address reads C (one-stage, Bare).\n"
        "5. MPP=3 with MPV=1: page C's physical address reads C (no translation).\n"
        "Every fault checks mtval, mstatus.GVA=1, mtval2 and mtinst.",
    )
    for n in ("A", "B", "X", "G", "N", "C"):
        t.page(n)

    def body(xlen: int) -> None:
        atp_off(t)
        two_stage(
            t,
            xlen,
            [
                (0, LEAF, 0, "A", ULEAF),
                (1, LEAF | U, 1, "B", ULEAF),
                (2, V | XP | A, 2, "X", ULEAF),
                (3, LEAF, 3, "G", V | U | XP | A),
                (4, LEAF, 4, "N", 0),
            ],
        )
        va = VA_BASE[xlen]
        gp = GPA_BASE[xlen]
        s = {n: sig(t.page_id(n)) & 0xFFFFFFFF for n in ("A", "B", "X", "G", "C")}
        one = MUT == "mprv_ignores_mpv"
        mprv_load(t, va, 1, 1, LOAD_AF if one else "ok", "VA_S, two-stage", None if one else s["A"])
        bits(t, 0x300, "mstatus.SUM", SUM, True)
        mprv_load(t, va + 0x1000, 1, 1, LOAD_AF if one else LOAD_PF, "VA_U, vsstatus.SUM=0, mstatus.SUM=1")
        bits(t, 0x300, "mstatus.SUM", SUM, False)
        vs_sum(t, True)
        mprv_load(t, va + 0x1000, 1, 1, LOAD_AF if one else "ok", "VA_U, vsstatus.SUM=1", None if one else s["B"])
        vs_sum(t, False)
        if not one:
            mprv_load(t, va + 0x4000, 1, 1, LOAD_GPF, "VA_N, no G-stage mapping", gpa=gp + 0x4000)
            for mm, vm in ((0, 0), (1, 0), (0, 1)):
                bits(t, 0x300, "mstatus.MXR", MXR, bool(mm))
                vs_mxr(t, bool(vm))
                okx = bool(mm or vm)
                mprv_load(
                    t,
                    va + 0x2000,
                    1,
                    1,
                    "ok" if okx else LOAD_PF,
                    f"VA_X, MXR={mm}, vsstatus.MXR={vm}",
                    s["X"] if okx else None,
                )
                mprv_load(
                    t,
                    va + 0x3000,
                    1,
                    1,
                    "ok" if mm else LOAD_GPF,
                    f"VA_G, MXR={mm}, vsstatus.MXR={vm}",
                    s["G"] if mm else None,
                    gpa=gp + 0x3000,
                )
            bits(t, 0x300, "mstatus.MXR", MXR, False)
            vs_mxr(t, False)
            mprv_load(t, va + 0x1000, 0, 1, "ok", "VA_U from VU", s["B"])
            mprv_load(t, va, 0, 1, LOAD_PF, "VA_S from VU")
        for mpp in (0, 1):
            mprv_load(t, t.page("C"), mpp, 0, "ok", "physical address of page C, one-stage Bare", s["C"])
        mprv_load(t, t.page("C"), 3, 1, "ok", "physical address of page C, MPP=3 ignores MPV", s["C"])
        atp_off(t)

    both(t, body)
    tests.append(t)

    t = new("mstatus_mprv_hlsv", req, boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="MPRV does not affect the virtual-machine load/store instructions, HLV, HLVX, and HSV. The "
        "explicit loads and stores of these instructions always act as though V=1 and the nominal privilege "
        "mode were hstatus.SPVP, overriding MPRV.",
        context="M-mode test (HLV is valid in M-mode, hlsv_mode). Two-stage maps: VA_S -> supervisor page A, "
        "VA_U -> user page B.",
        plan="1. MPRV=1 with MPV=0, MPP=0 (U-level, one-stage Bare): HLV.W of VA_S with SPVP=1 still reads A "
        "through both stages.\n"
        "2. MPRV=1, MPV=1, MPP=1 (VS-level): HLV.W of VA_S with SPVP=0 raises a load page fault (VU access to "
        "a supervisor page), and of VA_U reads B.\n"
        "3. MPRV=1, MPP=3: HLV.W of VA_S with SPVP=1 reads A (still translated).",
    )
    t.page("A")
    t.page("B")

    def body2(xlen: int) -> None:
        atp_off(t)
        two_stage(t, xlen, [(0, LEAF, 0, "A", ULEAF), (1, LEAF | U, 1, "B", ULEAF)])
        va = VA_BASE[xlen]
        sa, sb = sig(t.page_id("A")) & 0xFFFFFFFF, sig(t.page_id("B")) & 0xFFFFFFFF
        bad = MUT == "mprv_affects_hlv"
        spvp(t, True)
        mprv_load(t, va, 0, 0, LOAD_PF if bad else "ok", "SPVP=1, MPRV U-level", None if bad else sa, hlv=True)
        spvp(t, False)
        mprv_load(
            t,
            va,
            1,
            1,
            "ok" if bad else LOAD_PF,
            "SPVP=0, MPRV VS-level, supervisor page",
            sa if bad else None,
            hlv=True,
        )
        mprv_load(
            t,
            va + 0x1000,
            1,
            1,
            LOAD_PF if bad else "ok",
            "SPVP=0, MPRV VS-level, user page",
            None if bad else sb,
            hlv=True,
        )
        spvp(t, True)
        mprv_load(t, va, 3, 0, "ok", "SPVP=1, MPP=3", sa, hlv=True)
        spvp(t, False)
        atp_off(t)

    both(t, body2)
    tests.append(t)
    return tests


# ---------------------------------------------------------------- endianness
def sx32(v: int, xlen: int) -> int:
    """A 32-bit load value sign-extended to xlen bits."""
    v &= 0xFFFFFFFF
    return (v - (1 << 32) if v >> 31 else v) & ((1 << xlen) - 1)


def bswap(v: int, n: int) -> int:
    return int.from_bytes(v.to_bytes(n, "little"), "big")


def gen_vsbe() -> list[MemTest]:
    tests = []
    W32 = 0x11223384
    for rule in ("hstatus_vsbe_warl", "hstatus_vsbe_acc", "hstatus_vsbe_op", "hstatus_vsbe_implicit", "vsstatus_ube"):
        t = new(rule)
        texts = {
            "hstatus_vsbe_warl": "The VSBE bit is a WARL field that controls the endianness of explicit memory "
            "accesses made from VS-mode.",
            "hstatus_vsbe_acc": "An implementation may make VSBE a read-only field that always specifies the "
            "same endianness as HS-mode.",
            "hstatus_vsbe_op": "If VSBE=0, explicit load and store memory accesses made from VS-mode are "
            "little-endian, and if VSBE=1, they are big-endian.",
            "hstatus_vsbe_implicit": "VSBE also controls the endianness of all implicit accesses to VS-level "
            "memory management data structures, such as page tables.",
            "vsstatus_ube": "An implementation may make field UBE be a read-only copy of hstatus.VSBE.",
        }
        t.describe(
            source=HYP,
            rule_text=texts[rule],
            context="VSBE (hstatus bit 5) is probed at run time. HS-mode endianness is mstatus.SBE (bit 36, or "
            "mstatush bit 4 on RV32), read through T-SBI. HLV/HSV with SPVP=1 make VS-level accesses, so they "
            "follow VSBE; with SPVP=0 they make VU-level accesses, which follow vsstatus.UBE (bit 6). "
            "Little-endian-only harts exercise only the read-only paths.",
            plan={
                "hstatus_vsbe_warl": "1. Write VSBE=1 and read; write 0 and read. The field either follows the "
                "writes or holds one constant value.\n2. HLV.W with SPVP=1 reads the word with the endianness "
                "VSBE reads back.",
                "hstatus_vsbe_acc": "1. If VSBE does not follow writes, its constant value equals mstatus.SBE (RV64; on RV32 "
                "SBE is in mstatush, which T-SBI cannot read, so only the constancy is checked).",
                "hstatus_vsbe_op": "1. If VSBE is writable: with VSBE=0 and 1, HLV.W/HLV.H/HLV.B (SPVP=1) read "
                f"{hex(W32)} little- and big-endian, and HSV.W writes it in that byte order (checked with an "
                "HS-mode load).\n2. Otherwise the little-endian results (SBE=0) are checked.",
                "hstatus_vsbe_implicit": "1. If VSBE is writable: with VSBE=1, the VS-stage PTEs are stored "
                "big-endian (with HSV, SPVP=1, while vsatp is Bare) and HLV.W through vsatp reads the page "
                "(big-endian data). A design that reads PTEs little-endian sees invalid PTEs and faults.",
                "vsstatus_ube": "1. Probe UBE by writing VSBE and UBE to opposite values. If UBE is writable on its "
                "own, HLV.W with SPVP=0 (a VU-level access) follows UBE: big-endian with UBE=1, little-endian with "
                "UBE=0, while VSBE=0. If UBE reads as a copy of VSBE, HLV.W with SPVP=0 and VSBE=1 is big-endian. "
                "A constant UBE needs no further check.",
            }[rule],
        )
        init(t)
        pg = t.page("e", {0: (4, W32), 4: (4, 0)})
        t.comment("x1 = 1 if VSBE follows writes")
        bits(t, 0x600, "hstatus.VSBE", 0x20, True)
        t.emit("csrr x8, 0x600")
        bits(t, 0x600, "hstatus.VSBE", 0x20, False)
        t.emit("csrr x9, 0x600")
        t.emit("srli x8, x8, 5")
        t.emit("andi x8, x8, 1")
        t.emit("srli x9, x9, 5")
        t.emit("andi x9, x9, 1")
        t.emit("xor x1, x8, x9  // 1: writable")
        if rule in ("hstatus_vsbe_warl", "hstatus_vsbe_acc"):
            lab = t.label("probe")
            t.emit(f"{lab}:", 0)
            t.emit("slli x7, x8, 1")
            t.emit("or x7, x7, x9  // (after 1, after 0)")
            if rule == "hstatus_vsbe_warl":
                t.emit("li x5, 1")
                t.emit("sltu x7, x5, x7")  # x7 in {2(10)} -> 1; {0,3} -> 0, {1} -> 0
                t.emit("or x7, x7, x1")  # writable
                t.emit("xori x5, x1, 1")
                t.emit("xor x6, x8, x9")
                t.emit("seqz x6, x6")
                t.emit("and x6, x6, x5")
                t.emit("or x7, x7, x6")
                t.check("x7", 1, lab, "VSBE follows writes (1 then 0) or holds a constant")
            else:
                # RV64: mstatus.SBE is bit 36. RV32 keeps SBE in mstatush, which T-SBI cannot read, so the
                # RV32 file checks only that a read-only VSBE is constant (x1 = 0).
                with t.rv64_only():
                    t.tsbi_csr("READ", "MSTATUS")
                    t.emit("srli a0, a0, 36")
                    t.emit("andi a0, a0, 1")

                    def ro() -> None:
                        t.emit("xor x7, x8, a0")
                        t.check("x7", 0, lab, "read-only VSBE equals mstatus.SBE")

                    t.either("x1", lambda: None, ro)
        if rule in ("hstatus_vsbe_warl", "hstatus_vsbe_op"):
            spvp(t, True)

            def run(be: int) -> None:
                if be:
                    bits(t, 0x600, "hstatus.VSBE", 0x20, True)
                v = bswap(W32, 4) if be else W32
                v16 = bswap(W32 & 0xFFFF, 2) if be else W32 & 0xFFFF
                both(
                    t,
                    lambda xlen: (
                        hl(t, "hlv.w", pg, f"VSBE={be}", "ok", sx32(v, xlen)),
                        hl(t, "hlv.hu", pg, f"VSBE={be}", "ok", v16),
                        hl(t, "hlv.bu", pg, f"VSBE={be}", "ok", W32 & 0xFF),
                    ),
                )
                if rule == "hstatus_vsbe_op":
                    t.load("x8", 0xA1B2C3D4, "value")
                    lab = hl(t, "hsv.w", f"{pg}+4", f"VSBE={be}", "ok")
                    t.la("x6", f"{pg}+4")
                    t.emit("lw x7, 0(x6)")
                    mem = bswap(0xA1B2C3D4, 4) if be else 0xA1B2C3D4
                    mem = mem - (1 << 32) if mem >> 31 else mem
                    both(
                        t,
                        lambda xlen: t.check(
                            "x7", mem & ((1 << xlen) - 1), lab, f"hsv.w with VSBE={be} stores in that byte order"
                        ),
                    )
                bits(t, 0x600, "hstatus.VSBE", 0x20, False)

            t.either("x1", lambda: (run(0), run(1)), lambda: run(0))
            spvp(t, False)
        if rule == "hstatus_vsbe_implicit":
            t.page("pt_target")

            def be_path() -> None:
                def body(xlen: int) -> None:
                    v = PT(t, f"vs{xlen}", VS_OF[xlen], xlen)
                    # build the table little-endian first (allocates tables), then rewrite each PTE big-endian
                    v.leaf(VA_BASE[xlen], t.page("pt_target"), LEAF)
                    bits(t, 0x600, "hstatus.VSBE", 0x20, True)
                    spvp(t, True)
                    for (tab, idx), child in list(v.children.items()):
                        _rewrite_be(t, tab, idx, xlen)
                    tab = v.pointer(VA_BASE[xlen], len(v.geo) - 1)
                    _rewrite_be(t, tab, v._idx(VA_BASE[xlen], len(v.geo) - 1), xlen)
                    vsatp_on(t, v)
                    s = sig(t.page_id("pt_target")) & 0xFFFFFFFF
                    b = bswap(s, 4)
                    b = b - (1 << 32) if b >> 31 else b
                    hl(t, "hlv.w", VA_BASE[xlen], "VSBE=1, PTEs stored big-endian", "ok", b & ((1 << xlen) - 1))
                    atp_off(t)
                    spvp(t, False)
                    bits(t, 0x600, "hstatus.VSBE", 0x20, False)

                both(t, body)

            t.either("x1", be_path, lambda: None)
        if rule == "vsstatus_ube":
            t.comment("x9 = UBE after writing VSBE=1, UBE=0; x8 = UBE after VSBE=0, UBE=1")
            bits(t, 0x200, "vsstatus.UBE", 0x40, False)
            bits(t, 0x600, "hstatus.VSBE", 0x20, True)
            t.emit("csrr x9, 0x200")
            bits(t, 0x600, "hstatus.VSBE", 0x20, False)
            bits(t, 0x200, "vsstatus.UBE", 0x40, True)
            t.emit("csrr x8, 0x200")
            bits(t, 0x200, "vsstatus.UBE", 0x40, False)
            t.emit("srli x9, x9, 6")
            t.emit("andi x9, x9, 1")
            t.emit("srli x8, x8, 6")
            t.emit("andi x8, x8, 1")
            lab = t.label("ube")
            t.emit(f"{lab}:", 0)
            spvp(t, False)
            t.comment("x7 = 1 if UBE is writable on its own: (x9, x8) = (0, 1)")
            t.emit("xori x7, x9, 1")
            t.emit("and x7, x7, x8")

            def ube_w() -> None:
                bits(t, 0x200, "vsstatus.UBE", 0x40, True)
                both(t, lambda xlen: hl(t, "hlv.w", pg, "SPVP=0, UBE=1, VSBE=0", "ok", sx32(bswap(W32, 4), xlen)))
                bits(t, 0x200, "vsstatus.UBE", 0x40, False)
                both(t, lambda xlen: hl(t, "hlv.w", pg, "SPVP=0, UBE=0, VSBE=0", "ok", sx32(W32, xlen)))

            def ube_other() -> None:
                # UBE a copy of VSBE: (x9, x8) = (1, 0), possible only when VSBE is writable
                t.emit("xori x7, x8, 1")
                t.emit("and x7, x7, x9")
                t.emit("and x7, x7, x1")

                def copy() -> None:
                    bits(t, 0x600, "hstatus.VSBE", 0x20, True)
                    both(
                        t,
                        lambda xlen: hl(
                            t, "hlv.w", pg, "SPVP=0, VSBE=1, UBE its copy", "ok", sx32(bswap(W32, 4), xlen)
                        ),
                    )
                    bits(t, 0x600, "hstatus.VSBE", 0x20, False)

                t.either("x7", copy, lambda: None)

            t.either("x7", ube_w, ube_other)
        fini(t)
        tests.append(t)
    return tests


def _rewrite_be(t: MemTest, tab: str, idx: int, xlen: int) -> None:
    """Re-store the PTE at tab[idx] big-endian with HSV (VSBE=1, SPVP=1, vsatp Bare)."""
    n = xlen // 8
    t.la("x6", tab)
    t.emit(f"li x7, {idx * n}")
    t.emit("add x6, x6, x7")
    t.emit("LREG x8, 0(x6)")
    line, _ = hlsv("hsv.d" if xlen == 64 else "hsv.w", "x0", "x6", "x8")
    t.emit(line)


# ---------------------------------------------------------------- pointer masking for HLV/HSV (Ssnpm)
PMM_SHIFT = 32
HUPMM_SHIFT = 48
TAG = 0x2A << 57  # bits 62:57, masked by PMLEN 7 and 16


def gen_pm() -> list[MemTest]:
    tests = []
    specs = {
        "hstatus_hupmm_u_mode": "When Ssnpm extension is implemented, the HUPMM field enables or disables pointer "
        "masking (see <<Zpm>>) for HLV.* and HSV.* instructions in U-mode, according to the values in "
        "<<henvcfg-pmm-values>>, when their explicit memory access is performed as though in VU-mode.",
        "hstatus_hupmm_vu_mode": "In HS- and M-modes, pointer masking for these instructions is enabled or "
        "disabled by senvcfg.PMM, when their explicit memory access is performed as though in VU-mode.",
        "hstatus_hupmm_vs_mode": "Setting henvcfg.PMM enables or disables pointer masking for HLV.* and HSV.* when "
        "their explicit memory access is performed as though in VS-mode.",
    }
    for rule, text in specs.items():
        t = new(rule, ["I", "S", "H", "Ssnpm"], rv64=True)
        t.describe(
            source=HYP,
            rule_text=text,
            context="RV64 only (pointer masking is defined for RV64). PMM/HUPMM are WARL; the test probes 0b10 "
            "(PMLEN=7) and then 0b11 (PMLEN=16) and uses whichever sticks; both mask address bits 62:57. With "
            "vsatp Bare the guest address is physical, so the ignored bits are replaced by zeros (zpm.adoc, "
            "pm_ignore_pa). G-stage Sv39x4 identity-maps the image and maps GPA_BASE to a data page, so an "
            "unmasked tagged address raises a load/store guest-page fault (bits 63:41 nonzero).",
            plan={
                "hstatus_hupmm_u_mode": "1. U-mode, hstatus.HU=1, SPVP=0: with HUPMM enabled, HLV.W and HSV.W "
                "of the tagged address access the page; with HUPMM=0 they raise 21/23, even with senvcfg.PMM "
                "enabled.\n2. SPVP=1 in U-mode: HUPMM does not apply (henvcfg.PMM=0 -> 21).",
                "hstatus_hupmm_vu_mode": "1. HS-mode, SPVP=0: with senvcfg.PMM enabled, HLV.W/HSV.W of the "
                "tagged address access the page; with senvcfg.PMM=0 they fault (21/23) even with HUPMM "
                "enabled.",
                "hstatus_hupmm_vs_mode": "1. HS-mode and U-mode (HU=1), SPVP=1: with henvcfg.PMM enabled, HLV.W "
                "of the tagged address reads the page; with henvcfg.PMM=0 it faults (21) even with senvcfg.PMM "
                "and HUPMM enabled.",
            }[rule],
        )
        init(t)
        t.page("P")
        g = PT(t, "g64", "sv39x4", 64)
        g.identity(ULEAF)
        g.leaf(GPA_BASE[64], t.page("P"), ULEAF)
        hgatp_on(t, g)
        addr = GPA_BASE[64] | TAG
        s = sig(t.page_id("P")) & 0xFFFFFFFF

        def pm(csr: int, shift: int, name: str, on: bool) -> None:
            t.emit(f"li x7, {hex(3 << shift)}")
            t.emit(f"csrc {hex(csr)}, x7  // {name} = 0")
            if on:
                t.emit("li x8, 2")
                t.emit(f"slli x8, x8, {shift}")
                t.emit(f"csrs {hex(csr)}, x8  // {name} = 0b10")
                t.emit(f"csrr x8, {hex(csr)}")
                t.emit("and x8, x8, x7")
                skip = t.label("pmok")
                t.emit(f"bnez x8, {skip}")
                t.emit(f"csrs {hex(csr)}, x7  // {name} = 0b11 (PMLEN=16)")
                t.emit(f"{skip}:", 0)

        def case(mode: str, sp: int, sen: bool, hu: bool, hen: bool, okk: bool, d: str) -> None:
            spvp(t, bool(sp))
            pm(0x10A, PMM_SHIFT, "senvcfg.PMM", sen)
            pm(0x600, HUPMM_SHIFT, "hstatus.HUPMM", hu)
            pm(0x60A, PMM_SHIFT, "henvcfg.PMM", hen)
            hl(t, "hlv.w", addr, d, "ok" if okk else LOAD_GPF, s if okk else None, mode=mode)
            t.load("x8", 0x5151, "value")
            hl(t, "hsv.w", addr + 8, d, "ok" if okk else STORE_GPF, mode=mode)

        # the GPF htval for a GPA beyond hgatp's range: 0 or GPA>>2; don't constrain it (tval2 not checked)
        if rule == "hstatus_hupmm_u_mode":
            bits(t, 0x600, "hstatus.HU", 1 << 9, True)
            case("U", 0, False, True, False, True, "U-mode, SPVP=0, HUPMM on")
            case("U", 0, True, False, False, False, "U-mode, SPVP=0, HUPMM=0, senvcfg.PMM on")
            case("U", 1, False, True, False, False, "U-mode, SPVP=1, HUPMM on, henvcfg.PMM=0")
            bits(t, 0x600, "hstatus.HU", 1 << 9, False)
        elif rule == "hstatus_hupmm_vu_mode":
            hup = MUT == "hupmm_in_hs"
            case("S", 0, True, False, False, not hup, "HS-mode, SPVP=0, senvcfg.PMM on")
            case("S", 0, False, True, False, hup, "HS-mode, SPVP=0, senvcfg.PMM=0, HUPMM on")
        else:
            bits(t, 0x600, "hstatus.HU", 1 << 9, True)
            for mode in ("S", "U"):
                case(mode, 1, False, False, True, True, f"{mode}-mode, SPVP=1, henvcfg.PMM on")
                case(mode, 1, True, True, False, False, f"{mode}-mode, SPVP=1, henvcfg.PMM=0, others on")
            bits(t, 0x600, "hstatus.HU", 1 << 9, False)
        for csr, shift in ((0x10A, PMM_SHIFT), (0x600, HUPMM_SHIFT), (0x60A, PMM_SHIFT)):
            t.emit(f"li x7, {hex(3 << shift)}")
            t.emit(f"csrc {hex(csr)}, x7")
        fini(t)
        tests.append(t)

    t = new("hstatus_hupmm_not_ssnpm_access", ["I", "S", "H"], forbidden=["Ssnpm"], rv64=True)
    t.describe(
        source=HYP,
        rule_text="When the Ssnpm extension is not implemented, the HUPMM field is read-only zero.",
        context="RV64 only: on RV32 hstatus has no HUPMM field (hstatus_hupmm_rv32_access).",
        plan="1. Write HUPMM = 0b11, 0b10, 0b01 and read 0 each time.",
    )
    for v in (3, 2, 1):
        lab = t.label("hupmm")
        t.emit(f"li x7, {hex(v << HUPMM_SHIFT)}")
        t.emit(f"{lab}:", 0)
        t.emit("csrs 0x600, x7")
        t.emit("csrr x8, 0x600")
        t.emit("csrc 0x600, x7")
        t.check_masked("x8", 3 << HUPMM_SHIFT, 0, lab, f"HUPMM reads 0 after writing {v:#b} without Ssnpm")
    tests.append(t)
    return tests


def gen() -> list[MemTest]:
    tests = [gen_hlsv_op(), gen_hlvx(), gen_hlvx32()]
    tests += gen_priv()
    tests.append(gen_trans())
    tests += gen_mxr()
    tests += gen_v0()
    tests += gen_mprv()
    tests += gen_vsbe()
    tests += gen_pm()
    return tests
