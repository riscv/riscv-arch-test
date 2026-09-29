##################################
# cp_fp_NaNBox.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point NaN-Box value coverpoint generator (cp_NaNBox)."""

from testgen.asm.helpers import load_float_reg
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_instruction
from testgen.instructions.params import generate_random_params

# Improperly boxed value preloaded into fd, so the operation must write all 1s to its upper bits
FD_PRELOAD = 0x0123456789ABCDEF


@add_coverpoint_generator("cp_NaNBox")
def make_NaNBox(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate test for NaN-Box values."""
    if coverpoint.endswith("_D_S"):
        load_size, fd_load_size, fd_bits = "single", "double", 64
    elif coverpoint.endswith("D_H"):
        load_size, fd_load_size, fd_bits = "half", "double", 64
    elif coverpoint.endswith("S_H"):
        load_size, fd_load_size, fd_bits = "half", "single", 32
    else:
        raise ValueError(f"Unsupported coverpoint for NaN-Box test: {coverpoint} for instr {instr_name}.")

    params = generate_random_params(test_data, instr_type, exclude_regs=[0], fp_load_type=load_size)

    tc = test_data.begin_test_chunk()
    tc.code.append(f"# Testcase {coverpoint} (Test NaN-Boxed inputs)")
    label = test_data.add_testcase("NaNBox", coverpoint)
    # Preload fd with an improperly boxed value unless fd is also a source, so a result
    # that leaves the upper bits of fd unwritten is caught by the full-width signature check.
    if params.fd is not None and params.fd not in (params.fs1, params.fs2, params.fs3):
        fd_val = FD_PRELOAD & ((1 << fd_bits) - 1)
        tc.code.append(load_float_reg("fd (improperly boxed)", params.fd, fd_val, test_data, fd_load_size))
    setup, test, check = format_instruction(instr_name, instr_type, test_data, params)
    if setup:
        tc.code.append(setup)
    tc.code.extend([label, test])
    if check:
        tc.code.append(check)

    test_chunk = test_data.end_test_chunk()
    return_testcase_registers(test_data, params)
    return [test_chunk]
