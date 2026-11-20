##################################
# priv/extensions/Ziccamoa.py
#
# Ziccamoa main-memory atomics test generator.
# David_Harris@hmc.edu 22 October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ziccamoa extension test generator.

Main memory regions with the coherence and cacheability PMAs must provide AMOArithmetic-level PMA support. The test
runs each AMOArithmetic-level AMO the DUT supports (the Zaamo word AMOs, the doubleword AMOs on RV64, and the Zabha
byte and halfword AMOs) once on scratch. Atomicity cannot be checked with a single hart.
"""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZiccamoCommon import AMO_ARITHMETIC, amo_tests
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator("Ziccamoa", required_extensions=["Ziccamoa", "Zaamo"], march_extensions=["Zaamo", "Zabha"])
def make_ziccamoa(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the Ziccamoa main-memory atomics extension."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(amo_tests(test_data, AMO_ARITHMETIC, "cp_ziccamoa", "Ziccamoa_cg"))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
