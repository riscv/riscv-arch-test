##################################
# indexed_store_vector_type.py
#
#
# rwolk@hmc.edu August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import random

from testgen.asm.vector_helpers import (
    VectorLoad,
    get_lmul_flag,
    handle_parameter_exclusions,
    load_test_vtype,
    load_vec_regs,
    prep_mask_v,
    write_sigupd_v,
    write_sigupd_v_len,
)
from testgen.data.params import InstructionParams
from testgen.data.random import random_int
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter
from testgen.instructions.vector import parse_vector_instruction_info


def unordered_index_element_generator(element_count: int, sew: int) -> list[int]:
    # vlmax can take on values of any power of two, from 1 to the power of two exceeding element_count
    # All items in the generated list from [0, vlmax) must be unique mod 2*vlmax for all possible vlmaxes
    # LIMITATIONS: For SEW=8, unique indices are not guaranteed

    res = []
    sew_limit = 2**sew - 1

    for i in range(element_count):
        vlmax_power_of_2 = i.bit_length()

        # Generate a unique index value under limit for vlmax
        next_value = min(random_int(vlmax_power_of_2 + 1, signed=False), sew_limit)
        while next_value in res and i <= sew_limit:
            next_value = random_int(min(vlmax_power_of_2 + 1, sew), signed=False)

        res.append(next_value)

    return res


vsux_config = InstructionTypeConfig(
    required_params={"vs3", "rs1", "vs2"},
    instruction_class=["store", "indexed"],
    vector_data=VectorTypeConfig(random_element_generator=unordered_index_element_generator),
)

vsox_config = InstructionTypeConfig(
    required_params={"vs3", "rs1", "vs2"}, instruction_class=["store", "indexed"], vector_data=VectorTypeConfig()
)

vsuxseg_config = InstructionTypeConfig(
    required_params={"vs3", "rs1", "vs2"},
    instruction_class=["store", "indexed", "segmented"],
    vector_data=VectorTypeConfig(random_element_generator=unordered_index_element_generator),
)

vsoxseg_config = InstructionTypeConfig(
    required_params={"vs3", "rs1", "vs2"},
    instruction_class=["store", "indexed", "segmented"],
    vector_data=VectorTypeConfig(),
)


@add_instruction_formatter("VSOX", vsox_config)
def format_vlox_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vsxseg_like_type(instr_str, test_data, params, "VSOX")


@add_instruction_formatter("VSUX", vsux_config)
def format_vlux_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vsxseg_like_type(instr_str, test_data, params, "VSUX")


@add_instruction_formatter("VSOXSEG", vsoxseg_config)
def format_vloxseg_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vsxseg_like_type(instr_str, test_data, params, "VSOXSEG")


@add_instruction_formatter("VSUXSEG", vsuxseg_config)
def format_vluxseg_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vsxseg_like_type(instr_str, test_data, params, "VSUXSEG")


def format_vsxseg_like_type(
    instr_str: str,
    test_data: TestData,
    params: InstructionParams,
    instr_type: str,
) -> tuple[list[str], list[str], list[str]]:
    assert params.rs1 is not None and params.rs1val_pointer is not None, (
        f"rs1 and rs1val_pointer must be provided for {instr_type}-type instructions"
    )
    assert params.vs2 is not None and params.vs2_val_pointer is not None, (
        f"vs2 and vs2_val_pointer must be provided for {instr_type}-type instructions"
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
            (params.vs2_val_pointer, *test_data.vector_labels[params.vs2_val_pointer]),
            (params.vs3_val_pointer, *test_data.vector_labels[params.vs3_val_pointer]),
        ]
    )

    # Extract General Instruction Info
    info = parse_vector_instruction_info(instr_str, instr_type)
    index_eew = info.index_eew
    assert index_eew is not None, f"Could not extract an Index EEW from {instr_type}-type instruction {instr_str}"
    index_emul = params.lmul * index_eew / params.sew
    segments = info.segments

    setup = []

    # Setup Mask
    if params.maskval:
        setup.extend(prep_mask_v(params.maskval, test_data, params))

    reload_register = random.choice(list(test_data.vec_regs.free_registers(int(max(params.lmul, 1)), segments)))
    params.vd = reload_register
    params.vd_val_pointer = "NOT_A_LABEL"  # Placeholder value that should NOT end up in generated code
    test_data.vec_regs.allocate_operand("vd", reload_register, int(max(params.lmul, 1)) * segments)

    vd_vl = params.vl if params.vector_suite == "base" else "vlmax"
    to_load = [
        VectorLoad(reg="vs3", vl=vd_vl, no_fractional_load=True, segments=segments),
        VectorLoad(reg="vd", segments=segments, no_fractional_load=True, only_setup_tail=True),
    ]

    # Coverage workaround: It only checks for vs2_edges at SEW, not at the correct EEW, so
    # if the label is zero_emul8 or random_within_2vlmax, it needs special handling
    if params.vs2_val_pointer.startswith("vs2_edge_random_within_2vlmax_ls"):
        # FIXME: We are required load at wrong sew to make coverage happy
        to_load.append(VectorLoad(reg="vs2"))
    elif params.vs2_val_pointer.startswith("vs2_edge_zero_emul8_ls"):
        # FIXME: Coverage requires a load at vlmax here as the entire register must be zero
        to_load.append(VectorLoad(reg="vs2", lmul=max(index_emul, 1), sew=index_eew, vl="vlmax"))
    else:
        to_load.append(VectorLoad(reg="vs2", lmul=index_emul, sew=index_eew))

    load_code, random_vl_reg = load_vec_regs(to_load, params, test_data)
    setup.extend(load_code)

    if not params.ignore_vector_safety:
        # Ensure that the data in vs2 is within the range [0, 2*vlmax) and sew-aligned
        setup.extend(
            [
                "# Ensure that the data in vs2 is within the range [0, 2*vlmax) and sew-aligned",
                f"vsetvli x{params.temp_reg}, x0, e{params.sew}, m{get_lmul_flag(params.lmul)}, ta, ma",
                f"add x{params.temp_reg}, x{params.temp_reg}, x{params.temp_reg}",
            ]
        )
        if params.vs2_val_pointer == "vs2_edge_random_within_2vlmax_ls":
            # FIXME: Coverage workaround
            temp_reg2 = test_data.int_regs.get_register(exclude_regs=[0])
            setup.append(f"vsetvli x{temp_reg2}, x0, e{params.sew}, m{get_lmul_flag(params.lmul)}, tu, mu")
            test_data.int_regs.return_register(temp_reg2)
        elif params.vl == "vlmax":
            temp_reg2 = test_data.int_regs.get_register(exclude_regs=[0])
            setup.append(f"vsetvli x{temp_reg2}, x0, e{index_eew}, m{get_lmul_flag(index_emul)}, tu, mu")
            test_data.int_regs.return_register(temp_reg2)
        elif params.vl == "random":
            setup.append(f"vsetvli x0, {random_vl_reg}, e{index_eew}, m{get_lmul_flag(index_emul)}, tu, mu")
        else:
            assert isinstance(params.vl, int)
            setup.append(f"vsetivli x0, {params.vl}, e{index_eew}, m{get_lmul_flag(index_emul)}, tu, mu")
        # Construct a factor that masks off the correct bits to align load to the SEW
        sew_alignment_factor = -params.sew // 8
        setup.extend(
            [
                f"vremu.vx v{params.vs2}, v{params.vs2}, x{params.temp_reg}",
                f"vand.vi v{params.vs2}, v{params.vs2}, {sew_alignment_factor}",
            ]
        )

    setup.append(f"LA (x{params.rs1}, {params.rs1val_pointer})")
    setup.append(load_test_vtype(params, random_vl_reg))

    # We don't need random_vl_reg anymore
    if random_vl_reg.startswith("x"):
        test_data.int_regs.return_register(int(random_vl_reg[1:]))

    equivalent_load = "vl" + instr_str[2:]
    if params.maskval:
        test = [
            f"{instr_str} v{params.vs3}, (x{params.rs1}), v{params.vs2}, v0.t",
            f"{equivalent_load} v{params.vd}, (x{params.rs1}), v{params.vs2}, v0.t",
        ]
    else:
        test = [
            f"{instr_str} v{params.vs3}, (x{params.rs1}), v{params.vs2}",
            f"{equivalent_load} v{params.vd}, (x{params.rs1}), v{params.vs2}",
        ]

    # We no longer need vs2. This allows us to have enough registers for length SIGUPD where the maximum number of
    # registers (25) are required by the test section
    test_data.vec_regs.deallocate_operand("vs2")

    if params.vector_suite == "length":
        check = [*write_sigupd_v_len(test_data, params, params.lmul, segments=segments)]
    else:
        check = [*write_sigupd_v(test_data, params)]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(0)

    handle_parameter_exclusions(params.lmul, setup, check, encoded_eew=info.index_eew, index_eew=info.index_eew)

    return (setup, test, check)
