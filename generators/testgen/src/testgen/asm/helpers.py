##################################
# asm/helpers.py
#
# Assembly generation helpers for test code.
# jcarlin@hmc.edu 5 Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Assembly generation helpers for test code."""

from typing import Literal

from testgen.constants import INDENT
from testgen.data.state import TestData


def comment_banner(title: str, description: str | None = None) -> str:
    """
    Generate a comment banner for a test section.

    Args:
        title: The title of the section (e.g., coverpoint name)
        description: Optional multi-line description

    Returns:
        Formatted comment banner string
    """
    lines = [
        "",
        "",
        "/////////////////////////////////",
        f"// {title}",
    ]
    if description:
        lines.extend(f"//   {line}" for line in description.strip().split("\n"))
    lines.append("/////////////////////////////////")
    return "\n".join(lines)


def arch_block(lines: list[str], *extensions: str) -> list[str]:
    """Bracket a block of code with `.option arch, +ext...` so the extensions are enabled
    only where they are needed, instead of in the test's MARCH string."""
    adds = ", ".join(f"+{e.lower()}" for e in extensions)
    return [".option push", f".option arch, {adds}", *lines, ".option pop"]


def to_hex(value: int, bits: int) -> str:
    """
    Convert an integer to a hex string for assembly output.

    Args:
        value: The integer value (should already be in correct range)
        bits: Number of bits (used to handle negative values)
    """
    # For negative values, convert to unsigned representation
    if value < 0:
        value = value + (2**bits)
    return f"0x{value:0{bits // 4}x}"


def load_int_reg(name: str, reg: int, val: int, test_data: TestData) -> str:
    """Generate assembly to load an integer register with a specific value."""
    assert test_data.test_chunk is not None, "No active test chunk — call begin_test_chunk() first"
    test_data.test_chunk.data_values.append(val)
    return f"{INDENT}RVTEST_TESTDATA_LOAD_INT(x{test_data.int_regs.data_reg}, x{reg}) # load {name}: x{reg} = {to_hex(val, test_data.xlen)}"


def load_float_reg(
    name: str,
    reg: int,
    val: int,
    test_data: TestData,
    fp_load_type: Literal["single", "double", "half", "quad"] | None = None,
) -> str:
    """Generate assembly to load a floating point register with a specific value."""
    if fp_load_type is None:
        fp_load_type = test_data.fp_load_size

    assert test_data.test_chunk is not None, "No active test chunk — call begin_test_chunk() first"
    test_data.test_chunk.data_values.append(val)
    fp_load_bits = {"half": 16, "single": 32, "double": 64, "quad": 128}.get(fp_load_type, test_data.flen)
    return f"{INDENT}RVTEST_TESTDATA_LOAD_FLOAT_{fp_load_type.upper()}(x{test_data.int_regs.data_reg}, f{reg}) # load {name}: f{reg} = {to_hex(val & ((1 << fp_load_bits) - 1), fp_load_bits)}"


def write_sigupd(
    check_reg: int | None,
    test_data: TestData,
    sig_type: Literal["int", "fflags", "float"] = "int",
    *,
    label: str | None = None,
) -> str:
    """
    Generate assembly for SIGUPD and increment sigupd_count.
    """
    assert test_data.test_chunk is not None, "No active test chunk — call begin_test_chunk() first"
    sig_reg = test_data.int_regs.sig_reg
    link_reg = test_data.int_regs.link_reg
    temp_reg = test_data.int_regs.temp_reg
    fp_temp_reg = test_data.float_regs.temp_reg
    label = label or test_data.current_testcase_label
    if sig_type == "int":
        if check_reg is None:
            raise ValueError("check_reg must be provided for int sig_type")
        test_data.test_chunk.sigupd_count += 1
        return (
            f"{INDENT}# Check if x{check_reg} contains the expected result. x{sig_reg} is the signature ptr, "
            f"x{link_reg} is the link ptr, x{temp_reg} is a temp reg.\n"
            f"{INDENT}RVTEST_SIGUPD(x{sig_reg}, x{link_reg}, x{temp_reg}, x{check_reg}, {label}, {label}_str)"
        )
    elif sig_type == "fflags":
        test_data.test_chunk.sigupd_count += 1
        return (
            f"{INDENT}# Check fflags. x{sig_reg} is the signature ptr, "
            f"x{link_reg} is the link ptr, x{temp_reg} is a temp reg.\n"
            f"{INDENT}RVTEST_SIGUPD_FFLAGS(x{sig_reg}, x{link_reg}, x{temp_reg}, {label}, {label}_str)"
        )
    elif sig_type == "float":
        if check_reg is None:
            raise ValueError("check_reg must be provided for float sig_type")
        if test_data.flen > test_data.xlen:
            test_data.test_chunk.sigupd_count += 3
        else:
            test_data.test_chunk.sigupd_count += 2
        return (
            f"{INDENT}# Check if f{check_reg} contains the expected result. Also checks fflags. "
            f"x{sig_reg} is the signature ptr, x{link_reg} is the link ptr, x{temp_reg} "
            f"is a temp reg, f{fp_temp_reg} is a floating point temp reg.\n"
            f"{INDENT}RVTEST_SIGUPD_F(x{sig_reg}, x{link_reg}, x{temp_reg}, f{fp_temp_reg}, f{check_reg}, {label}, {label}_str)"
        )
    else:
        raise ValueError(f"Unknown sig_type: {sig_type}")


# Background pattern for store targets. Its bytes differ from each other and from common edge-value bytes.
STORE_CANARY = 0xD2691EA74DB836E5


def _store_area_words(area_bytes: int, test_data: TestData) -> range:
    """Byte offsets of the XLEN words that cover area_bytes."""
    xlen_bytes = test_data.xlen // 8
    return range(0, max(area_bytes, xlen_bytes), xlen_bytes)


def fill_store_canary(
    base_reg: int,
    temp_reg: int,
    test_data: TestData,
    *,
    area_bytes: int,
    store_val: int,
    store_bytes: int,
    offset: int = 0,
) -> list[str]:
    """Point base_reg at scratch and fill area_bytes there (rounded up to whole XLEN words) with a canary.

    The canary is STORE_CANARY, except that the store_bytes bytes at offset are the complement of the
    low store_bytes bytes of store_val. Each byte the store should write therefore changes, so a store
    that is dropped or goes to the wrong address fails the check. check_store_canary reads the area back.
    The area is outside the signature region, which self-checking tests preload with the expected results.
    """
    words = _store_area_words(area_bytes, test_data)
    area = bytearray(STORE_CANARY.to_bytes(8, "little") * ((words.stop + 7) // 8))
    for i in range(store_bytes):
        area[offset + i] = ~(store_val >> (8 * i)) & 0xFF
    lines = [f"LA(x{base_reg}, scratch) # point base at scratch"]
    for word_offset in words:
        canary = int.from_bytes(area[word_offset : word_offset + words.step], "little")
        lines.extend(
            [
                load_int_reg("store canary", temp_reg, canary, test_data),
                f"SREG x{temp_reg}, {word_offset}(x{base_reg}) # fill store target with canary",
            ]
        )
    return lines


def check_store_canary(base_reg: int, temp_reg: int, test_data: TestData, *, area_bytes: int) -> list[str]:
    """Read back and check every XLEN word filled by fill_store_canary."""
    lines: list[str] = []
    for word_offset in _store_area_words(area_bytes, test_data):
        lines.extend(
            [
                f"LREG x{temp_reg}, {word_offset}(x{base_reg}) # load store target for checking",
                write_sigupd(temp_reg, test_data),
            ]
        )
    return lines


def int_store_data(rs2: int, rs2val: int, base_reg: int, immval: int, store_bytes: int) -> tuple[int, int]:
    """Return (value, known bytes) that an integer store with base = scratch - immval writes.

    rs2 = x0 stores 0. If rs2 is the base register, it holds scratch - immval; scratch is 256-byte
    aligned, so only the low byte is known.
    """
    if rs2 == 0:
        return 0, store_bytes
    if rs2 == base_reg:
        return -immval & 0xFF, 1
    return rs2val, store_bytes


def reproducible_hash(s: str) -> int:
    """Return a simple hash of a string for use as a random seed.

    Python randomizes hashes by default, but we need a repeatable hash for repeatable test cases.
    """
    h = 0
    for c in s:
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return h
