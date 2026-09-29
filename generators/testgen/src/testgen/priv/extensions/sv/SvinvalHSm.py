##################################
# priv/extensions/sv/SvinvalHSm.py
#
# SvinvalHSm suite: Svinval instructions in M-mode, and in every mode with mstatus.TVM = 1.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svinval tests in M-mode with mstatus.TVM and hstatus.VTVM clear and set, and in HS, VS,
U and VU modes with TVM = 1.

The suite boots to M-mode and delegates nothing, so the M-mode handler takes every trap.
"""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.sv.SvinvalH import svinval_h_tests
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "SvinvalHSm",
    required_extensions=["Sm", "H", "Svinval"],
    extra_defines=["#define BOOT_TO_MMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_svinvalhsm(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("Svinval_mstatus_tvm")
    chunk.code.extend(svinval_h_tests(test_data, "M", (0, 1)))
    chunk.trap_sigupd_count = trap_sigupd_count(29)  # TVM = 1: 4 in HS, 5 in VS, 10 in VU, 10 in U
    return [test_data.end_test_chunk()]
