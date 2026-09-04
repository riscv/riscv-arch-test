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
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "UV_uvcsr_cg"

# Vector CSRs accessible from U-mode
_VECTOR_CSRS_RW = ["vstart", "vxsat", "vxrm", "vcsr"]
_VECTOR_CSRS_RO = ["vl", "vtype", "vlenb"]
_VECTOR_CSRS = _VECTOR_CSRS_RW + _VECTOR_CSRS_RO


def _gen_uvcsr_access(test_data: TestData, temp_reg: int, test_chunks: list[TestChunk]) -> None:
    """cp_uvcsr_access: csrrc-all/csrrw-0/csrrw-1/csrrs-all/csrr against each vector CSR in U-mode."""
    coverpoint = "cp_uvcsr_access"
    for idx, csr in enumerate(_VECTOR_CSRS):
        tc = test_data.new_test_chunk(test_chunks, "uvcsr")
        if idx == 0:
            tc.section_header = comment_banner(
                coverpoint,
                "U-mode access patterns (csrrw all 0s/all 1s, csrrs all 1s, csrrc all 1s, csrr) for each vector CSR",
            )
        tc.code.extend(csr_access_test(test_data, (csr, None), _CG, coverpoint))


def _gen_uvcsrwalk(test_data: TestData, temp_reg: int, test_chunks: list[TestChunk]) -> None:
    """cp_uvcsrwalk: csrrs/csrrc with rs1 = walking-1s against each vector CSR in U-mode."""
    coverpoint = "cp_uvcsrwalk"
    for idx, csr in enumerate(_VECTOR_CSRS):
        split = f"uvcsrwalk_{csr}" if csr in _VECTOR_CSRS_RO else "uvcsrwalk"
        tc = test_data.new_test_chunk(test_chunks, split)
        if idx == 0:
            tc.section_header = comment_banner(
                coverpoint,
                "Walking-1s csrrs/csrrc into each vector CSR from U-mode",
            )
        tc.code.extend(csr_walk_test(test_data, (csr, None), _CG, coverpoint))


@add_priv_test_generator(
    "UV",
    required_extensions=["Sm", "U", "M", "V", "Zicsr"],
    march_extensions=["M", "V"],
    extra_defines=[
        "#define RVTEST_VECTOR",
        "#define RVTEST_SEW 0",
        "#define VDSEW 0",
    ],
    testcases_per_file=512,
)
def make_uv(test_data: TestData) -> list[TestChunk]:
    """Generate UV tests (vector CSR access from U-mode)."""
    test_chunks: list[TestChunk] = []
    test_data.begin_test_chunk("uvcsr")
    temp_reg = test_data.int_regs.get_register()

    _gen_uvcsr_access(test_data, temp_reg, test_chunks)
    _gen_uvcsrwalk(test_data, temp_reg, test_chunks)

    test_data.int_regs.return_registers([temp_reg])
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
