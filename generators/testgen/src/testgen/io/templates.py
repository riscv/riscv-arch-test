##################################
# io/templates.py
#
# Template loading and insertion for test files.
# jcarlin@hmc.edu 5 October 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Template loading and insertion for test files."""

from __future__ import annotations

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
    test_config: TestConfig,
    test_file: Path,
    sigupd_count: int,
    extra_defines: list[str] | None = None,
    instr_name: str | None = None,
) -> str:
    """Load testgen header template file and replace placeholders.

    Args:
        test_config: Test configuration containing xlen, testsuite, E_ext, etc.
        test_file: Path to the test file (for header comments).
        sigupd_count: Number of signature updates in the test.
        extra_defines: (optional) Additional #define statements for the test.
        instr_name: (optional) Needed for vector tests to canonicalize extension names.
    """
    template = load_template("testgen_header.S")
    # Extract extension components
    xlen = test_config.xlen
    sew = test_config.sew
    testsuite = test_config.testsuite
    E_ext = test_config.E_ext
    required_extensions = test_config.required_extensions
    ext_components, params = canonicalize_extensions(testsuite, xlen, E_ext, required_extensions, sew, instr_name)
    if test_config.extra_params:
        params.extend(test_config.extra_params)
    march_extensions = test_config.march_extensions
    if march_extensions is not None:
        march_ext_components, _ = canonicalize_extensions(testsuite, xlen, E_ext, march_extensions, sew, instr_name)
        march = generate_march_string(march_ext_components, xlen)
        # combine required_extensions and march_extensions for extra_defines
        all_extensions = list(dict.fromkeys(ext_components + march_ext_components))
    else:
        march = generate_march_string(ext_components, xlen)
        all_extensions = ext_components
    all_defines = [*(extra_defines or []), *generate_defines_from_extensions(all_extensions)]
    # Replace placeholders
    template = (
        template.replace("@TEST_PATH@", f"{test_file}")
        .replace("@TEST_FILE_NAME@", f"{test_file.name}")
        .replace("@EXTENSION_LIST@", f"{ext_components}")
        .replace("@PARAMS@", format_params(params, ext_components))
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
    sew: int | None = None,
    instr_name: str | None = None,
) -> tuple[list[str], list[str]]:
    """Canonicalize extension string.

    Args:
        testsuite: Test suite name from test config.
        xlen: XLEN value.
        E_ext: Whether the E extension is enabled.
        required_extensions: If provided, use these extensions instead of parsing from testsuite.
        sew: Optional. Used in vector suites to determine the base extension
        instr_name: Optional. Used in vector suites to determine whether or not an instruction is part of a base extension
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

    # Handle Vector
    if testsuite.startswith(("V", "Zv")):
        assert sew is not None, "SEW must be set for all unpriv vector tests"
        assert instr_name is not None, "Passing an instruction is required for all vector extensions"

        # Get the most minimal V subextension for Vx, Vls, and Vf (e.g. Zve32f for Vf32)
        maybe_mapped = get_vector_base_extension(testsuite, instr_name, xlen, sew)
        if maybe_mapped is not None:
            ext_components.extend(maybe_mapped)

            # Our tests run some vector tests with the test SEW as a suffix. These suffixes are not part of
            # extension names, so they need to be dropped from the extensions list
            no_sew_suffix = re.sub(r"\d+$", "", testsuite)
            if no_sew_suffix in ext_components:
                ext_components.remove(no_sew_suffix)

    if any(ext.startswith(("V", "Zv")) for ext in ext_components):
        ext_components.append("M")  # Add M if V is present (required for gcc 15)

    ext_components = list(dict.fromkeys(ext_components))  # Remove duplicates while preserving order

    return ext_components, params


def get_vector_base_extension(testsuite: str, instr_name: str, xlen: int, sew: int) -> list[str] | None:
    """
    Helper function to derive the smallest possible vector extension containing an instruction. This is necessary because
    Vx, Vls, and Vf are not RISCV extensions. This maps each Vx, Vls, and Vf extension to one of Zve32(x|f), Zve64(x|f|d),
    Zvfh, or V. The requirements to be in one of these extensions can depend on xlen or sew, so these arguments contain
    necessary information.
    """
    vector_map = {
        "Vx8": ["Zve32x"],
        "Vx16": ["Zve32x"],
        "Vx32": ["Zve32x"],
        "Vls8": ["Zve32x"],
        "Vls16": ["Zve32x"],
        "Vls32": ["Zve32x"],
        "Vx64": ["Zve64x"],
        "Vls64": ["Zve64x"],
        "Vf16": ["Zvfh"],
        "Vf32": ["Zve32f"],
        "Vf64": ["Zve64d"],
    }

    if testsuite not in vector_map:
        return

    mapped = vector_map[testsuite]

    for zve_ext in ["Zve64x", "Zve64f", "Zve64d"]:
        # All Zve* extensions support all vector load and store instructions (31.1.7. Vector Loads and Stores),
        # except Zve64* extensions do not support EEW=64 for index values when XLEN=32.
        if zve_ext in mapped and "ei64" in instr_name and xlen == 32:
            mapped.remove(zve_ext)

        # All Zve* extensions support all vector integer instructions (31.1.11. Vector Integer Arithmetic
        # Instructions), except that the vmulh integer multiply variants that return the high word of the
        # product (vmulh.vv, vmulh.vx, vmulhu.vv, vmulhu.vx, vmulhsu.vv, vmulhsu.vx) are not included for
        # EEW=64 in Zve64*.
        if zve_ext in mapped and instr_name.startswith("vmulh") and sew == 64:
            mapped.remove(zve_ext)

        # All Zve* extensions support all vector fixed-point arithmetic instructions (31.1.12. Vector Fixed-Point
        # Arithmetic Instructions), except that vsmul.vv and vsmul.vx are not included in EEW=64 in Zve64*.
        if zve_ext in mapped and instr_name.startswith("vsmul") and sew == 64:
            mapped.remove(zve_ext)

        # All Zve* extensions support all vector permutation instructions (31.1.16. Vector Permutation Instructions),
        # except that Zve32x and Zve64x do not include those with floating-point operands, and Zve64f does not include
        # those with EEW=64 floating-point operands.
        # The first part of this requirement is handled by placing those operands into Vf.
        if (
            zve_ext in mapped
            and instr_name in ["vfmv.f.s", "vfmv.s.f", "vfslide1up.vf", "vfslide1down.vf"]
            and sew == 64
        ):
            mapped.remove(zve_ext)

    if "Zve32x" in mapped and instr_name.startswith(("vw", "vn")) and sew == 32:
        # Zve32x allows for an ELEN of 32, so a widening instruction at sew = 32 would widen to an eew of 64, which
        # requires Zve64x.
        mapped.remove("Zve32x")
        mapped.append("Zve64x")

    if mapped == []:
        return ["V"]

    return mapped


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
