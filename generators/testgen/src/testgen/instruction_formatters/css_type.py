##################################
# css_type.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd


@add_instruction_formatter("CSS", required_params={"rs2", "rs2val", "immval", "temp_reg"}, imm_bits=9, imm_signed=False)
def format_css_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CSS-type stack-pointer-based store instruction."""
    assert params.rs2 is not None and params.rs2val is not None, (
        "rs2 and rs2val must be provided for CSS-type instructions"
    )
    assert params.temp_reg is not None, "temp_reg must be provided for CSS-type instructions"
    assert params.immval is not None, "immval must be provided for CSS-type instructions"

    return (["#TODO: CSS tests are still a work in progress"], [], [])
    # TODO: Fix CSS trapping bug and re-enable these tests

    # Determine alignment requirement and max value: c.sdsp needs 8-byte, c.swsp needs 4-byte
    if instr_name == "c.sdsp":
        alignment = 8
        max_val = 504
    elif instr_name == "c.swsp":
        alignment = 4
        max_val = 252
    else:
        raise ValueError(f"Unknown CSS instruction: {instr_name}")

    # Mask off lower bits to ensure alignment
    params.immval = params.immval & ~(alignment - 1)
    # Wrap into valid range
    params.immval = params.immval % (max_val + alignment)

    setup: list[str] = []
    # sp (x2) is used as the base pointer for CSS instructions
    # Ensure sp is allocated
    if params.rs2 != 2:
        setup.append(test_data.int_regs.consume_registers([2]))

    setup.extend(
        [
            load_int_reg("rs2", params.rs2, params.rs2val, test_data),
            test_data.int_regs.move_sig_reg(2),  # Move sig_reg to sp
        ]
    )

    sig_reg = test_data.int_regs.sig_reg

    setup.append(f"addi x{sig_reg}, x{sig_reg}, {-params.immval} # adjust base address for offset")

    test = [f"{instr_name} x{params.rs2}, {params.immval}(x{sig_reg}) # perform store"]
    check = [
        f"addi x{sig_reg}, x{sig_reg}, {params.immval} # restore base address",
        f"addi x{sig_reg}, x{sig_reg}, SIG_STRIDE # increment signature pointer",
        "#ifdef SELFCHECK",
        f"LREG x{params.temp_reg}, -SIG_STRIDE(x{sig_reg}) # load stored value for checking",
        write_sigupd(params.temp_reg, test_data),
        "#else",
        f"{instr_name} x{params.rs2}, 0(x{sig_reg}) # repeat store so it is available for checking",
        f"addi x{sig_reg}, x{sig_reg}, SIG_STRIDE # adjust base address for offset",
        "# nops to ensure length matches SELFCHECK",
        "nop",
        "nop",
        "nop",
        "#endif",
    ]
    test_data.sigupd_count += 1
    return (setup, test, check)
