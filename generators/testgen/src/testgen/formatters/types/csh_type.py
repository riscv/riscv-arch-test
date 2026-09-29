##################################
# csh_type.py
#
# harris@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import check_store_canary, fill_store_canary, int_store_data, load_int_reg
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

csh_config = InstructionTypeConfig(
    required_params={"rs1", "rs1val", "rs2", "rs2val", "immval", "temp_reg"},
    reg_range=range(8, 16),
    imm_bits=2,
    imm_signed=False,
)


@add_instruction_formatter("CSH", csh_config)
def format_csh_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CSH-type instruction."""
    assert params.rs1 is not None, "rs1 must be provided for CSH-type instructions"
    assert params.rs2 is not None and params.rs2val is not None, (
        "rs2 and rs2val must be provided for CSH-type instructions"
    )
    assert params.temp_reg is not None, "temp_reg must be provided for CSH-type instructions"
    assert params.immval is not None, "immval must be provided for CSH-type instructions"

    # Mask off bottom bit to ensure alignment
    params.immval &= ~1

    store_val, known_bytes = int_store_data(params.rs2, params.rs2val, params.rs1, params.immval, 2)

    setup = [
        load_int_reg("rs2", params.rs2, params.rs2val, test_data),
        *fill_store_canary(
            params.rs1,
            params.temp_reg,
            test_data,
            area_bytes=2,
            store_val=store_val,
            store_bytes=known_bytes,
        ),
        f"addi x{params.rs1}, x{params.rs1}, {-params.immval} # adjust base address for offset",
    ]

    test = [f"{instr_name} x{params.rs2}, {params.immval}(x{params.rs1}) # perform store"]
    check = [
        f"addi x{params.rs1}, x{params.rs1}, {params.immval} # restore base address",
        *check_store_canary(params.rs1, params.temp_reg, test_data, area_bytes=2),
    ]
    return (setup, test, check)
