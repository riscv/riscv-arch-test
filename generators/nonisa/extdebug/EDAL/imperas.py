##################################
# EDAL/imperas.py
#
# EDAL for the Imperas RISC-V model.  The model implements Sdext (dcsr, dpc,
# dret, step, ebreak and trigger entry) but no Debug Module: its documentation
# leaves the DM to the simulation harness, through the OP API (the haltreq and
# resethaltreq nets, opProcessorRegRead/Write, DMStall).  iss.exe offers only
# gdb RSP and MPD Tcl, whose halt stops the simulator rather than entering
# Debug Mode.  A hart-level EDAL therefore needs a small OP API harness that
# serves halt, resume, and register access over a socket; until it exists,
# every Imperas test reports SKIP.
#
# David Harris (David_Harris@hmc.edu) with Claude, 8 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

from EDAL.base import EDALUnsupported
from EDAL.config import DutConfig


class ImperasEDAL:
    """Placeholder: reports that the Imperas EDAL needs an OP API harness"""

    def __init__(self, config: DutConfig, args: str = "") -> None:
        raise EDALUnsupported(f"{config.name}: the Imperas EDAL needs an OP API harness (not written yet)")
