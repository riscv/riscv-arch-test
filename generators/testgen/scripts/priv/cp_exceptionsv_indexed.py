"""Priv coverpoint handler for cp_exceptionsv_indexed.

Runs an indexed vector load/store under otherwise-legal conditions (vill=0,
vstart=0, vl>0, valid address, mstatus.vs!=0) so that any resulting trap is
attributable to MAXINDEXEEW gating the index EEW. The test body mirrors
cp_exceptionsv_LS / cp_exceptionsv_index_eew.
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
        vd=8, vs2=16, vs1=24, rd=5, rs2=6, rs1=7,
        vd_val_pointer="vector_random",
        vs2_val_pointer="vector_random",
        vs1_val_pointer="vector_random",
    )

    args = common.getInstructionArguments(instruction)

    common.writeLine(f"\n# Testcase {CP}")
    common.writeLine(f"vsetivli x8, 1, e{sew}, m1, tu, mu", "# vill=0, vstart=0, vl=1")

    common.writeLine("la x2, random_mask_0", "# valid data address")
    if "vd" in args:
        common.writeLine(f"vle{sew}.v v8, (x2)", "# initialize vd (v8)")
    if "vs3" in args:
        common.writeLine(f"vle{sew}.v v8, (x2)", "# initialize vs3 (v8)")
    if "vs2" in args:
        common.writeLine(f"vle{sew}.v v16, (x2)", "# initialize vs2 (v16)")

    testline, vd, rd = _build_testline(instruction, instruction_data)
    sig_lmul, sig_wr = _sig_params(instruction, instruction_data)

    common.add_testcase_string(CP, instruction)
    common.writeVecTest(
        instruction, CP, vd, sew, testline,
        test=instruction, rd=rd, vl=1, sig_lmul=sig_lmul,
        sig_whole_register_store=sig_wr, priv=True,
    )
