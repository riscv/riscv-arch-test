##################################
# EDAL/dut.py
#
# Helpers to start and stop a DUT process
#
# David Harris (David_Harris@hmc.edu) with Claude, 8 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from EDAL.base import EDALError
from EDAL.config import ACT_ROOT, DutConfig


def start(config: DutConfig, command: list[str], log: Path, env: dict[str, str] | None = None) -> subprocess.Popen:
    """Start command in the ACT root (run_cmd.txt paths are relative to it), with the config's environment"""
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as f:
        f.write(" ".join(command) + "\n")
        f.flush()
        return subprocess.Popen(
            command,
            cwd=ACT_ROOT,
            env={**os.environ, **config.env, **(env or {})},
            stdout=f,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
        )


def drop_option(command: list[str], option: str, takes_value: bool) -> list[str]:
    """Remove option (as 'option value', or 'option=value') from command"""
    out: list[str] = []
    skip = False
    for tok in command:
        if skip:
            skip = False
        elif tok == option:
            skip = takes_value
        elif not tok.startswith(option + "="):
            out.append(tok)
    return out


def wait_for_port(proc: subprocess.Popen, log: Path, pattern: str, timeout: float) -> int:
    """Wait until log contains pattern (a regex with one integer group) and return that integer"""
    deadline = time.monotonic() + timeout
    regex = re.compile(pattern)
    while time.monotonic() < deadline:
        m = regex.search(log.read_text(errors="replace")) if log.exists() else None
        if m:
            return int(m.group(1))
        if proc.poll() is not None:
            raise EDALError(f"DUT exited with status {proc.returncode} before opening its debug port; see {log}")
        time.sleep(0.05)
    raise EDALError(f"DUT did not open its debug port within {timeout} s; see {log}")


def stop(proc: subprocess.Popen | None, timeout: float = 5.0) -> None:
    """Stop a DUT process, killing it if it does not exit"""
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
