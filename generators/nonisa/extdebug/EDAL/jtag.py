##################################
# EDAL/jtag.py
#
# JTAG Debug Transport Module (DTM) access over the remote_bitbang protocol.
# Spike (--rbb-port) and OpenOCD's remote_bitbang driver use this protocol;
# any DUT that serves it can use JtagEDAL.
#
# David Harris (David_Harris@hmc.edu) with Claude, 8 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

import contextlib
import socket
import time
from collections.abc import Callable

from EDAL.base import DMIEDAL, EDALError

# JTAG DTM instructions (Debug Spec section 6.1.2)
IR_IDCODE = 0x01
IR_DTMCS = 0x10
IR_DMI = 0x11
IR_BYPASS = 0x1F

# dtmcs fields
DTMCS_DMIRESET = 1 << 16
DTMCS_DMIHARDRESET = 1 << 17

# DMI op values: requests and responses
DMI_OP_NOP = 0
DMI_OP_READ = 1
DMI_OP_WRITE = 2
DMI_OP_FAILED = 2
DMI_OP_BUSY = 3

MAX_BUSY_RETRIES = 100


class RemoteBitbang:
    """Client for the remote_bitbang protocol: one ASCII character per pin change"""

    def __init__(self, host: str, port: int, timeout: float = 30.0, alive: Callable[[], bool] = lambda: True) -> None:
        """Connect to host:port, retrying until timeout while alive() reports the server process running"""
        deadline = time.monotonic() + timeout
        while True:
            try:
                self.sock = socket.create_connection((host, port), timeout=timeout)
                break
            except ConnectionRefusedError:
                if not alive():
                    raise EDALError(f"DUT exited before accepting a connection on {host}:{port}") from None
                if time.monotonic() > deadline:
                    raise EDALError(f"no remote_bitbang server on {host}:{port}") from None
                time.sleep(0.05)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def clock(self, bits: list[tuple[int, int, bool]]) -> list[int]:
        """Apply one TCK cycle per (tms, tdi, sample) entry.

        Each cycle drives TCK low, samples TDO if requested, then drives TCK high.
        Returns the sampled TDO bits in order.
        """
        out = bytearray()
        nsamples = 0
        for tms, tdi, sample in bits:
            out += b"%d" % ((tms << 1) | tdi)
            if sample:
                out += b"R"
                nsamples += 1
            out += b"%d" % (4 | (tms << 1) | tdi)
        self.sock.sendall(out)
        resp = bytearray()
        while len(resp) < nsamples:
            chunk = self.sock.recv(nsamples - len(resp))
            if not chunk:
                raise EDALError("remote_bitbang connection closed")
            resp += chunk
        return [b - ord("0") for b in resp]

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self.sock.sendall(b"Q")
        self.sock.close()


class JtagTap:
    """JTAG TAP controller driver.  Every scan starts and ends in Run-Test/Idle."""

    def __init__(self, cable: RemoteBitbang, ir_length: int = 5) -> None:
        self.cable = cable
        self.ir_length = ir_length
        self.reset()

    def reset(self) -> None:
        """Go to Test-Logic-Reset with TMS high, then to Run-Test/Idle"""
        self.cable.clock([(1, 0, False)] * 6 + [(0, 0, False)])

    def idle(self, cycles: int) -> None:
        """Stay in Run-Test/Idle for cycles TCK cycles"""
        if cycles > 0:
            self.cable.clock([(0, 0, False)] * cycles)

    def _scan(self, head: list[int], value: int, length: int) -> int:
        bits = [(tms, 0, False) for tms in head]  # Run-Test/Idle -> Shift-xR
        for i in range(length):
            last = i == length - 1
            bits.append((int(last), (value >> i) & 1, True))  # last bit moves to Exit1-xR
        bits += [(1, 0, False), (0, 0, False)]  # Update-xR, Run-Test/Idle
        tdo = self.cable.clock(bits)
        return sum(bit << i for i, bit in enumerate(tdo))

    def scan_ir(self, value: int) -> int:
        """Shift value into IR; return the captured IR bits"""
        return self._scan([1, 1, 0, 0], value, self.ir_length)

    def scan_dr(self, value: int, length: int) -> int:
        """Shift value into the selected DR; return the captured DR bits"""
        return self._scan([1, 0, 0], value, length)


class JtagDtm:
    """JTAG DTM: dtmcs and DMI access (Debug Spec chapter 6)"""

    def __init__(self, tap: JtagTap) -> None:
        self.tap = tap
        self.ir: int | None = None
        dtmcs = self.read_dtmcs()
        version = dtmcs & 0xF
        if version != 1:
            raise EDALError(f"dtmcs.version = {version}; expected 1 (Debug Spec 0.13/1.0). dtmcs = {dtmcs:#010x}")
        self.abits = (dtmcs >> 4) & 0x3F
        self.idle_cycles = (dtmcs >> 12) & 0x7

    def _select(self, ir: int) -> None:
        if self.ir != ir:
            self.tap.scan_ir(ir)
            self.ir = ir

    def idcode(self) -> int:
        self._select(IR_IDCODE)
        return self.tap.scan_dr(0, 32)

    def read_dtmcs(self) -> int:
        self._select(IR_DTMCS)
        return self.tap.scan_dr(0, 32)

    def write_dtmcs(self, value: int) -> None:
        self._select(IR_DTMCS)
        self.tap.scan_dr(value, 32)

    def _dmi_scan(self, op: int, addr: int, data: int) -> tuple[int, int]:
        self._select(IR_DMI)
        width = self.abits + 34
        r = self.tap.scan_dr((addr << 34) | ((data & 0xFFFFFFFF) << 2) | op, width)
        self.tap.idle(self.idle_cycles)
        return r & 3, (r >> 2) & 0xFFFFFFFF

    def _dmi_access(self, op: int, addr: int, data: int) -> int:
        for _ in range(MAX_BUSY_RETRIES):
            self._dmi_scan(op, addr, data)
            status, result = self._dmi_scan(DMI_OP_NOP, 0, 0)
            if status == 0:
                return result
            if status == DMI_OP_FAILED:
                self.write_dtmcs(DTMCS_DMIRESET)
                raise EDALError(f"DMI {'read' if op == DMI_OP_READ else 'write'} of {addr:#x} failed (op = 2)")
            # Busy: clear the sticky error, wait longer between scans, and retry
            self.write_dtmcs(DTMCS_DMIRESET)
            self.idle_cycles += 1
        raise EDALError(f"DMI access to {addr:#x} still busy after {MAX_BUSY_RETRIES} retries")

    def dmi_read(self, addr: int) -> int:
        return self._dmi_access(DMI_OP_READ, addr, 0)

    def dmi_write(self, addr: int, data: int) -> None:
        self._dmi_access(DMI_OP_WRITE, addr, data)


class JtagEDAL(DMIEDAL):
    """EDAL for a DUT that serves remote_bitbang JTAG on host:port"""

    name = "JtagEDAL"

    def __init__(
        self,
        xlen: int,
        host: str,
        port: int,
        ir_length: int = 5,
        timeout: float = 30.0,
        alive: Callable[[], bool] = lambda: True,
    ) -> None:
        super().__init__(xlen)
        self.cable = RemoteBitbang(host, port, timeout, alive)
        self.dtm = JtagDtm(JtagTap(self.cable, ir_length))

    def dmi_read(self, addr: int) -> int:
        return self.dtm.dmi_read(addr)

    def dmi_write(self, addr: int, data: int) -> None:
        self.dtm.dmi_write(addr, data)

    def close(self) -> None:
        self.cable.close()
