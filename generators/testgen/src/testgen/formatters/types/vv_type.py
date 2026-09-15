##################################
# vv_type.py
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
from testgen.instructions.vector import parse_vector_instruction_info

vmvr_config = InstructionTypeConfig(required_params={"vd", "vs2"}, vector_data=VectorTypeConfig())
vext_config = InstructionTypeConfig(
    required_params={"vd", "vs2"},
    vector_data=VectorTypeConfig(overlap_constraints={("vd_bottom", "vs2")}),
)
vm_config = InstructionTypeConfig(
    required_params={"vd", "vs2"},
    vector_data=VectorTypeConfig(
        mask_regs={"vs2"},
        overlap_constraints={("vd", "vs2")},
        masked_constraints={("vd", "v0")},
    ),
)


@add_instruction_formatter("VMVR", vmvr_config)
def format_vmvr_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    n_registers = int(instr_str[3])
    return format_vv_like_type(instr_str, test_data, params, "VMVR", lmul_override=n_registers, preload_vs2=True)


@add_instruction_formatter("VEXT", vext_config)
def format_vext_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    info = parse_vector_instruction_info(instr_str, "VEXT")
    assert info.vext_multiplier is not None, f"Unable to extract multiplier for VEXT-type instruction {instr_str}"
    return format_vv_like_type(instr_str, test_data, params, "VEXT", vs2_lmul_multiplier=info.vext_multiplier)


@add_instruction_formatter("VM", vm_config)
def format_vm_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vv_like_type(instr_str, test_data, params, "VM", vs2_mask=True)


def format_vv_like_type(
    instr_str: str,
    test_data: TestData,
    params: InstructionParams,
    type_name: str,
    *,
    lmul_override: float | None = None,
    vs2_lmul_multiplier: float = 1,
    vs2_mask: bool = False,
    preload_vs2: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    assert params.vs2 is not None and params.vs2_val_pointer is not None, (
        f"vs2 and vs2_val_pointer must be provided for {type_name}-type instructions"
    )
    assert params.vd is not None and params.vd_val_pointer is not None, (
        f"vd and vd_val_pointer must be provided for {type_name}-type instructions"
    )
    assert params.temp_reg is not None, f"temp_reg must be provided for {type_name}-type instructions"
    assert params.sew is not None, f"sew must be provided for {type_name}-type instructions"
    assert params.lmul is not None or lmul_override is not None, (
        f"lmul must be provided for {type_name}-type instructions"
    )
    assert test_data.test_chunk is not None, f"format_{type_name.lower()}_type must be used with an active TestChunk"

    test_data.test_chunk.vector_labels.extend(
        [
            (params.vs2_val_pointer, *test_data.vector_labels[params.vs2_val_pointer]),
            (params.vd_val_pointer, *test_data.vector_labels[params.vd_val_pointer]),
        ]
    )

    # Set up the instructions: Mask, vd (potentially preloaded), vs2 (at correct lmul)
    setup = []

    # Setup Mask
    if params.maskval:
        setup.extend(prep_mask_v(params.maskval, test_data, params))

    lmul = lmul_override if lmul_override is not None else params.lmul
    # This must be true because above we asserted, params.lmul is not None or lmul_override is not None
    assert lmul is not None

    vd_vl = params.vl if params.vector_suite == "base" else "vlmax"
    vs2_vl = params.vl if params.vector_suite == "base" or not preload_vs2 else "vlmax"
    vs2_lmul = max(lmul * vs2_lmul_multiplier, 1) if not vs2_mask else 1
    vs2_sew = int(params.sew * vs2_lmul_multiplier)

    to_load = [
        VectorLoad(reg="vd", vl=vd_vl, lmul=lmul, no_fractional_load=True),
        VectorLoad(reg="vs2", vl=vs2_vl, lmul=vs2_lmul, sew=vs2_sew),
    ]

    load_code, random_vl_reg = load_vec_regs(to_load, params, test_data)
    setup.extend(load_code)
    setup.append(load_test_vtype(params, random_vl_reg))

    # We don't need random_vl_reg anymore
    if random_vl_reg.startswith("x"):
        test_data.int_regs.return_register(int(random_vl_reg[1:]))

    if params.maskval:
        test = [f"{instr_str} v{params.vd}, v{params.vs2}, v0.t"]
    else:
        test = [f"{instr_str} v{params.vd}, v{params.vs2}"]

    if params.vector_suite == "length":
        check = [*write_sigupd_v_len(test_data, params, lmul)]
    else:
        check = [*write_sigupd_v(test_data, params)]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(0)

    handle_parameter_exclusions(lmul, setup, check)

    return (setup, test, check)
