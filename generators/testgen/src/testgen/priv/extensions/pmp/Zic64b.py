##################################
# priv/extensions/pmp/Zic64b.py
#
# Zic64b cache-block boundary across two adjacent PMP regions.
# SPDX-License-Identifier: Apache-2.0
##################################

"""cbo.zero at a PMP boundary when Zic64b fixes the block size at 64 bytes.

The two NAPOT regions are adjacent and each is at least 4 KiB, so every 64-byte
block lies entirely in one region. Permissions differ between regions and are
uniform inside a block. A split block is unspecified and is not tested.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.pmp.helpers import cfg_byte, cfg_shift, napot_mask_defines, set_pmpaddr, zero_pmp_regs
from testgen.priv.registry import add_priv_test_generator

_BLOCK = 64
_COVERGROUP = "Zic64b_cg"
# Entries 0 and 1 are the two regions. The background entry is the last usable
# entry and, for TOR, also consumes the entry below it, so at least four entries
# leave 0 and 1 free.
_MIN_PMP_ENTRIES = 4


def _store_bytes(addr: int, val: int, count: int) -> list[str]:
    return [f"sb x{val}, {offset}(x{addr})" for offset in range(count)]


def _load_bytes(test_data: TestData, addr: int, val: int, count: int) -> list[str]:
    lines: list[str] = []
    for offset in range(count):
        lines.append(f"lbu x{val}, {offset}(x{addr})")
        lines.append(write_sigupd(val, test_data))
    return lines


def _regions() -> list[str]:
    """Two adjacent NAPOT regions, each max(PMP grain, 4 KiB) bytes, filled with 0xFF."""
    return [
        ".p2align 12",
        ".p2align (UDB_PMP_GRANULARITY)",
        "zic64b_deny:",
        "#if UDB_PMP_GRANULARITY > 12",
        ".fill (1 << UDB_PMP_GRANULARITY), 1, 0xFF",
        "#else",
        ".fill 4096, 1, 0xFF",
        "#endif",
        "zic64b_allow:",
        "#if UDB_PMP_GRANULARITY > 12",
        ".fill (1 << UDB_PMP_GRANULARITY), 1, 0xFF",
        "#else",
        ".fill 4096, 1, 0xFF",
        "#endif",
    ]


def _program_pmp() -> list[str]:
    # 1001 = L|R, 1011 = L|R|W. OR into pmpcfg0 so a background byte in the same CSR survives.
    deny = cfg_byte("1001", "napot", cfg_shift(0))
    allow = cfg_byte("1011", "napot", cfg_shift(1))
    return [
        *zero_pmp_regs(),
        "",
        *napot_mask_defines(12),
        "",
        "RVTEST_PMP_SET_BACKGROUND x4",
        *set_pmpaddr("napot", 0, "zic64b_deny"),
        *set_pmpaddr("napot", 1, "zic64b_allow"),
        f"#define ZIC64B_PMP_DENY {deny}",
        f"#define ZIC64B_PMP_ALLOW {allow}",
        "LI(x5, (ZIC64B_PMP_DENY) | (ZIC64B_PMP_ALLOW))",
        "csrr x6, pmpcfg0",
        "or x5, x5, x6",
        "csrw pmpcfg0, x5",
        "RVTEST_SFENCE_VMA_IF_SUPPORTED",
        "LI(x5, MENVCFG_CBZE)",
        "csrs menvcfg, x5",
        "",
    ]


@add_priv_test_generator(
    "Zic64b",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm", "Zicboz", "Zic64b"],
    march_extensions=["Zicboz", "Zic64b"],
    params=[f"NUM_PMP_ENTRIES: '>={_MIN_PMP_ENTRIES}'", "PMP_NAPOT_SUPPORTED: true"],
)
def make_zic64b_pmp(test_data: TestData) -> list[TestChunk]:
    """Generate the Zic64b PMP-boundary test."""
    # x4-x6 are used by the PMP helpers and the cfg update.
    addr, val = test_data.int_regs.get_registers(2, exclude_regs=[0, 4, 5, 6])
    chunk = test_data.begin_test_chunk("pmp")
    chunk.section_header = comment_banner(
        "cp_zic64b_pmp_fault",
        "Adjacent NAPOT regions: entry 0 is read-only, entry 1 is readable and writable.\n"
        "cbo.zero at offsets 0 and 63 of the last block of entry 0 raises a store access fault.\n"
        "The same offsets in the first block of entry 1 zero that block and leave the next byte unchanged.",
    )
    chunk.trap_sigupd_count = trap_sigupd_count(2)
    chunk.code.extend(_program_pmp())

    for offset in (0, 63):
        chunk.code.extend(
            [
                f"LA(x{addr}, zic64b_allow)",
                f"addi x{addr}, x{addr}, {-_BLOCK + offset}",
                test_data.add_testcase(f"deny_off_{offset}", "cp_zic64b_pmp_fault", _COVERGROUP),
                f"cbo.zero 0(x{addr})",
                f"LA(x{addr}, zic64b_allow)",
                f"addi x{addr}, x{addr}, -{_BLOCK}",
                *_load_bytes(test_data, addr, val, _BLOCK),
                f"LA(x{addr}, zic64b_allow)",
                f"lbu x{val}, 0(x{addr})",
                write_sigupd(val, test_data),
                "",
            ]
        )

    for offset in (0, 63):
        chunk.code.extend(
            [
                f"LI(x{val}, 0xFF)",
                f"LA(x{addr}, zic64b_allow)",
                *_store_bytes(addr, val, _BLOCK),
                f"LA(x{addr}, zic64b_allow)",
                f"addi x{addr}, x{addr}, {offset}",
                test_data.add_testcase(f"allow_off_{offset}", "cp_zic64b_pmp_ok", _COVERGROUP),
                f"cbo.zero 0(x{addr})",
                f"LA(x{addr}, zic64b_allow)",
                *_load_bytes(test_data, addr, val, _BLOCK),
                f"lbu x{val}, {_BLOCK}(x{addr})",
                write_sigupd(val, test_data),
                "",
            ]
        )

    chunk.raw_data.extend(_regions())
    test_data.int_regs.return_registers([addr, val])
    return [test_data.end_test_chunk()]
