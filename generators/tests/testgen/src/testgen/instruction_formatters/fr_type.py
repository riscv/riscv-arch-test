##################################
# fr_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import load_float_reg, write_sigupd


@add_instruction_formatter("FR", required_params={"fd", "fs1", "fs1val", "fs2", "fs2val", "frm"})
def format_fr_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format FR-type instruction."""
    assert params.fs1 is not None and params.fs1val is not None
    assert params.fs2 is not None and params.fs2val is not None
    assert params.fd is not None
    assert params.frm is not None
    setup = [
        load_float_reg("fs1", params.fs1, params.fs1val, test_data),
        load_float_reg("fs2", params.fs2, params.fs2val, test_data),
        "fsflagsi 0b00000 # clear all fflags",
    ]
    test = [
        f"{instr_name} f{params.fd}, f{params.fs1}, f{params.fs2} # perform operation",
    ]
    check = [write_sigupd(params.fd, test_data, "float")]
    return (setup, test, check)
