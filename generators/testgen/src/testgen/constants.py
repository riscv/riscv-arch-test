##################################
# constants.py
#
# Package-wide constants for testgen.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Package-wide constants for testgen."""

# =============================================================================
# Test Generation Configuration
# =============================================================================

# Max testcases per file before splitting. Individual coverpoints won't be split,
# so if one coverpoint exceeds this, the file will exceed this limit.
# TODO: Currently only applies to unpriv tests. Should this apply to priv tests too?
TESTCASES_PER_FILE = 1000

# =============================================================================
# Extension Configuration
# =============================================================================

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

# Extensions that require config-dependent test generation and cannot use common directory.
# Applies to tests that use preprocessor conditionals based on the DUT configuration.
# Only unpriv extensions are listed here; privileged tests are always config-dependent.
CONFIG_DEPENDENT_EXTENSIONS = frozenset(
    {
        "Zicntr",  # Depends on TIME_CSR_IMPLEMENTED
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

# Extensions requiring 128-bit FLEN (Q extension)
FLEN_128_EXTENSIONS = frozenset(
    {
        "Q",
        "ZfaQ",
        "ZfhQ",
    }
)

# Extensions requiring 64-bit FLEN (D extension)
FLEN_64_EXTENSIONS = frozenset(
    {
        "D",
        "ZfhD",
        "ZfhminD",
        "ZfaD",
        "ZfaZfhD",
        "Zcd",
    }
)

# All other extensions default to 32-bit FLEN


def get_flen_for_extension(extension: str) -> int:
    """Get the required FLEN for a given extension.

    Args:
        extension: The extension name (e.g., 'F', 'D', 'Q')

    Returns:
        The FLEN value (32, 64, or 128)
    """
    if extension in FLEN_128_EXTENSIONS:
        return 128
    if extension in FLEN_64_EXTENSIONS:
        return 64
    return 32


# =============================================================================
# Coverpoint Configuration
# =============================================================================

# Coverpoints that don't need dedicated test generation
# (they are already covered by other tests)
SKIP_COVERPOINTS = frozenset(
    {
        # Hazard coverpoints - covered implicitly by register usage patterns
        "cp_gpr_hazard_rw",
        "cp_gpr_hazard_w",
        "cp_gpr_hazard_r",
        # Sign coverpoints - already covered by edge tests
        "cp_rd_sign",
        # Equal value comparisons - already covered by cr_rs1_rs2_edges
        "cmp_rd_rs1_eqval",
        "cmp_rd_rs2_eqval",
        # FP flags - covered by edge tests
        "cp_csr_fflags_n",
        "cp_csr_fflags_on",
        "cp_csr_fflags_v",
        "cp_csr_fflags_vd",
        "cp_csr_fflags_vdon",
        "cp_csr_fflags_vdoun",
        "cp_csr_fflags_vn",
        "cp_csr_fflags_von",
        "cp_csr_fflags_voun",
        "cp_csr_fflags_vun",
        # FP classification - covered elsewhere
        "cp_fclass",
    }
)
