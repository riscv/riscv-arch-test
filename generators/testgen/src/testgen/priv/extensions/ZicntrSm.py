##################################
# ZicntrSm.py
#
# ZicntrSm privileged extension test generator: counter-enable behavior observed from M-mode.
# David_Harris@hmc.edu 22 August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicntrSm extension test generator: M-mode counter reads under walking mcounteren / scounteren."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicntrCommon import counteren_walk_tests
from testgen.priv.registry import add_priv_test_generator

covergroup = "ZicntrSm_cg"


@add_priv_test_generator(
    "ZicntrSm",
    required_extensions=[
        "Sm",
        "U",
        "Zicntr",
    ],  # don't bother to generate if U is not supported, because it would be empty
    march_extensions=["Zicntr", "Zihpm"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zicntrsm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZicntrSm coverpoints: the M-mode halves of the Zicntr counter-enable tests."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(
        counteren_walk_tests(
            test_data,
            covergroup,
            "cp_mcounteren_access_m",
            "Write walking 1s and 0s to mcounteren.  Read from corresponding counter and counterh in M-mode",
            csrs=["mcounteren"],
            mode="M",
        )
    )
    tc.code.append("#ifdef S_SUPPORTED")
    for setting in ("ones", "zeros"):
        tc.code.extend(
            counteren_walk_tests(
                test_data,
                covergroup,
                "cp_scounteren_access_m",
                f"Write walking 1s and 0s to scounteren with mcounteren = all {setting}.  Read from corresponding counter and counterh in M-mode",
                csrs=["scounteren"],
                mode="M",
                mcounteren=setting,
                tag=f"mcounteren_{setting}_",
            )
        )
    tc.code.append("#endif // S_SUPPORTED")

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
