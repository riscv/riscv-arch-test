##################################
# priv/pmp/suites/PMPSm.py
#
# PMPSm: machine-mode PMP configuration and enforcement.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPSm suite: pmpcfg/pmpaddr WARL behaviour and M-mode PMP enforcement."""

from __future__ import annotations

from testgen.priv.pmp import add_pmp_suite
from testgen.priv.pmp.model import PmpFile
from testgen.priv.pmp.suites._pmpsm_cfg import build_cfg_files
from testgen.priv.pmp.suites._pmpsm_misc import build_misc_files
from testgen.priv.pmp.suites._pmpsm_walk import build_walk_files


@add_pmp_suite("PMPSm")
def build() -> list[PmpFile]:
    """All generated PMPSm files."""
    return [*build_walk_files(), *build_cfg_files(), *build_misc_files()]
