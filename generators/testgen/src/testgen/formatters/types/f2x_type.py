##################################
# f2x_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_float_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

f2x_config = InstructionTypeConfig(required_params={"rd", "fs1", "fs1val"})


@add_instruction_formatter("F2X", f2x_config)
def format_f2x_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format F2X-type instruction."""
    assert params.fs1 is not None and params.fs1val is not None
    assert params.rd is not None

    # fcvtmod.w.d requires rounding mode to be rtz
    if instr_name == "fcvtmod.w.d":
        params.frm = "rtz"

    frm = f", {params.frm}" if params.frm is not None else ""

    setup = [
        load_float_reg("fs1", params.fs1, params.fs1val, test_data, params.fp_load_type),
        "fsflagsi 0b00000 # clear all fflags",
    ]
    test = [
        f"{instr_name} x{params.rd}, f{params.fs1}{frm} # perform operation",
    ]
    check = [write_sigupd(params.rd, test_data)]
    return (setup, test, check)
