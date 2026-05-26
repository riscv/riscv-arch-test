##################################
# select_tests.py
#
# jcarlin@hmc.edu 6 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Select tests to run based on UDB config and test list
##################################

from __future__ import annotations

import re
from pathlib import Path

from act.config import Config, load_config
from act.parse_test_constraints import TestMetadata, generate_test_dict
from act.parse_udb_config import (
    generate_udb_files,
    get_config_implemented_extensions,
    get_config_params,
    get_implemented_extensions,
)

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


def select_tests_for_config_data(
    config_file: Path,
    full_test_dict: dict[str, TestMetadata],
    workdir: Path,
    *,
    validate_tools: bool = True,
    generate_udb: bool = True,
) -> tuple[Config, dict[str, ConfigParamValue], dict[str, TestMetadata]]:
    """Return config data and tests selected by the ACT framework for a single config."""
    config = load_config(config_file, validate_tools=validate_tools)
    config_dir = workdir / config.udb_config.stem
    config_dir.mkdir(parents=True, exist_ok=True)

    if generate_udb:
        generate_udb_files(config.udb_config, config_dir)
        implemented_extensions = get_implemented_extensions(config_dir / "extensions.txt")
    else:
        implemented_extensions = get_config_implemented_extensions(config.udb_config)
    config_params = get_config_params(config.udb_config)

    selected_tests = select_tests(
        full_test_dict, implemented_extensions, config_params, include_priv_tests=config.include_priv_tests
    )
    return config, config_params, selected_tests


def select_tests_for_config(
    config_file: Path,
    test_dir: Path,
    workdir: Path,
    extensions: str = "all",
    exclude: str = "",
) -> dict[str, TestMetadata]:
    """Return tests selected by the ACT framework for a single config.

    This is the reusable framework-level selection path shared by CI matrix
    discovery. It intentionally skips simulator and compiler executable
    validation so lightweight discovery jobs can compute the same selected
    test set without installing those tools first.
    """
    full_test_dict = generate_test_dict(test_dir, extensions, exclude)
    _, _, selected_tests = select_tests_for_config_data(
        config_file, full_test_dict, workdir, validate_tools=False, generate_udb=False
    )
    return selected_tests
