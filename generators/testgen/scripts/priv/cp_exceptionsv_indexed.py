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
        vd=8, vs2=16, vs1=24, rd=5, rs2=6, rs1=7,
        vd_val_pointer="vector_random",
        vs2_val_pointer="vector_random",
        vs1_val_pointer="vector_random",
        additional_no_overlap=[['vs3', 'vs2']],
    )

    args = common.getInstructionArguments(instruction)

    common.writeLine(f"\n# Testcase {CP}")
    common.writeLine(f"vsetivli x8, 1, e{sew}, m1, tu, mu", "# vill=0, vstart=0, vl=1")

    common.writeLine("la x9, random_mask_0", "# valid data address")
    vec_data = instruction_data[0]
    if "vs2" in args:
        if instruction in common.indexed_ls_ins:
            common.writeLine("vmv.v.x v16, x0", "# zero indexes for indexed LS")
        else:
            common.writeLine(f"vle{sew}.v v16, (x9)", "# initialize vs2 (v16)")
    if "vd" in args:
        common.writeLine(f"vle{sew}.v v8, (x9)", "# initialize vd (v8)")
    if "vs3" in args:
        common.writeLine(f"vle{sew}.v v8, (x9)", "# initialize vs3-target (v8)")
        vs3_reg = vec_data["vs3"]["reg"]
        nf = max(1, common.getInstructionSegments(instruction))
        for i in range(nf):
            r = vs3_reg + i
            if r != 8:
                common.writeLine(f"vle{sew}.v v{r}, (x9)", f"# initialize actual vs3+{i} (v{r}) so store is identity")

    testline, vd, rd = _build_testline(instruction, instruction_data)
    sig_lmul, sig_wr = _sig_params(instruction, instruction_data)

    common.add_testcase_string(CP, instruction)
    common.writeVecTest(
        instruction, CP, vd, sew, testline,
        test=instruction, rd=rd, vl=1, sig_lmul=sig_lmul,
        sig_whole_register_store=sig_wr, priv=True,
    )
