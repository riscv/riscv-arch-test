##################################
# csri_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.instruction_params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd
from testgen.utils.immediates import modify_imm


@add_instruction_formatter("CSRI", required_params={"rd", "rs2", "rs2val", "immval"})
def format_csri_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CSRI-type instruction."""
    assert params.rs2 is not None and params.rs2val is not None
    assert params.immval is not None
    assert params.rd is not None
    csr = "mscratch"  # Default CSR for testing
    scaled_imm = modify_imm(params.immval, 5, signed=False)
    setup = [
        load_int_reg("temp reg", params.rs2, params.rs2val, test_data),
        f"csrw {csr}, x{params.rs2} # setup CSR with random value",
    ]
    test = [
        f"{instr_name} x{params.rd}, {csr}, {scaled_imm} # perform operation",
    ]
    check = [
        write_sigupd(params.rd, test_data, "int"),
        f"csrr x{params.rs2}, {csr} # read back CSR to check updated value",
        write_sigupd(params.rs2, test_data, "int"),
    ]
    return (setup, test, check)
