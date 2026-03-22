##################################
# fs_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_float_reg, write_sigupd
from testgen.constants import INDENT
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

fs_config = InstructionTypeConfig(
    required_params={"temp_reg", "rs1", "rs1val", "fs2", "fs2val", "immval"}, imm_bits=12, imm_signed=True
)


@add_instruction_formatter("FS", fs_config)
def format_fs_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format FS-type instruction."""
    assert params.rs1 is not None, "rs1 must be provided for FS-type instructions"
    assert params.fs2 is not None and params.fs2val is not None, (
        "fs2 and fs2val must be provided for FS-type instructions"
    )
    assert params.temp_reg is not None, "temp_reg must be provided for FS-type instructions"
    assert params.immval is not None, "immval must be provided for FS-type instructions"

    # Ensure rs1 is not x0 (base address)
    if params.rs1 == 0:
        test_data.int_regs.return_register(params.rs1)
        params.rs1 = test_data.int_regs.get_register(exclude_regs=[0])

    # load test value
    setup = [
        load_float_reg("fs2", params.fs2, params.fs2val, test_data, params.fp_load_type),
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

    test = [f"{instr_name} f{params.fs2}, {params.immval}(x{sig_reg}) # perform store"]
    check = [
        f"addi x{sig_reg}, x{sig_reg}, {params.immval} # restore base address",
        f"addi x{sig_reg}, x{sig_reg}, SIG_STRIDE # increment signature pointer",
        "#ifdef RVTEST_SELFCHECK",
        f"LREG x{params.temp_reg}, -SIG_STRIDE(x{sig_reg}) # load stored value for checking",
        write_sigupd(params.temp_reg, test_data),
        "#else",
        f"{instr_name} f{params.fs2}, 0(x{sig_reg}) # repeat store so it is available for checking",
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
