##################################
# priv/pmp/suites/PMPS.py
#
# PMPS: PMP enforcement of supervisor-mode accesses.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPS suite: PMP configured in M mode, then checked from S mode."""

from __future__ import annotations

from testgen.priv.pmp import add_pmp_suite
from testgen.priv.pmp.model import PmpFile
from testgen.priv.pmp.suites._lower_mode import MODES, build_lower_mode_suite


@add_pmp_suite("PMPS")
def build() -> list[PmpFile]:
    return build_lower_mode_suite(MODES["S"])
