##################################
# x2f_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

x2f_config = InstructionTypeConfig(required_params={"fd", "rs1", "rs1val"})


@add_instruction_formatter("X2F", x2f_config)
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
