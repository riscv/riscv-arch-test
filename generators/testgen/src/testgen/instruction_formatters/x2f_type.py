##################################
# x2f_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd


@add_instruction_formatter("X2F", required_params={"fd", "rs1", "rs1val"})
def format_x2f_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format X2F-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.fd is not None
    frm = f", {params.frm}" if params.frm is not None else ""
    setup = [
        load_int_reg("rs1", params.rs1, params.rs1val, test_data),
        "fsflagsi 0b00000 # clear all fflags",
    ]
    test = [
        f"{instr_name} f{params.fd}, x{params.rs1}{frm} # perform operation",
    ]
    check = [write_sigupd(params.fd, test_data, "float")]
    return (setup, test, check)
