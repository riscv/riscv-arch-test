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

from testgen.data.config import TestConfig


def load_template(template_name: str) -> str:
    """Load a template file from the templates package."""
    with importlib.resources.open_text("testgen.templates", template_name) as template_file:
        template = template_file.read()
    return template


def insert_header_template(
    test_config: TestConfig, test_file: Path, sigupd_count: int, extra_defines: list[str] | None = None
) -> str:
    """Load testgen header template file and replace placeholders."""
    template = load_template("testgen_header.S")
    # Extract extension components
    xlen = test_config.xlen
    extension = test_config.extension
    E_ext = test_config.E_ext
    ext_components, params = canonicalize_extensions(extension, xlen, E_ext)
    march = generate_march_string(ext_components, xlen)
    if extra_defines is None:
        extra_defines = []
    extra_defines.extend(generate_defines_from_extensions(ext_components))
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


def canonicalize_extensions(extension: str, xlen: int, E_ext: bool) -> tuple[list[str], list[str]]:
    """Canonicalize extension string."""
    ext_components = re.findall(r"[A-Z][a-z]*", extension)

    # Extract parameters
    params: list[str] = []
    if xlen > 0:
        params.append(f"MXLEN: {xlen}")
    param_lookup = {
        "Misalign": "MISALIGNED_LDST: true",
    }
    for ext in ext_components:
        if ext in param_lookup:
            params.append(param_lookup[ext])
            ext_components.remove(ext)

    # Canonicize extensions
    if "I" not in ext_components and "E" not in ext_components:
        # Always include base integer extension
        if E_ext:
            ext_components.insert(0, "E")
        else:
            ext_components.insert(0, "I")
    if "Zcd" in ext_components and "D" not in ext_components:
        ext_components.append("D")  # Add D if Zcd is present
    if any(ext in ext_components for ext in ["Zcf", "D", "Zfh", "Zfhmin", "Zfa"]) and "F" not in ext_components:
        ext_components.append("F")  # Add F if any floating point extension is present
    if any(ext in ext_components for ext in ["Sm", "S", "U", "H"]) and "F" not in ext_components:
        ext_components.append("Zicsr")  # Add Zicsr is any priv extension is present

    return ext_components, params


def generate_march_string(ext_components: list[str], xlen: int) -> str:
    """Generate march string from extension components."""
    # Construct march string
    ext_str = ""
    for ext in ext_components:
        if ext in ["Sm", "S", "U"]:
            continue  # Skip privilege modes in march string
        if len(ext_str) > 0:
            ext_str += "_"
        ext_str += ext
    ext_str = ext_str.lower()
    march = f"rv{xlen if xlen != 0 else '${XLEN}'}{ext_str}"
    march = march.replace("zaamo", "a").replace("zalrsc", "a")  # gcc 14 does not accept Zaamo/Zalrsc

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
