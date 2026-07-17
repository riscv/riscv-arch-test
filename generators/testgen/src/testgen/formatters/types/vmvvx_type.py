##################################
# vmvvx_type.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.vector_helpers import (
    load_vec_reg,
    prep_base_v,
    prep_mask_v,
    reload_vtype,
    write_sigupd_v,
    write_sigupd_v_len,
)
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter

vmvvx_config = InstructionTypeConfig(required_params={"vd", "rs1"}, vector_data=VectorTypeConfig())
vmvsx_config = InstructionTypeConfig(required_params={"vd", "rs1"}, vector_data=VectorTypeConfig(scalar_regs={"vd"}))


@add_instruction_formatter("VMVVX", vmvvx_config)
def format_vmvvx_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vmvvx_like_type(instr_str, test_data, params, "VMVVX")


@add_instruction_formatter("VMVSX", vmvsx_config)
def format_vmvsx_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vmvvx_like_type(instr_str, test_data, params, "VMVSX", scalar_vd=True)


def format_vmvvx_like_type(
    instr_str: str, test_data: TestData, params: InstructionParams, type_name: str, *, scalar_vd: bool = False
) -> tuple[list[str], list[str], list[str]]:
    assert params.vd is not None and params.vd_val_pointer is not None, (
        f"vd and vd_val_pointer must be provided for {type_name}-type instructions"
    )
    assert params.rs1 is not None and params.rs1val is not None, (
        f"rs1 and rs1val must be provided for {type_name}-type instructions"
    )
    assert params.temp_reg is not None, f"temp_reg must provided for be {type_name}-type instructions"
    assert params.sew is not None, f"sew must provided for be {type_name}-type instructions"
    assert params.lmul is not None, f"lmul must provided for be {type_name}-type instructions"
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
    lmul = params.lmul if not scalar_vd else 1
    vd_preloaded = False
    if params.vector_suite == "length":
        setup.extend(load_vec_reg(params.vd, params.vd_val_pointer, params, lmul=max(lmul, 1), vl_register_or_imm="x0"))
        vd_preloaded = True
        registers.remove(params.vd)

    prep_lines, vl_register_or_imm = prep_base_v(test_data, params, registers)
    setup.extend(prep_lines)

    if not vd_preloaded:
        # This is set if we need to load at a different lmul (e.g. we have a scalar operand)
        lmul_override = lmul if lmul != params.lmul else None
        setup.extend(load_vec_reg(params.vd, params.vd_val_pointer, params, lmul=lmul_override))
        if lmul_override is not None:
            setup.append(reload_vtype(params, vl_register_or_imm))

    setup.append(f"LI (x{params.rs1}, {params.rs1val})")

    if isinstance(vl_register_or_imm, str) and vl_register_or_imm != "x0":
        test_data.int_regs.return_register(int(vl_register_or_imm[1:]))

    if params.maskval:
        test = [f"{instr_str} v{params.vd}, x{params.rs1}, v0.t"]
    else:
        test = [f"{instr_str} v{params.vd}, x{params.rs1}"]

    if params.vector_suite == "length":
        check = [*write_sigupd_v_len(test_data, params, 1, lmul, scalar_dest=scalar_vd)]
    else:
        check = [*write_sigupd_v(test_data, params)]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(0)

    return (setup, test, check)
