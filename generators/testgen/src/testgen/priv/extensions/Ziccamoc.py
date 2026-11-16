##################################
# priv/extensions/Ziccamoc.py
#
# Ziccamoc main-memory compare-and-swap test generator.
# David_Harris@hmc.edu 22 October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ziccamoc extension test generator.

Main memory regions with the coherence and cacheability PMAs must provide AMOCASQ-level PMA support, which includes
every AMOArithmetic-level AMO and amocas.w, amocas.d and amocas.q. The test runs each of these the DUT supports (with
the Zabha byte and halfword forms, and amocas.q only on RV64) once on scratch. Atomicity cannot be checked with a
single hart.
"""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZiccamoCommon import AMO_ARITHMETIC, AMO_CAS, amo_tests
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "Ziccamoc", required_extensions=["Ziccamoc", "Zacas"], march_extensions=["Zaamo", "Zabha", "Zacas"]
)
def make_ziccamoc(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the Ziccamoc main-memory compare-and-swap extension."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(amo_tests(test_data, [*AMO_ARITHMETIC, *AMO_CAS], "cp_ziccamoc", "Ziccamoc_cg"))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
