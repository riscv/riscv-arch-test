"""cp_ssstrictv_masking_vd_v0_overlap: vd=v0 with masking, all LMUL ≥ 1.

Cross: ``std_trap_vec, vtype_all_lmulge1, vd_eq_v0_overlap(=v0), vd_ne_vs1,
vd_ne_vs2, vs2_ne_vs1, mask_enabled``.

Same shape as masking_vd_eq_v0_lmulgt1 but also includes LMUL=1.
"""

from __future__ import annotations

from random import randint, seed as set_seed

import vector_testgen_common as common
from priv_coverpoint_registry import register
from ._ssstrictv_helpers import (build_testline, emit_vsetivli, init_operand_regs,
                                 make_dest_zero_overrides, max_legal_lmul, sig_params)

CP = "cp_ssstrictv_masking_vd_v0_overlap"


def _pick_distinct(step: int, exclude: set[int]) -> int:
    while True:
        v = randint(1, 31 // step) * step
        if v not in exclude:
            return v


@register(CP)
def make(instruction: str) -> None:
    set_seed(common.myhash(instruction + CP))
    eew = common.getInstructionEEW(instruction)
    sews = [eew] if eew else [8, 16, 32, 64]
    # See note in cp_ssstrictv_masking_vd_eq_v0_lmulgt1.py: emit all LMULs
    # regardless of max_legal_lmul; the cross is encoding+pre-state only.
    dest_overrides = make_dest_zero_overrides(instruction)

    sidx = 0
    for lmul in (1, 2, 4, 8):
        sew = sews[sidx % len(sews)]
        sidx += 1
        instruction_data = common.randomizeVectorInstructionData(
            instruction, sew, common.getBaseSuiteTestCount(),
            vd_val_pointer="vector_random",
            vs2_val_pointer="vector_random",
            vs1_val_pointer="vector_random",
        )
        common.remapPrivScalarRegs(instruction_data, instruction)
        used = {0}
        vs2 = _pick_distinct(lmul, used); used.add(vs2)
        vs1 = _pick_distinct(lmul, used); used.add(vs1)

        common.writeLine(f"\n# Testcase {CP} (lmul={lmul}, sew={sew})")
        scratch = common.pickPrivScratch(instruction_data[1])
        emit_vsetivli(scratch, vl=1, sew=sew, lmul=lmul)
        init_operand_regs(instruction, instruction_data[0], sew, scratch)
        # Re-emit vsetivli right before the test so SAMPLE_BEFORE sees vtype.
        emit_vsetivli(scratch, vl=1, sew=sew, lmul=lmul)

        testline, vd, rd = build_testline(
            instruction, instruction_data, maskval="v0.t",
            override_vs1=vs1, override_vs2=vs2, **dest_overrides,
        )
        sig_lmul, sig_wr = sig_params(instruction, instruction_data, lmul=lmul)

        common.add_testcase_string(CP, instruction)
        common.writeVecTest(
            instruction, CP, vd, sew, testline,
            test=instruction, rd=rd, vl=1, lmul=lmul,
            sig_lmul=sig_lmul, sig_whole_register_store=sig_wr,
            priv=True, skip_sigupd=True,
        )
