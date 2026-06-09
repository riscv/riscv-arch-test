##################################
# config.py
#
# jcarlin@hmc.edu 8 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Parse test framework configuration files
##################################

from __future__ import annotations

import shutil
import subprocess
from enum import Enum
from pathlib import Path

import rich
from pydantic import BaseModel, DirectoryPath, FilePath, ValidationInfo, field_validator, model_validator
from ruamel.yaml import YAML


class RefModelType(str, Enum):
    """Reference model types with their associated flags."""

    SAIL = "sail"
    SPIKE = "spike"

    def signature_flags(self, sig_file: Path | str, granularity: int) -> list[str]:
        """Get the flags for this reference model."""
        flags_map: dict[RefModelType, list[str]] = {
            RefModelType.SAIL: [f"--test-signature={sig_file}", "--signature-granularity", str(granularity)],
            RefModelType.SPIKE: [f"+signature={sig_file}", f"+signature-granularity={granularity}"],
        }
        return flags_map[self]


# Hardcoded spike ``--isa=`` strings — one per XLEN — covering every extension spike
# supports for that XLEN. Derived from the curated lists in
# ``config/spike/spike-rv{32,64}-max/run_cmd.txt``.
_SPIKE_ISA: dict[int, str] = {
    32: (
        "rv32imafdcbv"
        "_zicbom_zicboz_zicbop_zicfilp_zicfiss_zicond_zicsr_zicntr_zicclsm_ziccif"
        "_zifencei_zihintntl_zihintpause_zihpm_zimop"
        "_zabha_zacas_zaamo_zalrsc_zawrs"
        "_zfa_zfbfmin_zfh"
        "_zca_zcb_zcd_zcf_zcmop"
        "_zbc_zkn_zkr_zks"
        "_zvfbfmin_zvfbfwma_zvfh"
        "_zvbb_zvbc_zvkg_zvkned_zvknha_zvknhb_zvksed_zvksh_zvkt"
        "_sscofpmf_smcntrpmf_sstc"
        "_svinval_svade_svadu"
    ),
    64: (
        "rv64imafdcbvh"
        "_zicbom_zicboz_zicbop_zicfilp_zicfiss_zicond_zicsr_zicntr_zicclsm_ziccif"
        "_zifencei_zihintntl_zihintpause_zihpm_zimop"
        "_zabha_zacas_zaamo_zalrsc_zawrs"
        "_zfa_zfbfmin_zfh"
        "_zca_zcb_zcd_zcmop"
        "_zbc_zkn_zkr_zks"
        "_zvfbfmin_zvfbfwma_zvfh"
        "_zvbb_zvbc_zvkg_zvkned_zvknha_zvknhb_zvksed_zvksh_zvkt"
        "_sscofpmf_smcntrpmf_sstc"
        "_svinval_svade_svadu_svnapot_svpbmt"
    ),
}


def spike_isa_string(xlen: int) -> str:
    """Return spike's ``--isa=`` string for the given XLEN."""
    return _SPIKE_ISA[xlen]


class CompilerType(str, Enum):
    """Compiler types."""

    CLANG = "clang"
    GCC = "gcc"


class CoverageSimulator(str, Enum):
    """Coverage simulator backends."""

    QUESTA = "questa"
    VCS = "vcs"


class Config(BaseModel):
    """Configuration for the RISC-V architecture verification framework."""

    name: str
    udb_config: FilePath
    linker_script: FilePath
    dut_include_dir: DirectoryPath
    compiler_exe: Path
    objdump_exe: Path | None = None
    compiler_type: CompilerType  # Inferred from compiler_exe by model validator
    ref_model_exe: Path
    ref_model_type: RefModelType  # Inferred from ref_model_exe by model validator
    include_priv_tests: bool = True

    model_config = {"frozen": True}

    @field_validator("compiler_exe", "ref_model_exe", "objdump_exe")
    @classmethod
    def validate_executable(cls, v: Path | None, info: ValidationInfo) -> Path | None:
        """Ensure the executable can be found."""
        if v is not None:
            full_path = shutil.which(v)
            if full_path is None:
                raise FileNotFoundError(f"{info.field_name} executable not found: {v}")
            return Path(full_path)
        else:
            return v

    @model_validator(mode="before")
    @classmethod
    def infer_compiler_type(cls, data: dict[str, object]) -> dict[str, object]:
        """Infer compiler type from compiler_exe if not explicitly set."""
        if data.get("compiler_type") is None:
            compiler_exe = data.get("compiler_exe")
            compiler_str = str(compiler_exe) if isinstance(compiler_exe, (str, Path)) else None
            if compiler_str is None:
                raise ValueError("Unable to infer compiler type from compiler_exe.")
            if "clang" in compiler_str:
                data["compiler_type"] = CompilerType.CLANG
            else:
                data["compiler_type"] = CompilerType.GCC
        return data

    @model_validator(mode="before")
    @classmethod
    def infer_ref_model_type(cls, data: dict[str, object]) -> dict[str, object]:
        """Infer reference model type from ref_model_exe if not explicitly set."""
        if data.get("ref_model_type") is None:
            ref_model_exe = data.get("ref_model_exe")
            ref_model_str = str(ref_model_exe) if isinstance(ref_model_exe, (str, Path)) else None
            if ref_model_str is None:
                raise ValueError("Unable to infer reference model type from ref_model_exe.")
            executable_name = Path(ref_model_str).name.lower()
            if "spike" in executable_name:
                data["ref_model_type"] = RefModelType.SPIKE
            elif "sail" in executable_name:
                data["ref_model_type"] = RefModelType.SAIL
            else:
                raise ValueError(f"Unable to infer reference model type from ref_model_exe: {ref_model_exe}")
        return data

    @field_validator("udb_config", "linker_script", "dut_include_dir", mode="before")
    @classmethod
    def resolve_relative_paths(cls, v: str | None, info: ValidationInfo) -> Path | None:
        """Resolve relative paths relative to config file."""
        if v is None:
            return v
        path = Path(v)
        if path.is_absolute():
            return path
        context = info.context
        if context is None:
            raise ValueError("Unable to resolve relative paths.")
        config_file_dir: Path = context["config_file_dir"]
        return config_file_dir.absolute() / path

    def __str__(self) -> str:
        """Pretty print configuration."""
        lines = ["Configuration:"]
        for field_name, field_value in self.model_dump().items():
            lines.append(f"  {field_name}: {field_value}")
        return "\n".join(lines)


# Minimum required tool versions
REQUIRED_SAIL_VERSION = "0.11"
REQUIRED_GCC_MAJOR_VERSION = 15
REQUIRED_CLANG_MAJOR_VERSION = 20


def check_ref_model_version(config: Config) -> None:
    """Check that the reference model version is compatible."""
    if config.ref_model_type == RefModelType.SAIL:
        try:
            result = subprocess.run(
                [str(config.ref_model_exe), "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            version = result.stdout.strip()
            if version != REQUIRED_SAIL_VERSION:
                raise ValueError(
                    f"Sail reference model version mismatch. ACT4 requires version {REQUIRED_SAIL_VERSION}, but {version} was found. "
                    "Refer to the ACT4 README for installation instructions: https://github.com/riscv/riscv-arch-test/tree/act4?tab=readme-ov-file#4-risc-v-sail-reference-model",
                )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to check Sail version: {e}") from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Timeout while checking Sail version: {e}") from e
    elif config.ref_model_type == RefModelType.SPIKE:
        # Spike has no stable --version flag; perform a lightweight startup check instead.
        try:
            result = subprocess.run(
                [str(config.ref_model_exe), "--help"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if result.returncode != 0:
                error_output = result.stderr.strip() or result.stdout.strip()
                details = f": {error_output}" if error_output else ""
                raise RuntimeError(
                    f"Spike reference model exited with status {result.returncode} during startup check{details}",
                )
        except OSError as e:
            raise RuntimeError(f"Failed to start Spike reference model: {e}") from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Timeout while starting Spike reference model: {e}") from e

        rich.print(
            f"[yellow][bold]WARNING:[/bold] Using Spike as the reference model ([cyan]{config.ref_model_exe}[/cyan]). "
            "The reference model will not be configured to match your DUT and many privileged tests will likely mismatch. "
            "Coverage generation is not supported with Spike.[/yellow]"
        )


def check_compiler_version(config: Config) -> None:
    """Check that the compiler version is compatible."""
    try:
        result = subprocess.run(
            [str(config.compiler_exe), "-dumpversion"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        version_str = result.stdout.strip()
        try:
            major_version = int(version_str.split(".")[0])
        except ValueError:
            raise RuntimeError(f"Unable to parse compiler version from: {version_str!r}")

        if config.compiler_type == CompilerType.GCC:
            required_major = REQUIRED_GCC_MAJOR_VERSION
            compiler_name = "GCC"
        else:
            required_major = REQUIRED_CLANG_MAJOR_VERSION
            compiler_name = "Clang"

        if major_version < required_major:
            raise ValueError(
                f"Compiler version mismatch. ACT4 requires {compiler_name} {required_major} or later, but {version_str} was found. "
                "Refer to the ACT4 README for details: https://github.com/riscv/riscv-arch-test/tree/act4?tab=readme-ov-file#3-risc-v-compiler",
            )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to check compiler version: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"Timeout while checking compiler version: {e}") from e


def load_config(config_file: Path) -> Config:
    """Load riscv-arch-test framework configuration from a YAML file."""
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    yaml = YAML(typ="safe", pure=True)
    with config_file.open() as f:
        yaml_data = yaml.load(f)

    if yaml_data is None:
        raise ValueError(f"Configuration file is empty: {config_file}")

    config = Config.model_validate(yaml_data, context={"config_file_dir": config_file.parent})
    check_ref_model_version(config)
    check_compiler_version(config)
    return config
