#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 RISC-V International
#
# Generate a DUT's UDB configuration and Sail configuration by running the feature extractor on it.
#
# Written by David Harris with assistance from Claude.
#
#   uv run tests-dev/priv/UDBFeatureExtractor/make_config.py --config-dir config/cores/<vendor>/<core> --out-dir OUT
#
# Only test_config.yaml, run_cmd.txt, link.ld and rvmodel_macros.h are read from the configuration
# directory.  The steps are:
#   1. Run xlen_probe on the DUT to learn XLEN (the run command only decides which ELF class to try
#      first).
#   2. Build the extractor for that XLEN and run it with run_cmd.txt.
#   3. Write <name>.yaml: the extensions and parameters the extractor reported, then every parameter
#      UDB still requires, filled with the value most ACT configurations use and marked as assumed,
#      until `udb validate cfg` accepts the file.
#   4. Write sail.json from the yaml with udb_to_sail.py, adding the Sail-only values the extractor
#      measured ("# sail:" lines).

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections import Counter
from functools import cache
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

sys.path.insert(0, str(Path(__file__).resolve().parent))
import udb_to_sail

SRC_DIR = Path(__file__).resolve().parent
REPO_ROOT = SRC_DIR.parents[2]
GEMFILE = REPO_ROOT / "framework/src/act/data/Gemfile"

DEBUG_PLACEHOLDER_RE = re.compile(r"\{debug:([^}]*)\}")
TIMESTAMP_RE = re.compile(r"^\[\s*\d+ [a-z]+\] ")
# How to make each simulator write the console output to a file; anything else prints it on stdout
CONSOLE_FLAGS = {
    "sail_riscv_sim": "--terminal-log {out}",
    "wsim": "--args '+UART_LOG=1 +UART_LOG_FILE={out}'",
}


def load_yaml(text: str) -> dict[str, Any]:
    """Parse yaml; ruamel's YAML objects are not thread-safe, so each call makes its own."""
    return YAML(typ="safe").load(text)


# ---------------------------------------------------------------------------------------------
# Running on the DUT


def run_on_dut(config_dir: Path, elf: Path, out: Path, timeout: int) -> str:
    """Run an ELF with the configuration's run_cmd.txt and return its console output."""
    command = DEBUG_PLACEHOLDER_RE.sub("", (config_dir / "run_cmd.txt").read_text()).split()
    env = dict(os.environ)
    while command and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", command[0]):
        var, value = command.pop(0).split("=", 1)
        env[var] = value
    if not command or shutil.which(command[0]) is None:
        raise FileNotFoundError(f"{command[0] if command else 'run_cmd.txt'} not on PATH")
    out.unlink(missing_ok=True)
    flags = CONSOLE_FLAGS.get(Path(command[0]).name)
    if flags:
        command[1:1] = shlex.split(flags.format(out=out))
    command.append(str(elf))
    log = out.with_suffix(".log")
    try:
        with log.open("w") as f:
            subprocess.run(
                command, stdout=f, stderr=subprocess.STDOUT, cwd=REPO_ROOT, env=env, timeout=timeout, check=False
            )
    except subprocess.TimeoutExpired:
        pass
    text = out.read_text(errors="replace") if out.exists() and out.stat().st_size else log.read_text(errors="replace")
    if (
        re.search(r"no simulator at|not found|No such file or directory", log.read_text(errors="replace"))
        and "# " not in text
    ):
        raise FileNotFoundError(f"{command[0]} could not start its simulator; see {log}")
    return "\n".join(TIMESTAMP_RE.sub("", line) for line in text.splitlines())


def make(target: str, build: Path, test_config: dict[str, Any], config_dir: Path, xlen: int) -> Path:
    linker = (config_dir / test_config.get("linker_script", "link.ld")).resolve()
    include = (config_dir / test_config.get("dut_include_dir", ".")).resolve()
    build.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "make",
            "-s",
            "-f",
            str(SRC_DIR / "Makefile"),
            target,
            f"XLEN={xlen}",
            f"CONFIG_DIR={config_dir.resolve()}",
            f"LINKER_SCRIPT={linker}",
            f"DUT_INCLUDE_DIR={include}",
            f"BUILD_DIR={build}",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    return build / (f"xlen_probe{xlen}.elf" if target == "xlen-elf" else f"feature_extractor{xlen}.elf")


def xlen_hint(config_dir: Path) -> int:
    """32 if the run command (or a JSON/IC file it names) mentions RV32, else 64.  Only an ordering hint."""
    text = (config_dir / "run_cmd.txt").read_text()
    for path in re.findall(r"[\w./-]+\.(?:json|ic)\b", text):
        f = REPO_ROOT / path
        if f.exists():
            text += f.read_text(errors="replace")
    text += config_dir.name
    return 32 if re.search(r"rv32|riscv32|\"xlen\"\s*:\s*32|RV32", text) else 64


def detect_xlen(config_dir: Path, test_config: dict[str, Any], build: Path, timeout: int) -> int:
    first = xlen_hint(config_dir)
    for xlen in (first, 96 - first):
        try:
            elf = make("xlen-elf", build, test_config, config_dir, xlen)
        except subprocess.CalledProcessError:
            continue  # rvmodel_macros.h may only assemble for its own XLEN
        text = run_on_dut(config_dir, elf, build / f"xlen_probe{xlen}.txt", timeout)
        m = re.search(r"# xlen: (32|64)", text)
        if m:
            return int(m.group(1))
    raise RuntimeError(f"xlen_probe printed nothing on {config_dir}; see {build}/xlen_probe*.log")


# ---------------------------------------------------------------------------------------------
# The extractor's output


def parse_output(text: str) -> tuple[list[str], dict[str, Any], dict[str, Any], list[str]]:
    """Return the extension lines, the params, the "# sail:" values and the header comments."""
    ext_lines = re.findall(r"^\s*- \{ name: \w+, version: \"[^\"]*\" \}$", text, re.MULTILINE)
    sail: dict[str, Any] = {}
    for key, value in re.findall(r"^# sail: ([\w.]+): (.*)$", text, re.MULTILINE):
        sail[key] = json.loads(value)
    comments = [
        line for line in text.splitlines() if re.match(r"^# (untested|note|warning|FATAL|sail-unmodelled)", line)
    ]
    yaml_text = "\n".join(line for line in text.splitlines() if re.match(r"^(params:|  [A-Z0-9_]+: )", line))
    params: dict[str, Any] = {}
    for _ in range(8):  # a simulator that stops on a cycle limit can cut the last line
        try:
            params = (load_yaml(yaml_text) or {}).get("params") or {}
            break
        except Exception:  # noqa: BLE001
            yaml_text = yaml_text[: yaml_text.rstrip("\n").rfind("\n")]
    return [line.strip() for line in ext_lines], params, sail, comments


# ---------------------------------------------------------------------------------------------
# Completing the yaml with UDB


# UDB caches each resolved configuration under its name in $XDG_DATA_HOME/udb, and reuses it when it
# is newer than the yaml; a generated yaml shares its name with the checked-in one, so its UDB runs
# use a data directory of their own
UDB_DATA_HOME: Path | None = None


def bundle_env() -> dict[str, str]:
    env = {**os.environ, "BUNDLE_GEMFILE": str(GEMFILE)}
    if UDB_DATA_HOME is not None:
        env["XDG_DATA_HOME"] = str(UDB_DATA_HOME)
        env.setdefault("MISE_DATA_DIR", str(Path.home() / ".local/share/mise"))
    return env


@cache
def udb_param_dir() -> Path:
    path = subprocess.run(
        ["bundle", "info", "udb", "--path"], env=bundle_env(), capture_output=True, text=True, check=True
    ).stdout.strip()
    return Path(path) / ".data/spec/std/isa/param"


def udb_validate(path: Path) -> list[tuple[str, list[str]]]:
    """UDB's complaints about a configuration, each with its failing conditions."""
    r = subprocess.run(
        ["bundle", "exec", "udb", "validate", "cfg", str(path)],
        env=bundle_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode == 0:
        return []
    errors: list[tuple[str, list[str]]] = []
    # udb 0.1.18 crashes, rather than reporting the parameter missing, when a parameter that
    # another check reads is absent (SXLEN with S, for example)
    for name in re.findall(r'param_values\["(\w+)"\]', r.stdout + r.stderr):
        errors.append((f"Parameter is required but missing: '{name}'", ["udb crashed reading it"]))
    if errors:
        return errors
    for line in (r.stdout + r.stderr).splitlines():
        if m := re.match(r"^\s*\* (.*)$", line):
            errors.append((m.group(1).strip(), []))
        elif (m := re.match(r"^\s+- (.*)$", line)) and errors:
            errors[-1][1].append(m.group(1).strip())
    return errors or [(" ".join((r.stdout + r.stderr).split())[:300], [])]


@cache
def typical_values(xlen: int) -> dict[str, Counter[str]]:
    """How often each value of each parameter appears in the ACT configurations of this XLEN."""
    counts: dict[str, Counter[str]] = {}
    for f in (REPO_ROOT / "config").glob("**/*.yaml"):
        if f.name == "test_config.yaml" or f.name.startswith("ci"):
            continue
        doc = load_yaml(f.read_text())
        if not isinstance(doc, dict) or doc.get("kind") != "architecture configuration":
            continue
        params = doc.get("params") or {}
        if params.get("MXLEN") != xlen:
            continue
        for name, value in params.items():
            counts.setdefault(name, Counter())[json.dumps(value)] += 1
    return counts


def schema_value(name: str, xlen: int) -> object:
    """A legal value from the parameter's schema, for parameters no ACT configuration sets."""
    doc = load_yaml((udb_param_dir() / f"{name}.yaml").read_text())
    schema = doc.get("schema", {})
    if "oneOf" in schema:
        schema = (
            next(
                (s for s in schema["oneOf"] if s.get("when", {}).get("param", {}).get("equal") in (xlen, None)),
                schema["oneOf"][0],
            )["schema"]
            if "schema" in schema["oneOf"][0]
            else schema["oneOf"][0]
        )
    if "enum" in schema:
        return schema["enum"][0]
    if "const" in schema:
        return schema["const"]
    kind = schema.get("type")
    if kind == "boolean":
        return False
    if kind == "integer":
        return schema.get("minimum", 0)
    if kind == "string":
        return ""
    if kind == "array":
        items = schema.get("items", {})
        n = schema.get("minItems", 0)
        item = items.get("enum", [False if items.get("type") == "boolean" else 0])[0]
        return [item] * n
    return None


def fill_values(name: str, xlen: int) -> list[tuple[Any, str]]:
    """Candidate values for a parameter the extractor did not determine, most likely first."""
    counts = typical_values(xlen).get(name, Counter())
    total = sum(counts.values())
    out = [
        (json.loads(v), f"assumed: not extracted; the value {n} of {total} RV{xlen} ACT configurations use")
        for v, n in counts.most_common()
    ]
    return out + [(schema_value(name, xlen), "assumed: not extracted; a legal value from the UDB schema")]


def yaml_value(v: object) -> str:
    return (
        json.dumps(v)
        if not isinstance(v, str)
        else (v if re.fullmatch(r"[A-Za-z][\w ./()-]*", v) and v not in ("true", "false") else json.dumps(v))
    )


def render_yaml(
    name: str,
    description: str,
    header: list[str],
    ext_lines: list[str],
    params: dict[str, Any],
    notes: dict[str, str],
    dropped: list[str],
) -> str:
    lines = [
        "# yaml-language-server: $schema=https://raw.githubusercontent.com/riscv/riscv-unified-db/main/spec/schemas/config_schema.json"
    ]
    lines += [f"# {h}" for h in header]
    lines += [
        "---",
        "$schema: config_schema.json#",
        "kind: architecture configuration",
        "type: fully configured",
        f"name: {name}",
        f"description: {json.dumps(description)}",
        "implemented_extensions:",
    ]
    lines += [f"  {e}" for e in ext_lines]
    lines.append("params:")
    measured = [n for n in params if n not in notes]
    assumed = [n for n in params if n in notes]
    lines += [f"  {n}: {yaml_value(params[n])}" for n in measured]
    if assumed:
        lines.append("  # The extractor could not determine these; check each against the DUT")
        lines += [f"  {n}: {yaml_value(params[n])}  # {notes[n]}" for n in assumed]
    if dropped:
        lines.append("  # Extracted but not accepted by UDB:")
        lines += [f"  # {d}" for d in dropped]
    return "\n".join(lines) + "\n"


def complete_yaml(
    out: Path, name: str, description: str, header: list[str], ext_lines: list[str], params: dict[str, Any], xlen: int
) -> tuple[dict[str, Any], dict[str, str], list[str], list[str]]:
    """Make UDB accept the configuration.

    Missing parameters are filled in; parameters that do not apply or that the schema rejects are
    dropped; an extension another one requires is added when the extractor cannot probe it, and an
    extension's version is raised when another one requires the later version.  Returns the
    params, a note for each assumption, the dropped values and the complaints that remain.
    """
    params = dict(params)
    notes: dict[str, str] = {}
    dropped: list[str] = []
    errors: list[tuple[str, list[str]]] = []
    exts = {re.search(r"name: (\w+)", e).group(1): e for e in ext_lines}  # type: ignore[union-attr]
    tried: dict[str, int] = {}

    def assume(name: str) -> bool:
        """Give an undetermined parameter its next candidate value; False when none is left."""
        candidates = fill_values(name, xlen)
        i = tried.get(name, -1) + 1
        if i >= len(candidates):
            return False
        tried[name] = i
        params[name], notes[name] = candidates[i]
        return True

    for _ in range(16):
        out.write_text(render_yaml(name, description, header, list(exts.values()), params, notes, dropped))
        errors = udb_validate(out)
        progress = False
        for e, conditions in errors:
            if (
                (m := re.match(r"Parameter is required but missing: '(\w+)'", e))
                or (m := re.match(r"Parameter requirements not met: '(\w+)'", e))
                and m.group(1) in notes
            ):
                progress |= assume(m.group(1))
            elif (
                m := re.match(
                    r"Parameter (value violates the schema|has no definition|is not defined by this config): '(\w+)'", e
                )
            ) and m.group(2) in params:
                why = m.group(1) + (f" ({'; '.join(conditions)})" if conditions else "")
                dropped.append(f"{m.group(2)}: {json.dumps(params.pop(m.group(2)))}: {why}")
                notes.pop(m.group(2), None)
                progress = True
            elif m := re.match(r"Extension requirement is unmet: (\w+)@", e):
                for c in conditions:
                    if (r := re.fullmatch(r"`(\w+)(~>|=|>=)([\d.]+)`\{false\}", c)) is None:
                        continue
                    ext, version = r.group(1), r.group(3) + ".0" * (2 - r.group(3).count("."))
                    if ext in exts:
                        exts[ext] = (
                            f'- {{ name: {ext}, version: "= {version}" }}  # assumed: {m.group(1)} requires {ext} {version}'
                        )
                    else:
                        exts[ext] = f'- {{ name: {ext}, version: "= {version}" }}  # assumed: {m.group(1)} requires it'
                    progress = True
        if not errors or not progress:
            break
    ext_lines[:] = list(exts.values())
    return params, notes, dropped, [e + (": " + "; ".join(c) if c else "") for e, c in errors]


# ---------------------------------------------------------------------------------------------


def make_config(config_dir: Path, out_dir: Path, timeout: int, sim: str = "sail_riscv_sim") -> dict[str, Any]:
    global UDB_DATA_HOME
    config_dir = config_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if UDB_DATA_HOME is None:
        UDB_DATA_HOME = out_dir.resolve() / "udb-data"
    test_config = load_yaml((config_dir / "test_config.yaml").read_text())
    name = test_config.get("name", config_dir.name)
    build = out_dir / "build"

    xlen = detect_xlen(config_dir, test_config, build, timeout)
    elf = make("elf", build / "extractor", test_config, config_dir, xlen)
    text = run_on_dut(config_dir, elf, out_dir / "extractor_output.txt", timeout)
    ext_lines, params, sail_extra, comments = parse_output(text)
    if not ext_lines:
        raise RuntimeError(f"the extractor reported nothing; see {out_dir}/extractor_output.txt")

    header = [
        (
            f"Generated by tests-dev/priv/UDBFeatureExtractor/make_config.py from {config_dir.relative_to(REPO_ROOT)} "
            f"on {datetime.date.today()}"
        ),
        *(c[2:] for c in comments),
    ]
    yaml_path = out_dir / f"{name}.yaml"
    params, notes, dropped, errors = complete_yaml(
        yaml_path, name, f"{name}, generated by the UDB feature extractor", header, ext_lines, params, xlen
    )
    if errors:
        header += [f"UDB rejects this configuration: {e}" for e in errors]
        yaml_path.write_text(
            render_yaml(
                name, f"{name}, generated by the UDB feature extractor", header, ext_lines, params, notes, dropped
            )
        )

    (out_dir / "sail_extra.json").write_text(json.dumps(sail_extra, indent=2) + "\n")
    sail_text, _, conv, _ = udb_to_sail.convert_file(yaml_path, config_dir, sail_extra, sim)
    sail_path = out_dir / "sail.json"
    sail_path.write_text(sail_text)
    sail_error = udb_to_sail.validate(sail_path, sim)
    return {
        "name": name,
        "xlen": xlen,
        "yaml": yaml_path,
        "sail": sail_path,
        "assumed": notes,
        "dropped": dropped,
        "udb_errors": errors,
        "sail_error": sail_error,
        "sail_defaulted": conv.defaulted(),
        "sail_unmodelled": conv.unmodelled,
        "sail_extra": sail_extra,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config-dir", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--timeout", type=int, default=3600, help="seconds allowed per DUT run")
    ap.add_argument("--sim", default="sail_riscv_sim", help="Sail executable for the default configuration")
    args = ap.parse_args()
    r = make_config(args.config_dir, args.out_dir, args.timeout, args.sim)
    print(f"{r['yaml']}: RV{r['xlen']}, {len(r['assumed'])} parameters assumed, {len(r['dropped'])} dropped")
    for e in r["udb_errors"]:
        print(f"  UDB: {e}")
    print(
        f"{r['sail']}: {len(r['sail_defaulted'])} keys at Sail's default, {len(r['sail_unmodelled'])} not expressible"
    )
    if r["sail_error"]:
        print(f"  Sail rejects it: {r['sail_error']}")
    sys.exit(1 if r["udb_errors"] or r["sail_error"] else 0)


if __name__ == "__main__":
    main()
