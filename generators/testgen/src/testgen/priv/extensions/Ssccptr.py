##################################
# priv/extensions/Ssccptr.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Ssccptr test generator
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssccptr S-mode test generator.

Ssccptr: main memory regions with both the cacheability and coherence PMAs must support hardware
page-table reads.

The page tables live in main memory. The test loads a sentinel through a 4 KiB page whose virtual
address differs from its physical address, so the load reaches the sentinel only if the walker read
a PTE at every level of the table. An identity mapping would also pass on a hart that left
translation off.
"""

from testgen.asm.helpers import write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.access import virtual_address
from testgen.priv.extensions.sv.generate import begin_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import SV32, SV39, PteFlags, SvMode, create_page_mapping
from testgen.priv.registry import add_priv_test_generator

covergroup = "Ssccptr_cg"
_SENTINEL = "0xC0FFEE42"


def _make_ssccptr(test_data: TestData, sv: SvMode) -> list[TestChunk]:
    coverpoint = "cp_ssccptr"
    chunk = begin_sv_test(test_data, sv, "Smode", f"{sv.name}_hptw_read", coverpoint=coverpoint)

    pa_reg, va_reg, sentinel_reg, load_reg = test_data.int_regs.get_registers(4)
    chunk.code.extend(
        [
            "// Map va_data with a leaf at level 0, so the walk reads a PTE at every level.",
            *create_page_mapping(
                sv, virtual_address="va_data", physical_address="rvtest_data_1", leaf_level=0, leaf_flags=PteFlags()
            ),
            "sfence.vma",
            "",
            "// Store the sentinel through the identity map of the test image.",
            f"LA(x{pa_reg}, rvtest_data_1)",
            f"LI(x{sentinel_reg}, {_SENTINEL})",
            f"sw x{sentinel_reg}, 0(x{pa_reg})",
            "",
            "// Load it through va_data, whose physical address is rvtest_data_1.",
            *virtual_address(sv, "va_data", 0, destination=f"x{va_reg}", scratch=f"x{pa_reg}"),
            f"LI(x{load_reg}, 0)",
            test_data.add_testcase("lw_under_vm", coverpoint, covergroup),
            f"lw x{load_reg}, 0(x{va_reg})",
            write_sigupd(load_reg, test_data),
        ]
    )
    test_data.int_regs.return_registers([pa_reg, va_reg, sentinel_reg, load_reg])

    chunk.raw_data.extend(sv_data(sv))
    return [test_data.end_test_chunk()]


# Any hart with paging has Sv32 or Sv39: Sv48 requires Sv39 and Sv57 requires Sv48.
@add_priv_test_generator(
    "Ssccptr",
    required_extensions=["S", "Ssccptr", "Sv32"],
    march_extensions=["S"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_ssccptr_sv32(test_data: TestData) -> list[TestChunk]:
    return _make_ssccptr(test_data, SV32)


@add_priv_test_generator(
    "Ssccptr",
    required_extensions=["S", "Ssccptr", "Sv39"],
    march_extensions=["S"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_ssccptr_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_ssccptr(test_data, SV39)
