##################################
# xl_type.py
#
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_int_reg, to_hex, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

xl_config = InstructionTypeConfig(
    required_params={"rd", "rs1", "rs1val", "rs2", "temp_reg", "temp_val"},
    instruction_class=["load", "indexed"],
)

# mnemonic: (funct7, funct3, index scale, zero-extend index from 32 bits)
_ZILX_ENCODINGS = {
    "lxh": (0x48, 0b001, 0, False),
    "lxw": (0x48, 0b010, 0, False),
    "lxd": (0x48, 0b011, 0, False),
    "lxhu": (0x48, 0b101, 0, False),
    "lxwu": (0x48, 0b110, 0, False),
    "lxsb": (0x68, 0b000, 0, False),
    "lxsh": (0x68, 0b001, 1, False),
    "lxsw": (0x68, 0b010, 2, False),
    "lxsd": (0x68, 0b011, 3, False),
    "lxsbu": (0x68, 0b100, 0, False),
    "lxshu": (0x68, 0b101, 1, False),
    "lxswu": (0x68, 0b110, 2, False),
    "lxsuwb": (0x78, 0b000, 0, True),
    "lxsuwh": (0x78, 0b001, 1, True),
    "lxsuww": (0x78, 0b010, 2, True),
    "lxsuwd": (0x78, 0b011, 3, True),
    "lxsuwbu": (0x78, 0b100, 0, True),
    "lxsuwhu": (0x78, 0b101, 1, True),
    "lxsuwwu": (0x78, 0b110, 2, True),
}


@add_instruction_formatter("XL", xl_config)
def format_xl_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format a Zilx indexed-load instruction."""
    assert params.rd is not None
    assert params.rs1 is not None and params.rs1val is not None
    assert params.rs2 is not None
    assert params.temp_reg is not None and params.temp_val is not None
    assert test_data.test_chunk is not None

    funct7, funct3, scale, unsigned_word_index = _ZILX_ENCODINGS[instr_name]
    setup: list[str] = []
    alignment = params.immval or 0

    if params.rs2 == 0:
        test_data.int_regs.return_register(params.rs2)
        params.rs2 = test_data.int_regs.get_register(exclude_regs=[0, params.rs1])

    assert params.rs1 != params.rs2, "Zilx source registers must be distinct in generated tests"

    if params.rs1 != 0:
        setup.append(load_int_reg("index", params.rs1, params.rs1val, test_data))

    # load_int_reg advances the data pointer, so append the indexed-load value
    # after the index value. The data pointer now identifies the target address.
    test_data.test_chunk.data_values.append(params.temp_val)
    if alignment:
        test_data.test_chunk.data_values.append(params.temp_val)
    setup.append(
        f"addi x{params.rs2}, x{test_data.int_regs.data_reg}, {alignment} # copy target address into base"
    )

    if params.rs1 != 0:
        if unsigned_word_index:
            setup.extend(
                [
                    f"slli x{params.temp_reg}, x{params.rs1}, 32 # discard the upper 32 index bits",
                    f"srli x{params.temp_reg}, x{params.temp_reg}, 32 # zero-extend the 32-bit index",
                ]
            )
        else:
            setup.append(f"addi x{params.temp_reg}, x{params.rs1}, 0 # copy the index")

        if scale:
            setup.append(f"slli x{params.temp_reg}, x{params.temp_reg}, {scale} # scale the index")
        setup.append(
            f"sub x{params.rs2}, x{params.rs2}, x{params.temp_reg} # choose base so base + index selects test data"
        )

    canonical_syntax = f"{instr_name} x{params.rd}, (x{params.rs2}), x{params.rs1}"
    test = [
        (
            f".insn r 0x2f, {funct3}, {funct7}, x{params.rd}, x{params.rs1}, x{params.rs2}"
            f" # {canonical_syntax}; load {to_hex(params.temp_val, test_data.xlen)}"
        ),
    ]
    check = [
        write_sigupd(params.rd, test_data, "int"),
        (
            f"addi x{test_data.int_regs.data_reg}, x{test_data.int_regs.data_reg}, "
            f"{2 if alignment else 1}*SIG_STRIDE # increment data_ptr"
        ),
    ]
    return (setup, test, check)
