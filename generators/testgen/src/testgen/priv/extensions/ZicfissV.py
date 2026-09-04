##################################
# priv/extensions/ZicfissV.py
#
# Zicfiss (shadow stack) vector-access test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicfissV test generator.

Vector accesses to a shadow stack page. Split from ZicfissU because it needs V in the
march string and vector state configured before any access.

Boots to U-mode and uses the same T-SBI M-mode excursion as ZicfissU to set up
translation; see ``ZicfissU._umode_prologue`` for why that excursion stays.
"""

from __future__ import annotations

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfissCommon import (
    GOTO_SMODE,
    GOTO_UMODE,
    both_xlens,
    code_end_page_align,
    guard_ss_page,
    map_zicfiss_pages,
    priv_csr,
    satp_on_from_umode,
    set_envcfg_sse,
    set_sum,
    teardown_vm,
    va_for,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "ZicfissV_cg"


def _umode_prologue(test_data: TestData, xlen: int) -> list[str]:
    """S-mode setup then down to U-mode; see ZicfissU._umode_prologue for the rationale."""
    return [
        GOTO_SMODE,
        *map_zicfiss_pages(xlen),
        *set_sum(),
        *set_envcfg_sse("menvcfg", 1, test_data, mode="S"),
        *set_envcfg_sse("senvcfg", 1, test_data, mode="S"),
        GOTO_UMODE,
        *satp_on_from_umode(xlen),
    ]


def _generate_vector_load(test_data: TestData) -> list[str]:
    """Vector loads only read, so a shadow stack page is readable by them."""
    coverpoint = "cp_ss_vector_load"

    def build(xlen: int) -> list[str]:
        ss_va, _, _ = va_for(xlen)
        addr_reg, tmp_reg, mask_reg = test_data.int_regs.get_registers(3)
        lines = _umode_prologue(test_data, xlen)
        for mxr in (0, 1):
            lines.extend(
                [
                    f"LI(x{mask_reg}, {hex(1 << 19)})   # sstatus.MXR",
                    priv_csr(f"{'csrs' if mxr else 'csrc'} sstatus, x{mask_reg}", "U"),
                ]
            )
            for sew, mnemonic in ((8, "vle8.v"), (16, "vle16.v"), (32, "vle32.v")):
                lines.extend(
                    [
                        f"LI(x{addr_reg}, {hex(ss_va + 0x800)})",
                        f"vsetvli x{tmp_reg}, x0, e{sew}, m1, tu, mu",
                        test_data.add_testcase(
                            f"{mnemonic.replace('.', '_')}_ss_page_mxr{mxr}_rv{xlen}", coverpoint, _CG
                        ),
                        f"{mnemonic} v1, (x{addr_reg})",
                        write_sigupd(tmp_reg, test_data),
                    ]
                )
        lines.extend(teardown_vm("U"))
        test_data.int_regs.return_registers([addr_reg, tmp_reg, mask_reg])
        return lines

    return [comment_banner(coverpoint, "Vector loads from a shadow stack page"), *both_xlens(build)]


def _generate_vector_store(test_data: TestData) -> list[str]:
    """Vector stores are not permitted to write a shadow stack page."""
    coverpoint = "cp_ss_vector_store"

    def build(xlen: int) -> list[str]:
        ss_va, _, _ = va_for(xlen)
        addr_reg, tmp_reg = test_data.int_regs.get_registers(2)
        lines = _umode_prologue(test_data, xlen)
        for sew, mnemonic in ((8, "vse8.v"), (16, "vse16.v"), (32, "vse32.v")):
            lines.extend(
                [
                    f"LI(x{addr_reg}, {hex(ss_va + 0x800)})",
                    f"vsetvli x{tmp_reg}, x0, e{sew}, m1, tu, mu",
                    test_data.add_testcase(f"{mnemonic.replace('.', '_')}_ss_page_rv{xlen}", coverpoint, _CG),
                    f"{mnemonic} v1, (x{addr_reg})",
                ]
            )
        lines.extend(teardown_vm("U"))
        test_data.int_regs.return_registers([addr_reg, tmp_reg])
        return lines

    return [comment_banner(coverpoint, "Vector stores to a shadow stack page"), *both_xlens(build)]


def _generate_vector_scattered(test_data: TestData) -> list[str]:
    """Strided and indexed accesses, including ones that begin on the adjacent page."""

    def build(xlen: int) -> list[str]:
        ss_va, rw_va, _ = va_for(xlen)
        addr_reg, stride_reg, tmp_reg = test_data.int_regs.get_registers(3)
        lines = _umode_prologue(test_data, xlen)

        # rs1 on the SS page, and on the adjacent RW page running back into it.
        for origin, base in (("on_ss", ss_va + 0x800), ("adjacent", rw_va - 0x40)):
            for sew, mnemonic, cp in (
                (8, "vlse8.v", "cp_ss_vector_strided"),
                (32, "vlse32.v", "cp_ss_vector_strided"),
            ):
                lines.extend(
                    [
                        f"LI(x{addr_reg}, {hex(base)})",
                        f"LI(x{stride_reg}, 8)",
                        f"vsetvli x{tmp_reg}, x0, e{sew}, m1, tu, mu",
                        test_data.add_testcase(f"{mnemonic.replace('.', '_')}_{origin}_rv{xlen}", cp, _CG),
                        f"{mnemonic} v1, (x{addr_reg}), x{stride_reg}",
                    ]
                )
            for mnemonic, cp in (("vluxei8.v", "cp_ss_vector_indexed"), ("vsuxei8.v", "cp_ss_vector_indexed")):
                lines.extend(
                    [
                        f"LI(x{addr_reg}, {hex(base)})",
                        f"vsetvli x{tmp_reg}, x0, e8, m1, tu, mu",
                        test_data.add_testcase(f"{mnemonic.replace('.', '_')}_{origin}_rv{xlen}", cp, _CG),
                        f"{mnemonic} v1, (x{addr_reg}), v2",
                    ]
                )

        lines.extend(teardown_vm("U"))
        test_data.int_regs.return_registers([addr_reg, stride_reg, tmp_reg])
        return lines

    return [
        comment_banner("cp_ss_vector_strided/indexed", "Strided and indexed vector accesses to a shadow stack page"),
        *both_xlens(build),
    ]


@add_priv_test_generator(
    "ZicfissV",
    required_extensions=["S", "U", "V", "Zicfiss", "Zimop", "Zaamo", "Zcmop", "Zca", "Zicsr"],
    march_extensions=["V", "Zicfiss", "Zimop", "Zaamo", "Zcmop", "Zca"],
    extra_defines=[
        "#define RVTEST_VECTOR",
        "#define RVTEST_SEW 0",
        "#define VDSEW 0",
    ],
)
def make_zicfissv(test_data: TestData) -> list[TestChunk]:
    """Generate the ZicfissV test suite."""
    test_chunks: list[TestChunk] = []
    for section in (_generate_vector_load, _generate_vector_store, _generate_vector_scattered):
        tc = test_data.begin_test_chunk()
        tc.code.extend(guard_ss_page(section(test_data), reason="the vector access targets the shadow stack page"))
        tc.code.extend(code_end_page_align())
        test_chunks.append(test_data.end_test_chunk())

    return test_chunks
