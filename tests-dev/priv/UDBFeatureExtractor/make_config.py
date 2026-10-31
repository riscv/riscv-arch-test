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
#   2. Build the extractor for that XLEN and run it with run_cmd.txt.  If the run stops before the
#      extractor's last line (a probe hung, or the simulator stopped on an assertion), rebuild it to
#      name each probe as it starts, then leave out the probe the run stopped in, until it finishes.
#   3. Write <name>.yaml: the extensions and parameters the extractor reported, then every parameter
#      UDB still requires, filled with the value most ACT configurations use and marked as assumed,
#      until `udb validate cfg` accepts the file.
#   4. Write sail.json from the yaml with udb_to_sail.py, adding the Sail-only values the extractor
#      measured ("# sail:" lines).

from __future__ import annotations

import argparse
import contextlib
import datetime
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
from collections import Counter
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import udb_to_sail

import run_tests

SRC_DIR = Path(__file__).resolve().parent
REPO_ROOT = SRC_DIR.parents[2]
GEMFILE = REPO_ROOT / "framework/src/act/data/Gemfile"

TIMESTAMP_RE = re.compile(r"^\[\s*\d+ [a-z]+\] ")
# How to make each simulator write the console output to a file; anything else prints it on stdout
CONSOLE_FLAGS = {
    "sail_riscv_sim": "--terminal-log {out}",
    "wsim": "--args '+UART_LOG=1 +UART_LOG_FILE={out}'",
}


# Extensions defined as exactly a set of others: a yaml that lists the members but not the name is
# not contradicted when the extractor reports the name (used by the regressions in test/)
IMPLIED = {
    "A": {"Zaamo", "Zalrsc"},
    "B": {"Zba", "Zbb", "Zbs"},
    "Zkn": {"Zbkb", "Zbkc", "Zbkx", "Zkne", "Zknd", "Zknh"},
    "Zks": {"Zbkb", "Zbkc", "Zbkx", "Zksed", "Zksh"},
    "Zbkc": {"Zbc"},
}


def load_yaml(text: str) -> dict[str, Any]:
    """Parse yaml; ruamel's YAML objects are not thread-safe, so each call makes its own."""
    return YAML(typ="safe").load(text)


def find_configs() -> list[tuple[Path, Path]]:
    """Every configuration directory under config/ with a run_cmd.txt and one UDB yaml."""
    out = []
    for run_cmd in sorted((REPO_ROOT / "config").glob("**/run_cmd.txt")):
        d = run_cmd.parent
        yamls = [y for y in d.glob("*.yaml") if y.name != "test_config.yaml"]
        if len(yamls) == 1:
            out.append((d, yamls[0]))
    return out


def untested_extensions(text: str) -> set[str]:
    """The extensions the extractor's output lists as not looked for."""
    untested: set[str] = set()
    for m in re.finditer(r"^# untested: (.*)$", text, re.MULTILINE):
        untested |= set(m.group(1).split())
    return untested


# ---------------------------------------------------------------------------------------------
# Running on the DUT


def run_on_dut(config_dir: Path, elf: Path, out: Path, timeout: int) -> str:
    """Run an ELF with the configuration's run_cmd.txt and return its console output."""
    return run_on_dut_ex(config_dir, elf, out, timeout)[0]


def run_on_dut_ex(config_dir: Path, elf: Path, out: Path, timeout: int) -> tuple[str, bool]:
    """run_on_dut, also saying whether the run was stopped for taking longer than timeout seconds."""
    run_cmd = run_tests._expand_debug_placeholders((config_dir / "run_cmd.txt").read_text(), debug=False)
    env_overrides, command = run_tests.split_env_assignments(shlex.split(run_cmd))
    env = {**os.environ, **env_overrides}
    if not command or shutil.which(command[0]) is None:
        raise FileNotFoundError(f"{command[0] if command else 'run_cmd.txt'} not on PATH")
    out.unlink(missing_ok=True)
    flags = CONSOLE_FLAGS.get(Path(command[0]).name)
    if flags:
        command[1:1] = shlex.split(flags.format(out=out))
    command.append(str(elf))
    log = out.with_suffix(".log")
    timed_out = False
    # The run command is often a script that starts the simulator as a child, so a timeout stops
    # the whole process group; otherwise the simulator keeps running after the script is killed.
    with log.open("w") as f:
        proc = subprocess.Popen(
            command, stdout=f, stderr=subprocess.STDOUT, cwd=REPO_ROOT, env=env, start_new_session=True
        )
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGTERM)
            with contextlib.suppress(subprocess.TimeoutExpired):
                proc.wait(timeout=10)
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
    text = out.read_text(errors="replace") if out.exists() and out.stat().st_size else log.read_text(errors="replace")
    if (
        re.search(r"no simulator at|not found|No such file or directory", log.read_text(errors="replace"))
        and "# " not in text
    ):
        raise FileNotFoundError(f"{command[0]} could not start its simulator; see {log}")
    return "\n".join(TIMESTAMP_RE.sub("", line) for line in text.splitlines()), timed_out


def make(target: str, build: Path, test_config: dict[str, Any], config_dir: Path, xlen: int, cflags: str = "") -> Path:
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
            f"EXTRA_CFLAGS={cflags}",
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


END_MARK = "# end of extractor output"
MAX_SKIPS = 8


def stopped_after(text: str, out_dir: Path) -> str:
    """Where a run that got past the extension probes stopped."""
    last = next((line.strip() for line in reversed(text.splitlines()) if re.match(r"^  [A-Z0-9_]+: ", line)), "")
    return (
        "the run stopped after the extension probes"
        + (f", after printing {last.split(':')[0]}" if last else "")
        + f" (a hang there, or a cycle or time limit); see {out_dir / 'extractor_output.log'}"
    )


def run_extractor(
    config_dir: Path, test_config: dict[str, Any], xlen: int, out_dir: Path, timeout: int
) -> tuple[str, list[str], str]:
    """Run the extractor until it finishes, leaving out each probe that stops the run.

    Returns its output, the probes left out, and why it did not finish ("" when it did).  The first
    run is untraced; when it stops early the extractor is rebuilt with TRACE_PROBES, which prints
    "# probe: NAME" before each extension probe, so the last such line names the probe the run
    stopped in.  That probe is then run by itself (ONLY_PROBE): if it finishes alone, the run
    ran into a cycle or time limit rather than a hang, and nothing is left out.  A run that stops
    after the extension probes cannot be helped this way, and neither can one that took longer
    than the timeout on a DUT with the watchdog, which would have stopped a hanging probe.
    """
    limit = "the simulator probably hit a cycle or time limit; raise it (run_cmd.txt, or --timeout)"
    skips: list[str] = []
    trace = False
    text = first = ""
    for attempt in range(MAX_SKIPS + 2):
        flags = ["-DTRACE_PROBES"] if trace else []
        if skips:
            flags.append(f"-DSKIP_PROBES='\"{','.join(skips)}\"'")
        build = out_dir / "build" / ("extractor" if attempt == 0 else f"extractor-retry{attempt}")
        elf = make("elf", build, test_config, config_dir, xlen, " ".join(flags))
        text, timed_out = run_on_dut_ex(config_dir, elf, out_dir / "extractor_output.txt", timeout)
        if END_MARK in text:
            return text, skips, ""
        if timed_out and "# watchdog: a probe" in text:
            return text, skips, f"the run took longer than {timeout} s with the watchdog on, so {limit}"
        if not trace:
            if "implemented_extensions:" in text:  # past every probe that can be left out
                return text, skips, stopped_after(text, out_dir)
            first = text
            trace = True
            continue
        lines = text.splitlines()
        started = [i for i, line in enumerate(lines) if line.startswith("# probe: ")]
        if not started or any(line.startswith("implemented_extensions:") for line in lines[started[-1] :]):
            # tracing slows a run down, so a run that stops on a limit may get less far traced
            best = max((text, first), key=lambda t: len(re.findall(r"^  [A-Z0-9_]+: ", t, re.MULTILINE)))
            return best, skips, stopped_after(best, out_dir)
        name = lines[started[-1]].split()[2]
        if name in skips:
            break
        alone = make(
            "elf", out_dir / "build" / f"only-{name}", test_config, config_dir, xlen, f"-DONLY_PROBE='\"{name}\"'"
        )
        if END_MARK in run_on_dut(config_dir, alone, out_dir / f"only-{name}.txt", timeout):
            return text, skips, f"the run stopped in the {name} probe, which finishes when run alone, so {limit}"
        skips.append(name)
    return text, skips, f"the run still stops after leaving out {', '.join(skips)}"


# ---------------------------------------------------------------------------------------------
# The extractor's output


def parse_output(text: str) -> tuple[list[str], dict[str, Any], dict[str, Any], list[str]]:
    """Return the extension lines, the params, the "# sail:" values and the header comments."""
    ext_lines = re.findall(r"^\s*- \{ name: \w+, version: \"[^\"]*\" \}$", text, re.MULTILINE)
    sail: dict[str, Any] = {}
    for key, value in re.findall(r"^# sail: ([\w.]+): (.*)$", text, re.MULTILINE):
        sail[key] = json.loads(value)
    comments = [
        line
        for line in text.splitlines()
        if re.match(r"^# (untested|watchdog|note|warning|FATAL|sail-unmodelled|  )", line)
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


def bundle(*args: str) -> list[str]:
    """A bundle command line.  The repository's mise configuration chooses the Ruby, and mise puts
    it on PATH only inside the repository, so go through `mise exec` when mise is installed."""
    return ["mise", "exec", "--", "bundle", *args] if shutil.which("mise") else ["bundle", *args]


@cache
def udb_param_dir() -> Path:
    path = subprocess.run(
        bundle("info", "udb", "--path"), env=bundle_env(), cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    return Path(path) / ".data/spec/std/isa/param"


def udb_validate(path: Path) -> list[tuple[str, list[str]]]:
    """UDB's complaints about a configuration, each with its failing conditions."""
    r = subprocess.run(
        bundle("exec", "udb", "validate", "cfg", str(path.resolve())),
        env=bundle_env(),
        cwd=REPO_ROOT,  # mise chooses the Ruby by directory
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

        def first(item: dict[str, Any]) -> object:
            return item.get("enum", [False if item.get("type") == "boolean" else item.get("minimum", 0)])[0]

        if isinstance(items, list):  # one schema per position
            return [first(i) for i in items][: max(n, len(items))]
        return [first(items)] * n
    return None


# Parameters no probe can measure that get a fixed value instead of the one most configurations
# use: imprecise exceptions cannot be told from precise ones, and the bit that would select
# imprecise vector traps is not a standard CSR field.
FIXED = {
    "PRECISE_SYNCHRONOUS_EXCEPTIONS": False,
    "IMPRECISE_VECTOR_TRAP_SETTABLE": False,
}


def fill_values(name: str, xlen: int) -> list[tuple[Any, str]]:
    """Candidate values for a parameter the extractor did not determine, most likely first."""
    if name in FIXED:
        return [(FIXED[name], "assumed: not measurable; the extractor's fixed value")]
    counts = typical_values(xlen).get(name, Counter())
    total = sum(counts.values())
    out = [
        (json.loads(v), f"assumed: not extracted; the value {n} of {total} RV{xlen} ACT configurations use")
        for v, n in counts.most_common()
    ]
    return out + [(schema_value(name, xlen), "assumed: not extracted; a legal value from the UDB schema")]


@cache
def never_measurable() -> tuple[frozenset[str], frozenset[str]]:
    """The UDB parameters and Sail keys parameters_not_extracted.md says no probe measures."""
    text = (SRC_DIR / "parameters_not_extracted.md").read_text()

    def section(title: str) -> str:
        return text.split(f"## {title}", 1)[1].split("\n## ", 1)[0]

    udb = frozenset(re.findall(r"`([A-Z][A-Z0-9_]+)`", section("Not measurable from a single hart in M-mode")))
    sail = frozenset(re.findall(r"`([a-z][\w.]+)`", section("Sail keys not measured")))
    return udb, sail


def json_key_lines(text: str) -> dict[str, int]:
    """Line number of each key in JSON written with two-space indentation, by dotted path."""
    out: dict[str, int] = {}
    stack: list[str] = []
    for number, line in enumerate(text.splitlines(), 1):
        if m := re.match(r'^( +)"([^"]+)":', line):
            depth = len(m.group(1)) // 2
            stack = [*stack[: depth - 1], m.group(2)]
            out.setdefault(".".join(stack), number)
    return out


def ranges(numbers: list[int]) -> str:
    """1,2,3,7 -> 1-3,7"""
    out: list[str] = []
    for n in sorted(numbers):
        if out and int(out[-1].split("-")[-1]) == n - 1:
            out[-1] = f"{out[-1].split('-')[0]}-{n}"
        else:
            out.append(str(n))
    return ",".join(out)


def manual_checks(r: dict[str, Any]) -> list[str]:
    """Where in the generated files a person has to check or fix something, one line each."""
    out: list[str] = []
    yaml_path, sail_path = Path(r["yaml"]), Path(r["sail"])
    try:
        yp, sp = yaml_path.relative_to(Path.cwd()), sail_path.relative_to(Path.cwd())
    except ValueError:
        yp, sp = yaml_path, sail_path
    lines = yaml_path.read_text().splitlines()
    never_udb, never_sail = never_measurable()

    def where(pred: Callable[[str], bool]) -> list[int]:
        return [i for i, line in enumerate(lines, 1) if pred(line)]

    def names(nums: list[int]) -> str:
        found = [re.match(r"^\s*#?\s*-?\s*\{?\s*(?:name: )?(\w+)", lines[i - 1]) for i in nums]
        return ", ".join(m.group(1) for m in found if m)

    for i in where(lambda line: line.startswith("# warning:")):
        warning = lines[i - 1][len("# warning: ") :]
        j = i
        while j < len(lines) and re.match(r"^#  {2,}\S", lines[j]):
            warning += " " + lines[j][1:].strip()
            j += 1
        out.append(f"{yp}:{i}: {warning}")
    for i in where(lambda line: line.startswith("# watchdog: none")):
        reason = re.sub(r"^# watchdog: none \((.*)\);.*$", r"\1", lines[i - 1])
        out.append(f"{yp}:{i}: no watchdog ({reason}), so a probe that hangs costs a rerun")
    for i in where(lambda line: line.startswith("# untested:")):
        out.append(f"{yp}:{i}: extensions the extractor cannot detect: add any the DUT implements")
    for i in where(lambda line: line.startswith("# UDB rejects")):
        out.append(f"{yp}:{i}: {lines[i - 1][2:]}")
    nums = where(lambda line: line.startswith("  - {") and "# assumed:" in line)
    if nums:
        out.append(f"{yp}:{ranges(nums)}: extensions added because another requires them: {names(nums)}")
    nums = where(lambda line: "# assumed:" in line and line.split(":")[0].strip() in never_udb)
    if nums:
        out.append(
            f"{yp}:{ranges(nums)}: no probe can measure these; set them from the DUT's documentation: {names(nums)}"
        )
    nums = where(
        lambda line: (
            "# assumed:" in line and not line.startswith("  - {") and line.split(":")[0].strip() not in never_udb
        )
    )
    if nums:
        out.append(
            f"{yp}:{ranges(nums)}: {len(nums)} parameters not determined on this DUT, given typical values; check each"
        )
    nums = where(lambda line: re.match(r"^  # [A-Z0-9_]+: ", line) is not None)
    if nums:
        out.append(
            f"{yp}:{ranges(nums)}: measured values UDB did not accept (the DUT may disagree with UDB): {names(nums)}"
        )

    out.sort(key=lambda item: int(re.split(r"[-,]", item[len(str(yp)) + 1 :].split(":")[0])[0]))
    text = sail_path.read_text()
    keys = json_key_lines(text)
    header = [i for i, line in enumerate(text.splitlines(), 1) if line.startswith("//")]
    if r["sail_defaulted"]:
        out.append(
            f"{sp}:{ranges(header)}: {len(r['sail_defaulted'])} keys left at Sail's default (listed there); check each"
        )
    for key in r["sail_defaulted"]:
        if any(key == k or key.startswith(k + ".") or key.endswith("." + k) for k in never_sail):
            out.append(f"{sp}:{keys.get(key, header[-1] if header else 1)}: {key}: no probe can measure it")
    if r["sail_unmodelled"]:
        out.append(f"{sp}:{ranges(header)}: UDB values Sail cannot express (listed there)")
    return out


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
    never = [n for n in assumed if n in never_measurable()[0]]
    rest = [n for n in assumed if n not in never]
    if never:
        lines.append(
            "  # No probe can measure these (see parameters_not_extracted.md); set each from the DUT's documentation"
        )
        lines += [f"  {n}: {yaml_value(params[n])}  # {notes[n]}" for n in never]
    if rest:
        lines.append("  # The extractor did not determine these on this DUT; check each against the DUT")
        lines += [f"  {n}: {yaml_value(params[n])}  # {notes[n]}" for n in rest]
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
    untested = {n for h in header if h.startswith("untested:") for n in h.split()[1:]}

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
                    elif ext in untested:
                        # only an extension the extractor cannot look for may be added; one it found
                        # absent stays absent, and UDB's complaint is reported
                        exts[ext] = f'- {{ name: {ext}, version: "= {version}" }}  # assumed: {m.group(1)} requires it'
                    else:
                        continue
                    progress = True
        if not errors or not progress:
            break
    ext_lines[:] = list(exts.values())
    return params, notes, dropped, [e + (": " + "; ".join(c) if c else "") for e, c in errors]


# ---------------------------------------------------------------------------------------------


def make_config(config_dir: Path, out_dir: Path, timeout: int, sim: str = "sail_riscv_sim") -> dict[str, Any]:
    global UDB_DATA_HOME
    config_dir = config_dir.resolve()
    out_dir = out_dir.resolve()  # the DUT runs in the repository root
    out_dir.mkdir(parents=True, exist_ok=True)
    if UDB_DATA_HOME is None:
        UDB_DATA_HOME = out_dir.resolve() / "udb-data"
    test_config = load_yaml((config_dir / "test_config.yaml").read_text())
    name = test_config.get("name", config_dir.name)
    build = out_dir / "build"

    xlen = detect_xlen(config_dir, test_config, build, timeout)
    text, skipped, incomplete = run_extractor(config_dir, test_config, xlen, out_dir, timeout)
    ext_lines, params, sail_extra, comments = parse_output(text)
    if not ext_lines:
        raise RuntimeError(f"the extractor reported nothing ({incomplete}); see {out_dir}/extractor_output.txt")
    if incomplete:
        comments.append(f"# warning: the extractor did not finish: {incomplete}; parameters after that are assumed")

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
        "skipped_probes": skipped,
        "incomplete": incomplete,
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
    checks = manual_checks(r)
    if checks:
        print("\nCheck or fix these by hand:")
        for c in checks:
            print(f"  {c}")
    sys.exit(1 if r["udb_errors"] or r["sail_error"] else 0)


if __name__ == "__main__":
    main()
