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

    # Check if this instruction uses pair registers, which requires additional setup and checking of upper halves of registers and memory
    is_pair = getattr(params, "rd_is_pair", False)

    # Apply mask to ensure values fit within xlen, and calculate offset for upper half of memory for pair registers
    mask = (1 << test_data.xlen) - 1
    offset = test_data.xlen // 8

    setup = [
        load_int_reg("value in memory", params.temp_reg, params.rs1val & mask, test_data),
        load_int_reg("rs2", params.rs2, params.rs2val & mask, test_data),
        load_int_reg("rd compare value", params.rd, params.rdval & mask, test_data),
        f"LA(x{params.rs1}, scratch) # load base address into rs1",
        f"SREG x{params.temp_reg}, 0(x{params.rs1}) # store lower value into memory",
    ]

    # For pair registers, setup upper halves and write upper half to memory
    if is_pair:
        setup.extend(
            [
                load_int_reg("rs2 upper", params.rs2 + 1, params.rs2val >> test_data.xlen, test_data),
                load_int_reg("rd compare value upper", params.rd + 1, params.rdval >> test_data.xlen, test_data),
                # Reuse temp_reg safely to init the upper half of memory
                load_int_reg("value in memory upper", params.temp_reg, params.rs1val >> test_data.xlen, test_data),
                f"SREG x{params.temp_reg}, {offset}(x{params.rs1}) # store upper value into memory",
            ]
        )
    test = [
        f"{instr_name} x{params.rd}, x{params.rs2}, (x{params.rs1}) # perform operation",
    ]
    check = [
        write_sigupd(params.rd, test_data, "int"),
    ]

    # For pair registers, check the upper half of the destination register to ensure the instruction correctly updated both halves
    if is_pair:
        check.append(write_sigupd(params.rd + 1, test_data, "int"))

    check.extend(
        [
            f"LA(x{params.rs1}, scratch) # reload base address into rs1" if params.rs1 == params.rd else "",
            f"LREG x{params.rs1}, 0(x{params.rs1}) # Load the updated lower memory value",
            write_sigupd(params.rs1, test_data, "int"),
        ]
    )

    # Load and check the upper half of memory for pair registers to ensure the instruction correctly updated both halves
    if is_pair:
        check.extend(
            [
                f"LA(x{params.rs1}, scratch) # reload base address",
                f"LREG x{params.rs1}, {offset}(x{params.rs1}) # Load the updated upper memory value",
                write_sigupd(params.rs1, test_data, "int"),
            ]
        )

    return (setup, test, check)
