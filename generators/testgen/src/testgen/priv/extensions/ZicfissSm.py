##################################
# priv/extensions/ZicfissSm.py
#
# Zicfiss (shadow stack) M-mode control-plane test generator.
# umer@riscv.org September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicfissSm test generator.

The ZicfissSm sheet of the testplan linked from docs/ctp/src/privmisc23.adoc: what needs
M-mode to set up or observe. Use of Zicfiss in M-mode is not supported by the
architecture, so what is testable here is the gating (menvcfg.SSE at the top of the
enable chain, and the read-only-zero propagation into senvcfg/henvcfg), PMP, satp.MODE=Bare,
the software-check exception taken in M-mode, and the one M-mode instruction behaviour the
spec does define -- SSAMOSWAP always faults at M, unless mstatus.MPRV lowers the effective
privilege mode.

The suite boots to M-mode, so medeleg is zero and every trap is taken in M-mode.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfissCommon import (
    MOP_FORMS,
    POP_FORMS,
    PTE_SS,
    PUSH_FORMS,
    SATP_OFF,
    SSAMOSWAP_WIDTHS,
    enable_translation,
    map_zicfiss_pages,
    page_table_data_section,
    set_envcfg_sse,
    ss_forms_against,
    ss_instr,
    ssamoswap_forms,
    ssamoswap_only,
    zcmop_only,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "ZicfissSm_cg"
_CSR_OPS = (
    ("csrrw", "csrrw x{rd}, ssp, x{v}"),
    ("csrrs", "csrrs x{rd}, ssp, x{v}"),
    ("csrrc", "csrrc x{rd}, ssp, x{v}"),
    ("csrrwi", "csrrwi x{rd}, ssp, 1"),
    ("csrrsi", "csrrsi x{rd}, ssp, 1"),
    ("csrrci", "csrrci x{rd}, ssp, 1"),
)


# ---------------------------------------------------------------------------
# cp_ssamoswap_mmode_fault
# ---------------------------------------------------------------------------


def _mprv_on(mask_reg: int, mpp: str) -> list[str]:
    """Set mstatus.MPRV with MPP=``mpp`` ("MPP_SMODE" or "MPP_MMODE")."""
    return [
        f"LI(x{mask_reg}, MSTATUS_MPP)",
        f"csrc mstatus, x{mask_reg}",
        f"LI(x{mask_reg}, MSTATUS_MPRV | {mpp})",
        f"csrs mstatus, x{mask_reg}",
    ]


def _mprv_off(mask_reg: int) -> list[str]:
    """Clear mstatus.MPRV. A trap from M-mode leaves MPP=M, so mret keeps MPRV=1 and lowers MPP;
    this must come straight after the access, before any other load or store."""
    return [f"LI(x{mask_reg}, MSTATUS_MPRV)", f"csrc mstatus, x{mask_reg}"]


def _generate_ssamoswap_mmode_fault(test_data: TestData) -> list[str]:
    """SSAMOSWAP faults whenever the effective privilege mode is M -- sweep menvcfg.SSE, satp.MODE
    and MPRV with MPP=M.

    The target is the physical address of the shadow stack page, which the translating leg
    maps as a valid, writable SS page. The location is seeded first, and both it and rd are
    recorded after the fault to show that neither changed.

    Then MPRV=1 with MPP=S, where the effective privilege mode is S (menvcfg.SSE=1): with
    satp.MODE=Bare the swap raises a store/AMO access fault (norm:satp_mode_bare), and with
    translation it swaps the S-mode SS page.
    """
    coverpoint = "cp_ssamoswap_mmode_fault"
    lines: list[str] = [
        comment_banner(coverpoint, "SSAMOSWAP.W/.D always faults when the effective privilege mode is M")
    ]
    for sse in (0, 1):
        for satp_mode in ("bare", "translating"):
            lines.append(f"# --- menvcfg.SSE={sse}, satp.MODE {satp_mode} ---")
            if satp_mode == "translating":
                lines.extend(
                    [
                        "#ifdef ZICFISS_VM_SUPPORTED",
                        *map_zicfiss_pages(test_data, user=False),
                        *enable_translation(test_data, mode="M"),
                        "#endif",
                    ]
                )
            else:
                lines.extend(SATP_OFF)
            lines.extend(set_envcfg_sse("menvcfg", sse, test_data, mode="M"))
            addr_reg, rd_reg, rs2_reg, mask_reg = test_data.int_regs.get_registers(4)
            for mprv in (0, 1):
                for width in SSAMOSWAP_WIDTHS:
                    tag = f"ssamoswap_{width}_mmode_sse{sse}_{satp_mode}{'_mprv_mpp_m' if mprv else ''}"
                    case = [
                        f"LA(x{addr_reg}, rvtest_zicfiss_ss_page)",
                        f"LI(x{rs2_reg}, 0x5EED5EED)",
                        f"SREG x{rs2_reg}, 0(x{addr_reg})   # seed the location",
                        f"LI(x{rd_reg}, 0x0DDBA11)   # rd must keep this value",
                        f"LI(x{rs2_reg}, 0x11223344)",
                        *(_mprv_on(mask_reg, "MPP_MMODE") if mprv else []),
                        test_data.add_testcase(tag, coverpoint, _CG),
                        f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                        *(_mprv_off(mask_reg) if mprv else []),
                        write_sigupd(rd_reg, test_data),
                        f"LREG x{rd_reg}, 0(x{addr_reg})   # memory must still hold the seed",
                        write_sigupd(rd_reg, test_data),
                    ]
                    body = ssamoswap_only(width, case)
                    lines.extend(
                        ["#ifdef ZICFISS_VM_SUPPORTED", *body, "#endif"] if satp_mode == "translating" else body
                    )
            test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, mask_reg])
    lines.extend(SATP_OFF)

    # MPRV=1 with MPP=S: the effective privilege mode is S.
    coverpoint = "cp_ssamoswap_mprv_s"
    lines.extend(
        [
            comment_banner(coverpoint, "SSAMOSWAP at M with MPRV=1, MPP=S follows the S-mode rules"),
            *set_envcfg_sse("menvcfg", 1, test_data, mode="M"),
        ]
    )
    for satp_mode in ("bare", "translating"):
        lines.append(f"# --- MPRV=1, MPP=S, satp.MODE {satp_mode} ---")
        if satp_mode == "translating":
            lines.extend(
                [
                    "#ifdef ZICFISS_VM_SUPPORTED",
                    *map_zicfiss_pages(test_data, user=False),
                    *enable_translation(test_data, mode="M"),
                    "#endif",
                ]
            )
        addr_reg, rd_reg, rs2_reg, mask_reg = test_data.int_regs.get_registers(4)
        # Bare: the physical address, which the swap must not change. Translating: the S-mode SS
        # page, which the swap must change.
        target = "rvtest_zicfiss_ss_page" if satp_mode == "bare" else "ZICFISS_VA_SS"
        for width in SSAMOSWAP_WIDTHS:
            case = [
                f"LA(x{addr_reg}, rvtest_zicfiss_ss_page)",
                f"LI(x{rs2_reg}, 0x5EED5EED)",
                f"SREG x{rs2_reg}, 0(x{addr_reg})   # seed the location",
                *([f"LI(x{addr_reg}, {target})"] if satp_mode == "translating" else []),
                f"LI(x{rd_reg}, 0x0DDBA11)   # kept if the swap faults",
                f"LI(x{rs2_reg}, 0x11223344)",
                *_mprv_on(mask_reg, "MPP_SMODE"),
                test_data.add_testcase(f"ssamoswap_{width}_mprv_mpp_s_{satp_mode}", coverpoint, _CG),
                f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                *_mprv_off(mask_reg),
                write_sigupd(rd_reg, test_data),
                f"LA(x{addr_reg}, rvtest_zicfiss_ss_page)",
                f"LREG x{rd_reg}, 0(x{addr_reg})   # the seed if the swap faulted",
                write_sigupd(rd_reg, test_data),
            ]
            body = ssamoswap_only(width, case)
            lines.extend(["#ifdef ZICFISS_VM_SUPPORTED", *body, "#endif"] if satp_mode == "translating" else body)
        test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, mask_reg])
    lines.extend(SATP_OFF)
    return lines


# ---------------------------------------------------------------------------
# cp_ssamoswap_mprv_non_idempotent
# ---------------------------------------------------------------------------


def _generate_mprv_non_idempotent(test_data: TestData) -> list[str]:
    """SSAMOSWAP in M-mode with mstatus.MPRV=1 and MPP=S accesses memory as S-mode.

    The effective privilege mode is then S, so the access is translated and the S-mode shadow
    stack rules apply: it completes on a PBMT=PMA shadow stack page and raises a store/AMO access
    fault on a PBMT=IO one, which is non-idempotent. PBMT=NC is left out for the reason given in
    cp_ss_non_idempotent. A trap taken in M-mode sets MPP to M and mret then lowers it, so MPRV
    and MPP are set before each swap, and MPRV is cleared before its result is recorded.
    """
    coverpoint = "cp_ssamoswap_mprv_non_idempotent"
    lines: list[str] = [
        comment_banner(coverpoint, "SSAMOSWAP at M with MPRV=1, MPP=S on PBMT=PMA and PBMT=IO shadow stack pages"),
        "#ifdef ZICFISS_VM_SUPPORTED",
        "#if defined(SVPBMT_SUPPORTED) && __riscv_xlen == 64",
        *set_envcfg_sse("menvcfg", 1, test_data, mode="M"),
    ]
    pbmte_reg = test_data.int_regs.get_register()
    lines.extend([f"LI(x{pbmte_reg}, MENVCFG_PBMTE)", f"csrs menvcfg, x{pbmte_reg}"])
    test_data.int_regs.return_registers([pbmte_reg])
    # pte.PBMT is bits [62:61]: 00 PMA, 10 IO.
    for tag, pbmt in (("pma", 0), ("io", 2)):
        lines.extend(
            [
                f"# --- pte.PBMT = {tag} ---",
                *map_zicfiss_pages(test_data, ss_perms=f"{PTE_SS} | ({pbmt} << 61)", user=False),
                *enable_translation(test_data, mode="M"),
            ]
        )
        addr_reg, rd_reg, rs2_reg, mask_reg = test_data.int_regs.get_registers(4)
        lines.extend([f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)", f"LI(x{rs2_reg}, 0x11223344)"])
        for width in SSAMOSWAP_WIDTHS:
            case = [
                f"LI(x{rd_reg}, 0x0DDBA11)   # kept if the swap faults",
                *_mprv_on(mask_reg, "MPP_SMODE"),
                "sfence.vma   # each swap walks, so the trace logs the PTE it used",
                test_data.add_testcase(f"ssamoswap_{width}_mprv_pbmt_{tag}", coverpoint, _CG),
                f"ssamoswap.{width} x{rd_reg}, x{rs2_reg}, (x{addr_reg})",
                *_mprv_off(mask_reg),
                write_sigupd(rd_reg, test_data),
            ]
            lines.extend(ssamoswap_only(width, case))
        test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg, mask_reg])
        lines.extend(SATP_OFF)
    pbmte_reg = test_data.int_regs.get_register()
    lines.extend(
        [
            f"LI(x{pbmte_reg}, MENVCFG_PBMTE)",
            f"csrc menvcfg, x{pbmte_reg}",
            "#endif  // SVPBMT_SUPPORTED && RV64",
            "#endif  // ZICFISS_VM_SUPPORTED",
        ]
    )
    test_data.int_regs.return_registers([pbmte_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_menvcfg_sse_gating / cp_menvcfg_sse_ss_page
# ---------------------------------------------------------------------------


def _generate_menvcfg_gating(test_data: TestData) -> list[str]:
    """menvcfg.SSE gates ssp CSR access, and the SS page encoding, for every mode below M.

    ssp is accessible from M-mode for both values of menvcfg.SSE, the positive control. From
    S-mode it is accessible only with menvcfg.SSE=1. Each access records rd, which an
    illegal-instruction exception leaves unchanged. With menvcfg.SSE=0 the xwr=010 encoding
    is reserved, so an ordinary load or store to such a page raises a page fault from S- and
    U-mode alike; with menvcfg.SSE=1 the page is an SS page, which loads may read and stores
    may not write, whatever senvcfg.SSE is.
    """
    lines: list[str] = [comment_banner("cp_menvcfg_sse_gating", "menvcfg.SSE gates ssp CSR access below M-mode")]
    rd_reg, val_reg = test_data.int_regs.get_registers(2)
    for sse in (0, 1):
        lines.extend(set_envcfg_sse("menvcfg", sse, test_data, mode="M"))
        for mode in ("M", "S"):
            lines.extend(["RVTEST_TSBI_GOTO_SMODE"] if mode == "S" else [])
            # An XLEN-aligned ssp value, different per mode so that each successful write shows
            lines.append(f"LI(x{val_reg}, {'0x2000' if mode == 'S' else '0x1000'})")
            for op, form in _CSR_OPS:
                lines.extend(
                    [
                        f"LI(x{rd_reg}, 0x0DDBA11)",
                        test_data.add_testcase(f"ssp_{op}_{mode.lower()}mode_sse{sse}", "cp_menvcfg_sse_gating", _CG),
                        form.format(rd=rd_reg, v=val_reg),
                        write_sigupd(rd_reg, test_data),
                    ]
                )
            lines.extend(["RVTEST_TSBI_GOTO_MMODE"] if mode == "S" else [])
    test_data.int_regs.return_registers([rd_reg, val_reg])

    # The SS page encoding, from S-mode (supervisor pages) and U-mode (user pages). Only
    # menvcfg.SSE makes xwr=010 reserved; senvcfg.SSE does not (norm:ssmp_menvcfg_sse), so with
    # menvcfg.SSE=1 and senvcfg.SSE=0 the page is still an SS page for U-mode ordinary accesses,
    # even though Zicfiss is inactive there.
    coverpoint = "cp_menvcfg_sse_ss_page"
    lines.extend(
        [
            comment_banner(coverpoint, "pte.xwr=010 is reserved below M-mode while menvcfg.SSE=0"),
            "#ifdef ZICFISS_VM_SUPPORTED",
        ]
    )
    for sse, senvcfg_sse in ((0, 0), (1, 1), (1, 0)):
        for mode in ("S", "U"):
            envcfg = [("senvcfg", 0), ("menvcfg", 0)] if not sse else [("menvcfg", 1), ("senvcfg", senvcfg_sse)]
            tag = f"sse{sse}" if sse == senvcfg_sse else "sse1_sen0"
            lines.extend(
                [
                    f"# --- menvcfg.SSE={sse}, senvcfg.SSE={senvcfg_sse}, {mode}-mode ---",
                    *map_zicfiss_pages(test_data, user=mode == "U"),
                    *enable_translation(test_data, mode="M"),
                    *[ln for csr, value in envcfg for ln in set_envcfg_sse(csr, value, test_data, mode="M")],
                    f"RVTEST_TSBI_GOTO_{mode}MODE",
                ]
            )
            addr_reg, rd_reg, val_reg = test_data.int_regs.get_registers(3)
            lines.extend(
                [
                    f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)",
                    f"LI(x{rd_reg}, 0x0DDBA11)   # kept if the load faults",
                    test_data.add_testcase(f"load_{mode.lower()}mode_{tag}", coverpoint, _CG),
                    f"LREG x{rd_reg}, 0(x{addr_reg})",
                    write_sigupd(rd_reg, test_data),
                    f"LI(x{val_reg}, 0x55)",
                    test_data.add_testcase(f"store_{mode.lower()}mode_{tag}", coverpoint, _CG),
                    f"SREG x{val_reg}, 0(x{addr_reg})",
                    "RVTEST_TSBI_GOTO_MMODE",
                    *SATP_OFF,
                ]
            )
            test_data.int_regs.return_registers([addr_reg, rd_reg, val_reg])
    lines.append("#endif  // ZICFISS_VM_SUPPORTED")
    return lines


# ---------------------------------------------------------------------------
# cp_envcfg_sse_rdonly0_senvcfg / cp_envcfg_sse_rdonly0_henvcfg / cp_envcfg_sse_rdonly0_virt
# ---------------------------------------------------------------------------


def _generate_envcfg_rdonly0(test_data: TestData) -> list[str]:
    """menvcfg.SSE=0 makes senvcfg.SSE and henvcfg.SSE read-only zero (leg A), and henvcfg.SSE=0
    makes senvcfg.SSE read-only zero when V=1 (leg B).

    Only the SSE bit is set (csrs) or cleared (csrc), so no other field changes. The henvcfg
    and V=1 cases need the hypervisor extension and are assembled only with H_SUPPORTED.
    """
    rd_reg, val_reg = test_data.int_regs.get_registers(2)
    lines: list[str] = [
        comment_banner("cp_envcfg_sse_rdonly0_*", "The SSE enable chain forces the lower SSE fields read-only zero"),
    ]

    # Leg A: menvcfg.SSE=0 and =1, then write both values into each child.
    for menvcfg_sse in (0, 1):
        lines.extend(set_envcfg_sse("menvcfg", menvcfg_sse, test_data, mode="M"))
        for csr in ("senvcfg", "henvcfg"):
            body: list[str] = []
            for written in (0, 1):
                op = "csrrs" if written else "csrrc"
                body.extend(
                    [
                        f"LI(x{val_reg}, {csr.upper()}_SSE)",
                        test_data.add_testcase(f"{csr}_sse_{op}_men{menvcfg_sse}", f"cp_envcfg_sse_rdonly0_{csr}", _CG),
                        f"{op} x{rd_reg}, {csr}, x{val_reg}",
                        f"csrr x{rd_reg}, {csr}   # SSE must read 0 when menvcfg.SSE=0",
                        write_sigupd(rd_reg, test_data),
                    ]
                )
            lines.extend(["#ifdef H_SUPPORTED", *body, "#endif"] if csr == "henvcfg" else body)

    # Leg B: menvcfg.SSE=1 (still set from leg A); with henvcfg.SSE=0, and =1 as the positive
    # control, write both values into senvcfg.SSE from VS-mode and read it back. Its coverpoint
    # is in ZicfissH_cg.
    # VS-mode reaches senvcfg only when hstateen0.ENVCFG is set (Ssstateen), and HS-mode reaches
    # hstateen0.ENVCFG only when mstateen0.ENVCFG is set (Smstateen).
    lines.extend(
        [
            "#ifdef H_SUPPORTED",
            "#ifdef SMSTATEEN_SUPPORTED",
            "#if __riscv_xlen == 64",
            f"LI(x{val_reg}, MSTATEEN0_HENVCFG)",
            f"csrs mstateen0, x{val_reg}",
            "#else",
            f"LI(x{val_reg}, MSTATEEN0H_HENVCFG)",
            f"csrs mstateen0h, x{val_reg}",
            "#endif",
            "#endif",
            "#ifdef SSSTATEEN_SUPPORTED",
            "#if __riscv_xlen == 64",
            f"LI(x{val_reg}, HSTATEEN0_SENVCFG)",
            f"csrs hstateen0, x{val_reg}",
            "#else",
            f"LI(x{val_reg}, HSTATEEN0H_SENVCFG)",
            f"csrs hstateen0h, x{val_reg}",
            "#endif",
            "#endif",
        ]
    )
    for henvcfg_sse in (0, 1):
        lines.extend(
            [
                f"LI(x{val_reg}, HENVCFG_SSE)",
                f"{'csrs' if henvcfg_sse else 'csrc'} henvcfg, x{val_reg}",
                "RVTEST_TSBI_GOTO_VSMODE",
            ]
        )
        for written in (0, 1):
            op = "csrrs" if written else "csrrc"
            lines.extend(
                [
                    f"LI(x{val_reg}, SENVCFG_SSE)",
                    test_data.add_testcase(
                        f"senvcfg_sse_{op}_vs_hen{henvcfg_sse}", "cp_envcfg_sse_rdonly0_virt", "ZicfissH_cg"
                    ),
                    f"{op} x{rd_reg}, senvcfg, x{val_reg}",
                    f"csrr x{rd_reg}, senvcfg   # SSE must read 0 when henvcfg.SSE=0 and V=1",
                    write_sigupd(rd_reg, test_data),
                ]
            )
        lines.append("RVTEST_TSBI_GOTO_MMODE")
    lines.append("#endif  // H_SUPPORTED")

    test_data.int_regs.return_registers([rd_reg, val_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_ss_pmp_permissions
# ---------------------------------------------------------------------------


def _generate_pmp_permissions(test_data: TestData) -> list[str]:
    """Shadow stack instructions require PMP read-write, including the read-only SSPOPCHK.

    Only M-mode can program PMP. Entry 0 covers the shadow stack page as one 4 KiB NAPOT
    region, so this needs NAPOT and a PMP granularity of at most 4 KiB; entry 1 grants
    everything else, and the lowest matching entry wins. The link register is set so that a
    pop would also mismatch, so the denied cases double as the fault-priority check.
    """
    coverpoint = "cp_ss_pmp_permissions"
    lines: list[str] = [
        comment_banner(coverpoint, "PMP read-write requirement and fault priority"),
        "#ifdef ZICFISS_VM_SUPPORTED",
        "#if defined(UDB_PMP_NAPOT_SUPPORTED) && UDB_PMP_GRANULARITY <= 12 && UDB_NUM_USABLE_PMP_ENTRIES >= 2",
    ]

    # pmp0cfg: A=NAPOT (0x18) plus the R/W bits under test. pmp1cfg = 0x1F allows the rest.
    # R=0 with W=1 is reserved, so it is not a configuration that can be tested.
    for tag, rw in (("none", 0x0), ("r", 0x1), ("rw", 0x3)):
        lines.extend(
            [
                f"# --- pmp0cfg R/W = {tag} ---",
                *enable_translation(test_data, mode="M"),
                *map_zicfiss_pages(test_data, user=False),
                *set_envcfg_sse("menvcfg", 1, test_data, mode="M"),
            ]
        )
        addr_reg, cfg_reg = test_data.int_regs.get_registers(2)
        lines.extend(
            [
                f"LA(x{addr_reg}, rvtest_zicfiss_ss_page)",
                f"srli x{addr_reg}, x{addr_reg}, 2",
                f"LI(x{cfg_reg}, 0x1FF)",
                f"or x{addr_reg}, x{addr_reg}, x{cfg_reg}   # NAPOT, 4 KiB",
                f"csrw pmpaddr0, x{addr_reg}",
                f"LI(x{addr_reg}, -1)",
                f"csrw pmpaddr1, x{addr_reg}",
                f"LI(x{cfg_reg}, {hex(0x1F00 | 0x18 | rw)})   # pmp0 NAPOT {tag}; pmp1 NAPOT RWX",
                f"csrw pmpcfg0, x{cfg_reg}",
                "sfence.vma",
                "RVTEST_TSBI_GOTO_SMODE",
            ]
        )
        test_data.int_regs.return_registers([addr_reg, cfg_reg])
        lines.extend(
            [
                *ss_forms_against(
                    test_data,
                    PUSH_FORMS + POP_FORMS,
                    "ZICFISS_VA_SS + 0x800",
                    "0x0BADF00D",
                    f"pmp_{tag}",
                    coverpoint,
                    _CG,
                ),
                *ssamoswap_forms(test_data, "ZICFISS_VA_SS", f"pmp_{tag}", coverpoint, _CG),
                "RVTEST_TSBI_GOTO_MMODE",
                *SATP_OFF,
            ]
        )
        addr_reg, cfg_reg = test_data.int_regs.get_registers(2)
        lines.extend(
            [
                f"LI(x{addr_reg}, -1)",
                f"csrw pmpaddr0, x{addr_reg}",
                f"LI(x{cfg_reg}, 0x1F)",
                f"csrw pmpcfg0, x{cfg_reg}   # restore the boot-time allow-all region",
                "sfence.vma",
            ]
        )
        test_data.int_regs.return_registers([addr_reg, cfg_reg])
    lines.append("#endif  // PMP NAPOT, granularity <= 4 KiB, at least 2 usable entries")
    lines.append("#endif  // ZICFISS_VM_SUPPORTED")
    return lines


# ---------------------------------------------------------------------------
# cp_ss_satp_bare
# ---------------------------------------------------------------------------


def _generate_satp_bare(test_data: TestData) -> list[str]:
    """Below M-mode, an SS instruction with satp.MODE=Bare raises a store/AMO access fault.

    ssp and the SSAMOSWAP address point at the shadow stack page's physical address. No page
    tables are involved, so this runs on configurations without Sv39/Sv32 too. Each testcase
    records ssp or rd, which the fault leaves unchanged.
    """
    coverpoint = "cp_ss_satp_bare"
    lines: list[str] = [
        comment_banner(coverpoint, "SS instructions in S- and U-mode with satp.MODE=Bare"),
        *SATP_OFF,
        *set_envcfg_sse("menvcfg", 1, test_data, mode="M"),
        *set_envcfg_sse("senvcfg", 1, test_data, mode="M"),
    ]
    addr_reg, data_reg, rd_reg = test_data.int_regs.get_registers(3)
    for mode in ("S", "U"):
        tag = f"{mode.lower()}mode_bare"
        lines.append(f"RVTEST_TSBI_GOTO_{mode}MODE")
        for form in PUSH_FORMS + POP_FORMS:
            case = [
                f"LA(x{addr_reg}, rvtest_zicfiss_ss_page + 0x800)",
                f"csrw ssp, x{addr_reg}",
                f"LI({form.link_reg}, 0x0BADF00D)",
                test_data.add_testcase(f"{form.name}_{tag}", coverpoint, _CG),
                *ss_instr(form),
                f"csrr x{rd_reg}, ssp",
                write_sigupd(rd_reg, test_data),
            ]
            lines.extend(zcmop_only(form.compressed, case))
        lines.extend([f"LA(x{addr_reg}, rvtest_zicfiss_ss_page)", f"LI(x{data_reg}, 0x11223344)"])
        for width in SSAMOSWAP_WIDTHS:
            lines.extend(
                ssamoswap_only(
                    width,
                    [
                        f"LI(x{rd_reg}, 0x0DDBA11)   # kept by the fault",
                        test_data.add_testcase(f"ssamoswap_{width}_{tag}", coverpoint, _CG),
                        f"ssamoswap.{width} x{rd_reg}, x{data_reg}, (x{addr_reg})",
                        write_sigupd(rd_reg, test_data),
                    ],
                )
            )
        lines.append("RVTEST_TSBI_GOTO_MMODE")
    test_data.int_regs.return_registers([addr_reg, data_reg, rd_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_ss_swcheck_mtval
# ---------------------------------------------------------------------------


def _generate_swcheck_mtval(test_data: TestData) -> list[str]:
    """An SSPOPCHK value mismatch in S-mode is taken in M-mode, reporting mtval = shadow stack fault.

    This suite boots to M-mode, where RVTEST_BOOT_TO_MMODE leaves medeleg at zero, so the
    software-check exception is not delegated.
    """
    coverpoint = "cp_ss_swcheck_mtval"
    lines = [
        comment_banner(coverpoint, "SSPOPCHK mismatch in S-mode reports the shadow stack fault code in mtval"),
        "#ifdef ZICFISS_VM_SUPPORTED",
        *enable_translation(test_data, mode="M"),
        *map_zicfiss_pages(test_data, user=False),
        *set_envcfg_sse("menvcfg", 1, test_data, mode="M"),
        "RVTEST_TSBI_GOTO_SMODE",
    ]
    addr_reg = test_data.int_regs.get_register()
    for pop in POP_FORMS:
        case = [
            f"LI(x{addr_reg}, ZICFISS_VA_SS + 0x800)",
            f"csrw ssp, x{addr_reg}",
            f"LI({pop.link_reg}, 0xA5A5A5A5)",
            f"sspush {pop.link_reg}",
            f"LI({pop.link_reg}, 0x0BADF00D)   # no longer matches what the shadow stack holds",
            test_data.add_testcase(f"{pop.name}_mismatch", coverpoint, _CG),
            *ss_instr(pop),
            f"csrr x{addr_reg}, ssp   # unchanged by the failed check",
            write_sigupd(addr_reg, test_data),
        ]
        lines.extend(zcmop_only(pop.compressed, case))
    lines.extend(["RVTEST_TSBI_GOTO_MMODE", *SATP_OFF, "#endif"])
    test_data.int_regs.return_registers([addr_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_ss_instr_inactive_m / cp_ss_instr_inactive_s
# ---------------------------------------------------------------------------


def _generate_instr_inactive(test_data: TestData) -> list[str]:
    """MOP-encoded SS instructions stay inert whenever Zicfiss is inactive.

    Leg A is M-mode, where Zicfiss is never supported, across every SSE state. Leg B
    executes in S-mode with menvcfg.SSE=0; ssp is set from M-mode because it is not
    accessible to S-mode then. Both legs repeat every instruction with a hostile ssp.
    """
    lines: list[str] = [
        comment_banner("cp_ss_instr_inactive_m/s", "SS instructions inert while Zicfiss is inactive"),
        "#ifdef ZICFISS_VM_SUPPORTED",
    ]
    for mode, menvcfg, senvcfg in (("m", 0, 0), ("m", 1, 0), ("m", 1, 1), ("s", 0, 0)):
        leg = f"{mode}_men{menvcfg}_sen{senvcfg}"
        # Clear senvcfg.SSE before menvcfg.SSE, and set it after, so the pair never
        # passes through the unreachable menvcfg.SSE=0, senvcfg.SSE=1 state.
        envcfg = [("menvcfg", menvcfg), ("senvcfg", senvcfg)]
        if not senvcfg:
            envcfg.reverse()
        lines.extend(
            [
                f"# --- {mode.upper()}-mode, menvcfg.SSE={menvcfg}, senvcfg.SSE={senvcfg} ---",
                *enable_translation(test_data, mode="M"),
                *map_zicfiss_pages(test_data, user=False),
                *[ln for csr, value in envcfg for ln in set_envcfg_sse(csr, value, test_data, mode="M")],
            ]
        )
        addr_reg, rd_reg = test_data.int_regs.get_registers(2)
        for state, addr in (
            ("valid", "ZICFISS_VA_SS + 0x800"),
            ("unaligned", "ZICFISS_VA_SS + 0x804"),
            ("unmapped", "ZICFISS_VA_UNMAPPED"),
            ("mismatch", "ZICFISS_VA_SS + 0x800"),
        ):
            lines.extend([f"LI(x{addr_reg}, {addr})", f"csrw ssp, x{addr_reg}"])
            lines.extend(["RVTEST_TSBI_GOTO_SMODE"] if mode == "s" else [])
            for form in MOP_FORMS:
                label = test_data.add_testcase(f"{form.name}_{leg}_{state}", f"cp_ss_instr_inactive_{mode}", _CG)
                if form.link_reg is None:  # SSRDP writes 0 while inactive
                    lines.extend([label, f"ssrdp x{rd_reg}", write_sigupd(rd_reg, test_data)])
                    continue
                value = "0xDEADBEEF" if state == "mismatch" else "0"
                lines.extend(zcmop_only(form.compressed, [f"LI({form.link_reg}, {value})", label, *ss_instr(form)]))
            lines.extend(["RVTEST_TSBI_GOTO_MMODE"] if mode == "s" else [])
            lines.extend([f"csrr x{rd_reg}, ssp   # unchanged", write_sigupd(rd_reg, test_data)])
        lines.extend(SATP_OFF)
        test_data.int_regs.return_registers([addr_reg, rd_reg])
    lines.append("#endif  // ZICFISS_VM_SUPPORTED")
    return lines


# ---------------------------------------------------------------------------
# Top-level generator
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "ZicfissSm",
    required_extensions=["S", "Zicfiss"],
    # Zicfiss implies Zimop and Zaamo; name them for the assembler.
    march_extensions=["Zicfiss", "Zimop", "Zaamo"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zicfisssm(test_data: TestData) -> list[TestChunk]:
    """Generate the ZicfissSm test suite."""
    test_chunks: list[TestChunk] = []
    for section in (
        _generate_ssamoswap_mmode_fault,
        _generate_mprv_non_idempotent,
        _generate_menvcfg_gating,
        _generate_envcfg_rdonly0,
        _generate_pmp_permissions,
        _generate_satp_bare,
        _generate_swcheck_mtval,
        _generate_instr_inactive,
    ):
        tc = test_data.begin_test_chunk()
        tc.code.extend(page_table_data_section())
        tc.code.extend(section(test_data))
        test_chunks.append(test_data.end_test_chunk())
    return test_chunks
