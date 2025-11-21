##################################
# load_templates.py
#
# jcarlin@hmc.edu 5 Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""
Insert templates into test files.
"""

import importlib.resources
import re

from testgen.data.test_data import TestData


def insert_setup_template(template_name: str, xlen: int, extension: str, test_file: str) -> str:
    """Insert a header/footer template file into the test file."""
    ext_components, march = canonicalize_extension(extension, xlen)
    with importlib.resources.open_text("testgen.templates", template_name) as template_file:
        template = template_file.read()
    # Replace placeholders
    template = (
        template.replace("@TEST_PATH@", f"{test_file}")
        .replace("@EXTENSION_LIST@", f"{ext_components}")
        .replace("@MARCH@", march.lower())
        .replace("@XLEN@", str(xlen))
        .replace("@CONFIG_DEPENDENT@", "false")  # TODO: Make this configurable for some tests (e.g. Zimop)
    )
    return template


def insert_test_template(template_name: str, xlen: int, test_data: TestData) -> tuple[str, int]:
    """Insert a custom test template into the test file, handling signature pointer updates."""
    with importlib.resources.open_text("testgen.templates", template_name) as template_file:
        template = template_file.read()
    # Extract test data
    test_lines = test_data.int_regs.reset_special_registers()
    sig_reg = test_data.int_regs.sig_reg
    link_reg = test_data.int_regs.link_reg
    temp_reg = test_data.int_regs.temp_reg
    # Initialize return variables
    sigupd_count_increment = 0
    # Count SIGUPD macros
    sigupd_count_custom = template.count("RVTEST_SIGUPD(")
    # Count SIG_POINTER_INCREMENT(...) macros
    sig_pointer_incr_matches = list(re.finditer(r"SIG_POINTER_INCREMENT\((\d+)\)", template))
    # Move sig pointer to x3 for use in custom template
    # Handle RVTEST_SIGUPD macros
    template = (
        template.replace("SIGPOINTER", f"x{sig_reg}")
        .replace("LINKREG", f"x{link_reg}")
        .replace("TEMPREG", f"x{temp_reg}")
    )
    sigupd_count_increment += sigupd_count_custom
    # Handle SIG_POINTER_INCREMENT(n) macros
    if sig_pointer_incr_matches:
        for match in sig_pointer_incr_matches:
            incr_val = int(match.group(1))
            addi_instr = f"addi x{sig_reg}, x{sig_reg}, {incr_val}  # increment pointer {incr_val} bytes"
            template = template.replace(match.group(0), addi_instr, 1)
            sigupd_count_increment += incr_val // (4 * (xlen // 32))
    # Handle wrong or unused macro
    elif "SIG_POINTER_INCREMENT" in template and not sig_pointer_incr_matches:
        raise ValueError(f"Invalid or missing SIG_POINTER_INCREMENT(n) in '{template_name}'.")
    # Return test text and sigupd count increment
    test_lines += template
    return template, sigupd_count_increment


def canonicalize_extension(extension: str, xlen: int) -> tuple[list[str], str]:
    """Canonicalize extension string."""
    ext_components = re.findall(r"[A-Z][a-z]*", extension)
    if "I" not in ext_components and "E" not in ext_components:
        ext_components.insert(0, "I")  # Always include base integer extension
    if ("Zcf" in ext_components or "D" in ext_components) and "F" not in ext_components:
        ext_components.append("F")  # Add F if Zcf or D is present
    if "Zcd" in ext_components and "D" not in ext_components:
        ext_components.append("D")  # Add D if Zcd is present
    ext_str = ""
    for ext in ext_components:
        if len(ext_str) > 0:
            ext_str += "_"
        ext_str += ext
    march = f"rv{xlen}{ext_str}"
    march = march.replace("zaamo", "a").replace("zalrsc", "a")  # gcc 14 does not accept Zaamo/Zalrsc
    return ext_components, march
