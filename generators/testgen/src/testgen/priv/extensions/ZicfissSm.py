##################################
# priv/extensions/ZicfissSm.py
#
# Zicfiss (shadow stack) M-mode control-plane test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicfissSm test generator.

Covers the ZicfissSm sheet of the simplified Zicfiss testplan: the M-mode control
plane. Use of Zicfiss in M-mode is not supported by the architecture, so what is
testable here is the gating (menvcfg.SSE at the top of the enable chain, and the
read-only-zero propagation into senvcfg/henvcfg) plus the one M-mode instruction
behaviour the spec does define — SSAMOSWAP always faults at M.

"""

from __future__ import annotations

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfissCommon import (
    GOTO_MMODE,
    GOTO_SMODE,
    GOTO_UMODE,
    SSE_BIT,
    both_xlens,
    identity_map_only,
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

_CG = "ZicfissSm_cg"

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
_MOP_FORMS = _PUSH_FORMS + _POP_FORMS + [("ssrdp", False, "ssrdp")]


# ---------------------------------------------------------------------------
# cp_ssamoswap_mmode_fault
# ---------------------------------------------------------------------------


def _generate_ssamoswap_mmode_fault(test_data: TestData) -> list[str]:
    """SSAMOSWAP at M faults unconditionally — sweep menvcfg.SSE and satp.MODE."""
    coverpoint = "cp_ssamoswap_mmode_fault"

    def build(xlen: int) -> list[str]:
        addr_reg, rd_reg, rs2_reg = test_data.int_regs.get_registers(3)
        lines: list[str] = []

        for sse in (0, 1):
            for satp_mode in ("bare", "translating"):
                tag = f"sse{sse}_{satp_mode}"
                lines.extend(set_envcfg_sse("menvcfg", sse, test_data, mode="M"))
                if satp_mode == "translating":
                    # M-mode never translates, so this only moves satp.MODE off Bare
                    # for the coverage bin. Deliberately no SS page is created.
                    lines.extend(identity_map_only(xlen))
                    lines.extend(satp_setup(xlen))
                else:
                    lines.extend(["csrwi satp, 0", "sfence.vma"])

                lines.extend(
                    [
                        f"LA(x{addr_reg}, scratch)",
                        f"LI(x{rs2_reg}, 0x11223344)",
                        test_data.add_testcase(f"ssamoswap_w_mmode_{tag}_rv{xlen}", coverpoint, _CG),
                        *ss_insn(f"ssamoswap.w x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
                    ]
                )
                if xlen == 64:
                    lines.extend(
                        [
                            test_data.add_testcase(f"ssamoswap_d_mmode_{tag}_rv{xlen}", coverpoint, _CG),
                            *ss_insn(f"ssamoswap.d x{rd_reg}, x{rs2_reg}, (x{addr_reg})"),
                        ]
                    )

        lines.extend(["csrwi satp, 0", "sfence.vma"])
        test_data.int_regs.return_registers([addr_reg, rd_reg, rs2_reg])
        return lines

    return [
        comment_banner(coverpoint, "SSAMOSWAP.W/.D always faults when the effective privilege mode is M"),
        *both_xlens(build),
    ]


# ---------------------------------------------------------------------------
# cp_menvcfg_sse_gating
# ---------------------------------------------------------------------------


def _generate_menvcfg_gating(test_data: TestData) -> list[str]:
    """menvcfg.SSE gates ssp CSR access for every mode below M."""
    coverpoint = "cp_menvcfg_sse_gating"
    rd_reg, val_reg = test_data.int_regs.get_registers(2)
    lines: list[str] = [comment_banner(coverpoint, "menvcfg.SSE gates ssp CSR access below M-mode")]

    for sse in (0, 1):
        lines.extend(set_envcfg_sse("menvcfg", sse, test_data, mode="M"))
        # M-mode: ssp is reachable regardless of menvcfg.SSE (the rule is scoped to
        # "privilege mode less than M"), so this leg is the positive control.
        ops = (
            ("csrrw", "csrrw x{rd}, ssp, x{v}"),
            ("csrrs", "csrrs x{rd}, ssp, x{v}"),
            ("csrrc", "csrrc x{rd}, ssp, x{v}"),
            ("csrrwi", "csrrwi x{rd}, ssp, 1"),
            ("csrrsi", "csrrsi x{rd}, ssp, 1"),
            ("csrrci", "csrrci x{rd}, ssp, 1"),
        )
        lines.append(f"LI(x{val_reg}, 0x1000)")
        for op, form in ops:
            lines.extend(
                [
                    test_data.add_testcase(f"ssp_{op}_mmode_sse{sse}", coverpoint, _CG),
                    form.format(rd=rd_reg, v=val_reg),
                ]
            )
        # S-mode: illegal-instruction when menvcfg.SSE=0, allowed when 1.
        lines.extend([GOTO_SMODE, f"LI(x{val_reg}, 0x2000)"])
        for op, form in ops:
            lines.extend(
                [
                    test_data.add_testcase(f"ssp_{op}_smode_sse{sse}", coverpoint, _CG),
                    form.format(rd=rd_reg, v=val_reg),
                ]
            )
        lines.append(GOTO_MMODE)

    test_data.int_regs.return_registers([rd_reg, val_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_envcfg_sse_rdonly0_senvcfg / cp_envcfg_sse_rdonly0_henvcfg
# ---------------------------------------------------------------------------


def _generate_envcfg_rdonly0(test_data: TestData) -> list[str]:
    """With menvcfg.SSE=0, senvcfg.SSE and henvcfg.SSE are read-only zero regardless of what is written.

    The henvcfg leg needs the hypervisor extension, so it is assembled only with H_SUPPORTED.
    """
    rd_reg, val_reg = test_data.int_regs.get_registers(2)
    lines: list[str] = [
        comment_banner("cp_envcfg_sse_rdonly0_*", "menvcfg.SSE=0 forces senvcfg.SSE and henvcfg.SSE read-only zero"),
    ]

    for csr in ("senvcfg", "henvcfg"):
        coverpoint = f"cp_envcfg_sse_rdonly0_{csr}"
        body: list[str] = []
        for menvcfg_sse in (0, 1):
            body.extend(set_envcfg_sse("menvcfg", menvcfg_sse, test_data, mode="M"))
            for written in (0, 1):
                tag = f"men{menvcfg_sse}_wrote{written}"
                # csrrw writes the whole register; csrrs sets just the SSE bit.
                body.extend(
                    [
                        f"LI(x{val_reg}, {hex(written << SSE_BIT)})",
                        test_data.add_testcase(f"{csr}_sse_csrrw_{tag}", coverpoint, _CG),
                        f"csrrw x{rd_reg}, {csr}, x{val_reg}",
                        f"csrr x{rd_reg}, {csr}   # SSE must read 0 when menvcfg.SSE=0",
                        write_sigupd(rd_reg, test_data),
                    ]
                )
                if written:
                    body.extend(
                        [
                            f"LI(x{val_reg}, {hex(1 << SSE_BIT)})",
                            test_data.add_testcase(f"{csr}_sse_csrrs_{tag}", coverpoint, _CG),
                            f"csrrs x{rd_reg}, {csr}, x{val_reg}",
                            f"csrr x{rd_reg}, {csr}",
                            write_sigupd(rd_reg, test_data),
                        ]
                    )
        lines.extend(["#ifdef H_SUPPORTED", *body, "#endif"] if csr == "henvcfg" else body)

    test_data.int_regs.return_registers([rd_reg, val_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_sspopchk_fault_priority_pmp
# ---------------------------------------------------------------------------


def _generate_pmp_permissions(test_data: TestData) -> list[str]:
    """Shadow stack instructions require PMP read-write, including the read-only SSPOPCHK.

    Only M-mode can program PMP. Entry 0 covers the shadow stack page and entry 1 grants
    everything else; the lowest matching entry wins. The denied case doubles as the
    fault-priority check, since the link register is set to also mismatch.
    """
    coverpoint = "cp_ss_pmp_permissions"
    lines: list[str] = [comment_banner(coverpoint, "PMP read-write requirement and fault priority")]

    # pmp0cfg: A=NAPOT (0x18) plus the R/W bits under test. pmp1cfg = 0x1F allows the rest.
    # R=0 with W=1 is reserved, so it is not a configuration that can be tested.
    for tag, rw in (("none", 0x0), ("r", 0x1), ("rw", 0x3)):

        def build(xlen: int, rw: int = rw, tag: str = tag) -> list[str]:
            ss_va, _, _ = va_for(xlen)
            ssp_top = ss_va + 0x800
            addr_reg, cfg_reg = test_data.int_regs.get_registers(2)
            cfg = 0x1F00 | 0x18 | rw
            block = [
                *satp_setup(xlen),
                *map_zicfiss_pages(xlen, user=False),
                *set_envcfg_sse("menvcfg", 1, test_data, mode="M"),
                f"LA(x{addr_reg}, rvtest_zicfiss_ss_page)",
                f"srli x{addr_reg}, x{addr_reg}, 2",
                f"LI(x{cfg_reg}, 0x1FF)",
                f"or x{addr_reg}, x{addr_reg}, x{cfg_reg}   # NAPOT, 4 KiB",
                f"csrw pmpaddr0, x{addr_reg}",
                f"LI(x{addr_reg}, -1)",
                f"csrw pmpaddr1, x{addr_reg}",
                f"LI(x{cfg_reg}, {hex(cfg)})   # pmp0 NAPOT {tag}; pmp1 NAPOT RWX",
                f"csrw pmpcfg0, x{cfg_reg}",
                "sfence.vma",
                GOTO_SMODE,
            ]
            save_x1, save_x5, save_lines = save_link_regs(test_data)
            block.extend(save_lines)
            for mnemonic, compressed, name in _PUSH_FORMS + _POP_FORMS:
                reg = "x1" if "x1" in mnemonic else "x5"
                block.extend(
                    [
                        f"LI(x{addr_reg}, {hex(ssp_top)})",
                        f"csrw ssp, x{addr_reg}",
                        f"LI({reg}, 0x0BADF00D)   # would also mismatch, so the fault must win",
                        test_data.add_testcase(f"{name}_pmp_{tag}_rv{xlen}", coverpoint, _CG),
                        *ss_insn(mnemonic, compressed=compressed),
                    ]
                )
            for width in ["w"] + (["d"] if xlen == 64 else []):
                block.extend(
                    [
                        f"LI(x{addr_reg}, {hex(ss_va)})",
                        f"LI(x{cfg_reg}, 0x11223344)",
                        test_data.add_testcase(f"ssamoswap_{width}_pmp_{tag}_rv{xlen}", coverpoint, _CG),
                        *ss_insn(f"ssamoswap.{width} x{cfg_reg}, x{cfg_reg}, (x{addr_reg})"),
                    ]
                )
            block.extend(restore_link_regs(save_x1, save_x5))
            block.extend(teardown_vm("M"))
            block.extend(
                [
                    f"LI(x{addr_reg}, -1)",
                    f"csrw pmpaddr0, x{addr_reg}",
                    f"LI(x{cfg_reg}, 0x1F)",
                    f"csrw pmpcfg0, x{cfg_reg}   # restore the boot-time allow-all region",
                    "sfence.vma",
                ]
            )
            test_data.int_regs.return_registers([addr_reg, cfg_reg, save_x1, save_x5])
            return block

        lines.append(f"# --- pmp0cfg R/W = {tag} ---")
        lines.extend(both_xlens(build))
    return lines


# ---------------------------------------------------------------------------
# cp_ss_satp_bare
# ---------------------------------------------------------------------------


def _generate_satp_bare(test_data: TestData) -> list[str]:
    """Below M-mode, an SS instruction with satp.MODE=Bare raises a store/AMO access fault."""
    coverpoint = "cp_ss_satp_bare"
    lines: list[str] = [comment_banner(coverpoint, "SS instructions in S- and U-mode with satp.MODE=Bare")]

    def build(xlen: int) -> list[str]:
        addr_reg, data_reg = test_data.int_regs.get_registers(2)
        block = [
            "csrwi satp, 0",
            "sfence.vma",
            *set_envcfg_sse("menvcfg", 1, test_data, mode="M"),
            *set_envcfg_sse("senvcfg", 1, test_data, mode="M"),
        ]
        save_x1, save_x5, save_lines = save_link_regs(test_data)
        block.extend(save_lines)
        for mode in ("S", "U"):
            block.append(GOTO_SMODE if mode == "S" else GOTO_UMODE)
            tag = f"{mode.lower()}mode_bare_rv{xlen}"
            for mnemonic, compressed, name in _PUSH_FORMS + _POP_FORMS:
                reg = "x1" if "x1" in mnemonic else "x5"
                block.extend(
                    [
                        f"LA(x{addr_reg}, rvtest_zicfiss_ss_page + 0x800)",
                        f"csrw ssp, x{addr_reg}",
                        f"LI({reg}, 0x0BADF00D)",
                        test_data.add_testcase(f"{name}_{tag}", coverpoint, _CG),
                        *ss_insn(mnemonic, compressed=compressed),
                    ]
                )
            block.extend([f"LA(x{addr_reg}, rvtest_zicfiss_ss_page)", f"LI(x{data_reg}, 0x11223344)"])
            for width in ["w"] + (["d"] if xlen == 64 else []):
                block.extend(
                    [
                        test_data.add_testcase(f"ssamoswap_{width}_{tag}", coverpoint, _CG),
                        *ss_insn(f"ssamoswap.{width} x{data_reg}, x{data_reg}, (x{addr_reg})"),
                    ]
                )
            block.append(GOTO_MMODE)
        block.extend(restore_link_regs(save_x1, save_x5))
        test_data.int_regs.return_registers([addr_reg, data_reg, save_x1, save_x5])
        return block

    lines.extend(both_xlens(build))
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
    lines: list[str] = [comment_banner("cp_ss_instr_inactive_m/s", "SS instructions inert while Zicfiss is inactive")]

    for mode, menvcfg, senvcfg in (("m", 0, 0), ("m", 1, 0), ("m", 1, 1), ("s", 0, 0)):
        leg = f"{mode}_men{menvcfg}_sen{senvcfg}"

        def build(
            xlen: int, mode: str = mode, leg: str = leg, menvcfg: int = menvcfg, senvcfg: int = senvcfg
        ) -> list[str]:
            ss_va, _, _ = va_for(xlen)
            addr_reg, rd_reg = test_data.int_regs.get_registers(2)
            # Clear senvcfg.SSE before menvcfg.SSE, and set it after, so the pair never
            # passes through the unreachable menvcfg.SSE=0, senvcfg.SSE=1 state.
            envcfg = [("menvcfg", menvcfg), ("senvcfg", senvcfg)]
            if not senvcfg:
                envcfg.reverse()
            block = [*satp_setup(xlen), *map_zicfiss_pages(xlen, user=False)]
            for csr, value in envcfg:
                block.extend(set_envcfg_sse(csr, value, test_data, mode="M"))
            save_x1, save_x5, save_lines = save_link_regs(test_data)
            block.extend(save_lines)

            for state, addr in (
                ("valid", ss_va + 0x800),
                ("unaligned", ss_va + 0x804),
                ("unmapped", va_unmapped(xlen)),
                ("mismatch", ss_va + 0x800),
            ):
                block.extend([f"LI(x{addr_reg}, {hex(addr)})", f"csrw ssp, x{addr_reg}"])
                if mode == "s":
                    block.append(GOTO_SMODE)
                for mnemonic, compressed, name in _MOP_FORMS:
                    reg = "x1" if "x1" in mnemonic else ("x5" if "x5" in mnemonic else None)
                    if reg:
                        block.append(f"LI({reg}, {'0xDEADBEEF' if state == 'mismatch' else '0'})")
                    form = f"ssrdp x{rd_reg}" if mnemonic == "ssrdp" else mnemonic
                    block.extend(
                        [
                            test_data.add_testcase(
                                f"{name}_{leg}_{state}_rv{xlen}", f"cp_ss_instr_inactive_{mode}", _CG
                            ),
                            *ss_insn(form, compressed=compressed),
                        ]
                    )
                    if mnemonic == "ssrdp":
                        block.append(write_sigupd(rd_reg, test_data))
                if mode == "s":
                    block.append(GOTO_MMODE)
                block.extend([f"csrr x{rd_reg}, ssp   # unchanged", write_sigupd(rd_reg, test_data)])

            block.extend(restore_link_regs(save_x1, save_x5))
            block.extend(["csrwi satp, 0", "sfence.vma"])
            test_data.int_regs.return_registers([addr_reg, rd_reg, save_x1, save_x5])
            return block

        lines.append(f"# --- {mode.upper()}-mode, menvcfg.SSE={menvcfg}, senvcfg.SSE={senvcfg} ---")
        lines.extend(both_xlens(build))
    return lines


# ---------------------------------------------------------------------------
# Top-level generator
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "ZicfissSm",
    required_extensions=["S", "U", "Zicfiss", "Zimop", "Zaamo", "Zcmop", "Zca", "Zicsr"],
    # M-mode control-plane suite: it boots to M-mode and drops to S-mode through T-SBI
    # for the legs that need a lower privilege level.
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zicfisssm(test_data: TestData) -> list[TestChunk]:
    """Generate the ZicfissSm test suite."""
    test_chunks: list[TestChunk] = []
    for section in (
        _generate_ssamoswap_mmode_fault,
        _generate_menvcfg_gating,
        _generate_envcfg_rdonly0,
        _generate_pmp_permissions,
        _generate_satp_bare,
        _generate_instr_inactive,
    ):
        tc = test_data.begin_test_chunk()
        tc.code.extend(page_table_data_section())
        tc.code.extend(section(test_data))
        test_chunks.append(test_data.end_test_chunk())

    return test_chunks
