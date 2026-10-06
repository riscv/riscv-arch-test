##################################
# priv/extensions/SscofpmfInhibit.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf xINH (mode inhibit) test-case generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sscofpmf mhpmevent xINH tests, called with priv_mode in {"Sm", "S", "U"}."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.extensions.SscofpmfCommon import (
    EVENT_VAL_HI,
    HIGHER_MODE_INHIBITS,
    HIGHER_MODE_INHIBITS_32,
    csr_access,
)

_INHIBIT_MODE_SUFFIX = {"Sm": "mmode", "S": "smode", "U": "umode"}


def generate_xinh_inhibits_tests(
    test_data: TestData, priv_mode: str, combos: range = range(32), toggles: bool = True
) -> list[str]:
    """xINH toggles (when ``toggles``) and the MINH/SINH/UINH/VSINH/VUINH combinations in ``combos``."""
    _INHIBIT_BIT_POS = {"Sm": 62, "S": 61, "U": 60}
    _INHIBIT_PREFIX = {"Sm": "m", "S": "s", "U": "u"}

    covergroup = "Sscofpmf_cg"
    inh_prefix = _INHIBIT_PREFIX[priv_mode]
    coverpoint = f"cp_{inh_prefix}inh_inhibits_{_INHIBIT_MODE_SUFFIX[priv_mode]}"
    inh_bit_pos = _INHIBIT_BIT_POS[priv_mode]
    inh_bit_pos_32 = inh_bit_pos - 32  # RV32 position within mhpmevent3h

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    higher_inhibits = HIGHER_MODE_INHIBITS[priv_mode]
    higher_inhibits_32 = HIGHER_MODE_INHIBITS_32[priv_mode]

    lines = [
        comment_banner(
            coverpoint,
            f"{inh_prefix.upper()}INH bit (mhpmevent[{inh_bit_pos}]) inhibits counting in {priv_mode}-mode.\n"
            "Counting stays inhibited in the modes above the one under test, so the counter\n"
            "only ever reflects the workload and never the T-SBI round trip that reaches the\n"
            "M-level counter CSRs.",
        ),
        "",
        csr_access("csrw mie, zero   # disable interrupts before toggle/sweep", priv_mode),
        "",
    ]
    indent = ""

    # --- individual 0/1 single-bit toggle ---
    for inh_val in [0, 1] if toggles else []:
        binname = f"{inh_prefix}inh_{inh_val}_{priv_mode.lower()}"
        lines.extend(
            [
                f"{indent}# Testcase: {inh_prefix}inh = {inh_val}",
                f"{indent}#if __riscv_xlen == 32",
                f"{indent}LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)",
                f"{indent}{csr_access(f'csrw RVMODEL_MHPMEVENT, x{r_val}', priv_mode)}",
                f"{indent}LI(x{r_val}, {EVENT_VAL_HI} | {hex(higher_inhibits_32 | (inh_val << inh_bit_pos_32))})",
                f"{indent}{csr_access(f'csrw CSR_MHPMEVENT3H, x{r_val}', priv_mode)}",
                f"{indent}#else",
                f"{indent}LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | {hex(higher_inhibits | (inh_val << inh_bit_pos))})",
                f"{indent}{csr_access(f'csrw RVMODEL_MHPMEVENT, x{r_val}', priv_mode)}",
                f"{indent}#endif",
                f"{indent}{csr_access('csrw RVMODEL_MHPMCOUNTER, zero', priv_mode)}",
                "",
                f"{indent}LA(x{r_temp}, scratch)",
                f"{indent}RVMODEL_MHPMEVENT_CODE(x{r_temp}, x{r_val})",
                "",
                f"{indent}{test_data.add_testcase(binname, coverpoint, covergroup)}",
                f"{indent}{csr_access(f'csrr x{r_temp}, RVMODEL_MHPMCOUNTER', priv_mode)}",
                # Normalize to nonzero/zero: counter must be nonzero iff xinh=0, regardless of
                # how many events a given model counted.
                f"{indent}snez x{r_temp}, x{r_temp}",
                f"{indent}{write_sigupd(r_temp, test_data)}",
                "",
            ]
        )

    lines.extend(
        [
            f"{indent}LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)",
            f"{indent}{csr_access(f'csrw RVMODEL_MHPMEVENT, x{r_val}', priv_mode)}",
            f"{indent}#if __riscv_xlen == 32",
            f"{indent}LI(x{r_val}, {EVENT_VAL_HI})",
            f"{indent}{csr_access(f'csrw CSR_MHPMEVENT3H, x{r_val}', priv_mode)}",
            f"{indent}#endif",
            "",
        ]
    )

    r_hval = test_data.int_regs.get_register(exclude_regs=[0, 31])

    def combo_counts() -> list[str]:
        """In M-mode, also run the workload so every combination checks that only MINH
        decides whether M-mode events count. Below M the counter is reached through a
        T-SBI round trip that the combinations with MINH=0 would count, so the S and U
        suites check counting only in the single-bit toggles above."""
        if priv_mode != "Sm":
            return []
        return [
            f"{indent}csrw RVMODEL_MHPMCOUNTER, zero",
            f"{indent}LA(x{r_temp}, scratch)",
            f"{indent}RVMODEL_MHPMEVENT_CODE(x{r_temp}, x{r_hval})",
            f"{indent}csrr x{r_temp}, RVMODEL_MHPMCOUNTER",
            f"{indent}snez x{r_temp}, x{r_temp}   # counted iff MINH = 0",
            f"{indent}{write_sigupd(r_temp, test_data)}",
        ]

    lines.append(f"{indent}#if __riscv_xlen == 32")
    for combo in combos:
        binname = f"xinh_combo_{combo:05b}_{priv_mode.lower()}_rv32"
        lines.extend(
            [
                # The low half keeps RVMODEL_MHPMEVENT_VAL from the write above the loop.
                f"{indent}LI(x{r_hval}, {EVENT_VAL_HI} | ({combo} << 26))",  # 58-32 = 26
                f"{indent}{csr_access(f'csrw CSR_MHPMEVENT3H, x{r_hval}', priv_mode)}",
                "",
                f"{indent}{test_data.add_testcase(binname, coverpoint, covergroup)}",
                f"{indent}{csr_access(f'csrr x{r_temp}, CSR_MHPMEVENT3H', priv_mode)}",
                # VSINH/VUINH are read-only zero without H, so check them only on an H hart.
                # (tests/env/riscv_arch_test.h currently undefines H_SUPPORTED everywhere.)
                "#ifndef H_SUPPORTED",
                f"{indent}LI(x{r_hval}, 0xF3FFFFFF)   # clear bits 27:26 (VSINH/VUINH)",
                f"{indent}and x{r_temp}, x{r_temp}, x{r_hval}",
                "#endif",
                f"{indent}{write_sigupd(r_temp, test_data)}",
                *combo_counts(),
                "",
            ]
        )
    lines.append(f"{indent}#else")
    for combo in combos:
        binname = f"xinh_combo_{combo:05b}_{priv_mode.lower()}_rv64"
        lines.extend(
            [
                f"{indent}LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | ({combo} << 58))",
                f"{indent}{csr_access(f'csrw RVMODEL_MHPMEVENT, x{r_val}', priv_mode)}",
                "",
                f"{indent}{test_data.add_testcase(binname, coverpoint, covergroup)}",
                f"{indent}{csr_access(f'csrr x{r_temp}, RVMODEL_MHPMEVENT', priv_mode)}",
                # VSINH/VUINH are read-only zero without H, so check them only on an H hart.
                "#ifndef H_SUPPORTED",
                f"{indent}LI(x{r_val}, 0xF3FFFFFFFFFFFFFF)   # clear bits 59:58 (VSINH/VUINH)",
                f"{indent}and x{r_temp}, x{r_temp}, x{r_val}",
                "#endif",
                f"{indent}{write_sigupd(r_temp, test_data)}",
                *combo_counts(),
                "",
            ]
        )
    lines.append(f"{indent}#endif")
    lines.extend(
        [
            f"{indent}{csr_access('csrw RVMODEL_MHPMEVENT, zero', priv_mode)}",
            f"{indent}#if __riscv_xlen == 32",
            f"{indent}{csr_access('csrw CSR_MHPMEVENT3H, zero', priv_mode)}",
            f"{indent}#endif",
            f"{indent}{csr_access('csrw RVMODEL_MHPMCOUNTER, zero', priv_mode)}",
            "",
        ]
    )
    test_data.int_regs.return_registers([r_hval])
    test_data.int_regs.return_registers([r_val, r_temp])
    return lines
