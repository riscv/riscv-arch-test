##################################
# Shtvala.py
#
# Shtvala extension test generator: guest-page faults write htval with the faulting guest physical address.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shtvala extension test generator: guest-page faults write htval with the faulting guest physical address.

The suite boots to HS-mode.  Guest code in VS-mode and VU-mode runs under two-stage translation and loads, stores
and fetches through two VS-stage mappings whose guest physical addresses the G-stage leaves unmapped: a superpage
leaf, where the final access faults, and a pointer to a VS-stage page table, where the implicit PTE read faults.
Each guest-page fault traps to HS-mode, whose trap handler records htval, after htval is set to a random value.
"""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.HCommon import guest_fault_tests
from testgen.priv.extensions.sv.page_tables import PteFlags, SvMode, write_pte
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "Shtvala_cg"
FAULTS = [
    ("lw", "cp_load_guest_page_fault"),
    ("sw", "cp_store_guest_page_fault"),
    ("jalr", "cp_instr_guest_page_fault"),
]


def _implicit_va(vs: SvMode) -> int:
    """The guest virtual address one superpage below vs.data_va, whose VS-stage walk reads an unmapped PTE."""
    return int(vs.data_va, 16) - (1 << vs.page_offset_bits(vs.levels - 1))


def _leaves(g: SvMode, vs: SvMode, user: bool, regs: tuple[int, int, int]) -> list[str]:
    """A VS-stage superpage leaf at vs.data_va and a pointer for _implicit_va, both to the unmapped g.data_va."""
    top = vs.levels - 1
    return [
        *write_pte(
            vs,
            level=top,
            flags=PteFlags(user=user),
            virtual_address=vs.data_va,
            physical_address=g.data_va,
            regs=regs,
            pa_is_label=False,
            superpage=True,
        ),
        *write_pte(
            vs,
            level=top,
            flags=PteFlags.nonleaf(),
            virtual_address=f"{_implicit_va(vs):#x}",
            physical_address=g.data_va,
            regs=regs,
            pa_is_label=False,
        ),
    ]


@add_priv_test_generator(
    "Shtvala",
    required_extensions=["H", "Shtvala"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_shtvala(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Shtvala coverpoints."""
    faults = [
        (access, coverpoint, instr, (lambda vs: int(vs.data_va, 16)) if access == "final" else _implicit_va)
        for instr, coverpoint in FAULTS
        for access in ("final", "implicit")
    ]
    tc = test_data.begin_test_chunk()
    tc.code.extend(
        [
            comment_banner(
                "cp_load_guest_page_fault, cp_store_guest_page_fault, cp_instr_guest_page_fault",
                "In VS-mode and VU-mode, load, store and fetch where the final access or the implicit VS-stage PTE\n"
                "read has an unmapped guest physical address",
            ),
            *guest_fault_tests(test_data, COVERGROUP, "htval", _leaves, faults),
        ]
    )
    return [test_data.end_test_chunk()]
