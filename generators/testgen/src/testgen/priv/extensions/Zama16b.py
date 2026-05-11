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

# Each row: (mnemonic, access_size_bytes, is_fp, guard).
# `guard` is a complete preprocessor directive (e.g. "#ifdef X") or None.
# Contiguous rows sharing the same guard are wrapped in a single #if/#endif block.

_LOAD_OPS: list[tuple[str, int, bool, str | None]] = [
    # Integer loads (always present)
    ("lb", 1, False, None),
    ("lbu", 1, False, None),
    ("lh", 2, False, None),
    ("lhu", 2, False, None),
    ("lw", 4, False, None),
    # RV64-only integer loads
    ("lwu", 4, False, "#if __riscv_xlen == 64"),
    ("ld", 8, False, "#if __riscv_xlen == 64"),
    # Floating-point loads
    ("flh", 2, True, "#ifdef ZFH_SUPPORTED"),
    ("flw", 4, True, "#ifdef F_SUPPORTED"),
    ("fld", 8, True, "#ifdef D_SUPPORTED"),
    ("flq", 16, True, "#ifdef Q_SUPPORTED"),
]

_STORE_OPS: list[tuple[str, int, bool, str | None]] = [
    # Integer stores (always present)
    ("sb", 1, False, None),
    ("sh", 2, False, None),
    ("sw", 4, False, None),
    # RV64-only integer store
    ("sd", 8, False, "#if __riscv_xlen == 64"),
    # Floating-point stores
    ("fsh", 2, True, "#ifdef ZFH_SUPPORTED"),
    ("fsw", 4, True, "#ifdef F_SUPPORTED"),
    ("fsd", 8, True, "#ifdef D_SUPPORTED"),
    ("fsq", 16, True, "#ifdef Q_SUPPORTED"),
]

_AMO_OPS: list[tuple[str, int, str]] = [
    # Word AMOs (Zaamo)
    ("amoswap.w", 4, "#ifdef ZAAMO_SUPPORTED"),
    ("amoadd.w", 4, "#ifdef ZAAMO_SUPPORTED"),
    ("amoand.w", 4, "#ifdef ZAAMO_SUPPORTED"),
    ("amoor.w", 4, "#ifdef ZAAMO_SUPPORTED"),
    ("amoxor.w", 4, "#ifdef ZAAMO_SUPPORTED"),
    ("amomax.w", 4, "#ifdef ZAAMO_SUPPORTED"),
    ("amomaxu.w", 4, "#ifdef ZAAMO_SUPPORTED"),
    ("amomin.w", 4, "#ifdef ZAAMO_SUPPORTED"),
    ("amominu.w", 4, "#ifdef ZAAMO_SUPPORTED"),
    # Doubleword AMOs (Zaamo + RV64)
    ("amoswap.d", 8, "#if defined(ZAAMO_SUPPORTED) && __riscv_xlen == 64"),
    ("amoadd.d", 8, "#if defined(ZAAMO_SUPPORTED) && __riscv_xlen == 64"),
    ("amoand.d", 8, "#if defined(ZAAMO_SUPPORTED) && __riscv_xlen == 64"),
    ("amoor.d", 8, "#if defined(ZAAMO_SUPPORTED) && __riscv_xlen == 64"),
    ("amoxor.d", 8, "#if defined(ZAAMO_SUPPORTED) && __riscv_xlen == 64"),
    ("amomax.d", 8, "#if defined(ZAAMO_SUPPORTED) && __riscv_xlen == 64"),
    ("amomaxu.d", 8, "#if defined(ZAAMO_SUPPORTED) && __riscv_xlen == 64"),
    ("amomin.d", 8, "#if defined(ZAAMO_SUPPORTED) && __riscv_xlen == 64"),
    ("amominu.d", 8, "#if defined(ZAAMO_SUPPORTED) && __riscv_xlen == 64"),
    # Byte AMOs (Zaamo + Zabha)
    ("amoswap.b", 1, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    ("amoadd.b", 1, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    ("amoand.b", 1, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    ("amoor.b", 1, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    ("amoxor.b", 1, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    ("amomax.b", 1, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    ("amomaxu.b", 1, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    ("amomin.b", 1, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    ("amominu.b", 1, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    # Halfword AMOs (Zaamo + Zabha)
    ("amoswap.h", 2, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    ("amoadd.h", 2, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    ("amoand.h", 2, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    ("amoor.h", 2, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    ("amoxor.h", 2, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    ("amomax.h", 2, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    ("amomaxu.h", 2, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    ("amomin.h", 2, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    ("amominu.h", 2, "#if defined(ZAAMO_SUPPORTED) && defined(ZABHA_SUPPORTED)"),
    # Compare-and-swap (Zaamo + Zacas)
    ("amocas.w", 4, "#if defined(ZAAMO_SUPPORTED) && defined(ZACAS_SUPPORTED)"),
    ("amocas.d", 8, "#if defined(ZAAMO_SUPPORTED) && defined(ZACAS_SUPPORTED) && __riscv_xlen == 64"),
    ("amocas.q", 16, "#if defined(ZAAMO_SUPPORTED) && defined(ZACAS_SUPPORTED) && __riscv_xlen == 64"),
]


_SCRATCH_INIT_WORDS = [0x44556677, 0x00112233, 0x89ABCDEF, 0x01234567]


def _emit_scratch_init(base_reg: int, data_reg: int) -> list[str]:
    """Re-initialize the 16-byte scratch region with a known distinct pattern."""
    out = [f"LA(x{base_reg}, scratch)   # reload base — init 16-byte region"]
    for i, word in enumerate(_SCRATCH_INIT_WORDS):
        out += [
            f"LI(x{data_reg}, 0x{word:08X})",
            f"sw x{data_reg}, {i * 4}(x{base_reg})",
        ]
    return out


def _emit_sig_dump(base_reg: int, check_reg: int, test_data: TestData) -> list[str]:
    """Dump all 16 bytes of scratch to the signature so modified bytes are visible."""
    out = []
    for i in range(0, 16, 4):
        out += [
            f"lw x{check_reg}, {i}(x{base_reg})   # read back bytes [{i}:{i + 3}]",
            write_sigupd(check_reg, test_data),
        ]
    return out


def _generate_load_tests(test_data: TestData) -> list[str]:
    """Generate per-instruction load tests matching SV coverpoint names (cp_<mnemonic>_load)."""
    covergroup = "Zama16b_cg"
    addr_reg, dest_reg, sentinel_reg, base_reg = test_data.int_regs.get_registers(4)
    fp_reg = test_data.float_regs.get_register()  # allocate one FP reg for load result

    lines = [
        comment_banner(
            "cp_zama16b_load",
            "Misaligned loads that stay within a 16-byte aligned window must not fault.\n"
            "Base address is 16-byte aligned; offsets sweep [0, 16 - access_size].",
        ),
        "",
        "# Align base address to 16 bytes",
        f"LA(x{base_reg}, scratch)          # load address of scratch region",
        f"LI(x{sentinel_reg}, 0xDEADBEEF)   # sentinel — overwritten by a successful load",
    ]

    prev_guard: str | None = None
    for mnemonic, size, is_fp, guard in _LOAD_OPS:
        if guard != prev_guard:
            if prev_guard is not None:
                lines.append("#endif")
            if guard is not None:
                lines.append(guard)
            prev_guard = guard

        bin_name = mnemonic.replace(".", "_")
        coverpoint = f"cp_{bin_name}_load"

        for offset in range(16 - size + 1):
            lines.extend(
                [
                    "",
                    f"# {mnemonic} at offset {offset} (access [{offset}, {offset + size - 1}] within 16-byte window)",
                    f"addi x{addr_reg}, x{base_reg}, {offset}   # effective address = base + {offset}",
                    f"mv x{dest_reg}, x{sentinel_reg}       # preset dest with sentinel",
                    test_data.add_testcase(f"{bin_name}_off{offset}", coverpoint, covergroup),
                ]
            )
            if is_fp:
                storeback = mnemonic.replace("fl", "fs", 1)  # fp store instruction
                lines.extend(
                    [
                        f"{mnemonic} f{fp_reg}, 0(x{addr_reg})",
                        "nop",
                        f"{storeback} f{fp_reg}, 0(x{base_reg})        # store FP result back to scratch",
                        f"lw x{dest_reg}, 0(x{base_reg})        # read back lower word as evidence",
                        write_sigupd(dest_reg, test_data),
                    ]
                )
            else:
                lines.extend(
                    [
                        f"{mnemonic} x{dest_reg}, 0(x{addr_reg})",
                        "nop",
                        write_sigupd(dest_reg, test_data),
                    ]
                )

    if prev_guard is not None:
        lines.append("#endif")

    test_data.int_regs.return_registers([addr_reg, dest_reg, sentinel_reg, base_reg])
    test_data.float_regs.return_register(fp_reg)
    return lines


def _generate_store_tests(test_data: TestData) -> list[str]:
    """Generate per-instruction store tests matching SV coverpoint names (cp_<mnemonic>_store).

    For each store instruction, sweep offsets [0, 16 - size]. The scratch region
    is re-initialized before each store; after each store all 16 bytes are written
    to the signature so the exact bytes modified by the store are visible.
    """
    covergroup = "Zama16b_cg"
    addr_reg, data_reg, check_reg, base_reg = test_data.int_regs.get_registers(4)
    fp_reg = test_data.float_regs.get_register()

    lines = [
        comment_banner(
            "cp_zama16b_store",
            "Misaligned stores that stay within a 16-byte aligned window must not fault.\n"
            "Base address is 16-byte aligned; offsets sweep [0, 16 - access_size].\n"
            "Scratch is re-initialized before each store; all 16 bytes are signed out\n"
            "so the exact modified bytes are visible in the signature.",
        ),
        "",
    ]

    prev_guard: str | None = None
    last_fp_preload_guard: str | None = None
    for mnemonic, size, is_fp, guard in _STORE_OPS:
        if guard != prev_guard:
            if prev_guard is not None:
                lines.append("#endif")
            if guard is not None:
                lines.append(guard)
            prev_guard = guard

        bin_name = mnemonic.replace(".", "_")
        coverpoint = f"cp_{bin_name}_store"

        # FP needs a value preloaded into f{fp_reg} once per guard block (matches the FP store width).
        if is_fp and guard != last_fp_preload_guard:
            preload = mnemonic.replace("fs", "fl", 1)
            lines += [
                f"LA(x{base_reg}, scratch)",
                f"LI(x{data_reg}, 0xA5A5A5A5)",
                f"sw x{data_reg}, 0(x{base_reg})",
                f"{preload} f{fp_reg}, 0(x{base_reg})  # f{fp_reg} holds store pattern",
            ]
            last_fp_preload_guard = guard

        for offset in range(16 - size + 1):
            lines.append(
                f"# {mnemonic} at offset {offset} (access [{offset}, {offset + size - 1}] within 16-byte window)"
            )

            # Re-initialize scratch so each testcase starts from a known state
            lines.extend(_emit_scratch_init(base_reg, data_reg))

            # Compute effective address after re-init (base_reg is reloaded inside _emit_scratch_init)
            lines.append(f"addi x{addr_reg}, x{base_reg}, {offset}   # effective address = base + {offset}")

            if is_fp:
                lines.extend(
                    [
                        test_data.add_testcase(f"{bin_name}_off{offset}", coverpoint, covergroup),
                        f"{mnemonic} f{fp_reg}, 0(x{addr_reg})",
                        "nop",
                    ]
                )
            else:
                lines.extend(
                    [
                        f"LI(x{data_reg}, 0xA5A5A5A5)   # value to store",
                        test_data.add_testcase(f"{bin_name}_off{offset}", coverpoint, covergroup),
                        f"{mnemonic} x{data_reg}, 0(x{addr_reg})",
                        "nop",
                    ]
                )

            # Dump all 16 bytes to signature — shows exactly which bytes the store touched
            lines.extend(_emit_sig_dump(base_reg, check_reg, test_data))

    if prev_guard is not None:
        lines.append("#endif")

    test_data.int_regs.return_registers([addr_reg, data_reg, check_reg, base_reg])
    test_data.float_regs.return_register(fp_reg)
    return lines


def _generate_amo_tests(test_data: TestData) -> list[str]:
    """Generate per-instruction AMO tests matching SV coverpoint names (cp_<mnemonic>_amo).

    AMOs have no immediate offset — the address is in rs1 directly.
    Base address is 16-byte aligned; rs1 is set to base + offset for
    each offset in [0, 16 - size]. Scratch is re-initialized before each
    AMO testcase; all 16 bytes are written to the signature afterward so
    the exact bytes modified are visible.
    Note: atomicity under concurrent masters is NOT verified here.
    """
    covergroup = "Zama16b_cg"

    addr_reg, src_reg, dest_reg, base_reg = test_data.int_regs.get_registers(4)

    lines = [
        comment_banner(
            "cp_zama16b_amo",
            "Misaligned AMOs that stay within a 16-byte aligned window must not fault.\n"
            "Base address is 16-byte aligned; offsets sweep [0, 16 - access_size].\n"
            "Scratch is re-initialized before each AMO; all 16 bytes are signed out\n"
            "so the exact bytes modified by the AMO are visible in the signature.\n"
            "Note: atomicity under concurrent masters is NOT verified here.",
        ),
        "",
    ]

    prev_guard: str | None = None
    for mnemonic, size, guard in _AMO_OPS:
        if guard != prev_guard:
            if prev_guard is not None:
                lines.append("#endif")
            if guard is not None:
                lines.append(guard)
            prev_guard = guard

        bin_name = mnemonic.replace(".", "_")
        coverpoint = f"cp_{bin_name}_amo"

        for offset in range(16 - size + 1):
            lines.append(
                f"# {mnemonic} at offset {offset} (access [{offset}, {offset + size - 1}] within 16-byte window)"
            )

            # Re-initialize scratch with known distinct pattern before each AMO
            lines.extend(_emit_scratch_init(base_reg, src_reg))

            # Compute effective address after re-init
            lines.extend(
                [
                    f"addi x{addr_reg}, x{base_reg}, {offset}   # effective address = base + {offset}",
                    f"LI(x{src_reg}, 0xABC)                      # value AMO will write into memory",
                    test_data.add_testcase(f"{bin_name}_off{offset}", coverpoint, covergroup),
                    f"{mnemonic} x{dest_reg}, x{src_reg}, (x{addr_reg})",
                    "nop",
                ]
            )

            # Dump all 16 bytes to signature — shows exactly which bytes the AMO touched
            lines.extend(_emit_sig_dump(base_reg, dest_reg, test_data))

    if prev_guard is not None:
        lines.append("#endif")

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
