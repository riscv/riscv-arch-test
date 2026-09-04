##################################
# vlr_type.py
#
#
# rwolk@hmc.edu August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.vector_helpers import (
    VectorLoad,
    handle_parameter_exclusions,
    load_test_vtype,
    load_vec_regs,
    write_sigupd_v,
    write_sigupd_v_len,
)
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter
from testgen.instructions.vector import parse_vector_instruction_info

vlr_config = InstructionTypeConfig(
    required_params={"vd", "rs1"}, instruction_class=["load"], vector_data=VectorTypeConfig()
)


@add_instruction_formatter("VLR", vlr_config)
def format_vlr_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.rs1 is not None and params.rs1val_pointer is not None, (
        "rs1 and rs1val_pointer must be provided for VLR-type instructions"
    )
    assert params.vd is not None and params.vd_val_pointer is not None, (
        "vd and vd_val_pointer must be provided for VLR-type instructions"
    )
    assert params.temp_reg is not None, "temp_reg must be provided for VLR-type instructions"
    assert params.sew is not None, "SEW must be provided for Vector instructions"
    assert params.lmul is not None, "lmul must be provided for VLR-type instructions"
    assert test_data.test_chunk is not None, "format_vlr_type must be used with an active TestChunk"

    test_data.test_chunk.vector_labels.extend(
        [
            (params.rs1val_pointer, *test_data.vector_labels[params.rs1val_pointer]),
            (params.vd_val_pointer, *test_data.vector_labels[params.vd_val_pointer]),
        ]
    )

    # Extract General Instruction Info
    info = parse_vector_instruction_info(instr_str, "VLR")
    eew = info.load_store_eew
    assert eew is not None, f"Could not extract an EEW from VLR-type instruction {instr_str}"
    emul = info.whole_registers
    assert emul is not None, f"Could not extract a number of whole registers from VLR-type instruction {instr_str}"
    segments = info.segments

    setup = []

    # Preload vd at vlmax
    vd_vl = params.vl if params.vector_suite == "base" else "vlmax"
    to_load = [VectorLoad(reg="vd", vl=vd_vl, no_fractional_load=True, segments=segments, lmul=emul, sew=eew)]
    load_code, random_vl_reg = load_vec_regs(to_load, params, test_data)
    setup.extend(load_code)
    setup.append(f"LA (x{params.rs1}, {params.rs1val_pointer})")
    setup.append(load_test_vtype(params, random_vl_reg))

    # We don't need random_vl_reg anymore
    if random_vl_reg.startswith("x"):
        test_data.int_regs.return_register(int(random_vl_reg[1:]))

    test = [f"{instr_str} v{params.vd}, (x{params.rs1})"]

    if params.vector_suite == "length":
        check = [*write_sigupd_v_len(test_data, params, emul, segments=segments, sew_override=info.load_store_eew)]
    else:
        check = [*write_sigupd_v(test_data, params, sew_override=info.load_store_eew)]

    handle_parameter_exclusions(params.lmul, setup, check, encoded_eew=eew)

    return (setup, test, check)
