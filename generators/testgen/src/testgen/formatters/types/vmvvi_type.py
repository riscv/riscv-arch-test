##################################
# vmvvi_type.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.vector_helpers import (
    VectorLoad,
    handle_parameter_exclusions,
    load_test_vtype,
    load_vec_regs,
    prep_mask_v,
    write_sigupd_v,
    write_sigupd_v_len,
)
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter

vmvvi_config = InstructionTypeConfig(required_params={"vd", "immval"}, imm_bits=5, vector_data=VectorTypeConfig())


@add_instruction_formatter("VMVVI", vmvvi_config)
def format_vmvvi(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.vd is not None and params.vd_val_pointer is not None, (
        "vd and vd_val_pointer must be provided for VMVVI-type instructions"
    )
    assert params.immval is not None, "immval must be provided for VMVVI-type instructions"
    assert params.temp_reg is not None, "temp_reg must be provided for VID-type instructions"
    assert params.sew is not None, "sew must be provided for VID-type instructions"
    assert params.lmul is not None, "lmul must be provided for VID-type instructions"
    assert test_data.test_chunk is not None, "format_vid_type must be used with an active TestChunk"

    test_data.test_chunk.vector_labels.append(
        (params.vd_val_pointer, *test_data.vector_labels[params.vd_val_pointer]),
    )

    # Set up the instructions: Mask, vd (potentially preloaded)
    setup = []

    # Setup Mask
    if params.maskval:
        setup.extend(prep_mask_v(params.maskval, test_data, params))

    vd_vl = params.vl if params.vector_suite == "base" else "vlmax"
    load_code, random_vl_reg = load_vec_regs([VectorLoad("vd", vl=vd_vl, no_fractional_load=True)], params, test_data)
    setup.extend(load_code)
    setup.append(load_test_vtype(params, random_vl_reg))

    # We don't need random_vl_reg anymore
    if random_vl_reg.startswith("x"):
        test_data.int_regs.return_register(int(random_vl_reg[1:]))

    if params.maskval:
        test = [f"{instr_str} v{params.vd}, {params.immval}, v0.t"]
    else:
        test = [f"{instr_str} v{params.vd}, {params.immval}"]

    if params.vector_suite == "length":
        check = [*write_sigupd_v_len(test_data, params, params.lmul)]
    else:
        check = [*write_sigupd_v(test_data, params)]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(0)

    handle_parameter_exclusions(params.lmul, setup, check)

    return (setup, test, check)
