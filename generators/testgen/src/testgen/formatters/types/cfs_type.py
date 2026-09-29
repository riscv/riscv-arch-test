##################################
# cfs_type.py
#
# harris@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import FP_STORE_AREA_BYTES, check_store_canary, fill_store_canary, load_float_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

cfs_config = InstructionTypeConfig(
    required_params={"rs1", "rs1val", "fs2", "fs2val", "immval", "temp_reg"},
    reg_range=range(8, 16),
    imm_bits=8,
    imm_signed=False,
)


@add_instruction_formatter("CFS", cfs_config)
def format_cfs_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CFS-type instruction."""
    assert params.rs1 is not None, "rs1 must be provided for CFS-type instructions"
    assert params.fs2 is not None and params.fs2val is not None, (
        "fs2 and fs2val must be provided for CFS-type instructions"
    )
    assert params.temp_reg is not None, "temp_reg must be provided for CFS-type instructions"
    assert params.immval is not None, "immval must be provided for CFS-type instructions"

    # Determine alignment requirement and max value: c.fsd needs 8-byte, c.fsw needs 4-byte
    if instr_name == "c.fsd":
        alignment = 8
        max_val = 248
    elif instr_name == "c.fsw":
        alignment = 4
        max_val = 124
    else:
        raise ValueError(f"Unknown CFS instruction: {instr_name}")

    # Mask off lower bits to ensure alignment
    params.immval = params.immval & ~(alignment - 1)
    # Wrap into valid range
    params.immval = params.immval % (max_val + alignment)

    setup = [
        load_float_reg("fs2", params.fs2, params.fs2val, test_data),
        "fsflagsi 0b00000 # clear all fflags",
        *fill_store_canary(
            params.rs1,
            params.temp_reg,
            test_data,
            area_bytes=FP_STORE_AREA_BYTES,
            store_val=params.fs2val,
            store_bytes=alignment,
        ),
        f"addi x{params.rs1}, x{params.rs1}, {-params.immval} # adjust base address for offset",
    ]

    test = [f"{instr_name} f{params.fs2}, {params.immval}(x{params.rs1}) # perform store"]
    check = [
        f"addi x{params.rs1}, x{params.rs1}, {params.immval} # restore base address",
        *check_store_canary(params.rs1, params.temp_reg, test_data, area_bytes=FP_STORE_AREA_BYTES),
        write_sigupd(None, test_data, "fflags"),
    ]
    return (setup, test, check)
