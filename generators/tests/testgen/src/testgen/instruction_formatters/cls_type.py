##################################
# cls_type.py
#
# jcarlin@hmc.edu Nov 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd


@add_instruction_formatter(
    "CLS", required_params={"rd", "rs1", "immval", "temp_reg", "temp_val"}, imm_bits=6, imm_signed=True
)
def format_cls_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CLS-type instruction."""
    assert params.rs1 is not None
    assert params.temp_reg is not None and params.temp_val is not None
    assert params.rd is not None and params.immval is not None
    # rs1 must be x2 (sp)
    test_data.int_regs.return_register(params.rs1)
    params.rs1 = 2
    setup = [
        "" if params.rd == 2 else test_data.int_regs.consume_registers([params.rs1]),  # ensure sp is reserved
        load_int_reg("value to load", params.temp_reg, params.temp_val, test_data),
        f"LA(x{params.rs1}, scratch) # base address",
        f"addi x{params.rs1}, x{params.rs1}, {-params.immval} # adjust base address for load",
        f"SREG x{params.temp_reg}, {params.immval}(x{params.rs1}) # store value to load",
    ]
    test = [
        f"{instr_name} x{params.rd}, {params.immval}(x{params.rs1}) # perform operation",
    ]
    check = [write_sigupd(params.rd, test_data, "int")]
    return (setup, test, check)
