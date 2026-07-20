##################################
# vvx_type.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.vector_helpers import (
    load_vec_reg,
    load_vxrm,
    prep_base_v,
    prep_mask_v,
    reload_vtype,
    write_sigupd_v,
    write_sigupd_v_len,
)
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter

vvx_config = InstructionTypeConfig(required_params={"vd", "rs1", "vs2"}, vector_data=VectorTypeConfig())
wvx_config = InstructionTypeConfig(
    required_params={"vd", "rs1", "vs2"},
    vector_data=VectorTypeConfig(overlap_constraints={("vd_bottom", "vs2")}, widened_regs={"vd"}),
)
vwx_config = InstructionTypeConfig(
    required_params={"vd", "rs1", "vs2"},
    vector_data=VectorTypeConfig(overlap_constraints={("vd", "vs2_top")}, widened_regs={"vs2"}),
)
wwx_config = InstructionTypeConfig(
    required_params={"vd", "rs1", "vs2"}, vector_data=VectorTypeConfig(widened_regs={"vd", "vs2"})
)
vvxm_config = InstructionTypeConfig(
    required_params={"vd", "rs1", "vs2", "maskval"},
    vector_data=VectorTypeConfig(overlap_constraints={("vd", "v0"), ("vs2", "v0")}),
)
vvx_acc_config = InstructionTypeConfig(required_params={"vd", "rs1", "vs2"}, vector_data=VectorTypeConfig())
wvx_acc_config = InstructionTypeConfig(
    required_params={"vd", "rs1", "vs2"},
    vector_data=VectorTypeConfig(overlap_constraints={("vd", "vs2")}, widened_regs={"vd"}),
)
vvx_sat_config = InstructionTypeConfig(required_params={"vd", "rs1", "vs2"}, vector_data=VectorTypeConfig())
vvxp_config = InstructionTypeConfig(
    required_params={"vd", "rs1", "vs2"}, vector_data=VectorTypeConfig(overlap_constraints={("vd", "vs2")})
)
vvxp_down_config = InstructionTypeConfig(required_params={"vd", "rs1", "vs2"}, vector_data=VectorTypeConfig())


@add_instruction_formatter("VVX", vvx_config)
def format_vvx(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vvx_like_type(instr_str, test_data, params, "VVX")


@add_instruction_formatter("WVX", wvx_config)
def format_wvx(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vvx_like_type(instr_str, test_data, params, "WVX", widen={"vd"})


@add_instruction_formatter("VWX", vwx_config)
def format_vwx(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vvx_like_type(instr_str, test_data, params, "VWX", widen={"vs2"})


@add_instruction_formatter("WWX", wwx_config)
def format_wwx(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vvx_like_type(instr_str, test_data, params, "WWX", widen={"vd", "vs2"})


@add_instruction_formatter("VVXM", vvxm_config)
def format_vvxm(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.maskval is not None, "Masks are required for VVXM-Type Instructions"
    setup, test, check = format_vvx_like_type(instr_str, test_data, params, "VVXM")
    # Overwrite the test, as otherwise it generates with v0.t
    test = [f"{instr_str} v{params.vd}, v{params.vs2}, x{params.rs1}, v0"]
    return setup, test, check


@add_instruction_formatter("VVX_ACC", vvx_acc_config)
def format_vvx_acc(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    setup, test, check = format_vvx_like_type(instr_str, test_data, params, "VVX_ACC")
    # Overwrite the test, as otherwise it generates in the wrong order
    if params.maskval:
        test = [f"{instr_str} v{params.vd}, x{params.rs1}, v{params.vs2}, v0.t"]
    else:
        test = [f"{instr_str} v{params.vd}, x{params.rs1}, v{params.vs2}"]
    return setup, test, check


@add_instruction_formatter("WVX_ACC", wvx_acc_config)
def format_wvx_acc(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    setup, test, check = format_vvx_like_type(instr_str, test_data, params, "WVX_ACC", widen={"vd"})
    # Overwrite the test, as otherwise it generates in the wrong order
    if params.maskval:
        test = [f"{instr_str} v{params.vd}, x{params.rs1}, v{params.vs2}, v0.t"]
    else:
        test = [f"{instr_str} v{params.vd}, x{params.rs1}, v{params.vs2}"]
    return setup, test, check


@add_instruction_formatter("VVX_SAT", vvx_sat_config)
def format_vvx_sat(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    setup, test, check = format_vvx_like_type(instr_str, test_data, params, "VVX_SAT")
    setup = ["csrwi vxsat, 0"] + setup
    return setup, test, check


@add_instruction_formatter("VVXP", vvxp_config)
def format_vvxp(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vvx_like_type(instr_str, test_data, params, "VVXP", enable_vs2_preload=True)


@add_instruction_formatter("VVXP_DOWN", vvxp_down_config)
def format_vvxp_down(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vvx_like_type(instr_str, test_data, params, "VVXP_DOWN", enable_vs2_preload=True)


def format_vvx_like_type(
    instr_str: str,
    test_data: TestData,
    params: InstructionParams,
    type_name: str,
    *,
    widen: set[str] | None = None,
    enable_vs2_preload: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    assert params.rs1 is not None and params.rs1val is not None, (
        f"rs1 and rs1val must be provided for {type_name}-type instructions"
    )
    assert params.vs2 is not None and params.vs2_val_pointer is not None, (
        f"vs2 and vs2_val_pointer must be provided for {type_name}-type instructions"
    )
    assert params.vd is not None and params.vd_val_pointer is not None, (
        f"vd and vd_val_pointer must be provided for {type_name}-type instructions"
    )
    assert params.temp_reg is not None, f"temp_reg must provided for be {type_name}-type instructions"
    assert params.sew is not None, f"sew must provided for be {type_name}-type instructions"
    assert params.lmul is not None, f"lmul must provided for be {type_name}-type instructions"
    assert test_data.test_chunk is not None, f"format_{type_name.lower()}_type must be used with an active TestChunk"

    if widen is None:
        widen = set()

    test_data.test_chunk.vector_labels.extend(
        [
            (params.vs2_val_pointer, *test_data.vector_labels[params.vs2_val_pointer]),
            (params.vd_val_pointer, *test_data.vector_labels[params.vd_val_pointer]),
        ]
    )

    setup = []
    registers = [params.vd, params.vs2]

    # Setup Mask
    if params.maskval:
        setup.extend(prep_mask_v(params.maskval, test_data, params, clobber_vd=True))

    # Setup VXRM (if necessary)
    if params.vxrm is not None:
        setup.extend(load_vxrm(params.vxrm))

    # Preload vd at vlmax
    vd_preloaded = False
    if params.vector_suite == "length":
        vd_lmul = params.lmul * (2 if "vd" in widen else 1)
        vd_sew = params.sew * (2 if "vd" in widen else 1)
        setup.extend(
            load_vec_reg(
                params.vd,
                params.vd_val_pointer,
                params,
                sew_override=vd_sew,
                lmul=max(vd_lmul, 1),
                vl_register_or_imm="x0",
            )
        )
        vd_preloaded = True
        registers.remove(params.vd)

    # Preload vs2 for VVXP
    vs2_preloaded = False
    if params.vector_suite == "length" and enable_vs2_preload:
        setup.extend(
            load_vec_reg(params.vs2, params.vs2_val_pointer, params, lmul=params.lmul, vl_register_or_imm="x0")
        )
        vs2_preloaded = True
        registers.remove(params.vs2)

    # vl_register_or_imm is useful if we ever overwrite vl as it allows us to easily restore it
    prep_lines, vl_register_or_imm = prep_base_v(test_data, params, registers)
    setup.extend(prep_lines)

    # Load Registers at the Proper LMULs (loading whole registers if necessary, and tracking changes to vtype)
    lmul_overwrite: int | None = None
    if params.lmul < 1:
        lmul_overwrite = 1
    elif widen:
        # We need to overwrite LMUL in widening cases
        lmul_overwrite = int(params.lmul)

    vl_overwrite: int | None = None
    if vl_register_or_imm == 0:  # Loads at vl=0 are a no-op
        vl_overwrite = 1

    if not vd_preloaded:
        vd_lmul_overwrite = params.lmul * 2 if "vd" in widen else lmul_overwrite
        vd_sew = params.sew * (2 if "vd" in widen else 1)
        setup.extend(
            load_vec_reg(
                params.vd,
                params.vd_val_pointer,
                params,
                sew_override=vd_sew,
                lmul=vd_lmul_overwrite,
                vl_register_or_imm=vl_overwrite,
            )
        )

    if not vs2_preloaded:
        vs2_lmul_overwrite = params.lmul * 2 if "vs2" in widen else lmul_overwrite
        vs2_sew = params.sew * (2 if "vs2" in widen else 1)
        setup.extend(
            load_vec_reg(
                params.vs2,
                params.vs2_val_pointer,
                params,
                sew_override=vs2_sew,
                lmul=vs2_lmul_overwrite,
                vl_register_or_imm=vl_overwrite,
            )
        )

    setup.append(f"LI (x{params.rs1}, {params.rs1val})")

    # Ensure vtype is correct for the instruction
    if (lmul_overwrite is not None or vl_overwrite is not None) and not (vd_preloaded and vs2_preloaded):
        setup.append(reload_vtype(params, vl_register_or_imm))

    # Now we are done with the clean up register
    if isinstance(vl_register_or_imm, str) and vl_register_or_imm != "x0":
        test_data.int_regs.return_register(int(vl_register_or_imm[1:]))

    if params.maskval:
        test = [f"{instr_str} v{params.vd}, v{params.vs2}, x{params.rs1}, v0.t"]
    else:
        test = [f"{instr_str} v{params.vd}, v{params.vs2}, x{params.rs1}"]

    # Return non-vd registers, so that we have enough for length-suite sigupd
    test_data.vec_regs.deallocate_operand("vs2")
    test_data.vec_regs.deallocate_operand("vs1")

    if params.vector_suite == "length":
        sig_lmul = params.lmul * (2 if "vd" in widen else 1)
        check = [*write_sigupd_v_len(test_data, params, 1, sig_lmul, widen_vd="vd" in widen)]
    else:
        check = [*write_sigupd_v(test_data, params, widen_vd="vd" in widen)]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(0)

    return (setup, test, check)
