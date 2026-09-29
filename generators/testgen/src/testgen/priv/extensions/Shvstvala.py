##################################
# Shvstvala.py
#
# Shvstvala extension test generator: traps into VS-mode write vstval in every case Sstvala requires for stval.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shvstvala extension test generator: traps into VS-mode write vstval in every case Sstvala requires for stval.

The suite boots to HS-mode, which delegates the exceptions to VS-mode with hedeleg.  Each exception is raised in
VS-mode and in VU-mode after vstval is set to a random value, and the VS-mode trap handler records vstval.
Virtual-instruction exceptions are never taken in VS-mode (hedeleg[22] is read-only zero), so the Sstvala case for
them does not apply.
"""

from dataclasses import replace

from testgen.asm.helpers import comment_banner
from testgen.data.random import random_int
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ExceptionsCommon import (
    generate_illegal_instruction_tests,
    generate_instr_access_fault_tests,
    generate_instr_adr_misaligned_jalr_tests,
    generate_load_access_fault_tests,
    generate_load_address_misaligned_tests,
    generate_store_access_fault_tests,
    generate_store_address_misaligned_tests,
)
from testgen.priv.extensions.HCommon import guest_fault_tests
from testgen.priv.extensions.sv.page_tables import PteFlags, SvMode, create_page_walk, write_pte
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "Shvstvala_cg"

# The exceptions delegated to VS-mode
HEDELEG = " | ".join(
    f"(1 << CAUSE_{cause})"
    for cause in (
        "MISALIGNED_FETCH",
        "FETCH_ACCESS",
        "ILLEGAL_INSTRUCTION",
        "MISALIGNED_LOAD",
        "LOAD_ACCESS",
        "MISALIGNED_STORE",
        "STORE_ACCESS",
        "FETCH_PAGE_FAULT",
        "LOAD_PAGE_FAULT",
        "STORE_PAGE_FAULT",
    )
)

# (coverpoint, offset of a VS-stage 4 KiB page from vs.data_va, its leaf permissions, instruction).  W alone is
# reserved, so loads fault; stores need W; fetches need X.  The leaves point to the guest physical page g.data_va,
# which the G-stage leaves unmapped, so an access that wrongly passes the VS-stage check raises a guest-page fault.
PAGE_FAULTS = [
    ("cp_load_page_fault", 0x0000, PteFlags(read=False, execute=False), "lw"),
    ("cp_store_page_fault", 0x1000, PteFlags(write=False), "sw"),
    ("cp_instr_page_fault", 0x2000, PteFlags(execute=False), "jalr"),
]


def _hedeleg(test_data: TestData) -> list[str]:
    """Delegate the exceptions to VS-mode."""
    reg = test_data.int_regs.get_register()
    lines = [f"LI(x{reg}, {HEDELEG})", f"csrw hedeleg, x{reg}"]
    test_data.int_regs.return_register(reg)
    return lines


def _exception_tests(test_data: TestData, mode: str) -> list[str]:
    """Access faults, misaligned accesses and fetches, and illegal instructions in VS-mode or VU-mode.

    Misaligned loads and stores fault only without UDB_MISALIGNED_LDST, and misaligned fetches only without Zca.
    """
    setup = [f"RVTEST_TSBI_CSR_WRITE(CSR_VSTVAL, {random_int(32, signed=False):#x})"]
    return [
        *_hedeleg(test_data),
        f"RVTEST_TSBI_GOTO_{mode.upper()}MODE",
        *generate_load_access_fault_tests(test_data, COVERGROUP, setup=setup),
        *generate_store_access_fault_tests(test_data, COVERGROUP, setup=setup),
        *generate_instr_access_fault_tests(test_data, COVERGROUP, setup=setup),
        "#ifndef UDB_MISALIGNED_LDST",
        *generate_load_address_misaligned_tests(test_data, COVERGROUP, setup=setup),
        *generate_store_address_misaligned_tests(test_data, COVERGROUP, setup=setup),
        "#endif",
        "#ifndef ZCA_SUPPORTED",
        *generate_instr_adr_misaligned_jalr_tests(test_data, COVERGROUP, setup=setup),
        "#endif",
        *generate_illegal_instruction_tests(test_data, COVERGROUP, setup=setup),
        "RVTEST_TSBI_GOTO_SMODE",
        "csrw hedeleg, zero",
    ]


def _page_fault_leaves(g: SvMode, vs: SvMode, user: bool, regs: tuple[int, int, int]) -> list[str]:
    """The VS-stage leaves of PAGE_FAULTS, each lacking R, W or X, and the page walk above them."""
    lines = create_page_walk(vs, leaf_level=0, virtual_address=vs.data_va, regs=regs)
    for _, offset, flags, _ in PAGE_FAULTS:
        lines += write_pte(
            vs,
            level=0,
            flags=replace(flags, user=user),
            virtual_address=f"{int(vs.data_va, 16) + offset:#x}",
            physical_address=g.data_va,
            regs=regs,
            pa_is_label=False,
        )
    return lines


@add_priv_test_generator(
    "Shvstvala",
    required_extensions=["H", "Shvstvala"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_shvstvala(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Shvstvala coverpoints."""
    test_chunks: list[TestChunk] = []
    # One file per mode, because the ExceptionsCommon testcase labels do not name the mode
    for mode in ("vs", "vu"):
        tc = test_data.new_test_chunk(test_chunks, mode)
        tc.code.extend(_exception_tests(test_data, mode))
    tc = test_data.new_test_chunk(test_chunks, "page_fault")
    faults = [
        (instr, coverpoint, instr, lambda vs, offset=offset: int(vs.data_va, 16) + offset)
        for coverpoint, offset, _, instr in PAGE_FAULTS
    ]
    tc.code.extend(
        [
            comment_banner(
                "cp_load_page_fault, cp_store_page_fault, cp_instr_page_fault",
                "In VS-mode and VU-mode under two-stage translation, load from a page without R, store to a page\n"
                "without W and fetch from a page without X",
            ),
            *_hedeleg(test_data),
            *guest_fault_tests(test_data, COVERGROUP, "vstval", _page_fault_leaves, faults),
            "csrw hedeleg, zero",
        ]
    )
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
