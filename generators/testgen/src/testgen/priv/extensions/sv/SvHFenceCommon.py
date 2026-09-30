##################################
# priv/extensions/sv/SvHFenceCommon.py
#
# Guest address-translation fences: a changed VS-stage or G-stage leaf is used after the fence.
# David_Harris@hmc.edu 29 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Check that HFENCE.VVMA, HFENCE.GVMA, SFENCE.VMA in VS-mode and their Svinval forms remove stale translations.

Each case maps a guest virtual address through the VS-stage to guest physical page A and through the G-stage to
physical page A, and loads from it in VS-mode, which may cache the translation.  HS-mode then points the VS-stage
leaf at guest physical page B (mapped to physical page B), or the G-stage leaf of page A at physical page B, and
runs the fence.  The next VS-mode load must read page B.  A hart that caches nothing passes; only one that uses the
stale translation after the fence fails.

The fence operands are x0, the address (the guest virtual address, or the guest physical address >> 2), the
current ASID or VMID, and all ASIDMAX or VMIDMAX bits set, which a hart with fewer ASID or VMID bits ignores.
The cases run with every implemented vsatp.ASID and hgatp.VMID bit set.  The isolation cases load under ASID or
VMID 0, switch to the other ID, change the leaf, and fence only the new ID: the load under the new ID must not use
the translation cached for the old one.
"""

from typing import Literal, NamedTuple

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.generate import guest_translation_setup, guest_translation_teardown
from testgen.priv.extensions.sv.page_tables import PteFlags, SvMode, create_page_mapping, write_pte

Operand = Literal["x0", "va", "gpa", "asid", "asidmax", "vmid", "vmidmax"]


class Fence(NamedTuple):
    """A fence sequence: the leaf it removes, the mode it runs in, its instructions and its operand kinds."""

    name: str
    stage: Literal["vs", "g"]
    mode: Literal["HS", "VS"]
    instructions: tuple[str, ...]
    address: Operand
    identifier: Operand
    coverpoint: str


def _svinval(instruction: str) -> tuple[str, ...]:
    return ("sfence.w.inval", instruction, "sfence.inval.ir")


HFENCE_VVMA = Fence("hfence_vvma", "vs", "HS", ("hfence.vvma {rs1}, {rs2}",), "va", "asid", "cp_hfence_vvma")
HFENCE_GVMA = Fence("hfence_gvma", "g", "HS", ("hfence.gvma {rs1}, {rs2}",), "gpa", "vmid", "cp_hfence_gvma")
SFENCE_VMA_VS = Fence("sfence_vma", "vs", "VS", ("sfence.vma {rs1}, {rs2}",), "va", "asid", "cp_sfence_vma_vs")
HINVAL_VVMA = Fence("hinval_vvma", "vs", "HS", _svinval("hinval.vvma {rs1}, {rs2}"), "va", "asid", "cp_hinval_vvma")
HINVAL_GVMA = Fence("hinval_gvma", "g", "HS", _svinval("hinval.gvma {rs1}, {rs2}"), "gpa", "vmid", "cp_hinval_gvma")
SINVAL_VMA_VS = Fence("sinval_vma", "vs", "VS", _svinval("sinval.vma {rs1}, {rs2}"), "va", "asid", "cp_sinval_vma_vs")


class FenceCase(NamedTuple):
    """One testcase: its bin name, fence and operands, and the ID that changes between the two loads."""

    name: str
    fence: Fence
    rs1: Operand
    rs2: Operand
    switch: Literal["vmid", "asid"] | None = None


def _operand_cases(fence: Fence) -> list[FenceCase]:
    """x0 and the address in rs1, crossed with x0 and the current ID in rs2, and the address with all ID bits."""
    cases = [
        FenceCase(f"rs1_{rs1}_rs2_{rs2}", fence, rs1, rs2)
        for rs1 in ("x0", fence.address)
        for rs2 in ("x0", fence.identifier)
    ]
    maximum: Operand = "asidmax" if fence.identifier == "asid" else "vmidmax"
    return [*cases, FenceCase(f"rs1_{fence.address}_rs2_{maximum}", fence, fence.address, maximum)]


# The CSR and field mask of each ID
_ID_FIELDS = {"asid": ("vsatp", "SATP{xlen}_ASID"), "vmid": ("hgatp", "HGATP{xlen}_VMID")}


def _id_bits(xlen: int, identifier: Literal["vmid", "asid"], on: bool, reg: int) -> list[str]:
    """Set every implemented bit of vsatp.ASID or hgatp.VMID, or clear them all."""
    csr, mask = _ID_FIELDS[identifier]
    return [f"LI(x{reg}, {mask.format(xlen=xlen)})", f"{'csrs' if on else 'csrc'} {csr}, x{reg}"]


def _operand(operand: Operand, g: SvMode, reg: int, tmp: int) -> list[str]:
    """Load a guest physical address or ID operand into x{reg}.  The current ASID or VMID is read from vsatp or
    hgatp, using x{tmp}."""
    shift = 44 if g.xlen == 64 else 22
    if operand == "x0":
        return []
    if operand == "gpa":
        return [f"LI(x{reg}, ({g.data_va}) >> 2)"]
    csr, mask = _ID_FIELDS[operand.removesuffix("max")]
    mask = mask.format(xlen=g.xlen)
    if operand.endswith("max"):
        return [f"LI(x{reg}, ({mask}) >> {shift})"]
    return [
        f"LI(x{tmp}, {mask})",
        f"csrr x{reg}, {csr}",
        f"and x{reg}, x{reg}, x{tmp}",
        f"srli x{reg}, x{reg}, {shift}",
    ]


def _map_page_a(test_data: TestData, g: SvMode, vs: SvMode) -> list[str]:
    """Map vs.data_va to guest physical page A (g.data_va), page A to fence_page_a and page B to fence_page_b."""
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    regs = (pte, addr, tmp)
    lines = [
        *create_page_mapping(
            vs,
            leaf_level=0,
            leaf_flags=PteFlags(),
            virtual_address=vs.data_va,
            physical_address=g.data_va,
            regs=regs,
            pa_is_label=False,
        ),
        *create_page_mapping(
            g,
            leaf_level=0,
            leaf_flags=PteFlags(user=True),
            virtual_address=g.data_va,
            physical_address="fence_page_a",
            regs=regs,
        ),
        *write_pte(
            g,
            level=0,
            flags=PteFlags(user=True),
            virtual_address=f"({g.data_va} + 0x1000)",
            physical_address="fence_page_b",
            regs=regs,
        ),
    ]
    test_data.int_regs.return_registers(list(regs))
    return lines


def _move_to_page_b(test_data: TestData, g: SvMode, vs: SvMode, stage: str) -> list[str]:
    """Point the VS-stage leaf at guest physical page B, or the G-stage leaf of page A at fence_page_b."""
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    regs = (pte, addr, tmp)
    if stage == "vs":
        lines = write_pte(
            vs,
            level=0,
            flags=PteFlags(),
            virtual_address=vs.data_va,
            physical_address=f"({g.data_va} + 0x1000)",
            regs=regs,
            pa_is_label=False,
        )
    else:
        lines = write_pte(
            g, level=0, flags=PteFlags(user=True), virtual_address=g.data_va, physical_address="fence_page_b", regs=regs
        )
    test_data.int_regs.return_registers(list(regs))
    return lines


def _fence_case(test_data: TestData, g: SvMode, vs: SvMode, case: FenceCase, covergroup: str) -> list[str]:
    """Load through page A, move the leaf to page B, fence, and load again.  Both loads are checked."""
    fence = case.fence
    label = test_data.add_testcase(case.name, fence.coverpoint, covergroup)
    sig_label = label.removesuffix(":")
    tmp = test_data.int_regs.get_register()
    lines = [f"// {fence.name} with {case.name}"]
    for identifier in ("vmid", "asid"):
        lines.extend(_id_bits(g.xlen, identifier, identifier != case.switch, tmp))
    test_data.int_regs.return_register(tmp)
    lines.extend([*_map_page_a(test_data, g, vs), "hfence.gvma", "hfence.vvma"])
    va, data = test_data.int_regs.get_registers(2)
    lines.extend(
        [
            f"LI(x{va}, {vs.data_va})",
            "RVTEST_TSBI_GOTO_VSMODE",
            f"lw x{data}, 0(x{va})",
            "RVTEST_TSBI_GOTO_SMODE",
            write_sigupd(data, test_data, label=sig_label),
        ]
    )
    test_data.int_regs.return_register(data)
    lines.extend(_move_to_page_b(test_data, g, vs, fence.stage))
    rs1, rs2, tmp = test_data.int_regs.get_registers(3)
    if case.switch is not None:
        lines.extend(_id_bits(g.xlen, case.switch, True, tmp))
    operands = {
        "rs1": {"x0": "x0", "va": f"x{va}"}.get(case.rs1, f"x{rs1}"),
        "rs2": "x0" if case.rs2 == "x0" else f"x{rs2}",
    }
    lines.extend(
        [
            *(_operand(case.rs1, g, rs1, tmp) if case.rs1 == "gpa" else []),
            *_operand(case.rs2, g, rs2, tmp),
            *(["RVTEST_TSBI_GOTO_VSMODE"] if fence.mode == "VS" else []),
            label,
            *(instruction.format(**operands) for instruction in fence.instructions),
            *(["RVTEST_TSBI_GOTO_VSMODE"] if fence.mode == "HS" else []),
        ]
    )
    test_data.int_regs.return_registers([rs1, rs2, tmp])
    data = test_data.int_regs.get_register()
    lines.extend(
        [
            f"lw x{data}, 0(x{va})",
            "RVTEST_TSBI_GOTO_SMODE",
            write_sigupd(data, test_data, label=sig_label),
            "",
        ]
    )
    test_data.int_regs.return_registers([va, data])
    return lines


# VMID and ASID isolation: (fence, the ID that changes, fence operands)
ISOLATION_CASES = (
    FenceCase("vmid_switch", HFENCE_GVMA, "x0", "vmid", "vmid"),
    FenceCase("vmid_switch", HFENCE_VVMA, "x0", "x0", "vmid"),
    FenceCase("asid_switch", HFENCE_VVMA, "x0", "asid", "asid"),
    FenceCase("vmid_switch", SFENCE_VMA_VS, "x0", "x0", "vmid"),
)


def fence_chunk(
    test_data: TestData,
    g: SvMode,
    vs: SvMode,
    split_name: str,
    fences: tuple[Fence, ...],
    covergroup: str,
    isolation: tuple[FenceCase, ...] = (),
) -> TestChunk:
    """Return a chunk that runs every operand case of each fence in ``fences``, then the ``isolation`` cases.

    ``split_name`` names the chunk, and its testcases are in ``covergroup``.
    """
    names = ", ".join(dict.fromkeys(fence.coverpoint for fence in fences))
    chunk = test_data.begin_test_chunk(split_name)
    chunk.section_header = comment_banner(
        names,
        "Change a VS-stage or G-stage leaf, run the fence with x0, address, ID and all-ID-bits operands, and check\n"
        "that the next VS-mode load uses the new leaf",
    )
    chunk.raw_data.extend(
        [
            ".p2align 12",
            "fence_page_a:",
            ".4byte 0x0a0a0a0a",
            ".skip 4092",
            "fence_page_b:",
            ".4byte 0x0b0b0b0b",
            ".skip 4092",
        ]
    )
    code = guest_translation_setup(test_data, g, vs, "VSmode")
    for case in [*(case for fence in fences for case in _operand_cases(fence)), *isolation]:
        code.extend(_fence_case(test_data, g, vs, case, covergroup))
    code.extend(guest_translation_teardown(test_data))
    chunk.code.extend(code)
    return test_data.end_test_chunk()
