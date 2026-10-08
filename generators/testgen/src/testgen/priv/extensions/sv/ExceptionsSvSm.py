##################################
# priv/extensions/sv/ExceptionsSvSm.py
#
# Virtual-memory exception tests that need M-mode state.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate virtual-memory exception tests that need M-mode state."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.ExceptionsSvCommon import make_exception_suite
from testgen.priv.extensions.sv.page_tables import SV32, SV39
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "ExceptionsSvSm",
    required_extensions=["Sm", "Sv32"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_exceptions_svsm32(test_data: TestData) -> list[TestChunk]:
    return make_exception_suite(test_data, SV32, suite="ExceptionsSvSm", operation="rwx", machine_state=True)


@add_priv_test_generator(
    "ExceptionsSvSm",
    required_extensions=["Sm", "Sv39"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_exceptions_svsm39(test_data: TestData) -> list[TestChunk]:
    return make_exception_suite(test_data, SV39, suite="ExceptionsSvSm", operation="rwx", machine_state=True)
