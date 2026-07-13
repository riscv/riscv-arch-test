##################################
# priv/extensions/SsstrictSm.py
#
# Ssstrict machine-mode privileged test generator.
# Tests all CSR encodings and reserved instruction encodings from M-mode.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsstrictSm — machine-mode strict/negative compliance tests.

The fast trap handler is NOT emitted here — generate/priv.py prepends it
to every split file so every generated .S file redirects mtvec immediately
after RVTEST_TRAP_PROLOG.
"""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SsstrictCommon import (
    H_CUSTOM_CSR_RANGES,
    M_CUSTOM_CSR_RANGES,
    S_CUSTOM_CSR_RANGES,
    USER_CUSTOM_CSR_RANGES,
    csr_range_set,
    generate_ssstrict_suite,
)
from testgen.priv.registry import add_priv_test_generator

# ── CSR skip set ──────────────────────────────────────────────────────────

_M_CSR_SKIP: frozenset[int] = frozenset(
    csr_range_set(
        range(0x3A0, 0x3F0),  # PMP regs
        range(0x7A0, 0x7B0),  # debug trigger regs
        range(0xFC0, 0x1000),  # M-mode read-only
        *M_CUSTOM_CSR_RANGES,
        *S_CUSTOM_CSR_RANGES,
        *H_CUSTOM_CSR_RANGES,
        *USER_CUSTOM_CSR_RANGES,
    )
    | {
        0x340,  # mscratch: corrupts trap stack
        0x305,  # mtvec: corrupts trap stack
        0x747,  # mseccfg: confuses M-mode
        0x5A8,  # scontext ignore, sail does not support it but other sims do
    }
)


# ── Entry point ────────────────────────────────────────────────────────────


@add_priv_test_generator(
    "SsstrictSm",
    required_extensions=["Sm", "Zicsr", "Ssstrict"],
    march_extensions=[
        "I",
        "V",
        "Zicsr",
    ],
    extra_defines=["#define RVTEST_USE_FAST_TRAP_HANDLER"],
)
def make_ssstrictsm(test_data: TestData) -> list[TestChunk]:
    """SsstrictSm — machine-mode strict compliance tests."""
    return generate_ssstrict_suite(test_data, "SsstrictSm", "M", _M_CSR_SKIP)
