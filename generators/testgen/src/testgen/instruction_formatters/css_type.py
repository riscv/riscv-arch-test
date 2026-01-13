##################################
# css_type.py
#
# harris@hmc.edu Oct 2025
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import InstructionTypeConfig, add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd

css_config = InstructionTypeConfig(
    required_params={"rs2", "rs2val", "immval", "temp_reg"},
    imm_bits=9,
    imm_signed=False,
)


@add_instruction_formatter("CSS", css_config)
def format_css_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CSS-type stack-pointer-based store instruction."""
    assert params.rs2 is not None and params.rs2val is not None, (
        "rs2 and rs2val must be provided for CSS-type instructions"
    )
    assert params.temp_reg is not None, "temp_reg must be provided for CSS-type instructions"
    assert params.immval is not None, "immval must be provided for CSS-type instructions"

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
            f"addi sp, x{test_data.int_regs.sig_reg}, {-params.immval}  # copy sig_reg to sp and adjust for offset",
        ]
    )

    test = [f"{instr_name} x{params.rs2}, {params.immval}(sp) # perform store"]

    check = [
        "#ifdef SELFCHECK",
        f"LREG x{params.temp_reg}, 0(x{test_data.int_regs.sig_reg}) # load stored value for checking",
        write_sigupd(params.temp_reg, test_data),
        "#else",
        f"addi sp, sp, {params.immval} # remove offset from sp",
        "addi sp, sp, SIG_STRIDE # increment signature pointer in sp",
        f"{instr_name} x{params.rs2}, 0(sp) # repeat store so it is available for checking",
        f"addi x{test_data.int_regs.sig_reg}, x{test_data.int_regs.sig_reg}, SIG_STRIDE # increment signature pointer",
        "# nops to ensure length matches SELFCHECK",
        "nop",
        "nop",
        "#endif",
    ]

    test_data.sigupd_count += 1  # Extra sigupd that doesn't use the write_sigupd helper

    if params.rs2 != 2:
        # Return sp if it was allocated specially for this testcase
        test_data.int_regs.return_register(2)

    return (setup, test, check)
