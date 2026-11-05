##################################
# priv/extensions/sv/Zic64b.py
#
# Zic64b cache-block boundary across two adjacent pages.
# SPDX-License-Identifier: Apache-2.0
##################################

"""cbo.zero at a 4 KiB page boundary when Zic64b fixes the block size at 64 bytes.

A naturally aligned 64-byte block lies entirely in one page. The last block of a
writable page and the first block of the next read-only page are checked at
block offsets 0 and 63.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.generate import SvRegs, begin_sv_test, end_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import (
    SV32,
    SV39,
    SV48,
    SV57,
    PteFlags,
    SvMode,
    create_leaf_pte,
    create_page_mapping,
)
from testgen.priv.registry import add_priv_test_generator

_BLOCK = 64
_PAGE = 4096
_COVERGROUP = "Zic64b_cg"
_PAGES = """\
.p2align 12
zic64b_page_a:
.skip 4096
.p2align 12
zic64b_page_b:
.skip 4096
"""


def _store_bytes(addr: int, val: int, count: int) -> list[str]:
    return [f"sb x{val}, {offset}(x{addr})" for offset in range(count)]


def _load_bytes(test_data: TestData, addr: int, val: int, count: int) -> list[str]:
    lines: list[str] = []
    for offset in range(count):
        lines.append(f"lbu x{val}, {offset}(x{addr})")
        lines.append(write_sigupd(val, test_data))
    return lines


def _make_page_boundary(test_data: TestData, sv: SvMode) -> TestChunk:
    regs = SvRegs.allocate(test_data)
    chunk = begin_sv_test(
        test_data,
        regs,
        sv,
        "Smode",
        f"{sv.name}_page",
        sig_init=None,
        setup_asm=(
            f"LI(x{regs.scratch}, MENVCFG_CBZE)",
            tsbi_call(f"csrs menvcfg, x{regs.scratch}"),
        ),
    )
    chunk.section_header = comment_banner(
        "cp_zic64b_sv_fault / cp_zic64b_sv_ok",
        "Page A is writable and page B = A+4KiB is read-only.\n"
        "cbo.zero at offsets 0 and 63 of the last block of A succeeds and does not modify B.\n"
        "The same offsets in the first block of B raise a store page fault and leave both blocks unchanged.",
    )
    addr, val = regs.addr, regs.value
    writable = PteFlags()
    read_only = PteFlags(write=False)
    last_block = f"(va_data + {_PAGE - _BLOCK})"
    chunk.code.extend(
        [
            ".set va_next, va_data + 0x1000",
            *create_page_mapping(
                sv,
                leaf_level=0,
                leaf_flags=writable,
                virtual_address="va_data",
                physical_address="zic64b_page_a",
            ),
            *create_page_mapping(
                sv,
                leaf_level=0,
                leaf_flags=writable,
                virtual_address="va_next",
                physical_address="zic64b_page_b",
            ),
            "sfence.vma",
            f"LI(x{val}, 0xFF)",
            f"LI(x{addr}, {last_block})",
            *_store_bytes(addr, val, _BLOCK),
            f"LI(x{addr}, va_next)",
            *_store_bytes(addr, val, _BLOCK + 1),
            create_leaf_pte(
                sv,
                level=0,
                flags=read_only,
                virtual_address="va_next",
                physical_address="zic64b_page_b",
            ),
            "sfence.vma",
            "",
        ]
    )

    for offset in (0, 63):
        chunk.code.extend(
            [
                f"LI(x{addr}, (va_next + {offset}))",
                test_data.add_testcase(f"deny_off_{offset}", "cp_zic64b_sv_fault", _COVERGROUP),
                f"cbo.zero 0(x{addr})",
                f"LI(x{addr}, va_next)",
                *_load_bytes(test_data, addr, val, _BLOCK),
                "",
            ]
        )

    for offset in (0, 63):
        chunk.code.extend(
            [
                f"LI(x{val}, 0xFF)",
                f"LI(x{addr}, {last_block})",
                *_store_bytes(addr, val, _BLOCK),
                f"LI(x{addr}, ({last_block} + {offset}))",
                test_data.add_testcase(f"allow_off_{offset}", "cp_zic64b_sv_ok", _COVERGROUP),
                f"cbo.zero 0(x{addr})",
                f"LI(x{addr}, {last_block})",
                *_load_bytes(test_data, addr, val, _BLOCK),
                f"LI(x{addr}, va_next)",
                f"lbu x{val}, 0(x{addr})",
                write_sigupd(val, test_data),
                "",
            ]
        )

    chunk.raw_data.extend(sv_data(sv, regs, data_region_body=_PAGES))
    return end_sv_test(test_data, regs)


def _register(sv: SvMode) -> None:
    @add_priv_test_generator(
        "Zic64b",
        required_extensions=[sv.extension, "Zicboz", "Zic64b"],
        march_extensions=["Zicboz", "Zic64b"],
        extra_defines=["#define BOOT_TO_SMODE"],
    )
    def generate(test_data: TestData, mode: SvMode = sv) -> list[TestChunk]:
        return [_make_page_boundary(test_data, mode)]

    generate.__name__ = f"make_zic64b_{sv.name}_page"


for _sv in (SV32, SV39, SV48, SV57):
    _register(_sv)
