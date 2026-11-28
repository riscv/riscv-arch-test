##################################
# EDAL/whisper.py
#
# Hart-level EDAL for Whisper, which models Sdext but has no Debug Module.
# Whisper runs in interactive mode on the idle program:
#   halt         enter_debug (dcsr.cause = haltreq)
#   resume       exit_debug
#   is_halted    the PC is in the Debug Mode park loop (debug_park_loop)
#   read_reg     peek;  write_reg  poke
# Interactive Whisper executes only when told to: the EDAL first runs the boot
# code up to the idle loop, then advances a running hart RUN_BURST instructions
# each time it checks whether the hart halted.
#
# David Harris (David_Harris@hmc.edu) with Claude, 8 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

import json
import re
import subprocess

from EDAL import dut
from EDAL.base import EDAL, REGNO_CSR, REGNO_FPR, REGNO_GPR, EDALError
from EDAL.config import ACT_ROOT, DutConfig

RUN_BURST = 16
_VALUE_RE = re.compile(r"^(0x[0-9a-fA-F]+)\s*$")


class WhisperEDAL(EDAL):
    """Drive Whisper's interactive mode from the config's run_cmd.txt"""

    name = "WhisperEDAL"

    def __init__(self, config: DutConfig, args: str = "") -> None:
        super().__init__(config.xlen)
        elf = config.build_idle_elf()
        self.park = config.symbol(elf, "extdebug_park")
        extra = config.extdebug_dir / "whisper-extdebug.json"
        extra.write_text(json.dumps({"debug_park_loop": hex(self.park), "debug_trap_address": hex(self.park)}) + "\n")
        command = dut.drop_option(config.command, "--maxinst", takes_value=True)
        if "--config" not in command:
            raise EDALError(f"{config.name}: run_cmd.txt has no --config")
        i = command.index("--config")
        command[i : i + 2] = ["--configfile", f"{command[i + 1]},{extra}"]
        command = [*command, "--interactive", *args.split(), str(elf)]
        self.log = config.extdebug_dir / "whisper.log"
        self.proc = subprocess.Popen(
            command, cwd=ACT_ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        self.logf = self.log.open("w")
        self.logf.write(" ".join(command) + "\n")
        self.halted = False
        # Run the ACT boot code up to the idle loop, where the other DUTs are when a test starts
        self._command(f"until {config.symbol(elf, 'extdebug_idle'):#x}")

    def _command(self, line: str, *, value: bool = False) -> int:
        """Send one interactive command; with value, return the number it prints"""
        assert self.proc.stdin is not None and self.proc.stdout is not None
        # A marker command after each request shows where its output ends.
        self.proc.stdin.write(f"{line}\npeek pc\n")
        self.proc.stdin.flush()
        self.logf.write(f"> {line}\n")
        lines: list[str] = []
        while True:
            out = self.proc.stdout.readline()
            if not out:
                raise EDALError(f"Whisper exited during '{line}'; see {self.log}")
            self.logf.write(out)
            lines.append(out.rstrip())
            if _VALUE_RE.match(out) and (not value or len([x for x in lines if _VALUE_RE.match(x)]) == 2):
                break
        errors = [x for x in lines if x.startswith("Error")]
        if errors:
            raise EDALError(f"Whisper '{line}': {errors[0]}")
        if not value:
            return 0
        m = _VALUE_RE.match(next(x for x in lines if _VALUE_RE.match(x)))
        assert m is not None
        return int(m.group(1), 16)

    def _resource(self, regno: int) -> str:
        if REGNO_CSR <= regno < REGNO_GPR:
            return f"c {regno:#x}"
        if REGNO_GPR <= regno < REGNO_FPR:
            return f"r x{regno - REGNO_GPR}"
        if REGNO_FPR <= regno < REGNO_FPR + 32:
            return f"f f{regno - REGNO_FPR}"
        raise EDALError(f"regno {regno:#x} is not a CSR, GPR, or FPR")

    def halt(self) -> None:
        if not self.halted:
            self._command("enter_debug")
            self.halted = True

    def resume(self) -> None:
        self._command("exit_debug")
        self.halted = False

    def is_halted(self) -> bool:
        if not self.halted:
            self._command(f"step {RUN_BURST}")
            pc = self._command("peek pc", value=True)
            self.halted = self.park <= pc < self.park + 4
        return self.halted

    def read_reg(self, regno: int) -> int:
        return self._command(f"peek {self._resource(regno)}", value=True)

    def write_reg(self, regno: int, value: int) -> None:
        self._command(f"poke {self._resource(regno)} {value:#x}")

    def close(self) -> None:
        if self.proc.poll() is None and self.proc.stdin is not None:
            try:
                self.proc.stdin.write("quit\n")
                self.proc.stdin.close()
            except OSError:
                pass
        dut.stop(self.proc)
        self.logf.close()
