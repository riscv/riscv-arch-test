# SPDX-License-Identifier: Apache-2.0
"""Helpers for writing rule-derived, self-checking ACT tests (tests_ai/).

A generator builds one TestFile per normative rule. TestFile emits XLEN-independent
assembly: code is shared, and the expected-value table and description strings are emitted
twice, under #if __riscv_xlen == 64 / #else. Values are given as X(v32, v64) pairs (or a
plain int when both XLENs use the same mathematical value, which is then masked per XLEN).

The table is read in program order through x3 by AI_LOAD and AI_CHECK* (common/ai_macros.h).
"""

from __future__ import annotations

import hashlib
import random
import textwrap
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

ROOT = Path(__file__).resolve().parents[1]  # tests_ai/

# Registers a test may use for operands. x2-x5 are reserved by the framework and the
# check macros. x10-x12 are T-SBI arguments; x13-x15 hold trap-window state and results.
# Tests that use neither may use them for operands.
POOL_ALL = ["x1", "x6", "x7", "x8", "x9", "x10", "x11", "x12", "x13", "x14", "x15"]
POOL_NO_TSBI = ["x1", "x6", "x7", "x8", "x9", "x13", "x14", "x15"]
POOL_TRAP = ["x1", "x6", "x7", "x8", "x9"]


@dataclass(frozen=True)
class X:
    """A per-XLEN value: an int or a symbol (str, e.g. a label)."""

    v32: int | str
    v64: int | str

    def at(self, xlen: int) -> int | str:
        return self.v32 if xlen == 32 else self.v64

    def num(self, xlen: int) -> int:
        """The value at xlen, which must be a number (not a symbol)."""
        v = self.at(xlen)
        assert isinstance(v, int), f"{v!r} is a symbol"
        return v


if TYPE_CHECKING:  # annotations only, so the generators also run on Python 3.9
    Value = int | str | X  # one value, or a per-XLEN pair
    Expect = Value | list[Value]  # one expected value, or up to three legal alternatives
Conds = tuple[str, ...]  # preprocessor conditions of a table entry
T = TypeVar("T")


def xv(v: Value) -> X:
    return v if isinstance(v, X) else X(v, v)


def _groups(items: list[tuple[T, Conds]]) -> Iterator[tuple[Conds, list[T]]]:
    """Runs of consecutive items that share the same conditions."""
    cur: Conds = ()
    buf: list[T] = []
    for item, conds in items:
        if conds != cur and buf:
            yield cur, buf
            buf = []
        cur = conds
        buf.append(item)
    if buf:
        yield cur, buf


# Trap-window encodings (common/ai_macros.h)
NO_TRAP = X((1 << 32) - 1, (1 << 64) - 1)  # AI_OUTCOME's x14 when no trap was taken
ORIGIN = {"U": 0, "S": 1, "M": 3, "VU": 4, "VS": 5}  # AI_ORIGIN's x15


def mask(v: int, xlen: int) -> int:
    return v & ((1 << xlen) - 1)


def sext(v: int, bits: int) -> int:
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


def fmt(v: int | str, xlen: int) -> str:
    if isinstance(v, str):
        return v
    return f"0x{mask(v, xlen):0{xlen // 4}x}"


def wrap(text: str, indent: str = "//   ", width: int = 100) -> list[str]:
    out = []
    for para in text.strip().split("\n"):
        if not para.strip():
            out.append(indent.rstrip())
            continue
        lead = len(para) - len(para.lstrip())
        out += textwrap.wrap(
            para.strip(), width, initial_indent=indent + " " * lead, subsequent_indent=indent + " " * (lead + 2)
        ) or [indent]
    return out


class TestFile:
    """One test = one normative rule."""

    def __init__(
        self,
        suite: str,
        rule: str,
        *,
        required: list,
        march: str = "rv${XLEN}i_zicsr_zifencei",
        boot: str | None = None,
        params: dict | None = None,
        forbidden: list | None = None,
        pool: list[str] | None = None,
        rv64: bool = False,
        suffix: str = "",
    ) -> None:
        """rv64=True: the rule exists only on RV64; the whole body is under #if __riscv_xlen == 64 and the
        file passes trivially on RV32 (no MXLEN parameter is used). suffix distinguishes a second file for
        the same rule, e.g. "_Sm" for its M-mode part."""
        self.suite, self.rule = suite, rule
        self.required, self.forbidden = required, forbidden or []
        self.march, self.boot, self.params = march, boot, params or {}
        self.pool = list(pool or POOL_ALL)
        seed = int(hashlib.sha256(f"{suite}/{rule}".encode()).hexdigest()[:16], 16)
        self.rng = random.Random(seed)
        self.code: list[str] = []
        self.table: list[tuple[X, Conds]] = []
        self.strings: list[tuple[tuple[str, X], Conds]] = []  # ((label, per-XLEN text), conditions)
        self.doc: dict[str, str] = {}
        self.ninst = 0  # rough dynamic instruction estimate
        self._lab = 0
        self.cur = boot or "U"  # privilege mode the test body runs in (U: the lowest mode)
        self._conds: list[str] = []
        self.rv64, self.suffix = rv64, suffix
        if rv64:
            self.code.append("#if __riscv_xlen == 64")
            self._conds.append("__riscv_xlen == 64")

    # ---------- documentation ----------
    def describe(self, *, rule_text: str, source: str, context: str = "", issues: str = "", plan: str = "") -> None:
        self.doc = {"rule_text": rule_text, "source": source, "context": context, "issues": issues, "plan": plan}

    # ---------- randomness ----------
    def rand(self, bits: int) -> int:
        return self.rng.getrandbits(bits)

    def rand_x(self) -> X:
        """Random full-width value for each XLEN."""
        return X(self.rand(32), self.rand(64))

    def regs(self, n: int, exclude: tuple[str, ...] = ()) -> list[str]:
        cands = [r for r in self.pool if r not in exclude]
        return self.rng.sample(cands, n)

    @contextmanager
    def only_if(self, cond: str) -> Iterator[None]:
        """Code and table entries that exist only when the preprocessor condition holds, e.g.
        "__riscv_xlen == 64" or "defined(H_SUPPORTED)". The same #if wraps the table entries."""
        self.emit(f"#if {cond}", 0)
        self._conds.append(cond)
        yield
        self._conds.pop()
        self.emit("#endif", 0)

    def rv64_only(self) -> AbstractContextManager[None]:
        return self.only_if("__riscv_xlen == 64")

    def rv32_only(self) -> AbstractContextManager[None]:
        return self.only_if("__riscv_xlen == 32")

    def _entry(self, v: T) -> tuple[T, Conds]:
        return (v, tuple(self._conds))

    # ---------- code emission ----------
    def label(self, stem: str) -> str:
        self._lab += 1
        return f"{self.rule}_{stem}_{self._lab}"

    def comment(self, text: str) -> None:
        self.code.append(f"  // {text}")

    def blank(self) -> None:
        self.code.append("")

    def emit(self, line: str, n: int = 1) -> None:
        """Emit raw assembly; n is its dynamic instruction count for the budget."""
        self.code.append(("" if line.endswith(":") else "  ") + line)
        self.ninst += n

    def li(self, reg: str, value: int) -> None:
        """LI of a value that is the same at both XLENs (keep it 32-bit signed or small)."""
        self.emit(f"LI({reg}, {value})", 2)

    def la(self, reg: str, sym: str) -> None:
        self.emit(f"LA({reg}, {sym})", 2)

    def load(self, reg: str, value: int | str | X, note: str = "") -> None:
        """Load a per-XLEN value from the table; note is shown as a comment."""
        self.table.append(self._entry(xv(value)))
        self.emit(f"AI_LOAD({reg})" + (f"  // {note}" if note else ""), 2)

    def check(self, reg: str, expected: Expect, insn_label: str, desc: str) -> None:
        """Check reg against one expected value or a list of 2-3 legal values.

        expected: int | str | X, or a list of those (alternatives)."""
        alts = expected if isinstance(expected, list) else [expected]
        alts = [xv(a) for a in alts]
        assert 1 <= len(alts) <= 3
        self.table += [self._entry(a) for a in alts]
        slabel = f"{insn_label}_s{len(self.strings)}"
        d = xv(desc)
        text = X(*(f"{self.rule}: {d.at(x)}; expect " + " or ".join(fmt(a.at(x), x) for a in alts) for x in (32, 64)))
        self.strings.append(self._entry((slabel, text)))
        macro = {1: "AI_CHECK", 2: "AI_CHECK2", 3: "AI_CHECK3"}[len(alts)]
        self.emit(f"{macro}({reg}, {insn_label}, {slabel})", 2 + 2 * len(alts))

    def check_masked(
        self, reg: str, mask: Value, expected: Expect, insn_label: str, desc: str, tmp: str = "x4"
    ) -> None:
        """Check only the bits in mask (for fields whose other bits may legally hold any value).
        tmp is clobbered; x4 is safe because AI_CHECK reloads it."""
        self.load(tmp, mask, "mask of the checked bits")
        self.emit(f"and {tmp}, {tmp}, {reg}")
        self.check(tmp, expected, insn_label, desc)

    def check_bool(self, reg: str, insn_label: str, desc: str) -> None:
        """reg must hold 1 (a condition computed by the test)."""
        self.check(reg, 1, insn_label, desc)

    # ---------- trap windows (the framework trap log) ----------
    def allow(self, n: int = 1) -> None:
        """Open a trap window: permit up to n traps (AI_ALLOW; x13 holds the trap count)."""
        self.emit(f"AI_ALLOW({n})", 8)

    def outcome(
        self,
        expect: Expect,
        lab: str,
        desc: str,
        tval: Expect | None = None,
        epc: bool = True,
        origin: str | None = None,
    ) -> None:
        """Close the window opened by allow() and check its outcome.

        expect: "ok" (no trap), an exception or interrupt cause (int or X), or a list of up to three of
        those, any of which is legal. When a trap is legal, the log entry is also checked: xepc is lab
        (when epc), xtval is one of tval (when given), and the trap came from mode origin (when given:
        U, S, M, VU, VS). These checks are skipped when no trap was taken."""
        alts = expect if isinstance(expect, list) else [expect]
        oks = "ok" in alts
        causes = [a for a in alts if a != "ok"]
        self.emit("AI_OUTCOME", 20)
        self.check("x13", [0, 1] if oks and causes else (0 if oks else 1), lab, f"{desc}: number of traps")
        self.check(
            "x14",
            [NO_TRAP if a == "ok" else a for a in alts],
            lab,
            f"{desc}: outcome (xcause, or all ones for no trap)",
        )
        if not causes or not (epc or tval is not None or origin):
            return
        skip, done = self.label("notrap"), self.label("checked")
        if oks:
            self.emit("li x5, -1")
            self.emit(f"beq x14, x5, {skip}")
        first = len(self.table)
        if epc:
            self.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
            self.check("x15", lab, lab, f"{desc}: xepc is the trapping instruction")
        if tval is not None:
            self.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
            self.check("x15", tval, lab, f"{desc}: xtval is one of its legal values")
        if origin:
            self.emit("AI_ORIGIN", 25)
            self.check(
                "x15",
                ORIGIN[origin],
                lab,
                f"{desc}: xPP/xPV record the mode the trap came from (0 U, 1 S, 3 M, 4 VU, 5 VS)",
            )
        if oks:
            self.emit(f"j {done}")
            self.emit(f"{skip}:", 0)
            self.emit(f"AI_SKIP({len(self.table) - first})")
            self.emit(f"{done}:", 0)

    # ---------- privilege-mode windows ----------
    def enter(self, mode: str) -> None:
        """From the current mode (S or M, see self.cur), enter `mode` through sret/mret: U, VS or VU
        from S; S or U from M. The next instruction runs in `mode`. Uses x14."""
        after = self.label(f"in{mode}")
        self.la("x14", after)
        if self.cur == "S":
            self.emit("csrw sepc, x14")
            self.li("x14", 0x100)  # SPP
            self.emit(f"{'csrs' if mode == 'VS' else 'csrc'} sstatus, x14")
            self.emit("#ifdef H_SUPPORTED", 0)
            self.emit("LI(x14, HSTATUS_SPV)", 2)
            self.emit(f"{'csrs' if mode in ('VS', 'VU') else 'csrc'} CSR_HSTATUS, x14")
            self.emit("#endif", 0)
            self.emit("sret")
        else:
            assert self.cur == "M" and mode in ("S", "U")
            self.emit("csrw mepc, x14")
            self.emit("LI(x14, MSTATUS_MPP)", 2)
            self.emit("csrc mstatus, x14")
            if mode == "S":
                self.emit("LI(x14, MPP_SMODE)", 2)
                self.emit("csrs mstatus, x14")
            self.emit("mret")
        self.emit(f"{after}:", 0)

    def leave(self) -> None:
        """Return from a lower mode to the current mode through T-SBI (clobbers a0)."""
        self.emit(f"RVTEST_TSBI_GOTO_{self.cur}MODE", 120)

    def window(
        self,
        mode: str,
        lines: list[str],
        expect: Expect,
        desc: str,
        tval: Expect | None = None,
        origin: str | None = None,
    ) -> str:
        """Run `lines` in `mode` (entered from and returning to self.cur when different) inside a trap
        window, and check the outcome (see outcome()). The first line is the instruction that may trap.
        A trap must come from `origin` (default: `mode`). Returns its label."""
        lab = self.label(f"in_{mode}")
        self.allow(1)
        if mode != self.cur:
            self.enter(mode)
        self.emit(f"{lab}:", 0)
        for ln in lines:
            self.emit(ln)
        if mode != self.cur:
            self.leave()
        self.outcome(expect, lab, f"{desc} in {mode}-mode", tval, origin=origin or mode)
        return lab

    # ---------- T-SBI ----------
    def tsbi_csr(self, op: str, csr: str, value_reg: str | None = None, imm: int | None = None) -> None:
        """op: READ/WRITE/SET/CLEAR; value from value_reg (mv to a1) or imm (LI to a1). Result in a0."""
        if op != "READ":
            if value_reg is not None:
                if value_reg != "a1":
                    self.emit(f"mv a1, {value_reg}")
            else:
                assert imm is not None, "tsbi_csr needs value_reg or imm"
                self.li("a1", imm)
        self.emit(f"RVTEST_TSBI_CSR_ACCESS TSBI_CSR_{op}(CSR_{csr.upper()})", 120)

    # ---------- output ----------
    def _header(self) -> list[str]:
        d = self.doc
        h = [
            "///////////////////////////////////////////",
            f"// tests_ai/{self.suite}/{self.rule}{self.suffix}.S",
            f"// Generated by tests_ai/gen/gen_{self.suite}.py. Edit the generator, not this file.",
            "// SPDX-License-Identifier: Apache-2.0",
            "///////////////////////////////////////////",
            "//",
            f"// Normative rule {self.rule} ({d['source']}):",
        ]
        h += wrap(d["rule_text"])
        for key, title in (("context", "Context"), ("issues", "Clarifications"), ("plan", "Test plan")):
            if d.get(key):
                h += ["//", f"// {title}:"] + wrap(d[key])
        h += ["//", f"// Approximate dynamic instruction count: {self.ninst}", "//", ""]
        return h

    def _config(self) -> list[str]:
        def ext(e: str | list[str]) -> str:
            return f"[{', '.join(repr(x) for x in e)}]" if isinstance(e, list) else repr(e)

        c = ["##### START_TEST_CONFIG #####", f"# REQUIRED_EXTENSIONS: [{', '.join(ext(e) for e in self.required)}]"]
        if self.forbidden:
            c.append(f"# FORBIDDEN_EXTENSIONS: [{', '.join(repr(e) for e in self.forbidden)}]")
        if self.params:
            c.append("# params:")
            c += [f"#   {k}: {v}" for k, v in self.params.items()]
        c += [f"# MARCH: {self.march}", "# NEEDS_SIGNATURE: false", "##### END_TEST_CONFIG #####", ""]
        return c

    def _data(self, xlen: int) -> list[str]:
        directive = ".dword" if xlen == 64 else ".word"
        out = [f"{'#if __riscv_xlen == 64' if xlen == 64 else '#else'}"]

        other = f"__riscv_xlen == {96 - xlen}"
        for conds, vals in _groups(self.table):
            if other in conds:
                continue
            conds = tuple(c for c in conds if c != f"__riscv_xlen == {xlen}")
            if conds:
                out.append("#if " + " && ".join(f"({c})" for c in conds))
            vs = [v.at(xlen) for v in vals]
            for i in range(0, len(vs), 4):
                out.append(f"  {directive} " + ", ".join(fmt(v, xlen) for v in vs[i : i + 4]))
            if conds:
                out.append("#endif")
        for conds, strs in _groups(self.strings):
            if other in conds:
                continue
            conds = tuple(c for c in conds if c != f"__riscv_xlen == {xlen}")
            if conds:
                out.append("#if " + " && ".join(f"({c})" for c in conds))
            for lab, text in strs:
                st = str(text.at(xlen)).replace("\\", "\\\\").replace('"', '\\"')
                out.append(f'{lab}: .string "{st}"')
            if conds:
                out.append("#endif")
        return out

    def render(self) -> str:
        assert self.doc, "call describe() first"
        assert self.ninst < 100_000, f"{self.rule}: ~{self.ninst} dynamic instructions exceeds 100k"
        lines = self._header() + self._config()
        lines.append("#define SIGUPD_COUNT 0")
        if self.boot:
            lines.append(f"#define BOOT_TO_{self.boot}MODE")
        lines += [
            '#include "riscv_arch_test.h"',
            '#include "../common/ai_macros.h"',
            "",
            "RVTEST_BEGIN",
            "  LA(x3, ai_table)",
            "",
        ]
        lines += self.code
        if self.rv64:
            lines.append("#endif")
        lines += ["", "RVTEST_CODE_END", "", "RVTEST_DATA_BEGIN", "  .p2align 3", "ai_table:"]
        lines += self._data(64) + self._data(32) + ["#endif", "", "RVTEST_DATA_END", "", "RVTEST_SIG_SETUP", ""]
        return "\n".join(lines)

    def write(self) -> Path:
        path = ROOT / self.suite / f"{self.rule}{self.suffix}.S"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render())
        return path
