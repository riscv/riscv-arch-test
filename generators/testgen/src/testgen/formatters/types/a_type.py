##################################
# a_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

a_config = InstructionTypeConfig(required_params={"rd", "rs1", "rs1val", "rs2", "rs2val", "temp_reg"})


@add_instruction_formatter("A", a_config)
def format_a_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format A-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.rs2 is not None and params.rs2val is not None
    assert params.rd is not None and params.temp_reg is not None

    # Ensure rs1 is not x0 (base address)
    if params.rs1 == 0:
        test_data.int_regs.return_register(params.rs1)
        params.rs1 = test_data.int_regs.get_register(exclude_regs=[0])

    setup = [
        load_int_reg("value in memory", params.temp_reg, params.rs1val, test_data),
        load_int_reg("rs2", params.rs2, params.rs2val, test_data),
        f"LA(x{params.rs1}, scratch) # load base address into rs1",
        f"SREG x{params.temp_reg}, 0(x{params.rs1}) # store value into memory at address in rs1",
    ]
    test = [
        f"{instr_name} x{params.rd}, x{params.rs2}, (x{params.rs1}) # perform operation",
    ]
    check = [write_sigupd(params.rd, test_data, "int")]
    if params.rs1 == params.rd:
        check.append(f"LA(x{params.rs1}, scratch) # reload base address into rs1")
    check.extend(
        [
            f"LREG x{params.rs1}, 0(x{params.rs1}) # Load the updated value from memory",
            write_sigupd(params.rs1, test_data, "int"),
        ]
    )
    return (setup, test, check)
