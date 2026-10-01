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

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfissCommon import (
    MOP_FORMS,
    POP_FORMS,
    PTE_RW,
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

_CG = "ZicfissU_cg"
_SATP_OFF = tsbi_call("csrw satp, x0")  # turn translation off from U-mode


def _umode_prologue(
    test_data: TestData,
    *,
    menvcfg: int = 1,
    senvcfg: int = 1,
    ss_perms: str = PTE_SS,
    ss_page_user: bool | None = None,
    extra_mappings: list[str] | None = None,
) -> list[str]:
    """Build the page tables and SSE state in S-mode, then enable translation from U-mode.

    The image map makes the test body a user page, so S-mode cannot fetch it once
    translation is on: an S-mode ``csrw satp`` here would fault on the next fetch. satp is
    therefore written from U-mode through T-SBI. The ecall is delegated to the S-mode T-SBI
    handler, which runs from the supervisor-only pages above rvtest_code_end, performs the
    write there and returns to U-mode, whose next fetch is from a user page.

    The S-mode trap handler records trap signatures in the signature region, which the image
    map makes user-accessible, so sstatus.SUM is set to let it write there.
    """
    return [
        "RVTEST_TSBI_GOTO_SMODE",
        *map_zicfiss_pages(ss_perms=ss_perms, user=True, ss_page_user=ss_page_user),
        *(extra_mappings or []),
        "LI(t0, SSTATUS_SUM)",
        "csrs sstatus, t0   # the S-mode handler writes trap signatures to user pages",
        *set_envcfg_sse("menvcfg", menvcfg, test_data, mode="S"),
        *set_envcfg_sse("senvcfg", senvcfg, test_data, mode="S"),
        "RVTEST_TSBI_GOTO_UMODE",
        "# Enable translation: T-SBI satp write from U-mode (see _umode_prologue)",
        "LA(t0, rvtest_Sroot_pg_tbl)",
        "srli t0, t0, 12",
        "LI(t1, ZICFISS_SATP_MODE)",
        "or t0, t0, t1",
        tsbi_call("csrw satp, t0"),
    ]


def _vm_section(title: str, description: str, lines: list[str]) -> list[str]:
    """A section banner, and ``lines`` guarded on the configuration supporting Sv39/Sv32."""
    return [comment_banner(title, description), "#ifdef ZICFISS_VM_SUPPORTED", *lines, "#endif"]


def _ssamoswap_forms(test_data: TestData, addr: str, addr_reg: int, tag: str, coverpoint: str) -> list[str]:
    """SSAMOSWAP.W, and SSAMOSWAP.D on RV64, against ``addr``."""
    rd_reg, rs2_reg = test_data.int_regs.get_registers(2)
    lines = [f"LI(x{addr_reg}, {addr})", f"LI(x{rs2_reg}, 0x11223344)"]
    for width in ("w", "d"):
        lines.extend(
            rv64_only(
                width,
                [
                    test_data.add_testcase(f"ssamoswap_{width}_{tag}", coverpoint, _CG),
                    f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                ],
            )
        )
    test_data.int_regs.return_registers([rd_reg, rs2_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_ssp_access / cp_ssp_low_bits_ro_zero
# ---------------------------------------------------------------------------


def _generate_ssp_access(test_data: TestData) -> list[str]:
    coverpoint = "cp_ssp_access"
    val_reg, rd_reg = test_data.int_regs.get_registers(2)
    lines = _umode_prologue(test_data)

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

    lines.append(_SATP_OFF)
    test_data.int_regs.return_registers([val_reg, rd_reg])
    return _vm_section(coverpoint, "ssp CSR access, width, and read-only-zero low bits", lines)


# ---------------------------------------------------------------------------
# cp_sspush / cp_sspopchk_match / cp_sspopchk_mismatch
# ---------------------------------------------------------------------------


def _generate_push_pop(test_data: TestData) -> list[str]:
    # Start ssp near the top of the SS page so pushes have room to grow down.
    ssp_top = "ZICFISS_VA_SS + 0x800"
    addr_reg, rd_reg = test_data.int_regs.get_registers(2)
    lines = _umode_prologue(test_data)
    save_x1, save_x5, save_lines = save_link_regs(test_data)
    lines.extend(save_lines)

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
            ]
            lines.extend(zcmop_only(pop.compressed, case))

    lines.extend(restore_link_regs(save_x1, save_x5))
    lines.append(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg, save_x1, save_x5])
    return _vm_section("cp_sspush/cp_sspopchk", "Shadow stack push and pop, matching and mismatching", lines)


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
    lines = _umode_prologue(test_data)
    save_x1, save_x5, save_lines = save_link_regs(test_data)
    lines.extend(save_lines)
    lines.extend(
        ss_forms_against(test_data, POP_FORMS, "ZICFISS_VA_UNMAPPED", "0x0BADF00D", "fault_priority", coverpoint, _CG)
    )
    lines.extend(restore_link_regs(save_x1, save_x5))
    lines.append(_SATP_OFF)
    test_data.int_regs.return_registers([save_x1, save_x5])
    return _vm_section(coverpoint, "Memory fault on the pop outranks the software-check exception", lines)


# ---------------------------------------------------------------------------
# cp_ss_call_return
# ---------------------------------------------------------------------------


def _generate_call_return(test_data: TestData) -> list[str]:
    """Nested non-leaf prologue/epilogue round trip, emitted straight-line (no asm loops)."""
    coverpoint = "cp_ss_call_return"
    addr_reg, rd_reg = test_data.int_regs.get_registers(2)
    lines = _umode_prologue(test_data)
    save_x1, save_x5, save_lines = save_link_regs(test_data)
    lines.extend(save_lines)
    lines.extend([f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)", f"csrw ssp, x{addr_reg}"])

    # Three nested prologues: each spills the link register to the shadow stack.
    for depth in range(3):
        lines.extend(
            [
                f"LI(x1, {hex(0xC0DE0000 + depth)})   # simulated return address at depth {depth}",
                test_data.add_testcase(f"call_prologue_depth{depth}", coverpoint, _CG),
                "sspush x1",
            ]
        )
    # Three matching epilogues, unwinding in reverse order.
    for depth in reversed(range(3)):
        lines.extend(
            [
                f"LI(x1, {hex(0xC0DE0000 + depth)})   # link register reloaded from the regular stack",
                test_data.add_testcase(f"return_epilogue_depth{depth}", coverpoint, _CG),
                "sspopchk x1",
            ]
        )
    lines.extend([f"csrr x{rd_reg}, ssp   # must be back at the starting ssp", write_sigupd(rd_reg, test_data)])

    # Subverted return address: the epilogue compare must catch it.
    lines.extend(
        [
            f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)",
            f"csrw ssp, x{addr_reg}",
            "LI(x1, 0xC0DE1234)",
            "sspush x1",
            "LI(x1, 0xBAD00BAD)   # attacker-supplied return address",
            test_data.add_testcase("return_subverted", coverpoint, _CG),
            "sspopchk x1",
        ]
    )

    lines.extend(restore_link_regs(save_x1, save_x5))
    lines.append(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg, save_x1, save_x5])
    return _vm_section(coverpoint, "Non-leaf prologue/epilogue round trip across nested depth", lines)


# ---------------------------------------------------------------------------
# cp_ssrdp
# ---------------------------------------------------------------------------


def _generate_ssrdp(test_data: TestData) -> list[str]:
    coverpoint = "cp_ssrdp"
    addr_reg, rd_reg = test_data.int_regs.get_registers(2)
    lines = _umode_prologue(test_data)
    save_x1, save_x5, save_lines = save_link_regs(test_data)
    lines.extend(save_lines)
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
        ]
    )
    lines.extend(restore_link_regs(save_x1, save_x5))
    lines.append(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg, save_x1, save_x5])
    return _vm_section(coverpoint, "SSRDP moves ssp into rd", lines)


# ---------------------------------------------------------------------------
# cp_ssamoswap
# ---------------------------------------------------------------------------


def _generate_ssamoswap(test_data: TestData) -> list[str]:
    coverpoint = "cp_ssamoswap"
    addr_reg, rd_reg, rs2_reg, seed_reg = test_data.int_regs.get_registers(4)
    lines = _umode_prologue(test_data)

    # The loaded value's bit 31 (the sign bit RV64 SSAMOSWAP.W extends) and, on RV64, whether
    # rs2[63:32] is non-zero, which SSAMOSWAP.W must ignore.
    for width in ("w", "d"):
        block: list[str] = []
        for msb in (0, 1):
            for upper in (0, 1):
                name = f"ssamoswap_{width}_msb{msb}_upper{upper}"
                case = [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS)",
                    f"LI(x{seed_reg}, {'0x80000000' if msb else '0x7FFFFFFF'})",
                    # Seed the SS page through a shadow stack store: ordinary stores to an
                    # SS page raise an access fault, so the seeding swap is the only way to
                    # give the location under test a defined value.
                    f"ssamoswap.{width} x{rd_reg}, x{seed_reg}, (x{addr_reg})",
                    f"LI(x{rs2_reg}, {'0xAAAAAAAA12345678' if upper else '0x12345678'})",
                    test_data.add_testcase(name, coverpoint, _CG),
                    f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                    write_sigupd(rd_reg, test_data),
                ]
                block.extend(["#if __riscv_xlen == 64", *case, "#endif"] if upper else case)
        lines.extend(rv64_only(width, block))

    for width in ("w", "d"):
        block = []
        # cp_ssamoswap_aqrl: all four ordering-bit encodings.
        for aq, rl, suffix in ((0, 0, ""), (0, 1, ".rl"), (1, 0, ".aq"), (1, 1, ".aqrl")):
            block.extend(
                [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS)",
                    f"LI(x{rs2_reg}, 0x5A5A5A5A)",
                    test_data.add_testcase(f"ssamoswap_{width}_aq{aq}_rl{rl}", "cp_ssamoswap_aqrl", _CG),
                    f"ssamoswap.{width}{suffix} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                ]
            )
        # cp_ssamoswap_reg_edges: all distinct, rd=x0, rs2=x0, rd==rs1.
        for name, form in (
            ("distinct", f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
            ("rd_x0", f"ssamoswap.{width} x0, x{rs2_reg}, (x{addr_reg})"),
            ("rs2_x0", f"ssamoswap.{width} x{rd_reg}, x0, (x{addr_reg})"),
            ("rd_eq_rs1", f"ssamoswap.{width} x{addr_reg}, x{rs2_reg}, (x{addr_reg})"),
        ):
            block.extend(
                [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS)",
                    f"LI(x{rs2_reg}, 0x3C3C3C3C)",
                    test_data.add_testcase(f"ssamoswap_{width}_{name}", "cp_ssamoswap_reg_edges", _CG),
                    form,
                ]
            )
        lines.extend(rv64_only(width, block))

    lines.append(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, seed_reg])
    return _vm_section(coverpoint, "SSAMOSWAP.W/.D swap, sign-extension, ordering bits and register edges", lines)


# ---------------------------------------------------------------------------
# cp_ss_address_alignment
# ---------------------------------------------------------------------------


def _generate_alignment(test_data: TestData) -> list[str]:
    """Sweep addr[2:0] for ssp and for SSAMOSWAP; see SSAMOSWAP_SWEEP_BASE."""
    addr_reg, rd_reg, rs2_reg = test_data.int_regs.get_registers(3)
    lines = _umode_prologue(test_data)
    save_x1, save_x5, save_lines = save_link_regs(test_data)
    lines.extend(save_lines)

    for offset in range(8):
        addr = f"ZICFISS_VA_SS + {hex(0x400 + offset)}"
        lines.extend(
            ss_forms_against(
                test_data, PUSH_FORMS, addr, "0xDEADBEEF", f"ssp_off{offset}", "cp_ss_address_alignment_ssp", _CG
            )
        )
        lines.extend(
            ss_forms_against(
                test_data, POP_FORMS, addr, "0xDEADBEEF", f"ssp_off{offset}", "cp_ss_address_alignment_pop", _CG
            )
        )

    # SSAMOSWAP address alignment sweep; see SSAMOSWAP_SWEEP_BASE.
    for width in ("w", "d"):
        block: list[str] = []
        for offset in ssamoswap_sweep_offsets(width):
            block.extend(
                [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS + {hex(SSAMOSWAP_SWEEP_BASE + offset)})",
                    f"LI(x{rs2_reg}, 0x11223344)",
                    test_data.add_testcase(f"ssamoswap_{width}_off{offset}", "cp_ss_address_alignment_swap", _CG),
                    f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                ]
            )
        lines.extend(rv64_only(width, block))

    lines.extend(restore_link_regs(save_x1, save_x5))
    lines.append(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, save_x1, save_x5])
    return _vm_section("cp_ss_address_alignment", "ssp and SSAMOSWAP address alignment sweep over addr[2:0]", lines)


# ---------------------------------------------------------------------------
# cp_ss_instr_target_page -- SS instructions against every kind of page
# ---------------------------------------------------------------------------


def _generate_target_page(test_data: TestData) -> list[str]:
    """Remap the shadow stack page with each of the eight pte.xwr encodings."""
    coverpoint = "cp_ss_instr_target_page"
    lines: list[str] = []
    for xwr, perms in XWR_PERMS.items():
        addr_reg = test_data.int_regs.get_register()
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        # Aim at the middle of the page: sspush decrements ssp before storing, so a
        # pointer at the page base would push into the preceding page instead.
        mid = "ZICFISS_VA_SS + 0x800"
        lines.extend(
            [
                f"# --- pte.xwr = {xwr} ---",
                *_umode_prologue(test_data, ss_perms=perms),
                *save_lines,
                *ss_forms_against(test_data, PUSH_FORMS + POP_FORMS, mid, "0xDEADBEEF", f"xwr{xwr}", coverpoint, _CG),
                *_ssamoswap_forms(test_data, mid, addr_reg, f"xwr{xwr}", coverpoint),
                *restore_link_regs(save_x1, save_x5),
                _SATP_OFF,
            ]
        )
        test_data.int_regs.return_registers([addr_reg, save_x1, save_x5])
    return _vm_section(coverpoint, "SS instructions against every pte.xwr encoding", lines)


def _generate_target_page_mxr_u(test_data: TestData) -> list[str]:
    """Sweep sstatus.MXR and the SS page's U bit against the SS instructions."""
    coverpoint = "cp_ss_instr_target_page_u_mxr"
    lines: list[str] = []
    for u_bit in (0, 1):
        addr_reg, mask_reg = test_data.int_regs.get_registers(2)
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        # The image is mapped user-accessible for the U-mode testcases; ss_page_user leaves
        # the SS page's U bit to this sweep.
        lines.extend(
            [
                f"# --- pte.U = {u_bit} ---",
                *_umode_prologue(test_data, ss_perms=PTE_SS + (" | PTE_U" if u_bit else ""), ss_page_user=False),
                *save_lines,
            ]
        )
        for mxr in (0, 1):
            tag = f"u{u_bit}_mxr{mxr}"
            lines.extend(
                [
                    f"LI(x{mask_reg}, SSTATUS_MXR)",
                    tsbi_call(f"{'csrs' if mxr else 'csrc'} sstatus, x{mask_reg}"),
                    *ss_forms_against(
                        test_data, PUSH_FORMS + POP_FORMS, "ZICFISS_VA_SS + 0x800", "0x4D4D4D4D", tag, coverpoint, _CG
                    ),
                    *_ssamoswap_forms(test_data, "ZICFISS_VA_SS + 0x800", addr_reg, tag, coverpoint),
                ]
            )
        lines.extend([*restore_link_regs(save_x1, save_x5), _SATP_OFF])
        test_data.int_regs.return_registers([addr_reg, mask_reg, save_x1, save_x5])
    return _vm_section(coverpoint, "MXR and pte.U axes on the shadow stack page", lines)


# ---------------------------------------------------------------------------
# cp_ss_page_crossing
# ---------------------------------------------------------------------------


def _generate_page_crossing(test_data: TestData) -> list[str]:
    """A push at a page base writes into the preceding page; a pop reads its own page."""
    coverpoint = "cp_ss_page_crossing"
    lines = _umode_prologue(test_data)
    save_x1, save_x5, save_lines = save_link_regs(test_data)
    lines.extend(save_lines)

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

    lines.extend(restore_link_regs(save_x1, save_x5))
    lines.append(_SATP_OFF)
    test_data.int_regs.return_registers([save_x1, save_x5])
    return _vm_section(coverpoint, "Shadow stack accesses that straddle a page boundary", lines)


# ---------------------------------------------------------------------------
# cp_ss_page_ad_bits
# ---------------------------------------------------------------------------


def _generate_page_ad_bits(test_data: TestData) -> list[str]:
    """D is required by the writing SS instructions but not by SSPOPCHK; A by all."""
    coverpoint = "cp_ss_page_ad_bits"
    lines: list[str] = []
    for a_bit, d_bit in ((0, 0), (1, 0), (0, 1), (1, 1)):
        perms = " | ".join(["PTE_W", "PTE_V"] + (["PTE_A"] if a_bit else []) + (["PTE_D"] if d_bit else []))
        tag = f"a{a_bit}_d{d_bit}"
        addr_reg = test_data.int_regs.get_register()
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        lines.extend(
            [
                f"# --- pte.A={a_bit}, pte.D={d_bit} ---",
                *_umode_prologue(test_data, ss_perms=perms),
                *save_lines,
                *ss_forms_against(
                    test_data, PUSH_FORMS + POP_FORMS, "ZICFISS_VA_SS + 0x800", "0xADADADAD", tag, coverpoint, _CG
                ),
                *_ssamoswap_forms(test_data, "ZICFISS_VA_SS + 0x800", addr_reg, tag, coverpoint),
                *restore_link_regs(save_x1, save_x5),
                _SATP_OFF,
            ]
        )
        test_data.int_regs.return_registers([addr_reg, save_x1, save_x5])
    return _vm_section(coverpoint, "PTE A/D bits on the shadow stack page", lines)


# ---------------------------------------------------------------------------
# cp_ss_non_idempotent
# ---------------------------------------------------------------------------


def _generate_non_idempotent(test_data: TestData) -> list[str]:
    """PBMT=IO makes the page non-idempotent, which SS instructions must reject."""
    coverpoint = "cp_ss_non_idempotent"
    lines = ["#if defined(SVPBMT_SUPPORTED) && __riscv_xlen == 64"]
    # pte.PBMT is bits [62:61]: 00 PMA, 01 NC, 10 IO.
    for tag, pbmt in (("pma", 0), ("nc", 1), ("io", 2)):
        addr_reg = test_data.int_regs.get_register()
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        lines.extend(
            [
                f"# --- pte.PBMT = {tag} ---",
                *_umode_prologue(test_data, ss_perms=f"{PTE_SS} | ({pbmt} << 61)"),
                *save_lines,
                *ss_forms_against(
                    test_data,
                    PUSH_FORMS + POP_FORMS,
                    "ZICFISS_VA_SS + 0x800",
                    "0x1D1D1D1D",
                    f"pbmt_{tag}",
                    coverpoint,
                    _CG,
                ),
                *_ssamoswap_forms(test_data, "ZICFISS_VA_SS + 0x800", addr_reg, f"pbmt_{tag}", coverpoint),
                *restore_link_regs(save_x1, save_x5),
                _SATP_OFF,
            ]
        )
        test_data.int_regs.return_registers([addr_reg, save_x1, save_x5])
    lines.append("#endif  // SVPBMT_SUPPORTED && RV64")
    return _vm_section(coverpoint, "Non-idempotent shadow stack memory via Svpbmt PBMT=IO", lines)


# ---------------------------------------------------------------------------
# cp_ss_page_access -- non-SS accessors against an SS page
# ---------------------------------------------------------------------------


def _generate_page_access(test_data: TestData) -> list[str]:
    addr_reg, data_reg, mxr_reg = test_data.int_regs.get_registers(3)
    lines = [*_umode_prologue(test_data), f"LI(x{addr_reg}, ZICFISS_VA_SS)"]

    def rv64(ops: list[str]) -> list[str]:
        return ["#if __riscv_xlen == 64", *ops, "#endif"]

    def access(mnemonic: str, form: str, coverpoint: str, tag: str = "", sig: bool = False) -> list[str]:
        name = f"{mnemonic.replace('.', '_')}_on_ss_page{tag}"
        return [
            test_data.add_testcase(name, coverpoint, _CG),
            form,
            *([write_sigupd(data_reg, test_data)] if sig else []),
        ]

    for mnemonic in ("sb", "sh", "sw", "sd"):
        store = [
            f"LI(x{data_reg}, 0xDEADBEEF)",
            *access(mnemonic, f"{mnemonic} x{data_reg}, 0(x{addr_reg})", "cp_ss_page_access_store"),
        ]
        lines.extend(rv64(store) if mnemonic == "sd" else store)

    for mxr in (0, 1):
        lines.extend([f"LI(x{mxr_reg}, SSTATUS_MXR)", tsbi_call(f"{'csrs' if mxr else 'csrc'} sstatus, x{mxr_reg}")])
        for mnemonic in ("lb", "lh", "lw", "lbu", "lhu", "ld", "lwu"):
            load = access(
                mnemonic, f"{mnemonic} x{data_reg}, 0(x{addr_reg})", "cp_ss_page_access_load", f"_mxr{mxr}", sig=True
            )
            lines.extend(rv64(load) if mnemonic in ("ld", "lwu") else load)

    # Zicfiss requires Zaamo, so the ordinary AMOs are always present.
    for mnemonic in ("amoswap.w", "amoadd.w", "amoor.w", "amoswap.d", "amoadd.d"):
        amo = [
            f"LI(x{data_reg}, 0x1)",
            *access(mnemonic, f"{mnemonic} x{data_reg}, x{data_reg}, (x{addr_reg})", "cp_ss_page_access_amo"),
        ]
        lines.extend(rv64(amo) if mnemonic.endswith(".d") else amo)

    # Cache-block ops are themselves gated by menvcfg/senvcfg CBIE/CBCFE/CBZE. Without
    # those enabled the CBO would trap on its own gating rather than on the SS page.
    lines.extend(
        [
            f"LI(x{data_reg}, 0xD0)   # CBIE=01, CBCFE=1, CBZE=1",
            tsbi_call(f"csrs menvcfg, x{data_reg}"),
            tsbi_call(f"csrs senvcfg, x{data_reg}"),
            "#ifdef ZICBOM_SUPPORTED",
            ".option push",
            ".option arch, +zicbom",
        ]
    )
    for mnemonic in ("cbo.clean", "cbo.flush", "cbo.inval"):
        lines.extend(access(mnemonic, f"{mnemonic} (x{addr_reg})", "cp_ss_page_access_cbo"))
    lines.extend([".option pop", "#endif", "#ifdef ZICBOZ_SUPPORTED", ".option push", ".option arch, +zicboz"])
    lines.extend(access("cbo.zero", f"cbo.zero (x{addr_reg})", "cp_ss_page_access_cboz"))
    lines.extend([".option pop", "#endif", "#ifdef ZALRSC_SUPPORTED", ".option push", ".option arch, +a"])
    for mnemonic in ("lr.w", "sc.w", "lr.d", "sc.d"):
        form = (
            f"{mnemonic} x{data_reg}, (x{addr_reg})"
            if mnemonic.startswith("lr")
            else f"{mnemonic} x{data_reg}, x{data_reg}, (x{addr_reg})"
        )
        lrsc = access(mnemonic, form, "cp_ss_page_access_lrsc")
        lines.extend(rv64(lrsc) if mnemonic.endswith(".d") else lrsc)
    lines.extend([".option pop", "#endif", "#ifdef ZACAS_SUPPORTED", ".option push", ".option arch, +zacas"])
    for mnemonic in ("amocas.w", "amocas.d"):
        cas = [
            f"LI(x{data_reg}, 0x1)",
            *access(mnemonic, f"{mnemonic} x{data_reg}, x{data_reg}, (x{addr_reg})", "cp_ss_page_access_amocas"),
        ]
        lines.extend(rv64(cas) if mnemonic.endswith(".d") else cas)
    lines.extend([".option pop", "#endif"])

    lines.append(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, data_reg, mxr_reg])
    return _vm_section("cp_ss_page_access", "Non-SS accessors against an SS page", lines)


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
    addr_reg, tmp_reg, stride_reg = test_data.int_regs.get_registers(3)
    below = f"ZICFISS_PTE_SETUP(rvtest_zicfiss_rw_page, ({PTE_RW} | PTE_U), (ZICFISS_VA_SS - 0x1000), LEVEL0)"
    lines = [
        "#ifdef ZVE32X_SUPPORTED",
        *_umode_prologue(test_data, extra_mappings=[below, "sfence.vma"]),
        ".option push",
        ".option arch, +zve32x",
    ]

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

    # Unit-stride stores fault.
    for sew in (8, 16, 32):
        lines.extend(
            [
                f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)",
                f"vsetivli x{tmp_reg}, {_VECTOR_VL}, e{sew}, m1, tu, mu",
                test_data.add_testcase(f"vse{sew}_ss_page", "cp_ss_vector_store", _CG),
                f"vse{sew}.v v1, (x{addr_reg})",
            ]
        )

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
                ]
            )
        for mnemonic in ("vluxei8.v", "vsuxei8.v"):
            lines.extend(
                [
                    f"LI(x{addr_reg}, {base})",
                    f"vsetivli x{tmp_reg}, {_VECTOR_VL}, e8, m1, tu, mu",
                    "vid.v v2",
                    "vsll.vi v2, v2, 2   # byte offsets 0, 4, 8, ...",
                    test_data.add_testcase(f"{mnemonic.replace('.', '_')}_{origin}", "cp_ss_vector_indexed", _CG),
                    f"{mnemonic} v1, (x{addr_reg}), v2",
                ]
            )

    lines.extend([".option pop", _SATP_OFF, "#endif  // ZVE32X_SUPPORTED"])
    test_data.int_regs.return_registers([addr_reg, tmp_reg, stride_reg])
    return _vm_section("cp_ss_vector_*", "Vector accesses to a shadow stack page", lines)


# ---------------------------------------------------------------------------
# cp_ssp_csr_gating_u / cp_ssamoswap_sse_gating
# ---------------------------------------------------------------------------


def _generate_sse_gating(test_data: TestData) -> list[str]:
    """Sweep the reachable (menvcfg.SSE, senvcfg.SSE) states from U-mode.

    menvcfg.SSE=0 makes senvcfg.SSE read-only zero, so (0, 1) is the same state as (0, 0).
    """
    lines: list[str] = []
    for menvcfg, senvcfg in ((1, 1), (1, 0), (0, 0)):
        tag = f"m{menvcfg}s{senvcfg}"
        addr_reg, rd_reg = test_data.int_regs.get_registers(2)
        lines.extend(
            [
                f"# --- menvcfg.SSE={menvcfg}, senvcfg.SSE={senvcfg} ---",
                *_umode_prologue(test_data, menvcfg=menvcfg, senvcfg=senvcfg),
                f"LI(x{addr_reg}, ZICFISS_VA_SS)",
            ]
        )
        # ssp CSR access: allowed only when both bits are set, else illegal-instruction.
        for op, form in (
            ("csrrw", f"csrrw x{rd_reg}, ssp, x{addr_reg}"),
            ("csrrs", f"csrrs x{rd_reg}, ssp, x{addr_reg}"),
            ("csrrc", f"csrrc x{rd_reg}, ssp, x{addr_reg}"),
            ("csrrwi", f"csrrwi x{rd_reg}, ssp, 1"),
            ("csrrsi", f"csrrsi x{rd_reg}, ssp, 1"),
            ("csrrci", f"csrrci x{rd_reg}, ssp, 1"),
        ):
            lines.extend([test_data.add_testcase(f"ssp_{op}_{tag}", "cp_ssp_csr_gating_u", _CG), form])

        if not (menvcfg and senvcfg):
            # SSAMOSWAP is AMO-encoded, so unlike the MOP-encoded instructions it traps
            # rather than becoming inert. The inert case is cp_ss_instr_inactive_u.
            lines.extend(
                _ssamoswap_forms(test_data, "ZICFISS_VA_SS", addr_reg, f"gated_{tag}", "cp_ssamoswap_sse_gating")
            )
        lines.append(_SATP_OFF)
        test_data.int_regs.return_registers([addr_reg, rd_reg])
    return _vm_section("cp_ssp_csr_gating_u", "SSE enable chain seen from U-mode", lines)


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
    addr_reg, rd_reg = test_data.int_regs.get_registers(2)
    lines = _umode_prologue(test_data)
    save_x1, save_x5, save_lines = save_link_regs(test_data)
    lines.extend(save_lines)

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
            lines.extend(set_envcfg_sse("menvcfg", 1, test_data, mode="U"))
            lines.extend(set_envcfg_sse("senvcfg", 1, test_data, mode="U"))
            lines.extend([f"csrr x{rd_reg}, ssp   # unchanged", write_sigupd(rd_reg, test_data)])

    lines.extend(restore_link_regs(save_x1, save_x5))
    lines.append(_SATP_OFF)
    test_data.int_regs.return_registers([addr_reg, rd_reg, save_x1, save_x5])
    return _vm_section(coverpoint, "SS instructions inert in U-mode while Zicfiss is inactive", lines)


# ---------------------------------------------------------------------------
# Top-level generator
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "ZicfissU",
    required_extensions=["S", "Zicfiss"],
    # Zicfiss implies Zimop and Zaamo; name them for the assembler.
    march_extensions=["Zicfiss", "Zimop", "Zaamo"],
)
def make_zicfissu(test_data: TestData) -> list[TestChunk]:
    """Generate the ZicfissU test suite."""
    test_chunks: list[TestChunk] = []
    for section in (
        _generate_ssp_access,
        _generate_push_pop,
        _generate_fault_priority,
        _generate_call_return,
        _generate_ssrdp,
        _generate_ssamoswap,
        _generate_alignment,
        _generate_target_page,
        _generate_target_page_mxr_u,
        _generate_page_crossing,
        _generate_page_ad_bits,
        _generate_non_idempotent,
        _generate_page_access,
        _generate_vector,
        _generate_sse_gating,
        _generate_instr_inactive_u,
    ):
        tc = test_data.begin_test_chunk()
        tc.code.extend(page_table_data_section())
        tc.code.extend(section(test_data))
        test_chunks.append(test_data.end_test_chunk())
    return test_chunks
