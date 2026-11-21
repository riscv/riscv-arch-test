# SPDX-License-Identifier: Apache-2.0
"""Helpers for the vector memory rule-derived tests (gen_Vmem.py).

Tests use only integer vector instructions (MARCH ..._zve64x) and require V, so SEW 8..64 and LMUL 1/8..8 are
all supported and VLEN >= 128. Every expectation is VLEN-independent: element positions that are checked lie in
the first 16 bytes of a vector register, and anything that depends on VLEN is computed at run time.

- VTest: an SvTest (svlib.py) that also emits named data buffers whose bytes the generator knows.
- Register checks: an element is read by storing the register group with a whole-register store (vs<n>r.v) and
  loading the element with a sign-extending scalar load (SEW <= 32), or with vmv.x.s for element 0; 64-bit elements
  are read as two 32-bit words. No permutation instruction (slide) is used, so a test of a load or store does not
  depend on the permutation unit.
- Fault tests boot to S-mode and map two test pages at constant virtual addresses: page A (always valid) and the
  page after it, page B, whose PTE each test chooses (absent, read-only, valid). An element whose address lies in
  page B faults; the scheme is Sv39 (RV64) or Sv32 (RV32), probed at run time.

This module holds no expectations; gen_Vmem.py owns them (and the mutants).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

sys.path.insert(0, str(Path(__file__).parent))
from aigen import NO_TRAP, POOL_TRAP, TestFile, X
from svlib import BASE, LEAF, VA_T, A, D, R, SvPT, SvTest, V, W, guard, probe, satp_off

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect

ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
VEC = "src/unpriv/vector-common.adoc"
MARCH = "rv${XLEN}i_zicsr_zifencei_zve64x"
REQ = ["I", "V"]
REQ_S = ["I", "S", "V"]
FILL = 0xA5  # byte written into destination registers before a load (never a memory pattern byte or 0xFF)
LOAD_MIS, LOAD_AF, LOAD_PF = 4, 5, 13
STORE_MIS, STORE_AF, STORE_PF = 6, 7, 15
ILLEGAL = 2
PG = 0x1000
RO = V | R | A | D  # read-only leaf


def pat(seed: int, n: int) -> bytes:
    """n pattern bytes in 0x01..0x7e (never FILL, 0xff or 0): consecutive bytes differ for 126 positions."""
    return bytes(1 + ((seed * 53 + i * 29) % 126) for i in range(n))


def le(b: bytes | bytearray) -> int:
    return int.from_bytes(b, "little")


def sx(v: int, sew: int) -> X:
    """What vmv.x.s (or a sign-extending scalar load) of a sew-bit value gives at each XLEN."""
    v &= (1 << sew) - 1
    s = v - (1 << sew) if v >> (sew - 1) else v
    return X(s & 0xFFFFFFFF, s & ((1 << 64) - 1))


def ones(sew: int) -> int:
    return (1 << sew) - 1


def fill_elem(sew: int) -> int:
    return le(bytes([FILL]) * (sew // 8))


LMUL = {"mf8": 0.125, "mf4": 0.25, "mf2": 0.5, "m1": 1, "m2": 2, "m4": 4, "m8": 8}


def vlmax128(sew: int, lmul: str) -> int:
    """VLMAX at the smallest V VLEN (128): any vl up to this is granted exactly."""
    return int(128 // sew * LMUL[lmul])


VEL_SCR = ["  .p2align 6", "vm_vel_scr:", "  .fill 4096, 1, 0  // vel(): 8 registers at VLEN <= 4096"]


class VTest(SvTest):
    """SvTest with named data buffers (bytes known to the generator) and vector check helpers."""

    def __init__(self, *a: Any, **kw: Any) -> None:  # noqa: ANN401 (TestFile's arguments, passed through)
        super().__init__(*a, **kw)
        self.bufs: dict[str, tuple[int, bytes]] = {}
        self.lab = "rvtest_entry_point"  # label of the instruction under test, reported on a failed check
        self.vel_scr = False  # vel() used: emit its scratch buffer

    def buf(self, name: str, data: bytes, align: int = 6) -> str:
        lab = f"vm_{name}"
        assert lab not in self.bufs
        self.bufs[lab] = (align, data)
        return lab

    def _buf_data(self) -> list[str]:
        out = []
        for lab, (al, data) in self.bufs.items():
            out += [f"  .p2align {al}", f"{lab}:"]
            for i in range(0, len(data), 16):
                out.append("  .byte " + ", ".join(f"0x{b:02x}" for b in data[i : i + 16]))
        return out

    def render(self) -> str:
        self.extra_data = [
            "  // page tables, data pages and buffers (vmemlib.py)",
            *self._extra_data(),
            *self._block_data(),
            *self._buf_data(),
            *(VEL_SCR if self.vel_scr else []),
        ]
        return TestFile.render(self)

    # ---------- vector configuration
    def vset(self, vl: int | str, sew: int, lmul: str = "m1", ta: bool = False, ma: bool = False) -> None:
        """vl = vl (an int no larger than VLMAX at VLEN=128, or "max" for VLMAX), vtype = (sew, lmul, ta, ma).
        Clobbers x8."""
        pol = f"e{sew}, {lmul}, {'ta' if ta else 'tu'}, {'ma' if ma else 'mu'}"
        if vl == "max":
            self.emit(f"vsetvli x8, x0, {pol}")
        elif isinstance(vl, int) and vl <= 31:
            assert vl <= vlmax128(sew, lmul), f"vl {vl} > VLMAX at VLEN=128 for e{sew} {lmul}"
            self.emit(f"vsetivli x0, {vl}, {pol}")
        else:
            assert isinstance(vl, int) and vl <= vlmax128(sew, lmul)
            self.emit(f"li x8, {vl}")
            self.emit(f"vsetvli x0, x8, {pol}")

    def vfill(self, vreg: int, nregs: int = 1, byte: int = FILL) -> None:
        """Fill v[vreg .. vreg+nregs-1] (whole registers) with `byte`. Clobbers x7, x8, vl/vtype."""
        w = le(bytes([byte]) * 4)
        self.li("x7", w - (1 << 32) if w >> 31 else w)
        lm = {1: "m1", 2: "m2", 4: "m4", 8: "m8"}
        r = vreg
        left = nregs
        while left:
            n = (
                8
                if left >= 8 and r % 8 == 0
                else 4
                if left >= 4 and r % 4 == 0
                else 2
                if left >= 2 and r % 2 == 0
                else 1
            )
            self.emit(f"vsetvli x8, x0, e32, {lm[n]}, ta, ma")
            self.emit(f"vmv.v.x v{r}, x7")
            r += n
            left -= n

    def vmask(self, bits: int) -> None:
        """v0 = bits (mask elements 0..31), other bits 0. Clobbers x7, x8, vl/vtype."""
        self.emit("vsetvli x8, x0, e32, m1, ta, ma")
        self.emit("vmv.v.i v0, 0")
        self.li("x7", bits - (1 << 32) if bits >> 31 else bits)
        self.emit("vsetivli x0, 1, e32, m1, tu, mu")
        self.emit("vmv.s.x v0, x7")

    def vel(self, xr: str, vreg: int, idx: int, sew: int) -> None:
        """xr = element idx (a sew-bit element, sign-extended) of the register group starting at v[vreg]: the
        element at byte idx*sew/8 of v[vreg], v[vreg+1], ... concatenated, at any VLEN. The smallest group that
        holds idx at VLEN=128 is stored with a whole-register store (registers are laid out contiguously, whatever
        vtype) and the element is read with a scalar load; element 0 is read with vmv.x.s. No slide is used, so a
        memory test does not depend on the permutation unit. Clobbers vl/vtype (vsetivli also clears vstart, which
        a whole-register store honors) and xr's old value."""
        assert sew <= 32 and vreg < 32
        n = next(n for n in (1, 2, 4, 8) if vreg % n == 0 and idx < 16 * n // (sew // 8))
        assert idx < 16 * n // (sew // 8), f"element {idx} of v{vreg} is not reachable at VLEN=128"
        self.emit(f"vsetivli x0, 1, e{sew}, m{n}, ta, ma")
        if idx == 0:
            self.emit(f"vmv.x.s {xr}, v{vreg}")
            return
        self.vel_scr = True
        self.la(xr, "vm_vel_scr")
        self.emit(f"vs{n}r.v v{vreg}, ({xr})")
        load = {8: "lb", 16: "lh", 32: "lw"}[sew]  # sign-extending, like vmv.x.s
        self.emit(f"{load} {xr}, {idx * sew // 8}({xr})")

    def in_set(self, xr: str, vals: list, desc: str) -> None:
        """Check that xr equals one of vals (any number of values) with a branch-free predicate. Clobbers x8, x9."""
        if len(vals) <= 3:
            self.check(xr, vals, self.lab, desc)
            return
        self.emit("li x9, 0")
        for v in vals:
            self.load("x8", v)
            self.emit(f"sub x8, x8, {xr}")
            self.emit("seqz x8, x8")
            self.emit("or x9, x9, x8")
        self.check_bool("x9", self.lab, f"{desc}: one of {len(vals)} legal values")

    def ck_elem(self, vreg: int, idx: int, eew: int, alts: int | list[int], desc: str) -> None:
        """Check element idx (EEW eew) of register v[vreg] against 1-3 legal values. 64-bit elements are checked
        as two words (each word against the matching word of each alternative)."""
        al = alts if isinstance(alts, list) else [alts]
        if eew <= 32:
            self.vel("x7", vreg, idx, eew)
            self.in_set("x7", [sx(a, eew) for a in al], f"{desc}: v{vreg}[{idx}] (e{eew})")
            return
        for h in range(2):
            self.vel("x7", vreg, idx * 2 + h, 32)
            vals = []
            for a in al:
                w = sx(a >> (32 * h), 32)
                if w not in vals:
                    vals.append(w)
            self.in_set("x7", vals, f"{desc}: v{vreg}[{idx}] (e64) word {h}")

    def ck_reg(self, vreg: int, eew: int, elems: list, desc: str) -> None:
        """Check elements 0.. of v[vreg]; elems[i] is a value or a list of legal values (None: not checked)."""
        for i, e in enumerate(elems):
            if e is not None:
                self.ck_elem(vreg, i, eew, e, desc)

    def ck_mem(self, lab: str, off: int, data: list, desc: str, unit: int = 4, base_reg: str = "x9") -> None:
        """Check memory at lab+off: data[i] is the expected unit-byte value (or a list of legal values) of the i-th
        unit. Loads are sign-extending (lb/lh/lw). Clobbers base_reg and x7."""
        ld = {1: "lb", 2: "lh", 4: "lw"}[unit]
        self.la(base_reg, f"{lab}+{off}")
        for i, d in enumerate(data):
            if d is None:
                continue
            al = d if isinstance(d, list) else [d]
            self.emit(f"{ld} x7, {i * unit}({base_reg})")
            if len(al) > 3:
                self.emit(f"mv x1, {base_reg}")
                self.in_set("x7", [sx(a, unit * 8) for a in al], f"{desc}: bytes {lab}+{off + i * unit}")
                self.emit(f"mv {base_reg}, x1")
            else:
                self.check("x7", [sx(a, unit * 8) for a in al], self.lab, f"{desc}: bytes {lab}+{off + i * unit}")

    def vload(self, vreg: int, eew: int, values: list[int], name: str, lmul: str | None = None) -> None:
        """v[vreg] group = values (EEW eew, vl = len(values)) through a unit-stride load from a new buffer. Leaves
        vl = len(values) with SEW = eew. Clobbers x8, x9."""
        data = b"".join((v & ((1 << eew) - 1)).to_bytes(eew // 8, "little") for v in values)
        lab = self.buf(name, data + bytes(16))
        if lmul is None:
            lmul = next(m for m in ("m1", "m2", "m4", "m8") if len(values) <= vlmax128(eew, m))
        self.vset(len(values), eew, lmul)
        self.la("x9", lab)
        self.emit(f"vle{eew}.v v{vreg}, (x9)")

    def ck_csr(self, csr: str, expected: Expect, desc: str) -> None:
        self.emit(f"csrr x7, {csr}")
        self.check("x7", expected, self.lab, f"{desc}: {csr}")

    def mark(self, stem: str) -> str:
        """Emit a fresh label for the next instruction under test and make it the reported label."""
        self.lab = self.label(stem)
        self.emit(f"{self.lab}:", 0)
        return self.lab

    def win(self, lines: list[str], expect: Expect, desc: str, tval: Expect | None = None) -> str:
        """Run lines (the first is the instruction under test) in a trap window in the current mode. A trap
        must have xepc at the first line and xtval in tval (when given). The trap's origin mode is not checked
        (unprivileged tests run in the lowest mode, which may be M)."""
        self.allow(1)
        lab = self.mark("in")
        for ln in lines:
            self.emit(ln)
        self.outcome(expect, lab, desc, tval, origin=self.cur if self.boot else None)
        return lab


def lmul_for(n: int, eew: int) -> str:
    """The smallest integer LMUL whose VLMAX at VLEN=128 holds n elements of eew bits."""
    return next(m for m in ("m1", "m2", "m4", "m8") if n <= vlmax128(eew, m))


def elems(data: bytes, off: int, eew: int, n: int, stride: int | None = None) -> list[int]:
    """n EEW-bit little-endian elements of data starting at off, stride bytes apart (default EEW/8)."""
    s = eew // 8 if stride is None else stride
    return [le(data[off + i * s : off + i * s + eew // 8]) for i in range(n)]


# ---------------------------------------------------------------- fault tests: two test pages
class Pages:
    """Page A at VA_T (always mapped RW) and page B at VA_T + 4 KiB. Page A holds pattern bytes in its last
    256 bytes and page B in its first 256 bytes, so an access straddling VA_B reads A's tail then B's head."""

    def __init__(self, t: VTest, xlen: int, b_perms: int | None, seed: int = 7) -> None:
        self.t, self.xlen = t, xlen
        self.va_a = VA_T[xlen]
        self.va_b = self.va_a + PG
        self.a_data = pat(seed, 256)  # page A bytes [0xf00, 0x1000)
        self.b_data = pat(seed + 1, 256)  # page B bytes [0, 0x100)
        self.a = t.page(f"a{xlen}", {0xF00 + i: (1, b) for i, b in enumerate(self.a_data)})
        self.b = t.page(f"b{xlen}", {i: (1, b) for i, b in enumerate(self.b_data)})
        self.b_perms = b_perms
        self.pt = SvPT(t, f"p{xlen}", BASE[xlen])

    def window_bytes(self) -> bytes:
        """The 512 bytes from VA_B - 256 to VA_B + 256 (A's tail, B's head)."""
        return self.a_data + self.b_data

    def va(self, off: int) -> int:
        """Virtual address VA_B + off (off < 0 lies in page A)."""
        return self.va_b + off

    def setup(self, body: Callable[[Pages], None]) -> None:
        """Build the table, then (if satp accepts the scheme) run body with translation on; satp is Bare after."""
        t, pt = self.t, self.pt
        pt.identity()
        pt.leaf(self.va_a, self.a, LEAF, note="page A")
        if self.b_perms is not None:
            pt.leaf(self.va_b, self.b, self.b_perms, note="page B")
        probe(t, pt)

        def run() -> None:
            pt.on()
            body(self)
            satp_off(t)

        guard(t, "x1", run)

    def set_b(self, perms: int | None) -> None:
        """Rewrite page B's PTE (None: absent) and fence. Clobbers x6-x8."""
        if perms is None:
            self.pt.raw(self.va_b, 0, note="page B absent")
        else:
            self.pt.leaf(self.va_b, self.b, perms, note="page B")
        self.t.emit("sfence.vma x0, x0")

    def addr(self, reg: str, off: int) -> None:
        self.t.emit(f"li {reg}, {hex(self.va(off))}")


def both(t: VTest, body: Callable[[int], object]) -> None:
    with t.rv64_only():
        body(64)
    with t.rv32_only():
        body(32)


__all__ = [
    "FILL",
    "ILLEGAL",
    "ISSUE",
    "LEAF",
    "LMUL",
    "LOAD_AF",
    "LOAD_MIS",
    "LOAD_PF",
    "MARCH",
    "NO_TRAP",
    "PG",
    "POOL_TRAP",
    "REQ",
    "REQ_S",
    "RO",
    "STORE_AF",
    "STORE_MIS",
    "STORE_PF",
    "VEC",
    "Pages",
    "VTest",
    "W",
    "both",
    "elems",
    "fill_elem",
    "le",
    "lmul_for",
    "ones",
    "pat",
    "sx",
    "vlmax128",
]
