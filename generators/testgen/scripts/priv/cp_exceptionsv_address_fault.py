"""Priv coverpoint handler for cp_exceptionsv_address_fault.

Generates tests that execute vector LS instructions with a valid vtype
but a bad address (0) in rs1, triggering an address fault while vill=0.
This crosses vtype_valid × trap_occurred.
"""

from __future__ import annotations

from random import seed as set_seed

import vector_testgen_common as common
from priv_coverpoint_registry import register

CP = "cp_exceptionsv_address_fault"


@register(CP)
def make_exceptionsv_address_fault(instruction: str) -> None:
    """Execute LS instruction with valid vtype + bad address → address fault."""
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
    )

    args = common.getInstructionArguments(instruction)

    # Setup: valid vtype (vill=0), vstart=0, vl=1
    common.writeLine(f"\n# Testcase {CP}")
    common.writeLine(f"vsetivli x8, 1, e{sew}, m1, tu, mu", "# valid vtype, vl=1")

    common.writeLine("la x2, random_mask_0", "# valid data address for init")
    if "vd" in args:
        common.writeLine(f"vle{sew}.v v8, (x2)", "# initialize vd (v8)")
    if "vs3" in args:
        common.writeLine(f"vle{sew}.v v8, (x2)", "# initialize vs3 (v8)")
    if "vs2" in args:
        common.writeLine(f"vle{sew}.v v16, (x2)", "# initialize vs2 (v16)")

    # rs1 = 0 → triggers address fault (access to address 0)
    common.writeLine("li x7, 0", "# rs1 = 0 → address fault trigger")

    # Build testline: unmasked to ensure memory access actually occurs
    vec_data, scalar_data, fp_data, imm_val = instruction_data
    testline = instruction + " "
    for arg in args:
        if arg == "vm":
            # Unmasked: drop vm to guarantee the access happens
            testline = testline[:-2]
        elif arg == "v0":
            testline += "v0"
        elif arg == "imm":
            testline += f"{imm_val}"
        elif arg[0] == "v":
            testline += f"v{vec_data[arg]['reg']}"
        elif arg[0] == "r":
            if arg == "rs1":
                # rs1 = 0 → address fault
                scalar_data[arg]["val"] = 0
                testline += f"(x{scalar_data[arg]['reg']})"
            else:
                common.loadScalarReg(arg, scalar_data)
                testline += f"x{scalar_data[arg]['reg']}"
        elif arg[0] == "f":
            testline += f"f{fp_data[arg]['reg']}"
        else:
            raise TypeError(f"Unsupported argument type: '{arg}'")
        testline += ", "
    testline = testline[:-2]

    vd = vec_data["vd"]["reg"]
    rd = scalar_data["rd"]["reg"]

    if vec_data["vd"]["reg_type"] in ("mask", "scalar"):
        sig_lmul, sig_wr = 1, True
    elif instruction in common.whole_register_move:
        sig_lmul, sig_wr = common.getLengthLmul(instruction), True
    else:
        sig_lmul, sig_wr = 1, False

    common.add_testcase_string(CP, instruction)
    common.writeVecTest(
        instruction, CP, vd, sew, testline,
        test=instruction, rd=rd, vl=1, sig_lmul=sig_lmul,
        sig_whole_register_store=sig_wr, priv=True,
    )
