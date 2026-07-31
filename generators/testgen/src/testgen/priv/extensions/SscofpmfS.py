##################################
# priv/extensions/SscofpmfSm.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf M-mode test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SscofpmfCommon import generate_sscofpmf_suite
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "SscofpmfSm",
    required_extensions=["Sm", "Sscofpmf"],
    march_extensions=[],
    extra_defines=[],
)
def make_sscofpmfsm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the SscofpmfSm performance-counter-overflow testsuite."""
    return generate_sscofpmf_suite(test_data, "Sm")
