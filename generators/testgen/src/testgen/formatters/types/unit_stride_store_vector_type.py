##################################
# unit_stride_store_vector_type.py
#
#
#
# rwolk@hmc.edu June 2026
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
    write_sigupd_v_mask_prod,
)
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter
from testgen.instructions.vector import parse_vector_instruction_info

vsus_config = InstructionTypeConfig(
    required_params={"vs3", "rs1"}, instruction_class=["store"], vector_data=VectorTypeConfig()
)
vsseg_config = InstructionTypeConfig(
    required_params={"vs3", "rs1"},
    instruction_class=["store", "segmented"],
    vector_data=VectorTypeConfig(),
)
vsm_config = InstructionTypeConfig(
    required_params={"vs3", "rs1"},
    instruction_class=["store"],
    vector_data=VectorTypeConfig(
        mask_regs={"vs3"},
    ),
)


@add_instruction_formatter("VSUS", vsus_config)
def format_vsus_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vsseg_like_type(instr_str, test_data, params, "VLUS")


@add_instruction_formatter("VSSEG", vsseg_config)
def format_vsseg_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vsseg_like_type(instr_str, test_data, params, "VSSEG")


@add_instruction_formatter("VSM", vsm_config)
def format_vlm_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.maskval is None, "VLM-Type instructions cannot be masked"
    return format_vsseg_like_type(instr_str, test_data, params, "VSM", vs3_mask=True)


def format_vsseg_like_type(
    instr_str: str,
    test_data: TestData,
    params: InstructionParams,
    instr_type: str,
    *,
    vs3_mask: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    assert params.rs1 is not None and params.rs1val_pointer is not None, (
        f"rs1 and rs1val_pointer must be provided for {instr_type}-type instructions"
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
    emul = params.lmul * eew / params.sew if not vs3_mask else 1
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
    setup.append(load_test_vtype(params, random_vl_reg))

    # We don't need random_vl_reg anymore
    if random_vl_reg.startswith("x"):
        test_data.int_regs.return_register(int(random_vl_reg[1:]))

    # Reload after storing to arbitrary memory
    equivalent_load = "vl" + instr_str[2:]
    if params.maskval:
        test = [
            f"{instr_str} v{params.vs3}, (x{params.rs1}), v0.t",
            f"{equivalent_load} v{params.vd}, (x{params.rs1}), v0.t",
        ]
    else:
        test = [
            f"{instr_str} v{params.vs3}, (x{params.rs1})",
            f"{equivalent_load} v{params.vd}, (x{params.rs1})",
        ]

    if params.vector_suite == "length":
        check = [
            *write_sigupd_v_len(
                test_data,
                params,
                emul,
                segments=segments,
                sew_override=info.load_store_eew,
                mask_producing=vs3_mask,
                check_reg=reload_register,
            )
        ]

        if vs3_mask:
            check.extend(
                [
                    "# Mask-producing SIGUPD Requires a VLMAX variant of the instruction. But, for vlm.v specifically, the",
                    "# spec does not allow the vlm.v variant. So, we fill the VLMAX sigupd with the same value",
                    *write_sigupd_v_mask_prod(test_data, params),
                ]
            )
    else:
        check = [
            *write_sigupd_v(
                test_data, params, sew_override=info.load_store_eew, mask_producing=vs3_mask, check_reg=reload_register
            )
        ]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(0)

    handle_parameter_exclusions(params.lmul, setup, check, encoded_eew=eew)

    return (setup, test, check)
