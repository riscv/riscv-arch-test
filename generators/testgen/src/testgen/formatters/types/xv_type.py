##################################
# xv_type.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import write_sigupd
from testgen.asm.vector_helpers import load_vec_reg, prep_base_v, prep_mask_v, reload_vtype
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter

xv_config = InstructionTypeConfig(required_params={"rd", "vs2"}, vector_data=VectorTypeConfig())
vmvxs_config = InstructionTypeConfig(required_params={"rd", "vs2"}, vector_data=VectorTypeConfig(scalar_regs={"vs2"}))


@add_instruction_formatter("XV", xv_config)
def format_xv_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_xv_like_type(instr_str, test_data, params, "XV")


@add_instruction_formatter("VMVXS", vmvxs_config)
def format_vmvxs_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.maskval is None, "VMVXS-Type instructions cannot be masked"
    return format_xv_like_type(instr_str, test_data, params, "VMVXS", scalar_vs2=True)


def format_xv_like_type(
    instr_str: str, test_data: TestData, params: InstructionParams, type_name: str, *, scalar_vs2: bool = False
) -> tuple[list[str], list[str], list[str]]:
    assert params.vs2 is not None and params.vs2_val_pointer is not None, (
        f"vs2 and vs2_val_pointer must be provided for {type_name}-type instructions"
    )
    assert params.rd is not None, f"rd must be provided for {type_name}-type instructions"
    assert params.temp_reg is not None, f"temp_reg must provided for be {type_name}-type instructions"
    assert params.sew is not None, f"sew must provided for be {type_name}-type instructions"
    assert params.lmul is not None, f"lmul must provided for be {type_name}-type instructions"
    assert test_data.test_chunk is not None, f"format_{type_name.lower()}_type must be used with an active TestChunk"

    test_data.test_chunk.vector_labels.extend(
        [
            (params.vs2_val_pointer, *test_data.vector_labels[params.vs2_val_pointer]),
        ]
    )

    # Set up the instructions: Mask, vs2 (at correct lmul), no need to touch rd
    setup = []

    # Setup Mask
    if params.maskval:
        setup.extend(prep_mask_v(params.maskval, test_data, params))

    prep_lines, vl_register_or_imm = prep_base_v(test_data, params, [params.vs2])
    setup.extend(prep_lines)

    lmul_override = 1 if scalar_vs2 else None
    setup.extend(load_vec_reg(params.vs2, params.vs2_val_pointer, params, lmul=lmul_override))

    if lmul_override is not None:
        setup.append(reload_vtype(params, vl_register_or_imm))
    if isinstance(vl_register_or_imm, str) and vl_register_or_imm != "x0":
        test_data.int_regs.return_register(int(vl_register_or_imm[1:]))

    if params.maskval:
        test = [f"{instr_str} x{params.rd}, v{params.vs2}, v0.t"]
    else:
        test = [f"{instr_str} x{params.rd}, v{params.vs2}"]

    check = [write_sigupd(params.rd, test_data, "int")]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(0)

    return (setup, test, check)
