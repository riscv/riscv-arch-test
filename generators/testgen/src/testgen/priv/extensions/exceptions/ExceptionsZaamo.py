##################################
# priv/extensions/exceptions/ExceptionsZaamo.py
#
# ExceptionsZaamo extension exception test generator.
# huahuang@hmc.edu Feb 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zaamo extension exception test generator."""

from collections.abc import Callable

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

AMO_OPS = ["amoswap", "amoadd", "amoxor", "amoand", "amoor", "amomin", "amomax", "amominu", "amomaxu"]

# Sentinel values for the rd pair (even, odd)
RD_SENTINELS = (0xBAD, 0xBAD1)

# Bytes reached by the misaligned tests: amocas.q at offset 31 touches bytes 31-46
WINDOW_BYTES = 48


def _window_word(offset: int, word: int) -> int:
    """Return a fill word with distinct bytes in the window and a distinct pattern per offset."""
    return sum(((5 * (4 * word + i) + 7 * offset + 0x11) & 0xFF) << (8 * i) for i in range(4))


def _fill_window(base_reg: int, data_reg: int, offset: int) -> list[str]:
    lines = []
    for word in range(WINDOW_BYTES // 4):
        lines.extend(
            [f"LI(x{data_reg}, {_window_word(offset, word):#010x})", f"sw x{data_reg}, {4 * word}(x{base_reg})"]
        )
    return lines


def _check_window(base_reg: int, check_reg: int, test_data: TestData) -> list[str]:
    """Read back the window with XLEN-wide loads and record each value in the signature."""
    lines = []
    for word in range(WINDOW_BYTES // 4):
        check = [f"LREG x{check_reg}, {4 * word}(x{base_reg})", write_sigupd(check_reg, test_data)]
        lines.extend(check if word % 2 == 0 else ["#if __riscv_xlen == 32", *check, "#endif"])
    return lines


def _amo_test(
    test_data: TestData,
    instr: str,
    bin_name: str,
    coverpoint: str,
    regs: tuple[int, int, int],
    pair: bool = False,
) -> list[str]:
    """Run one AMO with sentinel rd and check rd. For pair instructions, also check the odd rd register."""
    dest_reg, source_reg, addr_reg = regs
    dest_regs = [dest_reg, dest_reg + 1] if pair else [dest_reg]
    return [
        *[f"LI(x{reg}, 0x{sentinel:X})" for reg, sentinel in zip(dest_regs, RD_SENTINELS)],
        test_data.add_testcase(bin_name, coverpoint, "Exceptions_Zaamo_cg"),
        f"{instr} x{dest_reg}, x{source_reg}, (x{addr_reg})",
        *[write_sigupd(reg, test_data) for reg in dest_regs],
    ]


def _init_source_pair(source_reg: int) -> list[str]:
    return [f"LI(x{source_reg}, 1)", f"LI(x{source_reg + 1}, 2)"]


def _amo_tests(
    test_data: TestData,
    coverpoint: str,
    regs: tuple[int, int, int],
    bin_name: Callable[[str], str],
    include_b: bool = True,
) -> list[str]:
    """Run each AMO op at each width, then amocas, with the gating for each extension and XLEN."""

    def ops(width: str) -> list[str]:
        lines = []
        for op in AMO_OPS:
            lines.extend(_amo_test(test_data, f"{op}.{width}", bin_name(f"{op}_{width}"), coverpoint, regs))
        return lines

    lines = [*ops("w"), "#if __riscv_xlen == 64", *ops("d"), "#endif", "#ifdef ZABHA_SUPPORTED", *ops("h")]
    if include_b:
        lines.extend(ops("b"))
    lines.extend(
        [
            "#endif",
            "#ifdef ZACAS_SUPPORTED",
            *_amo_test(test_data, "amocas.w", bin_name("amocas_w"), coverpoint, regs),
            *_amo_test(test_data, "amocas.d", bin_name("amocas_d"), coverpoint, regs, pair=True),
            "#if __riscv_xlen == 64",
            *_amo_test(test_data, "amocas.q", bin_name("amocas_q"), coverpoint, regs, pair=True),
            "#endif",
            "#endif",
        ]
    )
    return lines


def _generate_amo_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "Exceptions_Zaamo_cg", "cp_amo_address_misaligned"

    # Reserve dest/source as AMOCAS-capable register pairs for use later
    dest_reg = test_data.int_regs.get_register_pair()
    source_reg = test_data.int_regs.get_register_pair()
    addr_reg, base_reg = test_data.int_regs.get_registers(2)
    regs = (dest_reg, source_reg, addr_reg)

    lines = [
        comment_banner(
            coverpoint,
            "Test amo instructions on misaligned addresses to check for traps\n"
            "Testing all offsets upto MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE+1",
        ),
    ]

    for offset in range(32):
        lines.extend(
            [
                "",
                f"# Offset {offset} (LSBs: {offset:05b})",
                f"LA(x{base_reg}, scratch)",
                *_fill_window(base_reg, source_reg, offset),
                "",
                f"# Update scratch address to be misaligned with offset {offset}",
                f"addi x{addr_reg}, x{base_reg}, {offset}",
                "",
                *_init_source_pair(source_reg),
                *_amo_tests(test_data, coverpoint, regs, lambda name, offset=offset: f"{name}_offset_{offset}"),
                f"# Check memory after offset {offset}",
                test_data.add_testcase(f"memory_offset_{offset}", coverpoint, covergroup),
                *_check_window(base_reg, dest_reg, test_data),
            ]
        )

    test_data.int_regs.return_register_pair(dest_reg)
    test_data.int_regs.return_register_pair(source_reg)
    test_data.int_regs.return_registers([addr_reg, base_reg])

    return lines


def _generate_amo_access_fault_tests(test_data: TestData) -> list[str]:
    coverpoint = "cp_amo_access_fault"

    # Reserve dest/source as AMOCAS-capable register pairs before choosing the
    # long-lived address register so addr_reg cannot break either even/odd pair.
    dest_reg = test_data.int_regs.get_register_pair()
    source_reg = test_data.int_regs.get_register_pair()
    addr_reg = test_data.int_regs.get_register()

    lines = [
        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
        comment_banner(coverpoint, "Test amo instructions on restricted memory and check for access fault"),
        *_init_source_pair(source_reg),
        f"LI(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
        *_amo_tests(test_data, coverpoint, (dest_reg, source_reg, addr_reg), lambda name: f"amo_access_fault_{name}"),
        "#endif",
    ]

    test_data.int_regs.return_register_pair(dest_reg)
    test_data.int_regs.return_register_pair(source_reg)
    test_data.int_regs.return_register(addr_reg)
    return lines


def _generate_amo_access_misaligned_priority_tests(test_data: TestData) -> list[str]:
    coverpoint = "cp_amo_access_misaligned_priority"

    dest_reg = test_data.int_regs.get_register_pair()
    source_reg = test_data.int_regs.get_register_pair()
    addr_reg = test_data.int_regs.get_register()

    # .b is never misaligned, so it is not tested here
    lines = [
        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
        comment_banner(coverpoint, "Test misaligned amo instructions on restricted memory for exception priority"),
        *_init_source_pair(source_reg),
        f"LI(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
        f"addi x{addr_reg}, x{addr_reg}, 1",
        *_amo_tests(
            test_data,
            coverpoint,
            (dest_reg, source_reg, addr_reg),
            lambda name: f"amo_access_misaligned_priority_{name}",
            include_b=False,
        ),
        "#endif",
    ]

    test_data.int_regs.return_register_pair(dest_reg)
    test_data.int_regs.return_register_pair(source_reg)
    test_data.int_regs.return_register(addr_reg)
    return lines


@add_priv_test_generator(
    "Exceptions",
    required_extensions=["Zaamo", ["Sm", "U"]],
    march_extensions=["Zaamo", "Zabha", "Zacas"],
)
def make_exceptionszaamo(test_data: TestData) -> list[TestChunk]:
    """Main entry point for Zaamo exception test generation."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("Zaamo")

    tc.code.extend(_generate_amo_address_misaligned_tests(test_data))
    tc.code.extend(_generate_amo_access_fault_tests(test_data))
    tc.code.extend(_generate_amo_access_misaligned_priority_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
