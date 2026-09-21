#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 RISC-V International
#
# Regression for the UDB feature extractor.
#
# Adapted by David Harris from the original by Jayant Malvi (riscv-arch-test #1655),
# with assistance from Claude.
#
# For every configuration directory under config/ that has a run_cmd.txt and a UDB yaml, builds
# the extractor against that directory's link.ld and rvmodel_macros.h, runs it with the run_cmd.txt
# command, and compares the extensions it reports with the yaml's implemented_extensions.
# Configurations whose simulator is not on PATH are skipped.  Names only are compared: the
# extractor cannot see versions, and the untested extensions it names in its output header are
# reported separately rather than as mismatches.

import argparse
import concurrent.futures
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import yaml

# name, status ("ok", "FAIL" or "skip"), note, reported, expected, untested
# params: (matched, mismatched {name: (extracted, expected)}, not extracted, extra)
Params = tuple[set[str], dict[str, tuple[object, object]], set[str], set[str]]
NO_PARAMS: Params = (set(), {}, set(), set())
Result = tuple[str, str, str, set[str], set[str], set[str], Params]

DEBUG_PLACEHOLDER_RE = re.compile(r"\{debug:([^}]*)\}")

# How to make each simulator write the extractor's console output to a file; anything else is
# expected to print it on stdout
CONSOLE_FLAGS = {
    "sail_riscv_sim": "--terminal-log {out}",
    "wsim": "--args '+UART_LOG=1 +UART_LOG_FILE={out}'",
}


# Extensions defined as exactly a set of others: a yaml that lists the members but not the name is
# not contradicted when the extractor reports the name, so such an extra is listed as implied
IMPLIED = {
    "A": {"Zaamo", "Zalrsc"},
    "B": {"Zba", "Zbb", "Zbs"},
    "Zkn": {"Zbkb", "Zbkc", "Zbkx", "Zkne", "Zknd", "Zknh"},
    "Zks": {"Zbkb", "Zbkc", "Zbkx", "Zksed", "Zksh"},
    "Zbkc": {"Zbc"},
}


def find_configs(root: Path) -> Iterator[tuple[Path, Path]]:
    for run_cmd in sorted((root / "config").glob("**/run_cmd.txt")):
        d = run_cmd.parent
        yamls = [y for y in d.glob("*.yaml") if y.name != "test_config.yaml"]
        if len(yamls) == 1:
            yield d, yamls[0]


def expected_extensions(udb_yaml: Path) -> tuple[set[str], int, dict]:
    doc = yaml.safe_load(udb_yaml.read_text())
    names = set()
    for e in doc.get("implemented_extensions", []):
        names.add(e["name"] if isinstance(e, dict) else str(e))
    params = doc.get("params") or {}
    return names, int(params.get("MXLEN", 64)), params


def compare_params(text: str, expected: dict) -> Params:
    """Compare the params section of the extracted yaml with the configuration's."""
    # Simulators that print to stdout surround the yaml with their own messages, and some
    # prefix every line with a timestamp such as "[123 ns] "
    text = "\n".join(re.sub(r"^\[\s*\d+ [a-z]+\] ", "", l) for l in text.splitlines())
    yaml_text = "\n".join(l for l in text.splitlines() if re.match(r"^(#|params:|implemented_extensions:|  )", l))
    # A simulator that stops on a cycle limit can cut the last line; drop a truncated tail
    extracted = None
    for _ in range(8):
        try:
            extracted = (yaml.safe_load(yaml_text) or {}).get("params") or {}
            break
        except yaml.YAMLError:
            yaml_text = yaml_text[: yaml_text.rstrip("\n").rfind("\n")]
    if extracted is None:
        return NO_PARAMS
    matched, mismatched = set(), {}
    for name, value in extracted.items():
        if name in expected:
            if value == expected[name]:
                matched.add(name)
            else:
                mismatched[name] = (value, expected[name])
    return matched, mismatched, set(expected) - set(extracted), set(extracted) - set(expected)


def run_config(root: Path, build: Path, makefile: Path, config_dir: Path, udb_yaml: Path, timeout: int) -> Result:
    name = config_dir.name
    expected, xlen, expected_params = expected_extensions(udb_yaml)
    work = build / name
    work.mkdir(parents=True, exist_ok=True)
    log = work / "build.log"
    with log.open("w") as f:
        rc = subprocess.run(
            ["make", "-f", str(makefile), "elf", f"XLEN={xlen}", f"CONFIG_DIR={config_dir}", f"BUILD_DIR={work}"],
            stdout=f,
            stderr=subprocess.STDOUT,
            cwd=root,
            check=False,
        ).returncode
    if rc:
        return name, "FAIL", f"build failed, see {log}", set(), expected, set(), NO_PARAMS
    elf = work / f"feature_extractor{xlen}.elf"

    # A run_cmd.txt may start with VAR=value environment settings, as the shell would accept
    command = DEBUG_PLACEHOLDER_RE.sub("", (config_dir / "run_cmd.txt").read_text()).split()
    env = dict(os.environ)
    while command and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", command[0]):
        var, value = command.pop(0).split("=", 1)
        env[var] = value
    if not command or shutil.which(command[0]) is None:
        return (
            name,
            "skip",
            f"{command[0] if command else 'run_cmd.txt'} not on PATH",
            set(),
            expected,
            set(),
            NO_PARAMS,
        )
    out = work / "extracted_config.yaml"
    out.unlink(missing_ok=True)
    # Console flags go right after the executable: some commands end with the option that takes
    # the ELF (wsim --elf, qemu -bios)
    flags = CONSOLE_FLAGS.get(Path(command[0]).name)
    if flags:
        command[1:1] = shlex.split(flags.format(out=out))
    command.append(str(elf))
    log = work / "run.log"
    try:
        with log.open("w") as f:
            proc = subprocess.run(
                command, stdout=f, stderr=subprocess.STDOUT, cwd=root, env=env, timeout=timeout, check=False
            )
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        return name, "FAIL", f"timed out after {timeout}s, see {log}", set(), expected, set(), NO_PARAMS
    text = out.read_text() if out.exists() else log.read_text()
    if not out.exists():
        out.write_text(text)
    text = "\n".join(re.sub(r"^\[\s*\d+ [a-z]+\] ", "", l) for l in text.splitlines())
    reported = set(re.findall(r"^\s*- \{ name: (\w+),", text, re.MULTILINE))
    untested = set()
    for m in re.finditer(r"^# untested: (.*)$", text, re.MULTILINE):
        untested |= set(m.group(1).split())
    problems = [l for l in text.splitlines() if l.startswith(("# warning", "# FATAL"))]
    if not reported:
        return name, "FAIL", f"nothing reported (exit {rc}), see {log}", set(), expected, set(), NO_PARAMS
    status = "ok"
    notes = []
    if problems:
        status = "FAIL"
        notes += problems
    return name, status, "; ".join(notes), reported, expected, untested, compare_params(text, expected_params)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", required=True)
    p.add_argument("--build-dir", required=True)
    p.add_argument("--jobs", "-j", type=int, default=1, help="configurations to run in parallel")
    p.add_argument("--timeout", type=int, default=3600, help="seconds allowed per simulator run")
    p.add_argument("--configs", default="", help="comma-separated configuration names to run (default all)")
    args = p.parse_args()

    root = Path(args.repo_root).resolve()
    build = Path(args.build_dir).resolve()
    makefile = root / "tests-dev/priv/UDBFeatureExtractor/Makefile"
    wanted = set(args.configs.split(",")) if args.configs else None
    configs = [(d, y) for d, y in find_configs(root) if wanted is None or d.name in wanted]
    if not configs:
        print("no configurations found")
        sys.exit(1)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_config, root, build, makefile, d, y, args.timeout) for d, y in configs]
        results = [f.result() for f in futures]

    width = max(len(r[0]) for r in results)
    failures = 0
    total_matched = total_mismatched = total_untested = 0
    p_matched = p_mismatched = p_missing = 0
    for name, status, note, reported, expected, untested, params in results:
        if status == "skip":
            print(f"skip {name:{width}}  {note}")
            continue
        matched = expected & reported
        missing = expected - reported - untested
        extra = reported - expected
        implied = {n for n in extra if n in IMPLIED and IMPLIED[n] <= expected}
        extra -= implied
        untested_expected = expected & untested
        if missing or extra:
            status = "FAIL"
        if status == "FAIL":
            failures += 1
        total_matched += len(matched)
        total_mismatched += len(missing) + len(extra)
        total_untested += len(untested_expected)
        line = f"{status:4} {name:{width}}  {len(matched):3} of {len(expected):3} match"
        if untested_expected:
            line += f", {len(untested_expected)} untested"
        if missing:
            line += "  missing: " + " ".join(sorted(missing))
        if extra:
            line += "  extra: " + " ".join(sorted(extra))
        if implied:
            line += "  implied: " + " ".join(sorted(implied))
        if note:
            line += "  " + note
        pm, pmis, pmissing, pextra = params
        if pmis and status != "FAIL":
            status = "FAIL"
            failures += 1
            line = "FAIL" + line[4:]
        print(line)
        if pm or pmis or pmissing:
            p_matched += len(pm)
            p_mismatched += len(pmis)
            p_missing += len(pmissing)
            pline = f"     params: {len(pm):3} of {len(pm) + len(pmis) + len(pmissing):3} match, {len(pmissing)} not extracted"
            if pmis:
                pline += "  mismatched: " + " ".join(
                    f"{n} (extracted {v!r}, yaml {e!r})" for n, (v, e) in sorted(pmis.items())
                )
            if pextra:
                pline += "  extra: " + " ".join(sorted(pextra))
            print(pline)
    ran = sum(1 for r in results if r[1] != "skip")
    print(
        f"{ran} configurations run, {len(results) - ran} skipped: {total_matched} extensions match, "
        f"{total_mismatched} mismatch, {total_untested} untested; "
        f"{p_matched} parameters match, {p_mismatched} mismatch, {p_missing} not extracted"
    )
    print("all configurations match" if not failures else f"{failures} configuration(s) FAILED")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
