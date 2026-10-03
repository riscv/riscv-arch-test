##################################
# asm/helpers.py
#
# Assembly generation helpers for test code.
# jcarlin@hmc.edu 5 Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Assembly generation helpers for test code."""

from functools import lru_cache
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
    """Enable *extensions* around *lines*, or return *lines* unchanged if none are given."""
    if not extensions:
        return lines
    adds = ", ".join(f"+{e.lower()}" for e in extensions)
    return [".option push", f".option arch, {adds}", *lines, ".option pop"]


def lrsc_retry_loop(label: str, counter_reg: int, sc_rd: int) -> tuple[list[str], list[str]]:
    """Return the lines that open and close a constrained LR/SC loop.

    A single LR/SC pair may fail spuriously; only a constrained LR/SC loop is guaranteed to succeed eventually.
    Put the opening lines directly before the LR and the closing lines directly after the SC. The loop retries
    the pair up to 100 times until the SC writes 0 to ``sc_rd``. ``label`` must be unique, such as the testcase label.
    Code between the LR and the SC must be base I instructions other than loads, stores, backward jumps and taken
    backward branches, JALR, FENCE, and SYSTEM.
    """
    retry_label = f"{label}_retry"
    success_label = f"{label}_success"
    opening = [
        f"LI(x{counter_reg}, 100) # retry counter for constrained LR/SC loop",
        f"{retry_label}:",
    ]
    closing = [
        f"beqz x{sc_rd}, {success_label} # SC succeeded, skip retry",
        f"addi x{counter_reg}, x{counter_reg}, -1 # decrement retry count",
        f"bnez x{counter_reg}, {retry_label} # retry LR/SC if not exhausted",
        f"{success_label}:",
    ]
    return opening, closing


@lru_cache(maxsize=4096)
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


# Bytes written by each store whose formatter does not take the width from its own alignment rules
STORE_BYTES = {"sb": 1, "sh": 2, "sw": 4, "sd": 8, "fsh": 2, "fsw": 4, "fsd": 8, "fsq": 16}

# Background pattern for FP store targets. Its bytes differ from each other and from common edge-value bytes.
STORE_CANARY = 0xD2691EA74DB836E5

# Coverpoints whose FP stores check at least 8 bytes, so an RV32 store that writes a whole 64-bit FP
# register instead of its low bytes fails. One coverpoint per instruction is enough to catch it.
_FP_STORE_WIDE_CHECK_COVERPOINTS = ("cp_fs2", "cp_fs2_p")


def store_area_offsets(area_bytes: int, test_data: TestData) -> range:
    """Byte offsets of the XLEN words that cover area_bytes."""
    xlen_bytes = test_data.xlen // 8
    return range(0, max(area_bytes, xlen_bytes), xlen_bytes)


def store_canary(
    base_reg: int, rs2: int, temp_reg: int, offsets: range | tuple[int, ...] = (0,), shift_bytes: int = 0
) -> list[str]:
    """Fill the XLEN words at offsets(base_reg) with ~rs2 shifted left by shift_bytes bytes.

    A store of rs2 at byte shift_bytes of one of these words then changes every bit it writes, so a store
    that is dropped or goes to another address fails the readback. The complement is taken at run time
    because rs2 may hold the base address.
    """
    lines = [f"xori x{temp_reg}, x{rs2}, -1 # canary = ~rs2, so the store changes every bit it writes"]
    if shift_bytes:
        lines.append(f"slli x{temp_reg}, x{temp_reg}, {8 * shift_bytes} # line the canary up with the store")
    lines.extend(f"SREG x{temp_reg}, {offset}(x{base_reg}) # fill store target with canary" for offset in offsets)
    return lines


def fp_store_area_bytes(store_bytes: int, test_data: TestData) -> int:
    """Bytes of an FP store target to fill and check."""
    if test_data.current_coverpoint in _FP_STORE_WIDE_CHECK_COVERPOINTS:
        return max(8, store_bytes)
    return store_bytes


def fp_store_canary(
    base_reg: int, temp_reg: int, test_data: TestData, *, area_bytes: int, store_val: int, store_bytes: int
) -> list[str]:
    """Fill area_bytes at base_reg, rounded up to whole XLEN words, with STORE_CANARY.

    The low store_bytes bytes hold the complement of store_val instead, so the store changes each of them.
    """
    offsets = store_area_offsets(area_bytes, test_data)
    area = bytearray(STORE_CANARY.to_bytes(8, "little") * ((offsets.stop + 7) // 8))
    for i in range(store_bytes):
        area[i] = ~(store_val >> (8 * i)) & 0xFF
    lines: list[str] = []
    for offset in offsets:
        canary = int.from_bytes(area[offset : offset + offsets.step], "little")
        lines.extend(
            [
                load_int_reg("store canary", temp_reg, canary, test_data),
                f"SREG x{temp_reg}, {offset}(x{base_reg}) # fill store target with canary",
            ]
        )
    return lines


def check_store_canary(base_reg: int, temp_reg: int, test_data: TestData, *, area_bytes: int) -> list[str]:
    """Read back and check the XLEN words that cover area_bytes at base_reg."""
    lines: list[str] = []
    for offset in store_area_offsets(area_bytes, test_data):
        lines.extend(
            [
                f"LREG x{temp_reg}, {offset}(x{base_reg}) # load store target for checking",
                write_sigupd(temp_reg, test_data),
            ]
        )
    return lines


def reproducible_hash(s: str) -> int:
    """Return a simple hash of a string for use as a random seed.

    Python randomizes hashes by default, but we need a repeatable hash for repeatable test cases.
    """
    h = 0
    for c in s:
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return h
