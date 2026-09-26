##################################
# constants.py
#
# Package-wide constants for testgen.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Package-wide constants for testgen."""

# Assembly indentations
INDENT = "  "


def indent_asm(line: str) -> str:
    """Add INDENT to an assembly line unless it's already indented, a label, comment, or preprocessor directive."""
    if not line or line[0] in (" ", "\t", "#", "\n", "/"):
        return line
    colon_pos = line.find(":")
    if colon_pos > 0 and all(c.isalnum() or c == "_" for c in line[:colon_pos]):
        return line
    return f"{INDENT}{line}"


# =============================================================================
# Test Generation Configuration
# =============================================================================

# Max testcases per test file before splitting into multiple files. Individual test
# chunks won't be split, so if one test chunk exceeds this, the file will exceed this limit.
TESTCASES_PER_FILE = 1000
TESTCASES_PER_PRIV_FILE = 512

# =============================================================================
# Extension Configuration
# =============================================================================

EXPERIMENTAL_EXTENSIONS = frozenset({})

# Extensions that should generate RV32E/RV64E variants
# TODO: Add Zcmp and Zcmt when implemented
E_EXTENSION_TESTS = frozenset(
    {
        "I",
        "M",
        "Zmmul",
        "Zca",
        "Zcb",
        "Zba",
        "Zbb",
        "Zbs",
    }
)

# Testplan to param mapping. These names are removed from the extension list and the corresponding
# parameter is added to the @PARAMS@ field in the header of the generated test along with the required value.
EXTENSION_PARAM_MAP = {
    "Misalign": "MISALIGNED_LDST: true",
}

# =============================================================================
# FLEN Mapping
# =============================================================================


def get_flen_for_extensions(extensions: list[str]) -> int:
    """Get the required FLEN for canonical extension components."""
    if "Q" in extensions:
        return 128
    if "D" in extensions:
        return 64
    return 32


# =============================================================================
# Coverpoint Configuration
# =============================================================================

# Coverpoints that don't need dedicated test generation
# (they are already covered by other tests)
SKIP_COVERPOINTS = frozenset(
    {
        # FP classification - covered elsewhere
        "cp_fclass",
    }
)

# =============================================================================
# Vector Configuration
# =============================================================================
MIN_SEW_MIN = 8
ELEN_MAX = 64
VLEN_MAX = 1024
