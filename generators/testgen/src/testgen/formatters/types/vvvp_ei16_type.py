##################################
# vvvp_ei16_type.py
#
# rwolk@hmc.edu October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.vector_helpers import (
    VectorLoad,
    handle_parameter_exclusions,
    index_register_safety,
    load_test_vtype,
    load_vec_regs,
    prep_mask_v,
    write_sigupd_v,
    write_sigupd_v_len,
)
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter

vvvp_ei16_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(overlap_constraints={("vd", "vs1"), ("vd", "vs2")}, index_register="vs1"),
)


@add_instruction_formatter("VVVP_EI16", vvvp_ei16_config)
def format_vvvp_ei16_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.vs1 is not None and params.vs1_val_pointer is not None, (
        "vs1 and vs1_val_pointer must be provided for VVVP_EI16-type instructions"
    )
    assert params.vs2 is not None and params.vs2_val_pointer is not None, (
        "vs2 and vs2_val_pointer must be provided for VVVP_EI16-type instructions"
    )
    assert params.vd is not None and params.vd_val_pointer is not None, (
        "vd and vd_val_pointer must be provided for VVVP_EI16-type instructions"
    )
    assert params.temp_reg is not None, "temp_reg must be provided for VVVP_EI16-type instructions"
    assert params.sew is not None, "sew must be provided for VVVP_EI16-type instructions"
    assert params.lmul is not None, "lmul must be provided for VVVP_EI16-type instructions"
    assert test_data.test_chunk is not None, "format_vvvp_ei16_type must be used with an active TestChunk"

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

    vd_vl = params.vl if params.vector_suite == "base" else "vlmax"
    vs1_vl = "vlmax" if params.vs1 == params.vs2 else params.vl

    to_load = [
        VectorLoad(reg="vd", vl=vd_vl, no_fractional_load=True),
        VectorLoad(reg="vs2", vl="vlmax"),
        VectorLoad(reg="vs1", vl=vs1_vl, sew=16, lmul=16 * params.lmul / params.sew),
    ]

    load_code, random_vl_reg = load_vec_regs(to_load, params, test_data, base_tail_fill=True)
    setup.extend(load_code)

    if not params.ignore_vector_safety:
        setup.extend(index_register_safety(params.vs1, 16, 1, random_vl_reg, test_data, params, align_indices=False))

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
        check = [*write_sigupd_v_len(test_data, params, params.lmul)]
    else:
        check = [*write_sigupd_v(test_data, params)]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(0)

    handle_parameter_exclusions(params.lmul, setup, check)

    return (setup, test, check)
