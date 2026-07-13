"""cp_ssstrictv_vmv{2,4}r_reg_align: cover both_unaligned cross.

The cg ``cp_ssstrictv_vmv<N>r_reg_align`` contains an inner cross
``cp_ssstrictv_vmv<N>r_both_unaligned`` requiring (vd_unaligned * vs2_unaligned)
combinations (16x16 = 256 for N=2; 24x24 = 576 for N=4). Other tests passively
fire the single-axis bins; this generator pairs every unaligned vd with every
unaligned vs2 to close the cross.

vmv8r.v is not enabled for ``cp_ssstrictv_vmv8r_reg_align`` in the CSV, so the
cross is never instantiated for it (vacuously 100%).
"""

from __future__ import annotations

from priv_coverpoint_registry import register

from ._ssstrictv_helpers import issue_simple_test


def _unaligned(nreg: int) -> list[int]:
    return [r for r in range(0, 32) if r % nreg != 0]


def _emit_pairs(instruction: str, cp: str, nreg: int) -> None:
    pool = _unaligned(nreg)
    for vd in pool:
        for vs2 in pool:
            issue_simple_test(instruction, cp, sew=8, lmul=1, maskval=None,
                              override_vd=vd, override_vs2=vs2)


@register("cp_ssstrictv_vmv2r_reg_align")
def vmv2r_reg_align(instruction: str) -> None:
    _emit_pairs(instruction, "cp_ssstrictv_vmv2r_both_unaligned", 2)


@register("cp_ssstrictv_vmv4r_reg_align")
def vmv4r_reg_align(instruction: str) -> None:
    _emit_pairs(instruction, "cp_ssstrictv_vmv4r_both_unaligned", 4)
