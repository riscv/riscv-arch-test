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
from collections.abc import Sequence
from pathlib import Path

from act.config import Config, load_config
from act.parse_test_constraints import TestMetadata
from act.parse_udb_config import (
    get_config_params,
    get_implemented_extensions,
    get_ref_model_pmp_params,
    prepare_dut_outputs,
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


def prepare_configs_and_select_tests(
    config_files: Sequence[Path],
    full_test_dict: dict[str, TestMetadata],
    workdir: Path,
    *,
    jobs: int = 1,
    verbose: bool = False,
    validate_tools: bool = True,
) -> list[tuple[Config, dict[str, ConfigParamValue], dict[str, TestMetadata]]]:
    """Load configs, generate their UDB outputs, and select tests for each.

    Loads each config, prepares all DUT-derived files (including
    extensions.txt) in one parallel UDB pass, then runs select_tests per
    config. Returns a (config, config_params, selected_tests) tuple per
    config file, in input order.

    Args:
        config_files: ACT test config files to load.
        full_test_dict: Candidate tests, usually from ``generate_test_dict``.
        workdir: Directory for generated UDB outputs (one subdir per config).
        jobs: Parallelism for DUT output generation.
        verbose: Verbose output during DUT output generation.
        validate_tools: Validate configured compiler and simulator executables
            when true. Set false for callers that only need test selection and
            may run before those tools are installed.
    """
    configs = [load_config(config_file, validate_tools=validate_tools) for config_file in config_files]
    prepare_dut_outputs(configs, workdir, jobs, verbose)

    results: list[tuple[Config, dict[str, ConfigParamValue], dict[str, TestMetadata]]] = []
    for config in configs:
        implemented_extensions = get_implemented_extensions(workdir / config.name / "extensions.txt")
        config_params = get_config_params(config.udb_config) | get_ref_model_pmp_params(config.dut_include_dir)
        selected_tests = select_tests(
            full_test_dict, implemented_extensions, config_params, include_priv_tests=config.include_priv_tests
        )
        results.append((config, config_params, selected_tests))
    return results
