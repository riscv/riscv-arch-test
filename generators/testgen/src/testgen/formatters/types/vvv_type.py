##################################
# vvv_type.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.vector_helpers import (
    VectorLoad,
    handle_parameter_exclusions,
    load_test_vtype,
    load_vec_regs,
    load_vxrm,
    prep_mask_v,
    write_sigupd_v,
    write_sigupd_v_len,
    write_sigupd_vxsat,
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

    check = write_sigupd_vxsat(test_data) + check

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
    assert params.temp_reg is not None, f"temp_reg must be provided for {type_name}-type instructions"
    assert params.sew is not None, f"sew must be provided for {type_name}-type instructions"
    assert params.lmul is not None, f"lmul must be provided for {type_name}-type instructions"
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

    # Setup Mask
    if params.maskval:
        setup.extend(prep_mask_v(params.maskval, test_data, params, clobber_vd=True))

    # Setup VXRM (if necessary)
    if params.vxrm is not None:
        setup.extend(load_vxrm(params.vxrm))

    vd_vl = params.vl if params.vector_suite == "base" else "vlmax"
    vs2_vl = params.vl if params.vector_suite == "base" or not enable_vs2_preload else "vlmax"

    to_load = [
        VectorLoad(reg="vd", widen="vd" in widen, vl=vd_vl, no_fractional_load=True),
        VectorLoad(reg="vs2", widen="vs2" in widen, vl=vs2_vl),
    ]

    if not (params.vs1 == params.vs2 and params.vector_suite == "length" and enable_vs2_preload):
        # Don't overwrite vs2 in this case
        to_load.append(VectorLoad(reg="vs1", widen="vs1" in widen))

    load_code, random_vl_reg = load_vec_regs(to_load, params, test_data)
    setup.extend(load_code)
    setup.append(load_test_vtype(params, random_vl_reg))

    # We don't need random_vl_reg anymore
    if random_vl_reg.startswith("x"):
        test_data.int_regs.return_register(int(random_vl_reg[1:]))

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
        check = [*write_sigupd_v_len(test_data, params, sig_lmul, widen_vd="vd" in widen, vcompress=vcompress)]
    else:
        check = [*write_sigupd_v(test_data, params, widen_vd="vd" in widen)]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(0)

    handle_parameter_exclusions(params.lmul, setup, check)

    return (setup, test, check)
