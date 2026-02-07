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
from typing import TypedDict

import pyjson5
from pydantic import BaseModel, DirectoryPath, FilePath, ValidationInfo, field_validator
from ruamel.yaml import YAML

from act.parse_test_constraints import TestMetadata


class RefModelType(str, Enum):
    """Reference model types with their associated flags."""

    # TODO: Add support for additional reference models (Spike, Whisper, etc.)
    SAIL = "sail"
    # SPIKE = "spike"

    @property
    def signature_flags(self) -> str:
        """Get the flags for this reference model."""
        flags_map = {
            RefModelType.SAIL: "--test-signature={sig_file} --signature-granularity {granularity}",
            # RefModelType.SPIKE: "+signature={sig_file} +signature-granularity={granularity}",
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
        return f"{self.compiler_exe} {'--target=riscv${XLEN}' if compiler_is_clang else ''}\\\n\t\t-I{self.dut_include_dir.absolute()} \\\n\t\t-T{self.linker_script.absolute()}"

    def __str__(self) -> str:
        """Pretty print configuration."""
        lines = ["Configuration:"]
        for field_name, field_value in self.model_dump().items():
            lines.append(f"  {field_name}: {field_value}")
        return "\n".join(lines)


def check_ref_model_version(config: Config) -> None:
    """Check that the reference model version is compatible."""
    if config.ref_model_type == RefModelType.SAIL:
        required_version = "0.9"
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
                    "Refer to the ACT4 README for installation instructions: https://github.com/riscv-non-isa/riscv-arch-test/tree/act4?tab=readme-ov-file#3-risc-v-sail-golden-reference-model",
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


class ConfigData(TypedDict):
    """Type definition for configuration data dictionary."""

    config: Config
    xlen: int
    e_ext: bool
    selected_tests: dict[str, TestMetadata]


def check_config_consistency(configs: list[ConfigData]) -> None:
    """Validate that multiple configurations are mutually consistent.

    Configurations are grouped by their (XLEN, E-extension) pair, using the
    ``xlen`` and ``e_ext`` fields in each :class:`ConfigData` entry. Within each
    group, the first configuration encountered is treated as the reference, and
    all subsequent configurations in that group are compared against it.

    The following fields and artifacts of the underlying :class:`Config` objects
    must match for all configurations that share the same (XLEN, E-ext) pair:
    * ``compiler_exe``
    * ``objdump_exe``
    * ``ref_model_type``
    * ``ref_model_exe``
    * The contents of ``linker_script``
    * The contents of ``model_test.h`` located in ``dut_include_dir``
    * The contents of ``sail.json`` located in ``dut_include_dir`` (if present)

    If any of these values or file contents differ between configurations with
    the same (XLEN, E-ext) pair, a :class:`ValueError` is raised describing the
    inconsistency and identifying the conflicting configurations.
    """
    # Store the reference configuration for each (XLEN, E-ext) pair (first one encountered)
    ref_configs: dict[tuple[int, bool], Config] = {}

    for config_data in configs:
        xlen = config_data["xlen"]
        e_ext = config_data["e_ext"]
        config: Config = config_data["config"]
        key = (xlen, e_ext)

        # First time seeing this (XLEN, E-ext) pair? Set it as reference.
        if key not in ref_configs:
            ref_configs[key] = config
            continue

        # Otherwise, compare against the reference
        ref_config = ref_configs[key]
        ref_model_header = ref_config.dut_include_dir / "model_test.h"
        ref_linker_script = ref_config.linker_script

        # Validate compiler_exe
        if ref_config.compiler_exe != config.compiler_exe:
            raise ValueError(
                f"Inconsistent compiler_exe for XLEN={xlen}, E-ext={e_ext}: "
                f"{ref_config.name} uses {ref_config.compiler_exe}, "
                f"{config.name} uses {config.compiler_exe}. "
                f"All configs with XLEN={xlen} and E-ext={e_ext} must have the same compiler_exe for common compilation. Update the configs to match or pass the configs to separate runs of the ACT framework."
            )

        # Validate objdump_exe
        if ref_config.objdump_exe != config.objdump_exe:
            raise ValueError(
                f"Inconsistent objdump_exe for XLEN={xlen}, E-ext={e_ext}: "
                f"{ref_config.name} uses {ref_config.objdump_exe}, "
                f"{config.name} uses {config.objdump_exe}. "
                f"All configs with XLEN={xlen} and E-ext={e_ext} must have the same objdump_exe for common compilation. Update the configs to match or pass the configs to separate runs of the ACT framework."
            )

        # Validate ref_model_type
        if ref_config.ref_model_type != config.ref_model_type:
            raise ValueError(
                f"Inconsistent ref_model_type for XLEN={xlen}, E-ext={e_ext}: "
                f"{ref_config.name} uses {ref_config.ref_model_type}, "
                f"{config.name} uses {config.ref_model_type}. "
                f"All configs with XLEN={xlen} and E-ext={e_ext} must have the same ref_model_type for common compilation. Update the configs to match or pass the configs to separate runs of the ACT framework."
            )

        # Validate ref_model_exe
        if ref_config.ref_model_exe != config.ref_model_exe:
            raise ValueError(
                f"Inconsistent ref_model_exe for XLEN={xlen}, E-ext={e_ext}: "
                f"{ref_config.name} uses {ref_config.ref_model_exe}, "
                f"{config.name} uses {config.ref_model_exe}. "
                f"All configs with XLEN={xlen} and E-ext={e_ext} must have the same ref_model_exe for common compilation. "
                "Update the configs to match or pass the configs to separate runs of the ACT framework."
            )

        # Validate linker_script content
        try:
            ref_linker_content = ref_linker_script.read_bytes()
            config_linker_content = config.linker_script.read_bytes()
        except (FileNotFoundError, OSError) as e:
            raise ValueError(f"Error reading linker script: {e}") from e

        if ref_linker_content != config_linker_content:
            raise ValueError(
                f"Inconsistent linker_script content for XLEN={xlen}, E-ext={e_ext} between {ref_config.name} and {config.name}. "
                f"All configs with XLEN={xlen} and E-ext={e_ext} must have the same linker_script contents for common compilation. Update the configs to match or pass the configs to separate runs of the ACT framework."
            )

        # Validate model_test.h content
        model_header = config.dut_include_dir / "model_test.h"

        if not ref_model_header.is_file():
            raise ValueError(
                f"Missing model_test.h in dut_include_dir for reference config '{ref_config.name}' "
                f"(XLEN={xlen}, E-ext={e_ext}): expected at {ref_model_header}."
            )
        if not model_header.is_file():
            raise ValueError(
                f"Missing model_test.h in dut_include_dir for config '{config.name}' "
                f"(XLEN={xlen}, E-ext={e_ext}): expected at {model_header}."
            )

        try:
            ref_header_content = ref_model_header.read_bytes()
            header_content = model_header.read_bytes()
        except (FileNotFoundError, OSError) as e:
            raise ValueError(f"Error reading model_test.h: {e}") from e

        if ref_header_content != header_content:
            raise ValueError(
                f"Inconsistent model_test.h content for XLEN={xlen}, E-ext={e_ext} between {ref_config.name} and {config.name}. "
                f"All configs with XLEN={xlen} and E-ext={e_ext} must have the same model_test.h contents for common compilation. Update the configs to match or pass the configs to separate runs of the ACT framework."
            )

        # Validate sail.json memory map if defined
        ref_sail_path = ref_config.dut_include_dir / "sail.json"
        sail_path = config.dut_include_dir / "sail.json"

        if ref_sail_path.exists() and sail_path.exists():
            try:
                ref_sail_data = pyjson5.decode(ref_sail_path.read_text())
                sail_data = pyjson5.decode(sail_path.read_text())
            except (FileNotFoundError, OSError) as e:
                raise ValueError(f"Error reading sail.json: {e}") from e
            except Exception as e:
                raise ValueError(f"Error parsing sail.json: {e}") from e

            try:
                ref_memory_map = ref_sail_data["memory"]["regions"]
                memory_map = sail_data["memory"]["regions"]
            except KeyError as e:
                raise ValueError(f"Invalid sail.json structure (missing memory regions): {e}") from e

            if ref_memory_map != memory_map:
                raise ValueError(
                    f"Inconsistent sail.json memory map for XLEN={xlen}, E-ext={e_ext} between {ref_config.name} and {config.name}. "
                    f"All configs with XLEN={xlen} and E-ext={e_ext} must have the same memory map for common compilation. "
                    "Update the configs to have a consistent memory map, or pass the configs to separate runs of the ACT framework."
                )
