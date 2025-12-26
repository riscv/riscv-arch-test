##################################
# cs_type.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd


@add_instruction_formatter(
    "CS",
    required_params={"rs1", "rs1val", "rs2", "rs2val", "immval", "temp_reg"},
    reg_range=range(8, 16),
    imm_bits=8,
    imm_signed=False,
)
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

    # load test value
    setup = [
        load_int_reg("rs2", params.rs2, params.rs2val, test_data),
    ]

    # Move sig_reg to rs1
    if params.rs1 != test_data.int_regs.sig_reg:
        setup.append(
            test_data.int_regs.move_sig_reg(params.rs1),
        )
        params.rs1 = None

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
