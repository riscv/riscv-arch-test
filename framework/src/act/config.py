##################################
# config.py
#
# jcarlin@hmc.edu 8 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Parse test framework configuration files
##################################

import shutil
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, DirectoryPath, FilePath, ValidationInfo, field_validator
from ruamel.yaml import YAML


class RefModelType(str, Enum):
    """Reference model types with their associated flags."""

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


class Config(BaseModel):
    """Configuration for the RISC-V architecture verification framework."""

    name: str
    udb_config: FilePath
    linker_script: FilePath
    dut_include_dir: DirectoryPath
    compiler_exe: Path
    objdump_exe: Path | None = None
    ref_model_type: RefModelType
    ref_model_exe: Path

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
        return (
            f"{self.compiler_exe} \\\n\t\t-I{self.dut_include_dir.absolute()} \\\n\t\t-T{self.linker_script.absolute()}"
        )

    def __str__(self) -> str:
        """Pretty print configuration."""
        lines = ["Configuration:"]
        for field_name, field_value in self.model_dump().items():
            lines.append(f"  {field_name}: {field_value}")
        return "\n".join(lines)


def load_config(config_file: Path) -> Config:
    """Load riscv-arch-test framework configuration from a YAML file."""
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    yaml = YAML(typ="safe", pure=True)
    with config_file.open() as f:
        yaml_data = yaml.load(f)

    if yaml_data is None:
        raise ValueError(f"Configuration file is empty: {config_file}")

    return Config.model_validate(yaml_data, context={"config_file_dir": config_file.parent})
