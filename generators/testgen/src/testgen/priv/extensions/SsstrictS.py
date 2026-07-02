##################################
# priv/extensions/SsstrictS.py
#
# Ssstrict supervisor-mode privileged test generator.
# Tests all CSR encodings and reserved instruction encodings from S-mode.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsstrictS — supervisor-mode strict/negative compliance tests.

The fast trap handler is NOT emitted here — generate/priv.py prepends it
to every split file so every generated .S file redirects mtvec immediately
after RVTEST_TRAP_PROLOG.

Structure
---------
1. CSR sweep from S-mode (only CSRs accessible from S/HS and below).
2. Illegal instruction and compressed encoding sweeps.
"""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SsstrictCommon import (
    H_CUSTOM_CSR_RANGES,
    M_PRIV_CSR_RANGES,
    S_CUSTOM_CSR_RANGES,
    USER_CUSTOM_CSR_RANGES,
    csr_range_set,
    generate_ssstrict_suite,
)
from testgen.priv.registry import add_priv_test_generator

# ── CSR skip set (S-mode) ─────────────────────────────────────────────────

_S_CSR_SKIP: frozenset[int] = frozenset(
    csr_range_set(*M_PRIV_CSR_RANGES, *S_CUSTOM_CSR_RANGES, *H_CUSTOM_CSR_RANGES, *USER_CUSTOM_CSR_RANGES)
    | {
        0x180,  # satp: TLB flush / address-translation mode change
        0x105,  # stvec: overwriting stvec breaks the delegated-trap handler
        0x140,  # sscratch: avoid corrupting framework save area
        0x5A8,  # scontext: Sail traps, Spike does not
    }
)


# ── Entry point ───────────────────────────────────────────────────────────


@add_priv_test_generator(
    "SsstrictS",
    required_extensions=["S", "Zicsr", "Ssstrict"],
    march_extensions=[
        "I",
        "V",  # V included: sets vl/vtype for vector loads and stores in the encoding sweep
        "Zicsr",
    ],
    extra_defines=["#define RVTEST_USE_FAST_TRAP_HANDLER", "#define RVTEST_TEMP_BOOT_TO_S"],
)
def make_ssstrictss(test_data: TestData) -> list[TestChunk]:
    """SsstrictS — supervisor-mode strict compliance tests."""
    return generate_ssstrict_suite(test_data, "SsstrictS", "S", _S_CSR_SKIP)
