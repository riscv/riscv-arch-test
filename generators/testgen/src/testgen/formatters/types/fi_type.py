##################################
# fi_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_float_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

fi_config = InstructionTypeConfig(required_params={"fd", "fs1", "fs1val"})


@add_instruction_formatter("FI", fi_config)
def format_fi_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format FI-type instruction."""
    assert params.fs1 is not None and params.fs1val is not None
    assert params.fd is not None
    frm = f", {params.frm}" if params.frm is not None else ""
    setup = [
        load_float_reg("fs1", params.fs1, params.fs1val, test_data, params.fp_load_type),
        "fsflagsi 0b00000 # clear all fflags",
    ]
    test = [
        f"{instr_name} f{params.fd}, f{params.fs1}{frm} # perform operation",
    ]
    check = [write_sigupd(params.fd, test_data, "float")]
    return (setup, test, check)
