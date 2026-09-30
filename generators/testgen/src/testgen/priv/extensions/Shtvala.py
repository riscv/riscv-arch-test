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

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.random import random_int
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.HCommon import TWO_STAGE_GATE, guest_fault_tests
from testgen.priv.extensions.sv.generate import guest_translation_setup, guest_translation_teardown, per_xlen
from testgen.priv.extensions.sv.page_tables import PteFlags, SvMode, create_page_mapping, write_pte
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


#####################################################################
# Misaligned accesses that straddle into an unmapped guest page
#####################################################################

# Bytes of a word access at the end of a page that fall in the next page
_STRADDLE_OFFSET = 2


def _straddle_va(vs: SvMode) -> int:
    """A word two bytes below vs.data_va, so the access continues into the page at vs.data_va."""
    return int(vs.data_va, 16) - _STRADDLE_OFFSET


def _straddle_leaves(g: SvMode, vs: SvMode, user: bool, regs: tuple[int, int, int]) -> list[str]:
    """A VS-stage superpage leaf at vs.data_va to the guest physical superpage of g.data_va, where a G-stage kilopage
    maps the page below g.data_va to shtvala_straddle_page and leaves g.data_va unmapped."""
    return [
        *write_pte(
            vs,
            level=vs.levels - 1,
            flags=PteFlags(user=user),
            virtual_address=vs.data_va,
            physical_address=g.data_va,
            regs=regs,
            pa_is_label=False,
            superpage=True,
        ),
        *create_page_mapping(
            g,
            leaf_level=0,
            leaf_flags=PteFlags(user=True),
            virtual_address=f"({g.data_va} - 0x1000)",
            physical_address="shtvala_straddle_page",
            regs=regs,
        ),
    ]


def _hs_straddle_tests(test_data: TestData) -> list[str]:
    """hlv.w and hsv.w from HS-mode with hstatus.SPVP = 0 across the end of the mapped guest page.

    A faulting hlv.w leaves rd unchanged.  After each guest-page fault, record htinst's Addr. Offset, the difference
    between the faulting virtual address in stval and the original virtual address (hypervisor.adoc
    H_tinst_addr_offset).  htinst may instead be zero, which records the expected offset.
    """

    def mappings(g: SvMode, vs: SvMode) -> list[str]:
        pte, addr, tmp = test_data.int_regs.get_registers(3)
        leaves = _straddle_leaves(g, vs, True, (pte, addr, tmp))
        test_data.int_regs.return_registers([pte, addr, tmp])
        return [*leaves, *guest_translation_setup(test_data, g, vs, "VUmode")]

    lines = [f"#if {TWO_STAGE_GATE}", *per_xlen(mappings)]
    addr, rd, tinst, zero = test_data.int_regs.get_registers(4)
    lines.extend(
        [
            *per_xlen(lambda _, vs: [f"LI(x{addr}, {_straddle_va(vs):#x})"]),
            f"LI(x{rd}, HSTATUS_SPVP)",
            f"csrc hstatus, x{rd}",
            f"LI(x{rd}, 42)",
        ]
    )
    for instr, coverpoint, load in (
        ("hlv.w", "cp_hlv_straddle_guest_page_fault", True),
        ("hsv.w", "cp_hsv_straddle_guest_page_fault", False),
    ):
        lines.extend(
            [
                f"LI(x{tinst}, {random_int(32, signed=False):#x})",
                f"csrw htval, x{tinst}",
                test_data.add_testcase(f"hs_{instr.replace('.', '_')}", coverpoint, COVERGROUP),
                f"{instr} x{rd}, (x{addr})",
                *([write_sigupd(rd, test_data)] if load else []),
                f"csrr x{tinst}, htinst",
                f"seqz x{zero}, x{tinst}",
                f"neg x{zero}, x{zero}",
                f"andi x{zero}, x{zero}, {_STRADDLE_OFFSET}",
                f"srli x{tinst}, x{tinst}, 15",
                f"andi x{tinst}, x{tinst}, 0x1F",
                f"or x{tinst}, x{tinst}, x{zero}",
                write_sigupd(tinst, test_data),
            ]
        )
    test_data.int_regs.return_registers([addr, rd, tinst, zero])
    return [*lines, *guest_translation_teardown(test_data), f"#endif // {TWO_STAGE_GATE}"]


@add_priv_test_generator(
    "Shtvala",
    required_extensions=["H", "Shtvala"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler.  The hart performs the first part of a misaligned access in
    # main memory and faults on the second, so stval holds the page-boundary address.
    params=["TIME_CSR_IMPLEMENTED: true", "MISALIGNED_LDST: true", "MISALIGNED_SPLIT_STRATEGY: sequential_bytes"],
)
def make_shtvala_straddle(test_data: TestData) -> list[TestChunk]:
    """Misaligned loads and stores whose second part has an unmapped guest physical address."""
    faults = [
        ("straddle", "cp_load_straddle_guest_page_fault", "lw", _straddle_va),
        ("straddle", "cp_store_straddle_guest_page_fault", "sw", _straddle_va),
    ]
    tc = test_data.begin_test_chunk("straddle")
    tc.code.extend(
        [
            comment_banner(
                "cp_{load,store,hlv,hsv}_straddle_guest_page_fault",
                "lw and sw in VS-mode and VU-mode, and hlv.w and hsv.w in HS-mode, two bytes below the end of a mapped\n"
                "guest page whose successor has an unmapped guest physical address.  stval holds the page-boundary\n"
                "address, htval its guest physical address, and htinst's Addr. Offset their distance from the\n"
                "original address (hypervisor.adoc H_straddle)",
            ),
            *guest_fault_tests(test_data, COVERGROUP, "htval", _straddle_leaves, faults),
            *_hs_straddle_tests(test_data),
        ]
    )
    tc.raw_data.extend([".p2align 12", "shtvala_straddle_page:", ".zero 4096"])
    return [test_data.end_test_chunk()]
