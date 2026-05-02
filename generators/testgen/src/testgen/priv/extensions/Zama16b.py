##################################
# Zama16b.py
# Written:  Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, MAY 2026)
#
# Zama16b misaligned atomicity granule extension test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zama16b extension test generator.

Verifies that misaligned loads, stores, and AMOs that do not cross a
naturally aligned 16-byte boundary do NOT raise a misaligned fault.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

_LOAD_OPS = [
    # Integer loads (always present)
    ("lb", 1, False, False, None),
    ("lbu", 1, False, False, None),
    ("lh", 2, False, False, None),
    ("lhu", 2, False, False, None),
    ("lw", 4, False, False, None),
    # RV64-only integer loads
    ("lwu", 4, False, False, "__riscv_xlen == 64"),
    ("ld", 8, False, False, "__riscv_xlen == 64"),
    # Floating-point loads
    ("flh", 2, True, False, "ZFH_SUPPORTED"),
    ("flw", 4, True, False, "F_SUPPORTED"),
    ("fld", 8, True, False, "D_SUPPORTED"),
    ("flq", 16, True, False, "Q_SUPPORTED"),
]

_STORE_OPS = [
    # Integer stores (always present)
    ("sb", 1, False, False, None),
    ("sh", 2, False, False, None),
    ("sw", 4, False, False, None),
    # RV64-only integer store
    ("sd", 8, False, False, "__riscv_xlen == 64"),
    # Floating-point stores
    ("fsh", 2, True, False, "ZFH_SUPPORTED"),
    ("fsw", 4, True, False, "F_SUPPORTED"),
    ("fsd", 8, True, False, "D_SUPPORTED"),
    ("fsq", 16, True, False, "Q_SUPPORTED"),
]

_AMO_OPS = [
    # Word AMOs (always present with Zaamo)
    ("amoswap.w", 4, False, True, None),
    ("amoadd.w", 4, False, True, None),
    ("amoand.w", 4, False, True, None),
    ("amoor.w", 4, False, True, None),
    ("amoxor.w", 4, False, True, None),
    ("amomax.w", 4, False, True, None),
    ("amomaxu.w", 4, False, True, None),
    ("amomin.w", 4, False, True, None),
    ("amominu.w", 4, False, True, None),
    # Doubleword AMOs (RV64 only)
    ("amoswap.d", 8, False, True, "__riscv_xlen == 64"),
    ("amoadd.d", 8, False, True, "__riscv_xlen == 64"),
    ("amoand.d", 8, False, True, "__riscv_xlen == 64"),
    ("amoor.d", 8, False, True, "__riscv_xlen == 64"),
    ("amoxor.d", 8, False, True, "__riscv_xlen == 64"),
    ("amomax.d", 8, False, True, "__riscv_xlen == 64"),
    ("amomaxu.d", 8, False, True, "__riscv_xlen == 64"),
    ("amomin.d", 8, False, True, "__riscv_xlen == 64"),
    ("amominu.d", 8, False, True, "__riscv_xlen == 64"),
    # Zabha: byte AMOs
    ("amoswap.b", 1, False, True, "ZABHA_SUPPORTED"),
    ("amoadd.b", 1, False, True, "ZABHA_SUPPORTED"),
    ("amoand.b", 1, False, True, "ZABHA_SUPPORTED"),
    ("amoor.b", 1, False, True, "ZABHA_SUPPORTED"),
    ("amoxor.b", 1, False, True, "ZABHA_SUPPORTED"),
    ("amomax.b", 1, False, True, "ZABHA_SUPPORTED"),
    ("amomaxu.b", 1, False, True, "ZABHA_SUPPORTED"),
    ("amomin.b", 1, False, True, "ZABHA_SUPPORTED"),
    ("amominu.b", 1, False, True, "ZABHA_SUPPORTED"),
    # Zabha: halfword AMOs
    ("amoswap.h", 2, False, True, "ZABHA_SUPPORTED"),
    ("amoadd.h", 2, False, True, "ZABHA_SUPPORTED"),
    ("amoand.h", 2, False, True, "ZABHA_SUPPORTED"),
    ("amoor.h", 2, False, True, "ZABHA_SUPPORTED"),
    ("amoxor.h", 2, False, True, "ZABHA_SUPPORTED"),
    ("amomax.h", 2, False, True, "ZABHA_SUPPORTED"),
    ("amomaxu.h", 2, False, True, "ZABHA_SUPPORTED"),
    ("amomin.h", 2, False, True, "ZABHA_SUPPORTED"),
    ("amominu.h", 2, False, True, "ZABHA_SUPPORTED"),
    # Zacas: compare-and-swap
    ("amocas.w", 4, False, True, "ZACAS_SUPPORTED"),
    ("amocas.d", 8, False, True, "ZACAS_SUPPORTED && __riscv_xlen == 64"),
    ("amocas.q", 16, False, True, "ZACAS_SUPPORTED && __riscv_xlen == 64"),
]

_FP_STOREBACK = {
    "flh": "fsh",
    "flw": "fsw",
    "fld": "fsd",
    "flq": "fsq",
}


def _open_guard(guard: str | None) -> list[str]:
    """Return opening preprocessor guard lines, or empty list if none."""
    if guard is None:
        return []
    # If guard contains operators, treat it as an expression
    if any(op in guard for op in ["==", "!=", "<", ">", "&&", "||"]):
        return [f"#if {guard}"]
    # Otherwise treat it as a macro
    return [f"#ifdef {guard}"]


def _close_guard(guard: str | None) -> list[str]:
    """Return closing preprocessor guard lines, or empty list if none."""
    if guard is None:
        return []
    return [f"#endif // {guard}"]


def _safe_mnemonic(mnemonic: str) -> str:
    """Convert mnemonic to a safe identifier for bin names (dots -> underscores)."""
    return mnemonic.replace(".", "_")


def _generate_load_tests(test_data: TestData) -> list[str]:
    """Generate cp_zama16b_load tests."""
    covergroup = "Zama16b_cg"
    coverpoint = "cp_zama16b_load"

    addr_reg, dest_reg, sentinel_reg, base_reg = test_data.int_regs.get_registers(4)

    lines = [
        comment_banner(
            coverpoint,
            "Misaligned loads that stay within a 16-byte aligned window must not fault.\n"
            "Base address is 16-byte aligned; offsets sweep [0, 16 - access_size].",
        ),
        "",
        "# Align base address to 16 bytes",
        f"LA(x{base_reg}, scratch)          # load address of scratch region",
        f"LI(x{sentinel_reg}, 0xDEADBEEF)   # sentinel — overwritten by a successful load",
    ]

    prev_guard = None
    for mnemonic, size, is_fp, _, guard in _LOAD_OPS:
        max_offset = 16 - size  # highest offset that keeps access within the window

        # Emit guard transitions only when the guard changes
        if guard != prev_guard:
            lines.extend(_close_guard(prev_guard))
            lines.extend(_open_guard(guard))
            prev_guard = guard

        safe_mn = _safe_mnemonic(mnemonic)

        for offset in range(max_offset + 1):
            lines.extend(
                [
                    "",
                    f"# {mnemonic} at offset {offset} (access [{offset}, {offset + size - 1}] within 16-byte window)",
                    f"addi x{addr_reg}, x{base_reg}, {offset}   # effective address = base + {offset}",
                ]
            )

            if is_fp:
                storeback = _FP_STOREBACK[mnemonic]
                lines.extend(
                    [
                        f"mv x{dest_reg}, x{sentinel_reg}       # preset dest with sentinel",
                        test_data.add_testcase(f"{safe_mn}_off{offset}", coverpoint, covergroup),
                        f"{mnemonic} f8, 0(x{addr_reg})",
                        "nop",
                        f"{storeback} f8, 0(x{base_reg})        # store FP result back to scratch",
                        f"lw x{dest_reg}, 0(x{base_reg})        # read back lower word as evidence",
                        write_sigupd(dest_reg, test_data),
                    ]
                )

            else:
                lines.extend(
                    [
                        f"mv x{dest_reg}, x{sentinel_reg}       # preset dest with sentinel",
                        test_data.add_testcase(f"{safe_mn}_off{offset}", coverpoint, covergroup),
                        f"{mnemonic} x{dest_reg}, 0(x{addr_reg})",
                        "nop",
                        write_sigupd(dest_reg, test_data),
                    ]
                )

    lines.extend(_close_guard(prev_guard))
    test_data.int_regs.return_registers([addr_reg, dest_reg, sentinel_reg, base_reg])
    return lines


# ---------------------------------------------------------------------------
# Store coverpoint
# ---------------------------------------------------------------------------


def _generate_store_tests(test_data: TestData) -> list[str]:
    """Generate cp_zama16b_store tests.

    For each store instruction, sweep offsets [0, 16 - size].  A known
    data value is written; the scratch region is read back to confirm
    no fault diverted execution.
    """
    covergroup = "Zama16b_cg"
    coverpoint = "cp_zama16b_store"

    addr_reg, data_reg, check_reg, base_reg = test_data.int_regs.get_registers(4)

    lines = [
        comment_banner(
            coverpoint,
            "Misaligned stores that stay within a 16-byte aligned window must not fault.\n"
            "Base address is 16-byte aligned; offsets sweep [0, 16 - access_size].",
        ),
        "",
        "# Align base address to 16 bytes",
        f"LA(x{base_reg}, scratch)          # load address of scratch region",
        f"LI(x{data_reg}, 0xA5A5A5A5)       # pattern to store",
        f"sw x{data_reg}, 0(x{base_reg})    # write pattern to scratch memory",
        f"flw f9, 0(x{base_reg})            # load known pattern into f9 for FP stores",
    ]

    prev_guard = None
    for mnemonic, size, is_fp, _, guard in _STORE_OPS:
        max_offset = 16 - size

        if guard != prev_guard:
            lines.extend(_close_guard(prev_guard))
            lines.extend(_open_guard(guard))
            prev_guard = guard

        safe_mn = _safe_mnemonic(mnemonic)

        for offset in range(max_offset + 1):
            lines.extend(
                [
                    "",
                    f"# {mnemonic} at offset {offset} (access [{offset}, {offset + size - 1}] within 16-byte window)",
                    f"addi x{addr_reg}, x{base_reg}, {offset}   # effective address = base + {offset}",
                ]
            )

            if is_fp:
                # fp stores: use fp source register f9 (pre-loaded with pattern)
                lines.extend(
                    [
                        test_data.add_testcase(f"{safe_mn}_off{offset}", coverpoint, covergroup),
                        f"{mnemonic} f9, 0(x{addr_reg})",
                        "nop",
                        f"lw x{check_reg}, 0(x{base_reg})",
                        write_sigupd(check_reg, test_data),
                    ]
                )
            else:
                lines.extend(
                    [
                        test_data.add_testcase(f"{safe_mn}_off{offset}", coverpoint, covergroup),
                        f"{mnemonic} x{data_reg}, 0(x{addr_reg})",
                        "nop",
                        f"lw x{check_reg}, 0(x{base_reg})   # read back to confirm store executed",
                        write_sigupd(check_reg, test_data),
                    ]
                )

    lines.extend(_close_guard(prev_guard))
    test_data.int_regs.return_registers([addr_reg, data_reg, check_reg, base_reg])
    return lines


# ---------------------------------------------------------------------------
# AMO coverpoint
# ---------------------------------------------------------------------------


def _generate_amo_tests(test_data: TestData) -> list[str]:
    """Generate cp_zama16b_amo tests.

    AMOs have no immediate offset — the address is in rs1 directly.
    Base address is 16-byte aligned; rs1 is set to base + offset for
    each offset in [0, 16 - size].
    """
    covergroup = "Zama16b_cg"
    coverpoint = "cp_zama16b_amo"

    addr_reg, src_reg, dest_reg, base_reg = test_data.int_regs.get_registers(4)

    lines = [
        comment_banner(
            coverpoint,
            "Misaligned AMOs that stay within a 16-byte aligned window must not fault.\n"
            "Base address is 16-byte aligned; offsets sweep [0, 16 - access_size].\n"
            "Note: atomicity under concurrent masters is NOT verified here.",
        ),
        "",
        "# Align base address to 16 bytes",
        f"LA(x{base_reg}, scratch)          # load address of scratch region",
        f"LI(x{src_reg}, 1)                 # AMO source operand",
    ]

    prev_guard = None
    for mnemonic, size, _, _, guard in _AMO_OPS:
        max_offset = 16 - size

        if guard != prev_guard:
            lines.extend(_close_guard(prev_guard))
            lines.extend(_open_guard(guard))
            prev_guard = guard

        safe_mn = _safe_mnemonic(mnemonic)

        for offset in range(max_offset + 1):
            lines.extend(
                [
                    "",
                    f"# {mnemonic} at offset {offset} (access [{offset}, {offset + size - 1}] within 16-byte window)",
                    f"addi x{addr_reg}, x{base_reg}, {offset}   # effective address = base + {offset}",
                    f"LI(x{dest_reg}, 0xBAD)            # preset dest with sentinel",
                    test_data.add_testcase(f"{safe_mn}_off{offset}", coverpoint, covergroup),
                    f"{mnemonic} x{dest_reg}, x{src_reg}, (x{addr_reg})",
                    "nop",
                    write_sigupd(dest_reg, test_data),
                ]
            )

    lines.extend(_close_guard(prev_guard))
    test_data.int_regs.return_registers([addr_reg, src_reg, dest_reg, base_reg])
    return lines


@add_priv_test_generator(
    "Zama16b",
    required_extensions=["Zama16b"],
    march_extensions=["I", "Zicsr", "Zaamo", "Zabha", "Zacas", "F", "D", "Zfh"],
)
def make_zama16b(test_data: TestData) -> list[str]:
    """Generate tests for Zama16b misaligned atomicity granule extension."""
    lines: list[str] = []

    lines.extend(_generate_load_tests(test_data))
    lines.extend(_generate_store_tests(test_data))
    lines.extend(_generate_amo_tests(test_data))

    return lines
