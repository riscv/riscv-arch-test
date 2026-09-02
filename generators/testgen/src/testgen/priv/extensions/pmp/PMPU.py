##################################
# priv/extensions/pmp/PMPU.py
#
# PMPU: PMP enforcement of user-mode accesses.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPU suite: PMP configured in M mode, then checked from U mode."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.pmp._lower_mode import U_MODE, make_lower_mode_amode, make_lower_mode_base
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "PMPU",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["U", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpu_base(test_data: TestData) -> list[TestChunk]:
    return make_lower_mode_base(test_data, U_MODE)


@add_priv_test_generator(
    "PMPU",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["U", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NA4_SUPPORTED: true"],
)
def make_pmpu_na4(test_data: TestData) -> list[TestChunk]:
    return make_lower_mode_amode(test_data, U_MODE, "na4")


@add_priv_test_generator(
    "PMPU",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["U", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
)
def make_pmpu_napot(test_data: TestData) -> list[TestChunk]:
    return make_lower_mode_amode(test_data, U_MODE, "napot")


@add_priv_test_generator(
    "PMPU",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["U", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
)
def make_pmpu_tor(test_data: TestData) -> list[TestChunk]:
    return make_lower_mode_amode(test_data, U_MODE, "tor")
