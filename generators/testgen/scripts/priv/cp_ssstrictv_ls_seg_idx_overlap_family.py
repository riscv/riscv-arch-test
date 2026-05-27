"""Indexed-segment LS register-overlap reserved-encoding coverpoints.

`vd` (load) / `vs3` (store) register group must not overlap the `vs2`
index register group for indexed-segment instructions. Two crosses:

- ``cp_ssstrictv_ls_seg_idx_vd_vs2_overlap`` — LMUL=1, vs2 anywhere in
  ``vd..vd+nf-1``.
- ``cp_ssstrictv_ls_seg_idx_vd_vs2_grp_overlap`` — LMUL=2, vs2 group
  overlaps vd group (only NF in ``{2, 3, 4}`` since ``NF*EMUL <= 8``).

Per-instruction NF is fixed by the mnemonic (``vsuxseg3ei8`` → NF=3),
so each cg only needs ONE test that satisfies one of the bin tuples
matching its own NF field.
"""

from __future__ import annotations

import vector_testgen_common as common
from priv_coverpoint_registry import register

from ._ssstrictv_helpers import issue_simple_test


_INDEXED_SEG = [i for i in common.indexed_ls_ins
                if common.getInstructionSegments(i) > 1]


def _emit(instruction: str, cp: str, *, lmul: int, vd: int, vs2: int) -> None:
    args = common.getInstructionArguments(instruction)
    overrides: dict[str, int] = {"override_vd": vd, "override_vs2": vs2}
    if "vs3" in args:
        overrides["override_vs3"] = vd
    issue_simple_test(instruction, cp, lmul=lmul, maskval=None, **overrides)


@register("cp_ssstrictv_ls_seg_idx_vd_vs2_overlap")
def seg_idx_vd_vs2_overlap(instruction: str) -> None:
    if instruction not in _INDEXED_SEG:
        return
    nf = common.getInstructionSegments(instruction)
    # vd=8, vs2=vd+nf-1 (matches the (8, 8+nf-1, nf-1) tuple in the template).
    _emit(instruction, "cp_ssstrictv_ls_seg_idx_vd_vs2_overlap",
          lmul=1, vd=8, vs2=8 + nf - 1)


@register("cp_ssstrictv_ls_seg_idx_vd_vs2_grp_overlap")
def seg_idx_vd_vs2_grp_overlap(instruction: str) -> None:
    if instruction not in _INDEXED_SEG:
        return
    nf = common.getInstructionSegments(instruction)
    # Template only has bins for NF ∈ {2, 3, 4} at LMUL=2.
    if nf not in (2, 3, 4):
        return
    # Pick a vs2 in the bin list for this nf:
    #   NF=2 → vs2 ∈ {8, 9, 10, 11}
    #   NF=3 → vs2 ∈ {12, 13}
    #   NF=4 → vs2 ∈ {14, 15}
    vs2 = {2: 9, 3: 12, 4: 14}[nf]
    _emit(instruction, "cp_ssstrictv_ls_seg_idx_vd_vs2_grp_overlap",
          lmul=2, vd=8, vs2=vs2)
