##################################
# vvv_type.py
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

vvv_config = InstructionTypeConfig(required_params={"vd", "vs1", "vs2"}, vector_data=VectorTypeConfig())
wvv_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(overlap_constraints={("vd_bottom", "vs1"), ("vd_bottom", "vs2")}, widened_regs={"vd"}),
)
vwv_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(
        overlap_constraints={("vd", "vs2_top"), ("vs1", "vs2")},
        widened_regs={"vs2"},
    ),
)
wwv_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(
        overlap_constraints={("vd_bottom", "vs1"), ("vs1", "vs2")},
        widened_regs={"vd", "vs2"},
    ),
)
vvvm_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2", "maskval"},
    vector_data=VectorTypeConfig(
        overlap_constraints={("vd", "v0"), ("vs1", "v0"), ("vs2", "v0")},
    ),
)
vvv_acc_config = InstructionTypeConfig(required_params={"vd", "vs1", "vs2"}, vector_data=VectorTypeConfig())
wvv_acc_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(overlap_constraints={("vd", "vs2"), ("vd", "vs1")}, widened_regs={"vd"}),
)
vvv_sat_config = InstructionTypeConfig(required_params={"vd", "vs1", "vs2"}, vector_data=VectorTypeConfig())
vvvp_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(overlap_constraints={("vd", "vs1"), ("vd", "vs2")}),
)
vcompress_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(overlap_constraints={("vd", "vs1"), ("vd", "vs2"), ("vs1", "vs2")}),
)


@add_instruction_formatter("VVV", vvv_config)
def format_vvv(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vvv_like_type(instr_str, test_data, params, "VVV")


@add_instruction_formatter("WWV", wwv_config)
def format_wwv(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vvv_like_type(instr_str, test_data, params, "WWV", widen={"vd", "vs2"})


@add_instruction_formatter("WVV", wvv_config)
def format_wvv(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vvv_like_type(instr_str, test_data, params, "WVV", widen={"vd"})


@add_instruction_formatter("VWV", vwv_config)
def format_vwv(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vvv_like_type(instr_str, test_data, params, "VWV", widen={"vs2"})


@add_instruction_formatter("VVVM", vvvm_config)
def format_vvvm(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.maskval is not None, "Masks are required for VVVM-Type Instructions"
    setup, test, check = format_vvv_like_type(instr_str, test_data, params, "VVVM")
    # Overwrite the test, as otherwise it generates with v0.t
    test = [f"{instr_str} v{params.vd}, v{params.vs2}, v{params.vs1}, v0"]
    return setup, test, check


@add_instruction_formatter("VVV_ACC", vvv_acc_config)
def format_vvv_acc(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    setup, test, check = format_vvv_like_type(instr_str, test_data, params, "VVV_ACC")
    # Overwrite the test, as otherwise it generates in the wrong order
    if params.maskval:
        test = [f"{instr_str} v{params.vd}, v{params.vs1}, v{params.vs2}, v0.t"]
    else:
        test = [f"{instr_str} v{params.vd}, v{params.vs1}, v{params.vs2}"]
    return setup, test, check


@add_instruction_formatter("WVV_ACC", wvv_acc_config)
def format_wvv_acc(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    setup, test, check = format_vvv_like_type(instr_str, test_data, params, "WVV_ACC", widen={"vd"})
    # Overwrite the test, as otherwise it generates in the wrong order
    if params.maskval:
        test = [f"{instr_str} v{params.vd}, v{params.vs1}, v{params.vs2}, v0.t"]
    else:
        test = [f"{instr_str} v{params.vd}, v{params.vs1}, v{params.vs2}"]
    return setup, test, check


@add_instruction_formatter("VVV_SAT", vvv_sat_config)
def format_vvv_sat(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    setup, test, check = format_vvv_like_type(instr_str, test_data, params, "VVV_SAT")
    setup = ["csrwi vxsat, 0"] + setup
    return setup, test, check


@add_instruction_formatter("VVVP", vvvp_config)
def format_vvvp(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vvv_like_type(instr_str, test_data, params, "VVVP", enable_vs2_preload=True)


@add_instruction_formatter("VCOMPRESS", vcompress_config)
def format_vcompress(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.maskval is None, "vcompress cannot be masked"
    return format_vvv_like_type(instr_str, test_data, params, "VCOMPRESS")


def format_vvv_like_type(
    instr_str: str,
    test_data: TestData,
    params: InstructionParams,
    type_name: str,
    *,
    widen: set[str] | None = None,
    enable_vs2_preload: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    assert params.vs1 is not None and params.vs1_val_pointer is not None, (
        f"vs1 and vs1_val_pointer must be provided for {type_name}-type instructions"
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
            (params.vs1_val_pointer, *test_data.vector_labels[params.vs1_val_pointer]),
            (params.vs2_val_pointer, *test_data.vector_labels[params.vs2_val_pointer]),
            (params.vd_val_pointer, *test_data.vector_labels[params.vd_val_pointer]),
        ]
    )

    setup = []
    registers = [params.vd, params.vs2, params.vs1]

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

    # Preload vs2 for VVVP
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

    vl_overwrite: int | str | None = None
    if vl_register_or_imm == 0:  # Loads at vl=0 are a no-op
        vl_overwrite = 1
    elif lmul_overwrite is not None:
        vl_overwrite = vl_register_or_imm

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

    if not (vs2_preloaded and params.vs2 == params.vs1):  # Don't overwrite a preloaded register
        vs1_lmul_overwrite = params.lmul * 2 if "vs1" in widen else lmul_overwrite
        vs1_sew = params.sew * (2 if "vs1" in widen else 1)
        setup.extend(
            load_vec_reg(
                params.vs1,
                params.vs1_val_pointer,
                params,
                sew_override=vs1_sew,
                lmul=vs1_lmul_overwrite,
                vl_register_or_imm=vl_overwrite,
            )
        )

    # Ensure vtype is correct for the instruction
    if lmul_overwrite is not None or vl_overwrite is not None:
        setup.append(reload_vtype(params, vl_register_or_imm))

    # Now we are done with the clean up register
    if isinstance(vl_register_or_imm, str) and vl_register_or_imm != "x0":
        test_data.int_regs.return_register(int(vl_register_or_imm[1:]))

    if params.maskval:
        test = [f"{instr_str} v{params.vd}, v{params.vs2}, v{params.vs1}, v0.t"]
    else:
        test = [f"{instr_str} v{params.vd}, v{params.vs2}, v{params.vs1}"]

    # Return non-vd registers, so that we have enough for length-suite sigupd
    test_data.vec_regs.deallocate_operand("vs2")
    test_data.vec_regs.deallocate_operand("vs1")

    if params.vector_suite == "length":
        vcompress = type_name == "VCOMPRESS"
        sig_lmul = params.lmul * (2 if "vd" in widen else 1)
        check = [*write_sigupd_v_len(test_data, params, 1, sig_lmul, widen_vd="vd" in widen, vcompress=vcompress)]
    else:
        check = [*write_sigupd_v(test_data, params, widen_vd="vd" in widen)]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(0)

    return (setup, test, check)
