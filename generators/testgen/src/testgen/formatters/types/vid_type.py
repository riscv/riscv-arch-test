##################################
# vid_type.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.vector_helpers import (
    load_vec_reg,
    prep_base_v,
    prep_mask_v,
    write_sigupd_v,
    write_sigupd_v_len,
)
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter

vid_config = InstructionTypeConfig(required_params={"vd"}, vector_data=VectorTypeConfig())


@add_instruction_formatter("VID", vid_config)
def format_vid(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.vd is not None and params.vd_val_pointer is not None, (
        "vd and vd_val_pointer must be provided for VID-type instructions"
    )
    assert params.temp_reg is not None, "temp_reg must provided for be VID-type instructions"
    assert params.sew is not None, "sew must provided for be VID-type instructions"
    assert params.lmul is not None, "lmul must provided for be VID-type instructions"
    assert test_data.test_chunk is not None, "format_vid_type must be used with an active TestChunk"

    test_data.test_chunk.vector_labels.append(
        (params.vd_val_pointer, *test_data.vector_labels[params.vd_val_pointer]),
    )

    # Set up the instructions: Mask, vd (potentially preloaded)
    setup = []
    registers = [params.vd]

    # Setup Mask
    if params.maskval:
        setup.extend(prep_mask_v(params.maskval, test_data, params))

    # Preload vd at vlmax
    vd_preloaded = False
    if params.vector_suite == "length":
        setup.extend(
            load_vec_reg(params.vd, params.vd_val_pointer, params, lmul=max(params.lmul, 1), vl_register_or_imm="x0")
        )
        vd_preloaded = True
        registers.remove(params.vd)

    prep_lines, vl_register_or_imm = prep_base_v(test_data, params, registers)
    setup.extend(prep_lines)

    if not vd_preloaded:
        setup.extend(load_vec_reg(params.vd, params.vd_val_pointer, params))

    # No need to reset vtype as there is one vector operand
    if isinstance(vl_register_or_imm, str) and vl_register_or_imm != "x0":
        test_data.int_regs.return_register(int(vl_register_or_imm[1:]))

    test = [f"{instr_str} v{params.vd}, v0.t"] if params.maskval else [f"{instr_str} v{params.vd}"]

    if params.vector_suite == "length":
        check = [*write_sigupd_v_len(test_data, params, 1, params.lmul)]
    else:
        check = [*write_sigupd_v(test_data, params)]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(0)

    return (setup, test, check)
