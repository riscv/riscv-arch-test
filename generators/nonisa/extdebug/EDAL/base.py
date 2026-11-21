##################################
# EDAL/base.py
#
# The two levels of the External Debug Abstraction Layer (EDAL):
#   EDAL     hart level, used by Sdext tests: halt, resume, step, and
#            register access with Access Register numbering.
#   DMIEDAL  DMI level, used by Debug Module tests: dmi_read and dmi_write.
#            It implements the hart level through the Debug Module, so the
#            same Sdext test runs through a real DM on DUTs that have one.
# A DUT without a Debug Module implements only the hart level.
#
# David Harris (David_Harris@hmc.edu) with Claude, 8 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing_extensions import Self

# Access Register regno ranges (Debug Spec table 3.3)
REGNO_CSR = 0x0000
REGNO_GPR = 0x1000
REGNO_FPR = 0x1020
CSR_DCSR = 0x7B0
CSR_DPC = 0x7B1
DCSR_STEP = 1 << 2

# DM registers and fields used here (the same values as DM_regs.py)
DATA0 = 0x04
DATA1 = 0x05
DMCONTROL = 0x10
DMSTATUS = 0x11
ABSTRACTCS = 0x16
COMMAND = 0x17
DMCONTROL_HALTREQ = 1 << 31
DMCONTROL_RESUMEREQ = 1 << 30
DMCONTROL_DMACTIVE = 1 << 0
DMSTATUS_ALLRESUMEACK = 1 << 17
DMSTATUS_ALLHALTED = 1 << 9
ABSTRACTCS_BUSY = 1 << 12
ABSTRACTCS_CMDERR_SHIFT = 8
COMMAND_AARSIZE_SHIFT = 20
COMMAND_TRANSFER = 1 << 17
COMMAND_WRITE = 1 << 16

POLL_LIMIT = 1000


class EDALError(Exception):
    """The EDAL could not complete an access or control the DUT"""


class EDALUnsupported(EDALError):
    """The DUT's EDAL does not provide this level, e.g. DMI access on a DUT with no Debug Module"""


class EDAL(ABC):
    """Hart-level debug control of one DUT"""

    name = "EDAL"

    def __init__(self, xlen: int) -> None:
        self.xlen = xlen

    @abstractmethod
    def halt(self) -> None:
        """Halt the hart (enter Debug Mode with cause haltreq)"""

    @abstractmethod
    def resume(self) -> None:
        """Resume the hart (leave Debug Mode at dpc)"""

    @abstractmethod
    def is_halted(self) -> bool:
        """True if the hart is in Debug Mode"""

    @abstractmethod
    def read_reg(self, regno: int) -> int:
        """Read a register by Access Register regno (CSR 0x0000-0x0fff, GPR 0x1000+, FPR 0x1020+)"""

    @abstractmethod
    def write_reg(self, regno: int, value: int) -> None:
        """Write a register by Access Register regno"""

    @abstractmethod
    def close(self) -> None:
        """Disconnect and stop the DUT"""

    def step(self) -> None:
        """Execute one instruction with dcsr.step set and halt again"""
        dcsr = self.read_reg(CSR_DCSR)
        self.write_reg(CSR_DCSR, dcsr | DCSR_STEP)
        self.resume()
        self.wait_halted()
        self.write_reg(CSR_DCSR, self.read_reg(CSR_DCSR) & ~DCSR_STEP)

    def wait_halted(self) -> None:
        for _ in range(POLL_LIMIT):
            if self.is_halted():
                return
        raise EDALError(f"hart did not halt after {POLL_LIMIT} polls")

    def dmi_read(self, addr: int) -> int:
        raise EDALUnsupported(f"{self.name} has no Debug Module Interface")

    def dmi_write(self, addr: int, data: int) -> None:
        raise EDALUnsupported(f"{self.name} has no Debug Module Interface")

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class DMIEDAL(EDAL):
    """A DUT with a Debug Module: DMI access, and hart control through the DM (hart 0)"""

    name = "DMIEDAL"

    @abstractmethod
    def dmi_read(self, addr: int) -> int:
        """Return the 32-bit DM register at DMI address addr"""

    @abstractmethod
    def dmi_write(self, addr: int, data: int) -> None:
        """Write 32-bit data to the DM register at DMI address addr"""

    def _poll(self, addr: int, mask: int, want: int, what: str) -> int:
        for _ in range(POLL_LIMIT):
            value = self.dmi_read(addr)
            if value & mask == want:
                return value
        raise EDALError(f"timed out waiting for {what}")

    def activate(self) -> None:
        """Make sure the DM is active"""
        if not self.dmi_read(DMCONTROL) & DMCONTROL_DMACTIVE:
            self.dmi_write(DMCONTROL, DMCONTROL_DMACTIVE)
            self._poll(DMCONTROL, DMCONTROL_DMACTIVE, DMCONTROL_DMACTIVE, "dmcontrol.dmactive")

    def halt(self) -> None:
        self.activate()
        self.dmi_write(DMCONTROL, DMCONTROL_HALTREQ | DMCONTROL_DMACTIVE)
        self._poll(DMSTATUS, DMSTATUS_ALLHALTED, DMSTATUS_ALLHALTED, "dmstatus.allhalted")
        self.dmi_write(DMCONTROL, DMCONTROL_DMACTIVE)

    def resume(self) -> None:
        self.activate()
        self.dmi_write(DMCONTROL, DMCONTROL_RESUMEREQ | DMCONTROL_DMACTIVE)
        self._poll(DMSTATUS, DMSTATUS_ALLRESUMEACK, DMSTATUS_ALLRESUMEACK, "dmstatus.allresumeack")

    def is_halted(self) -> bool:
        return bool(self.dmi_read(DMSTATUS) & DMSTATUS_ALLHALTED)

    def _access_register(self, regno: int, write: bool) -> None:
        aarsize = 3 if self.xlen == 64 else 2
        command = (aarsize << COMMAND_AARSIZE_SHIFT) | COMMAND_TRANSFER | (COMMAND_WRITE if write else 0) | regno
        self.dmi_write(COMMAND, command)
        abstractcs = self._poll(ABSTRACTCS, ABSTRACTCS_BUSY, 0, "abstractcs.busy to clear")
        cmderr = (abstractcs >> ABSTRACTCS_CMDERR_SHIFT) & 7
        if cmderr:
            self.dmi_write(ABSTRACTCS, 7 << ABSTRACTCS_CMDERR_SHIFT)  # cmderr is W1C
            raise EDALError(f"Access Register {'write' if write else 'read'} of regno {regno:#x}: cmderr = {cmderr}")

    def read_reg(self, regno: int) -> int:
        self._access_register(regno, write=False)
        value = self.dmi_read(DATA0)
        if self.xlen == 64:
            value |= self.dmi_read(DATA1) << 32
        return value

    def write_reg(self, regno: int, value: int) -> None:
        self.dmi_write(DATA0, value & 0xFFFFFFFF)
        if self.xlen == 64:
            self.dmi_write(DATA1, (value >> 32) & 0xFFFFFFFF)
        self._access_register(regno, write=True)
