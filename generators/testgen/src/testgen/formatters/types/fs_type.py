##################################
# fs_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import (
    STORE_BYTES,
    check_store_canary,
    fp_store_area_bytes,
    fp_store_canary,
    load_float_reg,
    write_sigupd,
)
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

fs_config = InstructionTypeConfig(
    required_params={"temp_reg", "rs1", "rs1val", "fs2", "fs2val", "immval"}, imm_bits=12, imm_signed=True
)


@add_instruction_formatter("FS", fs_config)
def format_fs_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format FS-type instruction."""
    assert params.rs1 is not None, "rs1 must be provided for FS-type instructions"
    assert params.fs2 is not None and params.fs2val is not None, (
        "fs2 and fs2val must be provided for FS-type instructions"
    )
    assert params.temp_reg is not None, "temp_reg must be provided for FS-type instructions"
    assert params.immval is not None, "immval must be provided for FS-type instructions"

    store_bytes = STORE_BYTES[instr_name]
    area_bytes = fp_store_area_bytes(store_bytes, test_data)

    # Ensure rs1 is not x0 (base address)
    if params.rs1 == 0:
        test_data.int_regs.return_register(params.rs1)
        params.rs1 = test_data.int_regs.get_register(exclude_regs=[0])

    # load test value and fill the store target at scratch with a canary
    setup = [
        load_float_reg("fs2", params.fs2, params.fs2val, test_data, params.fp_load_type),
        "fsflagsi 0b00000 # clear all fflags",
        f"LA(x{params.rs1}, scratch) # point base at scratch",
        *fp_store_canary(
            params.rs1,
            params.temp_reg,
            test_data,
            area_bytes=area_bytes,
            store_val=params.fs2val,
            store_bytes=store_bytes,
        ),
    ]

    # Handle special case where offset is -2048
    if params.immval == -2048:
        setup.extend(
            [
                f"addi x{params.rs1}, x{params.rs1}, 2047 # increment by 2047",
                f"addi x{params.rs1}, x{params.rs1}, 1 # increment by 1 more for total +2048",
            ]
        )
    else:
        setup.append(f"addi x{params.rs1}, x{params.rs1}, {-params.immval} # adjust base address for offset")

    test = [f"{instr_name} f{params.fs2}, {params.immval}(x{params.rs1}) # perform store"]
    check = [
        f"addi x{params.rs1}, x{params.rs1}, {params.immval} # restore base address",
        *check_store_canary(params.rs1, params.temp_reg, test_data, area_bytes=area_bytes),
        write_sigupd(None, test_data, "fflags"),
    ]
    return (setup, test, check)
