##################################
# ZicntrSm.py
#
# ZicntrSm privileged extension test generator: counter-enable behavior observed from M-mode.
# David_Harris@hmc.edu 22 August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicntrSm extension test generator: M-mode counter reads under walking mcounteren / scounteren."""

from __future__ import annotations

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_COUNTERS = ["cycle", "time", "instret"]


def _read_counter(read_reg: int, i: int) -> list[str]:
    """Read counter i (and its high half on RV32) in M-mode."""
    if i < 3:
        name = _COUNTERS[i]
        return [f"csrr x{read_reg}, {name}", "#if __riscv_xlen == 32", f"csrr x{read_reg}, {name}h", "#endif"]
    return [
        "#ifdef ZIHPM_SUPPORTED",
        f"csrr x{read_reg}, hpmcounter{i} # read from hpmcounter{i} in M-mode",
        "#if __riscv_xlen == 32",
        f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i}h in M-mode",
        "#endif",
        "#endif",
    ]


def _walk_counteren_m(
    test_data: TestData, csr: str, coverpoint: str, covergroup: str, *, mcounteren: str | None = None
) -> list[str]:
    """
    Walk a 1 and then a 0 through every bit of csr, reading every counter in M-mode after each write.

    M-mode reads are never gated by mcounteren/scounteren, so every read must succeed regardless of
    the walked value.
    """
    read_reg, ones_reg, walk_reg = test_data.int_regs.get_registers(3)
    lines = [f"LI(x{ones_reg}, -1)"]
    tag = f"mcounteren_{mcounteren}_" if mcounteren is not None else ""
    if mcounteren == "ones":
        lines.append(f"csrw mcounteren, x{ones_reg}  # enable all counters in M-mode")
    elif mcounteren == "zeros":
        lines.append("csrw mcounteren, zero  # disable all counters in M-mode")
    elif mcounteren is not None:
        raise ValueError(f"mcounteren must be 'ones', 'zeros', or None, not {mcounteren!r}")

    lines.append(f"LI(x{walk_reg}, 1)")
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"{tag}walking_1_{i}", coverpoint, covergroup),
                f"csrw {csr}, zero  # clear all bits",
                f"csrs {csr}, x{walk_reg}  # set current bit",
                *_read_counter(read_reg, i),
                f"slli x{walk_reg}, x{walk_reg}, 1",
            ]
        )
    # walking a single 0
    lines.append(f"LI(x{walk_reg}, 1)")
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"{tag}walking_0_{i}", coverpoint, covergroup),
                f"csrs {csr}, x{ones_reg}  # set all bits",
                f"csrc {csr}, x{walk_reg}  # clear current bit",
                *_read_counter(read_reg, i),
                f"slli x{walk_reg}, x{walk_reg}, 1",
            ]
        )
    test_data.int_regs.return_registers([read_reg, ones_reg, walk_reg])
    return lines


def _generate_mcounteren_access_m_tests(test_data: TestData) -> list[str]:
    """Generate mcounteren access M-mode tests (moved from ZicntrU)."""
    covergroup, coverpoint = "ZicntrSm_cg", "cp_mcounteren_access_m"
    return [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to mcounteren.  Read from corresponding counter and counterh in M-mode",
        ),
        "",
        *_walk_counteren_m(test_data, "mcounteren", coverpoint, covergroup),
    ]


def _generate_scounteren_access_m_tests(test_data: TestData) -> list[str]:
    """Generate scounteren access M-mode tests (moved from ZicntrS)."""
    covergroup, coverpoint = "ZicntrSm_cg", "cp_scounteren_access_m"
    return [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to scounteren with mcounteren = all 1s/all 0s.  Read from corresponding counter and counterh in M-mode",
        ),
        "",
        *_walk_counteren_m(test_data, "scounteren", coverpoint, covergroup, mcounteren="ones"),
        *_walk_counteren_m(test_data, "scounteren", coverpoint, covergroup, mcounteren="zeros"),
    ]


@add_priv_test_generator(
    "ZicntrSm",
    required_extensions=[
        "Sm",
        "U",
        "Zicntr",
    ],  # don't bother to generate if U is not supported, because it would be empty
    march_extensions=["Zicntr", "Zihpm"],
)
def make_zicntrsm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZicntrSm coverpoints: the M-mode halves of the Zicntr counter-enable tests."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.append("#ifdef U_SUPPORTED")
    tc.code.extend(_generate_mcounteren_access_m_tests(test_data))
    tc.code.append("#endif // U_SUPPORTED")
    tc.code.append("")
    tc.code.append("#ifdef S_SUPPORTED")
    tc.code.extend(_generate_scounteren_access_m_tests(test_data))
    tc.code.append("#endif // S_SUPPORTED")

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
