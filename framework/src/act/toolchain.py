# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
"""Discover RISC-V compiler capabilities and build compiler flags."""

import re
import shutil
import subprocess
from enum import Enum
from pathlib import Path


class CompilerType(str, Enum):
    """Supported RISC-V compiler drivers."""

    CLANG = "clang"
    GCC = "gcc"


_MARCH_HELP_HEADER = "All available -march extensions for RISC-V"
_EXPERIMENTAL_EXTENSIONS_HEADER = "Experimental extensions"
_MARCH_HELP_END_HEADERS = ("Supported Profiles", "Experimental Profiles", "Use -march")
_MARCH_HELP_ROW = re.compile(r"^\s*([a-z][a-z0-9]*)\s+([0-9][0-9., ]*)", re.IGNORECASE)
_MARCH_PREFIX = re.compile(r"^(rv(?:32|64))(.*)$", re.IGNORECASE)
_SINGLE_LETTER_EXTENSION = re.compile(r"[a-z](?:\d+p\d+)?", re.IGNORECASE)
_MARCH_VERSION = re.compile(r"\d+p\d+$", re.IGNORECASE)


def _parse_supported_extensions(output: str, tool: str) -> dict[str, str | None]:
    """Parse RISC-V extensions from ``-march=help`` style output."""
    _, header, output = output.partition(_MARCH_HELP_HEADER)
    if not header:
        raise RuntimeError(f"Unable to parse RISC-V extensions reported by {tool}.")

    extensions: dict[str, str | None] = {}
    experimental = False
    for line in output.splitlines():
        if any(header in line for header in _MARCH_HELP_END_HEADERS):
            break
        if _EXPERIMENTAL_EXTENSIONS_HEADER in line:
            experimental = True
            continue
        if match := _MARCH_HELP_ROW.match(line):
            name, versions = match.groups()
            if experimental:
                latest = max(tuple(int(part) for part in version.split(".")) for version in versions.split(","))
                extensions[name.lower()] = "p".join(map(str, latest))
            else:
                extensions[name.lower()] = None

    if not extensions:
        raise RuntimeError(f"Unable to parse RISC-V extensions reported by {tool}.")
    return extensions


def _parse_march(march: str) -> tuple[str, list[str]]:
    """Split a canonical ISA string into its base and extension tokens."""
    parts = march.lower().split("_")
    if not (match := _MARCH_PREFIX.match(parts.pop(0))):
        raise ValueError(f"Invalid RISC-V ISA string: {march}")

    extensions = _SINGLE_LETTER_EXTENSION.findall(match.group(2))
    if (
        not extensions
        or "".join(extensions) != match.group(2)
        or any(not extension.isalnum() or not extension[0].isalpha() for extension in parts)
    ):
        raise ValueError(f"Invalid RISC-V ISA string: {march}")

    extensions.extend(f"_{extension}" for extension in parts)
    return match.group(1), extensions


class Toolchain:
    """A configured RISC-V compiler driver and its related tools."""

    def __init__(self, compiler_exe: Path, compiler_type: CompilerType) -> None:
        self.compiler_exe = compiler_exe
        self.compiler_type = compiler_type
        self._version: str | None = None
        self._assembler: Path | None = None
        self._isa_support: dict[tuple[int, bool], dict[str, str | None]] = {}

    def version(self) -> str:
        """Return the compiler version reported by the driver."""
        if self._version is None:
            result = subprocess.run(
                [str(self.compiler_exe), "-dumpversion"], capture_output=True, text=True, check=True, timeout=5
            )
            self._version = result.stdout.strip()
        return self._version

    def compile_prefix(self, xlen: int) -> tuple[str, ...]:
        """Build the compiler command prefix for one RISC-V target."""
        compiler = str(self.compiler_exe)
        if self.compiler_type == CompilerType.CLANG:
            return compiler, f"--target=riscv{xlen}", "-fuse-ld=lld"
        return (compiler, "-Wl,--no-warn-rwx-segments")

    def march_flags(self, xlen: int, march: str, *, assembly: bool, e_ext: bool = False) -> tuple[str, ...]:
        """Build compiler flags that set and validate the ISA string."""
        march = march.replace("${XLEN}", str(xlen))
        base, extension_tokens = _parse_march(march)
        extensions = {_MARCH_VERSION.sub("", token.removeprefix("_")) for token in extension_tokens}
        if "g" in extensions:
            extensions.remove("g")
            extensions.update(("i", "m", "a", "f", "d", "zicsr", "zifencei"))

        support = self._supported_extensions(xlen, assembly)
        missing_extensions = sorted(extensions - support.keys())
        if missing_extensions:
            tool = "Clang" if self.compiler_type == CompilerType.CLANG else "GNU assembler" if assembly else "GCC"
            raise ValueError(
                f"{tool} does not support extension(s) {', '.join(missing_extensions)} required by -march={march}."
            )

        if self.compiler_type == CompilerType.CLANG:
            experimental = False
            resolved_extensions: list[str] = []
            for token in extension_tokens:
                name = _MARCH_VERSION.sub("", token.removeprefix("_"))
                version = support.get(name)
                experimental |= version is not None
                resolved_extensions.append(
                    f"{'_' if token.startswith('_') else ''}{name}{version}" if version else token
                )
            resolved_march = f"{base}{''.join(resolved_extensions)}"
            experimental_flags = ("-menable-experimental-extensions",) if experimental else ()
            return (*experimental_flags, f"-march={resolved_march}")

        if not assembly:
            return (f"-march={march}",)
        base_march = f"rv{xlen}{'e' if e_ext else 'i'}"
        return f"-march={base_march}", "-Xassembler", f"-march={march}"

    def _supported_extensions(self, xlen: int, assembly: bool) -> dict[str, str | None]:
        """Return cached ISA support for the program that receives MARCH flags."""
        assembly &= self.compiler_type == CompilerType.GCC
        key = xlen, assembly
        if key not in self._isa_support:
            if self.compiler_type == CompilerType.CLANG:
                command = [str(self.compiler_exe), f"--target=riscv{xlen}", "-print-supported-extensions"]
                tool = str(self.compiler_exe)
            elif assembly:
                if self._assembler is None:
                    assembler = subprocess.run(
                        [str(self.compiler_exe), "-print-prog-name=as"],
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=5,
                    ).stdout.strip()
                    if Path(assembler).is_absolute():
                        self._assembler = Path(assembler)
                    elif resolved := shutil.which(assembler):
                        self._assembler = Path(resolved)
                    else:
                        raise FileNotFoundError(f"Assembler selected by {self.compiler_exe} was not found: {assembler}")
                command = [str(self._assembler), "-march=help"]
                tool = str(self._assembler)
            else:
                command = [str(self.compiler_exe), "-march=help"]
                tool = str(self.compiler_exe)
            result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=5)
            self._isa_support[key] = _parse_supported_extensions(f"{result.stdout}\n{result.stderr}", tool)
        return self._isa_support[key]
