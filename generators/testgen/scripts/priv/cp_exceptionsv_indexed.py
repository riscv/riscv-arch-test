"""Priv coverpoint handler for cp_exceptionsv_indexed.

Runs an indexed vector load/store under otherwise-legal conditions (vill=0,
vstart=0, vl>0, valid 8-byte-aligned base, mstatus.vs!=0) so that any
resulting trap is attributable to MAXINDEXEEW gating the index EEW. The
instruction may or may not trap depending on the configured MAXINDEXEEW.

Dual-signature design (vector-priv specific):
  - The vd SIGUPD_V always fires (no skip_sigupd), capturing the data path
    when the instruction does not trap.
  - The framework trap handler writes the trap signature to mtrap_sigptr
    when a trap does fire.
  Both DUT and the reference simulator run the same code under the same
  config, so whichever path fires is observed identically on both sides
  and the signatures match. Do NOT pass skip_sigupd=True here -- that
  would discard the no-trap data check.
"""

from __future__ import annotations

from random import seed as set_seed

import vector_testgen_common as common
from priv_coverpoint_registry import register

from .cp_exceptionsv_LS import _build_testline, _sig_params

CP = "cp_exceptionsv_indexed"


@register(CP)
def make_exceptionsv_indexed(instruction: str) -> None:
    set_seed(common.myhash(instruction + CP))

    eew = common.getInstructionEEW(instruction) or common.minSEW_MIN
    sew = eew

    instruction_data = common.randomizeVectorInstructionData(
        instruction, sew, common.getBaseSuiteTestCount(),
        vd_val_pointer="vector_random",
        vs2_val_pointer="vector_random",
        vs1_val_pointer="vector_random",
    )
    common.remapPrivScalarRegs(instruction_data, instruction)

    common.writeLine(f"\n# Testcase {CP}")
    from .cp_exceptionsv_LS import _emit_setup
    _emit_setup(instruction, instruction_data, sew)

    testline, vd, rd = _build_testline(instruction, instruction_data)
    sig_lmul, sig_wr = _sig_params(instruction, instruction_data)

    skip = instruction in common.vector_stores
    common.add_testcase_string(CP, instruction)
    common.writeVecTest(
        instruction, CP, vd, sew, testline,
        test=instruction, rd=rd, vl=1, sig_lmul=sig_lmul,
        sig_whole_register_store=sig_wr, priv=True, skip_sigupd=skip,
    )
