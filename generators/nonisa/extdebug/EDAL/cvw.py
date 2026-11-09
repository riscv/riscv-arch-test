##################################
# EDAL/cvw.py
#
# EDAL for CORE-V Wally: JTAG over the remote_bitbang server in Wally's
# testbench (testbench/common/jtag_rbb.sv, enabled by +RBB_PORT).
#
# The config's run_cmd.txt runs wsim on a base configuration such as rv64gc;
# the EDAL runs the derivative configuration with the Debug Module instead
# (debug64 for rv64gc).  $WALLY must name a cvw tree that has the Debug
# Module and jtag_rbb.
#
# David Harris (David_Harris@hmc.edu) with Claude, 8 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

import os
import shlex
from pathlib import Path

from EDAL import dut
from EDAL.base import EDALError, EDALUnsupported
from EDAL.config import DutConfig
from EDAL.jtag import JtagEDAL

# Base cvw configuration -> derivative configuration with DEBUG_SUPPORTED
DEBUG_CONFIGS = {"rv64gc": "debug64", "rv32gc": "debug32"}

# The first run compiles the simulation, which takes a few minutes.
START_TIMEOUT = 900.0


class CvwEDAL(JtagEDAL):
    """Start wsim on an idle program with +RBB_PORT=0 and connect to Wally's JTAG DTM"""

    name = "cvw"

    def __init__(self, config: DutConfig, args: str = "", timeout: float = START_TIMEOUT) -> None:
        wally = Path(os.environ.get("WALLY", ""))
        if not (wally / "testbench" / "common" / "jtag_rbb.sv").exists():
            raise EDALError(f"$WALLY ({wally}) is not a cvw tree with jtag_rbb.sv; set WALLY to the debug branch")
        command = list(config.command)
        if not command or command[0] != "wsim":
            raise EDALError(f"{config.name}: run_cmd.txt does not start with wsim")
        command[0] = str(wally / "bin" / "wsim")
        base = next((tok for tok in command if tok in DEBUG_CONFIGS), None)
        if base is None:
            raise EDALUnsupported(f"{config.name}: no cvw configuration with the Debug Module")
        command[command.index(base)] = DEBUG_CONFIGS[base]
        if command[-1] != "--elf":
            raise EDALError(f"{config.name}: expected run_cmd.txt to end with --elf")
        elf = config.build_idle_elf()
        command = [*command[:-1], "--args", "+RBB_PORT=0", *shlex.split(args), "--elf", str(elf)]
        self.log = config.extdebug_dir / "wsim.log"
        self.proc = dut.start(config, command, self.log, env={"WALLY": str(wally)})
        try:
            port = dut.wait_for_port(self.proc, self.log, r"remote bitbang connection on port (\d+)", timeout)
            super().__init__(config.xlen, "127.0.0.1", port, timeout=timeout, alive=lambda: self.proc.poll() is None)
        except BaseException:
            dut.stop(self.proc)
            raise

    def close(self) -> None:
        try:
            super().close()
        finally:
            dut.stop(self.proc, timeout=30.0)
