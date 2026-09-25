##################################
# priv/extensions/sv/ExceptionsSvZalrsc.py
#
# Virtual-memory LR/SC exception test generation.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate S-mode and U-mode virtual-memory LR/SC exception tests."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.ExceptionsSvCommon import make_exception_suite
from testgen.priv.extensions.sv.page_tables import SV32, SV39
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "ExceptionsSvZalrsc",
    required_extensions=["Sv32", "Zalrsc"],
    march_extensions=["Zalrsc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_exceptions_svzalrsc32(test_data: TestData) -> list[TestChunk]:
    return make_exception_suite(test_data, SV32, suite="ExceptionsSvZalrsc", operation="Zalrsc", machine_state=False)


@add_priv_test_generator(
    "ExceptionsSvZalrsc",
    required_extensions=["Sv39", "Zalrsc"],
    march_extensions=["Zalrsc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_exceptions_svzalrsc39(test_data: TestData) -> list[TestChunk]:
    return make_exception_suite(test_data, SV39, suite="ExceptionsSvZalrsc", operation="Zalrsc", machine_state=False)
