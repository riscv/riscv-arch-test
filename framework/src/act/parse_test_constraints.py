##################################
# parse_test_constraints.py
#
# jcarlin@hmc.edu 6 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Parse YAML comment header from test files
##################################

import re
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, FilePath, ValidationError
from rich.console import Console
from rich.panel import Panel
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_TEST_FILE_SUFFIXES = (".S", ".c")

# A directory containing this manifest is a single directory-level test unit:
# all of its sources are compiled and linked into one ELF, instead of every
# file being an independent test.
SUITE_MANIFEST = "suite.yaml"

ExtensionRequirement = str | Annotated[frozenset[str], Field(min_length=1)]


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
    required_extensions: frozenset[ExtensionRequirement] = Field(alias="REQUIRED_EXTENSIONS", min_length=1)
    forbidden_extensions: frozenset[str] = Field(alias="FORBIDDEN_EXTENSIONS", default_factory=frozenset)
    march: str = Field(alias="MARCH", pattern=r"rv(?:32|64|\$\{XLEN\})[ieg].*")
    needs_signature: bool = Field(alias="NEEDS_SIGNATURE", default=True)
    min_harts: int = Field(alias="MIN_HARTS", default=1, ge=1)
    params: dict[str, int | bool | str] = Field(default_factory=dict)

    # Directory-level test units only (see SUITE_MANIFEST). Every field has a
    # default so single-file .S/.c test headers are unaffected.
    sources: tuple[str, ...] = Field(alias="SOURCES", default_factory=tuple)
    runtime: tuple[str, ...] = Field(alias="RUNTIME", default_factory=tuple)
    linker_script: str | None = Field(alias="LINKER_SCRIPT", default=None)
    extra_cflags: tuple[str, ...] = Field(alias="EXTRA_CFLAGS", default_factory=tuple)

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
        Scans both the single-letter cluster (before first underscore) and any
        underscore-separated multi-letter extensions, so D in "rv32i_f_d_zfhmin"
        is detected correctly.
        """
        m = self.march.lower()
        parts = m.split("_")
        single_letter = parts[0]
        # Skip the rv{XLEN} prefix when scanning single-letter extensions.
        sl_exts = re.sub(r"^rv\d+", "", single_letter)
        rest = parts[1:]
        if "q" in sl_exts or "q" in rest:
            return "128"
        if "d" in sl_exts or "g" in sl_exts or "d" in rest:
            return "64"
        if "f" in sl_exts or "f" in rest:
            return "32"
        return "32"

    @property
    def e_ext(self) -> bool:
        """Check if E extension is present."""
        return self.march.startswith(("rv32e", "rv64e", "rv${XLEN}e"))

    @property
    def is_c_test(self) -> bool:
        """Whether the test is compiled from C sources."""
        return self.is_suite or self.test_path.suffix == ".c"

    @property
    def is_suite(self) -> bool:
        """Whether this is a directory-level test unit with its own sources."""
        return bool(self.sources)

    @property
    def suite_dir(self) -> Path:
        """Root directory of a directory-level test unit."""
        return self.test_path.parent


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
    if etype == "value_error":
        return e["msg"].removeprefix("Value error, ")
    if etype.startswith("string_pattern_mismatch"):
        return f"illegal value for key '{field}': {got!r}"
    return f"invalid value for key '{field}': {e['msg']}"


def _strip_yaml_comment_prefix(line: str) -> str:
    """Remove an assembly/C comment prefix from a YAML header line."""
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return stripped[1:]
    if stripped.startswith("//"):
        return stripped[2:]
    if stripped.startswith("*"):
        return stripped[1:]
    return line


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

    yaml_lines = [_strip_yaml_comment_prefix(line) for line in yaml_section.split("\n")]
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


def _is_excluded(test_file: Path, exclude_list: list[str]) -> bool:
    """Returns true if the test is excluded.

    An exclusion entry names a suite directory (Sm) or a group of tests whose file names start with
    the entry followed by _ or - (Sm_mcsr_walk matches Sm_mcsr_walk-00.S; I-add matches I-add-00.S).
    An entry ending in - matches only that group, not longer groups that extend its name
    (S_scsr- matches S_scsr-00.S but not S_scsr_addr-00.S; S- matches S-00.S but not S_F-00.S).
    """
    return test_file.parent.name in exclude_list or (
        any(test_file.name.startswith(ext if ext.endswith("-") else (f"{ext}_", f"{ext}-")) for ext in exclude_list)
    )


def extract_suite_config(manifest: Path) -> TestMetadata:
    """Load a directory-level test unit's ``suite.yaml`` manifest.

    Unlike single-file tests, the manifest is plain YAML: the file has a .yaml
    suffix, so it needs no START_TEST_CONFIG/END_TEST_CONFIG markers.
    """
    yaml = YAML(typ="safe", pure=True)
    try:
        config_dict = yaml.load(manifest.read_text())
    except YAMLError as e:
        raise TestYamlHeaderError(manifest, f"YAML parse error: {e}") from None

    if not isinstance(config_dict, dict):
        raise TestYamlHeaderError(manifest, "manifest must be a YAML mapping")

    config_dict["test_path"] = str(manifest.absolute())

    try:
        metadata = TestMetadata.model_validate(config_dict)
    except ValidationError as e:
        raise TestYamlHeaderError(manifest, _describe_validation_error(e)) from None

    # Fail at discovery time rather than at compile time when a manifest names
    # a source or linker script that is not there.
    suite_dir = manifest.parent
    declared = list(metadata.sources)
    if metadata.linker_script is not None:
        declared.append(metadata.linker_script)
    missing = sorted(name for name in declared if not (suite_dir / name).is_file())
    if missing:
        raise TestYamlHeaderError(manifest, f"missing file(s): {', '.join(missing)}")

    return metadata


def generate_test_dict(tests_dir: Path, extensions: str, exclude: str = "") -> dict[str, TestMetadata]:
    """Generate a dictionary of tests with their corresponding metadata from the specified directory.

    Args:
        tests_dir: Directory containing test files.
        extensions: Comma-separated list of extensions to include, or "all" for all extensions.
        exclude: Comma-separated list of extensions or test groups to exclude (applied after extensions filter).

    Returns:
        Dictionary mapping test file paths to their metadata. A directory-level
        test unit is keyed by its directory path relative to ``tests_dir``.
    """

    extension_list: list[str] = []
    if extensions != "all":
        extension_list.extend(ext.strip() for ext in extensions.split(",") if ext.strip())

    exclude_list: list[str] = []
    if exclude:
        exclude_list.extend(ext.strip() for ext in exclude.split(",") if ext.strip())

    # Directories holding a manifest are single multi-source test units; the
    # sources inside them belong to the unit and are not independent tests.
    suite_dirs = frozenset(manifest.parent for manifest in tests_dir.rglob(SUITE_MANIFEST))

    def _is_runtime_or_suite_source(test_file: Path) -> bool:
        # Everything under tests/env/ is shared runtime support code, at any depth.
        if "env" in test_file.relative_to(tests_dir).parts:
            return True
        return any(suite_dir in test_file.parents for suite_dir in suite_dirs)

    test_list: dict[str, TestMetadata] = {}

    if extension_list:
        for ext in extension_list:
            if ext in exclude_list:
                continue
            for suffix in _TEST_FILE_SUFFIXES:
                for test_file in tests_dir.rglob(f"*/{ext}/*{suffix}"):
                    if _is_runtime_or_suite_source(test_file) or _is_excluded(test_file, exclude_list):
                        continue
                    config = extract_yaml_config(test_file)
                    test_file_unique_name = str(test_file.relative_to(tests_dir))
                    test_list[test_file_unique_name] = config
    else:
        for suffix in _TEST_FILE_SUFFIXES:
            for test_file in tests_dir.rglob(f"*{suffix}"):
                if _is_runtime_or_suite_source(test_file) or _is_excluded(test_file, exclude_list):
                    continue
                config = extract_yaml_config(test_file)
                test_file_unique_name = str(test_file.relative_to(tests_dir))
                test_list[test_file_unique_name] = config

    for suite_dir in sorted(suite_dirs):
        rel_dir = suite_dir.relative_to(tests_dir)
        if any(part in exclude_list for part in rel_dir.parts):
            continue
        if extension_list and not any(ext in rel_dir.parts for ext in extension_list if ext not in exclude_list):
            continue
        test_list[str(rel_dir)] = extract_suite_config(suite_dir / SUITE_MANIFEST)

    return test_list
