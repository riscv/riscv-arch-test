##################################
# fl_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import to_hex, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

fl_config = InstructionTypeConfig(
    required_params={"fd", "rs1", "temp_fval", "immval", "temp_reg"}, imm_bits=12, imm_signed=True
)


@add_instruction_formatter("FL", fl_config)
def format_fl_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format FL-type instruction."""
    assert params.rs1 is not None, "rs1 must be provided for FL-type instruction"
    assert params.fd is not None, "fd must be provided for FL-type instruction"
    assert params.immval is not None and params.temp_fval is not None, (
        "immval and temp_fval must be provided for FL-type instruction"
    )

    # Add value to load data region
    test_data.add_test_data_value(params.temp_fval)

    # Ensure rs1 is not x0 (base address)
    if params.rs1 == 0:
        test_data.int_regs.return_register(params.rs1)
        params.rs1 = test_data.int_regs.get_register(exclude_regs=[0])

    setup: list[str] = []

    # Handle special case where offset is -2048 (can't represent +2048 in 12 bits)
    if params.immval == -2048:
        setup.extend(
            [
                f"addi x{params.rs1}, x{test_data.int_regs.data_reg}, 2047 # copy data_ptr to rs1 and increment by 2047",
                f"addi x{params.rs1}, x{params.rs1}, 1    # increment by 1 more for total +2048 offset",
            ]
        )
    else:
        setup.append(
            f"addi x{params.rs1}, x{test_data.int_regs.data_reg}, {-params.immval} # copy data_ptr to rs1 and adjust for offset"
        )

    test = [
        f"{instr_name} f{params.fd}, {params.immval}(x{params.rs1}) # perform load ({to_hex(params.temp_fval, test_data.flen)})",
    ]
    check = [
        write_sigupd(params.fd, test_data, "float"),
        f"addi x{test_data.int_regs.data_reg}, x{test_data.int_regs.data_reg}, SIG_STRIDE # increment data_ptr",
    ]
    return (setup, test, check)
