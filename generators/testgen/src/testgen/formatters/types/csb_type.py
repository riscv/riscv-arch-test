##################################
# csb_type.py
#
# harris@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import check_store_target, fill_store_target, load_int_reg
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

csb_config = InstructionTypeConfig(
    required_params={"rs1", "rs1val", "rs2", "rs2val", "immval", "temp_reg"},
    reg_range=range(8, 16),
    imm_bits=2,
    imm_signed=False,
)


@add_instruction_formatter("CSB", csb_config)
def format_csb_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CSB-type instruction."""
    assert params.rs1 is not None, "rs1 must be provided for CSB-type instructions"
    assert params.rs2 is not None and params.rs2val is not None, (
        "rs2 and rs2val must be provided for CSB-type instructions"
    )
    assert params.temp_reg is not None, "temp_reg must be provided for CSB-type instructions"
    assert params.immval is not None, "immval must be provided for CSB-type instructions"

    # rs1 points at the store target itself, so uimm selects the byte within it. The store lands at
    # offset uimm of the checked area, and a misdecoded offset writes a different byte of it.
    area_bytes = params.immval + 1
    setup = [
        load_int_reg("rs2", params.rs2, params.rs2val, test_data),
        f"LA(x{params.rs1}, scratch) # point base at scratch",
        *fill_store_target(params.rs1, params.temp_reg, test_data, area_bytes=area_bytes),
    ]

    test = [f"{instr_name} x{params.rs2}, {params.immval}(x{params.rs1}) # perform store"]
    check = [
        *check_store_target(params.rs1, params.temp_reg, test_data, area_bytes=area_bytes),
    ]
    return (setup, test, check)
