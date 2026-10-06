##################################
# priv/extensions/SscofpmfSuite.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Assembles the Sscofpmf tests shared by the Sm, S and U suites.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Assembly of the Sscofpmf tests shared by SscofpmfSm, SscofpmfS and SscofpmfU."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SscofpmfCommon import MACRO_CHECKS
from testgen.priv.extensions.SscofpmfInhibit import generate_xinh_inhibits_tests
from testgen.priv.extensions.SscofpmfOverflow import (
    generate_lcofip_hw_only_tests,
    generate_of_set_on_overflow_tests,
    generate_overflow_hw_only_tests,
)
from testgen.priv.extensions.SscofpmfScountovf import (
    MCOUNTEREN_OF_PATTERNS,
    SHADOW_PATTERNS,
    boot_of_state,
    generate_scountovf_mcounteren_tests,
    generate_scountovf_shadow_tests,
    generate_sscofpmf_access_tests,
    unknown_of_state,
)


def generate_sscofpmf_suite(test_data: TestData, mode: str) -> list[TestChunk]:
    """Assemble the shared Sscofpmf tests for ``mode`` ("Sm"/"S"/"U").

    Sm accesses the CSRs directly, so its tests stay together. Below M every access to an
    M-level CSR is a T-SBI call, so the S and U tests are split into small named test files."""
    test_chunks: list[TestChunk] = []

    if mode == "Sm":
        of_state = unknown_of_state()
        tc = test_data.begin_test_chunk()
        tc.code.extend(MACRO_CHECKS)  # this chunk may land in its own file
        tc.code.extend(generate_xinh_inhibits_tests(test_data, mode))
        tc.code.extend(generate_of_set_on_overflow_tests(test_data, mode))
        tc.code.extend(generate_overflow_hw_only_tests(test_data, mode))
        tc.code.extend(generate_lcofip_hw_only_tests(test_data, mode))
        tc.code.extend(generate_scountovf_mcounteren_tests(test_data, mode, of_state, list(MCOUNTEREN_OF_PATTERNS)))
        tc.code.extend(generate_sscofpmf_access_tests(test_data, mode))
        for patterns in SHADOW_PATTERNS.values():
            tc.code.extend(generate_scountovf_shadow_tests(test_data, mode, of_state, patterns))
        test_chunks.append(test_data.end_test_chunk())
        return test_chunks

    # xINH toggles and inhibit combinations 00000-01111
    tc = test_data.begin_test_chunk(split_name="inhibit_lo")
    tc.code.extend(MACRO_CHECKS)
    tc.code.extend(generate_xinh_inhibits_tests(test_data, mode, combos=range(16)))
    test_chunks.append(test_data.end_test_chunk())

    # inhibit combinations 10000-11111
    tc = test_data.begin_test_chunk(split_name="inhibit_hi")
    tc.code.extend(MACRO_CHECKS)
    tc.code.extend(generate_xinh_inhibits_tests(test_data, mode, combos=range(16, 32), toggles=False))
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.begin_test_chunk(split_name="overflow")
    tc.code.extend(MACRO_CHECKS)
    tc.code.extend(generate_of_set_on_overflow_tests(test_data, mode))
    tc.code.extend(generate_overflow_hw_only_tests(test_data, mode))
    tc.code.extend(generate_lcofip_hw_only_tests(test_data, mode))
    test_chunks.append(test_data.end_test_chunk())

    if mode == "U":  # scountovf is not accessible from U, so the scountovf tests are S-only
        return test_chunks

    # One file per OF pattern. Each starts from boot, where every OF bit is 0.
    for of_name in MCOUNTEREN_OF_PATTERNS:
        tc = test_data.begin_test_chunk(split_name=f"mcounteren_{of_name}")
        tc.code.extend(MACRO_CHECKS)
        tc.code.extend(generate_scountovf_mcounteren_tests(test_data, mode, boot_of_state(), [of_name]))
        test_chunks.append(test_data.end_test_chunk())

    tc = test_data.begin_test_chunk(split_name="access")
    tc.code.extend(MACRO_CHECKS)
    tc.code.extend(generate_sscofpmf_access_tests(test_data, mode))
    test_chunks.append(test_data.end_test_chunk())

    for split_name, patterns in SHADOW_PATTERNS.items():
        tc = test_data.begin_test_chunk(split_name=split_name)
        tc.code.extend(MACRO_CHECKS)
        tc.code.extend(generate_scountovf_shadow_tests(test_data, mode, boot_of_state(), patterns))
        test_chunks.append(test_data.end_test_chunk())
    return test_chunks
