##################################
# cp_fp_NaNBox.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point NaN-Box value coverpoint generator (cp_NaNBox)."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.params import generate_random_params


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
    if params.fd is None or params.fd in (params.fs1, params.fs2, params.fs3):
        raise ValueError(f"cp_NaNBox needs an fd that is not also a source: {instr_name} ({instr_type}).")

    # Preload fd with an improperly boxed value, so a result that leaves the upper bits of fd
    # unwritten is caught by the full-width signature check.
    fd_preload = (0x0123456789ABCDEF & ((1 << fd_bits) - 1), fd_load_size)
    test_chunk = format_single_testcase(
        instr_name,
        instr_type,
        test_data,
        params,
        f"{coverpoint} (Test NaN-Boxed inputs)",
        "NaNBox",
        coverpoint,
        fd_preload=fd_preload,
    )
    return_testcase_registers(test_data, params)
    return [test_chunk]
