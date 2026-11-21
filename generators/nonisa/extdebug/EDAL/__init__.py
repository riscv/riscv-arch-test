##################################
# EDAL/__init__.py
#
# External Debug Abstraction Layer (EDAL)
#
# An EDAL connects the External Debug tests to one DUT, at two levels:
#   DMI level (Debug Module tests):  dmi_read, dmi_write
#   Hart level (Sdext tests):        halt, resume, step, is_halted, read_reg, write_reg
# Tests call the module-level functions below, which use the active EDAL.
# A DUT with no Debug Module has only the hart level; its DMI functions raise
# EDALUnsupported, and the runner reports such tests as SKIP.
#
# David Harris (David_Harris@hmc.edu) with Claude, 8 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

import importlib

from EDAL.base import DMIEDAL, EDAL, EDALError, EDALUnsupported
from EDAL.config import DutConfig, find_configs

__all__ = [
    "DMIEDAL",
    "EDAL",
    "EDALS",
    "DutConfig",
    "EDALError",
    "EDALUnsupported",
    "dmi_read",
    "dmi_write",
    "find_configs",
    "halt",
    "is_halted",
    "open_edal",
    "read_reg",
    "resume",
    "set_active",
    "step",
    "write_reg",
]

# Simulator family (config/<family>/... or config/cores/<family>/...) -> "module:class" implementing its EDAL
EDALS = {
    "spike": "EDAL.spike:SpikeEDAL",
    "cvw": "EDAL.cvw:CvwEDAL",
    "whisper": "EDAL.whisper:WhisperEDAL",
    "imperas": "EDAL.imperas:ImperasEDAL",
}

_active: EDAL | None = None


def open_edal(config: DutConfig, **options: str) -> EDAL:
    """Start the DUT described by an ACT config and return its EDAL"""
    if config.simulator not in EDALS:
        raise EDALUnsupported(f"no EDAL for {config.name} ({config.simulator}); EDALs exist for {', '.join(EDALS)}")
    module_name, class_name = EDALS[config.simulator].split(":")
    cls = getattr(importlib.import_module(module_name), class_name)
    return cls(config, **options)


def set_active(edal: EDAL | None) -> None:
    """Route the module-level functions to edal"""
    global _active
    _active = edal


def _require_active() -> EDAL:
    if _active is None:
        raise EDALError("no active EDAL; run the tests with run_dm_tests.py")
    return _active


# DMI level
def dmi_read(addr: int) -> int:
    """Read the DM register at DMI address addr"""
    return _require_active().dmi_read(addr)


def dmi_write(addr: int, data: int) -> None:
    """Write data to the DM register at DMI address addr"""
    _require_active().dmi_write(addr, data)


# Hart level
def halt() -> None:
    _require_active().halt()


def resume() -> None:
    _require_active().resume()


def step() -> None:
    _require_active().step()


def is_halted() -> bool:
    return _require_active().is_halted()


def read_reg(regno: int) -> int:
    return _require_active().read_reg(regno)


def write_reg(regno: int, value: int) -> None:
    _require_active().write_reg(regno, value)
