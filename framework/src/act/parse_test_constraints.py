##################################
# parse_test_constraints.py
#
# jcarlin@hmc.edu 6 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Parse YAML comment header from test files
##################################

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, FilePath
from ruamel.yaml import YAML


class TestMetadata(BaseModel):
    """Metadata for a RISC-V test case extracted from YAML configuration."""

    test_path: FilePath
    implemented_extensions: set[str] = Field(min_length=1)
    march: str = Field(alias="MARCH", pattern=r"rv(?:32|64|\$\{XLEN\})[ieg].*")
    config_dependent: bool = Field(alias="CONFIG_DEPENDENT")
    params: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid", "frozen": True}

    @property
    def coverage_group(self) -> str:
        return self.test_path.parent.name

    @property
    def mxlen(self) -> int | None:
        """Get MXLEN parameter if present."""
        return self.params.get("MXLEN")

    @property
    def flen(self) -> str:
        """Get floating-point register length: '64' if D extension present, else '32'."""
        return "128" if "Q" in self.implemented_extensions else "64" if "D" in self.implemented_extensions else "32"


def extract_yaml_config(file: Path) -> TestMetadata:
    """Extract YAML configuration from a test file between START_TEST_CONFIG and END_TEST_CONFIG markers."""
    content = file.read_text()

    # Find boundaries using simple string operations
    start_marker = "START_TEST_CONFIG"
    end_marker = "END_TEST_CONFIG"

    start_pos = content.find(start_marker)
    end_pos = content.find(end_marker)

    if start_pos == -1 or end_pos == -1:
        raise ValueError(f"Could not find YAML config section in {file}")

    # Extract content between markers
    start_pos = content.find("\n", start_pos) + 1  # Skip to next line after start marker
    end_pos = content.rfind("\n", 0, end_pos)  # Go to line before end marker

    yaml_section = content[start_pos:end_pos]

    # Process lines to remove comment prefixes
    yaml_lines: list[str] = []
    for line in yaml_section.split("\n"):
        line = line.lstrip("#")
        yaml_lines.append(line)
    yaml_lines.append(f" test_path: '{file.absolute()}'")  # Add test_path to config data

    yaml = YAML(typ="safe", pure=True)
    config_dict = yaml.load("\n".join(yaml_lines))
    return TestMetadata.model_validate(config_dict)


def generate_test_dict(tests_dir: Path) -> dict[str, TestMetadata]:
    """Generate a dictionary of tests with their corresponding metadata from the specified directory."""
    if not tests_dir.is_dir():
        raise ValueError(f"tests_dir is not a directory: {tests_dir}")

    test_list: dict[str, TestMetadata] = {}

    for test_file in tests_dir.rglob("*.S"):
        config = extract_yaml_config(test_file)
        test_file_unique_name = str(test_file.relative_to(tests_dir))
        test_list[test_file_unique_name] = config

    return test_list
