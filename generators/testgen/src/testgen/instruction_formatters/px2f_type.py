##################################
# px2f_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import InstructionTypeConfig, add_instruction_formatter
from testgen.utils.common import load_int_reg, write_sigupd

px2f_config = InstructionTypeConfig(required_params={"fd", "rs1", "rs1val", "rs2", "rs2val"})


@add_instruction_formatter("PX2F", px2f_config)
def format_px2f_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format PX2F-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.rs2 is not None and params.rs2val is not None
    assert params.fd is not None

    setup = [
        load_int_reg("rs1", params.rs1, params.rs1val, test_data),
        load_int_reg("rs2", params.rs2, params.rs2val, test_data),
        "fsflagsi 0b00000 # clear all fflags",
    ]
    test = [
        f"{instr_name} f{params.fd}, x{params.rs1}, x{params.rs2} # perform operation",
    ]
    check = [write_sigupd(params.fd, test_data, "float")]
    return (setup, test, check)
