"""cp_ssstrictv_masking_vd_eq_v0_lmulgt1: vd group includes v0 with mask enabled at LMUL > 1.

Cross: ``std_trap_vec, vtype_all_lmulgt1, vd_eq_v0(=v0), vd_ne_vs1, vd_ne_vs2,
vs2_ne_vs1, mask_enabled``.
"""

from __future__ import annotations

from random import randint, seed as set_seed

import vector_testgen_common as common
from priv_coverpoint_registry import register
from ._ssstrictv_helpers import (build_testline, emit_vsetivli, init_operand_regs,
                                 make_dest_zero_overrides, max_legal_lmul, sig_params)

CP = "cp_ssstrictv_masking_vd_eq_v0_lmulgt1"


def _pick_distinct(low: int, high: int, exclude: set[int], step: int = 1) -> int:
    while True:
        v = randint(low // step, high // step) * step
        if v not in exclude:
            return v


@register(CP)
def make(instruction: str) -> None:
    set_seed(common.myhash(instruction + CP))
    eew = common.getInstructionEEW(instruction)
    sews = [eew] if eew else [8, 16, 32, 64]
    # NOTE: do not gate on max_legal_lmul; the cross is over the reserved
    # encoding (vd=v0, masked, LMUL>1) and fires on SAMPLE_BEFORE pre-state,
    # not on whether the instruction is otherwise legal. For segment loads
    # with NF*EMUL > 8 the instruction will trap for two reasons; that's
    # fine — the cross still samples the encoding bits + vtype.
    dest_overrides = make_dest_zero_overrides(instruction)

    sidx = 0
    for lmul in (2, 4, 8):
        sew = sews[sidx % len(sews)]
        sidx += 1
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
