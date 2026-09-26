#!/usr/bin/env -S uv run
# SPDX-License-Identifier: Apache-2.0
#
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ruamel-yaml>=0.18.16",
# ]
# ///
"""
Mechanical review checks for one ACT suite.

Usage:
  review_checks.py <Suite> [--udb-param-dir DIR] [--ref-rv32 CFG] [--ref-rv64 CFG] [--metrics-csv FILE]

Run from the repository root after `EXTENSIONS=<Suite> make tests`. The trap and
coverage sections use build outputs in work/ when they exist (trap reports need DEBUG=True).
Every line printed is a lead to verify, not a confirmed finding.
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from ruamel.yaml import YAML

ROOT = Path.cwd()
PRIV_GEN_DIR = ROOT / "generators/testgen/src/testgen/priv/extensions"
GATE_RE = re.compile(r"^\s*[#`](?:ifdef|ifndef|elsif)\s+(\w+)|defined\s*\(\s*(\w+)\s*\)", re.MULTILINE)
DEFINE_RE = re.compile(r"^\s*[#`]define\s+(\w+)", re.MULTILINE)
BOOT_RE = re.compile(r"#define\s+(?:RVTEST_)?BOOT_TO_([MSU])MODE")
CG_RE = re.compile(r"\b([A-Za-z0-9][\w.]*_cg)\b")


def section(title: str, lines: list[str]) -> None:
    print(f"\n== {title}")
    for line in lines or ["ok"]:
        print(f"  {line}")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def find_generator(suite: str) -> list[Path]:
    pattern = re.compile(rf'add_priv_test_generator\(\s*"{re.escape(suite)}"')
    return [p for p in PRIV_GEN_DIR.rglob("*.py") if pattern.search(p.read_text())]


def find_tests(suite: str) -> list[Path]:
    return sorted(ROOT.glob(f"tests/priv/{suite}/*.S")) + sorted(ROOT.glob(f"tests/rv*/{suite}/*.S"))


def find_coverage_files(covergroups: set[str]) -> list[Path]:
    files = []
    for svh in ROOT.glob("coverpoints/**/*.svh"):
        text = svh.read_text(errors="replace")
        if any(re.search(rf"\bcovergroup\s+{cg}\b", text) for cg in covergroups):
            files.append(svh)
    return files


def check_sources(suite: str, generators: list[Path], tests: list[Path], covergroups: set[str]) -> list[str]:
    out = []
    unpriv = bool(list(ROOT.glob(f"testplans/{suite}.csv")))
    if not generators and not unpriv:
        out.append(f"no generator registers {suite!r} and no testplans/{suite}.csv exists")
        if tests:
            out.append(f"tests/.../{suite}/ is stale generated output; run `make clean tests` before reviewing")
    if not tests:
        out.append(f"no generated tests found; run `EXTENSIONS={suite} make tests`")
    defined = {
        cg for f in ROOT.glob("coverpoints/**/*.svh") for cg in re.findall(r"\bcovergroup\s+(\w+)", f.read_text())
    }
    for cg in sorted(covergroups - defined):
        out.append(f"tests reference covergroup {cg}, which no coverpoint file defines")
    return out


def check_suite_type(suite: str, tests: list[Path], generators: list[Path]) -> list[str]:
    out = []
    texts = {t: t.read_text(errors="replace") for t in tests}
    boots = {m for text in texts.values() for m in BOOT_RE.findall(text)}
    if not boots:
        boots = {m for g in generators for m in BOOT_RE.findall(g.read_text())}
    if len(boots) > 1:
        out.append(f"test files boot to different modes: {sorted(boots)}")
    boot = next(iter(boots)) if len(boots) == 1 else None
    priv = bool(list(ROOT.glob(f"tests/priv/{suite}/*.S"))) or bool(generators)
    m_name = suite.startswith("Sm") or suite.endswith("Sm") or "PMP" in suite
    su_name = suite.startswith(("Ss", "Sv", "Su")) or suite.endswith(("S", "U"))
    if priv and boot is None:
        out.append("privileged suite has no BOOT_TO_*MODE define")
    if boot == "M" and not m_name:
        out.append("boots to M-mode, but the name does not mark it as an M-mode suite")
    if boot in ("S", "U") and m_name:
        out.append(f"boots to {boot}-mode, but the name marks it as an M-mode suite")
    if boot in ("S", "U") and not su_name:
        out.append(f"boots to {boot}-mode, but the name does not follow the S/U suite naming rules")
    for path, text in texts.items():
        name = rel(path)
        if boot in ("S", "U") and "RVTEST_TSBI_GOTO_MMODE" in text:
            out.append(f"{name}: RVTEST_TSBI_GOTO_MMODE in a suite that boots to {boot}-mode")
        if not priv and "RVTEST_TSBI_" in text:
            out.append(f"{name}: RVTEST_TSBI_* call in an unprivileged suite")
        if re.search(r"\bRVTEST_GOTO_(?:MMODE|LOWER_MODE)\b", text):
            out.append(f"{name}: legacy RVTEST_GOTO_* macro")
    return out


def check_coverpoint_text(cov_files: list[Path]) -> list[str]:
    out = []
    commented = re.compile(
        r"^\s*//\s*(?:wildcard\s+|ignore_|illegal_)?bins\b|^\s*//\s*\w+\s*:\s*(?:cross|coverpoint)\b"
    )
    for f in cov_files:
        lines = f.read_text(errors="replace").splitlines()
        for n, line in enumerate(lines, 1):
            if commented.search(line):
                out.append(f"{rel(f)}:{n}: commented-out bin or coverpoint")
            elif re.search(r"\bignore_bins\b", line) and "//" not in line and "//" not in lines[n - 2]:
                out.append(f"{rel(f)}:{n}: ignore_bins without a reason comment on it or the line before")
    return out


def known_defines() -> set[str]:
    names: set[str] = set()
    for pattern in (
        "work/*/rvtest_config.h",
        "work/*/rvtest_config.svh",
        "tests/env/*.h",
        "framework/src/act/fcov/**/*.svh",
    ):
        for f in ROOT.glob(pattern):
            names.update(DEFINE_RE.findall(f.read_text(errors="replace")))
    return names


def check_guards(files: list[Path], udb_params: dict[str, set[str]]) -> list[str]:
    known = known_defines()
    if not any(ROOT.glob("work/*/rvtest_config.h")):
        return ["no work/*/rvtest_config.h yet; build any config once so extension macros can be checked"]
    out = []
    for f in files:
        text = f.read_text(errors="replace")
        for m in GATE_RE.finditer(text):
            name = m.group(1) or m.group(2)
            if name in known or name.startswith(("RVMODEL_", "__")):
                continue
            if name.startswith("UDB_") and any(name[4:].startswith(p) for p in udb_params):
                continue
            line = text.count("\n", 0, m.start()) + 1
            out.append(f"{rel(f)}:{line}: guard {name} is not defined by any config or header (typo?)")
    return sorted(set(out))


def defining_extensions(node: object) -> set[str]:
    """Collect every extension name in a UDB definedBy expression."""
    exts: set[str] = set()
    if isinstance(node, dict):
        ext = node.get("extension")
        if isinstance(ext, dict) and isinstance(ext.get("name"), str):
            exts.add(ext["name"])
        for value in node.values():
            exts |= defining_extensions(value)
    elif isinstance(node, list):
        for value in node:
            exts |= defining_extensions(value)
    return exts


def load_udb_params(param_dir: Path | None) -> dict[str, set[str]]:
    """Map each UDB parameter to the extensions that define it."""
    if param_dir is not None:
        yaml = YAML(typ="safe", pure=True)
        params: dict[str, set[str]] = {}
        for f in param_dir.glob("*.yaml"):
            data = yaml.load(f.read_text())
            params[data["name"]] = defining_extensions(data.get("definedBy", {}))
        return params
    gemdir = ROOT / "framework/src/act/data"
    result = subprocess.run(
        ["bundle", "exec", "udb", "list", "parameters", "-f", "json"],
        cwd=gemdir,
        capture_output=True,
        text=True,
        check=True,
    )
    return {
        e["name"]: set(re.findall(r"\b([A-Z][A-Za-z0-9]*)\s*(?:>=|<=|==|>|<)", e.get("exts", "")))
        for e in json.loads(result.stdout)
    }


def check_params(suite: str, tests: list[Path], files: list[Path], udb_params: dict[str, set[str]]) -> list[str]:
    out = []
    required: set[str] = set()
    for t in tests:
        m = re.search(r"#\s*REQUIRED_EXTENSIONS:\s*\[(.*)\]", t.read_text(errors="replace"))
        if m:
            required.update(re.findall(r"'(\w+)'", m.group(1)))
    # Focus on the extension the suite is named after; base modes (Sm, S, U) define dozens of parameters.
    prefixes = sorted((e for e in required if suite.startswith(e)), key=len, reverse=True)
    required = {prefixes[0]} if prefixes else required - {"I", "E"}
    used = set()
    for f in files:
        for token in set(re.findall(r"\bUDB_(\w+)", f.read_text(errors="replace"))):
            used.update(p for p in udb_params if token == p or token.startswith(p + "_"))
    mapped: set[str] = set()
    param_yaml = ROOT / f"coverpoints/param/{suite}.yaml"
    if param_yaml.exists():
        data = YAML(typ="safe", pure=True).load(param_yaml.read_text()) or {}
        mapped = {d["name"] for d in data.get("parameter_definitions", []) if "name" in d}
    else:
        out.append(f"no {rel(param_yaml)}")
    applicable = {p for p, exts in udb_params.items() if exts & required}
    out.append(f"extensions checked for parameters: {', '.join(sorted(required)) or 'none'}")
    unhandled = sorted(applicable - used - mapped)
    if unhandled:
        out.append(
            f"{len(unhandled)} parameters defined by these extensions are neither used nor mapped: {', '.join(unhandled)}"
        )
    for p in sorted(used - mapped):
        if "XLEN" not in p:
            out.append(f"{p}: used as UDB_{p}*, but missing from the param mapping")
    for p in sorted(mapped - set(udb_params)):
        out.append(f"{p}: in the param mapping, but not a UDB parameter")
    return out


def expand_braces(ref: str) -> list[str]:
    m = re.search(r"\{([^}]*)\}", ref)
    if not m:
        return [ref]
    return [x for alt in m.group(1).split(",") for x in expand_braces(ref[: m.start()] + alt.strip() + ref[m.end() :])]


REF_RE = re.compile(r"(\{[^}]*\}|\w+)/(\w*(?:\{[^}]*\}\w*)?)")


def covergroup_members() -> dict[str, set[str]]:
    """Map every covergroup in coverpoints/ to the coverpoint and cross names it defines."""
    members: dict[str, set[str]] = {}
    for f in ROOT.glob("coverpoints/**/*.svh"):
        text = f.read_text(errors="replace")
        for m in re.finditer(r"\bcovergroup\s+(\w+)(.*?)\bendgroup\b", text, re.DOTALL):
            members[m.group(1)] = set(re.findall(r"^\s*(\w+)\s*:\s*(?:coverpoint|cross)\b", m.group(2), re.MULTILINE))
    return members


def check_norm(suite: str, covergroups: set[str]) -> list[str]:
    files = {ROOT / f"coverpoints/norm/{suite}.yaml"}
    for f in ROOT.glob("coverpoints/norm/*.yaml"):
        if any(re.search(rf"\b{cg}\b", f.read_text(errors="replace")) for cg in covergroups):
            files.add(f)
    members = covergroup_members()
    out = []
    for norm in sorted(files):
        if not norm.exists():
            out.append(f"no {rel(norm)}")
            continue
        data = YAML(typ="safe", pure=True).load(norm.read_text()) or {}
        empty = 0
        for rule in data.get("normative_rule_definitions", []):
            refs = [r for r in rule.get("coverpoint", []) if r and r.strip()]
            if not refs:
                empty += 1
            for ref in refs:
                for m in REF_RE.finditer(ref):
                    for cg in expand_braces(m.group(1)):
                        if cg not in members:
                            if re.fullmatch(r"[A-Z]\w*_\w+", cg):
                                out.append(f"{rel(norm)}: {rule.get('name')}: covergroup {cg} does not exist")
                            continue
                        for cp in expand_braces(m.group(2)):
                            if cp not in members[cg]:
                                out.append(f"{rel(norm)}: {rule.get('name')}: {cg} has no coverpoint {cp}")
        if empty:
            out.append(f"{rel(norm)}: {empty} rules have no coverpoint (TODO)")
    return out


def trap_sequence(path: Path) -> list[str]:
    seq, mode, cause = [], "", ""
    for line in path.read_text(errors="replace").splitlines():
        if m := re.match(r"\s*Mode:\s*(\S+)", line):
            mode = m.group(1)
        elif m := re.match(r"\s*XCAUSE:\s*\S+\s*\((.*)\)", line):
            cause = m.group(1)
        elif m := re.match(r"\s*XEPC:\s*\S+\s*\((.*)\)", line):
            seq.append(f"{mode}:{cause}@{m.group(1)}")
    return seq


def check_traps(suite: str, priv: bool, ref32: str, ref64: str) -> list[str]:
    reports: dict[str, dict[str, Path]] = defaultdict(dict)
    for f in ROOT.glob(f"work/*/build/*/{suite}/*.sig.trap_report"):
        reports[f.parts[len(ROOT.parts) + 1]][f.name] = f
    if not reports:
        return ["no trap reports; build with DEBUG=True"]
    out = []
    for cfg, tests in sorted(reports.items()):
        for name, path in sorted(tests.items()):
            seq = trap_sequence(path)
            if not priv and seq:
                out.append(f"{cfg}/{name}: {len(seq)} traps in an unprivileged suite, first {seq[0]}")
                continue
            ref = ref32 if "RV32" in path.read_text(errors="replace").splitlines()[0] else ref64
            if cfg == ref or name not in reports.get(ref, {}):
                continue
            ref_seq = trap_sequence(reports[ref][name])
            if seq != ref_seq:
                i = next((k for k, (a, b) in enumerate(zip(seq, ref_seq)) if a != b), min(len(seq), len(ref_seq)))
                got = seq[i] if i < len(seq) else "end"
                want = ref_seq[i] if i < len(ref_seq) else "end"
                out.append(f"{cfg}/{name}: differs from {ref} at trap #{i}: {got} vs {want}")
    return out


def check_coverage(suite: str, covergroups: set[str]) -> list[str]:
    out = []
    seen: set[str] = set()
    for f in ROOT.glob("work/*/reports/*_summary.txt"):
        for line in f.read_text(errors="replace").splitlines():
            fields = line.split()
            if len(fields) >= 2 and fields[0] in covergroups and fields[1].endswith("%"):
                seen.add(fields[0])
                if fields[1] != "100.00%":
                    out.append(f"{f.parts[len(ROOT.parts)]}: {fields[0]} {fields[1]} (see {suite}_uncovered.txt)")
    if not seen:
        return [f"no coverage data for this suite's covergroups; run `make coverage EXTENSIONS={suite}`"]
    if missing := sorted(covergroups - seen):
        out.append(f"{len(missing)} covergroups missing from every report: {', '.join(missing)}")
    return out


# Per-instruction PC patterns for each simulator's trace format.
# Group 1 is the PC; group 2, when present, numbers the instruction so repeated lines count once.
TRACE_PC_RES = (
    re.compile(r"^core\s+\d+: \d 0x([0-9a-f]+) "),  # Spike --log-commits
    re.compile(r"^#(?P<n>\d+) \d+\s+\S+\s+([0-9a-f]+) "),  # Whisper --log: one line per changed resource
    re.compile(r"^Info (?P<n>\d+): '[^']+', 0x([0-9a-fA-F]+)"),  # Imperas --trace
    re.compile(r"^\[\d+\] \[[^\]]+\]: 0x([0-9A-Fa-f]+) "),  # Sail --trace
)
QEMU_TB_RE = re.compile(r"^Trace \d+: \S+ \[[0-9a-f]+/([0-9a-f]+)/")
QEMU_INSN_RE = re.compile(r"^0x([0-9a-f]+):\s")
TRAP_ENTRY_RE = re.compile(r"^trap_[MSV]handler$|^trap_handler_fast\w+$")
HALT_RE = re.compile(r"^rvmodel_halt_(?:pass|fail)$")
PARTITION_LIMIT = 100_000


def elf_symbols(elf: Path) -> tuple[set[int], set[int]]:
    """Return the trap-entry and halt addresses of an ELF."""
    result = subprocess.run(["riscv64-unknown-elf-nm", str(elf)], capture_output=True, text=True, check=True)
    traps, halts = set(), set()
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) == 3:
            if TRAP_ENTRY_RE.match(fields[2]):
                traps.add(int(fields[0], 16))
            elif HALT_RE.match(fields[2]):
                halts.add(int(fields[0], 16))
    return traps, halts


def elf_bytes(elf: Path) -> int:
    """Loadable text + data bytes."""
    result = subprocess.run(["riscv64-unknown-elf-size", str(elf)], capture_output=True, text=True, check=True)
    text, data = result.stdout.splitlines()[1].split()[:2]
    return int(text) + int(data)


def trace_counts(trace: Path, elf: Path) -> tuple[int, int] | None:
    """Count instructions and traps up to the halt routine, so simulator halt latency is excluded."""
    traps_at, halts = elf_symbols(elf)
    instrs = traps = 0
    qemu_tb: dict[int, int] = {}
    tb_pc = None
    last_n = None
    fmt = None
    with trace.open(errors="replace") as f:
        for line in f:
            if fmt is None or fmt == "qemu":
                if line.startswith("IN:"):
                    fmt, tb_pc = "qemu", None
                    continue
                if fmt == "qemu":
                    if m := QEMU_INSN_RE.match(line):
                        pc = int(m.group(1), 16)
                        if tb_pc is None:
                            tb_pc, qemu_tb[pc] = pc, 0
                        qemu_tb[tb_pc] += 1
                        continue
                    if m := QEMU_TB_RE.match(line):
                        pc = int(m.group(1), 16)
                        if pc in halts:
                            break
                        instrs += qemu_tb.get(pc, 0)
                    elif line.startswith("riscv_cpu_do_interrupt"):
                        traps += 1
                    continue
            if fmt is None:
                fmt = next((r for r in TRACE_PC_RES if r.match(line)), None)
                if fmt is None:
                    continue
            if isinstance(fmt, re.Pattern) and (m := fmt.match(line)):
                if "n" in m.groupdict():
                    if m.group("n") == last_n:
                        continue
                    last_n = m.group("n")
                pc = int(m.group(m.re.groups), 16)
                if pc in halts:
                    break
                instrs += 1
                traps += pc in traps_at
    return (instrs, traps) if fmt is not None else None


def collect_metrics(suite: str) -> list[dict[str, object]]:
    rows = []
    for elf in sorted(ROOT.glob(f"work/*/elfs/*/{suite}/*.elf")):
        cfg = elf.parts[len(ROOT.parts) + 1]
        sub = elf.relative_to(ROOT / "work" / cfg / "elfs").with_suffix("")
        row: dict[str, object] = {"config": cfg, "test": sub.name, "xlen": 32 if "rv32" in str(sub) else 64}
        row["elf_bytes"] = elf_bytes(elf)
        dut = ROOT / "work" / cfg / "logs" / f"{sub}.trace.log"
        counts = trace_counts(dut, elf) if dut.exists() else None
        row["instrs"], row["traps"] = counts if counts else (None, None)
        sig_elf = ROOT / "work" / cfg / "build" / f"{sub}.sig.elf"
        sig_trace = sig_elf.with_suffix(".trace")
        ref = trace_counts(sig_trace, sig_elf) if sig_trace.exists() else None
        row["ref_instrs"], row["ref_traps"] = ref if ref else (None, None)
        rows.append(row)
    return rows


def median(values: list[int]) -> float:
    v = sorted(values)
    return (v[len(v) // 2] + v[(len(v) - 1) // 2]) / 2


def check_metrics(suite: str, csv_path: Path | None) -> list[str]:
    rows = collect_metrics(suite)
    if not rows:
        return ["no ELFs in work/; build the suite first (DUT traces need DEBUG=True)"]
    if csv_path:
        keys = list(rows[0])
        csv_path.write_text("\n".join([",".join(keys)] + [",".join(str(r[k]) for k in keys) for r in rows]) + "\n")
    out: list[str] = []
    for xlen in sorted({int(r["xlen"]) for r in rows}):  # type: ignore[arg-type]
        group = [r for r in rows if r["xlen"] == xlen]
        tests = sorted({str(r["test"]) for r in group})
        configs = sorted({str(r["config"]) for r in group})

        def val(r: dict[str, object], key: str) -> int | None:
            v = r[key]
            return None if v is None else int(v)  # type: ignore[arg-type]

        def instrs(r: dict[str, object]) -> int | None:
            return val(r, "instrs") if val(r, "instrs") is not None else val(r, "ref_instrs")

        all_i = [i for r in group if (i := instrs(r)) is not None]
        out.append(
            f"RV{xlen}: {len(tests)} tests x {len(configs)} configs; ELF bytes median "
            f"{median([val(r, 'elf_bytes') or 0 for r in group]):.0f}; instructions median {median(all_i):.0f} "
            f"max {max(all_i)}"
        )
        # Difference from each test's median. A config's fixed overhead (boot code, halt, extra traps)
        # is reported once; a test is reported only when it departs from its config's usual overhead.
        deltas: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
        mids: dict[tuple[str, str], float] = {}
        for key, get in (("instructions", instrs), ("ELF bytes", lambda r: val(r, "elf_bytes"))):
            for test in tests:
                vals = {str(r["config"]): v for r in group if r["test"] == test and (v := get(r)) is not None}
                if len(vals) >= 3:
                    mids[(key, test)] = mid = median(list(vals.values()))
                    for cfg, v in vals.items():
                        deltas[(key, cfg)][test] = v - mid
        for (key, cfg), per_test in sorted(deltas.items()):
            typical = median(list(per_test.values()))
            scale = median([mids[(key, t)] for t in per_test])
            if abs(typical) > max(0.2 * scale, 500):
                out.append(f"RV{xlen} {cfg}: {key} typically {typical:+.0f} vs the per-test median")
            for test, delta in sorted(per_test.items()):
                if abs(delta - typical) > max(0.2 * mids[(key, test)], 500):
                    out.append(
                        f"RV{xlen} {test} {cfg}: {key} {delta:+.0f} vs median, unlike this config's usual {typical:+.0f}"
                    )
        for cfg in configs:
            pats: dict[tuple[int | None, int | None], list[str]] = defaultdict(list)
            for r in group:
                if r["config"] == cfg:
                    pats[(val(r, "traps"), val(r, "ref_traps"))].append(str(r["test"]))
            desc = "; ".join(
                f"DUT {d if d is not None else '-'} / ref {f if f is not None else '-'} in {len(t)} tests"
                for (d, f), t in sorted(pats.items(), key=lambda kv: -len(kv[1]))
            )
            mismatch = any(d is not None and f is not None and d != f for d, f in pats)
            out.append(f"RV{xlen} {cfg} traps: {desc}{'  <- DUT differs from reference' if mismatch else ''}")
        for test in tests:
            worst = max((i for r in group if r["test"] == test and (i := instrs(r)) is not None), default=0)
            if worst > PARTITION_LIMIT:
                out.append(f"RV{xlen} {test}: {worst} dynamic instructions > {PARTITION_LIMIT}; split into more files")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("suite")
    parser.add_argument("--udb-param-dir", type=Path, help="spec/std/isa/param of a riscv-unified-db checkout")
    parser.add_argument("--ref-rv32", default="sail-rv32-max")
    parser.add_argument("--ref-rv64", default="sail-rv64-max")
    parser.add_argument("--metrics-csv", type=Path, help="write per-test, per-config metrics to this CSV file")
    args = parser.parse_args()
    if not (ROOT / "generators/testgen").is_dir():
        print("run from the riscv-arch-test repository root", file=sys.stderr)
        return 2

    suite = args.suite
    generators = find_generator(suite)
    tests = find_tests(suite)
    covergroups = {cg.replace(".", "_") for t in tests for cg in CG_RE.findall(t.read_text(errors="replace"))}
    cov_files = find_coverage_files(covergroups)
    udb_params = load_udb_params(args.udb_param_dir)
    priv = bool(generators) or bool(list(ROOT.glob(f"tests/priv/{suite}/*.S")))

    print(f"Suite {suite}: {len(tests)} tests, generators {[rel(g) for g in generators]}")
    print(f"Coverage files: {[rel(f) for f in cov_files]}")
    section("Sources", check_sources(suite, generators, tests, covergroups))
    section("Suite type", check_suite_type(suite, tests, generators))
    section("Coverpoint text", check_coverpoint_text(cov_files))
    section("Guard names", check_guards(tests + cov_files + generators, udb_params))
    section("UDB parameters", check_params(suite, tests, tests + cov_files + generators, udb_params))
    section("Normative-rule mapping", check_norm(suite, covergroups))
    section("Coverage", check_coverage(suite, covergroups))
    section("Traps (reference model under each config)", check_traps(suite, priv, args.ref_rv32, args.ref_rv64))
    section("Size, instructions and traps per config", check_metrics(suite, args.metrics_csv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
