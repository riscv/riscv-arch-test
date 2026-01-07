##################################
# fix_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import InstructionTypeConfig, add_instruction_formatter
from testgen.utils.common import load_float_reg, write_sigupd

fix_config = InstructionTypeConfig(required_params={"rd", "fs1", "fs1val"})


@add_instruction_formatter("FIX", fix_config)
def format_fix_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format FIX-type instruction."""
    assert params.fs1 is not None and params.fs1val is not None
    assert params.rd is not None
    setup = [
        load_float_reg("fs1", params.fs1, params.fs1val, test_data, params.fp_load_type),
        "fsflagsi 0b00000 # clear all fflags",
    ]
    test = [
        f"{instr_name} x{params.rd}, f{params.fs1} # perform operation",
    ]
    check = [write_sigupd(params.rd, test_data)]
    return (setup, test, check)
