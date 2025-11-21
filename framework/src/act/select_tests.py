##################################
# select_tests.py
#
# jcarlin@hmc.edu 6 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Select tests to run based on UDB config and test list
##################################

from typing import Any

from act.parse_test_constraints import TestMetadata


def check_test_params(test_params: dict[str, Any], config_params: dict[str, Any]) -> bool:
    """Check if all parameters in test_params match those in config_params."""
    for param, value in test_params.items():
        if param not in config_params or config_params[param] != value:
            return False
    return True


def select_tests(
    test_dict: dict[str, TestMetadata], implemented_extensions: set[str], config_params: dict[str, Any]
) -> dict[str, TestMetadata]:
    """Select tests that match the UDB configuration."""
    selected_tests: dict[str, TestMetadata] = {}
    for test_name, test_metadata in test_dict.items():
        # Check if all required extensions are implemented
        required_exts = set(test_metadata.implemented_extensions)
        if required_exts.issubset(implemented_extensions):
            # Check if all parameters match
            test_params = test_metadata.params
            if check_test_params(test_params, config_params):
                selected_tests[test_name] = test_metadata
    return selected_tests


def get_common_tests(test_dict: dict[str, TestMetadata], xlen: int) -> dict[str, TestMetadata]:
    "Get tests that do not depend on configuration and match the given XLEN."
    common_tests: dict[str, TestMetadata] = {}
    for test_name, test_metadata in test_dict.items():
        if not test_metadata.config_dependent and test_metadata.mxlen == xlen:
            common_tests[test_name] = test_metadata
    return common_tests
