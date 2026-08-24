##################################
# priv/sv/macros.py
#
# Verbatim assembly building blocks for the Sv* virtual-memory suite generators.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Loader for the verbatim assembly blocks shared by the generated Sv* suites.

The blocks live as individual files in ``sv_templates/``. They are byte-for-byte
copies of the local ``.macro`` blocks and data regions of the original
hand-written suites: keeping them verbatim (rather than re-deriving the address
arithmetic in Python) guarantees the generated tests exercise exactly the same
instruction sequences that the architectural coverage was written against.
"""

from __future__ import annotations

from pathlib import Path

_TEMPLATE_DIR = Path(__file__).parent / "sv_templates"

# Horizontal rule used throughout the original files
HR = "//" + "-" * 129


def template(name: str) -> str:
    """Return the contents of ``sv_templates/<name>.S`` verbatim."""
    return (_TEMPLATE_DIR / f"{name}.S").read_text()


# RWX access battery (store/load/execute via a5) and the standard runners
RWX_VERIFICATION = template("rwx_verification")
RWX_RUNNER_RV64 = template("rwx_runner_rv64")
RWX_RUNNER_RV32 = template("rwx_runner_rv32")

# The physical test region the RWX battery stores to, loads from, and jumps into
DATA_REGION = template("data_region")
