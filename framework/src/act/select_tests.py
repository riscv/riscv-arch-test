##################################
# select_tests.py
#
# jcarlin@hmc.edu 6 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Select tests to run based on UDB config and test list
##################################

import re

from act.parse_test_constraints import TestMetadata

PRIV_EXTENSIONS = {"Sm", "S", "U"}

# Type alias
ConfigParamValue = int | bool | str | list[int | str | bool]

# Parameter constraint comparison operators
_COMPARISON_RE = re.compile(r"^(>=|<=|!=|==|>|<)\s*(0[xX][0-9a-fA-F]+|\d+)$")


def _compare_param(test_value: object, config_value: object) -> bool:
    """Compare a test parameter requirement against a config parameter value.

    Supports comparison operator prefixes on strings with decimal or hex values.
    e.g. '>=128', '<= 64', '> 0', '<256', '!=0', '==64', '>=0x80', '<0xFF'.
    Falls back to exact equality if there is no comparison operator prefix.
    """
    if isinstance(test_value, str):
        match = _COMPARISON_RE.match(test_value)
        if match:
            op, required_val = match.groups()
            required_val = int(required_val, 0)
            if type(config_value) is not int:
                return False
            if op == ">=":
                return config_value >= required_val
            if op == "<=":
                return config_value <= required_val
            if op == ">":
                return config_value > required_val
            if op == "<":
                return config_value < required_val
            if op == "!=":
                return config_value != required_val
            if op == "==":
                return config_value == required_val
    return test_value == config_value


def check_test_params(test_params: dict[str, int | bool | str], config_params: dict[str, ConfigParamValue]) -> bool:
    """Check if all parameters in test_params match those in config_params."""
    for param, value in test_params.items():
        if param not in config_params:
            return False
        if not _compare_param(value, config_params[param]):
            return False
    return True


def select_tests(
    test_dict: dict[str, TestMetadata],
    implemented_extensions: set[str],
    config_params: dict[str, ConfigParamValue],
    *,
    include_priv_tests: bool = True,
) -> dict[str, TestMetadata]:
    """Select tests that match the UDB configuration."""
    selected_tests: dict[str, TestMetadata] = {}
    for test_name, test_metadata in test_dict.items():
        # Skip privileged tests if disabled
        if not include_priv_tests and not test_metadata.required_extensions.isdisjoint(PRIV_EXTENSIONS):
            continue
        # Check if all required extensions are implemented
        if test_metadata.required_extensions.issubset(implemented_extensions):
            # Check if all parameters match
            test_params = test_metadata.params
            if check_test_params(test_params, config_params):
                selected_tests[test_name] = test_metadata
    return selected_tests
