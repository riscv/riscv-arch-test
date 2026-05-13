"""Batch generator for SsstrictV "register-overlap" reserved-encoding coverpoints.

Each of these coverpoints is satisfied by setting up a trap-eligible vtype/vstart/
vl/mstatus pre-state and then issuing the instruction with specific vd/vs1/vs2
register overrides that satisfy the encoding-bit constraints.

Patterns covered:
- vd == vs1 / vd == vs2 at LMUL=1 (entire register equality)
- vd group overlaps vs1/vs2 group at LMUL>1 (partial overlap by sharing top
  4/3/2 bits of the 5-bit reg field)
- vd == v0 (overlap with implicit mask register)
"""

from __future__ import annotations

import vector_testgen_common as common
from priv_coverpoint_registry import register

from ._ssstrictv_helpers import issue_simple_test, max_legal_lmul


# Pairs of registers used to satisfy <role>_vd_overlap_lmul<L> coverpoints.
# `vs?_vd_overlap_lmul<L>` requires insn[X:Y] == insn[11:Y] where the slice
# masks off the LMUL-aligned top bits. Concretely (vd, other) pairs below
# differ by 1 (smaller than the LMUL group size) so the high bits match.
_OVERLAP_PAIRS = {
    1: (2, 3),   # vd=2, other=3 -> top4 bits match (group of 2)
    2: (4, 6),   # vd=4, other=6 -> top3 bits match (group of 4)
    4: (8, 12),  # vd=8, other=12 -> top2 bits match (group of 8)
}

# vd that is aligned to LMUL (used by widen/narrow templates that also require
# vd_reg_aligned_lmul_<L>).
_VD_ALIGNED = {1: 4, 2: 4, 4: 8, 8: 16}


def _emit_vd_eq_role(instruction: str, cp: str, lmul: int, role: str,
                     vd: int = 4) -> None:
    """vd == role (full equality) at given LMUL."""
    args = common.getInstructionArguments(instruction)
    if role not in args:
        return
    kwargs = {"override_vd": vd}
    if role == "vs1":
        kwargs["override_vs1"] = vd
    elif role == "vs2":
        kwargs["override_vs2"] = vd
    issue_simple_test(instruction, cp, lmul=lmul, maskval=None, **kwargs)


def _emit_partial_overlap(instruction: str, cp: str, lmul: int, role: str) -> None:
    """vd group overlaps role group at LMUL>1 (insn-bit-slice match)."""
    args = common.getInstructionArguments(instruction)
    if role not in args:
        return
    if lmul not in _OVERLAP_PAIRS:
        return
    vd, other = _OVERLAP_PAIRS[lmul]
    kwargs = {"override_vd": vd}
    if role == "vs1":
        kwargs["override_vs1"] = other
    elif role == "vs2":
        kwargs["override_vs2"] = other
    issue_simple_test(instruction, cp, lmul=lmul, maskval=None, **kwargs)


# ---------------------------------------------------------------------------
# vrgather: vd may not overlap vs1 OR vs2 register group
# ---------------------------------------------------------------------------

@register("cp_ssstrictv_vrgather_vd_vs1_eq")
def vrgather_vs1_eq(instruction: str) -> None:
    cp = "cp_ssstrictv_vrgather_vd_vs1_eq"
    cap = max_legal_lmul(instruction)
    for lmul in (1, 2, 4, 8):
        if lmul > cap:
            break
        _emit_vd_eq_role(instruction, cp, lmul=lmul, role="vs1")


@register("cp_exceptionsv_vd_vs2_overlap")
def exceptionsv_vd_vs2_overlap(instruction: str) -> None:
    cp = "cp_exceptionsv_vd_vs2_overlap"
    cap = max_legal_lmul(instruction)
    for lmul in (1, 2, 4, 8):
        if lmul > cap:
            break
        _emit_vd_eq_role(instruction, cp, lmul=lmul, role="vs2")


@register("cp_ssstrictv_vrgather_vd_vs2_eq")
def vrgather_vs2_eq(instruction: str) -> None:
    cp = "cp_ssstrictv_vrgather_vd_vs2_eq"
    cap = max_legal_lmul(instruction)
    for lmul in (1, 2, 4, 8):
        if lmul > cap:
            break
        _emit_vd_eq_role(instruction, cp, lmul=lmul, role="vs2")


@register("cp_ssstrictv_vrgather_vd_vs1_overlap")
def vrgather_vs1_overlap(instruction: str) -> None:
    cp = "cp_ssstrictv_vrgather_vd_vs1_overlap"
    cap = max_legal_lmul(instruction)
    _emit_vd_eq_role(instruction, cp, lmul=1, role="vs1")
    for lmul in (2, 4):
        if lmul > cap:
            break
        _emit_partial_overlap(instruction, cp, lmul=lmul, role="vs1")


@register("cp_ssstrictv_vrgather_vd_vs2_overlap")
def vrgather_vs2_overlap(instruction: str) -> None:
    cp = "cp_ssstrictv_vrgather_vd_vs2_overlap"
    cap = max_legal_lmul(instruction)
    _emit_vd_eq_role(instruction, cp, lmul=1, role="vs2")
    for lmul in (2, 4, 8):
        if lmul > cap:
            break
        _emit_partial_overlap(instruction, cp, lmul=lmul, role="vs2")


# ---------------------------------------------------------------------------
# vslideup / vslide1up: vd may not overlap vs2 register group
# ---------------------------------------------------------------------------

@register("cp_ssstrictv_vslideup_vd_vs2_overlap")
def vslideup_vs2_overlap(instruction: str) -> None:
    cp = "cp_ssstrictv_vslideup_vd_vs2_overlap"
    cap = max_legal_lmul(instruction)
    _emit_vd_eq_role(instruction, cp, lmul=1, role="vs2")
    for lmul in (2, 4):
        if lmul > cap:
            break
        _emit_partial_overlap(instruction, cp, lmul=lmul, role="vs2")


@register("cp_ssstrictv_vslide1up_vd_vs2_overlap")
def vslide1up_vs2_overlap(instruction: str) -> None:
    cp = "cp_ssstrictv_vslide1up_vd_vs2_overlap"
    cap = max_legal_lmul(instruction)
    _emit_vd_eq_role(instruction, cp, lmul=1, role="vs2")
    for lmul in (2, 4):
        if lmul > cap:
            break
        _emit_partial_overlap(instruction, cp, lmul=lmul, role="vs2")


# ---------------------------------------------------------------------------
# vcompress: vd may not overlap vs2 (source) or v0 (mask)
# ---------------------------------------------------------------------------

@register("cp_ssstrictv_vcompress_vd_vs2_overlap")
def vcompress_vs2_overlap(instruction: str) -> None:
    cp = "cp_ssstrictv_vcompress_vd_vs2_overlap"
    cap = max_legal_lmul(instruction)
    _emit_vd_eq_role(instruction, cp, lmul=1, role="vs2")
    for lmul in (2, 4):
        if lmul > cap:
            break
        _emit_partial_overlap(instruction, cp, lmul=lmul, role="vs2")


@register("cp_ssstrictv_vcompress_vd_v0_overlap")
def vcompress_vd_v0_overlap(instruction: str) -> None:
    cp = "cp_ssstrictv_vcompress_vd_v0_overlap"
    cap = max_legal_lmul(instruction)
    for lmul in (1, 2, 4, 8):
        if lmul > cap:
            break
        issue_simple_test(instruction, cp, lmul=lmul, override_vd=0, maskval=None)


# ---------------------------------------------------------------------------
# vsext/vzext vfN: vd group must not overlap vs2 (source). At LMUL=N (i.e.
# dest LMUL=N, src EMUL=1) this means vs2 == vd or vs2 in vd's group.
# Templates: vext{2,4,8}_overlapping_vd_vs2 = std_trap_vec, vtype_lmul_<N>,
#   vd_reg_aligned_lmul_<N>, vs2 in bottom of group (vs2 == vd low offset).
# ---------------------------------------------------------------------------

@register("cp_ssstrictv_vext2_overlapping_vd_vs2")
def vext2_overlap(instruction: str) -> None:
    # vd_eq_vs2 at LMUL=2
    issue_simple_test(instruction, "cp_ssstrictv_vext2_overlapping_vd_vs2",
                      lmul=2, override_vd=4, override_vs2=4, maskval=None)


@register("cp_ssstrictv_vext4_overlapping_vd_vs2")
def vext4_overlap(instruction: str) -> None:
    # vd aligned to 4, vs2_vd_overlap_lmul2 (insn[24:22]==insn[11:9]),
    # vs2 != top of group (vs2 offset != 3). vd=4, vs2=5: top3-of-vs2=00010,
    # top3-of-vd=00010 -> overlap; vs2 offset = 5-4 = 1 (not 3).
    issue_simple_test(instruction, "cp_ssstrictv_vext4_overlapping_vd_vs2",
                      lmul=4, override_vd=4, override_vs2=5, maskval=None)


@register("cp_ssstrictv_vext8_overlapping_vd_vs2")
def vext8_overlap(instruction: str) -> None:
    # vd aligned to 8, vs2_vd_overlap_lmul4 (insn[24:23]==insn[11:10]),
    # vs2 != top of group (vs2 offset != 7). vd=8, vs2=9 -> overlap, offset=1.
    issue_simple_test(instruction, "cp_ssstrictv_vext8_overlapping_vd_vs2",
                      lmul=8, override_vd=8, override_vs2=9, maskval=None)


# ---------------------------------------------------------------------------
# Narrowing instructions: vd may not overlap vs2 (source is 2*SEW).
# Template: cross std_trap_vec, vtype_lmul_1, vs2_reg_aligned_lmul_2,
#           vd_eq_vs2.
# ---------------------------------------------------------------------------

@register("cp_ssstrictv_vnarrow_overlapping_vd_vs2")
def vnarrow_overlap(instruction: str) -> None:
    # vd=vs2=4 (vs2 is even -> aligned to lmul=2 group).
    issue_simple_test(instruction, "cp_ssstrictv_vnarrow_overlapping_vd_vs2",
                      lmul=1, override_vd=4, override_vs2=4, maskval=None)


# ---------------------------------------------------------------------------
# Widening instructions at LMUL=1: vd is 2 regs (EMUL=2). vd group must
# not overlap vs1/vs2 (which are 1 reg each, EMUL=1).
# Templates require vd_reg_aligned_lmul_2 + vd_eq_vs1/vs2 + vs?_vd_no_overlap_lmul1.
# vd=4 (aligned to 2). For vs1 overlap: vs1=4 (==vd), vs2 must NOT overlap
# vd's lmul=2 group -> vs2's top4 != vd's top4 -> vs2=8 or 6 etc.
# ---------------------------------------------------------------------------

@register("cp_ssstrictv_vwiden_overlapping_vd_vs1_lmul1")
def vwiden_vd_vs1(instruction: str) -> None:
    issue_simple_test(instruction, "cp_ssstrictv_vwiden_overlapping_vd_vs1_lmul1",
                      lmul=1, override_vd=4, override_vs1=4, override_vs2=8,
                      maskval=None)


@register("cp_ssstrictv_vwiden_overlapping_vd_vs2_lmul1")
def vwiden_vd_vs2(instruction: str) -> None:
    args = common.getInstructionArguments(instruction)
    kwargs = {"override_vd": 4, "override_vs2": 4}
    if "vs1" in args:
        kwargs["override_vs1"] = 8  # vs1 must NOT overlap vd's lmul=2 group
    issue_simple_test(instruction, "cp_ssstrictv_vwiden_overlapping_vd_vs2_lmul1",
                      lmul=1, maskval=None, **kwargs)


@register("cp_ssstrictv_vwidenw_overlapping_vd_vs1_lmul1")
def vwidenw_vd_vs1(instruction: str) -> None:
    # widening .w form: vs2 is wide already (EMUL=2), vs1 narrow.
    issue_simple_test(instruction, "cp_ssstrictv_vwidenw_overlapping_vd_vs1_lmul1",
                      lmul=1, override_vd=4, override_vs1=4, override_vs2=8,
                      maskval=None)


# ---------------------------------------------------------------------------
# widening_source_overlap / all_widening_source_overlap: vd_eq_vs1 OR vd_eq_vs2
# ---------------------------------------------------------------------------

@register("cp_ssstrictv_widening_source_overlap")
def widening_source_overlap(instruction: str) -> None:
    """Cross requires vs2_eq_vs1 (insn[24:20] == insn[19:15]) at multiple LMULs.
    Template covers LMUL ∈ {mf2(7), m1(0), m2(1), m4(2)}.
    """
    cp = "cp_ssstrictv_widening_source_overlap"
    args = common.getInstructionArguments(instruction)
    if "vs1" not in args or "vs2" not in args:
        return
    cap = max_legal_lmul(instruction)
    # vd has 2x EMUL — choose vd far from vs1/vs2 group to avoid vd-overlap traps masking the cross.
    for lmul in (1, 2, 4):
        if lmul > cap:
            break
        # vs1 == vs2 = 8; vd = 16 (aligned to 2*lmul up to 8).
        vd = 16 if lmul <= 4 else 16
        issue_simple_test(instruction, cp, lmul=lmul,
                          override_vd=vd, override_vs1=8, override_vs2=8,
                          maskval=None)
    # mf2 case (LMUL code 7); helper accepts string lmul.
    issue_simple_test(instruction, cp, lmul="mf2", sew=8,
                      override_vd=16, override_vs1=8, override_vs2=8,
                      maskval=None)


@register("cp_ssstrictv_all_widening_source_overlap")
def all_widening_source_overlap(instruction: str) -> None:
    cp = "cp_ssstrictv_all_widening_source_overlap"
    args = common.getInstructionArguments(instruction)
    if "vs1" not in args or "vs2" not in args:
        return
    cap = max_legal_lmul(instruction)
    # Cross requires std_trap_vec ∧ vtype_all_lmulge1 ∧ vs2_eq_vs1.
    # Use vd=vs1=vs2=8 so the source-source equality satisfies vs2_eq_vs1
    # AND vd group includes vs1/vs2 (overlap → trap). vd=8 is aligned to
    # 2,4,8,16 so works for widening at any LMUL.
    for lmul in (1, 2, 4, 8):
        if lmul > cap and lmul != 8:
            break
        issue_simple_test(instruction, cp, lmul=lmul,
                          override_vd=8, override_vs1=8, override_vs2=8,
                          maskval=None)
    # Also exercise legacy vd_eq_role pattern for incidental coverage of
    # downstream cgs that depend on vd-overlap-vs1/vs2 bits.
    for lmul in (1, 2, 4):
        if lmul > cap:
            break
        if "vs1" in args:
            _emit_vd_eq_role(instruction, cp, lmul=lmul, role="vs1")
        if "vs2" in args:
            _emit_vd_eq_role(instruction, cp, lmul=lmul, role="vs2")


# ---------------------------------------------------------------------------
# ext_emul_lt1_overlap: vsext/vzext vfN where source EMUL < 1 and overlap.
# Template covers vf2/vf4/vf8 at multiple LMULs, all using vd_eq_vs2 or
# vs2_vd_overlap_lmul1/2.
# ---------------------------------------------------------------------------

@register("cp_ssstrictv_ext_emul_lt1_overlap")
def ext_emul_lt1_overlap(instruction: str) -> None:
    cp = "cp_ssstrictv_ext_emul_lt1_overlap"
    cap = max_legal_lmul(instruction)
    # vd_eq_vs2 at LMUL=1
    issue_simple_test(instruction, cp, lmul=1, override_vd=4, override_vs2=4,
                      maskval=None)
    # Partial overlaps at LMUL=2 and 4
    for lmul in (2, 4):
        if lmul > cap:
            break
        vd, other = _OVERLAP_PAIRS[lmul]
        issue_simple_test(instruction, cp, lmul=lmul, override_vd=vd,
                          override_vs2=other, maskval=None)
