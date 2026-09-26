##################################
# priv/extensions/sv/ExceptionsSvZaamoSm.py
#
# Virtual-memory AMO exception tests that need M-mode state.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate virtual-memory AMO exception tests that need M-mode state."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.ExceptionsSvCommon import make_exception_suite
from testgen.priv.extensions.sv.page_tables import SV32, SV39
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "ExceptionsSvZaamoSm",
    required_extensions=["Sm", "Sv32", "Zaamo"],
    march_extensions=["Zaamo"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_exceptions_svzaamosm32(test_data: TestData) -> list[TestChunk]:
    return make_exception_suite(test_data, SV32, suite="ExceptionsSvZaamoSm", operation="Zaamo", machine_state=True)


@add_priv_test_generator(
    "ExceptionsSvZaamoSm",
    required_extensions=["Sm", "Sv39", "Zaamo"],
    march_extensions=["Zaamo"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_exceptions_svzaamosm39(test_data: TestData) -> list[TestChunk]:
    return make_exception_suite(test_data, SV39, suite="ExceptionsSvZaamoSm", operation="Zaamo", machine_state=True)
