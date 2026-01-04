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
from pathlib import Path

from testgen.data.test_config import TestConfig


def insert_setup_template(template_name: str, test_config: TestConfig, test_file: Path, extra_defines: str) -> str:
    """Insert a header/footer template file into the test file."""
    xlen = test_config.xlen
    extension = test_config.extension
    E_ext = test_config.E_ext
    ext_components, march = canonicalize_extension(extension, xlen, E_ext)
    with importlib.resources.open_text("testgen.templates", template_name) as template_file:
        template = template_file.read()
    # Replace placeholders
    template = (
        template.replace("@TEST_PATH@", f"{test_file}")
        .replace("@TEST_FILE_NAME@", f"{test_file.name}")
        .replace("@EXTENSION_LIST@", f"{ext_components}")
        .replace("@MARCH@", march.lower())
        .replace("@XLEN@", str(xlen))
        .replace("@EXTRA_DEFINES@", extra_defines)
        .replace("@CONFIG_DEPENDENT@", "false")  # TODO: Make this configurable for some tests (e.g. Zimop)
    )
    return template


def canonicalize_extension(extension: str, xlen: int, E_ext: bool) -> tuple[list[str], str]:
    """Canonicalize extension string."""
    ext_components = re.findall(r"[A-Z][a-z]*", extension)
    if "I" not in ext_components and "E" not in ext_components:
        # Always include base integer extension
        if E_ext:
            ext_components.insert(0, "E")
        else:
            ext_components.insert(0, "I")
    if ("Zcf" in ext_components or "D" in ext_components) and "F" not in ext_components:
        ext_components.append("F")  # Add F if Zcf or D is present
    if "Zcd" in ext_components and "D" not in ext_components:
        ext_components.append("D")  # Add D if Zcd is present
    if "Misalign" in ext_components:
        ext_components.remove("Misalign")
    ext_str = ""
    for ext in ext_components:
        if len(ext_str) > 0:
            ext_str += "_"
        ext_str += ext
    march = f"rv{xlen}{ext_str}"
    march = march.replace("Zaamo", "A").replace("Zalrsc", "A")  # gcc 14 does not accept Zaamo/Zalrsc
    return ext_components, march
