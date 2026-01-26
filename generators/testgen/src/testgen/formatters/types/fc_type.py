##################################
# fc_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_float_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

fc_config = InstructionTypeConfig(required_params={"rd", "fs1", "fs1val", "fs2", "fs2val"})


@add_instruction_formatter("FC", fc_config)
def format_fc_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format FC-type instruction."""
    assert params.fs1 is not None and params.fs1val is not None
    assert params.fs2 is not None and params.fs2val is not None
    assert params.rd is not None
    setup = [
        load_float_reg("fs1", params.fs1, params.fs1val, test_data, params.fp_load_type),
        load_float_reg("fs2", params.fs2, params.fs2val, test_data, params.fp_load_type),
        "fsflagsi 0b00000 # clear all fflags",
    ]
    test = [
        f"{instr_name} x{params.rd}, f{params.fs1}, f{params.fs2} # perform operation",
    ]
    check = [write_sigupd(params.rd, test_data)]
    return (setup, test, check)
