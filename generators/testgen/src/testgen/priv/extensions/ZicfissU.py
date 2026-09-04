##################################
# priv/extensions/ZicfissU.py
#
# Zicfiss (shadow stack) U-mode test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicfissU test generator.

Covers the ZicfissU sheet of the simplified Zicfiss testplan: shadow stack
instruction behaviour, the ssp CSR, page/PMA behaviour, and the U-mode half of
the SSE enable chain.

The suite boots to U-mode. Each block makes a short T-SBI excursion to M-mode to set
up translation and the SS page, runs the testcases in U-mode, then makes a second
excursion to tear translation down and returns to U-mode. Privileged CSR accesses made
from inside the U-mode body go through T-SBI instead. See ZicfissCommon for the x1/x5
and encoding-width constraints.
"""

from __future__ import annotations

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfissCommon import (
    GOTO_SMODE,
    GOTO_UMODE,
    PTE_SS,
    both_xlens,
    code_end_page_align,
    guard_ss_page,
    map_zicfiss_pages,
    page_table_data_section,
    priv_csr,
    restore_link_regs,
    satp_on_from_umode,
    save_link_regs,
    set_envcfg_sse,
    set_sum,
    ss_insn,
    teardown_vm,
    va_for,
    va_unmapped,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "ZicfissU_cg"

# (mnemonic, compressed, short name) for the three push and three pop encodings.
_PUSH_FORMS = [
    ("sspush x1", False, "sspush_x1"),
    ("sspush x5", False, "sspush_x5"),
    ("c.sspush x1", True, "c_sspush_x1"),
]
_POP_FORMS = [
    ("sspopchk x1", False, "sspopchk_x1"),
    ("sspopchk x5", False, "sspopchk_x5"),
    ("c.sspopchk x5", True, "c_sspopchk_x5"),
]


def _umode_prologue(
    test_data: TestData, xlen: int, *, menvcfg: int = 1, senvcfg: int = 1, ss_perms: str = PTE_SS
) -> list[str]:
    """S-mode setup: translation, page mappings, SSE chain, then down to U-mode.

    Nothing here touches M-mode. The test steps up to S-mode through T-SBI, and the one
    M-mode CSR it needs -- menvcfg -- goes through a T-SBI call, which the handler services
    on the test's behalf. medeleg is deliberately left at its boot value, so exceptions stay
    delegated to the S-mode handler.

    The page tables are built with translation still off and satp is written last, so the
    hart never runs against a half-built chain. The image map splits user from supervisor
    pages at rvtest_code_end and rvtest_data_begin, which is what keeps the S-mode handler
    fetchable while the test body is user-executable; see ZicfissCommon._umode_image_map.
    """
    return [
        GOTO_SMODE,
        *map_zicfiss_pages(xlen, ss_perms=ss_perms),
        *set_sum(),
        *set_envcfg_sse("menvcfg", menvcfg, test_data, mode="S"),
        *set_envcfg_sse("senvcfg", senvcfg, test_data, mode="S"),
        GOTO_UMODE,
        *satp_on_from_umode(xlen),
    ]


# ---------------------------------------------------------------------------
# cp_ssp_access / cp_ssp_low_bits_ro_zero
# ---------------------------------------------------------------------------


def _generate_ssp_access(test_data: TestData) -> list[str]:
    coverpoint = "cp_ssp_access"

    def build(xlen: int) -> list[str]:
        ss_va, _, _ = va_for(xlen)
        val_reg, rd_reg = test_data.int_regs.get_registers(2)
        lines = _umode_prologue(test_data, xlen)

        # Read, write all-ones, write all-zeros, set all bits, clear all bits.
        for name, op, pattern in [
            ("ssp_csrrw_ones", "csrrw", "-1"),
            ("ssp_csrrw_zeros", "csrrw", "0"),
            ("ssp_csrrs_ones", "csrrs", "-1"),
            ("ssp_csrrs_zeros", "csrrs", "0"),
            ("ssp_csrrc_ones", "csrrc", "-1"),
            ("ssp_csrrc_zeros", "csrrc", "0"),
        ]:
            lines.extend(
                [
                    f"LI(x{val_reg}, {pattern})",
                    test_data.add_testcase(f"{name}_rv{xlen}", coverpoint, _CG),
                    f"{op} x{rd_reg}, ssp, x{val_reg}",
                    f"csrr x{rd_reg}, ssp   # read back",
                    write_sigupd(rd_reg, test_data),
                ]
            )

        # Immediate-form CSR ops so the csrrwi/csrrsi/csrrci bins fill.
        for name, op in [("ssp_csrrwi", "csrrwi"), ("ssp_csrrsi", "csrrsi"), ("ssp_csrrci", "csrrci")]:
            lines.extend(
                [
                    test_data.add_testcase(f"{name}_rv{xlen}", coverpoint, _CG),
                    f"{op} x{rd_reg}, ssp, 3   # bits [1:0] are read-only zero",
                    f"csrr x{rd_reg}, ssp",
                    write_sigupd(rd_reg, test_data),
                ]
            )

        # cp_ssp_low_bits_ro_zero: every CSR form x every value written into ssp[2:0].
        for low in range(8):
            for op, form in (
                ("csrrw", f"csrrw x{rd_reg}, ssp, x{val_reg}"),
                ("csrrs", f"csrrs x{rd_reg}, ssp, x{val_reg}"),
                ("csrrc", f"csrrc x{rd_reg}, ssp, x{val_reg}"),
                ("csrrwi", f"csrrwi x{rd_reg}, ssp, {low}"),
                ("csrrsi", f"csrrsi x{rd_reg}, ssp, {low}"),
                ("csrrci", f"csrrci x{rd_reg}, ssp, {low}"),
            ):
                lines.extend(
                    [
                        f"LI(x{val_reg}, {hex(ss_va | low)})",
                        test_data.add_testcase(f"ssp_low_bits_{op}_{low}_rv{xlen}", "cp_ssp_low_bits_ro_zero", _CG),
                        form,
                        f"csrr x{rd_reg}, ssp   # ssp low bits must read as zero",
                        write_sigupd(rd_reg, test_data),
                    ]
                )

        lines.extend(teardown_vm("U"))
        test_data.int_regs.return_registers([val_reg, rd_reg])
        return lines

    return [comment_banner(coverpoint, "ssp CSR access, width, and read-only-zero low bits"), *both_xlens(build)]


# ---------------------------------------------------------------------------
# cp_sspush / cp_sspopchk_match / cp_sspopchk_mismatch
# ---------------------------------------------------------------------------


def _generate_push_pop(test_data: TestData) -> list[str]:
    def build(xlen: int) -> list[str]:
        ss_va, _, _ = va_for(xlen)
        # Start ssp near the top of the SS page so pushes have room to grow down.
        ssp_top = ss_va + 0x800
        addr_reg, rd_reg = test_data.int_regs.get_registers(2)
        lines = _umode_prologue(test_data, xlen)
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        lines.extend(save_lines)

        # cp_sspush — each encoding pushes a known value and we read ssp back.
        for mnemonic, compressed, name in _PUSH_FORMS:
            reg = "x1" if "x1" in mnemonic else "x5"
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(ssp_top)})",
                    f"csrw ssp, x{addr_reg}",
                    f"LI({reg}, 0xA5A5A5A5)",
                    test_data.add_testcase(f"{name}_rv{xlen}", "cp_sspush", _CG),
                    *ss_insn(mnemonic, compressed=compressed),
                    f"csrr x{rd_reg}, ssp   # must be ssp_top - XLEN/8",
                    write_sigupd(rd_reg, test_data),
                ]
            )

        # cp_sspopchk_match — push then pop the same value back.
        for (push_m, push_c, _), (pop_m, pop_c, pop_name) in zip(_PUSH_FORMS, _POP_FORMS):
            reg = "x1" if "x1" in pop_m else "x5"
            push_reg = "x1" if "x1" in push_m else "x5"
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(ssp_top)})",
                    f"csrw ssp, x{addr_reg}",
                    f"LI({push_reg}, 0x5A5A5A5A)",
                    *ss_insn(push_m, compressed=push_c),
                    f"mv {reg}, {push_reg}   # matching value in the pop's link register",
                    test_data.add_testcase(f"{pop_name}_match_rv{xlen}", "cp_sspopchk_match", _CG),
                    *ss_insn(pop_m, compressed=pop_c),
                    f"csrr x{rd_reg}, ssp   # must be back at ssp_top",
                    write_sigupd(rd_reg, test_data),
                ]
            )

        # cp_sspopchk_mismatch — corrupt the link register so the compare fails.
        for pop_m, pop_c, pop_name in _POP_FORMS:
            reg = "x1" if "x1" in pop_m else "x5"
            push_m, push_c = ("sspush x1", False) if reg == "x1" else ("sspush x5", False)
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(ssp_top)})",
                    f"csrw ssp, x{addr_reg}",
                    f"LI({reg}, 0x11111111)",
                    *ss_insn(push_m, compressed=push_c),
                    f"LI({reg}, 0x22222222)   # corrupt: no longer matches the shadow copy",
                    test_data.add_testcase(f"{pop_name}_mismatch_rv{xlen}", "cp_sspopchk_mismatch", _CG),
                    *ss_insn(pop_m, compressed=pop_c),
                ]
            )
            # Edge cases: differ from the shadow copy in exactly one bit, at each end.
            for edge, delta in (("bit0", 1), (f"bit{xlen - 1}", 1 << (xlen - 1))):
                lines.extend(
                    [
                        f"LI(x{addr_reg}, {hex(ssp_top)})",
                        f"csrw ssp, x{addr_reg}",
                        f"LI({reg}, 0)",
                        *ss_insn(push_m, compressed=push_c),
                        f"LI({reg}, {hex(delta)})   # differs from the shadow copy in {edge} only",
                        test_data.add_testcase(f"{pop_name}_mismatch_{edge}_rv{xlen}", "cp_sspopchk_mismatch", _CG),
                        *ss_insn(pop_m, compressed=pop_c),
                    ]
                )

        lines.extend(restore_link_regs(save_x1, save_x5))
        lines.extend(teardown_vm("U"))
        test_data.int_regs.return_registers([addr_reg, rd_reg, save_x1, save_x5])
        return lines

    return [
        comment_banner("cp_sspush/cp_sspopchk", "Shadow stack push and pop, matching and mismatching"),
        *both_xlens(build),
    ]


# ---------------------------------------------------------------------------
# cp_sspopchk_fault_priority
# ---------------------------------------------------------------------------


def _generate_fault_priority(test_data: TestData) -> list[str]:
    """A memory fault on the pop outranks the software-check exception.

    ssp is pointed at a deliberately unmapped VA *and* the link register is given a
    value that would not match, so both faults are live at once. Only the memory
    fault may be reported. The walk of the unmapped VA fails at level 1, so no leaf
    PTE with the SS encoding is read — this section is not gated on the reference
    model's SS page support.
    """
    coverpoint = "cp_sspopchk_fault_priority"

    def build(xlen: int) -> list[str]:
        bad_va = va_unmapped(xlen)
        addr_reg = test_data.int_regs.get_register()
        lines = _umode_prologue(test_data, xlen)
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        lines.extend(save_lines)

        for mnemonic, compressed, name in _POP_FORMS:
            reg = "x1" if "x1" in mnemonic else "x5"
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(bad_va)})",
                    f"csrw ssp, x{addr_reg}   # unmapped: the pop's load will fault",
                    f"LI({reg}, 0xNOTMATCH)".replace("0xNOTMATCH", "0x0BADF00D"),
                    test_data.add_testcase(f"{name}_fault_priority_rv{xlen}", coverpoint, _CG),
                    *ss_insn(mnemonic, compressed=compressed),
                ]
            )

        lines.extend(restore_link_regs(save_x1, save_x5))
        lines.extend(teardown_vm("U"))
        test_data.int_regs.return_registers([addr_reg, save_x1, save_x5])
        return lines

    return [
        comment_banner(coverpoint, "Memory fault on the pop outranks the software-check exception"),
        *both_xlens(build),
    ]


# ---------------------------------------------------------------------------
# cp_ss_call_return
# ---------------------------------------------------------------------------


def _generate_call_return(test_data: TestData) -> list[str]:
    """Nested non-leaf prologue/epilogue round trip, emitted straight-line (no asm loops)."""
    coverpoint = "cp_ss_call_return"

    def build(xlen: int) -> list[str]:
        ss_va, _, _ = va_for(xlen)
        ssp_top = ss_va + 0x800
        addr_reg, rd_reg = test_data.int_regs.get_registers(2)
        lines = _umode_prologue(test_data, xlen)
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        lines.extend(save_lines)

        lines.extend([f"LI(x{addr_reg}, {hex(ssp_top)})", f"csrw ssp, x{addr_reg}"])

        # Three nested prologues: each spills the link register to the shadow stack.
        for depth in range(3):
            lines.extend(
                [
                    f"LI(x1, {hex(0xC0DE0000 + depth)})   # simulated return address at depth {depth}",
                    test_data.add_testcase(f"call_prologue_depth{depth}_rv{xlen}", coverpoint, _CG),
                    *ss_insn("sspush x1"),
                ]
            )
        # Three matching epilogues, unwinding in reverse order.
        for depth in reversed(range(3)):
            lines.extend(
                [
                    f"LI(x1, {hex(0xC0DE0000 + depth)})   # link register reloaded from the regular stack",
                    test_data.add_testcase(f"return_epilogue_depth{depth}_rv{xlen}", coverpoint, _CG),
                    *ss_insn("sspopchk x1"),
                ]
            )
        lines.extend([f"csrr x{rd_reg}, ssp   # must be back at ssp_top", write_sigupd(rd_reg, test_data)])

        # Subverted return address: the epilogue compare must catch it.
        lines.extend(
            [
                f"LI(x{addr_reg}, {hex(ssp_top)})",
                f"csrw ssp, x{addr_reg}",
                "LI(x1, 0xC0DE1234)",
                *ss_insn("sspush x1"),
                "LI(x1, 0xBAD00BAD)   # attacker-supplied return address",
                test_data.add_testcase(f"return_subverted_rv{xlen}", coverpoint, _CG),
                *ss_insn("sspopchk x1"),
            ]
        )

        lines.extend(restore_link_regs(save_x1, save_x5))
        lines.extend(teardown_vm("U"))
        test_data.int_regs.return_registers([addr_reg, rd_reg, save_x1, save_x5])
        return lines

    return [comment_banner(coverpoint, "Non-leaf prologue/epilogue round trip across nested depth"), *both_xlens(build)]


# ---------------------------------------------------------------------------
# cp_ssrdp
# ---------------------------------------------------------------------------


def _generate_ssrdp(test_data: TestData) -> list[str]:
    coverpoint = "cp_ssrdp"

    def build(xlen: int) -> list[str]:
        ss_va, _, _ = va_for(xlen)
        ssp_top = ss_va + 0x800
        addr_reg, rd_reg = test_data.int_regs.get_registers(2)
        lines = _umode_prologue(test_data, xlen)
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        lines.extend(save_lines)

        lines.extend(
            [
                f"LI(x{addr_reg}, {hex(ssp_top)})",
                f"csrw ssp, x{addr_reg}",
                test_data.add_testcase(f"ssrdp_reads_ssp_rv{xlen}", coverpoint, _CG),
                *ss_insn(f"ssrdp x{rd_reg}"),
                write_sigupd(rd_reg, test_data),
                "LI(x1, 0xFEEDFACE)",
                *ss_insn("sspush x1"),
                test_data.add_testcase(f"ssrdp_after_push_rv{xlen}", coverpoint, _CG),
                *ss_insn(f"ssrdp x{rd_reg}   # must equal ssp after the push"),
                write_sigupd(rd_reg, test_data),
            ]
        )

        lines.extend(restore_link_regs(save_x1, save_x5))
        lines.extend(teardown_vm("U"))
        test_data.int_regs.return_registers([addr_reg, rd_reg, save_x1, save_x5])
        return lines

    return [comment_banner(coverpoint, "SSRDP moves ssp into rd"), *both_xlens(build)]


# ---------------------------------------------------------------------------
# cp_ssamoswap
# ---------------------------------------------------------------------------


def _generate_ssamoswap(test_data: TestData) -> list[str]:
    coverpoint = "cp_ssamoswap"

    def build(xlen: int) -> list[str]:
        ss_va, _, _ = va_for(xlen)
        addr_reg, rd_reg, rs2_reg, seed_reg = test_data.int_regs.get_registers(4)
        lines = _umode_prologue(test_data, xlen)

        # RV64 SSAMOSWAP.W: sign-extension (MSB 0 and 1) and the rs2[63:32]-ignored case.
        cases = [("msb0", "0x7FFFFFFF", "0x12345678"), ("msb1", "0x80000000", "0xFFFFFFFF")]
        if xlen == 64:
            cases.append(("rs2_upper_ignored", "0x12345678", "0xAAAAAAAAFFFFFFFF"))

        for name, mem_val, rs2_val in cases:
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(ss_va)})",
                    f"LI(x{seed_reg}, {mem_val})",
                    f"csrw ssp, x{addr_reg}",
                    # Seed the SS page through a shadow stack store: ordinary stores to an
                    # SS page raise an access fault, so the seeding swap is the only way to
                    # give the location under test a defined value.
                    *ss_insn(f"ssamoswap.w x{rd_reg}, x{seed_reg}, (x{addr_reg})"),
                    f"LI(x{rs2_reg}, {rs2_val})",
                    test_data.add_testcase(f"ssamoswap_w_{name}_rv{xlen}", coverpoint, _CG),
                    *ss_insn(f"ssamoswap.w x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
                    write_sigupd(rd_reg, test_data),
                ]
            )

        if xlen == 64:
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(ss_va)})",
                    f"LI(x{rs2_reg}, 0xAABBCCDDEEFF0011)",
                    test_data.add_testcase(f"ssamoswap_d_rv{xlen}", coverpoint, _CG),
                    *ss_insn(f"ssamoswap.d x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
                    write_sigupd(rd_reg, test_data),
                ]
            )

        # cp_ssamoswap_aqrl: all four ordering-bit encodings.
        for aq, rl in ((0, 0), (0, 1), (1, 0), (1, 1)):
            suffix = "".join(s for s, f in ((".aq", aq), (".rl", rl)) if f)
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(ss_va)})",
                    f"LI(x{rs2_reg}, 0x5A5A5A5A)",
                    test_data.add_testcase(f"ssamoswap_w_aq{aq}_rl{rl}_rv{xlen}", "cp_ssamoswap_aqrl", _CG),
                    *ss_insn(f"ssamoswap.w{suffix} x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
                ]
            )

        # cp_ssamoswap_reg_edges: rd=x0, rs2=x0, rd==rs1.
        for name, form in (
            ("rd_x0", f"ssamoswap.w x0, x{rs2_reg}, (x{addr_reg})"),
            ("rs2_x0", f"ssamoswap.w x{rd_reg}, x0, (x{addr_reg})"),
            ("rd_eq_rs1", f"ssamoswap.w x{addr_reg}, x{rs2_reg}, (x{addr_reg})"),
        ):
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(ss_va)})",
                    f"LI(x{rs2_reg}, 0x3C3C3C3C)",
                    test_data.add_testcase(f"ssamoswap_w_{name}_rv{xlen}", "cp_ssamoswap_reg_edges", _CG),
                    *ss_insn(form),
                ]
            )

        lines.extend(teardown_vm("U"))
        test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, seed_reg])
        return lines

    return [
        comment_banner(coverpoint, "SSAMOSWAP.W/.D swap, sign-extension, ordering bits and register edges"),
        *both_xlens(build),
    ]


# ---------------------------------------------------------------------------
# cp_ss_address_alignment
# ---------------------------------------------------------------------------


def _generate_alignment(test_data: TestData) -> list[str]:
    """Sweep addr[2:0] over all 8 values rather than enumerating aligned/misaligned cases."""

    def build(xlen: int) -> list[str]:
        ss_va, _, _ = va_for(xlen)
        base = ss_va + 0x400
        addr_reg, rd_reg, rs2_reg = test_data.int_regs.get_registers(3)
        lines = _umode_prologue(test_data, xlen)
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        lines.extend(save_lines)

        # ssp alignment sweep for push and pop.
        for offset in range(8):
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(base + offset)})",
                    f"csrw ssp, x{addr_reg}",
                    "LI(x1, 0xDEADBEEF)",
                    test_data.add_testcase(f"sspush_ssp_off{offset}_rv{xlen}", "cp_ss_address_alignment_ssp", _CG),
                    *ss_insn("sspush x1"),
                ]
            )
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(base + offset)})",
                    f"csrw ssp, x{addr_reg}",
                    test_data.add_testcase(f"sspopchk_ssp_off{offset}_rv{xlen}", "cp_ss_address_alignment_pop", _CG),
                    *ss_insn("sspopchk x1"),
                ]
            )

        # SSAMOSWAP address alignment sweep.
        for offset in range(8):
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(base + offset)})",
                    f"LI(x{rs2_reg}, 0x11223344)",
                    test_data.add_testcase(f"ssamoswap_w_off{offset}_rv{xlen}", "cp_ss_address_alignment_swap", _CG),
                    *ss_insn(f"ssamoswap.w x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
                ]
            )
            if xlen == 64:
                lines.extend(
                    [
                        f"LI(x{addr_reg}, {hex(base + offset)})",
                        test_data.add_testcase(
                            f"ssamoswap_d_off{offset}_rv{xlen}", "cp_ss_address_alignment_swap", _CG
                        ),
                        *ss_insn(f"ssamoswap.d x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
                    ]
                )

        lines.extend(restore_link_regs(save_x1, save_x5))
        lines.extend(teardown_vm("U"))
        test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, save_x1, save_x5])
        return lines

    return [
        comment_banner("cp_ss_address_alignment", "ssp and SSAMOSWAP address alignment sweep over addr[2:0]"),
        *both_xlens(build),
    ]


# ---------------------------------------------------------------------------
# cp_ss_instr_target_page — SS instructions against the wrong kind of page
# ---------------------------------------------------------------------------


def _generate_target_page(test_data: TestData) -> list[str]:
    coverpoint = "cp_ss_instr_target_page"

    def build(xlen: int) -> list[str]:
        _, rw_va, ro_va = va_for(xlen)
        addr_reg, rd_reg, rs2_reg = test_data.int_regs.get_registers(3)
        lines = _umode_prologue(test_data, xlen)
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        lines.extend(save_lines)

        # Point ssp at a read/write page (xwr=011) and a read-only page (xwr=001).
        # Aim at the MIDDLE of each page: sspush decrements ssp before storing, so a
        # pointer at the page base would push into the preceding page instead.
        for page_name, va in [("rw_page", rw_va + 0x800), ("ro_page", ro_va + 0x800)]:
            for mnemonic, compressed, name in _PUSH_FORMS + _POP_FORMS:
                reg = "x1" if "x1" in mnemonic else "x5"
                lines.extend(
                    [
                        f"LI(x{addr_reg}, {hex(va)})",
                        f"csrw ssp, x{addr_reg}",
                        f"LI({reg}, 0xDEADBEEF)",
                        test_data.add_testcase(f"{name}_on_{page_name}_rv{xlen}", coverpoint, _CG),
                        *ss_insn(mnemonic, compressed=compressed),
                    ]
                )
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(va)})",
                    f"LI(x{rs2_reg}, 0x11223344)",
                    test_data.add_testcase(f"ssamoswap_w_on_{page_name}_rv{xlen}", coverpoint, _CG),
                    *ss_insn(f"ssamoswap.w x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
                ]
            )
            if xlen == 64:
                lines.extend(
                    [
                        f"LI(x{addr_reg}, {hex(va)})",
                        test_data.add_testcase(f"ssamoswap_d_on_{page_name}_rv{xlen}", coverpoint, _CG),
                        *ss_insn(f"ssamoswap.d x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
                    ]
                )

        lines.extend(restore_link_regs(save_x1, save_x5))
        lines.extend(teardown_vm("U"))
        test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, save_x1, save_x5])
        return lines

    return [comment_banner(coverpoint, "SS instructions targeting non-SS page types"), *both_xlens(build)]


# ---------------------------------------------------------------------------
# cp_ss_instr_target_page — MXR and pte.U axes
# ---------------------------------------------------------------------------


def _generate_target_page_mxr_u(test_data: TestData) -> list[str]:
    """Sweep sstatus.MXR and the page's U bit against the SS instructions."""
    coverpoint = "cp_ss_instr_target_page"
    lines: list[str] = [comment_banner(coverpoint, "MXR and pte.U axes on the shadow stack page")]

    for u_bit in (0, 1):
        perms = "PTE_D | PTE_A | PTE_W | PTE_V" + (" | PTE_U" if u_bit else "")

        def build(xlen: int, perms: str = perms, u_bit: int = u_bit) -> list[str]:
            ss_va, _, _ = va_for(xlen)
            ssp_top = ss_va + 0x800
            addr_reg, mask_reg = test_data.int_regs.get_registers(2)
            # user=False keeps the identity map supervisor-only; the SS page's own U bit
            # is what is being swept here.
            block = [
                GOTO_SMODE,
                *map_zicfiss_pages(xlen, ss_perms=perms, user=True),
                *set_sum(),
                *set_envcfg_sse("menvcfg", 1, test_data, mode="S"),
                *set_envcfg_sse("senvcfg", 1, test_data, mode="S"),
                GOTO_UMODE,
                *satp_on_from_umode(xlen),
            ]
            save_x1, save_x5, save_lines = save_link_regs(test_data)
            block.extend(save_lines)
            for mxr in (0, 1):
                block.extend(
                    [
                        f"LI(x{mask_reg}, {hex(1 << 19)})   # sstatus.MXR",
                        priv_csr(f"{'csrs' if mxr else 'csrc'} sstatus, x{mask_reg}", "U"),
                    ]
                )
                for mnemonic, compressed, name in _PUSH_FORMS + _POP_FORMS:
                    reg = "x1" if "x1" in mnemonic else "x5"
                    block.extend(
                        [
                            f"LI(x{addr_reg}, {hex(ssp_top)})",
                            f"csrw ssp, x{addr_reg}",
                            f"LI({reg}, 0x4D4D4D4D)",
                            test_data.add_testcase(f"{name}_u{u_bit}_mxr{mxr}_rv{xlen}", coverpoint, _CG),
                            *ss_insn(mnemonic, compressed=compressed),
                        ]
                    )
            block.extend(restore_link_regs(save_x1, save_x5))
            block.extend(teardown_vm("U"))
            test_data.int_regs.return_registers([addr_reg, mask_reg, save_x1, save_x5])
            return block

        lines.append(f"# --- pte.U = {u_bit} ---")
        lines.extend(both_xlens(build))
    return lines


# ---------------------------------------------------------------------------
# cp_ss_page_crossing
# ---------------------------------------------------------------------------


def _generate_page_crossing(test_data: TestData) -> list[str]:
    """A push at a page base writes into the preceding page; a pop reads its own page."""
    coverpoint = "cp_ss_page_crossing"

    def build(xlen: int) -> list[str]:
        ss_va, rw_va, _ = va_for(xlen)
        addr_reg = test_data.int_regs.get_register()
        lines = _umode_prologue(test_data, xlen)
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        lines.extend(save_lines)

        # Case A: ssp at the SS page base, so ssp-XLEN/8 lands on the unmapped page below.
        # Case B: ssp on the ordinary RW page, so ssp-XLEN/8 lands back on the SS page.
        for case, va in (("a_base", ss_va), ("b_below_valid", rw_va)):
            for mnemonic, compressed, name in _PUSH_FORMS + _POP_FORMS:
                reg = "x1" if "x1" in mnemonic else "x5"
                lines.extend(
                    [
                        f"LI(x{addr_reg}, {hex(va)})",
                        f"csrw ssp, x{addr_reg}",
                        f"LI({reg}, 0xC0DECAFE)",
                        test_data.add_testcase(f"{name}_{case}_rv{xlen}", coverpoint, _CG),
                        *ss_insn(mnemonic, compressed=compressed),
                    ]
                )

        lines.extend(restore_link_regs(save_x1, save_x5))
        lines.extend(teardown_vm("U"))
        test_data.int_regs.return_registers([addr_reg, save_x1, save_x5])
        return lines

    return [comment_banner(coverpoint, "Shadow stack accesses that straddle a page boundary"), *both_xlens(build)]


# ---------------------------------------------------------------------------
# cp_ss_page_ad_bits
# ---------------------------------------------------------------------------


def _generate_page_ad_bits(test_data: TestData) -> list[str]:
    """D is required by the writing SS instructions but not by SSPOPCHK; A by all."""
    coverpoint = "cp_ss_page_ad_bits"
    lines: list[str] = [comment_banner(coverpoint, "PTE A/D bits on the shadow stack page")]

    for a_bit, d_bit in ((0, 0), (1, 0), (0, 1), (1, 1)):
        perms = " | ".join(["PTE_W", "PTE_V"] + (["PTE_A"] if a_bit else []) + (["PTE_D"] if d_bit else []))

        def build(xlen: int, perms: str = perms, a_bit: int = a_bit, d_bit: int = d_bit) -> list[str]:
            ss_va, _, _ = va_for(xlen)
            ssp_top = ss_va + 0x800
            addr_reg = test_data.int_regs.get_register()
            block = _umode_prologue(test_data, xlen, ss_perms=perms)
            save_x1, save_x5, save_lines = save_link_regs(test_data)
            block.extend(save_lines)
            for mnemonic, compressed, name in _PUSH_FORMS + _POP_FORMS:
                reg = "x1" if "x1" in mnemonic else "x5"
                block.extend(
                    [
                        f"LI(x{addr_reg}, {hex(ssp_top)})",
                        f"csrw ssp, x{addr_reg}",
                        f"LI({reg}, 0xADADADAD)",
                        test_data.add_testcase(f"{name}_a{a_bit}_d{d_bit}_rv{xlen}", coverpoint, _CG),
                        *ss_insn(mnemonic, compressed=compressed),
                    ]
                )
            block.extend(restore_link_regs(save_x1, save_x5))
            block.extend(teardown_vm("U"))
            test_data.int_regs.return_registers([addr_reg, save_x1, save_x5])
            return block

        lines.append(f"# --- pte.A={a_bit}, pte.D={d_bit} ---")
        lines.extend(both_xlens(build))
    return lines


# ---------------------------------------------------------------------------
# cp_ss_non_idempotent
# ---------------------------------------------------------------------------


def _generate_non_idempotent(test_data: TestData) -> list[str]:
    """PBMT=IO makes the page non-idempotent, which SS instructions must reject."""
    coverpoint = "cp_ss_non_idempotent"
    lines: list[str] = [
        comment_banner(coverpoint, "Non-idempotent shadow stack memory via Svpbmt PBMT=IO"),
        "#ifdef SVPBMT_SUPPORTED",
    ]

    # pte.PBMT is bits [62:61]: 00 PMA, 01 NC, 10 IO.
    for tag, pbmt in (("pma", 0), ("nc", 1), ("io", 2)):

        def build(xlen: int, pbmt: int = pbmt, tag: str = tag) -> list[str]:
            if xlen != 64:
                return ["# Svpbmt requires RV64"]
            ss_va, _, _ = va_for(xlen)
            ssp_top = ss_va + 0x800
            addr_reg = test_data.int_regs.get_register()
            perms = f"PTE_D | PTE_A | PTE_W | PTE_V | ({pbmt} << 61)"
            block = _umode_prologue(test_data, xlen, ss_perms=perms)
            save_x1, save_x5, save_lines = save_link_regs(test_data)
            block.extend(save_lines)
            for mnemonic, compressed, name in _PUSH_FORMS + _POP_FORMS:
                reg = "x1" if "x1" in mnemonic else "x5"
                block.extend(
                    [
                        f"LI(x{addr_reg}, {hex(ssp_top)})",
                        f"csrw ssp, x{addr_reg}",
                        f"LI({reg}, 0x1D1D1D1D)",
                        test_data.add_testcase(f"{name}_pbmt_{tag}_rv{xlen}", coverpoint, _CG),
                        *ss_insn(mnemonic, compressed=compressed),
                    ]
                )
            block.extend(restore_link_regs(save_x1, save_x5))
            block.extend(teardown_vm("U"))
            test_data.int_regs.return_registers([addr_reg, save_x1, save_x5])
            return block

        lines.append(f"# --- pte.PBMT = {tag} ---")
        lines.extend(both_xlens(build))
    lines.append("#endif  // SVPBMT_SUPPORTED")
    return lines


# ---------------------------------------------------------------------------
# cp_ss_page_access — non-SS accessors against an SS page
# ---------------------------------------------------------------------------


def _generate_page_access(test_data: TestData) -> list[str]:
    def build(xlen: int) -> list[str]:
        ss_va, _, _ = va_for(xlen)
        addr_reg, data_reg = test_data.int_regs.get_registers(2)
        lines = _umode_prologue(test_data, xlen)
        lines.extend([f"LI(x{addr_reg}, {hex(ss_va)})"])

        stores = ["sb", "sh", "sw"] + (["sd"] if xlen == 64 else [])
        for mnemonic in stores:
            lines.extend(
                [
                    f"LI(x{data_reg}, 0xDEADBEEF)",
                    test_data.add_testcase(f"{mnemonic}_on_ss_page_rv{xlen}", "cp_ss_page_access_store", _CG),
                    f"{mnemonic} x{data_reg}, 0(x{addr_reg})",
                ]
            )

        loads = ["lb", "lh", "lw"] + (["ld"] if xlen == 64 else [])
        mxr_reg = test_data.int_regs.get_register()
        for mxr in (0, 1):
            lines.extend(
                [
                    f"LI(x{mxr_reg}, {hex(1 << 19)})   # sstatus.MXR",
                    priv_csr(f"{'csrs' if mxr else 'csrc'} sstatus, x{mxr_reg}", "U"),
                ]
            )
            for mnemonic in loads:
                lines.extend(
                    [
                        test_data.add_testcase(
                            f"{mnemonic}_on_ss_page_mxr{mxr}_rv{xlen}", "cp_ss_page_access_load", _CG
                        ),
                        f"{mnemonic} x{data_reg}, 0(x{addr_reg})",
                        write_sigupd(data_reg, test_data),
                    ]
                )
        test_data.int_regs.return_registers([mxr_reg])

        amos = ["amoswap.w", "amoadd.w"] + (["amoswap.d", "amoadd.d"] if xlen == 64 else [])
        for mnemonic in amos:
            lines.extend(
                [
                    f"LI(x{data_reg}, 0x1)",
                    test_data.add_testcase(
                        f"{mnemonic.replace('.', '_')}_on_ss_page_rv{xlen}", "cp_ss_page_access_amo", _CG
                    ),
                    f"{mnemonic} x{data_reg}, x{data_reg}, (x{addr_reg})",
                ]
            )

        # Cache-block ops are themselves gated by menvcfg/senvcfg CBIE/CBCFE/CBZE. Without
        # those enabled the CBO would trap on its own gating rather than on the SS page,
        # so enable them before the block. CBIE is bits [5:4], CBCFE bit 6, CBZE bit 7.
        cbo_reg = test_data.int_regs.get_register()
        lines.extend(
            [
                f"LI(x{cbo_reg}, 0xD0)   # CBIE=01, CBCFE=1, CBZE=1",
                tsbi_call(f"csrs menvcfg, x{cbo_reg}"),
                tsbi_call(f"csrs senvcfg, x{cbo_reg}"),
            ]
        )
        test_data.int_regs.return_registers([cbo_reg])
        # Zicbom/Zicboz are not in this suite's -march, so widen the arch locally.
        lines.extend(["#ifdef ZICBOM_SUPPORTED", ".option push", ".option arch, +zicbom"])
        for mnemonic in ["cbo.clean", "cbo.flush", "cbo.inval"]:
            lines.extend(
                [
                    test_data.add_testcase(
                        f"{mnemonic.replace('.', '_')}_on_ss_page_rv{xlen}", "cp_ss_page_access_cbo", _CG
                    ),
                    f"{mnemonic} (x{addr_reg})",
                ]
            )
        lines.extend([".option pop", "#endif  // ZICBOM_SUPPORTED"])
        lines.extend(["#ifdef ZICBOZ_SUPPORTED", ".option push", ".option arch, +zicboz"])
        lines.extend(
            [
                test_data.add_testcase(f"cbo_zero_on_ss_page_rv{xlen}", "cp_ss_page_access_cboz", _CG),
                f"cbo.zero (x{addr_reg})",
                ".option pop",
                "#endif  // ZICBOZ_SUPPORTED",
            ]
        )

        lines.extend(["#ifdef ZALRSC_SUPPORTED", ".option push", ".option arch, +a"])
        for mnemonic in ["lr.w", "sc.w"] + (["lr.d", "sc.d"] if xlen == 64 else []):
            form = (
                f"{mnemonic} x{data_reg}, (x{addr_reg})"
                if mnemonic.startswith("lr")
                else f"{mnemonic} x{data_reg}, x{data_reg}, (x{addr_reg})"
            )
            lines.extend(
                [
                    test_data.add_testcase(
                        f"{mnemonic.replace('.', '_')}_on_ss_page_rv{xlen}", "cp_ss_page_access_lrsc", _CG
                    ),
                    form,
                ]
            )
        lines.extend([".option pop", "#endif  // ZALRSC_SUPPORTED"])

        lines.extend(["#ifdef ZACAS_SUPPORTED", ".option push", ".option arch, +zacas"])
        for mnemonic in ["amocas.w"] + (["amocas.d"] if xlen == 64 else []):
            lines.extend(
                [
                    f"LI(x{data_reg}, 0x1)",
                    test_data.add_testcase(
                        f"{mnemonic.replace('.', '_')}_on_ss_page_rv{xlen}", "cp_ss_page_access_amocas", _CG
                    ),
                    f"{mnemonic} x{data_reg}, x{data_reg}, (x{addr_reg})",
                ]
            )
        lines.extend([".option pop", "#endif  // ZACAS_SUPPORTED"])

        lines.extend(teardown_vm("U"))
        test_data.int_regs.return_registers([addr_reg, data_reg])
        return lines

    return [comment_banner("cp_ss_page_access", "Non-SS accessors against an SS page"), *both_xlens(build)]


# ---------------------------------------------------------------------------
# cp_ssp_csr_gating_u / cp_ssamoswap_sse_gating
# ---------------------------------------------------------------------------


def _generate_sse_gating(test_data: TestData) -> list[str]:
    """Sweep the (menvcfg.SSE, senvcfg.SSE) enable chain from U-mode."""
    lines: list[str] = [comment_banner("cp_ssp_csr_gating_u", "SSE enable chain seen from U-mode")]

    for menvcfg, senvcfg in [(1, 1), (1, 0), (0, 1), (0, 0)]:
        tag = f"m{menvcfg}s{senvcfg}"

        def build(xlen: int, menvcfg: int = menvcfg, senvcfg: int = senvcfg, tag: str = tag) -> list[str]:
            ss_va, _, _ = va_for(xlen)
            addr_reg, rd_reg, rs2_reg = test_data.int_regs.get_registers(3)
            block = _umode_prologue(test_data, xlen, menvcfg=menvcfg, senvcfg=senvcfg)
            save_x1, save_x5, save_lines = save_link_regs(test_data)
            block.extend(save_lines)

            # ssp CSR access: allowed only when both bits are set, else illegal-instruction.
            block.append(f"LI(x{addr_reg}, {hex(ss_va)})")
            for op, form in (
                ("csrrw", f"csrrw x{rd_reg}, ssp, x{addr_reg}"),
                ("csrrs", f"csrrs x{rd_reg}, ssp, x{addr_reg}"),
                ("csrrc", f"csrrc x{rd_reg}, ssp, x{addr_reg}"),
                ("csrrwi", f"csrrwi x{rd_reg}, ssp, 1"),
                ("csrrsi", f"csrrsi x{rd_reg}, ssp, 1"),
                ("csrrci", f"csrrci x{rd_reg}, ssp, 1"),
            ):
                block.extend(
                    [
                        test_data.add_testcase(f"ssp_{op}_{tag}_rv{xlen}", "cp_ssp_csr_gating_u", _CG),
                        form,
                    ]
                )

            if menvcfg == 0 or senvcfg == 0:
                # SSAMOSWAP is AMO-encoded, so unlike the MOP-encoded instructions it
                # traps rather than becoming inert. The inert case is covered by
                # cp_ss_instr_inactive on ZicfissSm.
                block.extend(
                    [
                        f"LI(x{addr_reg}, {hex(ss_va)})",
                        f"LI(x{rs2_reg}, 0x11223344)",
                        test_data.add_testcase(f"ssamoswap_w_gated_{tag}_rv{xlen}", "cp_ssamoswap_sse_gating", _CG),
                        *ss_insn(f"ssamoswap.w x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
                    ]
                )
                if xlen == 64:
                    block.extend(
                        [
                            test_data.add_testcase(f"ssamoswap_d_gated_{tag}_rv{xlen}", "cp_ssamoswap_sse_gating", _CG),
                            *ss_insn(f"ssamoswap.d x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
                        ]
                    )

            block.extend(restore_link_regs(save_x1, save_x5))
            block.extend(teardown_vm("U"))
            test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, save_x1, save_x5])
            return block

        lines.append(f"# --- menvcfg.SSE={menvcfg}, senvcfg.SSE={senvcfg} ---")
        lines.extend(both_xlens(build))

    return lines


# ---------------------------------------------------------------------------
# Top-level generator
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "ZicfissU",
    required_extensions=["S", "U", "Zicfiss", "Zimop", "Zaamo", "Zcmop", "Zca", "Zicsr"],
)
def make_zicfissu(test_data: TestData) -> list[TestChunk]:
    """Generate the ZicfissU test suite."""
    test_chunks: list[TestChunk] = []

    # (section, reason) — reason is non-None when the section performs a translated
    # access through an SS page (pte.xwr=010) and is therefore gated on the reference
    # model handling that encoding. See ZicfissCommon.SS_PAGE_GUARD.
    sections: list[tuple[object, str | None]] = [
        (_generate_ssp_access, None),
        (_generate_push_pop, "sspush/sspopchk target the shadow stack page"),
        (_generate_fault_priority, None),
        (_generate_call_return, "prologue/epilogue push and pop through the shadow stack page"),
        (_generate_ssrdp, "reads ssp after a push to the shadow stack page"),
        (_generate_ssamoswap, "swaps against the shadow stack page"),
        (_generate_alignment, "sweeps ssp and SSAMOSWAP addresses inside the shadow stack page"),
        (_generate_target_page, None),
        (_generate_target_page_mxr_u, "MXR/U sweep against the shadow stack page"),
        (_generate_page_crossing, "pushes and pops straddling the shadow stack page boundary"),
        (_generate_page_ad_bits, "A/D bit sweep on the shadow stack page"),
        (_generate_non_idempotent, "PBMT sweep on the shadow stack page"),
        (_generate_page_access, "non-SS accessors aimed at the shadow stack page"),
        (_generate_sse_gating, None),
    ]
    for section, reason in sections:
        tc = test_data.begin_test_chunk()
        body = section(test_data)  # pyright: ignore[reportCallIssue]
        tc.code.extend(page_table_data_section())
        tc.code.extend(guard_ss_page(body, reason=reason) if reason else body)
        tc.code.extend(code_end_page_align())
        test_chunks.append(test_data.end_test_chunk())

    # Page-table and backing-page declarations, emitted once.

    return test_chunks
