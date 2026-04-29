"""cp_ssstrictv_masking_vd_eq_v0_lmulgt1: vd group includes v0 with mask enabled at LMUL > 1.

Cross: ``std_trap_vec, vtype_all_lmulgt1, vd_eq_v0(=v0), vd_ne_vs1, vd_ne_vs2,
vs2_ne_vs1, mask_enabled``.
"""

from __future__ import annotations

from random import randint, seed as set_seed

import vector_testgen_common as common
from priv_coverpoint_registry import register
from ._ssstrictv_helpers import (build_testline, emit_vsetivli, init_operand_regs,
                                 max_legal_lmul, sig_params)

CP = "cp_ssstrictv_masking_vd_eq_v0_lmulgt1"


def _pick_distinct(low: int, high: int, exclude: set[int], step: int = 1) -> int:
    while True:
        v = randint(low // step, high // step) * step
        if v not in exclude:
            return v


@register(CP)
def make(instruction: str) -> None:
    set_seed(common.myhash(instruction + CP))
    sew = common.getInstructionEEW(instruction) or common.minSEW_MIN
    cap = max_legal_lmul(instruction)

    for lmul in (2, 4, 8):
        if lmul > cap:
            break
        instruction_data = common.randomizeVectorInstructionData(
            instruction, sew, common.getBaseSuiteTestCount(),
            vd_val_pointer="vector_random",
            vs2_val_pointer="vector_random",
            vs1_val_pointer="vector_random",
        )
        common.remapPrivScalarRegs(instruction_data, instruction)
        # vd=0 (overlaps v0 group). vs1, vs2 must be != vd group AND != each other.
        # Use distinct LMUL-aligned regs so they cleanly differ from v0.
        used = {0}
        vs2 = _pick_distinct(lmul, 31, used, step=lmul); used.add(vs2)
        vs1 = _pick_distinct(lmul, 31, used, step=lmul); used.add(vs1)

        common.writeLine(f"\n# Testcase {CP} (lmul={lmul})")
        scratch = common.pickPrivScratch(instruction_data[1])
        emit_vsetivli(scratch, vl=1, sew=sew, lmul=lmul)
        init_operand_regs(instruction, instruction_data[0], sew, scratch)

        testline, vd, rd = build_testline(
            instruction, instruction_data, maskval="v0.t",
            override_vd=0, override_vs1=vs1, override_vs2=vs2,
        )
        sig_lmul, sig_wr = sig_params(instruction, instruction_data, lmul=lmul)

        common.add_testcase_string(CP, instruction)
        common.writeVecTest(
            instruction, CP, vd, sew, testline,
            test=instruction, rd=rd, vl=1, lmul=lmul,
            sig_lmul=sig_lmul, sig_whole_register_store=sig_wr,
            priv=True, skip_sigupd=True,
        )
