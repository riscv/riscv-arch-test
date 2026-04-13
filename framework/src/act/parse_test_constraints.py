##################################
# parse_test_constraints.py
#
# jcarlin@hmc.edu 6 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Parse YAML comment header from test files
##################################

from pathlib import Path

from pydantic import BaseModel, Field, FilePath, ValidationError
from rich.console import Console
from rich.panel import Panel
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError


class TestYamlHeaderError(Exception):
    """Raised when a test file's YAML config header is missing, malformed, or fails validation."""

    def __init__(self, file: Path, problem: str) -> None:
        self.file = file
        self.problem = problem
        super().__init__(f"Malformed {file.name} YAML header: {problem} ({file})")

    def print(self) -> None:
        """Render this error as a formatted panel on stderr."""
        body = (
            f"[bold red]Malformed YAML header in[/] [underline]{self.file.name}[/]\n\n"
            f"[bold]Problem:[/] {self.problem}\n"
            f"[bold]File:[/]    [cyan]{self.file}[/]"
        )
        Console(stderr=True).print(
            Panel(body, title="[bold red]Test YAML Header Error[/]", border_style="red", expand=False)
        )


class TestMetadata(BaseModel):
    """Metadata for a RISC-V test case extracted from YAML configuration."""

    test_path: FilePath
    required_extensions: set[str] = Field(alias="REQUIRED_EXTENSIONS", min_length=1)
    march: str = Field(alias="MARCH", pattern=r"rv(?:32|64|\$\{XLEN\})[ieg].*")
    params: dict[str, int | bool | str] = Field(default_factory=dict)

    model_config = {"extra": "forbid", "frozen": True}

    @property
    def coverage_group(self) -> str:
        return self.test_path.parent.name

    @property
    def mxlen(self) -> int | None:
        """Get MXLEN parameter if present."""
        value = self.params.get("MXLEN")
        return value if isinstance(value, int) else None

    @property
    def flen(self) -> str:
        """Get floating-point register length from the march string.

        FLEN is determined by the widest FP extension in the march: Q=128, D=64, F=32.
        Single-letter extensions (including G=IMAFD) appear before the first underscore.
        """
        base = self.march.split("_")[0].lower()
        if "q" in base:
            return "128"
        if "d" in base or "g" in base:
            return "64"
        if "f" in base:
            return "32"
        return "32"

    @property
    def e_ext(self) -> bool:
        """Check if E extension is present."""
        return self.march.startswith(("rv32e", "rv64e", "rv${XLEN}e"))


def _describe_validation_error(err: ValidationError) -> str:
    """Translate the first Pydantic error into a short human-readable error."""
    e = err.errors()[0]
    field = ".".join(str(p) for p in e["loc"]) or "<root>"
    etype = e["type"]
    got = e.get("input")
    if etype == "extra_forbidden":
        return f"unexpected key '{field}' found"
    if etype == "missing":
        return f"required key '{field}' is missing"
    if etype.startswith(("string_pattern_mismatch", "value_error")):
        return f"illegal value for key '{field}': {got!r}"
    return f"invalid value for key '{field}': {e['msg']}"


def extract_yaml_config(file: Path) -> TestMetadata:
    """Extract YAML configuration from a test file between START_TEST_CONFIG and END_TEST_CONFIG markers."""
    content = file.read_text()

    # Find boundaries using simple string operations
    start_marker = "START_TEST_CONFIG"
    end_marker = "END_TEST_CONFIG"

    start_pos = content.find(start_marker)
    end_pos = content.find(end_marker)

    if start_pos == -1 or end_pos == -1:
        raise TestYamlHeaderError(file, f"missing {start_marker}/{end_marker} markers")

    # Extract content between markers
    start_pos = content.find("\n", start_pos) + 1  # Skip to next line after start marker
    end_pos = content.rfind("\n", 0, end_pos)  # Go to line before end marker

    yaml_section = content[start_pos:end_pos]

    # Process lines to remove comment prefixes
    yaml_lines = [line.lstrip("#") for line in yaml_section.split("\n")]
    yaml_lines.append(f" test_path: '{file.absolute()}'")  # Add test_path to config data

    yaml = YAML(typ="safe", pure=True)
    try:
        config_dict = yaml.load("\n".join(yaml_lines))
    except YAMLError as e:
        raise TestYamlHeaderError(file, f"YAML parse error: {e}") from None

    try:
        return TestMetadata.model_validate(config_dict)
    except ValidationError as e:
        raise TestYamlHeaderError(file, _describe_validation_error(e)) from None


def generate_test_dict(tests_dir: Path, extensions: str, exclude: str = "") -> dict[str, TestMetadata]:
    """Generate a dictionary of tests with their corresponding metadata from the specified directory.

    Args:
        tests_dir: Directory containing test files.
        extensions: Comma-separated list of extensions to include, or "all" for all extensions.
        exclude: Comma-separated list of extensions to exclude (applied after extensions filter).

    Returns:
        Dictionary mapping test file paths to their metadata.
    """

    extension_list: list[str] = []
    if extensions != "all":
        extension_list.extend(ext.strip() for ext in extensions.split(","))

    exclude_list: list[str] = []
    if exclude:
        exclude_list.extend(ext.strip() for ext in exclude.split(","))

    test_list: dict[str, TestMetadata] = {}

    if extension_list:
        for ext in extension_list:
            if ext in exclude_list:
                continue
            for test_file in tests_dir.rglob(f"*/{ext}/*.S"):
                config = extract_yaml_config(test_file)
                test_file_unique_name = str(test_file.relative_to(tests_dir))
                test_list[test_file_unique_name] = config
    else:
        for test_file in tests_dir.rglob("*.S"):
            # Check if the test file's extension directory is in the exclude list
            ext_dir = test_file.parent.name
            if ext_dir in exclude_list:
                continue
            config = extract_yaml_config(test_file)
            test_file_unique_name = str(test_file.relative_to(tests_dir))
            test_list[test_file_unique_name] = config

    return test_list
