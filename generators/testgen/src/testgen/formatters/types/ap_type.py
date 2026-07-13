##################################
# ap_type.py
#
# jcarlin@hmc.edu Feb 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

ap_config = InstructionTypeConfig(
    required_params={"rd", "rdval", "rs1", "rs1val", "rs2", "rs2val", "temp_reg"}, pair_regs={"rs2", "rd"}
)


@add_instruction_formatter("AP", ap_config)
def format_ap_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format AP-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.rs2 is not None and params.rs2val is not None
    assert params.rd is not None and params.rdval is not None
    assert params.temp_reg is not None

    # Ensure rs1 is not x0 (base address)
    if params.rs1 == 0:
        test_data.int_regs.return_register(params.rs1)
        params.rs1 = test_data.int_regs.get_register(exclude_regs=[0])

    # Values in params may be wider than XLEN for pair instructions
    # Extract lower and upper halves explicitly to ensure correct values are loaded into registers and memory
    mask = (1 << test_data.xlen) - 1
    offset = test_data.xlen // 8  # offset in bytes to access the upper half of memory for pair registers

    setup = [
        # Lower halves of register values and memory value for pair registers
        load_int_reg("value in memory", params.temp_reg, params.rs1val & mask, test_data),
        load_int_reg("rs2", params.rs2, params.rs2val & mask, test_data),
        load_int_reg("rd compare value", params.rd, params.rdval & mask, test_data),
        # Base address
        f"LA(x{params.rs1}, scratch)",  # load base address into rs1
        f"SREG x{params.temp_reg}, 0(x{params.rs1})",  # store lower value into memory
        # Upper halves of register values and memory value for pair registers
        load_int_reg("rs2 upper", params.rs2 + 1, params.rs2val >> test_data.xlen, test_data),
        load_int_reg("rd compare value upper", params.rd + 1, params.rdval >> test_data.xlen, test_data),
        load_int_reg("value in memory upper", params.temp_reg, params.rs1val >> test_data.xlen, test_data),
        f"SREG x{params.temp_reg}, {offset}(x{params.rs1})",  # store upper value into memory
    ]

    test = [
        f"{instr_name} x{params.rd}, x{params.rs2}, (x{params.rs1})",  # perform operation
    ]

    check = [
        # Check the destination register to ensure the instruction correctly updated the value from memory
        write_sigupd(params.rd, test_data, "int"),
        write_sigupd(params.rd + 1, test_data, "int"),
        f"LA(x{params.rs1}, scratch)",  # Load base address into rs1 again to check memory values
        # Check lower memory value
        f"LREG x{params.temp_reg}, 0(x{params.rs1})",
        write_sigupd(params.temp_reg, test_data, "int"),
        # Check upper memory value
        f"LREG x{params.temp_reg}, {offset}(x{params.rs1})",
        write_sigupd(params.temp_reg, test_data, "int"),
    ]

    return (setup, test, check)
