# SPDX-License-Identifier: Apache-2.0
"""Helpers for the small privileged-extension rule-derived suites (gen_Sx.py): Sstvala, Sstvecd, Ssu64xl, Ssccptr,
Ssstrict, the Sh* hypervisor extensions, Svvptc, Svrsw60t59b, and the privileged-spec introduction and CSR chapters
(Ssintro).

This module holds no expectations; gen_Sx.py owns them (and the mutants). Page tables come from svlib.SvPT (S-stage)
and hmem.PT (G-stage and VS-stage), imported read-only.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

sys.path.insert(0, str(Path(__file__).parent))
from aigen import NO_TRAP, ORIGIN, X
from svlib import BASE, SvPT, SvTest, guard, probe, register_alias, satp_off, unregister_alias

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect, TestFile, Value

ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
SUP = "src/priv/supervisor.adoc"
MAC = "src/priv/machine.adoc"
HYP = "src/priv/hypervisor.adoc"
CSRS = "src/priv/csrs.adoc"
INTRO = "src/priv/intro.adoc"
MARCH = "rv${XLEN}i_zicsr_zifencei"

ILLEGAL, VIRTUAL, BREAKPOINT = 2, 22, 3
INSN_MIS, INSN_AF, LOAD_MIS, LOAD_AF, STORE_MIS, STORE_AF = 0, 1, 4, 5, 6, 7
INSN_PF, LOAD_PF, STORE_PF = 12, 13, 15
INSN_GPF, LOAD_GPF, STORE_GPF = 20, 21, 23
H = "defined(H_SUPPORTED)"
C16 = "defined(ZCA_SUPPORTED)"
# An address that raises an access fault, per kind of access (check_defines.h derives each from the plain
# RVMODEL_ACCESS_FAULT_ADDRESS when only that one is defined; some configurations define only these).
FA_KIND = {k: f"RVMODEL_ACCESS_FAULT_ADDRESS_{k.upper()}" for k in ("load", "store", "fetch")}
HAS_FA_KIND = {k: f"defined({v})" for k, v in FA_KIND.items()}


def icause(code: int) -> X:
    """xcause of interrupt `code`."""
    return X((1 << 31) | code, (1 << 63) | code)


# ---------------------------------------------------------------- trap-log vector field
# The framework trampoline (tests/env/rvtest_trap_handler.h) is a spreader of UDB_MXLEN jumps followed by one 3-word
# stub per cause. Spreader entry k jumps to stub k; the stub's jal leaves T6 = stub_k + 12, and the handler logs
# ((T6 - trampoline) * 3) >> 5 in bits 10:6 of the trap log's word 0. So a trap that entered the trampoline at byte
# offset 4k shows which entry the hart jumped to. Entries 0-23 have stubs; the others end the test.
NSTUBS = 24


def vect_field(k: int, xlen: int) -> int:
    off = 4 * xlen + 12 * (k + 1)
    return ((off * 3) >> 5) & 31


def vect_x(k: int) -> X:
    return X(vect_field(k, 32), vect_field(k, 64))


def check_vect(t: TestFile, k: int, lab: str, desc: str) -> None:
    """The last logged trap entered trampoline spreader entry k."""
    t.emit("AI_LOG(x15, TRAPLOG_VECT)", 10)
    t.emit("srli x15, x15, 6")
    t.emit("andi x15, x15, 31")
    t.check("x15", vect_x(k), lab, f"{desc}: the trap entered the trampoline at entry {k} (BASE + {4 * k})")


def check_handler(t: TestFile, mode: str, lab: str, desc: str) -> None:
    """The last logged trap was taken by the `mode` handler (M, S or VS)."""
    t.emit("AI_LOG(x15, TRAPLOG_VECT)", 10)
    t.emit("andi x15, x15, 3")
    t.check("x15", {"M": 3, "S": 1, "VS": 2}[mode], lab, f"{desc}: taken by the {mode}-mode handler (3 M, 1 S, 2 VS)")


# ---------------------------------------------------------------- windows with a free epc / tval
def outcome_at(
    t: TestFile,
    expect: Expect,
    lab: str,
    desc: str,
    epc: Value | None = None,
    tval: Expect | None = None,
    origin: str | None = None,
    handler: str | None = None,
    tval2: Expect | None = None,
) -> None:
    """Close a window opened by t.allow() (like TestFile.outcome), with xepc compared with `epc` (a label, a
    'label+off' string or a constant; None: not checked), and optionally the handler mode and htval/mtval2."""
    alts = expect if isinstance(expect, list) else [expect]
    oks = "ok" in alts
    causes = [a for a in alts if a != "ok"]
    t.emit("AI_OUTCOME", 20)
    t.check("x13", [0, 1] if oks and causes else (0 if oks else 1), lab, f"{desc}: number of traps")
    t.check("x14", [NO_TRAP if a == "ok" else a for a in alts], lab, f"{desc}: outcome (xcause, or all ones for none)")
    if not causes:
        return
    skip, done = t.label("notrap"), t.label("checked")
    if oks:
        t.emit("li x5, -1")
        t.emit(f"beq x14, x5, {skip}")
    first = len(t.table)
    if epc is not None:
        t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
        t.check("x15", epc, lab, f"{desc}: xepc")
    if tval is not None:
        t.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
        t.check("x15", tval, lab, f"{desc}: xtval")
    if tval2 is not None:
        t.emit("AI_LOG(x15, TRAPLOG_TVAL2)", 10)
        t.check("x15", tval2, lab, f"{desc}: htval")
    if handler:
        check_handler(t, handler, lab, desc)
    if origin:
        t.emit("AI_ORIGIN", 25)
        t.check("x15", ORIGIN[origin], lab, f"{desc}: xPP/xPV record the mode the trap came from")
    if oks:
        t.emit(f"j {done}")
        t.emit(f"{skip}:", 0)
        t.code += t._skip_lines(first, len(t.table))
        t.emit(f"{done}:", 0)


def delay(t: TestFile, n: int, reg: str = "x8") -> None:
    """A bounded busy wait of n iterations (no checks inside)."""
    loop = t.label("wait")
    t.emit(f"li {reg}, {n}")
    t.emit(f"{loop}:", 0)
    t.emit(f"addi {reg}, {reg}, -1", n)
    t.emit(f"bnez {reg}, {loop}", n)


# ---------------------------------------------------------------- S-stage paging (svlib)
def with_vm(
    t: SvTest, xlen: int, inner: Callable[[SvPT], None], *, user: bool = False, name: str | None = None
) -> SvPT:
    """Build the base scheme's table (Sv32 on RV32, Sv39 on RV64) identity-mapping the image (and its user alias if
    `user`), and run inner(pt) with satp still Bare; inner maps its pages and calls pt.on(). The whole thing runs
    only if satp accepts the scheme (probed). satp is Bare afterwards."""
    pt = SvPT(t, name or f"p{xlen}", BASE[xlen])
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

    probe(t, pt)
    guard(t, "x1", run)
    return pt


def both(t: TestFile, body: Callable[[int], object]) -> None:
    with t.rv64_only():
        body(64)
    with t.rv32_only():
        body(32)


def word(e: int, note: str) -> str:
    return f".word {hex(e)}  // {note}"


def half(e: int, note: str) -> str:
    return f".hword {hex(e)}  // {note}"


def enc_csr(csr: int, f3: int, rd: int, rs1: int) -> int:
    """A CSR instruction: f3 1 csrrw, 2 csrrs, 3 csrrc, 5 csrrwi, 6 csrrsi, 7 csrrci (rs1 = uimm for the I forms)."""
    return (csr << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x73


# The eight CSR instruction forms: (name, funct3, rs1/uimm, writes)
CSR_FORMS = [
    ("csrrw rd=x7", 1, 6, True),
    ("csrrw rd=x0", 1, 6, True),
    ("csrrs rs1=x6", 2, 6, True),
    ("csrrs rs1=x0", 2, 0, False),
    ("csrrc rs1=x6", 3, 6, True),
    ("csrrc rs1=x0", 3, 0, False),
    ("csrrwi uimm=0", 5, 0, True),
    ("csrrwi uimm=21", 5, 21, True),
    ("csrrsi uimm=21", 6, 21, True),
    ("csrrsi uimm=0", 6, 0, False),
    ("csrrci uimm=21", 7, 21, True),
    ("csrrci uimm=0", 7, 0, False),
]


def form_enc(csr: int, form: tuple) -> int:
    name, f3, rs1, _ = form
    rd = 0 if "rd=x0" in name else 7
    return enc_csr(csr, f3, rd, rs1)


def outcome_cases(
    t: TestFile,
    expect: Expect,
    lab: str,
    desc: str,
    tvals: dict,
    epc: Value | None = None,
    origin: str | None = None,
    handler: str | None = None,
    tval2s: dict | None = None,
) -> None:
    """Like outcome_at, but xtval (and, with tval2s, htval/mtval2) is checked per cause: tvals maps a cause to its
    legal xtval value(s). Causes missing from tvals have xtval unchecked."""
    alts = expect if isinstance(expect, list) else [expect]
    oks = "ok" in alts
    causes = [a for a in alts if a != "ok"]
    t.emit("AI_OUTCOME", 20)
    t.check("x13", [0, 1] if oks and causes else (0 if oks else 1), lab, f"{desc}: number of traps")
    t.check("x14", [NO_TRAP if a == "ok" else a for a in alts], lab, f"{desc}: outcome (xcause, or all ones for none)")
    if not causes:
        return
    skip, done = t.label("notrap"), t.label("checked")
    if oks:
        t.emit("li x5, -1")
        t.emit(f"beq x14, x5, {skip}")
    first = len(t.table)
    for c in causes:
        if c not in tvals and not (tval2s and c in tval2s):
            continue
        nxt = t.label("nextcause")
        a0 = len(t.table)
        if len(causes) > 1:
            t.load("x5", c, f"cause {c}")
            t.emit(f"bne x14, x5, {nxt}")
        if c in tvals:
            tv = tvals[c]
            t.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
            if isinstance(tv, tuple) and tv[0] == "range":
                # any address inside the access [lo, lo + size): the faulting portion of a split access
                _, lo, size = tv
                t.load("x13", lo, "first byte of the access")
                t.emit("sub x13, x15, x13")
                t.emit(f"sltiu x13, x13, {size}")
                t.check_bool("x13", lab, f"{desc}: cause {c}: xtval is an address inside the access")
            else:
                t.check("x15", cast("Expect", tv), lab, f"{desc}: cause {c}: xtval")
        if tval2s and c in tval2s:
            tv2 = tval2s[c]
            t.emit("AI_LOG(x15, TRAPLOG_TVAL2)", 10)
            if isinstance(tv2, tuple) and tv2[0] == "gpa_or_zero":
                # htval = GPA >> 2, or htval = 0 together with stval = 0 (a nonzero htval must correspond to the
                # address in stval, hypervisor.adoc mtval2_htval_virtaddr)
                t.load("x13", tv2[1], "GPA >> 2")
                t.emit("xor x13, x15, x13")
                t.emit("seqz x13, x13  // htval == GPA >> 2")
                t.emit("AI_LOG(x5, TRAPLOG_TVAL)", 10)
                t.emit("or x5, x5, x15")
                t.emit("seqz x5, x5  // stval == htval == 0")
                t.emit("or x13, x13, x5")
                t.check_bool("x13", lab, f"{desc}: cause {c}: htval = GPA >> 2 (or htval = stval = 0)")
            else:
                t.check("x15", cast("Expect", tv2), lab, f"{desc}: cause {c}: htval")
        if len(causes) > 1:
            t.emit(f"j {nxt}_end")
            t.emit(f"{nxt}:", 0)
            t.code += t._skip_lines(a0 + 1, len(t.table))
            t.emit(f"{nxt}_end:", 0)
    if epc is not None:
        t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
        t.check("x15", epc, lab, f"{desc}: xepc")
    if handler:
        check_handler(t, handler, lab, desc)
    if origin:
        t.emit("AI_ORIGIN", 25)
        t.check("x15", ORIGIN[origin], lab, f"{desc}: xPP/xPV record the mode the trap came from")
    if oks:
        t.emit(f"j {done}")
        t.emit(f"{skip}:", 0)
        t.code += t._skip_lines(first, len(t.table))
        t.emit(f"{done}:", 0)


# ---------------------------------------------------------------- two-stage translation (hmem.PT)
HGATP, VSATP = 0x680, 0x280
HFENCE_GVMA = ".word 0x62000073  // hfence.gvma x0, x0"
HFENCE_VVMA = ".word 0x22000073  // hfence.vvma x0, x0"


def atp_probe(t: TestFile, csr: int, pt: object, reg: str = "x1") -> None:
    """reg = 1 if `csr` (hgatp or vsatp) accepts pt's MODE (written with pt's root); the CSR is left 0.
    Clobbers x6, x7."""
    import hmem
    import svlib

    MODE = {**svlib.MODE, **hmem.MODE}
    pt.atp("x6")  # type: ignore[attr-defined]
    t.emit(f"csrw {hex(csr)}, x6  // probe MODE")
    t.emit(f"csrr {reg}, {hex(csr)}")
    t.emit(f"csrw {hex(csr)}, x0")
    t.emit(HFENCE_GVMA if csr == HGATP else HFENCE_VVMA)
    mode = MODE[pt.scheme]  # type: ignore[attr-defined]
    if pt.xlen == 64:  # type: ignore[attr-defined]
        t.emit(f"srli {reg}, {reg}, 60")
        t.emit(f"addi {reg}, {reg}, -{mode}")
    else:
        t.emit(f"srli {reg}, {reg}, 31")
        t.emit(f"addi {reg}, {reg}, -{mode}")
    t.emit(f"seqz {reg}, {reg}")


def spvp(t: TestFile, on: bool) -> None:
    t.emit("li x7, 0x100")
    t.emit(f"{'csrs' if on else 'csrc'} 0x600, x7  // hstatus.SPVP = {int(on)}")
