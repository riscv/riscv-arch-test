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
    # Columns: (mnemonic, access_size_bytes, is_fp, is_amo, preprocessor_guard)
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
    # Columns: (mnemonic, access_size_bytes, is_fp, is_amo, preprocessor_guard)
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
    # Columns: (mnemonic, access_size_bytes, is_fp, is_amo, preprocessor_guard)
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

# Maps each FP load mnemonic to its corresponding FP store mnemonic (used to write results back to scratch memory).
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


def _emit_scratch_init(base_reg: int, data_reg: int) -> list[str]:
    """Re-initialize the 16-byte scratch region with a known distinct pattern before each testcase.

    Pattern: 0x01234567_89ABCDEF_00112233_44556677 (matches other misaligned tests).
    """
    _INIT_WORDS = [0x44556677, 0x00112233, 0x89ABCDEF, 0x01234567]
    out = [f"LA(x{base_reg}, scratch)   # reload base — init 16-byte region"]
    for i, word in enumerate(_INIT_WORDS):
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

    prev_guard = None
    for mnemonic, size, is_fp, _, guard in _LOAD_OPS:
        max_offset = 16 - size  # highest offset that keeps access within the window
        coverpoint = f"cp_{_safe_mnemonic(mnemonic)}_load"  # e.g. cp_lb_load, cp_flw_load

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
                        f"mv x{dest_reg}, x{sentinel_reg}       # preset dest with sentinel",
                        test_data.add_testcase(f"{safe_mn}_off{offset}", coverpoint, covergroup),
                        f"{mnemonic} x{dest_reg}, 0(x{addr_reg})",
                        "nop",
                        write_sigupd(dest_reg, test_data),
                    ]
                )

    lines.extend(_close_guard(prev_guard))
    test_data.int_regs.return_registers([addr_reg, dest_reg, sentinel_reg, base_reg])
    test_data.float_regs.return_register(fp_reg)
    return lines


# ---------------------------------------------------------------------------
# Store coverpoint
# ---------------------------------------------------------------------------


def _generate_store_tests(test_data: TestData) -> list[str]:
    """Generate per-instruction store tests matching SV coverpoint names (cp_<mnemonic>_store).

    For each store instruction, sweep offsets [0, 16 - size]. The scratch region
    is re-initialized before each store; after each store all 16 bytes are written
    to the signature so the exact bytes modified by the store are visible.
    This matches the pattern used in Misalign-sd-00.S.
    """
    covergroup = "Zama16b_cg"

    addr_reg, data_reg, check_reg, base_reg = test_data.int_regs.get_registers(4)
    fp_reg = test_data.float_regs.get_register()

    _FP_PRELOAD_INSN = {
        "ZFH_SUPPORTED": "flh",
        "F_SUPPORTED": "flw",
        "D_SUPPORTED": "fld",
        "Q_SUPPORTED": "flq",
    }

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

    last_fp_preload_guard = None
    prev_guard = None

    for mnemonic, size, is_fp, _, guard in _STORE_OPS:
        max_offset = 16 - size
        coverpoint = f"cp_{_safe_mnemonic(mnemonic)}_store"

        if guard != prev_guard:
            lines.extend(_close_guard(prev_guard))
            lines.extend(_open_guard(guard))
            prev_guard = guard

        safe_mn = _safe_mnemonic(mnemonic)

        # Emit guarded FP preload once per extension guard block
        if is_fp and guard != last_fp_preload_guard:
            preload_insn = _FP_PRELOAD_INSN.get(guard, "flw")
            lines += [
                f"# Pre-load FP source register for {guard} stores",
                f"LA(x{base_reg}, scratch)",
                f"LI(x{data_reg}, 0xA5A5A5A5)",
                f"sw x{data_reg}, 0(x{base_reg})",
                f"{preload_insn} f{fp_reg}, 0(x{base_reg})  # f{fp_reg} holds store pattern",
            ]
            last_fp_preload_guard = guard

        for offset in range(max_offset + 1):
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
                        test_data.add_testcase(f"{safe_mn}_off{offset}", coverpoint, covergroup),
                        f"{mnemonic} f{fp_reg}, 0(x{addr_reg})",
                        "nop",
                    ]
                )
            else:
                lines.extend(
                    [
                        f"LI(x{data_reg}, 0xA5A5A5A5)   # value to store",
                        test_data.add_testcase(f"{safe_mn}_off{offset}", coverpoint, covergroup),
                        f"{mnemonic} x{data_reg}, 0(x{addr_reg})",
                        "nop",
                    ]
                )

            # Dump all 16 bytes to signature — shows exactly which bytes the store touched
            lines.extend(_emit_sig_dump(base_reg, check_reg, test_data))

    lines.extend(_close_guard(prev_guard))
    test_data.int_regs.return_registers([addr_reg, data_reg, check_reg, base_reg])
    test_data.float_regs.return_register(fp_reg)
    return lines


# ---------------------------------------------------------------------------
# AMO coverpoint
# ---------------------------------------------------------------------------


def _generate_amo_tests(test_data: TestData) -> list[str]:
    """Generate per-instruction AMO tests matching SV coverpoint names (cp_<mnemonic>_amo).

    AMOs have no immediate offset — the address is in rs1 directly.
    Base address is 16-byte aligned; rs1 is set to base + offset for
    each offset in [0, 16 - size]. Scratch is re-initialized before each
    AMO testcase; all 16 bytes are written to the signature afterward so
    the exact bytes modified are visible (matches Misalign-sd-00.S pattern).
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

    prev_guard = None
    for mnemonic, size, _, _, guard in _AMO_OPS:
        max_offset = 16 - size
        coverpoint = f"cp_{_safe_mnemonic(mnemonic)}_amo"

        if guard != prev_guard:
            lines.extend(_close_guard(prev_guard))
            lines.extend(_open_guard(guard))
            prev_guard = guard

        safe_mn = _safe_mnemonic(mnemonic)

        for offset in range(max_offset + 1):
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
                    test_data.add_testcase(f"{safe_mn}_off{offset}", coverpoint, covergroup),
                    f"{mnemonic} x{dest_reg}, x{src_reg}, (x{addr_reg})",
                    "nop",
                ]
            )

            # Dump all 16 bytes to signature — shows exactly which bytes the AMO touched
            lines.extend(_emit_sig_dump(base_reg, dest_reg, test_data))

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
