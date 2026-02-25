##################################
# config.py
#
# jcarlin@hmc.edu 8 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Parse test framework configuration files
##################################

import shutil
import subprocess
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, DirectoryPath, FilePath, ValidationInfo, field_validator
from ruamel.yaml import YAML


class RefModelType(str, Enum):
    """Reference model types with their associated flags."""

    # TODO: Add support for additional reference models (Whisper, etc.)
    SAIL = "sail"
    SPIKE = "spike"

    @property
    def signature_flags(self) -> str:
        """Get the flags for this reference model."""
        flags_map = {
            RefModelType.SAIL: "--test-signature={sig_file} --signature-granularity {granularity}",
            RefModelType.SPIKE: "+signature={sig_file} +signature-granularity={granularity}",
        }
        return flags_map[self]

    def debug_flags(self) -> str:
        """Get the debug/trace flags for this reference model."""
        flags_map = {
            RefModelType.SAIL: "--trace-all --trace-output {sig_trace_file}",
            RefModelType.SPIKE: "-l --log={sig_trace_file}",
        }
        return flags_map[self]


class Config(BaseModel):
    """Configuration for the RISC-V architecture verification framework."""

    name: str
    udb_config: FilePath
    linker_script: FilePath
    dut_include_dir: DirectoryPath
    compiler_exe: Path
    objdump_exe: Path | None = None
    ref_model_type: RefModelType = RefModelType.SAIL
    ref_model_exe: Path
    ref_model_args: str | None = None

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

    @property
    def compiler_string(self) -> str:
        """Get the compiler executable as a string with relevant flags."""
        compiler_is_clang = "clang" in self.compiler_exe.name
        clang_flags = "--target=riscv${XLEN} -fuse-ld=lld"
        return f"{self.compiler_exe} {clang_flags if compiler_is_clang else ''}\\\n\t\t-I{self.dut_include_dir.absolute()} \\\n\t\t-T{self.linker_script.absolute()}"

    def __str__(self) -> str:
        """Pretty print configuration."""
        lines = ["Configuration:"]
        for field_name, field_value in self.model_dump().items():
            lines.append(f"  {field_name}: {field_value}")
        return "\n".join(lines)


def check_ref_model_version(config: Config) -> None:
    """Check that the reference model version is compatible."""
    if config.ref_model_type == RefModelType.SAIL:
        required_version = "0.10"
        try:
            result = subprocess.run(
                [str(config.ref_model_exe), "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            version = result.stdout.strip()
            if version != required_version:
                raise ValueError(
                    f"Sail reference model version mismatch. ACT4 requires version {required_version}, but {version} was found. "
                    "Refer to the ACT4 README for installation instructions: https://github.com/riscv/riscv-arch-test/tree/act4?tab=readme-ov-file#3-risc-v-sail-golden-reference-model",
                )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to check Sail version: {e}") from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Timeout while checking Sail version: {e}") from e


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
    return config
