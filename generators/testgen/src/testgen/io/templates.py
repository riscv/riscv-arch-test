##################################
# io/templates.py
#
# Template loading and insertion for test files.
# jcarlin@hmc.edu 5 October 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Template loading and insertion for test files."""

import importlib.resources
import re
from pathlib import Path

from testgen.constants import EXTENSION_PARAM_MAP
from testgen.data.config import TestConfig


def load_template(template_name: str) -> str:
    """Load a template file from the templates package."""
    with importlib.resources.open_text("testgen.templates", template_name) as template_file:
        template = template_file.read()
    return template


def insert_header_template(
    test_config: TestConfig, test_file: Path, sigupd_count: int, extra_defines: list[str] | None = None
) -> str:
    """Load testgen header template file and replace placeholders.

    Args:
        test_config: Test configuration containing xlen, testsuite, E_ext, etc.
        test_file: Path to the test file (for header comments).
        sigupd_count: Number of signature updates in the test.
        extra_defines: (optional) Additional #define statements for the test.
    """
    template = load_template("testgen_header.S")
    # Extract extension components
    xlen = test_config.xlen
    testsuite = test_config.testsuite
    E_ext = test_config.E_ext
    required_extensions = test_config.required_extensions
    ext_components, params = canonicalize_extensions(testsuite, xlen, E_ext, required_extensions)
    march_extensions = test_config.march_extensions
    if march_extensions is not None:
        march_ext_components, _ = canonicalize_extensions(testsuite, xlen, E_ext, march_extensions)
        march = generate_march_string(march_ext_components, xlen)
        # combine required_extensions and march_extensions for extra_defines
        all_extensions = list(dict.fromkeys(ext_components + march_ext_components))
    else:
        march = generate_march_string(ext_components, xlen)
        all_extensions = ext_components
    if extra_defines is None:
        extra_defines = []
    extra_defines.extend(generate_defines_from_extensions(all_extensions))
    # Replace placeholders
    template = (
        template.replace("@TEST_PATH@", f"{test_file}")
        .replace("@TEST_FILE_NAME@", f"{test_file.name}")
        .replace("@EXTENSION_LIST@", f"{ext_components}")
        .replace("@PARAMS@", format_params(params))
        .replace("@MARCH@", march)
        .replace("@EXTRA_DEFINES@", "\n".join(extra_defines))
        .replace("@CONFIG_DEPENDENT@", str(test_config.config_dependent).lower())
        .replace("@SIGUPD_COUNT_FROM_TESTGEN@", str(sigupd_count))
    )
    return template


def insert_footer_template(test_data_section: str, test_string_section: str) -> str:
    """Load testgen footer template file and replace placeholders."""
    template = load_template("testgen_footer.S")
    # Replace placeholders
    template = template.replace("@TEST_DATA@", test_data_section).replace("@TESTCASE_STRINGS@", test_string_section)
    return template


def canonicalize_extensions(
    testsuite: str, xlen: int, E_ext: bool, required_extensions: list[str] | None = None
) -> tuple[list[str], list[str]]:
    """Canonicalize extension string.

    Args:
        testsuite: Test suite name from test config.
        xlen: XLEN value.
        E_ext: Whether the E extension is enabled.
        required_extensions: If provided, use these extensions instead of parsing from testsuite.
    """
    # Use required_extensions if provided, otherwise parse from testsuite name
    ext_components = required_extensions.copy() if required_extensions else re.findall(r"[A-Z][a-z]*", testsuite)

    # Extract parameters
    params: list[str] = []
    if xlen > 0:
        params.append(f"MXLEN: {xlen}")
    for ext in ext_components:
        if ext in EXTENSION_PARAM_MAP:
            params.append(EXTENSION_PARAM_MAP[ext])
            ext_components.remove(ext)

    # Canonicize extensions
    if "I" not in ext_components and "E" not in ext_components:
        ext_components.insert(0, "E" if E_ext else "I")  # Always include base integer extension
    if "Zcd" in ext_components:
        ext_components.append("D")  # Add D if Zcd is present
    if any(ext in ext_components for ext in ["Zcf", "D", "Zfh", "Zfhmin", "Zfa", "Zfbfmin"]):
        ext_components.append("F")  # Add F if any floating point extension is present
    if any(ext in ext_components for ext in ["Sm", "S", "U", "H"]):
        ext_components.append("Zicsr")  # Add Zicsr if any priv extension is present
    if any(ext in ext_components for ext in ["V", "Zvfh"]):
        ext_components.append("M")  # Add M if V is present (required for gcc 15)

    ext_components = list(dict.fromkeys(ext_components))  # Remove duplicates while preserving order

    return ext_components, params


def generate_march_string(ext_components: list[str], xlen: int) -> str:
    """Generate march string from extension components."""
    # Separate single-letter and multi-letter extensions
    single_letter = []
    multi_letter = []
    for ext in ext_components:
        if ext in ["Sm", "S", "U"]:
            continue  # Skip privilege modes in march string
        if len(ext) == 1:
            single_letter.append(ext)
        else:
            multi_letter.append(ext)

    # Construct march string: single-letter extensions first (no separator), then multi-letter (underscore separated)
    ext_str = "".join(single_letter)
    if multi_letter:
        ext_str += "_".join(multi_letter)
    ext_str = ext_str.lower()
    march = f"rv{xlen if xlen != 0 else '${XLEN}'}{ext_str}"

    return march


def format_params(params: list[str]) -> str:
    """Format parameters for insertion into template."""
    if not params:
        return "# # no param constraints"  # Extra comment symbol necessary because YAML parser strips initial comment
    param_lines = ["params:"]
    for param in params:
        param_lines.append(f"#   {param}")
    return "\n".join(param_lines)


def generate_defines_from_extensions(ext_components: list[str]) -> list[str]:
    """Generate extra #define statements from extension components."""
    extra_defines: list[str] = []
    # Enable floating point if needed
    if "F" in ext_components:
        extra_defines.append("#define RVTEST_FP")
    # TODO: Enable vector extension if needed when vector testgen is integrated

    # Enable trap handlers if needed
    if "H" in ext_components:
        extra_defines.append("#define rvtest_vtrap_routine")
    if any(ext in ext_components for ext in ["H", "S"]):
        extra_defines.append("#define rvtest_strap_routine")
    if any(ext in ext_components for ext in ["Sm", "H", "S", "U"]):
        extra_defines.append("#define rvtest_mtrap_routine")

    return extra_defines
