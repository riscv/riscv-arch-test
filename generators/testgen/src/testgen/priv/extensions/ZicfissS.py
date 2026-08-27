##################################
# priv/extensions/ZicfissS.py
#
# Zicfiss (shadow stack) S/HS-mode test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicfissS test generator.

Covers the ZicfissS sheet of the simplified Zicfiss testplan:

  1. S-specific gating — menvcfg.SSE alone gates S/HS. senvcfg.SSE is swept purely to
     prove it has NO effect at S/HS level, which no row of the source testplan tested.
  2. The S-mode re-run of the instruction behaviour, so the coverpoints crossed against
     priv_mode_s have stimulus.

Unlike ZicfissU, the identity map here does not carry PTE_U (S-mode executes from
supervisor pages), so traps can be delegated to the S-mode handler as normal.
"""

from __future__ import annotations

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfissCommon import (
    GOTO_SMODE,
    PTE_SS,
    both_xlens,
    guard_ss_page,
    map_zicfiss_pages,
    page_table_data_section,
    restore_link_regs,
    satp_setup,
    save_link_regs,
    set_envcfg_sse,
    ss_insn,
    teardown_vm,
    va_for,
    va_unmapped,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "ZicfissS_cg"

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


def _smode_prologue(
    test_data: TestData, xlen: int, *, menvcfg: int = 1, senvcfg: int = 1, ss_perms: str = PTE_SS
) -> list[str]:
    """M-mode setup then drop to S-mode. No PTE_U: these testcases run in S-mode."""
    return [
        *satp_setup(xlen),
        *map_zicfiss_pages(xlen, ss_perms=ss_perms, user=False),
        *set_envcfg_sse("menvcfg", menvcfg, test_data),
        *set_envcfg_sse("senvcfg", senvcfg, test_data),
        GOTO_SMODE,
    ]


# ---------------------------------------------------------------------------
# cp_ssp_csr_gating_s — senvcfg.SSE must NOT gate S/HS
# ---------------------------------------------------------------------------


def _generate_ssp_gating_s(test_data: TestData) -> list[str]:
    coverpoint = "cp_ssp_csr_gating_s"
    lines: list[str] = [
        comment_banner(coverpoint, "menvcfg.SSE gates ssp at S/HS; senvcfg.SSE must not"),
    ]

    for menvcfg in (0, 1):
        for senvcfg in (0, 1):
            tag = f"m{menvcfg}s{senvcfg}"

            def build(xlen: int, menvcfg: int = menvcfg, senvcfg: int = senvcfg, tag: str = tag) -> list[str]:
                rd_reg, val_reg = test_data.int_regs.get_registers(2)
                block = _smode_prologue(test_data, xlen, menvcfg=menvcfg, senvcfg=senvcfg)
                block.extend(
                    [
                        test_data.add_testcase(f"ssp_read_{tag}_rv{xlen}", coverpoint, _CG),
                        f"csrr x{rd_reg}, ssp",
                        f"LI(x{val_reg}, 0x3000)",
                        test_data.add_testcase(f"ssp_write_{tag}_rv{xlen}", coverpoint, _CG),
                        f"csrrw x{rd_reg}, ssp, x{val_reg}",
                        test_data.add_testcase(f"ssp_set_{tag}_rv{xlen}", coverpoint, _CG),
                        f"csrrs x{rd_reg}, ssp, x{val_reg}",
                        test_data.add_testcase(f"ssp_clr_{tag}_rv{xlen}", coverpoint, _CG),
                        f"csrrc x{rd_reg}, ssp, x{val_reg}",
                    ]
                )
                block.extend(teardown_vm())
                test_data.int_regs.return_registers([rd_reg, val_reg])
                return block

            lines.append(f"# --- menvcfg.SSE={menvcfg}, senvcfg.SSE={senvcfg} ---")
            lines.extend(both_xlens(build))

    return lines


# ---------------------------------------------------------------------------
# cp_ss_page_enc — the xwr=010 encoding, gated by menvcfg.SSE
# ---------------------------------------------------------------------------


def _generate_page_enc_s(test_data: TestData) -> list[str]:
    lines: list[str] = [
        comment_banner("cp_ss_page_enc", "pte.xwr=010 is an SS page when menvcfg.SSE=1, reserved when 0"),
    ]

    for menvcfg in (0, 1):

        def build(xlen: int, menvcfg: int = menvcfg) -> list[str]:
            ss_va, _, _ = va_for(xlen)
            ssp_top = ss_va + 0x800
            addr_reg, rd_reg = test_data.int_regs.get_registers(2)
            block = _smode_prologue(test_data, xlen, menvcfg=menvcfg)
            save_x1, save_x5, save_lines = save_link_regs(test_data)
            block.extend(save_lines)

            block.extend(
                [
                    f"LI(x{addr_reg}, {hex(ssp_top)})",
                    f"csrw ssp, x{addr_reg}",
                    "LI(x1, 0xC0FFEE11)",
                    test_data.add_testcase(f"ss_page_enc_push_men{menvcfg}_rv{xlen}", "cp_ss_page_enc", _CG),
                    *ss_insn("sspush x1"),
                ]
            )
            # An ordinary load from an SS page is permitted; an ordinary store is not.
            loads = ["lb", "lh", "lw"] + (["ld"] if xlen == 64 else [])
            for m in loads:
                block.extend(
                    [
                        test_data.add_testcase(f"{m}_ss_page_men{menvcfg}_rv{xlen}", "cp_ss_page_enc_load", _CG),
                        f"{m} x{rd_reg}, 0(x{addr_reg})",
                    ]
                )
            stores = ["sb", "sh", "sw"] + (["sd"] if xlen == 64 else [])
            for m in stores:
                block.extend(
                    [
                        f"LI(x{rd_reg}, 0x55)",
                        test_data.add_testcase(f"{m}_ss_page_men{menvcfg}_rv{xlen}", "cp_ss_page_enc_store", _CG),
                        f"{m} x{rd_reg}, 0(x{addr_reg})",
                    ]
                )

            block.extend(restore_link_regs(save_x1, save_x5))
            block.extend(teardown_vm())
            test_data.int_regs.return_registers([addr_reg, rd_reg, save_x1, save_x5])
            return block

        lines.append(f"# --- menvcfg.SSE={menvcfg} ---")
        lines.extend(both_xlens(build))

    return lines


# ---------------------------------------------------------------------------
# S-mode re-run of the instruction behaviour
# ---------------------------------------------------------------------------


def _generate_instr_s(test_data: TestData) -> list[str]:
    def build(xlen: int) -> list[str]:
        ss_va, _, _ = va_for(xlen)
        ssp_top = ss_va + 0x800
        addr_reg, rd_reg, rs2_reg = test_data.int_regs.get_registers(3)
        lines = _smode_prologue(test_data, xlen)
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        lines.extend(save_lines)

        for mnemonic, compressed, name in _PUSH_FORMS:
            reg = "x1" if "x1" in mnemonic else "x5"
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(ssp_top)})",
                    f"csrw ssp, x{addr_reg}",
                    f"LI({reg}, 0xA5A5A5A5)",
                    test_data.add_testcase(f"{name}_s_rv{xlen}", "cp_sspush_s", _CG),
                    *ss_insn(mnemonic, compressed=compressed),
                    f"csrr x{rd_reg}, ssp",
                    write_sigupd(rd_reg, test_data),
                ]
            )

        for (push_m, push_c, _), (pop_m, pop_c, pop_name) in zip(_PUSH_FORMS, _POP_FORMS):
            reg = "x1" if "x1" in pop_m else "x5"
            push_reg = "x1" if "x1" in push_m else "x5"
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(ssp_top)})",
                    f"csrw ssp, x{addr_reg}",
                    f"LI({push_reg}, 0x5A5A5A5A)",
                    *ss_insn(push_m, compressed=push_c),
                    f"mv {reg}, {push_reg}",
                    test_data.add_testcase(f"{pop_name}_match_s_rv{xlen}", "cp_sspopchk_match_s", _CG),
                    *ss_insn(pop_m, compressed=pop_c),
                    f"csrr x{rd_reg}, ssp",
                    write_sigupd(rd_reg, test_data),
                ]
            )

        for pop_m, pop_c, pop_name in _POP_FORMS:
            reg = "x1" if "x1" in pop_m else "x5"
            push_m = "sspush x1" if reg == "x1" else "sspush x5"
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(ssp_top)})",
                    f"csrw ssp, x{addr_reg}",
                    f"LI({reg}, 0x11111111)",
                    *ss_insn(push_m),
                    f"LI({reg}, 0x22222222)   # corrupt the shadow copy comparison",
                    test_data.add_testcase(f"{pop_name}_mismatch_s_rv{xlen}", "cp_sspopchk_mismatch_s", _CG),
                    *ss_insn(pop_m, compressed=pop_c),
                ]
            )

        lines.extend(
            [
                f"LI(x{addr_reg}, {hex(ssp_top)})",
                f"csrw ssp, x{addr_reg}",
                test_data.add_testcase(f"ssrdp_s_rv{xlen}", "cp_ssrdp_s", _CG),
                *ss_insn(f"ssrdp x{rd_reg}"),
                write_sigupd(rd_reg, test_data),
                f"LI(x{addr_reg}, {hex(ss_va)})",
                f"LI(x{rs2_reg}, 0x11223344)",
                test_data.add_testcase(f"ssamoswap_w_s_rv{xlen}", "cp_ssamoswap_s", _CG),
                *ss_insn(f"ssamoswap.w x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
                write_sigupd(rd_reg, test_data),
            ]
        )
        if xlen == 64:
            lines.extend(
                [
                    test_data.add_testcase(f"ssamoswap_d_s_rv{xlen}", "cp_ssamoswap_s", _CG),
                    *ss_insn(f"ssamoswap.d x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
                    write_sigupd(rd_reg, test_data),
                ]
            )

        lines.extend(restore_link_regs(save_x1, save_x5))
        lines.extend(teardown_vm())
        test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, save_x1, save_x5])
        return lines

    return [
        comment_banner("ZicfissS instructions", "Shadow stack instruction behaviour re-run in S-mode"),
        *both_xlens(build),
    ]


# ---------------------------------------------------------------------------
# cp_ss_address_alignment_*_s
# ---------------------------------------------------------------------------


def _generate_alignment_s(test_data: TestData) -> list[str]:
    def build(xlen: int) -> list[str]:
        ss_va, _, _ = va_for(xlen)
        base = ss_va + 0x400
        addr_reg, rd_reg, rs2_reg = test_data.int_regs.get_registers(3)
        lines = _smode_prologue(test_data, xlen)
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        lines.extend(save_lines)

        for offset in range(8):
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(base + offset)})",
                    f"csrw ssp, x{addr_reg}",
                    "LI(x1, 0xDEADBEEF)",
                    test_data.add_testcase(f"sspush_ssp_off{offset}_s_rv{xlen}", "cp_ss_address_alignment_ssp_s", _CG),
                    *ss_insn("sspush x1"),
                    f"LI(x{addr_reg}, {hex(base + offset)})",
                    f"csrw ssp, x{addr_reg}",
                    test_data.add_testcase(
                        f"sspopchk_ssp_off{offset}_s_rv{xlen}", "cp_ss_address_alignment_pop_s", _CG
                    ),
                    *ss_insn("sspopchk x1"),
                    f"LI(x{addr_reg}, {hex(base + offset)})",
                    f"LI(x{rs2_reg}, 0x11223344)",
                    test_data.add_testcase(
                        f"ssamoswap_w_off{offset}_s_rv{xlen}", "cp_ss_address_alignment_swap_s", _CG
                    ),
                    *ss_insn(f"ssamoswap.w x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
                ]
            )
            if xlen == 64:
                lines.extend(
                    [
                        f"LI(x{addr_reg}, {hex(base + offset)})",
                        test_data.add_testcase(
                            f"ssamoswap_d_off{offset}_s_rv{xlen}", "cp_ss_address_alignment_swap_s", _CG
                        ),
                        *ss_insn(f"ssamoswap.d x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
                    ]
                )

        lines.extend(restore_link_regs(save_x1, save_x5))
        lines.extend(teardown_vm())
        test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, save_x1, save_x5])
        return lines

    return [
        comment_banner("cp_ss_address_alignment_*_s", "ssp and SSAMOSWAP alignment sweep in S-mode"),
        *both_xlens(build),
    ]


# ---------------------------------------------------------------------------
# cp_ss_instr_target_page_s (non-SS pages only) and cp_sspopchk_fault_priority_s
# ---------------------------------------------------------------------------


def _generate_target_page_s(test_data: TestData) -> list[str]:
    coverpoint = "cp_ss_instr_target_page_s"

    def build(xlen: int) -> list[str]:
        _, rw_va, ro_va = va_for(xlen)
        addr_reg, rd_reg, rs2_reg = test_data.int_regs.get_registers(3)
        lines = _smode_prologue(test_data, xlen)
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        lines.extend(save_lines)

        # Aim at the middle of each page: sspush decrements before storing.
        for page_name, va in [("rw_page", rw_va + 0x800), ("ro_page", ro_va + 0x800)]:
            for mnemonic, compressed, name in _PUSH_FORMS + _POP_FORMS:
                reg = "x1" if "x1" in mnemonic else "x5"
                lines.extend(
                    [
                        f"LI(x{addr_reg}, {hex(va)})",
                        f"csrw ssp, x{addr_reg}",
                        f"LI({reg}, 0xDEADBEEF)",
                        test_data.add_testcase(f"{name}_on_{page_name}_s_rv{xlen}", coverpoint, _CG),
                        *ss_insn(mnemonic, compressed=compressed),
                    ]
                )
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(va)})",
                    f"LI(x{rs2_reg}, 0x11223344)",
                    test_data.add_testcase(f"ssamoswap_w_on_{page_name}_s_rv{xlen}", coverpoint, _CG),
                    *ss_insn(f"ssamoswap.w x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
                ]
            )

        # cp_sspopchk_fault_priority_s — unmapped ssp plus a value mismatch.
        bad_va = va_unmapped(xlen)
        for mnemonic, compressed, name in _POP_FORMS:
            reg = "x1" if "x1" in mnemonic else "x5"
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(bad_va)})",
                    f"csrw ssp, x{addr_reg}   # unmapped: the pop's load will fault",
                    f"LI({reg}, 0x0BADF00D)",
                    test_data.add_testcase(f"{name}_fault_priority_s_rv{xlen}", "cp_sspopchk_fault_priority_s", _CG),
                    *ss_insn(mnemonic, compressed=compressed),
                ]
            )

        lines.extend(restore_link_regs(save_x1, save_x5))
        lines.extend(teardown_vm())
        test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, save_x1, save_x5])
        return lines

    return [
        comment_banner(coverpoint, "SS instructions on non-SS pages, and memory-fault priority, in S-mode"),
        *both_xlens(build),
    ]


# ---------------------------------------------------------------------------
# Top-level generator
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "ZicfissS",
    required_extensions=["S", "U", "Zicfiss", "Zimop", "Zaamo", "Zcmop", "Zca", "Zicsr"],
)
def make_zicfisss(test_data: TestData) -> list[TestChunk]:
    """Generate the ZicfissS test suite."""
    test_chunks: list[TestChunk] = []

    sections: list[tuple[object, str | None]] = [
        (_generate_ssp_gating_s, None),
        (_generate_page_enc_s, "reads and writes through the shadow stack page"),
        (_generate_instr_s, "sspush/sspopchk/ssamoswap target the shadow stack page"),
        (_generate_alignment_s, "sweeps ssp and SSAMOSWAP addresses inside the shadow stack page"),
        (_generate_target_page_s, None),
    ]
    for section, reason in sections:
        tc = test_data.begin_test_chunk()
        body = section(test_data)  # pyright: ignore[reportCallIssue]
        tc.code.extend(guard_ss_page(body, reason=reason) if reason else body)
        test_chunks.append(test_data.end_test_chunk())

    tc = test_data.begin_test_chunk()
    tc.code.extend(page_table_data_section())
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
