"""Priv coverpoint handler for cp_exceptionsv_LS.

Generates tests that execute vector load/store instructions under standard
trap-valid conditions (vill=0, vstart=0, vl>0, mstatus.vs!=0).
"""

from __future__ import annotations

from random import seed as set_seed

import vector_testgen_common as common
from priv_coverpoint_registry import register

CP = "cp_exceptionsv_LS"


def _build_testline(instruction: str, instruction_data: list, maskval: str | None = None) -> tuple[str, int, int]:
    """Build the assembly test line and return (testline, vd_reg, rd_reg)."""
    args = common.getInstructionArguments(instruction)
    vec_data, scalar_data, fp_data, imm_val = instruction_data

    testline = instruction + " "
    for arg in args:
        if arg == "vm":
            if maskval is not None:
                testline += "v0.t"
            else:
                testline = testline[:-2]
        elif arg == "v0":
            testline += "v0"
        elif arg == "imm":
            testline += f"{imm_val}"
        elif arg[0] == "v":
            testline += f"v{vec_data[arg]['reg']}"
        elif arg[0] == "r":
            if arg == "rs1" and instruction in common.vector_ls_ins:
                # Use random_mask_0 as valid address (vector_ls_random_base
                # isn't available in priv tests). The randomly chosen rs1
                # holds the address.
                reg = scalar_data[arg]["reg"]
                common.writeLine(f"la x{reg}, random_mask_0", "# rs1 = valid memory address")
                testline += f"(x{reg})"
            else:
                common.loadScalarReg(arg, scalar_data)
                testline += f"x{scalar_data[arg]['reg']}"
        elif arg[0] == "f":
            testline += f"f{fp_data[arg]['reg']}"
        else:
            raise TypeError(f"Unsupported argument type: '{arg}'")
        testline += ", "

    testline = testline[:-2]  # strip trailing ", "

    vd = vec_data["vd"]["reg"]
    rd = scalar_data["rd"]["reg"]
    return testline, vd, rd


def _sig_params(instruction: str, instruction_data: list, lmul: int = 1) -> tuple[int, bool]:
    """Determine sig_lmul and sig_whole_register_store."""
    vec_data = instruction_data[0]
    if vec_data["vd"]["reg_type"] in ("mask", "scalar"):
        return 1, True
    if instruction in common.whole_register_move:
        return common.getLengthLmul(instruction), True
    return lmul, False


def _emit_setup(instruction: str, instruction_data: list, sew: int) -> int:
    """Emit vsetivli + vd/vs2/vs3 initialization. Returns scratch reg used."""
    vec_data, scalar_data, _, _ = instruction_data
    scratch = common.pickPrivScratch(scalar_data)
    args = common.getInstructionArguments(instruction)
    vd_reg  = vec_data["vd"]["reg"]
    vs2_reg = vec_data["vs2"]["reg"]
    vs3_reg = vec_data["vs3"]["reg"]
    common.writeLine(f"vsetivli x{scratch}, 1, e{sew}, m1, tu, mu", "# vill=0, vstart=0, vl=1")
    common.writeLine(f"la x{scratch}, random_mask_0", "# valid data address")
    if "vd" in args:
        common.writeLine(f"vle{sew}.v v{vd_reg}, (x{scratch})", f"# initialize vd (v{vd_reg})")
    if "vs3" in args:
        common.writeLine(f"vle{sew}.v v{vs3_reg}, (x{scratch})", f"# initialize vs3 (v{vs3_reg})")
    if "vs2" in args:
        common.writeLine(f"vle{sew}.v v{vs2_reg}, (x{scratch})", f"# initialize vs2 (v{vs2_reg})")
    return scratch


@register(CP)
def make_exceptionsv_LS(instruction: str) -> None:
    """Execute LS instruction normally under std_trap_vec conditions."""
    set_seed(common.myhash(instruction + CP))

    # Use SEW=EEW so EMUL=LMUL=1, avoiding register overlap issues
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
    _emit_setup(instruction, instruction_data, sew)

    testline, vd, rd = _build_testline(instruction, instruction_data)
    sig_lmul, sig_wr = _sig_params(instruction, instruction_data)

    # Stores have no architectural vd to compare; the vd used for SIGUPD here is
    # a random unused vector register and would fail comparison non-deterministically.
    # Skip the per-test data SIGUPD for stores -- the trap-handler signature still
    # records trap-vs-no-trap behavior cross-model.
    skip = instruction in common.vector_stores
    common.add_testcase_string(CP, instruction)
    common.writeVecTest(
        instruction, CP, vd, sew, testline,
        test=instruction, rd=rd, vl=1, sig_lmul=sig_lmul,
        sig_whole_register_store=sig_wr, priv=True, skip_sigupd=skip,
    )
