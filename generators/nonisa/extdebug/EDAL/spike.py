##################################
# EDAL/spike.py
#
# EDAL for Spike: JTAG over Spike's remote_bitbang port (--rbb-port)
#
# David Harris (David_Harris@hmc.edu) with Claude, 8 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

import shlex

from EDAL import dut
from EDAL.config import DutConfig
from EDAL.jtag import JtagEDAL


class SpikeEDAL(JtagEDAL):
    """Start Spike from the config's run_cmd.txt on an idle program and connect to its JTAG DTM"""

    name = "spike"

    def __init__(self, config: DutConfig, args: str = "", timeout: float = 30.0) -> None:
        elf = config.build_idle_elf()
        # The hart idles until the test ends, so drop the instruction limit.
        command = dut.drop_option(config.command, "--instructions", takes_value=True)
        command = [*command, "--rbb-port=0", *shlex.split(args), str(elf)]
        self.log = config.extdebug_dir / "spike.log"
        self.proc = dut.start(config, command, self.log)
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
            dut.stop(self.proc)
