"""SsstrictV generators for vsext/vzext source-EEW / source-EMUL reserved.

The CSV column ``cp_ssstrictv_v{s,z}ext_src_reserved`` maps to the template of
the same name in ``coverpoints/priv``; that template defines six sub-crosses
(``vfN_src_eew`` and ``vfN_src_emul`` for N in {2,4,8}).

For the cross to fire, the encoding must select a specific vsext/vzext variant
AND the pre-state vsew/vlmul must yield an out-of-range source EEW/EMUL.

Variants (insn[19:15]): vf2=7, vf4=5, vf8=3.
"""

from __future__ import annotations

from priv_coverpoint_registry import register

from ._ssstrictv_helpers import issue_simple_test


def _emit_all(instruction: str, cp: str) -> None:
    # NOTE: must keep VLMAX>=1 (vill=0) so std_trap_vec fires.
    # vsetvli will set vill=1 when SEW > LMUL*ELEN. With ELEN=64:
    #   LMUL=1   -> SEW <= 64 ok
    #   LMUL=mf2 -> SEW <= 32 ok
    #   LMUL=mf4 -> SEW <= 16 ok
    #   LMUL=mf8 -> SEW <= 8  ok
    if instruction.endswith(".vf2"):
        for sew in (8,):
            issue_simple_test(instruction, cp, sew=sew, lmul=1, maskval=None,
                              override_vd=8, override_vs2=12)
        # src_emul: vf2, LMUL=mf8 -> EMUL=mf16. SEW must be <= 8 to keep vill=0.
        issue_simple_test(instruction, cp, sew=8, lmul="mf8", maskval=None,
                          override_vd=8, override_vs2=12)
    elif instruction.endswith(".vf4"):
        for sew in (8, 16):
            issue_simple_test(instruction, cp, sew=sew, lmul=1, maskval=None,
                              override_vd=8, override_vs2=12)
        # src_emul: LMUL=mf8 -> SEW<=8; LMUL=mf4 -> SEW<=16
        issue_simple_test(instruction, cp, sew=8,  lmul="mf8", maskval=None,
                          override_vd=8, override_vs2=12)
        issue_simple_test(instruction, cp, sew=16, lmul="mf4", maskval=None,
                          override_vd=8, override_vs2=12)
    elif instruction.endswith(".vf8"):
        for sew in (8, 16, 32):
            issue_simple_test(instruction, cp, sew=sew, lmul=1, maskval=None,
                              override_vd=8, override_vs2=12)
        # src_emul: LMUL=mf8/mf4/mf2 -> SEW<=8/16/32
        issue_simple_test(instruction, cp, sew=8,  lmul="mf8", maskval=None,
                          override_vd=8, override_vs2=12)
        issue_simple_test(instruction, cp, sew=16, lmul="mf4", maskval=None,
                          override_vd=8, override_vs2=12)
        issue_simple_test(instruction, cp, sew=32, lmul="mf2", maskval=None,
                          override_vd=8, override_vs2=12)


@register("cp_ssstrictv_vsext_src_reserved")
def vsext_src_reserved(instruction: str) -> None:
    _emit_all(instruction, "cp_ssstrictv_vsext_src_reserved")


@register("cp_ssstrictv_vzext_src_reserved")
def vzext_src_reserved(instruction: str) -> None:
    _emit_all(instruction, "cp_ssstrictv_vzext_src_reserved")
