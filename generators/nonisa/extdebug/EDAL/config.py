##################################
# EDAL/config.py
#
# Use an ACT DUT configuration (config/**/test_config.yaml and run_cmd.txt):
# start the DUT with its run_cmd.txt, and build the program its hart runs
# with ACT's boot code, its rvmodel_macros.h, and its linker script.
#
# David Harris (David_Harris@hmc.edu) with Claude, 8 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from act.config import Config, load_config
from act.parse_udb_config import prepare_dut_outputs
from act.toolchain import Toolchain

from EDAL.base import EDALError

ACT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROOT = ACT_ROOT / "config"
WORK_ROOT = ACT_ROOT / "work"
TESTS_ENV = ACT_ROOT / "tests" / "env"

_DEBUG_PLACEHOLDER_RE = re.compile(r"\{debug:[^}]*\}")

# The hart spins in this loop while the debugger works through the DM.
IDLE_SOURCE = """\
// Idle program for External Debug tests: ACT boot code, then spin.
#define SIGUPD_COUNT 0
#include "riscv_arch_test.h"

RVTEST_BEGIN
extdebug_idle:
  j extdebug_idle

// Debug Mode park loop, for EDALs whose DUT runs Debug Mode code from memory
// (Whisper's debug_park_loop and debug_trap_address)
  .globl extdebug_park
extdebug_park:
  j extdebug_park

// Never reached; these emit the boot, trap-handler, and RVMODEL support code and data
RVTEST_CODE_END
RVTEST_DATA_BEGIN
RVTEST_DATA_END
RVTEST_SIG_SETUP
"""


@dataclass
class DutConfig:
    """One ACT configuration directory, e.g. config/spike/spike-rv64-max"""

    dir: Path
    act: Config
    xlen: int
    env: dict[str, str] = field(default_factory=dict)  # leading KEY=VALUE assignments in run_cmd.txt
    command: list[str] = field(default_factory=list)  # run_cmd.txt without {debug:...}; the ELF goes last

    @property
    def name(self) -> str:
        return self.act.name

    @property
    def simulator(self) -> str:
        """The DUT family, which selects the EDAL: spike, whisper, imperas, or the core vendor (cvw)"""
        parts = self.dir.relative_to(CONFIG_ROOT).parts
        return parts[1] if parts[0] == "cores" else parts[0]

    @property
    def workdir(self) -> Path:
        return WORK_ROOT / self.name

    @property
    def extdebug_dir(self) -> Path:
        return self.workdir / "extdebug"

    @classmethod
    def load(cls, config_dir: Path) -> DutConfig:
        config_dir = config_dir.resolve()
        act = load_config(config_dir / "test_config.yaml")
        m = re.search(r"^\s*MXLEN:\s*(\d+)", act.udb_config.read_text(), re.MULTILINE)
        if not m:
            raise EDALError(f"cannot find MXLEN in {act.udb_config}")
        tokens = shlex.split(_DEBUG_PLACEHOLDER_RE.sub("", (config_dir / "run_cmd.txt").read_text()))
        env = {}
        while tokens and "=" in tokens[0] and not tokens[0].startswith("-"):
            key, _, value = tokens.pop(0).partition("=")
            env[key] = value
        return cls(dir=config_dir, act=act, xlen=int(m.group(1)), env=env, command=tokens)

    def build_idle_elf(self) -> Path:
        """Build the idle program the way ACT builds a self-checking test without a signature"""
        prepare_dut_outputs([self.act], WORK_ROOT, jobs=1, verbose=False)  # rvtest_config.h; no-op when current
        out = self.extdebug_dir
        out.mkdir(parents=True, exist_ok=True)
        src = out / "idle.S"
        elf = out / "idle.elf"
        src.write_text(IDLE_SOURCE)
        toolchain = Toolchain(self.act.compiler_exe, self.act.compiler_type)
        cmd = [
            *toolchain.compile_prefix(self.xlen),
            f"-I{self.act.dut_include_dir.absolute()}",
            f"-T{self.act.linker_script.absolute()}",
            "-O0",
            "-g",
            "-mcmodel=medany",
            "-nostdlib",
            f"-I{TESTS_ENV}",
            f"-I{self.workdir / 'env'}",
            "-Wl,--defsym=__stack_size=128",
            "-o",
            str(elf),
            *toolchain.march_flags(self.xlen, f"rv{self.xlen}i_zicsr_zifencei", assembly=True),
            f"-mabi={'i' if self.xlen == 32 else ''}lp{self.xlen}",
            "-DRVTEST_SELFCHECK",
            "-DRVTEST_NOSIG",
            f"-DXLEN={self.xlen}",
            "-DTEST_FLEN=0",
            '-DTEST_FILE="idle.S"',
            str(src),
        ]
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            raise EDALError(f"building {elf} failed:\n{shlex.join(cmd)}\n{result.stderr}")
        return elf

    def symbol(self, elf: Path, name: str) -> int:
        """Address of symbol name in elf"""
        nm = Path(str(self.act.compiler_exe).replace("gcc", "nm").replace("clang", "llvm-nm"))
        result = subprocess.run([str(nm), str(elf)], check=False, capture_output=True, text=True)
        for line in result.stdout.splitlines():
            fields = line.split()
            if len(fields) == 3 and fields[2] == name:
                return int(fields[0], 16)
        raise EDALError(f"{elf} has no symbol {name}")


def find_configs(selector: str) -> list[DutConfig]:
    """Resolve a config path or a name, like the Makefile run targets.

    A name selects every config with a run_cmd.txt that has the name as a directory
    in its path: 'spike-rv64-max' selects one config, 'spike' every Spike config,
    'cvw' every cvw config.
    """
    path = Path(selector)
    if path.is_file():
        path = path.parent
    if path.is_dir() and (path / "run_cmd.txt").exists():
        return [DutConfig.load(path)]
    matches = sorted(
        f.parent for f in CONFIG_ROOT.rglob("run_cmd.txt") if selector in f.parent.relative_to(CONFIG_ROOT).parts
    )
    if not matches:
        raise EDALError(f"no ACT config with a run_cmd.txt matches {selector!r}")
    return [DutConfig.load(d) for d in matches]
