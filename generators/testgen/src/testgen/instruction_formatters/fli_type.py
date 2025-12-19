##################################
# fli_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import add_instruction_formatter
from testgen.utils.common import write_sigupd

fli_vals = (
    -1.0,
    "min",
    "0x1p-16",
    "0x1p-15",
    "0x1p-8",
    "0x1p-7",
    0.0625,
    0.125,
    0.25,
    0.3125,
    0.375,
    0.4375,
    0.5,
    0.625,
    0.75,
    0.875,
    1.0,
    1.25,
    1.5,
    1.75,
    2.0,
    2.5,
    3.0,
    4.0,
    8.0,
    16.0,
    128.0,
    256.0,
    "0x1p15",
    "0x1p16",
    "inf",
    "nan",
)


@add_instruction_formatter("FLI", required_params={"fd", "rs1"})
def format_fli_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format FLI-type instruction."""
    assert params.fd is not None and params.rs1 is not None
    fli_val = fli_vals[params.rs1]
    setup = [
        "fsflagsi 0b00000 # clear all fflags",
    ]
    test = [
        f"{instr_name} f{params.fd}, {fli_val} # perform operation",
    ]
    check = [write_sigupd(params.fd, test_data, "float")]
    return (setup, test, check)
