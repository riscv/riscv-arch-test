##################################
# s_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd


@add_instruction_formatter(
    "S", required_params={"temp_reg", "rs1", "rs1val", "rs2", "rs2val", "immval"}, imm_bits=12, imm_signed=True
)
def format_s_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format S-type instruction."""
    assert params.rs1 is not None, "rs1 must be provided for S-type instructions"
    assert params.rs2 is not None and params.rs2val is not None, (
        "rs2 and rs2val must be provided for S-type instructions"
    )
    assert params.temp_reg is not None, "temp_reg must be provided for S-type instructions"
    assert params.immval is not None, "immval must be provided for S-type instructions"

    # Ensure rs1 is not x0 (base address)
    if params.rs1 == 0:
        test_data.int_regs.return_register(params.rs1)
        params.rs1 = test_data.int_regs.get_register(exclude_regs=[0])

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

    # Handle special case where offset is -2048
    if params.immval == -2048:
        setup.extend(
            [
                f"addi x{sig_reg}, x{sig_reg}, 2047 # increment by 2047",
                f"addi x{sig_reg}, x{sig_reg}, 1 # increment by 1 more for total +2048",
            ]
        )
    else:
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
