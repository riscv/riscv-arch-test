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
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import make_config

# name, status ("ok", "FAIL" or "skip"), note, reported, expected, untested
# params: (matched, mismatched {name: (extracted, expected)}, not extracted, extra)
Params = tuple[set[str], dict[str, tuple[object, object]], set[str], set[str]]
NO_PARAMS: Params = (set(), {}, set(), set())
Result = tuple[str, str, str, set[str], set[str], set[str], Params]


def expected_extensions(udb_yaml: Path) -> tuple[set[str], int, dict]:
    doc = make_config.load_yaml(udb_yaml.read_text())
    names = set()
    for e in doc.get("implemented_extensions", []):
        names.add(e["name"] if isinstance(e, dict) else str(e))
    params = doc.get("params") or {}
    return names, int(params.get("MXLEN", 64)), params


def compare_params(text: str, expected: dict) -> Params:
    """Compare the params section of the extracted yaml with the configuration's."""
    extracted = make_config.parse_output(text)[1]
    matched, mismatched = set(), {}
    for name, value in extracted.items():
        if name in expected:
            if value == expected[name]:
                matched.add(name)
            else:
                mismatched[name] = (value, expected[name])
    return matched, mismatched, set(expected) - set(extracted), set(extracted) - set(expected)


def run_config(build: Path, config_dir: Path, udb_yaml: Path, timeout: int) -> Result:
    name = config_dir.name
    expected, xlen, expected_params = expected_extensions(udb_yaml)
    work = build / name
    test_config = make_config.load_yaml((config_dir / "test_config.yaml").read_text())
    try:
        elf = make_config.make("elf", work, test_config, config_dir, xlen)
    except subprocess.CalledProcessError:
        return name, "FAIL", "build failed", set(), expected, set(), NO_PARAMS
    out = work / "extracted_config.yaml"
    try:
        text, timed_out = make_config.run_on_dut_ex(config_dir, elf, out, timeout)
    except FileNotFoundError as e:
        return name, "skip", str(e), set(), expected, set(), NO_PARAMS
    log = out.with_suffix(".log")
    if timed_out:
        return name, "FAIL", f"timed out after {timeout}s, see {log}", set(), expected, set(), NO_PARAMS
    out.write_text(text)
    reported = set(re.findall(r"^\s*- \{ name: (\w+),", text, re.MULTILINE))
    untested = make_config.untested_extensions(text)
    problems = [l for l in text.splitlines() if l.startswith(("# warning", "# FATAL"))]
    if not reported:
        return name, "FAIL", f"nothing reported, see {log}", set(), expected, set(), NO_PARAMS
    status = "ok"
    notes = []
    if problems:
        status = "FAIL"
        notes += problems
    return name, status, "; ".join(notes), reported, expected, untested, compare_params(text, expected_params)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--build-dir", required=True)
    p.add_argument("--jobs", "-j", type=int, default=1, help="configurations to run in parallel")
    p.add_argument("--timeout", type=int, default=3600, help="seconds allowed per simulator run")
    p.add_argument("--configs", default="", help="comma-separated configuration names to run (default all)")
    args = p.parse_args()

    build = Path(args.build_dir).resolve()
    wanted = set(args.configs.split(",")) if args.configs else None
    configs = [(d, y) for d, y in make_config.find_configs() if wanted is None or d.name in wanted]
    if not configs:
        print("no configurations found")
        sys.exit(1)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_config, build, d, y, args.timeout) for d, y in configs]
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
        implied = {n for n in extra if n in make_config.IMPLIED and make_config.IMPLIED[n] <= expected}
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
