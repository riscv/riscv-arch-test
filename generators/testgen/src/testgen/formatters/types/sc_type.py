##################################
# sc_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

sc_config = InstructionTypeConfig(
    required_params={"rd", "rs1", "rs2", "rs2val", "temp_reg", "temp_val"}, imm_bits=12, imm_signed=True
)


@add_instruction_formatter("SC", sc_config)
def format_sc_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format SC-type instruction."""
    assert params.rs1 is not None and params.rd is not None, "rs1 and rd must be provided for SC-type instructions"
    assert params.rs2 is not None and params.rs2val is not None, (
        "rs2 and rs2val must be provided for SC-type instructions"
    )
    assert params.temp_reg is not None, "temp_reg must be provided for SC-type instructions"

    # Ensure rs1 is not x0 (base address)
    if params.rs1 == 0:
        test_data.int_regs.return_register(params.rs1)
        params.rs1 = test_data.int_regs.get_register(exclude_regs=[0])

    lr_insr = "lr.w" if instr_name.endswith(".w") else "lr.d"

    # load test value
    setup = [
        load_int_reg("rs2", params.rs2, params.rs2val, test_data),
        f"LA(x{params.rs1}, scratch) # rs1 = base address",
        f"{lr_insr} x0, (x{params.rs1}) # establish reservation",
    ]

    test = [f"{instr_name} x{params.rd}, x{params.rs2}, (x{params.rs1}) # perform operation"]
    check = [
        write_sigupd(params.rd, test_data),
        f"LA(x{params.rs1}, scratch) # reload base address",
        f"LREG x{params.temp_reg}, 0(x{params.rs1}) # load stored value",
        write_sigupd(params.temp_reg, test_data),
    ]
    return (setup, test, check)


# SC.W conditionally writes a word in rs2 to the address in rs1: the SC.W succeeds only if
# the reservation is still valid and the reservation set contains the bytes being written.
# If the SC.W succeeds, the instruction writes the word in rs2 to memory, and it writes zero to rd.
# If the SC.W fails, the instruction does not write to memory, and it writes a nonzero value to rd.

# # Testcase cmp_rd_rs1_rs2 (Test rd = rs1 = rs2 = x31)
# LI(x31, 0x3ba174cd783fd162) # initialize rs2
# LA(x31, scratch) # rs1 = base address
# sc.d x31, x31, (x31) # perform operation
# RVTEST_SIGUPD(x24, x31)
