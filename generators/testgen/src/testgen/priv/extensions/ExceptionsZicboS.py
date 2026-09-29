##################################
# ExceptionsZicboS.py
#
# ExceptionsZicboS privileged extension test generator.
# ellyu@g.hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicbo extension exception test generator."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ExceptionsZicboCommon import emit_suite
from testgen.priv.registry import add_priv_test_generator

_CG = "ExceptionsZicboS_cg"
_MODES = ["S", "U"]  # supervisor, then user


@add_priv_test_generator(
    "ExceptionsZicboS",
    required_extensions=["S", ["Zicbom", "Zicboz", "Zicbop"]],
    march_extensions=["Zicbom", "Zicboz", "Zicbop"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_exceptionszicbos(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ExceptionsZicboS coverpoints."""
    test_chunks: list[TestChunk] = []
    for mode in _MODES:
        test_chunks.extend(emit_suite(test_data, _CG, mode, cross_senvcfg=True, mode_entry=True))
    return test_chunks
