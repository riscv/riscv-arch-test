##################################
# SdtrigS.py
#
# Sdtrig S-mode test generator.
# pclark@hmc.edu Jul 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SdtrigCommon import UDB_DEFINES, generate_sdtrig_suite
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "SdtrigS",
    required_extensions=["S", "Sdtrig"],
    march_extensions=[],
    extra_defines=[*UDB_DEFINES, "#define BOOT_TO_SMODE"],
)
def make_sdtrigs(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the SdtrigS debug-trigger testsuite."""
    return generate_sdtrig_suite(test_data, "S")
