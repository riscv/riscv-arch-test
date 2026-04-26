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
                # isn't available in priv tests)
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


@register(CP)
def make_exceptionsv_LS(instruction: str) -> None:
    """Execute LS instruction normally under std_trap_vec conditions."""
    set_seed(common.myhash(instruction + CP))

    # Use SEW=EEW so EMUL=LMUL=1, avoiding register overlap issues
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

    # Setup: valid vtype, vstart=0, vl=1
    common.writeLine(f"\n# Testcase {CP}")
    common.writeLine(f"vsetivli x8, 1, e{sew}, m1, tu, mu", "# vill=0, vstart=0, vl=1")

    # Load valid data address into base register for LS instructions
    common.writeLine("la x9, random_mask_0", "# valid data address")
    vec_data = instruction_data[0]
    # vs2 init/zero FIRST so that vs3 init below wins on register overlap.
    if "vs2" in args:
        if instruction in common.indexed_ls_ins:
            common.writeLine("vmv.v.x v16, x0", "# zero indexes so vluxei/vloxei/vsuxei/vsoxei address == x7")
        else:
            common.writeLine(f"vle{sew}.v v16, (x9)", "# initialize vs2 (v16)")
    if "vd" in args:
        common.writeLine(f"vle{sew}.v v8, (x9)", "# initialize vd (v8)")
    if "vs3" in args:
        # Always init v8 (the register used by signature comparison)
        common.writeLine(f"vle{sew}.v v8, (x9)", "# initialize vs3-target (v8)")
        # Also init the actual source register(s) — segment stores use NF consecutive
        # regs starting at vs3 — so the store is identity (memory unchanged).
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
