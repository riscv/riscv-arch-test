##################################
# select_tests.py
#
# jcarlin@hmc.edu 6 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Select tests to run based on UDB config and test list
##################################

import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from rich import print as rprint

from act.certificate_tests import get_certificate_extensions
from act.config import Config, load_config
from act.parse_test_constraints import ExtensionRequirement, TestMetadata
from act.parse_udb_config import get_config_params, get_implemented_extensions, prepare_dut_outputs
from act.toolchain import EXPERIMENTAL_EXTENSIONS

PRIV_EXTENSIONS = {"Sm", "S", "U", "H"}

# Type alias
ConfigParamValue = int | bool | str | list[int | str | bool]

# Parameter constraint comparison operators
_COMPARISON_RE = re.compile(r"^(>=|<=|!=|==|>|<)\s*(0[xX][0-9a-fA-F]+|\d+)$")


def _compare_param(test_value: object, config_value: object) -> bool:
    """Compare a test parameter requirement against a config parameter value.

    A list config value (e.g. SUPPORTED_PMLEN_SMMPM: [0, 7, 16]) matches when it contains the test value.
    Supports comparison operator prefixes on strings with decimal or hex values.
    e.g. '>=128', '<= 64', '> 0', '<256', '!=0', '==64', '>=0x80', '<0xFF'.
    Falls back to exact equality if there is no comparison operator prefix.
    """
    if isinstance(config_value, list):
        return test_value in config_value
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


def check_test_extensions(
    required_extensions: frozenset[ExtensionRequirement],
    forbidden_extensions: frozenset[str],
    implemented_extensions: frozenset[str],
) -> bool:
    """Check required, alternative, and forbidden extension constraints."""
    if not forbidden_extensions.isdisjoint(implemented_extensions):
        return False

    return all(
        requirement in implemented_extensions
        if isinstance(requirement, str)
        else not requirement.isdisjoint(implemented_extensions)
        for requirement in required_extensions
    )


def _requires_extension_from(
    required_extensions: frozenset[ExtensionRequirement], extensions: frozenset[str] | set[str]
) -> bool:
    """Check whether a requirement can only be met with an extension in the given set."""
    return any(
        requirement in extensions if isinstance(requirement, str) else requirement.issubset(extensions)
        for requirement in required_extensions
    )


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
    implemented_extensions: frozenset[str],
    config_params: dict[str, ConfigParamValue],
    harts: int = 1,
    *,
    include_priv_tests: bool = True,
    enable_experimental_extensions: bool = False,
) -> dict[str, TestMetadata]:
    """Select tests that match the DUT configuration."""
    selected_tests: dict[str, TestMetadata] = {}
    for test_name, test_metadata in test_dict.items():
        if harts < test_metadata.min_harts:
            continue
        # Skip privileged tests if disabled
        if not include_priv_tests and _requires_extension_from(test_metadata.required_extensions, PRIV_EXTENSIONS):
            continue
        # Skip experimental extensions unless enabled
        if not enable_experimental_extensions and _requires_extension_from(
            test_metadata.required_extensions, EXPERIMENTAL_EXTENSIONS
        ):
            continue
        # Check if all extensions match
        if check_test_extensions(
            test_metadata.required_extensions,
            test_metadata.forbidden_extensions,
            implemented_extensions,
        ):
            # Check if all parameters match
            test_params = test_metadata.params
            if check_test_params(test_params, config_params):
                selected_tests[test_name] = test_metadata
    return selected_tests


def filter_tests_by_certificate(test_dict: dict[str, TestMetadata], certificate: str) -> dict[str, TestMetadata]:
    """Select tests whose required extensions are all covered by a certificate."""
    certificate_extensions = get_certificate_extensions(certificate)
    return {
        test_name: test_metadata
        for test_name, test_metadata in test_dict.items()
        if check_test_extensions(test_metadata.required_extensions, frozenset(), certificate_extensions)
    }


def _print_skipped_suites(
    config_name: str,
    certificate: str,
    selected_tests: dict[str, TestMetadata],
    certificate_tests: dict[str, TestMetadata],
) -> None:
    """Print the suites with tests that the DUT config selects but the certificate skips."""
    skipped_counts = Counter(Path(name).parent.name for name in selected_tests.keys() - certificate_tests.keys())
    total_counts = Counter(Path(name).parent.name for name in selected_tests)
    total_skipped = sum(skipped_counts.values())
    rprint(
        f"[bold yellow]{config_name}:[/] skipping {total_skipped} tests in {len(skipped_counts)} suites "
        f"not part of {certificate}:"
    )
    name_width = max(map(len, skipped_counts), default=0)
    for suite, skipped in sorted(skipped_counts.items()):
        total = total_counts[suite]
        print(f"  {suite:<{name_width}}  {skipped:>4} of {total:>4} tests")


def write_test_list(config_name: str, selected_tests: dict[str, TestMetadata], output_file: Path) -> None:
    """Write the selected suites and their test counts as a Markdown table."""
    suite_counts = Counter(Path(name).parent.name for name in selected_tests)
    rows = [(suite, str(count)) for suite, count in sorted(suite_counts.items())]
    suite_width = max([len("Suite")] + [len(suite) for suite, _ in rows])
    count_width = max([len("Tests")] + [len(count) for _, count in rows])
    lines = [
        f"# Selected tests for {config_name}",
        "",
        f"| {'Suite':<{suite_width}} | {'Tests':>{count_width}} |",
        f"| {'-' * suite_width} | {'-' * (count_width - 1)}: |",
    ]
    lines.extend(f"| {suite:<{suite_width}} | {count:>{count_width}} |" for suite, count in rows)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines) + "\n")


def prepare_configs_and_select_tests(
    config_files: Sequence[Path],
    certificate: str | None,
    full_test_dict: dict[str, TestMetadata],
    workdir: Path,
    *,
    jobs: int = 1,
    verbose: bool = False,
    validate_tools: bool = True,
    enable_experimental_extensions: bool = False,
) -> list[tuple[Config, dict[str, ConfigParamValue], dict[str, TestMetadata]]]:
    """Load configs, generate their UDB outputs, and select tests for each.

    Loads each config, prepares all DUT-derived files (including
    extensions.txt) in one parallel UDB pass, then runs select_tests per
    config. Returns a (config, config_params, selected_tests) tuple per
    config file, in input order.

    Args:
        config_files: ACT test config files to load.
        certificate: Certificate that limits selected tests to its extensions.
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
        implemented_extensions = get_implemented_extensions(workdir / config.name / "env" / "extensions.txt")
        config_params = get_config_params(config.udb_config)
        selected_tests = select_tests(
            full_test_dict,
            implemented_extensions,
            config_params,
            harts=config.harts,
            include_priv_tests=config.include_priv_tests,
            enable_experimental_extensions=enable_experimental_extensions,
        )
        if certificate:
            certificate_tests = filter_tests_by_certificate(selected_tests, certificate)
            _print_skipped_suites(config.name, certificate, selected_tests, certificate_tests)
            selected_tests = certificate_tests
        results.append((config, config_params, selected_tests))
    return results
