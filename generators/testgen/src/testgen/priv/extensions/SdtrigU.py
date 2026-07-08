##################################
# SdtrigU.py
#
# Sdtrig U-mode test generator.
# pclark@hmc.edu Jul 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SdtrigCommon import generate_sdtrig_suite
from testgen.priv.registry import add_priv_test_generator

MODE = "U"


@add_priv_test_generator(
    "SdtrigU",
    required_extensions=["U", "Sdtrig"],
    march_extensions=["I", "Zicsr"],
    extra_defines=["#define SKIP_MEPC"],  # hangs otherwise
)
def make_sdtrigu(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the SdtrigU debug-trigger testsuite."""
    return generate_sdtrig_suite(test_data, "U")
