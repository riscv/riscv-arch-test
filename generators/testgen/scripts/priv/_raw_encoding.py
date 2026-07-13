"""Raw .4byte encoding helper for SsstrictV reserved-encoding generators.

Many SsstrictV coverpoints sample reserved encodings the GAS assembler refuses
to emit (vd=v0 for vadc, vm=1 for unmasked-only ops, vs2!=v0 for vmv.v.v,
mew=1 for vector loads/stores, etc.). This module provides:

  - ``MATCH``: dict of base instruction-word values, parsed from
    ``tests/env/encoding.h``.
  - ``encode(instr)``: return the all-zero-fields base encoding for any vector
    instruction, including segment LS forms whose names are synthesised from
    the corresponding non-segment encoding plus an ``nf`` field.
  - ``set_field(word, lo, hi, val)``: bit-slice mutator.
  - Convenience helpers for the standard fields.

The generators that consume this module emit a normal trap-eligible vsetivli
plus operand-init prologue, then ``.4byte 0x...`` for the test instruction
itself, then run the standard SsstrictV epilog via ``writeVecTest``.
"""

from __future__ import annotations

import re
from pathlib import Path

import vector_testgen_common as common


def _parse_matches() -> dict[str, int]:
    enc_h = Path(__file__).resolve().parents[4] / "tests" / "env" / "encoding.h"
    out: dict[str, int] = {}
    pat = re.compile(r"^#define MATCH_(\S+)\s+0x([0-9a-fA-F]+)")
    with enc_h.open() as f:
        for line in f:
            m = pat.match(line)
            if m:
                out[m.group(1)] = int(m.group(2), 16)
    return out


MATCH: dict[str, int] = _parse_matches()


_SEG_PATTERNS = [
    # vlseg<n>e<ew>(ff)?.v / vsseg<n>e<ew>(ff)?.v
    (re.compile(r"^V(L|S)SEG(\d+)E(\d+)(FF)?_V$"),
     lambda m: f'V{m.group(1)}E{m.group(3)}{m.group(4) or ""}_V',
     lambda m: int(m.group(2))),
    # vlsseg / vssseg (strided segment)
    (re.compile(r"^V(L|S)SSEG(\d+)E(\d+)_V$"),
     lambda m: f'V{m.group(1)}SE{m.group(3)}_V',
     lambda m: int(m.group(2))),
    # vluxseg / vloxseg / vsuxseg / vsoxseg (indexed segment)
    (re.compile(r"^V(L|S)([OU])XSEG(\d+)EI(\d+)_V$"),
     lambda m: f'V{m.group(1)}{m.group(2)}XEI{m.group(4)}_V',
     lambda m: int(m.group(3))),
]


def encode(instr: str) -> int | None:
    """Return base encoding (all variable fields zero) for ``instr``."""
    name = instr.upper().replace(".", "_")
    if name in MATCH:
        return MATCH[name]
    for pat, basef, nff in _SEG_PATTERNS:
        m = pat.match(name)
        if m:
            base = basef(m)
            if base in MATCH:
                return MATCH[base] | ((nff(m) - 1) << 29)
    return None


def set_field(word: int, hi: int, lo: int, val: int) -> int:
    width = hi - lo + 1
    mask = ((1 << width) - 1) << lo
    return (word & ~mask) | ((val & ((1 << width) - 1)) << lo)


def with_vd(word: int, vd: int) -> int:
    return set_field(word, 11, 7, vd)


def with_vs1(word: int, vs1: int) -> int:
    return set_field(word, 19, 15, vs1)


def with_vs2(word: int, vs2: int) -> int:
    return set_field(word, 24, 20, vs2)


def with_rs1(word: int, rs1: int) -> int:
    return set_field(word, 19, 15, rs1)


def with_vm(word: int, vm: int) -> int:
    return set_field(word, 25, 25, vm)


def with_mew(word: int, mew: int) -> int:
    return set_field(word, 28, 28, mew)


def with_nf(word: int, nf: int) -> int:
    return set_field(word, 31, 29, nf)


def emit_vsetivli(scratch: int, vl: int, sew: int, lmul_flag: str = "m1") -> None:
    common.writeLine(
        f"vsetivli x{scratch}, {vl}, e{sew}, {lmul_flag}, tu, mu",
        f"# vill=0, vstart=0, vl={vl}, sew={sew}, lmul={lmul_flag}",
    )


def emit_init_vec(scratch: int, vreg: int, sew: int) -> None:
    common.writeLine(f"la x{scratch}, random_mask_0", f"# scratch <- &random_mask_0")
    common.writeLine(f"vle{sew}.v v{vreg}, (x{scratch})", f"# init v{vreg}")


def emit_raw_test(instruction: str, cp: str, encoded: int, *,
                  sew: int = 8, lmul_flag: str = "m1", vl: int = 1,
                  init_vregs: tuple[int, ...] = (),
                  rs1_addr: bool = False,
                  rs2_zero: bool = False,
                  scratch: int = 6,
                  comment: str = "") -> None:
    """Emit a single .4byte raw-encoding test under trap-eligible state.

    Wrapper around ``writeVecTest`` for SsstrictV reserved-encoding tests
    whose mnemonic/operand combination the assembler refuses.

    Args:
        instruction: instruction name (controls reporting / signature path).
        cp: coverpoint id.
        encoded: complete 32-bit instruction word.
        sew/lmul_flag/vl: vsetivli pre-state.
        init_vregs: vector regs to zero-initialise (load random_mask_0 over).
        rs1_addr: if True, set x1 = la random_mask_0 so the encoding's rs1=x1
            points to a valid LS address (caller must encode rs1=1).
        rs2_zero: if True, set x2 = 0 so the encoding's rs2=x2 (used by some
            strided-LS reserved tests) is a stride of 0.
        scratch: scratch GPR (must NOT be 0; default 6 is safe).
        comment: extra comment for the .4byte line.
    """
    from ._ssstrictv_helpers import sig_params

    common.writeLine(f"\n# Testcase {cp} ({instruction}) raw=0x{encoded:08x} {comment}")
    emit_vsetivli(scratch, vl=vl, sew=sew, lmul_flag=lmul_flag)
    if rs1_addr:
        common.writeLine("la x1, random_mask_0", "# rs1=x1 -> valid LS address")
    if rs2_zero:
        common.writeLine("li x2, 0", "# rs2=x2 = 0 (stride 0)")
    for vreg in init_vregs:
        emit_init_vec(scratch, vreg, sew)
    # Re-emit vsetivli right before the test so SAMPLE_BEFORE captures vtype.
    emit_vsetivli(scratch, vl=vl, sew=sew, lmul_flag=lmul_flag)

    testline = f".4byte 0x{encoded:08x}  # {instruction} reserved encoding"

    common.add_testcase_string(cp, instruction)
    # Use vd=0 / sew/lmul=1 for signature emission; the trap (or its absence)
    # is what matters for cross-model comparison.
    common.writeVecTest(
        instruction, cp, 0, sew if sew in (8, 16, 32, 64) else 8, testline,
        test=instruction, rd=0, vl=1, lmul=1,
        sig_lmul=1, sig_whole_register_store=True,
        priv=True, skip_sigupd=True,
    )
