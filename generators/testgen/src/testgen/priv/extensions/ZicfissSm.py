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

None of these testcases place a shadow stack on an SS page, so this suite is
independent of the sail-riscv SS-page limitation that blocks ZicfissU/ZicfissS.
"""

from __future__ import annotations

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfissCommon import (
    GOTO_MMODE,
    GOTO_SMODE,
    SSE_BIT,
    both_xlens,
    identity_map_only,
    satp_setup,
    set_envcfg_sse,
    ss_insn,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "ZicfissSm_cg"


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
                lines.extend(set_envcfg_sse("menvcfg", sse, test_data))
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
        lines.extend(set_envcfg_sse("menvcfg", sse, test_data))
        # M-mode: ssp is reachable regardless of menvcfg.SSE (the rule is scoped to
        # "privilege mode less than M"), so this leg is the positive control.
        lines.extend(
            [
                test_data.add_testcase(f"ssp_read_mmode_sse{sse}", coverpoint, _CG),
                f"csrr x{rd_reg}, ssp",
                f"LI(x{val_reg}, 0x1000)",
                test_data.add_testcase(f"ssp_write_mmode_sse{sse}", coverpoint, _CG),
                f"csrrw x{rd_reg}, ssp, x{val_reg}",
            ]
        )
        # S-mode: illegal-instruction when menvcfg.SSE=0, allowed when 1.
        lines.extend(
            [
                GOTO_SMODE,
                test_data.add_testcase(f"ssp_read_smode_sse{sse}", coverpoint, _CG),
                f"csrr x{rd_reg}, ssp",
                f"LI(x{val_reg}, 0x2000)",
                test_data.add_testcase(f"ssp_write_smode_sse{sse}", coverpoint, _CG),
                f"csrrs x{rd_reg}, ssp, x{val_reg}",
                GOTO_MMODE,
            ]
        )

    test_data.int_regs.return_registers([rd_reg, val_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_envcfg_sse_rdonly0_senvcfg
# ---------------------------------------------------------------------------


def _generate_envcfg_rdonly0(test_data: TestData) -> list[str]:
    """With menvcfg.SSE=0, senvcfg.SSE is read-only zero regardless of what is written."""
    coverpoint = "cp_envcfg_sse_rdonly0_senvcfg"
    rd_reg, val_reg = test_data.int_regs.get_registers(2)
    lines: list[str] = [
        comment_banner(coverpoint, "menvcfg.SSE=0 forces senvcfg.SSE read-only zero"),
    ]

    for menvcfg_sse in (0, 1):
        lines.extend(set_envcfg_sse("menvcfg", menvcfg_sse, test_data))
        for written in (0, 1):
            tag = f"men{menvcfg_sse}_wrote{written}"
            # csrrw writes the whole register; csrrs sets just the SSE bit.
            lines.extend(
                [
                    f"LI(x{val_reg}, {hex(written << SSE_BIT)})",
                    test_data.add_testcase(f"senvcfg_sse_csrrw_{tag}", coverpoint, _CG),
                    f"csrrw x{rd_reg}, senvcfg, x{val_reg}",
                    f"csrr x{rd_reg}, senvcfg   # SSE must read 0 when menvcfg.SSE=0",
                    write_sigupd(rd_reg, test_data),
                ]
            )
            if written:
                lines.extend(
                    [
                        f"LI(x{val_reg}, {hex(1 << SSE_BIT)})",
                        test_data.add_testcase(f"senvcfg_sse_csrrs_{tag}", coverpoint, _CG),
                        f"csrrs x{rd_reg}, senvcfg, x{val_reg}",
                        f"csrr x{rd_reg}, senvcfg",
                        write_sigupd(rd_reg, test_data),
                    ]
                )

    test_data.int_regs.return_registers([rd_reg, val_reg])
    return lines


# ---------------------------------------------------------------------------
# Top-level generator
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "ZicfissSm",
    required_extensions=["S", "U", "Zicfiss", "Zimop", "Zaamo", "Zicsr"],
)
def make_zicfisssm(test_data: TestData) -> list[TestChunk]:
    """Generate the ZicfissSm test suite."""
    test_chunks: list[TestChunk] = []
    for section in (_generate_ssamoswap_mmode_fault, _generate_menvcfg_gating, _generate_envcfg_rdonly0):
        tc = test_data.begin_test_chunk()
        tc.code.extend(section(test_data))
        test_chunks.append(test_data.end_test_chunk())
    return test_chunks
