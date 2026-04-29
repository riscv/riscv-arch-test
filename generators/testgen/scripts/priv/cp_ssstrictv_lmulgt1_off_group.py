"""cp_ssstrictv_lmulgt1_off_group: register fields not aligned to LMUL>1 group.

For each LMUL ∈ {2, 4, 8} and each role ∈ {vd, vs1, vs2}, emit a test where the
given role's register field is not divisible by LMUL. The 9 sub-coverpoints
share ``std_trap_vec, vtype_lmul_<L>`` and the corresponding ``<role>_all_reg_unaligned_lmul_<L>``.
"""

from __future__ import annotations

from random import randint, seed as set_seed

import vector_testgen_common as common
from priv_coverpoint_registry import register
from ._ssstrictv_helpers import (build_testline, emit_vsetivli, init_operand_regs,
                                 max_legal_lmul, sig_params)

CP = "cp_ssstrictv_lmulgt1_off_group"


def _all_unaligned_for_lmul(lmul: int) -> list[int]:
    """All register indices in [0,31] that are NOT divisible by ``lmul``."""
    return [r for r in range(32) if r % lmul != 0]


def _emit_one(instruction: str, lmul: int, role: str, off_reg: int) -> None:
    sew = common.getInstructionEEW(instruction) or common.minSEW_MIN
    instruction_data = common.randomizeVectorInstructionData(
        instruction, sew, common.getBaseSuiteTestCount(),
        vd_val_pointer="vector_random",
        vs2_val_pointer="vector_random",
        vs1_val_pointer="vector_random",
    )
    common.remapPrivScalarRegs(instruction_data, instruction)

    common.writeLine(f"\n# Testcase {CP} (lmul={lmul}, off_role={role}, reg=v{off_reg})")
    scratch = common.pickPrivScratch(instruction_data[1])
    emit_vsetivli(scratch, vl=1, sew=sew, lmul=lmul)
    init_operand_regs(instruction, instruction_data[0], sew, scratch)

    overrides: dict[str, int] = {}
    if role == "vd":
        overrides["override_vd"] = off_reg
    elif role == "vs1":
        overrides["override_vs1"] = off_reg
    elif role == "vs2":
        overrides["override_vs2"] = off_reg

    testline, vd, rd = build_testline(instruction, instruction_data, **overrides)
    sig_lmul, sig_wr = sig_params(instruction, instruction_data, lmul=lmul)

    common.add_testcase_string(CP, instruction)
    common.writeVecTest(
        instruction, CP, vd, sew, testline,
        test=instruction, rd=rd, vl=1, lmul=lmul,
        sig_lmul=sig_lmul, sig_whole_register_store=sig_wr,
        priv=True, skip_sigupd=True,
    )


@register(CP)
def make(instruction: str) -> None:
    set_seed(common.myhash(instruction + CP))
    args = common.getInstructionArguments(instruction)
    cap = max_legal_lmul(instruction)
    for lmul in (2, 4, 8):
        if lmul > cap:
            break
        for role in ("vd", "vs1", "vs2"):
            if role not in args:
                continue
            for off_reg in _all_unaligned_for_lmul(lmul):
                _emit_one(instruction, lmul, role, off_reg)
