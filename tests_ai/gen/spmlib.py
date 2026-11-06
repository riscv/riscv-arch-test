# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for the pointer-masking suites (gen_Spm.py): Smmpm, Smnpm, Ssnpm, Sspm and Supm.

Pointer masking is RV64-only, so every behavioral test is rv64=True. The helpers:

- write a PMM field (mseccfg, menvcfg, senvcfg, henvcfg) from the test's current mode, directly or through
  T-SBI, and read back what the hart holds (PMM is WARL);
- branch at run time on the PMM value read back (dispatch): each legal value (00, 10, 11) gets its own
  expectations, so whatever PMLEN the hart supports, the test checks the behavior of the value it holds;
- build tagged addresses at run time and run one explicit access in a trap window, with the outcome the
  ignore transformation predicts (zpm.adoc): physical addresses are zero-extended above XLEN-PMLEN-1, virtual
  ones sign-extended from bit XLEN-PMLEN-1;
- build a small Sv39/Sv48/Sv57 page table (identity map of the test image, a high-half alias of it, and
  pointers for the page-table-walk test).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import NO_TRAP, ORIGIN, POOL_TRAP, TestFile
from hmem import MemTest, sig

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect

MUT = os.environ.get("AI_MUTANT", "")  # mutate.py: model a plausible bug in the expectations
ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
ZPM = "src/priv/zpm.adoc"
MAC = "src/priv/machine.adoc"
SUP = "src/priv/supervisor.adoc"
HYP = "src/priv/hypervisor.adoc"
MARCH = "rv${XLEN}i_zicsr_zifencei"
M64 = (1 << 64) - 1

CSRN = {
    "mseccfg": 0x747,
    "mseccfgh": 0x757,
    "menvcfg": 0x30A,
    "menvcfgh": 0x31A,
    "senvcfg": 0x10A,
    "henvcfg": 0x60A,
    "henvcfgh": 0x61A,
    "mstatus": 0x300,
    "sstatus": 0x100,
    "satp": 0x180,
    "hgatp": 0x680,
    "vsatp": 0x280,
    "hstatus": 0x600,
    "vsstatus": 0x200,
    "mepc": 0x341,
    "mtval": 0x343,
    "sepc": 0x141,
    "stval": 0x143,
}
# CSRs each mode may access directly; the others go through T-SBI
DIRECT = {
    "M": set(CSRN),
    "S": {"senvcfg", "henvcfg", "sstatus", "satp", "hgatp", "vsatp", "hstatus", "vsstatus", "sepc", "stval"},
    "U": set(),
}
PMM_SH = 32
PMM_M = 3 << PMM_SH
PMLEN = {0: 0, 2: 7, 3: 16}
MXR = 1 << 19
MPRV = 1 << 17
MPP = 3 << 11

H = "defined(H_SUPPORTED)"
S_ = "defined(S_SUPPORTED)"
NOS = "!defined(S_SUPPORTED)"

ISSUE_3313 = (
    f"{ISSUE}3313 and {ISSUE}1915: MXR is never in effect for an access whose effective privilege mode is M, so "
    'mstatus.MXR does not disable M-mode pointer masking (aswaterman: otherwise "S-mode could disable M-mode pointer '
    'masking by setting sstatus.MXR"; gfavor: "mstatus.MXR is never in effect for M-mode"). For an S/U effective '
    "mode, MXR=1 disables pointer masking even with satp.MODE=Bare; for VS/VU, sstatus.MXR or vsstatus.MXR."
)
ISSUE_2423 = (
    f'{ISSUE}2423: pointer masking does not apply to instruction-fetch addresses, "whether when used to do '
    'instruction fetches or when written on an exception into a *tval CSR" (ARC ruling quoted by gfavor).'
)
ISSUE_1944 = (
    f"{ISSUE}1944: the ignore transformation comes first; address validity is checked on the transformed "
    'address (radimkrcmar, quoting the "semantically equivalent to ... applies the ignore operation" text).'
)
ISSUE_1844 = (
    f"{ISSUE}1844: CBO and other accesses report the transformed effective address; \"the term 'effective "
    "address' does all the work\" (aswaterman)."
)
TVAL_NOTE = (
    "xtval rules (supervisor.adoc stval): a fault may write 0; a valid faulting address must be written exactly; an "
    "invalid one may be replaced by another invalid address. So a fault on a transformed address that is valid must "
    "report 0 or that address, and a fault on an invalid address must not report the masked (valid) base address."
)


# ---------------------------------------------------------------- encodings (.word, so MARCH stays rv64i)
def r_type(f5: int, rs2: int, rs1: int, f3: int, rd: int) -> int:
    return (f5 << 27) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x2F


ENC = {
    "amoadd.d": r_type(0, 8, 6, 3, 7),  # amoadd.d x7, x8, (x6)
    "amoswap.w": r_type(1, 8, 6, 2, 7),  # amoswap.w x7, x8, (x6)
    "lr.d": r_type(2, 0, 6, 3, 7),  # lr.d x7, (x6)
    "sc.d": r_type(3, 8, 6, 3, 9),  # sc.d x9, x8, (x6)
    "sc.d7": r_type(3, 8, 6, 3, 7),  # sc.d x7, x8, (x6)
    "flw": (6 << 15) | (2 << 12) | (1 << 7) | 0x07,  # flw f1, 0(x6)
    "fmv.x.w": (0x70 << 25) | (1 << 15) | (7 << 7) | 0x53,  # fmv.x.w x7, f1
    "fsw": (1 << 20) | (6 << 15) | (2 << 12) | 0x27,  # fsw f1, 0(x6)
    "fmv.w.x": (0x78 << 25) | (8 << 15) | (1 << 7) | 0x53,  # fmv.w.x f1, x8
    "vsetivli": (3 << 30) | (0xD8 << 20) | (1 << 15) | (7 << 12) | 0x57,  # vsetivli x0, 1, e64, m1, ta, ma
    "vle64.v": (1 << 25) | (6 << 15) | (7 << 12) | (1 << 7) | 0x07,  # vle64.v v1, (x6)
    "vmv.x.s": (0x10 << 26) | (1 << 25) | (1 << 20) | (2 << 12) | (7 << 7) | 0x57,  # vmv.x.s x7, v1
    "vse64.v": (1 << 25) | (6 << 15) | (7 << 12) | (1 << 7) | 0x27,  # vse64.v v1, (x6)
    "vmv.s.x": (0x10 << 26) | (1 << 25) | (8 << 15) | (6 << 12) | (1 << 7) | 0x57,  # vmv.s.x v1, x8
    "cbo.zero": (4 << 20) | (6 << 15) | (2 << 12) | 0x0F,  # cbo.zero (x6)
}


def w(name: str, note: str = "") -> str:
    return f".word {hex(ENC[name])}  // {note or name}"


# ---------------------------------------------------------------- page contents
# Data page "A": offset 0 holds sig(id) (hmem), offset 8 a fixed pattern, 16.. store slots, 4088 the bytes before
# page "B" (which must follow A) for page-crossing misaligned accesses.
PAT8 = 0x0123456789ABCDEF
TAIL = 0xF1E2D3C4B5A69788  # the last 8 bytes of A


def a_contents() -> dict[int, tuple[int, int]]:
    return {8: (8, PAT8), 4088: (8, TAIL)}


def sx(v: int, bits: int) -> int:
    v &= (1 << bits) - 1
    return (v - (1 << bits) if v >> (bits - 1) else v) & M64


# ---------------------------------------------------------------- the ignore transformation (reference)
def tagmask(q: int) -> int:
    return ((1 << q) - 1) << (64 - q)


def transform(a: int, p: int, virt: bool, vabits: int = 0) -> int:
    """zpm.adoc pm_ignore_va / pm_ignore_pa, with the mutants that model implementation bugs."""
    if MUT == "va_validity_only" and virt and p > 64 - vabits:
        p = 64 - vabits  # masked bits that are VBITS are used untransformed (only validity checks are relaxed)
    if MUT == "pmlen_off_by_one_low" and p:
        p -= 1  # bit XLEN-PMLEN is not masked
    if MUT == "pmlen_off_by_one_high" and p:
        p += 1  # bit XLEN-PMLEN-1 is masked too
    if p == 0:
        return a
    low = a & ((1 << (64 - p)) - 1)
    if virt and MUT != "va_zero_extend":
        return sx(low, 64 - p)
    if not virt and MUT == "pa_sign_extend":
        return sx(low, 64 - p)
    return low


def canonical(a: int, vabits: int) -> bool:
    top = a >> (vabits - 1)
    return top in (0, (1 << (65 - vabits)) - 1)


# ---------------------------------------------------------------- test construction
def new(
    suite: str,
    rule: str,
    required: list[str],
    boot: str | None,
    *,
    suffix: str = "",
    forbidden: list[str] | None = None,
    rv64: bool = True,
) -> MemTest:
    t = MemTest(
        suite,
        rule,
        required=required,
        boot=boot,
        pool=POOL_TRAP,
        march=MARCH,
        rv64=rv64,
        suffix=suffix,
        forbidden=forbidden,
    )
    t.page("A", a_contents())
    t.page("B")
    t.page("Z")
    t.page("scr")
    return t


def scr(slot: int) -> int:
    """Offset of scratch slot `slot` in page scr (past its signature)."""
    return 64 + 8 * slot


# ---------------------------------------------------------------- CSR access from the current mode
def csr_op(t: TestFile, op: str, csr: str, imm: int | None = None, reg: str | None = None) -> None:
    """op in SET/CLEAR/WRITE on csr, with a constant (imm) or register value; direct when the current mode may
    access the CSR, otherwise through T-SBI. Clobbers x9 (and a0-a2 for T-SBI)."""
    if csr in DIRECT[t.cur]:
        if reg is None:
            assert imm is not None
            t.emit(f"li x9, {hex(imm & M64)}", 6)
            reg = "x9"
        ins = {"SET": "csrs", "CLEAR": "csrc", "WRITE": "csrw"}[op]
        t.emit(f"{ins} {hex(CSRN[csr])}, {reg}  // {csr}")
    elif reg is None:
        assert imm is not None
        t.emit(f"li a1, {hex(imm & M64)}", 6)
        t.tsbi_csr(op, csr.upper(), "a1")
    else:
        t.tsbi_csr(op, csr.upper(), reg)


def csr_read(t: TestFile, csr: str, rd: str) -> None:
    if csr in DIRECT[t.cur]:
        t.emit(f"csrr {rd}, {hex(CSRN[csr])}  // {csr}")
    else:
        t.tsbi_csr("READ", csr.upper())
        if rd != "a0":
            t.emit(f"mv {rd}, a0")


def pmm_field(t: TestFile, rd: str) -> None:
    t.emit(f"srli {rd}, {rd}, {PMM_SH}")
    t.emit(f"andi {rd}, {rd}, 3")


def pmm_write(t: TestFile, csr: str, val: int, rd: str = "x8", form: str = "setclear") -> None:
    """Write csr.PMM = val (other fields kept) and read the field back into rd (0..3).
    form: 'setclear' (csrc then csrs), or 'write' (read, modify, csrw)."""
    t.comment(f"{csr}.PMM = {val:02b}")
    if form == "write":
        csr_read(t, csr, rd)
        t.emit(f"li x9, {hex(~PMM_M & M64)}", 6)
        t.emit(f"and {rd}, {rd}, x9")
        if val:
            t.emit(f"li x9, {hex(val << PMM_SH)}", 6)
            t.emit(f"or {rd}, {rd}, x9")
        csr_op(t, "WRITE", csr, reg=rd)
    else:
        csr_op(t, "CLEAR", csr, imm=PMM_M)
        if val:
            csr_op(t, "SET", csr, imm=val << PMM_SH)
    csr_read(t, csr, rd)
    pmm_field(t, rd)


def u_ctrl_write(t: TestFile, val: int, rd: str = "x8") -> None:
    """U-mode's PMM: senvcfg with S, menvcfg without S."""
    with t.only_if(S_):
        pmm_write(t, "senvcfg", val, rd)
    with t.only_if(NOS):
        pmm_write(t, "menvcfg", val, rd)


def save(t: TestFile, reg: str, slot: int) -> None:
    tmp = "x5" if reg == "x9" else "x9"
    t.la(tmp, "ai_pg_scr")
    t.emit(f"sd {reg}, {scr(slot)}({tmp})")


def restore(t: TestFile, slot: int, rd: str) -> None:
    t.la(rd, "ai_pg_scr")
    t.emit(f"ld {rd}, {scr(slot)}({rd})")


def legal_pmm(t: TestFile, reg: str, desc: str) -> None:
    """PMM is WARL with legal values 00, 10, 11 (01 is reserved)."""
    lab = t.label("pmm")
    t.emit(f"{lab}:", 0)
    t.check(reg, [0, 2, 3], lab, f"{desc}: PMM reads a legal value (00, 10 or 11)")


def setpm(t: TestFile, csr: str, val: int, slot: int, desc: str = "") -> None:
    """Write csr.PMM = val, check the value read back is legal, and keep it in scratch slot `slot`."""
    if csr == "uctrl":
        u_ctrl_write(t, val)
    else:
        pmm_write(t, csr, val)
    d = desc or f"{'U-mode control' if csr == 'uctrl' else csr} write {val:02b}"
    if val == 0:
        lab = t.label("pmm0")
        t.emit(f"{lab}:", 0)
        t.check("x8", 0, lab, f"{d}: 00 (disabled) is always legal, so it reads back 00")
    else:
        legal_pmm(t, "x8", d)
    save(t, "x8", slot)


def dispatch(t: TestFile, slot: int, body: Callable[[int], object]) -> None:
    """Run body(PMLEN) for the PMM value in scratch slot `slot`: three paths (16, 7, 0), one taken at run time."""
    restore(t, slot, "x9")
    hi, lo = (7, 16) if MUT == "pmm_encodings_swapped" else (16, 7)
    t.emit("xori x5, x9, 3")
    t.emit("seqz x5, x5")

    def rest() -> None:
        t.emit("xori x5, x9, 2")
        t.emit("seqz x5, x5")
        t.either("x5", lambda: body(lo), lambda: body(0))

    t.either("x5", lambda: body(hi), rest)


# ---------------------------------------------------------------- trap window with a tval predicate
def pout(
    t: TestFile,
    expect: Expect,
    lab: str,
    desc: str,
    pred: Callable[[], object] | None = None,
    epc: bool = True,
    origin: str | None = None,
    save_count: bool = False,
) -> None:
    """TestFile.outcome, plus pred() (a computed xtval check) when a trap was taken, and x9 = number of traps when
    save_count."""
    alts = expect if isinstance(expect, list) else [expect]
    oks = "ok" in alts
    causes = [a for a in alts if a != "ok"]
    t.emit("AI_OUTCOME", 20)
    if save_count:
        t.emit("mv x9, x13")
    t.check("x13", [0, 1] if oks and causes else (0 if oks else 1), lab, f"{desc}: number of traps")
    t.check(
        "x14", [NO_TRAP if a == "ok" else a for a in alts], lab, f"{desc}: outcome (xcause, or all ones for no trap)"
    )
    if not causes:
        return
    skip, done = t.label("notrap"), t.label("checked")
    if oks:
        t.emit("li x5, -1")
        t.emit(f"beq x14, x5, {skip}")
    first = len(t.table)
    if epc:
        t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
        t.check("x15", lab, lab, f"{desc}: xepc is the trapping instruction")
    if pred:
        pred()
    if origin:
        t.emit("AI_ORIGIN", 25)
        t.check(
            "x15",
            ORIGIN[origin],
            lab,
            f"{desc}: xPP/xPV record the mode the trap came from (0 U, 1 S, 3 M, 4 VU, 5 VS)",
        )
    if oks:
        t.emit(f"j {done}")
        t.emit(f"{skip}:", 0)
        t.code += t._skip_lines(first, len(t.table))
        t.emit(f"{done}:", 0)


def pred_exact(t: TestFile, lab: str, desc: str) -> Callable[[], None]:
    """xtval is 0 or the address in x1."""

    def f() -> None:
        t.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
        t.emit("xor x5, x15, x1")
        t.emit("seqz x5, x5")
        t.emit("seqz x15, x15")
        t.emit("or x15, x15, x5")
        t.check_bool("x15", lab, f"{desc}: xtval is 0 or the transformed address")

    return f


def pred_exact_cross(t: TestFile, lab: str, desc: str) -> Callable[[], None]:
    """xtval is 0, the address in x1, or the start of the next page (the faulting portion of a page-crossing
    access)."""

    def f() -> None:
        t.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
        t.emit("xor x5, x15, x1")
        t.emit("seqz x5, x5")
        t.emit("seqz x14, x15")
        t.emit("or x5, x5, x14")
        t.emit("srli x14, x1, 12")
        t.emit("addi x14, x14, 1")
        t.emit("slli x14, x14, 12")
        t.emit("xor x15, x15, x14")
        t.emit("seqz x15, x15")
        t.emit("or x15, x15, x5")
        t.check_bool("x15", lab, f"{desc}: xtval is 0, the transformed address, or the start of the second page")

    return f


def pred_not(t: TestFile, lab: str, desc: str) -> Callable[[], None]:
    """xtval is not the address in x1 (the masked, valid base: reporting it would mean the hardware masked an
    address it did not use)."""

    def f() -> None:
        t.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
        t.emit("xor x15, x15, x1")
        t.emit("snez x15, x15")
        t.check_bool("x15", lab, f"{desc}: xtval is not the masked address (the access was not masked)")

    return f


MPRV_MODES = {"MPRV_M": 3, "MPRV_S": 1, "MPRV_U": 0}


def window(
    t: TestFile,
    mode: str,
    lines: list[str],
    expect: Expect,
    desc: str,
    pred: Callable[[str], Callable[[], object]] | None = None,
    save_count: bool = False,
    epc: bool = True,
) -> str:
    """Run lines in mode (entered from t.cur when different) in a trap window; the first line may trap.
    mode MPRV_M/MPRV_S/MPRV_U: from M-mode, the lines run with mstatus.MPRV=1 and MPP = M/S/U (x9 holds the MPRV
    bit, so the lines must not write x9)."""
    lab = t.label(f"in_{mode}")
    mpp = MPRV_MODES.get(mode)
    if mpp is not None:
        assert t.cur == "M"
        t.emit(f"li x9, {hex(MPP)}")
        t.emit("csrc mstatus, x9  // MPP = 0")
        if mpp:
            t.emit(f"li x9, {hex(mpp << 11)}")
            t.emit(f"csrs mstatus, x9  // MPP = {mpp}")
        t.allow(1)
        t.emit(f"li x9, {hex(MPRV)}")
        t.emit("csrs mstatus, x9  // MPRV = 1")
        t.emit(f"{lab}:", 0)
        for ln in lines:
            t.emit(ln)
        t.emit("csrc mstatus, x9  // MPRV = 0")
        origin = "M"
        desc = f"{desc} with MPRV=1, MPP={'MSU'[[3, 1, 0].index(mpp)]}"
    else:
        t.allow(1)
        if mode != t.cur:
            t.enter(mode)
        t.emit(f"{lab}:", 0)
        for ln in lines:
            t.emit(ln)
        if mode != t.cur:
            t.leave()
        origin = mode
        desc = f"{desc} in {mode}-mode"
    p = pred(lab) if pred else None
    pout(t, expect, lab, desc, p, epc=epc, origin=origin, save_count=save_count)
    return lab


# ---------------------------------------------------------------- addresses
IDENT_REP = 0x8012_3000  # representative physical address of the test image (it lies below 2^38)


class Addr:
    """A tagged effective address: base = data page `page` + off, its high-half alias (hi), or a constant VA
    (const), with its top q bits replaced by tag (a 64-bit value with bits only in the top q bits).

    space: "pa" (physical: M-mode, or satp/vsatp Bare with no G-stage), "gpa" (guest physical: vsatp Bare with
    G-stage translation), or "va" (vabits-bit virtual address; the page table identity-maps the root-level page
    holding the image and maps the last root-level page, the top of the high half, to the same page; R is the
    shift of a root-level page)."""

    def __init__(
        self,
        page: str | None,
        off: int,
        tag: int = 0,
        q: int = 7,
        space: str = "pa",
        vabits: int = 0,
        R: int = 0,
        hi: bool = False,
        const: int | None = None,
    ) -> None:
        assert tag & ~tagmask(q) == 0
        self.page, self.off, self.tag, self.q = page, off, tag, q
        self.space, self.vabits, self.R, self.hi, self.const = space, vabits, R, hi, const

    def moved(self, off: int) -> Addr:
        return Addr(
            self.page,
            self.off + off,
            self.tag,
            self.q,
            self.space,
            self.vabits,
            self.R,
            self.hi,
            None if self.const is None else self.const + off,
        )

    def rep(self) -> int:
        """A representative base: only bits >= 38 depend on where the image is."""
        if self.const is not None:
            return self.const
        if self.hi:
            return ((-(1 << self.R)) & M64) | (0x123000 + self.off)
        return IDENT_REP + self.off

    def tagged_rep(self) -> int:
        return (self.rep() & ~tagmask(self.q)) | self.tag

    def tr_rep(self, p: int) -> int:
        return transform(self.tagged_rep(), p, self.space == "va", self.vabits)

    def mapped(self, tr: int) -> bool:
        if not canonical(tr, self.vabits):
            return False
        idx = tr >> self.R
        low = (1 << self.R) - 1
        return idx in (IDENT_REP >> self.R, M64 >> self.R) and (tr & low) == (self.rep() & low)

    def ok(self, p: int) -> bool:
        tr = self.tr_rep(p)
        if self.space == "va":
            return self.mapped(tr)
        return tr == self.rep()

    def tval_exact(self, p: int) -> bool:
        """A fault on a transformed address that is a valid (canonical) VA: xtval is 0 or exactly that VA."""
        tr = self.tr_rep(p)
        return self.space == "va" and not self.ok(p) and canonical(tr, self.vabits)

    def emit(self, t: TestFile, p: int | None = None) -> None:
        """x6 = the tagged address; x1 = the untagged base, or, when p is given and tval_exact(p), the transformed
        address. Clobbers x9."""
        if self.const is not None:
            t.emit(f"li x6, {hex(self.const)}", 6)
        else:
            t.la("x6", f"ai_pg_{self.page}")
            if self.hi:
                t.emit(f"li x9, {hex((1 << self.R) - 1)}", 6)
                t.emit("and x6, x6, x9")
                t.emit(f"li x9, {hex((-(1 << self.R)) & M64)}", 6)
                t.emit("or x6, x6, x9")
            if -2048 <= self.off < 2048 and self.off:
                t.emit(f"addi x6, x6, {self.off}")
            elif self.off:
                t.emit(f"li x9, {self.off}")
                t.emit("add x6, x6, x9")
        t.emit("mv x1, x6")
        if p is not None and self.tval_exact(p):
            diff = (self.tr_rep(p) - self.rep()) & M64
            if diff:
                t.emit(f"li x9, {hex(diff)}", 6)
                t.emit("add x1, x1, x9")
        t.emit(f"li x9, {hex(~tagmask(self.q) & M64)}", 6)
        t.emit("and x6, x6, x9")
        if self.tag:
            t.emit(f"li x9, {hex(self.tag)}", 6)
            t.emit("or x6, x6, x9")
        if MUT == "tval_untransformed" and p is not None and self.tval_exact(p):
            t.emit("mv x1, x6")

    def __str__(self) -> str:
        if self.const is not None:
            b = hex(self.const)
        else:
            b = f"{'high-half alias of ' if self.hi else ''}{self.page}+{self.off}"
        sp = {"pa": "PA", "gpa": "GPA", "va": f"Sv{self.vabits} VA"}[self.space]
        return f"{sp} {b} with bits 63:{64 - self.q} = {hex(self.tag >> (64 - self.q))}"


# ---------------------------------------------------------------- access kinds
# name: (lines, kind, page offset, immediate, extension condition)
#   kind: load (x7 checked), store (memory checked through an untagged load), amo, lrsc, cbo
KINDS: dict[str, tuple[list[str], str, int, int, str | None]] = {
    "ld": (["ld x7, 0(x6)"], "load", 0, 0, None),
    "lw": (["lw x7, 12(x6)"], "load", 0, 12, None),  # imm 12: added before masking
    "lh": (["lh x7, 2(x6)"], "load", 0, 2, None),
    "lbu": (["lbu x7, 7(x6)"], "load", 0, 7, None),
    "sd": (["sd x8, 0(x6)"], "store", 16, 0, None),
    "sw": (["sw x8, 4(x6)"], "store", 24, 4, None),
    "sh": (["sh x8, 0(x6)"], "store", 32, 0, None),
    "sb": (["sb x8, 3(x6)"], "store", 40, 3, None),
    "amoadd.d": ([w("amoadd.d", "amoadd.d x7, x8, (x6)")], "amo", 48, 0, "defined(ZAAMO_SUPPORTED)"),
    "amoswap.w": ([w("amoswap.w", "amoswap.w x7, x8, (x6)")], "amo", 56, 0, "defined(ZAAMO_SUPPORTED)"),
    "lr.d": ([w("lr.d", "lr.d x7, (x6)"), w("sc.d", "sc.d x9, x8, (x6)")], "lrsc", 64, 0, "defined(ZALRSC_SUPPORTED)"),
    "flw": ([w("flw", "flw f1, 0(x6)"), w("fmv.x.w")], "load", 8, 0, "defined(F_SUPPORTED)"),
    "fsw": ([w("fsw", "fsw f1, 0(x6)")], "store", 72, 0, "defined(F_SUPPORTED)"),
    "vle64.v": ([w("vle64.v", "vle64.v v1, (x6)"), w("vmv.x.s")], "load", 0, 0, "defined(V_SUPPORTED)"),
    "vse64.v": ([w("vse64.v", "vse64.v v1, (x6)")], "store", 80, 0, "defined(V_SUPPORTED)"),
    "cbo.zero": ([w("cbo.zero", "cbo.zero (x6)")], "cbo", 0, 0, "defined(ZICBOZ_SUPPORTED)"),
}
INT_KINDS = ["ld", "lw", "lh", "lbu", "sd", "sw", "sh", "sb"]
ALL_KINDS = list(KINDS)
STORE_W = {"sd": (8, 0), "sw": (4, 4), "sh": (2, 0), "sb": (1, 3), "fsw": (4, 0), "vse64.v": (8, 0)}
OLD = 0x5A5A_A5A5_0F0F_F0F0
NEW = 0x1122_3344_5566_7788


def kind_cond(name: str) -> str | None:
    return KINDS[name][4]


def a_bytes() -> bytes:
    """The first 16 bytes of page A (sig(1) then PAT8): page A is always the first page."""
    return sig(1).to_bytes(8, "little") + PAT8.to_bytes(8, "little")


def load_value(name: str) -> int:
    b = a_bytes()
    if name in ("ld", "vle64.v"):
        return int.from_bytes(b[0:8], "little")
    if name == "lw":
        return sx(int.from_bytes(b[12:16], "little"), 32)
    if name == "lh":
        return sx(int.from_bytes(b[2:4], "little"), 16)
    if name == "lbu":
        return b[7]
    if name == "flw":
        return sx(int.from_bytes(b[8:12], "little"), 32)
    raise ValueError(name)


def store_result(name: str) -> int:
    n, o = STORE_W[name]
    mask = ((1 << (8 * n)) - 1) << (8 * o)
    return (OLD & ~mask) | ((NEW << (8 * o)) & mask)


def fault_cause(kind: str, space: str, gstage: bool = False) -> int:
    load = kind in ("load", "lr", "fetch")
    if kind == "fetch":
        return 12 if space == "va" else (20 if gstage else 1)
    if space == "va":
        return 13 if load else 15
    if space == "gpa" and gstage:
        return 21 if load else 23
    return 5 if load else 7


CLASS_MUT = {  # mutant -> access kinds it leaves unmasked
    "amo_unmasked": {"amoadd.d", "amoswap.w"},
    "lrsc_unmasked": {"lr.d"},
    "fp_unmasked": {"flw", "fsw"},
    "vec_unmasked": {"vle64.v", "vse64.v"},
    "cbo_unmasked": {"cbo.zero"},
    "subword_unmasked": {"lh", "lbu", "sh", "sb"},
}


def access(t: TestFile, mode: str, name: str, a: Addr, p: int, desc: str = "", gstage: bool = False) -> None:
    """One explicit access `name` to the tagged address a, run in `mode`, where PMLEN p is in effect for the access
    (0 when pointer masking does not apply). Checks the outcome, xtval, and the value loaded or the memory written.
    gstage: a guest-physical address goes through G-stage translation (faults are guest-page faults)."""
    lines, kind, off, imm, _ = KINDS[name]
    if name in CLASS_MUT.get(MUT, set()):
        p = 0
    a = a.moved(off)
    if kind == "cbo" and a.page:  # CBO.ZERO uses page Z, so page A's data survives
        a = Addr("Z", a.off, a.tag, a.q, a.space, a.vabits, a.R, a.hi, a.const)
    good = a.ok(p)
    exact = not good and a.tval_exact(p)
    d = f"{name} of {a}, PMLEN={p}{', ' + desc if desc else ''}"
    page = f"ai_pg_{a.page}"
    if kind in ("store", "amo", "lrsc", "cbo") and a.page:
        t.load("x7", OLD, "old memory value")
        t.la("x9", page)
        t.emit(f"sd x7, {a.off}(x9)")
    if name == "vse64.v":
        t.load("x8", NEW, "value to store")
        t.emit(w("vsetivli"))
        t.emit(w("vmv.s.x"))
    elif name == "fsw":
        t.load("x8", NEW, "value to store")
        t.emit(w("fmv.w.x"))
    elif kind in ("store", "amo", "lrsc"):
        t.load("x8", NEW, "value to store")
    if name == "vle64.v":
        t.emit(w("vsetivli"))
    a.emit(t, p if exact else None)
    if imm:
        t.emit(f"addi x1, x1, {imm}")
    cause = fault_cause("lr" if kind == "lrsc" else kind, a.space, gstage)
    if kind == "lrsc" and not good:
        lines = lines[:1]  # lr.d faults; sc.d is tried in a window of its own
    pr = (lambda lab: pred_exact(t, lab, d)) if exact else (lambda lab: pred_not(t, lab, d))
    window(t, mode, lines, "ok" if good else cause, d, None if good else pr)
    lab = t.label("val")
    t.emit(f"{lab}:", 0)
    if kind == "load" and good:
        t.check("x7", load_value(name), lab, f"{d}: loads the untagged location")
    if kind == "lrsc" and good:
        t.check("x7", OLD, lab, f"{d}: lr.d reads the untagged location")
    if kind == "amo" and good:
        t.check(
            "x7", OLD if name == "amoadd.d" else sx(OLD, 32), lab, f"{d}: returns the untagged location's old value"
        )
    if kind in ("store", "amo", "lrsc", "cbo") and a.page:
        t.la("x6", page)
        t.emit(f"ld x7, {a.off}(x6)")
        if kind == "lrsc" and good:
            # sc.d may succeed (x9 = 0, memory NEW) or fail (x9 != 0, memory OLD)
            t.emit("seqz x9, x9  // sc.d succeeded")
            t.load("x8", NEW, "NEW")
            t.emit("xor x8, x8, x7")
            t.emit("seqz x8, x8  // memory holds NEW")
            t.emit("and x8, x8, x9")
            t.load("x6", OLD, "OLD")
            t.emit("xor x6, x6, x7")
            t.emit("seqz x6, x6  // memory holds OLD")
            t.emit("xori x9, x9, 1")
            t.emit("and x6, x6, x9")
            t.emit("or x8, x8, x6")
            t.check_bool("x8", lab, f"{d}: sc.d succeeded and wrote the untagged location, or failed and wrote nothing")
        else:
            if kind == "store":
                exp = store_result(name) if good else OLD
            elif kind == "amo":
                if name == "amoadd.d":
                    exp = (OLD + NEW) & M64 if good else OLD
                else:
                    exp = ((OLD >> 32) << 32) | (NEW & 0xFFFFFFFF) if good else OLD
            elif kind == "cbo":
                exp = 0 if good else OLD
            else:
                exp = OLD
            what = "writes the untagged location" if good else "leaves the untagged location unchanged"
            t.check("x7", exp, lab, f"{d}: {what}")
    if kind == "lrsc" and not good:
        # sc.d with no reservation: it may raise the store fault, or fail without accessing memory
        # (zalrsc.adoc: it must fail; whether a failing SC to a faulting address traps is debatable, see the README)
        a.emit(t, None)
        t.load("x8", NEW, "value to store")
        t.emit("li x7, 0")
        ds = f"sc.d of {a} without a reservation, PMLEN={p}"
        window(
            t,
            mode,
            [w("sc.d7", "sc.d x7, x8, (x6)")],
            ["ok", fault_cause("store", a.space, gstage)],
            ds,
            lambda lab: pred_not(t, lab, d),
            save_count=True,
        )
        lab = t.label("sc")
        t.emit(f"{lab}:", 0)
        t.emit("snez x7, x7")
        t.emit("or x7, x7, x9")
        t.check_bool("x7", lab, f"{ds}: it trapped, or it failed (rd nonzero)")
        if a.page:
            t.la("x6", page)
            t.emit(f"ld x7, {a.off}(x6)")
            t.check("x7", OLD, lab, f"{ds}: the untagged location is unchanged")


# ---------------------------------------------------------------- page tables for satp (Sv39/Sv48/Sv57)
SCHEMES = {"sv39": (39, 3, 8), "sv48": (48, 4, 9), "sv57": (57, 5, 10)}  # VA bits, levels, satp.MODE
V, R_, W_, X_, U_, A_, D_ = 1, 2, 4, 8, 16, 64, 128
LEAF = V | R_ | W_ | X_ | A_ | D_


class SvPT:
    """A satp page table: root-level superpages only (plus pointers built by hand for the walk test)."""

    def __init__(self, t: MemTest, name: str, scheme: str) -> None:
        self.t, self.name, self.scheme = t, name, scheme
        self.vabits, self.levels, self.mode = SCHEMES[scheme]
        self.R = 12 + 9 * (self.levels - 1)  # shift of a root-level page
        self.root = t.pt_table(f"{name}_root")

    def _store_root(self, idx_reg: str, pte_reg: str) -> None:
        t = self.t
        t.emit(f"slli {idx_reg}, {idx_reg}, 3")
        t.la("x8", self.root)
        t.emit(f"add x8, x8, {idx_reg}")
        t.emit(f"sd {pte_reg}, 0(x8)")

    def identity(self, perms: int, n: int = 1) -> None:
        """Identity map n root-level pages from the one holding the test image."""
        t = self.t
        t.comment(f"{self.scheme}: identity map the test image ({n} root-level pages), perms {hex(perms)}")
        for k in range(n):
            t.la("x6", "rvtest_entry_point")
            t.emit(f"srli x6, x6, {self.R}")
            if k:
                t.emit(f"addi x6, x6, {k}")
            t.emit(f"slli x7, x6, {self.R - 2}")
            t.emit(f"li x9, {hex(perms)}")
            t.emit("or x7, x7, x9")
            t.emit("andi x6, x6, 511")
            self._store_root("x6", "x7")

    def hi_alias(self, page: str, perms: int) -> None:
        """Map the last root-level page (the top of the high half) to the root-level page holding `page`."""
        t = self.t
        t.comment(f"{self.scheme}: root entry 511 (high half) -> the root-level page of {page}, perms {hex(perms)}")
        t.la("x7", f"ai_pg_{page}")
        t.emit(f"srli x7, x7, {self.R}")
        t.emit(f"slli x7, x7, {self.R - 2}")
        t.emit(f"li x9, {hex(perms)}")
        t.emit("or x7, x7, x9")
        t.emit("li x6, 511")
        self._store_root("x6", "x7")

    def satp(self, reg: str = "x6") -> None:
        t = self.t
        t.la(reg, self.root)
        t.emit(f"srli {reg}, {reg}, 12")
        t.emit(f"li x9, {hex(self.mode << 60)}", 6)
        t.emit(f"or {reg}, {reg}, x9")


def satp_probe(t: MemTest, pt: SvPT, csr: str = "satp") -> None:
    """Write satp (or vsatp) for pt and leave x5 = 1 when MODE reads back (scheme supported), else 0 with satp
    unchanged (Bare): an unsupported MODE makes the whole write have no effect."""
    pt.satp("x6")
    if csr in DIRECT[t.cur]:
        t.emit(f"csrw {hex(CSRN[csr])}, x6  // {csr}")
        t.emit(f"csrr x5, {hex(CSRN[csr])}")
    else:
        t.tsbi_csr("WRITE", csr.upper(), "x6")
        t.tsbi_csr("READ", csr.upper())
        t.emit("mv x5, a0")
    t.emit("srli x5, x5, 60")
    t.emit(f"xori x5, x5, {pt.mode}")
    t.emit("seqz x5, x5")
    t.emit("sfence.vma" if csr == "satp" else ".word 0x22000073  // hfence.vvma")


def satp_off(t: MemTest, csr: str = "satp") -> None:
    if csr in DIRECT[t.cur]:
        t.emit(f"csrw {hex(CSRN[csr])}, x0  // {csr} = Bare")
    else:
        t.tsbi_csr("WRITE", csr.upper(), imm=0)
    t.emit("sfence.vma" if csr == "satp" else ".word 0x22000073  // hfence.vvma")


# ---------------------------------------------------------------- tags
def tags_basic(q: int) -> list[int]:
    """Tags exercising every masked bit position class for a q-bit tag."""
    sh = 64 - q
    out = [tagmask(q), (0x2A if q == 7 else 0xA5C3) << sh, 1 << 63, 1 << sh]
    return out


def boundary_tags() -> list[tuple[int, int]]:
    """(tag, q): single bits at the PMLEN boundaries: 57 (lowest bit PMLEN=7 masks), 56 (XLEN-PMLEN-1 for 7, masked by
    16), 48 (lowest bit PMLEN=16 masks), 47 (XLEN-PMLEN-1 for 16), plus a 9-bit pattern in 56:48."""
    return [(1 << 57, 7), (1 << 56, 16), (1 << 48, 16), (0x0155 << 48, 16)]
