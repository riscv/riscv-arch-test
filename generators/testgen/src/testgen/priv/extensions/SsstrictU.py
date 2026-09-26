##################################
# priv/extensions/SsstrictU.py
#
# Ssstrict user-mode privileged test generator.
# Tests all CSR encodings and reserved instruction encodings from U-mode.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsstrictU — user-mode strict/negative compliance tests."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SsstrictCommon import (
    USER_CUSTOM_CSR_RANGES,
    csr_range_set,
    generate_ssstrict_suite,
)
from testgen.priv.registry import add_priv_test_generator

# ── CSR skip set (U-mode) ─────────────────────────────────────────────────

# Sweep only user-level CSRs (bits[9:8]=00) from U-mode, so skip everything
# else. S/H/M CSRs are higher privilege and always raise illegal-instruction
# from U-mode — that is an architecturally known fact, so testing them here
# adds no value.  Custom and reserved ranges are skipped (undefined behaviour).

_U_CSR_SKIP: frozenset[int] = frozenset(
    a
    for a in range(4096)
    if ((a >> 8) & 3) != 0  # non-user-level (bits[9:8]!=00)
) | csr_range_set(*USER_CUSTOM_CSR_RANGES)


# ── Entry point ───────────────────────────────────────────────────────────


@add_priv_test_generator(
    "SsstrictU",
    required_extensions=["U", "Ssstrict"],
    march_extensions=[
        "I",
        "V",
    ],
    extra_defines=["#define RVTEST_USE_FAST_TRAP_HANDLER"],
)
def make_ssstrictu(test_data: TestData) -> list[TestChunk]:
    """SsstrictU — user-mode strict compliance tests."""
    return generate_ssstrict_suite(test_data, "SsstrictU", "U", _U_CSR_SKIP)
