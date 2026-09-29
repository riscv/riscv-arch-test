##################################
# cfss_type.py
#
# harris@hmc.edu Dec 2025
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import FP_STORE_AREA_BYTES, check_store_canary, fill_store_canary, load_float_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

cfss_config = InstructionTypeConfig(
    required_params={"fs2", "fs2val", "immval", "temp_reg"},
    imm_bits=9,
    imm_signed=False,
)


@add_instruction_formatter("CFSS", cfss_config)
def format_cfss_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CFSS-type stack-pointer-based store instruction."""
    assert params.fs2 is not None and params.fs2val is not None, (
        "fs2 and fs2val must be provided for CFSS-type instructions"
    )
    assert params.immval is not None, "immval must be provided for CFSS-type instructions"
    assert params.temp_reg is not None, "temp_reg must be provided for CFSS-type instructions"

    # Determine alignment requirement and max value: c.sdsp needs 8-byte, c.swsp needs 4-byte
    if instr_name == "c.fsdsp":
        alignment = 8
        max_val = 504
    elif instr_name == "c.fswsp":
        alignment = 4
        max_val = 252
    else:
        raise ValueError(f"Unknown CSS instruction: {instr_name}")

    # Mask off lower bits to ensure alignment
    params.immval = params.immval & ~(alignment - 1)
    # Wrap into valid range
    params.immval = params.immval % (max_val + alignment)

    setup: list[str] = ["fsflagsi 0b00000 # clear all fflags"]
    asm = test_data.int_regs.consume_registers([2])  # sp (x2) is used as the base pointer for CSS instructions
    if asm:
        setup.append(asm)
    setup.extend(
        [
            load_float_reg("fs2", params.fs2, params.fs2val, test_data),
            *fill_store_canary(
                2,
                params.temp_reg,
                test_data,
                area_bytes=FP_STORE_AREA_BYTES,
                store_val=params.fs2val,
                store_bytes=alignment,
            ),
            f"addi sp, sp, {-params.immval}  # adjust for offset",
        ]
    )

    test = [f"{instr_name} f{params.fs2}, {params.immval}(sp) # perform store"]

    check = [
        f"addi sp, sp, {params.immval} # remove offset from sp",
        *check_store_canary(2, params.temp_reg, test_data, area_bytes=FP_STORE_AREA_BYTES),
        write_sigupd(None, test_data, "fflags"),
    ]

    # Return sp since it was allocated specially for this testcase
    test_data.int_regs.return_register(2)

    return (setup, test, check)
