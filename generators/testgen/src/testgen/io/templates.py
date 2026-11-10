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

from testgen.constants import EXPERIMENTAL_EXTENSIONS
from testgen.data.config import TestConfig


def load_template(template_name: str) -> str:
    """Load a template file from the templates package."""
    with importlib.resources.open_text("testgen.templates", template_name) as template_file:
        template = template_file.read()
    return template


def insert_header_template(
    test_config: TestConfig,
    test_file: Path,
    sigupd_count: int,
    extra_defines: list[str] | None = None,
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
    forbidden_extensions = test_config.forbidden_extensions
    alternative_extensions = (
        [] if required_extensions is None else [ext for ext in required_extensions if isinstance(ext, list)]
    )
    required_extensions = (
        None if required_extensions is None else [ext for ext in required_extensions if isinstance(ext, str)]
    )
    ext_components, params = canonicalize_extensions(
        testsuite, xlen, E_ext, required_extensions, test_config.extra_extensions
    )
    extension_requirements = [*ext_components, *alternative_extensions]
    flat_ext_components = ext_components + [ext for alternatives in alternative_extensions for ext in alternatives]
    if test_config.extra_params:
        params.extend(test_config.extra_params)
    march_extensions = test_config.march_extensions
    if march_extensions is not None:
        march_ext_components, _ = canonicalize_extensions(testsuite, xlen, E_ext, march_extensions)
        march = generate_march_string(march_ext_components, xlen)
        # combine required_extensions and march_extensions for extra_defines
        all_extensions = list(dict.fromkeys(flat_ext_components + march_ext_components))
    else:
        all_extensions = flat_ext_components
        march = generate_march_string(all_extensions, xlen)
    all_defines = [*(extra_defines or []), *generate_defines_from_extensions(all_extensions)]
    if not EXPERIMENTAL_EXTENSIONS.isdisjoint(all_extensions):
        all_defines.append("#define RVTEST_EXPERIMENTAL")
    # Replace placeholders
    forbidden_extension_line = "" if not forbidden_extensions else f"\n# FORBIDDEN_EXTENSIONS: {forbidden_extensions}"
    template = (
        template.replace("@TEST_PATH@", f"{test_file}")
        .replace("@EXTENSION_LIST@", f"{extension_requirements}{forbidden_extension_line}")
        .replace("@PARAMS@", format_params(params, flat_ext_components))
        .replace("@MARCH@", march)
        .replace("@EXTRA_DEFINES@", "\n".join(all_defines))
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
    testsuite: str,
    xlen: int,
    E_ext: bool,
    required_extensions: list[str] | None = None,
    extra_extensions: tuple[str, ...] = (),
) -> tuple[list[str], list[str]]:
    """Canonicalize extension string.

    Args:
        testsuite: Test suite name from test config.
        xlen: XLEN value.
        E_ext: Whether the E extension is enabled.
        required_extensions: If provided, use these extensions instead of parsing from testsuite.
        sew: Optional. Used in vector suites to determine the base extension
        instr_name: Optional. Used in vector suites to determine whether or not an instruction is part of a base extension
        extra_extensions: Optional. Extensions a testplan row requires beyond the testsuite's own.
    """
    # Use required_extensions if provided, otherwise parse from testsuite name
    ext_components = (
        required_extensions.copy() if required_extensions is not None else re.findall(r"[A-Z][a-z0-9]*", testsuite)
    )
    ext_components.extend(extra_extensions)

    # Extract parameters
    params: list[str] = []
    if xlen > 0:
        params.append(f"MXLEN: {xlen}")

    # Canonicize extensions
    if "I" not in ext_components and "E" not in ext_components:
        ext_components.insert(0, "E" if E_ext else "I")  # Always include base integer extension
    if any(ext in ext_components for ext in ["Zcd", "Zve64d", "V"]):
        ext_components.append("D")  # Add D if any double precision floating point extension is present
    if any(
        ext in ext_components
        for ext in ["Zcf", "D", "Zfh", "Zfhmin", "Zfa", "Zfbfmin", "Zvfh", "Zvfhmin", "Zve32f", "Zve64f"]
    ):
        ext_components.append("F")  # Add F if any floating point extension is present

    ext_components = list(dict.fromkeys(ext_components))  # Remove duplicates while preserving order

    return ext_components, params


# Canonical order from RISC-V ISA spec
_EXTENSION_CANONICAL_ORDER = "iemafdqlcbkjtpvh"


def _single_letter_sort_key(ext: str) -> int:
    """Return the canonical sort position for a single-letter extension."""
    ext = ext.lower()
    if ext in _EXTENSION_CANONICAL_ORDER:
        return _EXTENSION_CANONICAL_ORDER.index(ext)
    return len(_EXTENSION_CANONICAL_ORDER)


def _multi_letter_sort_key(ext: str) -> tuple[int, int, str]:
    """Return sort key for multi-letter extensions in canonical order.

    Sort order: Z extensions first, then S extensions, then others.
    Z extensions are sub-sorted by their second letter in canonical
    single-letter order (e.g. Zi* < Zm* < Za* < Zf* < Zb* < Zv*),
    then alphabetically within the same sub-group.
    """
    ext = ext.lower()
    if ext.startswith("z"):
        group = 0
        # Sub-group by second letter in canonical single-letter order
        second_letter = ext[1] if len(ext) > 1 else ""
        subgroup = (
            _EXTENSION_CANONICAL_ORDER.index(second_letter)
            if second_letter in _EXTENSION_CANONICAL_ORDER
            else len(_EXTENSION_CANONICAL_ORDER)
        )
    elif ext.startswith("s"):
        group = 1
        subgroup = 0
    else:
        group = 2
        subgroup = 0
    return (group, subgroup, ext)


def generate_march_string(ext_components: list[str], xlen: int) -> str:
    """Generate march string from extension components."""
    # Separate single-letter and multi-letter extensions
    single_letter: list[str] = []
    multi_letter: list[str] = []
    for ext in ext_components:
        if ext in ["Sm", "S", "U"]:
            continue  # Skip privilege modes in march string
        if len(ext) == 1:
            single_letter.append(ext)
        else:
            multi_letter.append(ext)

    # Always include Zicsr so boot code CSR instructions can compile
    if "Zicsr" not in multi_letter:
        multi_letter.append("Zicsr")

    # Always include Zifencei so trap handler fence.i can be assembled
    if "Zifencei" not in multi_letter:
        multi_letter.append("Zifencei")

    # workaround for https://github.com/llvm/llvm-project/issues/190910; can be removed when this is resolved
    if ("Zihintntl" in multi_letter) and ("Zca" in multi_letter):
        single_letter.append("C")

    # Sort single-letter extensions in canonical order (I/E, M, A, F, D, Q, C, B, V, H)
    single_letter.sort(key=_single_letter_sort_key)
    # Sort multi-letter extensions in canonical order (Z by subgroup then alpha, S alpha, others alpha)
    multi_letter.sort(key=_multi_letter_sort_key)

    # Construct march string: single-letter extensions first (no separator), then multi-letter (underscore separated)
    ext_str = "".join(single_letter)
    if multi_letter:
        ext_str += "_" + "_".join(multi_letter)
    ext_str = ext_str.lower()
    march = f"rv{xlen if xlen != 0 else '${XLEN}'}{ext_str}"

    return march


def format_params(params: list[str], ext_components: list[str]) -> str:
    """Format parameters for insertion into template."""
    param_lines = ["params:"]
    if False:  # any(ext in ext_components for ext in ["Sm", "H", "S", "U"]):  # might need hack to require standard Sm for all priv tests until custom trap handler setup works
        param_lines.append(
            "#    STANDARD_SM_SUPPORTED: True"
        )  # dh 4/23/26 seems to need true, not in UDB, not sure how to handle yet
    elif not params:
        return "# # no param constraints"  # Extra comment symbol necessary because YAML parser strips initial comment
    param_lines.extend(f"#   {param}" for param in params)
    return "\n".join(param_lines)


def generate_defines_from_extensions(ext_components: list[str]) -> list[str]:
    """Generate extra #define statements from extension components."""
    extra_defines: list[str] = []

    # disable the following defines until booting to modes is implemented dh 7/1/26
    # if any(ext in ext_components for ext in ["H", "S"]):
    #     extra_defines.append("#define BOOT_TO_SMODE")
    # elif "Sm" in ext_components:
    #     extra_defines.append("#define BOOT_TO_MMODE")

    return extra_defines
