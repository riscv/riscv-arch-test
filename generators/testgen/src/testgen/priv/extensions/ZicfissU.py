##################################
# priv/extensions/ZicfissU.py
#
# Zicfiss (shadow stack) U-mode test generator.
# umer@riscv.org September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicfissU test generator.

Shadow stack behaviour seen from U-mode: the ssp CSR; SSPUSH, SSPOPCHK, SSRDP and
SSAMOSWAP; how shadow stack instructions treat pages of every type; how ordinary, atomic,
cache-block and (with Zve32x) vector accesses treat a shadow stack page; and the U-mode
half of the SSE enable chain.

The suite boots to U-mode. Each section steps up to S-mode through T-SBI to build the
page tables and set the SSE bits, drops back to U-mode, turns translation on (see
``_umode_prologue``), runs its testcases, and turns translation off again. The testplan
is the ZicfissU sheet linked from docs/ctp/src/privmisc23.adoc.
"""

from testgen.asm.helpers import write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfissCommon import (
    MOP_FORMS,
    POP_FORMS,
    PTE_RW,
    PTE_SS,
    PUSH_FORMS,
    SSAMOSWAP_WIDTHS,
    XWR_PERMS,
    enable_translation,
    map_zicfiss_pages,
    page_table_data_section,
    rv64_only,
    set_envcfg_sse,
    ss_forms_against,
    ss_instr,
    ssamoswap_forms,
    ssamoswap_only,
    vm_section,
    zcmop_only,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "ZicfissU_cg"
# Turn translation off from U-mode.
_SATP_OFF = [tsbi_call("csrw satp, x0")]


def _umode_prologue(
    test_data: TestData,
    *,
    menvcfg: int = 1,
    senvcfg: int = 1,
    ss_perms: str = PTE_SS,
    ss_page_user: bool | None = None,
    extra_mappings: tuple[str, ...] = (),
) -> list[str]:
    """Build the page tables and SSE state in S-mode, then enable translation from U-mode.

    The test body is mapped as user pages, which S-mode cannot fetch, so satp is written
    through T-SBI from U-mode. sstatus.SUM lets the S-mode trap handler record trap signatures
    in the user-mapped signature region. Arguments other than ``test_data`` are those of
    ``map_zicfiss_pages`` and the SSE values; ``extra_mappings`` adds page-table lines.
    """
    sum_reg = test_data.int_regs.get_register()
    lines = [
        "RVTEST_TSBI_GOTO_SMODE",
        *map_zicfiss_pages(test_data, ss_perms=ss_perms, user=True, ss_page_user=ss_page_user),
        *extra_mappings,
        f"LI(x{sum_reg}, SSTATUS_SUM)",
        f"csrs sstatus, x{sum_reg}",
        *set_envcfg_sse("menvcfg", menvcfg, test_data, mode="S"),
        *set_envcfg_sse("senvcfg", senvcfg, test_data, mode="S"),
        "RVTEST_TSBI_GOTO_UMODE",
        *enable_translation(test_data, mode="U"),
    ]
    test_data.int_regs.return_registers([sum_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_ssp_access / cp_ssp_low_bits_ro_zero
# ---------------------------------------------------------------------------


def _generate_ssp_access(test_data: TestData) -> list[str]:
    coverpoint = "cp_ssp_access"
    lines = _umode_prologue(test_data)
    val_reg, rd_reg = test_data.int_regs.get_registers(2)

    # Write all-ones and all-zeros through each register form.
    for op in ("csrrw", "csrrs", "csrrc"):
        for name, pattern in (("ones", "-1"), ("zeros", "0")):
            lines.extend(
                [
                    f"LI(x{val_reg}, {pattern})",
                    test_data.add_testcase(f"ssp_{op}_{name}", coverpoint, _CG),
                    f"{op} x{rd_reg}, ssp, x{val_reg}",
                    f"csrr x{rd_reg}, ssp   # read back",
                    write_sigupd(rd_reg, test_data),
                ]
            )

    # Immediate-form CSR ops so the csrrwi/csrrsi/csrrci bins fill.
    for op in ("csrrwi", "csrrsi", "csrrci"):
        lines.extend(
            [
                test_data.add_testcase(f"ssp_{op}", coverpoint, _CG),
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
                    f"LI(x{val_reg}, ZICFISS_VA_SS | {low})",
                    test_data.add_testcase(f"ssp_low_bits_{op}_{low}", "cp_ssp_low_bits_ro_zero", _CG),
                    form,
                    f"csrr x{rd_reg}, ssp   # ssp low bits must read as zero",
                    write_sigupd(rd_reg, test_data),
                ]
            )

    lines.extend(_SATP_OFF)
    test_data.int_regs.return_registers([val_reg, rd_reg])
    return vm_section(coverpoint, "ssp CSR access, width, and read-only-zero low bits", lines)


# ---------------------------------------------------------------------------
# cp_sspush / cp_sspopchk_match / cp_sspopchk_mismatch
# ---------------------------------------------------------------------------


def _generate_push_pop(test_data: TestData) -> list[str]:
    # Start ssp near the top of the SS page so pushes have room to grow down.
    ssp_top = "ZICFISS_VA_SS + 0x800"
    lines = _umode_prologue(test_data)
    addr_reg, rd_reg = test_data.int_regs.get_registers(2)

    # cp_sspush -- each encoding pushes all-zeros, all-ones and a pattern; read back ssp
    # and the pushed value.
    for form in PUSH_FORMS:
        for value_name, value in (("zeros", "0"), ("ones", "-1"), ("pattern", "0x5A5A5A5A")):
            case = [
                f"LI(x{addr_reg}, {ssp_top})",
                f"csrw ssp, x{addr_reg}",
                f"LI({form.link_reg}, {value})",
                test_data.add_testcase(f"{form.name}_{value_name}", "cp_sspush", _CG),
                *ss_instr(form),
                f"csrr x{rd_reg}, ssp   # must be ssp_top - XLEN/8",
                write_sigupd(rd_reg, test_data),
                f"LREG x{rd_reg}, 0(x{rd_reg})   # the pushed value",
                write_sigupd(rd_reg, test_data),
            ]
            lines.extend(zcmop_only(form.compressed, case))

    # cp_sspopchk_match -- push then pop the same value back.
    for push, pop in zip(PUSH_FORMS, POP_FORMS, strict=True):
        case = [
            f"LI(x{addr_reg}, {ssp_top})",
            f"csrw ssp, x{addr_reg}",
            f"LI({push.link_reg}, 0x5A5A5A5A)",
            *ss_instr(push),
            f"mv {pop.link_reg}, {push.link_reg}   # matching value in the pop's link register",
            test_data.add_testcase(f"{pop.name}_match", "cp_sspopchk_match", _CG),
            *ss_instr(pop),
            f"csrr x{rd_reg}, ssp   # must be back at ssp_top",
            write_sigupd(rd_reg, test_data),
        ]
        lines.extend(zcmop_only(push.compressed or pop.compressed, case))

    # cp_sspopchk_mismatch -- corrupt the link register so the compare fails, including
    # values that differ from the shadow copy in exactly one bit, at each end.
    for pop in POP_FORMS:
        for edge, pushed, popped in (
            ("", "0x11111111", "0x22222222"),
            ("_bit0", "0", "1"),
            ("_bit_msb", "0", "(1 << (__riscv_xlen - 1))"),
        ):
            case = [
                f"LI(x{addr_reg}, {ssp_top})",
                f"csrw ssp, x{addr_reg}",
                f"LI({pop.link_reg}, {pushed})",
                f"sspush {pop.link_reg}",
                f"LI({pop.link_reg}, {popped})   # no longer matches the shadow copy",
                test_data.add_testcase(f"{pop.name}_mismatch{edge}", "cp_sspopchk_mismatch", _CG),
                *ss_instr(pop),
                f"csrr x{rd_reg}, ssp   # unchanged by the failed check",
                write_sigupd(rd_reg, test_data),
            ]
            lines.extend(zcmop_only(pop.compressed, case))

    lines.extend(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg])
    return vm_section("cp_sspush/cp_sspopchk", "Shadow stack push and pop, matching and mismatching", lines)


# ---------------------------------------------------------------------------
# cp_sspopchk_fault_priority
# ---------------------------------------------------------------------------


def _generate_fault_priority(test_data: TestData) -> list[str]:
    """A memory fault on the pop outranks the software-check exception.

    ssp is pointed at a deliberately unmapped VA *and* the link register is given a
    value that would not match, so both faults are live at once. Only the memory
    fault may be reported.
    """
    coverpoint = "cp_sspopchk_fault_priority"
    lines = [
        *_umode_prologue(test_data),
        *ss_forms_against(test_data, POP_FORMS, "ZICFISS_VA_UNMAPPED", "0x0BADF00D", "fault_priority", coverpoint, _CG),
        *_SATP_OFF,
    ]
    return vm_section(coverpoint, "Memory fault on the pop outranks the software-check exception", lines)


# ---------------------------------------------------------------------------
# Call/return round trip
# ---------------------------------------------------------------------------


def _generate_call_return(test_data: TestData) -> list[str]:
    """Nested prologue pushes and epilogue pops of x1, then a subverted return address."""
    lines = _umode_prologue(test_data)
    addr_reg, rd_reg = test_data.int_regs.get_registers(2)
    lines.extend([f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)", f"csrw ssp, x{addr_reg}"])

    # Three nested prologues: each spills the link register to the shadow stack.
    for depth in range(3):
        lines.extend(
            [
                f"LI(x1, {hex(0xC0DE0000 + depth)})   # simulated return address at depth {depth}",
                test_data.add_testcase(f"call_prologue_depth{depth}", "cp_sspush", _CG),
                "sspush x1",
            ]
        )
    # Three matching epilogues, unwinding in reverse order.
    for depth in reversed(range(3)):
        lines.extend(
            [
                f"LI(x1, {hex(0xC0DE0000 + depth)})   # link register reloaded from the regular stack",
                test_data.add_testcase(f"return_epilogue_depth{depth}", "cp_sspopchk_match", _CG),
                "sspopchk x1",
            ]
        )
    lines.extend([f"csrr x{rd_reg}, ssp   # must be back at the starting ssp", write_sigupd(rd_reg, test_data)])

    # Subverted return address: the epilogue compare must catch it.
    lines.extend(
        [
            "LI(x1, 0xC0DE1234)",
            "sspush x1",
            "LI(x1, 0xBAD00BAD)   # attacker-supplied return address",
            test_data.add_testcase("return_subverted", "cp_sspopchk_mismatch", _CG),
            "sspopchk x1",
            f"csrr x{rd_reg}, ssp   # unchanged by the failed check",
            write_sigupd(rd_reg, test_data),
        ]
    )

    lines.extend(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg])
    return vm_section("call/return", "Non-leaf prologue/epilogue round trip across nested depth", lines)


# ---------------------------------------------------------------------------
# cp_ssrdp
# ---------------------------------------------------------------------------


def _generate_ssrdp(test_data: TestData) -> list[str]:
    coverpoint = "cp_ssrdp"
    lines = _umode_prologue(test_data)
    addr_reg, rd_reg = test_data.int_regs.get_registers(2)
    lines.extend(
        [
            f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)",
            f"csrw ssp, x{addr_reg}",
            test_data.add_testcase("ssrdp_reads_ssp", coverpoint, _CG),
            f"ssrdp x{rd_reg}",
            write_sigupd(rd_reg, test_data),
            "LI(x1, 0xFEEDFACE)",
            "sspush x1",
            test_data.add_testcase("ssrdp_after_push", coverpoint, _CG),
            f"ssrdp x{rd_reg}   # must equal ssp after the push",
            write_sigupd(rd_reg, test_data),
            *_SATP_OFF,
        ]
    )
    test_data.int_regs.return_registers([addr_reg, rd_reg])
    return vm_section(coverpoint, "SSRDP moves ssp into rd", lines)


# ---------------------------------------------------------------------------
# cp_ssamoswap
# ---------------------------------------------------------------------------


def _generate_ssamoswap(test_data: TestData) -> list[str]:
    coverpoint = "cp_ssamoswap"
    lines = _umode_prologue(test_data)
    addr_reg, rd_reg, rs2_reg, seed_reg = test_data.int_regs.get_registers(4)

    # The loaded value's bit 31 (the sign bit RV64 SSAMOSWAP.W extends) and, on RV64, whether
    # rs2[63:32] is non-zero, which SSAMOSWAP.W must ignore.
    for width in SSAMOSWAP_WIDTHS:
        block: list[str] = []
        for msb in (0, 1):
            for upper in (0, 1):
                name = f"ssamoswap_{width}_msb{msb}_upper{upper}"
                case = [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS)",
                    f"LI(x{seed_reg}, {'0x80000000' if msb else '0x7FFFFFFF'})",
                    # Ordinary stores to an SS page raise an access fault, so a swap seeds the location.
                    f"ssamoswap.{width} x{rd_reg}, x{seed_reg}, (x{addr_reg})",
                    f"LI(x{rs2_reg}, {'0xAAAAAAAA12345678' if upper else '0x12345678'})",
                    test_data.add_testcase(name, coverpoint, _CG),
                    f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                    write_sigupd(rd_reg, test_data),
                ]
                block.extend(rv64_only(case) if upper else case)
        lines.extend(ssamoswap_only(width, block))

    for width in SSAMOSWAP_WIDTHS:
        block = []
        # cp_ssamoswap_aqrl: all four ordering-bit encodings.
        for aq, rl, suffix in ((0, 0, ""), (0, 1, ".rl"), (1, 0, ".aq"), (1, 1, ".aqrl")):
            block.extend(
                [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS)",
                    f"LI(x{rs2_reg}, {hex(0x5A5A5A50 + 2 * aq + rl)})",
                    test_data.add_testcase(f"ssamoswap_{width}_aq{aq}_rl{rl}", "cp_ssamoswap_aqrl", _CG),
                    f"ssamoswap.{width}{suffix} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                    write_sigupd(rd_reg, test_data),
                ]
            )
        # cp_ssamoswap_reg_edges: all distinct, rd=x0, rs2=x0, rd==rs1. rd records the value the
        # previous swap stored; a load of the location records what this one stored.
        for name, form, rd in (
            ("distinct", f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})", rd_reg),
            ("rd_x0", f"ssamoswap.{width} x0, x{rs2_reg}, (x{addr_reg})", None),
            ("rs2_x0", f"ssamoswap.{width} x{rd_reg}, x0, (x{addr_reg})", rd_reg),
            ("rd_eq_rs1", f"ssamoswap.{width} x{addr_reg}, x{rs2_reg}, (x{addr_reg})", addr_reg),
        ):
            block.extend(
                [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS)",
                    f"LI(x{rs2_reg}, 0x3C3C3C3C)",
                    test_data.add_testcase(f"ssamoswap_{width}_{name}", "cp_ssamoswap_reg_edges", _CG),
                    form,
                    *([write_sigupd(rd, test_data)] if rd is not None else []),
                    f"LI(x{addr_reg}, ZICFISS_VA_SS)",
                    f"l{width} x{rd_reg}, 0(x{addr_reg})   # the stored value",
                    write_sigupd(rd_reg, test_data),
                ]
            )
        lines.extend(ssamoswap_only(width, block))

    lines.extend(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, seed_reg])
    return vm_section(coverpoint, "SSAMOSWAP.W/.D swap, sign-extension, ordering bits and register edges", lines)


# ---------------------------------------------------------------------------
# cp_ss_address_alignment
# ---------------------------------------------------------------------------


def _generate_alignment(test_data: TestData) -> list[str]:
    """Sweep addr[2:0] for ssp and for SSAMOSWAP; every misaligned SSAMOSWAP faults."""
    lines = _umode_prologue(test_data)
    addr_reg, rd_reg, rs2_reg = test_data.int_regs.get_registers(3)

    for offset in range(8):
        addr = f"ZICFISS_VA_SS + {hex(0x400 + offset)}"
        lines.extend(
            [
                *ss_forms_against(
                    test_data, PUSH_FORMS, addr, "0xDEADBEEF", f"ssp_off{offset}", "cp_ss_address_alignment_ssp", _CG
                ),
                *ss_forms_against(
                    test_data, POP_FORMS, addr, "0xDEADBEEF", f"ssp_off{offset}", "cp_ss_address_alignment_pop", _CG
                ),
            ]
        )

    for width in SSAMOSWAP_WIDTHS:
        block: list[str] = []
        for offset in range(8):
            block.extend(
                [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS + {hex(0x400 + offset)})",
                    f"LI(x{rs2_reg}, 0x11223344)",
                    f"LI(x{rd_reg}, 0x0DDBA11)   # kept if the swap faults",
                    test_data.add_testcase(f"ssamoswap_{width}_off{offset}", "cp_ss_address_alignment_swap", _CG),
                    f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                    write_sigupd(rd_reg, test_data),
                ]
            )
        lines.extend(ssamoswap_only(width, block))

    lines.extend(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg])
    return vm_section("cp_ss_address_alignment", "ssp and SSAMOSWAP address alignment sweep over addr[2:0]", lines)


# ---------------------------------------------------------------------------
# cp_ss_instr_target_page -- SS instructions against every kind of page
# ---------------------------------------------------------------------------


def _generate_target_page(test_data: TestData) -> list[str]:
    """Remap the shadow stack page with each of the eight pte.xwr encodings."""
    coverpoint = "cp_ss_instr_target_page"
    # Aim at the middle of the page: sspush decrements ssp before storing, so a pointer at
    # the page base would push into the preceding page instead.
    mid = "ZICFISS_VA_SS + 0x800"
    lines: list[str] = []
    for xwr, perms in XWR_PERMS.items():
        lines.extend(
            [
                f"# --- pte.xwr = {xwr} ---",
                *_umode_prologue(test_data, ss_perms=perms),
                *ss_forms_against(test_data, PUSH_FORMS + POP_FORMS, mid, "0xDEADBEEF", f"xwr{xwr}", coverpoint, _CG),
                *ssamoswap_forms(test_data, mid, f"xwr{xwr}", coverpoint, _CG),
                *_SATP_OFF,
            ]
        )
    return vm_section(coverpoint, "SS instructions against every pte.xwr encoding", lines)


def _generate_target_page_mxr_u(test_data: TestData) -> list[str]:
    """Sweep sstatus.MXR and the SS page's U bit against the SS instructions."""
    coverpoint = "cp_ss_instr_target_page_u_mxr"
    mid = "ZICFISS_VA_SS + 0x800"
    lines: list[str] = []
    for u_bit in (0, 1):
        # ss_page_user=False leaves the SS page's U bit to ss_perms.
        lines.extend(
            [
                f"# --- pte.U = {u_bit} ---",
                *_umode_prologue(test_data, ss_perms=PTE_SS + (" | PTE_U" if u_bit else ""), ss_page_user=False),
            ]
        )
        for mxr in (0, 1):
            tag = f"u{u_bit}_mxr{mxr}"
            mask_reg = test_data.int_regs.get_register()
            lines.extend(
                [
                    f"LI(x{mask_reg}, SSTATUS_MXR)",
                    tsbi_call(f"{'csrs' if mxr else 'csrc'} sstatus, x{mask_reg}"),
                    *ss_forms_against(test_data, PUSH_FORMS + POP_FORMS, mid, "0x4D4D4D4D", tag, coverpoint, _CG),
                    *ssamoswap_forms(test_data, mid, tag, coverpoint, _CG),
                ]
            )
            test_data.int_regs.return_registers([mask_reg])
        lines.extend(_SATP_OFF)
    return vm_section(coverpoint, "MXR and pte.U axes on the shadow stack page", lines)


# ---------------------------------------------------------------------------
# cp_ss_page_crossing
# ---------------------------------------------------------------------------


def _generate_page_crossing(test_data: TestData) -> list[str]:
    """A push at a page base writes into the preceding page; a pop reads its own page."""
    coverpoint = "cp_ss_page_crossing"
    lines = _umode_prologue(test_data)
    # a_base: ssp at the SS page base, so ssp-XLEN/8 lands on the unmapped page below.
    # b_below_valid: ssp on the ordinary RW page, so ssp-XLEN/8 lands back on the SS page.
    # The boundary cases stay inside the SS page: a push from one slot above the base
    # writes the first slot, and a pop from the last slot reads it.
    for case, va in (
        ("a_base", "ZICFISS_VA_SS"),
        ("b_below_valid", "ZICFISS_VA_RW"),
        ("near_base", "ZICFISS_VA_SS + REGWIDTH"),
        ("near_top", "ZICFISS_VA_SS + 0x1000 - REGWIDTH"),
    ):
        lines.extend(ss_forms_against(test_data, PUSH_FORMS + POP_FORMS, va, "0xC0DECAFE", case, coverpoint, _CG))
    lines.extend(_SATP_OFF)
    return vm_section(coverpoint, "Shadow stack accesses that straddle a page boundary", lines)


# ---------------------------------------------------------------------------
# cp_ss_page_ad_bits
# ---------------------------------------------------------------------------


def _generate_page_ad_bits(test_data: TestData) -> list[str]:
    """D is required by the writing SS instructions but not by SSPOPCHK; A by all."""
    coverpoint = "cp_ss_page_ad_bits"
    mid = "ZICFISS_VA_SS + 0x800"
    lines: list[str] = []
    for a_bit, d_bit in ((0, 0), (1, 0), (0, 1), (1, 1)):
        perms = " | ".join(["PTE_W", "PTE_V"] + (["PTE_A"] if a_bit else []) + (["PTE_D"] if d_bit else []))
        tag = f"a{a_bit}_d{d_bit}"
        lines.extend(
            [
                f"# --- pte.A={a_bit}, pte.D={d_bit} ---",
                *_umode_prologue(test_data, ss_perms=perms),
                *ss_forms_against(test_data, PUSH_FORMS + POP_FORMS, mid, "0xADADADAD", tag, coverpoint, _CG),
                *ssamoswap_forms(test_data, mid, tag, coverpoint, _CG),
                *_SATP_OFF,
            ]
        )
    return vm_section(coverpoint, "PTE A/D bits on the shadow stack page", lines)


# ---------------------------------------------------------------------------
# cp_ss_non_idempotent
# ---------------------------------------------------------------------------


def _generate_non_idempotent(test_data: TestData) -> list[str]:
    """Svpbmt NC memory is idempotent and IO memory is not, so SS instructions fault only on IO.

    menvcfg.PBMTE is set for this section, without which a nonzero PBMT is reserved. SSAMOSWAP
    is left out on NC pages, because an implementation may also override the AMO PMA there
    (norm:Svpbmt_impl_may_override_pmas), so its outcome is implementation-defined and no UDB
    parameter says which behavior a DUT has. Those coverage bins stay as a known gap.
    """
    coverpoint = "cp_ss_non_idempotent"
    mid = "ZICFISS_VA_SS + 0x800"
    pbmte_reg = test_data.int_regs.get_register()
    lines = [
        "#if defined(SVPBMT_SUPPORTED) && __riscv_xlen == 64",
        f"LI(x{pbmte_reg}, MENVCFG_PBMTE)",
        tsbi_call(f"csrs menvcfg, x{pbmte_reg}"),
    ]
    test_data.int_regs.return_registers([pbmte_reg])
    # pte.PBMT is bits [62:61]: 00 PMA, 01 NC, 10 IO.
    for tag, pbmt in (("pma", 0), ("nc", 1), ("io", 2)):
        lines.extend(
            [
                f"# --- pte.PBMT = {tag} ---",
                *_umode_prologue(test_data, ss_perms=f"{PTE_SS} | ({pbmt} << 61)"),
                *ss_forms_against(test_data, PUSH_FORMS + POP_FORMS, mid, "0x1D1D1D1D", f"pbmt_{tag}", coverpoint, _CG),
                *(ssamoswap_forms(test_data, mid, f"pbmt_{tag}", coverpoint, _CG) if tag != "nc" else []),
                *_SATP_OFF,
            ]
        )
    pbmte_reg = test_data.int_regs.get_register()
    lines.extend(
        [
            f"LI(x{pbmte_reg}, MENVCFG_PBMTE)",
            tsbi_call(f"csrc menvcfg, x{pbmte_reg}"),
            "#endif  // SVPBMT_SUPPORTED && RV64",
        ]
    )
    test_data.int_regs.return_registers([pbmte_reg])
    return vm_section(coverpoint, "Svpbmt NC and IO memory types on the shadow stack page", lines)


# ---------------------------------------------------------------------------
# cp_ss_page_access -- non-SS accessors against an SS page
# ---------------------------------------------------------------------------


def _generate_page_access(test_data: TestData) -> list[str]:
    """Ordinary, atomic and cache-block accesses to an SS page, and a fetch from it.

    Loads and LR succeed; stores, AMOs, SC and CBOs raise a store/AMO access fault. Each
    testcase records rd, or for the stores and CBOs, the location read back afterwards. A jump
    to the SS page raises an instruction access fault, recorded by the trap handler.
    """
    lines = _umode_prologue(test_data)
    addr_reg, data_reg, mxr_reg = test_data.int_regs.get_registers(3)

    def access(mnemonic: str, form: str, coverpoint: str, tag: str = "", read_back: bool = False) -> list[str]:
        return [
            test_data.add_testcase(f"{mnemonic.replace('.', '_')}_on_ss_page{tag}", coverpoint, _CG),
            form,
            *([f"LREG x{data_reg}, 0(x{addr_reg})   # unchanged"] if read_back else []),
            write_sigupd(data_reg, test_data),
        ]

    lines.append(f"LI(x{addr_reg}, ZICFISS_VA_SS)")
    for mnemonic in ("sb", "sh", "sw", "sd"):
        store = [
            f"LI(x{data_reg}, 0xDEADBEEF)",
            *access(mnemonic, f"{mnemonic} x{data_reg}, 0(x{addr_reg})", "cp_ss_page_access_store", read_back=True),
        ]
        lines.extend(rv64_only(store) if mnemonic == "sd" else store)

    for mxr in (0, 1):
        lines.extend([f"LI(x{mxr_reg}, SSTATUS_MXR)", tsbi_call(f"{'csrs' if mxr else 'csrc'} sstatus, x{mxr_reg}")])
        for mnemonic in ("lb", "lh", "lw", "lbu", "lhu", "ld", "lwu"):
            load = access(mnemonic, f"{mnemonic} x{data_reg}, 0(x{addr_reg})", "cp_ss_page_access_load", f"_mxr{mxr}")
            lines.extend(rv64_only(load) if mnemonic in ("ld", "lwu") else load)

    # Zicfiss requires Zaamo, so the ordinary AMOs are always present.
    for mnemonic in ("amoswap.w", "amoadd.w", "amoor.w", "amoswap.d", "amoadd.d"):
        amo = [
            f"LI(x{data_reg}, 0x1)",
            *access(mnemonic, f"{mnemonic} x{data_reg}, x{data_reg}, (x{addr_reg})", "cp_ss_page_access_amo"),
        ]
        lines.extend(rv64_only(amo) if mnemonic.endswith(".d") else amo)

    # The CBOs are gated by the CBIE, CBCFE and CBZE fields of menvcfg and senvcfg; enable them so
    # that a CBO traps on the SS page rather than on its own gating. The boot code enables them
    # too, so they are left set afterwards.
    def cbo_enables(op: str) -> list[str]:
        return [
            f"LI(x{data_reg}, MENVCFG_CBIE | MENVCFG_CBCFE | MENVCFG_CBZE)",
            tsbi_call(f"{op} menvcfg, x{data_reg}"),
            f"LI(x{data_reg}, SENVCFG_CBIE | SENVCFG_CBCFE | SENVCFG_CBZE)",
            tsbi_call(f"{op} senvcfg, x{data_reg}"),
        ]

    lines.extend(
        [
            *cbo_enables("csrs"),
            "#ifdef ZICBOM_SUPPORTED",
            ".option push",
            ".option arch, +zicbom",
            *access("cbo.clean", f"cbo.clean (x{addr_reg})", "cp_ss_page_access_cbo", read_back=True),
            *access("cbo.flush", f"cbo.flush (x{addr_reg})", "cp_ss_page_access_cbo", read_back=True),
            *access("cbo.inval", f"cbo.inval (x{addr_reg})", "cp_ss_page_access_cbo", read_back=True),
            ".option pop",
            "#endif",
            "#ifdef ZICBOZ_SUPPORTED",
            ".option push",
            ".option arch, +zicboz",
            *access("cbo.zero", f"cbo.zero (x{addr_reg})", "cp_ss_page_access_cboz", read_back=True),
            ".option pop",
            "#endif",
        ]
    )

    lines.extend(
        [
            "#ifdef ZALRSC_SUPPORTED",
            ".option push",
            ".option arch, +a",
            *access("lr.w", f"lr.w x{data_reg}, (x{addr_reg})", "cp_ss_page_access_lrsc"),
            *access("sc.w", f"sc.w x{data_reg}, x{data_reg}, (x{addr_reg})", "cp_ss_page_access_lrsc"),
            *rv64_only(
                [
                    *access("lr.d", f"lr.d x{data_reg}, (x{addr_reg})", "cp_ss_page_access_lrsc"),
                    *access("sc.d", f"sc.d x{data_reg}, x{data_reg}, (x{addr_reg})", "cp_ss_page_access_lrsc"),
                ]
            ),
            ".option pop",
            "#endif",
            "#ifdef ZACAS_SUPPORTED",
            ".option push",
            ".option arch, +zacas",
            f"LI(x{data_reg}, 0x1)",
            *access("amocas.w", f"amocas.w x{data_reg}, x{data_reg}, (x{addr_reg})", "cp_ss_page_access_amocas"),
            *rv64_only(
                [
                    f"LI(x{data_reg}, 0x1)",
                    *access(
                        "amocas.d", f"amocas.d x{data_reg}, x{data_reg}, (x{addr_reg})", "cp_ss_page_access_amocas"
                    ),
                ]
            ),
            ".option pop",
            "#endif",
            # Instruction fetches are implicit accesses, which an SS page does not permit: the fetch
            # raises an instruction access fault, and the handler returns to ra.
            f"LI(x{addr_reg}, ZICFISS_VA_SS)",
            test_data.add_testcase("jalr_fetch_ss_page", "cp_ss_page_fetch", _CG),
            f"jalr ra, 0(x{addr_reg})",
            *_SATP_OFF,
        ]
    )
    test_data.int_regs.return_registers([addr_reg, data_reg, mxr_reg])
    return vm_section("cp_ss_page_access", "Non-SS accessors against an SS page, and a fetch from it", lines)


# ---------------------------------------------------------------------------
# cp_ss_vector_* -- vector accesses to an SS page (Zve32x)
# ---------------------------------------------------------------------------


# A fixed vl keeps every vector access within 16 bytes of its base whatever VLEN is, where VLMAX
# could run past the shadow stack page. The strided and indexed accesses from the page below need
# three elements to reach the SS page.
_VECTOR_VL = 4


def _generate_vector(test_data: TestData) -> list[str]:
    """A shadow stack page is readable by vector loads and not writable by vector stores.

    The page below the shadow stack page is also mapped, as a second view of the read/write
    page, so a strided or indexed access can begin there and run up into the SS page.
    """
    below = f"ZICFISS_PTE_SETUP(rvtest_zicfiss_rw_page, ({PTE_RW} | PTE_U), (ZICFISS_VA_SS - 0x1000), LEVEL0)"
    lines = [
        "#ifdef ZVE32X_SUPPORTED",
        *_umode_prologue(test_data, extra_mappings=(below, "sfence.vma")),
        ".option push",
        ".option arch, +zve32x",
    ]
    addr_reg, tmp_reg, stride_reg = test_data.int_regs.get_registers(3)

    # Unit-stride loads succeed, whether or not MXR is set; the SS page has R=0.
    for mxr in (0, 1):
        lines.extend([f"LI(x{tmp_reg}, SSTATUS_MXR)", tsbi_call(f"{'csrs' if mxr else 'csrc'} sstatus, x{tmp_reg}")])
        for sew in (8, 16, 32):
            lines.extend(
                [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)",
                    f"vsetivli x{tmp_reg}, {_VECTOR_VL}, e{sew}, m1, tu, mu",
                    test_data.add_testcase(f"vle{sew}_ss_page_mxr{mxr}", "cp_ss_vector_load", _CG),
                    f"vle{sew}.v v1, (x{addr_reg})",
                    f"vmv.x.s x{tmp_reg}, v1   # the first element read from the SS page",
                    write_sigupd(tmp_reg, test_data),
                ]
            )

    # Unit-stride stores fault, leaving the SS page unchanged. The stored data is all ones, which
    # the SS page does not hold, so the readback shows any write.
    for sew in (8, 16, 32):
        lines.extend(
            [
                f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)",
                f"vsetivli x{tmp_reg}, {_VECTOR_VL}, e{sew}, m1, tu, mu",
                "vmv.v.i v1, -1",
                test_data.add_testcase(f"vse{sew}_ss_page", "cp_ss_vector_store", _CG),
                f"vse{sew}.v v1, (x{addr_reg})",
                f"lw x{tmp_reg}, 0(x{addr_reg})   # unchanged",
                write_sigupd(tmp_reg, test_data),
            ]
        )

    def record_load() -> list[str]:
        """Record elements 0 and 2; element 2 is on the SS page whichever page the access began on."""
        return [
            f"vmv.x.s x{tmp_reg}, v1",
            write_sigupd(tmp_reg, test_data),
            "vslidedown.vi v3, v1, 2",
            f"vmv.x.s x{tmp_reg}, v3",
            write_sigupd(tmp_reg, test_data),
        ]

    def record_store() -> list[str]:
        """Record the word at the base and the SS page word element 2 targets, which must be unchanged.

        From the page below, elements 0 and 1 land on the read/write page before element 2 faults,
        so the first readback shows the all-ones data there.
        """
        return [
            f"lw x{tmp_reg}, 0(x{addr_reg})",
            write_sigupd(tmp_reg, test_data),
            f"lw x{tmp_reg}, 8(x{addr_reg})",
            write_sigupd(tmp_reg, test_data),
        ]

    # Strided and indexed accesses with rs1 on the SS page, and on the page below it with
    # the elements running up into it: 4-byte steps from 8 bytes below reach it by the third.
    for origin, base in (("on_ss", "ZICFISS_VA_SS + 0x800"), ("adjacent", "ZICFISS_VA_SS - 8")):
        for sew in (8, 32):
            lines.extend(
                [
                    f"LI(x{addr_reg}, {base})",
                    f"LI(x{stride_reg}, 4)",
                    f"vsetivli x{tmp_reg}, {_VECTOR_VL}, e{sew}, m1, tu, mu",
                    test_data.add_testcase(f"vlse{sew}_{origin}", "cp_ss_vector_strided", _CG),
                    f"vlse{sew}.v v1, (x{addr_reg}), x{stride_reg}",
                    *record_load(),
                ]
            )
        for mnemonic in ("vluxei8.v", "vsuxei8.v"):
            lines.extend(
                [
                    f"LI(x{addr_reg}, {base})",
                    f"vsetivli x{tmp_reg}, {_VECTOR_VL}, e8, m1, tu, mu",
                    "vid.v v2",
                    "vsll.vi v2, v2, 2   # byte offsets 0, 4, 8, ...",
                    *([] if mnemonic.startswith("vl") else ["vmv.v.i v1, -1   # data neither page holds"]),
                    test_data.add_testcase(f"{mnemonic.replace('.', '_')}_{origin}", "cp_ss_vector_indexed", _CG),
                    f"{mnemonic} v1, (x{addr_reg}), v2",
                    *(record_load() if mnemonic.startswith("vl") else record_store()),
                ]
            )

    lines.extend([".option pop", *_SATP_OFF, "#endif  // ZVE32X_SUPPORTED"])
    test_data.int_regs.return_registers([addr_reg, tmp_reg, stride_reg])
    return vm_section("cp_ss_vector_*", "Vector accesses to a shadow stack page", lines)


# ---------------------------------------------------------------------------
# cp_ssp_csr_gating_u / cp_ssamoswap_sse_gating
# ---------------------------------------------------------------------------


def _generate_sse_gating(test_data: TestData) -> list[str]:
    """Sweep the reachable (menvcfg.SSE, senvcfg.SSE) states from U-mode.

    menvcfg.SSE=0 makes senvcfg.SSE read-only zero, so (0, 1) is the same state as (0, 0).
    Each ssp access records rd, which an illegal-instruction exception leaves unchanged.
    """
    lines: list[str] = []
    for menvcfg, senvcfg in ((1, 1), (1, 0), (0, 0)):
        tag = f"m{menvcfg}s{senvcfg}"
        lines.extend(
            [
                f"# --- menvcfg.SSE={menvcfg}, senvcfg.SSE={senvcfg} ---",
                *_umode_prologue(test_data, menvcfg=menvcfg, senvcfg=senvcfg),
            ]
        )
        addr_reg, rd_reg = test_data.int_regs.get_registers(2)
        lines.append(f"LI(x{addr_reg}, ZICFISS_VA_SS)")
        # ssp CSR access: allowed only when both bits are set, else illegal-instruction.
        for op, form in (
            ("csrrw", f"csrrw x{rd_reg}, ssp, x{addr_reg}"),
            ("csrrs", f"csrrs x{rd_reg}, ssp, x{addr_reg}"),
            ("csrrc", f"csrrc x{rd_reg}, ssp, x{addr_reg}"),
            ("csrrwi", f"csrrwi x{rd_reg}, ssp, 1"),
            ("csrrsi", f"csrrsi x{rd_reg}, ssp, 1"),
            ("csrrci", f"csrrci x{rd_reg}, ssp, 1"),
        ):
            lines.extend(
                [
                    f"LI(x{rd_reg}, 0x0DDBA11)",
                    test_data.add_testcase(f"ssp_{op}_{tag}", "cp_ssp_csr_gating_u", _CG),
                    form,
                    write_sigupd(rd_reg, test_data),
                ]
            )
        test_data.int_regs.return_registers([addr_reg, rd_reg])

        if not (menvcfg and senvcfg):
            # SSAMOSWAP is AMO-encoded, so unlike the MOP-encoded instructions it traps
            # rather than becoming inert. The inert case is cp_ss_instr_inactive_u.
            lines.extend(ssamoswap_forms(test_data, "ZICFISS_VA_SS", f"gated_{tag}", "cp_ssamoswap_sse_gating", _CG))
        lines.extend(_SATP_OFF)
    return vm_section("cp_ssp_csr_gating_u", "SSE enable chain seen from U-mode", lines)


# ---------------------------------------------------------------------------
# cp_ss_instr_inactive_u / cp_ssrdp (inactive half)
# ---------------------------------------------------------------------------


def _generate_instr_inactive_u(test_data: TestData) -> list[str]:
    """MOP-encoded SS instructions stay inert in U-mode while Zicfiss is inactive for it.

    ssp is only writable while Zicfiss is active, so each ssp value is set first and the
    enable chain is cleared through T-SBI afterwards. The unmapped and mismatching ssp
    values would fault or raise a software check if the instruction were not inert.
    """
    coverpoint = "cp_ss_instr_inactive_u"
    lines = _umode_prologue(test_data)
    addr_reg, rd_reg = test_data.int_regs.get_registers(2)

    for gate, cleared in (("men1_sen0", ("senvcfg",)), ("men0_sen0", ("senvcfg", "menvcfg"))):
        for state, addr in (
            ("valid", "ZICFISS_VA_SS + 0x800"),
            ("unaligned", "ZICFISS_VA_SS + 0x804"),
            ("unmapped", "ZICFISS_VA_UNMAPPED"),
            ("mismatch", "ZICFISS_VA_SS + 0x800"),
        ):
            lines.extend([f"LI(x{addr_reg}, {addr})", f"csrw ssp, x{addr_reg}"])
            for csr in cleared:
                lines.extend(set_envcfg_sse(csr, 0, test_data, mode="U"))
            for form in MOP_FORMS:
                name = f"{form.name}_{gate}_{state}"
                if form.link_reg is None:  # SSRDP writes 0 while inactive
                    lines.extend(
                        [
                            test_data.add_testcase(name, "cp_ssrdp", _CG),
                            f"ssrdp x{rd_reg}",
                            write_sigupd(rd_reg, test_data),
                        ]
                    )
                    continue
                value = "0xDEADBEEF" if state == "mismatch" else "0"
                case = [f"LI({form.link_reg}, {value})", test_data.add_testcase(name, coverpoint, _CG), *ss_instr(form)]
                lines.extend(zcmop_only(form.compressed, case))
            lines.extend(
                [
                    *set_envcfg_sse("menvcfg", 1, test_data, mode="U"),
                    *set_envcfg_sse("senvcfg", 1, test_data, mode="U"),
                    f"csrr x{rd_reg}, ssp   # unchanged",
                    write_sigupd(rd_reg, test_data),
                ]
            )

    lines.extend(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg])
    return vm_section(coverpoint, "SS instructions inert in U-mode while Zicfiss is inactive", lines)


# ---------------------------------------------------------------------------
# Top-level generator
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "ZicfissU",
    required_extensions=["S", "Zicfiss"],
    # Zicfiss implies Zimop and Zaamo; name them for the assembler.
    march_extensions=["Zicfiss", "Zimop", "Zaamo"],
    extra_defines=["#define BOOT_TO_UMODE"],
)
def make_zicfissu(test_data: TestData) -> list[TestChunk]:
    """Generate the ZicfissU test suite.

    The sections go into three files, each under 100k instructions: the instructions and the
    SSE enable chain, the page types and non-SS accessors, and the page A/D bits.
    """
    test_chunks: list[TestChunk] = []
    for section, split_name in (
        (_generate_ssp_access, None),
        (_generate_push_pop, None),
        (_generate_fault_priority, None),
        (_generate_call_return, None),
        (_generate_ssrdp, None),
        (_generate_ssamoswap, None),
        (_generate_alignment, None),
        (_generate_sse_gating, None),
        (_generate_instr_inactive_u, None),
        (_generate_target_page, "pages"),
        (_generate_target_page_mxr_u, None),
        (_generate_page_crossing, None),
        (_generate_non_idempotent, None),
        (_generate_page_access, None),
        (_generate_vector, None),
        (_generate_page_ad_bits, "page_ad_bits"),
    ):
        tc = test_data.begin_test_chunk(split_name)
        tc.code.extend(page_table_data_section())
        tc.code.extend(section(test_data))
        test_chunks.append(test_data.end_test_chunk())
    return test_chunks
