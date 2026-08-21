##################################
# strided_store_vector_type.py
#
#
# rwolk@hmc.edu August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import random

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

vss_config = InstructionTypeConfig(
    required_params={"vs3", "rs1", "rs2"}, instruction_class=["store", "strided"], vector_data=VectorTypeConfig()
)
vssseg_config = InstructionTypeConfig(
    required_params={"vs3", "rs1", "rs2"},
    instruction_class=["store", "strided", "segmented"],
    vector_data=VectorTypeConfig(),
)


@add_instruction_formatter("VSS", vss_config)
def format_vlus_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vssseg_like_type(instr_str, test_data, params, "VSS")


@add_instruction_formatter("VSSSEG", vssseg_config)
def format_vlseg_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vssseg_like_type(instr_str, test_data, params, "VSSSEG")


def format_vssseg_like_type(
    instr_str: str,
    test_data: TestData,
    params: InstructionParams,
    instr_type: str,
) -> tuple[list[str], list[str], list[str]]:
    assert params.rs1 is not None and params.rs1val_pointer is not None, (
        f"rs1 and rs1val_pointer must be provided for {instr_type}-type instructions"
    )
    assert params.rs2 is not None and params.rs2val is not None, (
        f"rs2 and rs2val must be provided for {instr_type}-type instructions"
    )
    assert params.vs3 is not None and params.vs3_val_pointer is not None, (
        f"vs3 and vs3_val_pointer must be provided for {instr_type}-type instructions"
    )
    assert params.vd is None and params.vd_val_pointer is None, (
        f"vd and vd_val_pointer must NOT be provided for {instr_type}-type instructions"
    )
    assert params.temp_reg is not None, f"temp_reg must be provided for {instr_type}-type instructions"
    assert params.sew is not None, "SEW must be provided for Vector instructions"
    assert params.lmul is not None, f"lmul must be provided for {instr_type}-type instructions"
    assert test_data.test_chunk is not None, f"format_{instr_type.lower()}_type must be used with an active TestChunk"

    test_data.test_chunk.vector_labels.extend(
        [
            (params.rs1val_pointer, *test_data.vector_labels[params.rs1val_pointer]),
            (params.vs3_val_pointer, *test_data.vector_labels[params.vs3_val_pointer]),
        ]
    )

    # Extract General Instruction Info
    info = parse_vector_instruction_info(instr_str, instr_type)
    eew = info.load_store_eew
    assert eew is not None, f"Could not extract an EEW from {instr_type}-type instruction {instr_str}"
    emul = params.lmul * eew / params.sew
    segments = info.segments

    setup = []

    # Setup Mask
    if params.maskval:
        setup.extend(prep_mask_v(params.maskval, test_data, params))

    reload_register = random.choice(list(test_data.vec_regs.free_registers(int(max(emul, 1)), segments)))
    params.vd = reload_register
    params.vd_val_pointer = "NOT_A_LABEL"  # Placeholder value that should NOT end up in generated code
    test_data.vec_regs.allocate_operand("vd", reload_register, int(max(emul, 1)) * segments)

    # Preload vd at vlmax
    vd_vl = params.vl if params.vector_suite == "base" else "vlmax"
    to_load = [
        VectorLoad(reg="vs3", vl=vd_vl, no_fractional_load=True, segments=segments, lmul=emul, sew=eew),
        VectorLoad(reg="vd", segments=segments, lmul=emul, sew=eew, no_fractional_load=True, only_setup_tail=True),
    ]
    load_code, random_vl_reg = load_vec_regs(to_load, params, test_data)
    setup.extend(load_code)
    setup.append(f"LA (x{params.rs1}, {params.rs1val_pointer})")

    # Ensure rs2val is valid (this only matters when there is more than one element)
    if params.vector_suite == "length" and not params.ignore_vector_safety:
        assert params.rs2val % (eew // 8) == 0, f"Stride {params.rs2val} is not aligned for {instr_str}"
        assert params.rs2val % (eew * info.segments // 8) == 0, (
            f"Stride {params.rs2val} allows for data to be overwritten for {instr_str}"
        )
        assert params.rs2val != 0, "Stride cannot be zero for strided stores because they are unordered"

    setup.append(f"LI (x{params.rs2}, {params.rs2val})")
    setup.append(load_test_vtype(params, random_vl_reg))

    # We don't need random_vl_reg anymore
    if random_vl_reg.startswith("x"):
        test_data.int_regs.return_register(int(random_vl_reg[1:]))

    equivalent_load = "vl" + instr_str[2:]
    if params.maskval:
        test = [
            f"{instr_str} v{params.vs3}, (x{params.rs1}), x{params.rs2}, v0.t",
            f"{equivalent_load} v{params.vd}, (x{params.rs1}), x{params.rs2}, v0.t",
        ]
    else:
        test = [
            f"{instr_str} v{params.vs3}, (x{params.rs1}), x{params.rs2}",
            f"{equivalent_load} v{params.vd}, (x{params.rs1}), x{params.rs2}",
        ]

    if params.vector_suite == "length":
        check = [*write_sigupd_v_len(test_data, params, emul, segments=segments, sew_override=info.load_store_eew)]
    else:
        check = [*write_sigupd_v(test_data, params, sew_override=info.load_store_eew)]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(0)

    handle_parameter_exclusions(params.lmul, setup, check, encoded_eew=eew)

    return (setup, test, check)
