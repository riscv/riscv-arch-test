##################################
# cfss_type.py
#
# harris@hmc.edu Dec 2025
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import InstructionTypeConfig, add_instruction_formatter
from testgen.utils.common import load_float_reg, write_sigupd

cfss_config = InstructionTypeConfig(
    required_params={"fs2", "fs2val", "immval", "temp_reg", "temp_freg"},
    imm_bits=9,
    imm_signed=False,
)


@add_instruction_formatter("CFSS", cfss_config)
def format_cfss_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CFSS-type stack-pointer-based store instruction."""
    assert params.fs2 is not None and params.fs2val is not None, (
        "fs2 and fs2val must be provided for CFSS-type instructions"
    )
    assert params.immval is not None, "immval must be provided for CFSS-type instructions"
    assert params.temp_reg is not None and params.temp_freg is not None, (
        "temp_reg and temp_freg must be provided for CFSS-type instructions"
    )

    # Determine alignment requirement and max value: c.sdsp needs 8-byte, c.swsp needs 4-byte
    if instr_name == "c.fsdsp":
        alignment = 8
        max_val = 504
    elif instr_name == "c.fswsp":
        alignment = 4
        max_val = 252
    else:
        raise ValueError(f"Unknown CSS instruction: {instr_name}")

    # Mask off lower bits to ensure alignment
    params.immval = params.immval & ~(alignment - 1)
    # Wrap into valid range
    params.immval = params.immval % (max_val + alignment)

    setup = [
        test_data.int_regs.consume_registers([2]),  # sp (x2) is used as the base pointer for CSS instructions
        load_float_reg("fs2", params.fs2, params.fs2val, test_data),
        "LA(sp, scratch) # set sp to scratch space",
        f"addi sp, sp, {-params.immval}  # adjust for offset",
    ]

    test = [f"{instr_name} f{params.fs2}, {params.immval}(sp) # perform store"]

    check = [
        f"addi sp, sp, {params.immval} # remove offset from sp",
        f"FLREG f{params.temp_freg}, 0(sp) # load stored value for checking",
        write_sigupd(params.temp_freg, test_data, sig_type="float"),
    ]

    # Return sp since it was allocated specially for this testcase
    test_data.int_regs.return_register(2)

    return (setup, test, check)
