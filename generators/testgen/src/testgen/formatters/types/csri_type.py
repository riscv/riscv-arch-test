##################################
# csri_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

csri_config = InstructionTypeConfig(required_params={"rd", "rs2", "rs2val", "immval"}, imm_bits=5, imm_signed=False)


@add_instruction_formatter("CSRI", csri_config)
def format_csri_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CSRI-type instruction."""
    assert params.rs2 is not None and params.rs2val is not None
    assert params.immval is not None
    assert params.rd is not None
    csr = "mscratch"  # Default CSR for testing
    setup = [
        load_int_reg("temp reg", params.rs2, params.rs2val, test_data),
        f"csrw {csr}, x{params.rs2} # setup CSR with random value",
    ]
    test = [
        f"{instr_name} x{params.rd}, {csr}, {params.immval} # perform operation",
    ]
    check = [
        write_sigupd(params.rd, test_data, "int"),
        f"csrr x{params.rs2}, {csr} # read back CSR to check updated value",
        write_sigupd(params.rs2, test_data, "int"),
    ]
    return (setup, test, check)
