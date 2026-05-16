##################################
# priv/extensions/UV.py
#
# UV user-mode vector privileged test generator.
# Vector CSR access from U-mode: read/write/walking-1s.
# SPDX-License-Identifier: Apache-2.0
##################################

"""UV privileged test generator: vector CSR access from U-mode."""

from testgen.asm.csr import csr_access_test, csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

_CG = "UV_cg"

_VS_MASK = 3 << 9


def _enable_vs_and_vector(temp_reg: int) -> list[str]:
    """In M-mode prelude: set mstatus.VS=Dirty and configure a legal vtype/vl."""
    return [
        f"LI(x{temp_reg}, {_VS_MASK})",
        f"CSRC(mstatus, x{temp_reg})  # clear VS",
        f"LI(x{temp_reg}, {3 << 9})",
        f"CSRS(mstatus, x{temp_reg})  # VS=Dirty",
        f"vsetivli x{temp_reg}, 1, e32, m1, tu, mu",
        "csrw vstart, x0",
    ]


# Vector CSRs accessible from U-mode
_VECTOR_CSRS_RW = ["vstart", "vxsat", "vxrm", "vcsr"]
_VECTOR_CSRS_RO = ["vl", "vtype", "vlenb"]
_VECTOR_CSRS = _VECTOR_CSRS_RW + _VECTOR_CSRS_RO


def _gen_uvcsr_access(test_data: TestData) -> list[str]:
    """cp_uvcsr_access: csrrc-all/csrrw-0/csrrw-1/csrrs-all/csrr against each vector CSR in U-mode."""
    coverpoint = "cp_uvcsr_access"
    lines = [
        comment_banner(
            coverpoint,
            "U-mode access patterns (csrrw all 0s/all 1s, csrrs all 1s, csrrc all 1s, csrr) for each vector CSR",
        ),
    ]
    for csr in _VECTOR_CSRS:
        lines.extend(csr_access_test(test_data, (csr, None), _CG, coverpoint))
    return lines


def _gen_uvcsrwalk(test_data: TestData) -> list[str]:
    """cp_uvcsrwalk: csrrs/csrrc with rs1 = walking-1s against each vector CSR in U-mode."""
    coverpoint = "cp_uvcsrwalk"
    lines = [
        comment_banner(
            coverpoint,
            "Walking-1s csrrs/csrrc into each vector CSR from U-mode",
        ),
    ]
    for csr in _VECTOR_CSRS:
        lines.extend(csr_walk_test(test_data, (csr, None), _CG, coverpoint))
    return lines


@add_priv_test_generator(
    "UV",
    required_extensions=["Sm", "U", "I", "M", "V", "Zicsr"],
    march_extensions=["I", "M", "V", "Zicsr"],
    extra_defines=[
        "#define RVTEST_VECTOR",
        "#define RVTEST_SEW 0",
        "#define VDSEW 0",
    ],
)
def make_uv(test_data: TestData) -> list[str]:
    """Generate UV tests (vector CSR access from U-mode)."""
    temp_reg = test_data.int_regs.get_register(exclude_regs=[0])

    lines: list[str] = []
    lines.extend(_enable_vs_and_vector(temp_reg))
    lines.append("RVTEST_GOTO_LOWER_MODE Umode  # run vector CSR tests in U-mode\n")
    lines.extend(_gen_uvcsr_access(test_data))
    lines.extend(_gen_uvcsrwalk(test_data))

    test_data.int_regs.return_registers([temp_reg])
    return lines
