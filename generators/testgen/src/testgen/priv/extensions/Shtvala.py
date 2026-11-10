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
Guest-page faults on AMOs and LR are taken the same way, and HLV and HSV fault from HS-mode and U-mode.
"""

from testgen.asm.helpers import arch_block, comment_banner, write_sigupd
from testgen.data.random import random_int
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.HCommon import TWO_STAGE_GATE, guest_fault_tests
from testgen.priv.extensions.sv.generate import guest_translation_setup, guest_translation_teardown, per_xlen
from testgen.priv.extensions.sv.page_tables import PteFlags, SvMode, create_page_mapping, guest_table_data, write_pte
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "Shtvala_cg"
FAULTS = [
    ("lw", "cp_load_guest_page_fault"),
    ("sw", "cp_store_guest_page_fault"),
    ("jalr", "cp_instr_guest_page_fault"),
]
# (instruction, coverpoint) of the hypervisor loads and stores from HS-mode and U-mode
HLSV_FAULTS = [
    ("hlv.w", "cp_hlv_guest_page_fault"),
    ("hlvx.wu", "cp_hlvx_guest_page_fault"),
    ("hsv.w", "cp_hsv_guest_page_fault"),
]
# (instruction, coverpoint, extension) of the atomic accesses, each compiled only with its extension
ATOMIC_FAULTS = [
    ("amoswap.w", "cp_amo_guest_page_fault", "ZAAMO"),
    ("lr.w", "cp_lr_guest_page_fault", "ZALRSC"),
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
)
def make_shtvala(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Shtvala coverpoints."""
    faults = [
        (access, coverpoint, instr, (lambda vs: int(vs.data_va, 16)) if access == "final" else _implicit_va)
        for instr, coverpoint in FAULTS
        for access in ("final", "implicit")
    ]
    test_chunks: list[TestChunk] = []
    tc = test_data.new_test_chunk(test_chunks)
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
    tc = test_data.new_test_chunk(test_chunks, "amo")
    tc.code.append(
        comment_banner(
            "cp_amo_guest_page_fault, cp_lr_guest_page_fault",
            "In VS-mode and VU-mode, amoswap.w and lr.w where the final access or the implicit VS-stage PTE read has\n"
            "an unmapped guest physical address",
        )
    )
    for instr, coverpoint, ext in ATOMIC_FAULTS:
        atomic = [
            (access, coverpoint, instr, (lambda vs: int(vs.data_va, 16)) if access == "final" else _implicit_va)
            for access in ("final", "implicit")
        ]
        tc.code.extend(
            [
                f"#ifdef {ext}_SUPPORTED",
                *arch_block(guest_fault_tests(test_data, COVERGROUP, "htval", _leaves, atomic), ext),
                "#endif",
            ]
        )
    tc = test_data.new_test_chunk(test_chunks, "hlsv")
    tc.code.extend(_hlsv_tests(test_data))
    tc = test_data.new_test_chunk(test_chunks, "fetch_straddle")
    tc.code.extend(_fetch_straddle_tests(test_data, tc))
    tc = test_data.new_test_chunk(test_chunks, "straddle")
    tc.code.extend(_straddle_tests(test_data, tc))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


def _hlsv_tests(test_data: TestData) -> list[str]:
    """hlv.w, hlvx.wu and hsv.w from HS-mode and from U-mode (hstatus.HU = 1) with hstatus.SPVP = 0, where the final
    access or the implicit VS-stage PTE read has an unmapped guest physical address.  The VS-stage and G-stage leaves
    allow execution, so hlvx.wu also takes a load guest-page fault.  A faulting load leaves rd unchanged."""

    def mappings(g: SvMode, vs: SvMode) -> list[str]:
        pte, addr, tmp = test_data.int_regs.get_registers(3)
        leaves = _leaves(g, vs, True, (pte, addr, tmp))
        test_data.int_regs.return_registers([pte, addr, tmp])
        return [*leaves, *guest_translation_setup(test_data, g, vs, "VUmode")]

    addr, rd = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner(
            "cp_hlv_guest_page_fault, cp_hlvx_guest_page_fault, cp_hsv_guest_page_fault",
            "In HS-mode and U-mode, hlv.w, hlvx.wu and hsv.w where the final access or the implicit VS-stage PTE read has an\n"
            "unmapped guest physical address",
        ),
        f"#if {TWO_STAGE_GATE}",
        *per_xlen(mappings),
        f"LI(x{rd}, HSTATUS_SPVP)",
        f"csrc hstatus, x{rd}",
        f"LI(x{rd}, HSTATUS_HU)",
        f"csrs hstatus, x{rd}",
        f"LI(x{rd}, 42)",
    ]
    for mode in ("hs", "u"):
        if mode == "u":
            lines.append("RVTEST_TSBI_GOTO_UMODE")
        for access, address in (("final", lambda vs: int(vs.data_va, 16)), ("implicit", _implicit_va)):
            for instr, coverpoint in HLSV_FAULTS:
                lines.extend(
                    [
                        *per_xlen(lambda _, vs, va=address: [f"LI(x{addr}, {va(vs):#x})"]),
                        f"RVTEST_TSBI_CSR_WRITE(CSR_HTVAL, {random_int(32, signed=False):#x})",
                        test_data.add_testcase(f"{mode}_{instr.replace('.', '_')}_{access}", coverpoint, COVERGROUP),
                        f"{instr} x{rd}, (x{addr})",
                    ]
                )
        if mode == "u":
            lines.append("RVTEST_TSBI_GOTO_SMODE")
        lines.append(write_sigupd(rd, test_data))
    lines.extend([f"LI(x{rd}, HSTATUS_HU)", f"csrc hstatus, x{rd}"])
    test_data.int_regs.return_registers([addr, rd])
    return [*lines, *guest_translation_teardown(test_data), f"#endif // {TWO_STAGE_GATE}"]


#####################################################################
# Misaligned accesses that straddle into an unmapped guest page
#####################################################################

# Bytes of a word access at the end of a page that fall in the next page
_STRADDLE_OFFSET = 2


def _straddle_va(vs: SvMode) -> int:
    """A word two bytes below vs.data_va, so the access continues into the page at vs.data_va."""
    return int(vs.data_va, 16) - _STRADDLE_OFFSET


def _straddle_leaves(
    g: SvMode, vs: SvMode, user: bool, regs: tuple[int, int, int], page: str = "shtvala_straddle_page"
) -> list[str]:
    """A VS-stage superpage leaf at vs.data_va to the guest physical superpage of g.data_va, where a G-stage kilopage
    maps the page below g.data_va to page and leaves g.data_va unmapped."""
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
            physical_address=page,
            regs=regs,
        ),
    ]


def _hlsv_straddle_tests(test_data: TestData) -> list[str]:
    """hlv.w and hsv.w from HS-mode with hstatus.SPVP = 0 and from U-mode, with hstatus.HU = 1, across the end of the
    mapped guest page.

    A faulting hlv.w leaves rd unchanged.  After each guest-page fault in HS-mode, record htinst's Addr. Offset, the
    difference between the faulting virtual address in stval and the original virtual address (hypervisor.adoc
    H_tinst_addr_offset), on harts that perform misaligned accesses.  htinst may instead be zero, which records the
    expected offset.  U-mode cannot read htinst, and the trap record holds it.
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
            f"LI(x{rd}, HSTATUS_HU)",
            f"csrs hstatus, x{rd}",
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
                # The Addr. Offset applies to the guest-page fault; without misaligned support the access raises
                # address-misaligned, whose htinst the trap record checks
                "#ifdef UDB_MISALIGNED_LDST",
                f"csrr x{tinst}, htinst",
                f"seqz x{zero}, x{tinst}",
                f"neg x{zero}, x{zero}",
                f"andi x{zero}, x{zero}, {_STRADDLE_OFFSET}",
                f"srli x{tinst}, x{tinst}, 15",
                f"andi x{tinst}, x{tinst}, 0x1F",
                f"or x{tinst}, x{tinst}, x{zero}",
                write_sigupd(tinst, test_data),
                "#endif",
            ]
        )
    lines.extend([f"LI(x{rd}, 42)", "RVTEST_TSBI_GOTO_UMODE"])
    for instr, coverpoint in (
        ("hlv.w", "cp_hlv_straddle_guest_page_fault"),
        ("hsv.w", "cp_hsv_straddle_guest_page_fault"),
    ):
        lines.extend(
            [
                f"RVTEST_TSBI_CSR_WRITE(CSR_HTVAL, {random_int(32, signed=False):#x})",
                test_data.add_testcase(f"u_{instr.replace('.', '_')}", coverpoint, COVERGROUP),
                f"{instr} x{rd}, (x{addr})",
            ]
        )
    lines.extend(
        ["RVTEST_TSBI_GOTO_SMODE", write_sigupd(rd, test_data), f"LI(x{rd}, HSTATUS_HU)", f"csrc hstatus, x{rd}"]
    )
    test_data.int_regs.return_registers([addr, rd, tinst, zero])
    return [*lines, *guest_translation_teardown(test_data), f"#endif // {TWO_STAGE_GATE}"]


def _fetch_straddle_tests(test_data: TestData, tc: TestChunk) -> list[str]:
    """A fetch in VS-mode and VU-mode of a 32-bit instruction two bytes below the end of a mapped guest page whose
    successor has an unmapped guest physical address.  The first half of an addi is in the last two bytes of
    shtvala_fetch_page, so the fetch faults on the second half: stval holds the page-boundary address, htval its guest
    physical address and sepc the start of the instruction.  Only with Zca, so that jalr can reach a pc that is not
    4-byte aligned."""
    tc.raw_data.extend(
        [
            "#ifdef ZCA_SUPPORTED",
            *guest_table_data(),
            ".p2align 12",
            "shtvala_fetch_page:",
            f".zero {4096 - _STRADDLE_OFFSET}",
            ".half 0x0013    # first half of addi x0, x0, 0",
            "#endif",
        ]
    )

    def leaves(g: SvMode, vs: SvMode, user: bool, regs: tuple[int, int, int]) -> list[str]:
        return _straddle_leaves(g, vs, user, regs, page="shtvala_fetch_page")

    faults = [("straddle", "cp_instr_straddle_guest_page_fault", "jalr", _straddle_va)]
    return [
        comment_banner(
            "cp_instr_straddle_guest_page_fault",
            "In VS-mode and VU-mode, jump to a 32-bit instruction two bytes below the end of a mapped guest page whose\n"
            "successor has an unmapped guest physical address",
        ),
        "#ifdef ZCA_SUPPORTED",
        *guest_fault_tests(test_data, COVERGROUP, "htval", leaves, faults),
        "#endif",
    ]


def _straddle_tests(test_data: TestData, tc: TestChunk) -> list[str]:
    """Misaligned loads and stores whose second part has an unmapped guest physical address.

    A hart that performs misaligned accesses faults on the part in the next page, so stval holds the page-boundary
    address and htval its guest physical address, whichever way the hart splits the access.  A hart that does not
    perform them raises an address-misaligned exception instead, which the reference model also predicts.
    """
    faults = [
        ("straddle", "cp_load_straddle_guest_page_fault", "lw", _straddle_va),
        ("straddle", "cp_store_straddle_guest_page_fault", "sw", _straddle_va),
    ]
    tc.raw_data.extend([*guest_table_data(), ".p2align 12", "shtvala_straddle_page:", ".zero 4096"])
    return [
        comment_banner(
            "cp_{load,store,hlv,hsv}_straddle_guest_page_fault",
            "lw and sw in VS-mode and VU-mode, and hlv.w and hsv.w in HS-mode and U-mode, two bytes below the end of a\n"
            "mapped guest page whose successor has an unmapped guest physical address.  stval holds the page-boundary\n"
            "address, htval its guest physical address, and htinst's Addr. Offset their distance from the\n"
            "original address (hypervisor.adoc H_straddle)",
        ),
        *guest_fault_tests(test_data, COVERGROUP, "htval", _straddle_leaves, faults),
        *_hlsv_straddle_tests(test_data),
    ]
