##################################
# priv/extensions/pmp/PMPS.py
#
# PMPS: PMP enforcement of supervisor-mode accesses.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPS suite: PMP configured in M mode, then checked from S mode."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.pmp._lower_mode import S_MODE, make_lower_mode_amode, make_lower_mode_base
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "PMPS",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["S", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmps_base(test_data: TestData) -> list[TestChunk]:
    return make_lower_mode_base(test_data, S_MODE)


@add_priv_test_generator(
    "PMPS",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["S", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NA4_SUPPORTED: true"],
)
def make_pmps_na4(test_data: TestData) -> list[TestChunk]:
    return make_lower_mode_amode(test_data, S_MODE, "na4")


@add_priv_test_generator(
    "PMPS",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["S", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
)
def make_pmps_napot(test_data: TestData) -> list[TestChunk]:
    return make_lower_mode_amode(test_data, S_MODE, "napot")


@add_priv_test_generator(
    "PMPS",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["S", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
)
def make_pmps_tor(test_data: TestData) -> list[TestChunk]:
    return make_lower_mode_amode(test_data, S_MODE, "tor")
