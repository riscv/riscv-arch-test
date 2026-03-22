##################################
# csb_type.py
#
# harris@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.constants import INDENT
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

    # Move sig_reg to rs1
    setup = [
        load_int_reg("rs2", params.rs2, params.rs2val, test_data),
    ]
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
        "#ifdef RVTEST_SELFCHECK",
        f"LREG x{params.temp_reg}, -SIG_STRIDE(x{sig_reg}) # load stored value for checking",
        write_sigupd(params.temp_reg, test_data),
        "#else",
        f"{instr_name} x{params.rs2}, 0(x{sig_reg}) # repeat store so it is available for checking",
        f"addi x{sig_reg}, x{sig_reg}, SIG_STRIDE # adjust base address for offset",
        f"{INDENT}# nops to ensure length matches SELFCHECK",
        "nop",
        "nop",
        "nop",
        "#endif",
    ]
    assert test_data.testcase is not None
    test_data.testcase.sigupd_count += 1
    return (setup, test, check)
