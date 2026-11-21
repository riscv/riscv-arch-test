# SPDX-License-Identifier: Apache-2.0

"""Indexed-load access sizes and index transformations."""

from typing import NamedTuple


class IndexedLoad(NamedTuple):
    size: int
    scale: int
    unsigned_word: bool = False
    rv64_only: bool = False


ZILX_INSTRUCTIONS = {
    "lxh": IndexedLoad(2, 0),
    "lxw": IndexedLoad(4, 0),
    "lxd": IndexedLoad(8, 0, rv64_only=True),
    "lxhu": IndexedLoad(2, 0),
    "lxwu": IndexedLoad(4, 0, rv64_only=True),
    "lxsb": IndexedLoad(1, 0),
    "lxsh": IndexedLoad(2, 1),
    "lxsw": IndexedLoad(4, 2),
    "lxsd": IndexedLoad(8, 3, rv64_only=True),
    "lxsbu": IndexedLoad(1, 0),
    "lxshu": IndexedLoad(2, 1),
    "lxswu": IndexedLoad(4, 2, rv64_only=True),
    "lxsuwb": IndexedLoad(1, 0, True, True),
    "lxsuwh": IndexedLoad(2, 1, True, True),
    "lxsuww": IndexedLoad(4, 2, True, True),
    "lxsuwd": IndexedLoad(8, 3, True, True),
    "lxsuwbu": IndexedLoad(1, 0, True, True),
    "lxsuwhu": IndexedLoad(2, 1, True, True),
    "lxsuwwu": IndexedLoad(4, 2, True, True),
}


def indexed_load(mnemonic: str, dest: int, base: int, index: int, offset: int = 0) -> tuple[list[str], str, list[str]]:
    """Load at base + offset using a nonzero index, then restore the base."""
    instruction = ZILX_INSTRUCTIONS[mnemonic]
    index_value = 0x100000001 if instruction.unsigned_word else 1
    adjustment = offset - (1 << instruction.scale)
    setup = [f"LI(x{index}, {index_value:#x})", f"addi x{base}, x{base}, {adjustment}"]
    load = f"{mnemonic} x{dest}, (x{base}), x{index}"
    cleanup = [f"addi x{base}, x{base}, {-adjustment}"]
    return setup, load, cleanup
