##################################
# priv/pmp/suites/PMPU.py
#
# PMPU: PMP enforcement of user-mode accesses.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPU suite: PMP configured in M mode, then checked from U mode."""

from __future__ import annotations

from testgen.priv.pmp import add_pmp_suite
from testgen.priv.pmp.model import PmpFile
from testgen.priv.pmp.suites._lower_mode import MODES, build_lower_mode_suite


@add_pmp_suite("PMPU")
def build() -> list[PmpFile]:
    return build_lower_mode_suite(MODES["U"])
