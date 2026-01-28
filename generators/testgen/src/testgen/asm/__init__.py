# testgen/asm/__init__.py
"""Assembly code generation helpers."""

from testgen.asm.csr import (
    csr_access_test,
    csr_walk_test,
    gen_csr_read_sigupd,
    gen_csr_write_sigupd,
)
from testgen.asm.helpers import (
    comment_banner,
    load_float_reg,
    load_int_reg,
    reproducible_hash,
    return_test_regs,
    to_hex,
    write_sigupd,
)
from testgen.asm.sections import generate_test_data_section, generate_test_string_section

__all__ = [
    "comment_banner",
    "csr_access_test",
    "csr_walk_test",
    "gen_csr_read_sigupd",
    "gen_csr_write_sigupd",
    "generate_test_data_section",
    "generate_test_string_section",
    "load_float_reg",
    "load_int_reg",
    "reproducible_hash",
    "return_test_regs",
    "to_hex",
    "write_sigupd",
]
