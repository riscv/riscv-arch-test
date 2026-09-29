##################################
# cs_type.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import check_store_canary, fill_store_canary, int_store_data, load_int_reg
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

cs_config = InstructionTypeConfig(
    required_params={"rs1", "rs1val", "rs2", "rs2val", "immval", "temp_reg"},
    reg_range=range(8, 16),
    imm_bits=8,
    imm_signed=False,
)


@add_instruction_formatter("CS", cs_config)
def format_cs_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CS-type instruction."""
    assert params.rs1 is not None, "rs1 must be provided for CS-type instructions"
    assert params.rs2 is not None and params.rs2val is not None, (
        "rs2 and rs2val must be provided for CS-type instructions"
    )
    assert params.temp_reg is not None, "temp_reg must be provided for CS-type instructions"
    assert params.immval is not None, "immval must be provided for CS-type instructions"

    # Determine alignment requirement and max value: c.sd needs 8-byte, c.sw needs 4-byte
    if instr_name == "c.sd":
        alignment = 8
        max_val = 248
    elif instr_name == "c.sw":
        alignment = 4
        max_val = 124
    else:
        raise ValueError(f"Unknown CS instruction: {instr_name}")

    # Mask off lower bits to ensure alignment
    params.immval = params.immval & ~(alignment - 1)
    # Wrap into valid range
    params.immval = params.immval % (max_val + alignment)

    store_val, known_bytes = int_store_data(params.rs2, params.rs2val, params.rs1, params.immval, alignment)

    setup = [
        load_int_reg("rs2", params.rs2, params.rs2val, test_data),
        *fill_store_canary(
            params.rs1,
            params.temp_reg,
            test_data,
            area_bytes=alignment,
            store_val=store_val,
            store_bytes=known_bytes,
        ),
        f"addi x{params.rs1}, x{params.rs1}, {-params.immval} # adjust base address for offset",
    ]

    test = [f"{instr_name} x{params.rs2}, {params.immval}(x{params.rs1}) # perform store"]
    check = [
        f"addi x{params.rs1}, x{params.rs1}, {params.immval} # restore base address",
        *check_store_canary(params.rs1, params.temp_reg, test_data, area_bytes=alignment),
    ]
    return (setup, test, check)
