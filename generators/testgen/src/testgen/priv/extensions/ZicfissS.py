##################################
# priv/extensions/ZicfissS.py
#
# Zicfiss (shadow stack) S/HS-mode test generator.
# umer@riscv.org September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicfissS test generator.

Shadow stack behaviour seen from S/HS-mode, following the ZicfissS sheet of the testplan
linked from docs/ctp/src/privmisc23.adoc:

  1. S-specific gating -- menvcfg.SSE alone gates S/HS. senvcfg.SSE is swept to show that
     it has no effect at S/HS.
  2. The instruction behaviour of ZicfissU repeated in S-mode, including how pte.U,
     sstatus.SUM and sstatus.MXR apply to shadow stack accesses from S-mode.

The suite boots to S-mode and stays there. The page tables are supervisor pages, so the
S-mode handler can take the traps as usual. menvcfg is the one M-mode CSR it writes, through
T-SBI.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfissCommon import (
    POP_FORMS,
    PTE_SS,
    PUSH_FORMS,
    SSAMOSWAP_SWEEP_BASE,
    XWR_PERMS,
    map_zicfiss_pages,
    page_table_data_section,
    restore_link_regs,
    rv64_only,
    save_link_regs,
    set_envcfg_sse,
    ss_forms_against,
    ss_instr,
    ssamoswap_sweep_offsets,
    zcmop_only,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "ZicfissS_cg"
_SATP_OFF = ["csrwi satp, 0", "sfence.vma"]


def _smode_prologue(test_data: TestData, *, menvcfg: int = 1, senvcfg: int = 1, ss_perms: str = PTE_SS) -> list[str]:
    """Translation, page mappings and the SSE bits, all from S-mode.

    Enabling translation before the mappings are written is safe because the boot code
    already identity-maps the superpage holding the code and data as supervisor RWX.
    """
    return [
        "ZICFISS_SATP_SETUP",
        *map_zicfiss_pages(ss_perms=ss_perms, user=False),
        *set_envcfg_sse("menvcfg", menvcfg, test_data, mode="S"),
        *set_envcfg_sse("senvcfg", senvcfg, test_data, mode="S"),
    ]


def _vm_section(title: str, description: str, lines: list[str]) -> list[str]:
    """A section banner, and ``lines`` guarded on the configuration supporting Sv39/Sv32."""
    return [comment_banner(title, description), "#ifdef ZICFISS_VM_SUPPORTED", *lines, "#endif"]


def _ssamoswap_forms(test_data: TestData, addr: str, tag: str, coverpoint: str) -> list[str]:
    """SSAMOSWAP.W, and SSAMOSWAP.D on RV64, against ``addr``."""
    addr_reg, data_reg = test_data.int_regs.get_registers(2)
    lines = [f"LI(x{addr_reg}, {addr})", f"LI(x{data_reg}, 0x11223344)"]
    for width in ("w", "d"):
        lines.extend(
            rv64_only(
                width,
                [
                    test_data.add_testcase(f"ssamoswap_{width}_{tag}", coverpoint, _CG),
                    f"ssamoswap.{width} x{data_reg}, x{data_reg}, (x{addr_reg})",
                ],
            )
        )
    test_data.int_regs.return_registers([addr_reg, data_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_ssp_csr_gating_s -- senvcfg.SSE must NOT gate S/HS
# ---------------------------------------------------------------------------


def _generate_ssp_gating_s(test_data: TestData) -> list[str]:
    coverpoint = "cp_ssp_csr_gating_s"
    lines: list[str] = []
    for menvcfg in (0, 1):
        for senvcfg in (0, 1):
            tag = f"m{menvcfg}s{senvcfg}"
            rd_reg, val_reg = test_data.int_regs.get_registers(2)
            lines.extend(
                [
                    f"# --- menvcfg.SSE={menvcfg}, senvcfg.SSE={senvcfg} ---",
                    *_smode_prologue(test_data, menvcfg=menvcfg, senvcfg=senvcfg),
                    f"LI(x{val_reg}, 0x3000)",
                ]
            )
            for op, form in (
                ("csrrw", f"csrrw x{rd_reg}, ssp, x{val_reg}"),
                ("csrrs", f"csrrs x{rd_reg}, ssp, x{val_reg}"),
                ("csrrc", f"csrrc x{rd_reg}, ssp, x{val_reg}"),
                ("csrrwi", f"csrrwi x{rd_reg}, ssp, 1"),
                ("csrrsi", f"csrrsi x{rd_reg}, ssp, 1"),
                ("csrrci", f"csrrci x{rd_reg}, ssp, 1"),
            ):
                lines.extend([test_data.add_testcase(f"ssp_{op}_{tag}", coverpoint, _CG), form])
            lines.extend(_SATP_OFF)
            test_data.int_regs.return_registers([rd_reg, val_reg])
    return _vm_section(coverpoint, "menvcfg.SSE gates ssp at S/HS; senvcfg.SSE must not", lines)


# ---------------------------------------------------------------------------
# cp_ss_page_enc -- the xwr=010 encoding, gated by menvcfg.SSE
# ---------------------------------------------------------------------------


def _generate_page_enc_s(test_data: TestData) -> list[str]:
    lines: list[str] = []
    for menvcfg in (0, 1):
        addr_reg, rd_reg = test_data.int_regs.get_registers(2)
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        lines.extend(
            [
                f"# --- menvcfg.SSE={menvcfg} ---",
                *_smode_prologue(test_data, menvcfg=menvcfg),
                *save_lines,
                f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)",
                f"csrw ssp, x{addr_reg}",
                "LI(x1, 0xC0FFEE11)",
                test_data.add_testcase(f"ss_page_enc_push_men{menvcfg}", "cp_ss_page_enc", _CG),
                "sspush x1",
            ]
        )
        # An ordinary load from an SS page is permitted; an ordinary store is not.
        for m in ("lb", "lh", "lw", "ld"):
            load = [
                test_data.add_testcase(f"{m}_ss_page_men{menvcfg}", "cp_ss_page_enc_load", _CG),
                f"{m} x{rd_reg}, 0(x{addr_reg})",
            ]
            lines.extend(["#if __riscv_xlen == 64", *load, "#endif"] if m == "ld" else load)
        for m in ("sb", "sh", "sw", "sd"):
            store = [
                f"LI(x{rd_reg}, 0x55)",
                test_data.add_testcase(f"{m}_ss_page_men{menvcfg}", "cp_ss_page_enc_store", _CG),
                f"{m} x{rd_reg}, 0(x{addr_reg})",
            ]
            lines.extend(["#if __riscv_xlen == 64", *store, "#endif"] if m == "sd" else store)
        lines.extend([*restore_link_regs(save_x1, save_x5), *_SATP_OFF])
        test_data.int_regs.return_registers([addr_reg, rd_reg, save_x1, save_x5])
    return _vm_section("cp_ss_page_enc", "pte.xwr=010 is an SS page when menvcfg.SSE=1, reserved when 0", lines)


# ---------------------------------------------------------------------------
# S-mode re-run of the instruction behaviour
# ---------------------------------------------------------------------------


def _generate_instr_s(test_data: TestData) -> list[str]:
    ssp_top = "ZICFISS_VA_SS + 0x800"
    addr_reg, rd_reg, rs2_reg = test_data.int_regs.get_registers(3)
    lines = _smode_prologue(test_data)
    save_x1, save_x5, save_lines = save_link_regs(test_data)
    lines.extend(save_lines)

    for form in PUSH_FORMS:
        case = [
            f"LI(x{addr_reg}, {ssp_top})",
            f"csrw ssp, x{addr_reg}",
            f"LI({form.link_reg}, 0xA5A5A5A5)",
            test_data.add_testcase(f"{form.name}_s", "cp_sspush_s", _CG),
            *ss_instr(form),
            f"csrr x{rd_reg}, ssp",
            write_sigupd(rd_reg, test_data),
            # An SS page is readable by ordinary loads, so confirm the value
            # actually landed at the new top of stack.
            f"LREG x{rd_reg}, 0(x{rd_reg})",
            write_sigupd(rd_reg, test_data),
        ]
        lines.extend(zcmop_only(form.compressed, case))

    for push, pop in zip(PUSH_FORMS, POP_FORMS, strict=True):
        case = [
            f"LI(x{addr_reg}, {ssp_top})",
            f"csrw ssp, x{addr_reg}",
            f"LI({push.link_reg}, 0x5A5A5A5A)",
            *ss_instr(push),
            f"mv {pop.link_reg}, {push.link_reg}",
            test_data.add_testcase(f"{pop.name}_match_s", "cp_sspopchk_match_s", _CG),
            *ss_instr(pop),
            f"csrr x{rd_reg}, ssp",
            write_sigupd(rd_reg, test_data),
        ]
        lines.extend(zcmop_only(push.compressed or pop.compressed, case))

    for pop in POP_FORMS:
        case = [
            f"LI(x{addr_reg}, {ssp_top})",
            f"csrw ssp, x{addr_reg}",
            f"LI({pop.link_reg}, 0x11111111)",
            f"sspush {pop.link_reg}",
            f"LI({pop.link_reg}, 0x22222222)   # no longer matches the shadow copy",
            test_data.add_testcase(f"{pop.name}_mismatch_s", "cp_sspopchk_mismatch_s", _CG),
            *ss_instr(pop),
        ]
        lines.extend(zcmop_only(pop.compressed, case))

    lines.extend(
        [
            f"LI(x{addr_reg}, {ssp_top})",
            f"csrw ssp, x{addr_reg}",
            test_data.add_testcase("ssrdp_s", "cp_ssrdp_s", _CG),
            f"ssrdp x{rd_reg}",
            write_sigupd(rd_reg, test_data),
            f"LI(x{addr_reg}, ZICFISS_VA_SS)",
            f"LI(x{rs2_reg}, 0x11223344)",
        ]
    )
    for width in ("w", "d"):
        lines.extend(
            rv64_only(
                width,
                [
                    test_data.add_testcase(f"ssamoswap_{width}_s", "cp_ssamoswap_s", _CG),
                    f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                    write_sigupd(rd_reg, test_data),
                ],
            )
        )

    lines.extend([*restore_link_regs(save_x1, save_x5), *_SATP_OFF])
    test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, save_x1, save_x5])
    return _vm_section("ZicfissS instructions", "Shadow stack instruction behaviour re-run in S-mode", lines)


# ---------------------------------------------------------------------------
# cp_ss_address_alignment_*_s
# ---------------------------------------------------------------------------


def _generate_alignment_s(test_data: TestData) -> list[str]:
    addr_reg, rd_reg, rs2_reg = test_data.int_regs.get_registers(3)
    lines = _smode_prologue(test_data)
    save_x1, save_x5, save_lines = save_link_regs(test_data)
    lines.extend(save_lines)

    for offset in range(8):
        addr = f"ZICFISS_VA_SS + {hex(0x400 + offset)}"
        tag = f"ssp_off{offset}_s"
        lines.extend(
            ss_forms_against(test_data, PUSH_FORMS, addr, "0xDEADBEEF", tag, "cp_ss_address_alignment_ssp_s", _CG)
        )
        lines.extend(
            ss_forms_against(test_data, POP_FORMS, addr, "0xDEADBEEF", tag, "cp_ss_address_alignment_pop_s", _CG)
        )

    # SSAMOSWAP address alignment sweep; see SSAMOSWAP_SWEEP_BASE.
    for width in ("w", "d"):
        block: list[str] = []
        for offset in ssamoswap_sweep_offsets(width):
            block.extend(
                [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS + {hex(SSAMOSWAP_SWEEP_BASE + offset)})",
                    f"LI(x{rs2_reg}, 0x11223344)",
                    test_data.add_testcase(f"ssamoswap_{width}_off{offset}_s", "cp_ss_address_alignment_swap_s", _CG),
                    f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                ]
            )
        lines.extend(rv64_only(width, block))

    lines.extend([*restore_link_regs(save_x1, save_x5), *_SATP_OFF])
    test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, save_x1, save_x5])
    return _vm_section("cp_ss_address_alignment_*_s", "ssp and SSAMOSWAP alignment sweep in S-mode", lines)


# ---------------------------------------------------------------------------
# cp_ss_instr_target_page_s and cp_sspopchk_fault_priority_s
# ---------------------------------------------------------------------------


def _generate_target_page_s(test_data: TestData) -> list[str]:
    """Remap the shadow stack page with each pte.xwr encoding; then the memory-fault priority."""
    coverpoint = "cp_ss_instr_target_page_s"
    lines: list[str] = []
    mid = "ZICFISS_VA_SS + 0x800"  # sspush decrements before storing
    for xwr, perms in XWR_PERMS.items():
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        lines.extend(
            [
                f"# --- pte.xwr = {xwr} ---",
                *_smode_prologue(test_data, ss_perms=perms),
                *save_lines,
                *ss_forms_against(test_data, PUSH_FORMS + POP_FORMS, mid, "0xDEADBEEF", f"xwr{xwr}_s", coverpoint, _CG),
                *_ssamoswap_forms(test_data, mid, f"xwr{xwr}_s", coverpoint),
                *restore_link_regs(save_x1, save_x5),
                *_SATP_OFF,
            ]
        )
        test_data.int_regs.return_registers([save_x1, save_x5])

    # cp_sspopchk_fault_priority_s -- unmapped ssp plus a value mismatch.
    save_x1, save_x5, save_lines = save_link_regs(test_data)
    lines.extend(
        [
            *_smode_prologue(test_data),
            *save_lines,
            *ss_forms_against(
                test_data,
                POP_FORMS,
                "ZICFISS_VA_UNMAPPED",
                "0x0BADF00D",
                "fault_priority_s",
                "cp_sspopchk_fault_priority_s",
                _CG,
            ),
            *restore_link_regs(save_x1, save_x5),
            *_SATP_OFF,
        ]
    )
    test_data.int_regs.return_registers([save_x1, save_x5])
    return _vm_section(coverpoint, "SS instructions against every pte.xwr encoding, and memory-fault priority", lines)


# ---------------------------------------------------------------------------
# cp_ss_page_perm_priority
# ---------------------------------------------------------------------------


def _generate_perm_priority_s(test_data: TestData) -> list[str]:
    """U/SUM/MXR resolve during translation, before any Zicfiss rule."""
    coverpoint = "cp_ss_page_perm_priority"
    ssp_top = "ZICFISS_VA_SS + 0x800"
    lines: list[str] = []
    for u_bit in (0, 1):
        mask_reg = test_data.int_regs.get_register()
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        lines.extend(
            [
                f"# --- pte.U = {u_bit} ---",
                *_smode_prologue(test_data, ss_perms=PTE_SS + (" | PTE_U" if u_bit else "")),
                *save_lines,
            ]
        )
        for sum_bit in (0, 1):
            for mxr_bit in (0, 1):
                tag = f"u{u_bit}_sum{sum_bit}_mxr{mxr_bit}"
                set_bits = " | ".join(
                    ["0"] + (["SSTATUS_SUM"] if sum_bit else []) + (["SSTATUS_MXR"] if mxr_bit else [])
                )
                lines.extend(
                    [
                        f"LI(x{mask_reg}, SSTATUS_SUM | SSTATUS_MXR)",
                        f"csrc sstatus, x{mask_reg}",
                        f"LI(x{mask_reg}, {set_bits})",
                        f"csrs sstatus, x{mask_reg}",
                        *ss_forms_against(
                            test_data, PUSH_FORMS + POP_FORMS, ssp_top, "0x5A5A5A5A", tag, coverpoint, _CG
                        ),
                        *_ssamoswap_forms(test_data, ssp_top, tag, coverpoint),
                    ]
                )
                # An ordinary load is permitted by the shadow stack rules, for both MXR
                # values; an ordinary store is not.
                addr_reg, data_reg = test_data.int_regs.get_registers(2)
                lines.append(f"LI(x{addr_reg}, {ssp_top})")
                for m in ("lb", "lh", "lw", "ld"):
                    load = [
                        test_data.add_testcase(f"{m}_{tag}", "cp_ss_page_perm_priority_load", _CG),
                        f"{m} x{data_reg}, 0(x{addr_reg})",
                    ]
                    lines.extend(["#if __riscv_xlen == 64", *load, "#endif"] if m == "ld" else load)
                for m in ("sb", "sh", "sw", "sd"):
                    store = [
                        f"LI(x{data_reg}, 0x55)",
                        test_data.add_testcase(f"{m}_{tag}", "cp_ss_page_perm_priority_store", _CG),
                        f"{m} x{data_reg}, 0(x{addr_reg})",
                    ]
                    lines.extend(["#if __riscv_xlen == 64", *store, "#endif"] if m == "sd" else store)
                test_data.int_regs.return_registers([addr_reg, data_reg])
        lines.extend([*restore_link_regs(save_x1, save_x5), *_SATP_OFF])
        test_data.int_regs.return_registers([mask_reg, save_x1, save_x5])
    return _vm_section(coverpoint, "pte.U, sstatus.SUM and sstatus.MXR against the SS page", lines)


# ---------------------------------------------------------------------------
# cp_senvcfg_sse_rdonly0_s
# ---------------------------------------------------------------------------


def _generate_senvcfg_rdonly0_s(test_data: TestData) -> list[str]:
    """senvcfg.SSE reads back 0 from S-mode whenever menvcfg.SSE is 0.

    csrrs sets and csrrc clears only the SSE bit, so no other senvcfg field changes.
    """
    coverpoint = "cp_senvcfg_sse_rdonly0_s"
    rd_reg, val_reg = test_data.int_regs.get_registers(2)
    lines: list[str] = [comment_banner(coverpoint, "senvcfg.SSE read-only zero while menvcfg.SSE=0")]
    for menvcfg in (0, 1):
        lines.extend(set_envcfg_sse("menvcfg", menvcfg, test_data, mode="S"))
        for written in (0, 1):
            op = "csrrs" if written else "csrrc"
            lines.extend(
                [
                    f"LI(x{val_reg}, SENVCFG_SSE)",
                    test_data.add_testcase(f"senvcfg_{op}_men{menvcfg}_wrote{written}", coverpoint, _CG),
                    f"{op} x{rd_reg}, senvcfg, x{val_reg}",
                    f"csrr x{rd_reg}, senvcfg   # SSE must read 0 when menvcfg.SSE=0",
                    write_sigupd(rd_reg, test_data),
                ]
            )
    test_data.int_regs.return_registers([rd_reg, val_reg])
    return lines


# ---------------------------------------------------------------------------
# Top-level generator
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "ZicfissS",
    required_extensions=["S", "Zicfiss"],
    # Zicfiss implies Zimop and Zaamo; name them for the assembler.
    march_extensions=["Zicfiss", "Zimop", "Zaamo"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_zicfisss(test_data: TestData) -> list[TestChunk]:
    """Generate the ZicfissS test suite."""
    test_chunks: list[TestChunk] = []
    for section in (
        _generate_ssp_gating_s,
        _generate_page_enc_s,
        _generate_instr_s,
        _generate_alignment_s,
        _generate_target_page_s,
        _generate_perm_priority_s,
        _generate_senvcfg_rdonly0_s,
    ):
        tc = test_data.begin_test_chunk()
        tc.code.extend(page_table_data_section())
        tc.code.extend(section(test_data))
        test_chunks.append(test_data.end_test_chunk())
    return test_chunks
