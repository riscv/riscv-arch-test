"""Priv coverpoint handlers for cp_exceptionsv_index_eew{16,32,64}.

These coverpoints fire when an indexed vector load/store with index EEW=N is
attempted on a configuration where MAXINDEXEEW < N, which traps as illegal.
The testgen body is identical to cp_exceptionsv_LS: execute the indexed
instruction under a valid vtype; whether it traps is determined by the
configuration at run time, which is exactly what the coverpoint crosses.
"""

from __future__ import annotations

from random import seed as set_seed

import vector_testgen_common as common
from priv_coverpoint_registry import register

from .cp_exceptionsv_LS import _build_testline, _sig_params


def _make_index_eew(cp: str, instruction: str) -> None:
    set_seed(common.myhash(instruction + cp))

    eew = common.getInstructionEEW(instruction) or common.minSEW_MIN
    sew = eew

    instruction_data = common.randomizeVectorInstructionData(
        instruction, sew, common.getBaseSuiteTestCount(),
        vd_val_pointer="vector_random",
        vs2_val_pointer="vector_random",
        vs1_val_pointer="vector_random",
    )
    common.remapPrivScalarRegs(instruction_data, instruction)

    common.writeLine(f"\n# Testcase {cp}")
    from .cp_exceptionsv_LS import _emit_setup
    _emit_setup(instruction, instruction_data, sew)

    testline, vd, rd = _build_testline(instruction, instruction_data)
    sig_lmul, sig_wr = _sig_params(instruction, instruction_data)

    skip = instruction in common.vector_stores
    common.add_testcase_string(cp, instruction)
    common.writeVecTest(
        instruction, cp, vd, sew, testline,
        test=instruction, rd=rd, vl=1, sig_lmul=sig_lmul,
        sig_whole_register_store=sig_wr, priv=True, skip_sigupd=skip,
    )


@register("cp_exceptionsv_index_eew16")
def make_exceptionsv_index_eew16(instruction: str) -> None:
    _make_index_eew("cp_exceptionsv_index_eew16", instruction)


@register("cp_exceptionsv_index_eew32")
def make_exceptionsv_index_eew32(instruction: str) -> None:
    _make_index_eew("cp_exceptionsv_index_eew32", instruction)


@register("cp_exceptionsv_index_eew64")
def make_exceptionsv_index_eew64(instruction: str) -> None:
    _make_index_eew("cp_exceptionsv_index_eew64", instruction)
