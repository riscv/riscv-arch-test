##################################
# verify_logs.py
#
# SPDX-License-Identifier: Apache-2.0
#
# Validate the logs a certification applicant returns against the kit manifest.
##################################

"""Check returned certification logs against the kit that produced them.

Confirms every certified test has a result and all passed, no result is for a
test outside the manifest, nothing is FAILED or SIGRUN (SIGRUN = not built
self-checking), and the kit's files still match the manifest hashes. A dropped test
is reported as loudly as a failure - it's the easy way to hide one.

The output names what each check compares with what: which log, which manifest
field, which file in the kit, and both values. --details lists every test.

This checks bookkeeping, not honesty: the applicant runs the ELFs and supplies
rvmodel_halt_pass, so it can't prove the logs are genuine.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import typer
from rich import print as rprint
from rich.console import Console
from rich.markup import escape

# Annotated/typer imported at module scope: Typer resolves CLI annotations at runtime.

# The summary line run_tests.py emits, same regex it parses.
_SUMMARY_RE = re.compile(r'RVCP-SUMMARY: TEST (PASSED|FAILED|SIGRUN) - Test File "([^"]*)"')
# Provenance line the test prints on the pass path: which signature set it checked against.
_SIGDIGEST_RE = re.compile(r"RVCP-SIGNATURES: results verified against sha256=([0-9a-f]{64})")
# Kit identity stamped into the object by act-package, printed next to the digest.
_KIT_RE = re.compile(r"RVCP-KIT: id=(\S+) built=(\S+)")

# Passing rows shown per check without --details.
_SAMPLES = 3

# The rows are wider than 80 columns; wrapping them would break the alignment, including in piped output.
_out = Console(soft_wrap=True, highlight=False)


@dataclass
class TestRow:
    """What one returned log says about one certified test, next to what the kit expects."""

    name: str  # manifest test name
    log: Path | None = None
    outcome: str | None = None
    sig_log: str | None = None  # RVCP-SIGNATURES digest printed by the run
    sig_kit: str | None = None  # signature_sha256 in the manifest
    sig_values: int | None = None  # number of expected values behind that digest
    stamp_log: tuple[str, str] | None = None  # RVCP-KIT (id, built) printed by the run


@dataclass
class LogReport:
    """Outcome of checking one returned log set."""

    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    sigrun: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)  # certified but no result returned
    sig_mismatch: list[str] = field(default_factory=list)  # log's signature digest != manifest
    sig_verified: int = 0
    kit_verified: int = 0
    kit_missing: list[str] = field(default_factory=list)  # log carries no kit stamp
    kit_mismatch: list[str] = field(default_factory=list)  # stamp is not this kit's
    unknown: list[str] = field(default_factory=list)  # result returned for a non-kit test
    duplicated: list[str] = field(default_factory=list)
    rows: list[TestRow] = field(default_factory=list)  # one per certified test, in manifest order

    @property
    def ok(self) -> bool:
        return not (
            self.failed
            or self.sigrun
            or self.missing
            or self.unknown
            or self.duplicated
            or self.sig_mismatch
            or self.kit_missing
            or self.kit_mismatch
        )

    def summary(self) -> str:
        parts = [f"{len(self.passed)} passed"]
        if self.sig_verified:
            parts.append(f"{self.sig_verified} signature digests verified")
        if self.kit_verified:
            parts.append(f"{self.kit_verified} kit stamps verified")
        for label, items in (
            ("failed", self.failed),
            ("SIGRUN", self.sigrun),
            ("missing", self.missing),
            ("unknown", self.unknown),
            ("duplicated", self.duplicated),
            ("signature-mismatch", self.sig_mismatch),
            ("kit-stamp-missing", self.kit_missing),
            ("kit-stamp-mismatch", self.kit_mismatch),
        ):
            if items:
                parts.append(f"{len(items)} {label}")
        return ", ".join(parts)


def _expected_test_files(manifest: dict) -> dict[str, str]:
    """Map the test-file basename a log reports -> the manifest test name.

    The RVCP-SUMMARY line carries the .S basename (e.g. "I-add-00.S"), while the
    manifest keys on the suite-qualified name (e.g. "rv64i/I/I-add-00").
    """
    out: dict[str, str] = {}
    for t in manifest.get("tests", []):
        out[f"{Path(t['name']).name}.S"] = t["name"]
    return out


def log_files(logs_dir: Path) -> list[Path]:
    """The returned log files under logs_dir."""
    return sorted(p for p in logs_dir.rglob("*") if p.is_file() and p.suffix in (".log", ".txt"))


def scan_logs(
    log_paths: list[Path],
) -> tuple[dict[str, list[str]], dict[str, str], dict[str, tuple[str, str]], dict[str, Path]]:
    """Return ({test-file: [outcomes]}, {test-file: signature digest}, {test-file: (kit id, built)},
    {test-file: log it came from})."""
    found: dict[str, list[str]] = {}
    digests: dict[str, str] = {}
    stamps: dict[str, tuple[str, str]] = {}
    sources: dict[str, Path] = {}
    for p in log_paths:
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        hits = _SUMMARY_RE.findall(text)
        for outcome, test_file in hits:
            found.setdefault(test_file, []).append(outcome)
            sources.setdefault(test_file, p)
        # The provenance line has no test name, so tie it to the test this log reports.
        sig = _SIGDIGEST_RE.search(text)
        if sig and len(hits) == 1:
            digests[hits[0][1]] = sig.group(1)
        kit = _KIT_RE.search(text)
        if kit and len(hits) == 1:
            stamps[hits[0][1]] = (kit.group(1), kit.group(2))
    return found, digests, stamps, sources


def verify(manifest_file: Path, logs_dir: Path) -> LogReport:
    """Check a returned log directory against a kit manifest."""
    manifest = json.loads(manifest_file.read_text())
    expected = _expected_test_files(manifest)

    found, digests, stamps, sources = scan_logs(log_files(logs_dir))
    tests = {f"{Path(t['name']).name}.S": t for t in manifest.get("tests", [])}

    kit_id = manifest.get("kit_id")
    kit_built = manifest.get("generated")

    report = LogReport()
    report.rows = [
        TestRow(
            name=t["name"],
            log=sources.get(test_file),
            sig_log=digests.get(test_file),
            sig_kit=t.get("signature_sha256"),
            sig_values=t.get("signature_values"),
            stamp_log=stamps.get(test_file),
        )
        for test_file, t in tests.items()
    ]
    rows = {f"{Path(r.name).name}.S": r for r in report.rows}

    for test_file, outcomes in sorted(found.items()):
        name = expected.get(test_file)
        if name is None:
            report.unknown.append(test_file)
            continue
        # More than one result for a test is ambiguous: we cannot tell which run
        # is being claimed, so treat it as unresolved rather than picking one.
        if len(set(outcomes)) > 1 or len(outcomes) > 1:
            report.duplicated.append(f"{name} ({', '.join(outcomes)})")
            continue
        outcome = outcomes[0]
        rows[test_file].outcome = outcome
        {"PASSED": report.passed, "FAILED": report.failed, "SIGRUN": report.sigrun}[outcome].append(name)
        # The kit stamp is what ties this log to the objects we shipped: the signature
        # digest below is reproducible from the test sources, the random kit id is not.
        if kit_id:
            got = stamps.get(test_file)
            if got is None:
                report.kit_missing.append(name)
            elif got == (kit_id, kit_built):
                report.kit_verified += 1
            else:
                report.kit_mismatch.append(f"{name} (log id {got[0][:12]}… built {got[1]})")
        # Cross-check the signatures the run says it validated against.
        expect_d, got_d = tests[test_file].get("signature_sha256"), digests.get(test_file)
        if expect_d and got_d:
            if expect_d == got_d:
                report.sig_verified += 1
            else:
                report.sig_mismatch.append(f"{name} (log {got_d[:12]}… != kit {expect_d[:12]}…)")

    accounted = set(report.passed) | set(report.failed) | set(report.sigrun)
    accounted |= {d.split(" (")[0] for d in report.duplicated}
    report.missing = sorted(set(expected.values()) - accounted)
    return report


@dataclass
class FileCheck:
    """One file in the kit, re-hashed and compared with the digest the manifest records for it."""

    path: str  # relative to the kit directory
    source: str  # where the expected digest comes from
    expected: str
    actual: str | None  # None: the file is missing

    @property
    def ok(self) -> bool:
        return self.actual == self.expected


def check_kit(manifest_file: Path, kit_dir: Path) -> list[FileCheck]:
    """Re-hash the manifest, archives and objects of a kit against the digests recorded for them.

    Run before trusting a returned log set: results are only meaningful if they
    came from the objects we certified.
    """
    manifest = json.loads(manifest_file.read_text())

    def sha256(path: Path) -> str | None:
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

    checks: list[FileCheck] = []
    stamp = kit_dir / "MANIFEST.sha256"
    if stamp.is_file():
        recorded = stamp.read_text().split()[0]
        checks.append(FileCheck("manifest.json", "MANIFEST.sha256", recorded, sha256(manifest_file)))
    for a in manifest.get("archives", []):
        checks.append(FileCheck(a["archive"], "manifest archives[]", a["sha256"], sha256(kit_dir / a["archive"])))
    for t in manifest.get("tests", []):
        checks.append(FileCheck(t["object"], "manifest tests[]", t["sha256"], sha256(kit_dir / t["object"])))
    return checks


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _short(digest: str | None) -> str:
    return f"{digest[:12]}…" if digest else "(none)"


def _mark(ok: bool) -> str:
    return "[green]✓[/]" if ok else "[bold red]✗[/]"


def _rows(rows: list[tuple[bool, list[str]]], details: bool, show: int) -> None:
    """Print aligned rows: every failing one (up to show), and a few passing ones unless details."""
    bad = [cells for ok, cells in rows if not ok]
    good = [cells for ok, cells in rows if ok]
    if not details and len(good) > _SAMPLES:
        # Spread the samples over the kit rather than showing the first suite only.
        good = [good[i * (len(good) - 1) // (_SAMPLES - 1)] for i in range(_SAMPLES)]
    picked = [(False, c) for c in bad[:show]] + [(True, c) for c in good]
    widths = [max(len(c[i]) for _, c in picked) for i in range(len(picked[0][1]))] if picked else []
    for ok, cells in picked:
        line = "  ".join(escape(c.ljust(w)) for c, w in zip(cells, widths))
        _out.print(f"    {line}  {_mark(ok)}")
    hidden = len(rows) - len(picked)
    if hidden:
        _out.print(f"    [dim]… {hidden} more (--details lists every one)[/]")


def _header(manifest_file: Path, manifest: dict, kit_dir: Path | None, logs_dir: Path, n_logs: int) -> None:
    tool = manifest.get("toolchain", {})
    _out.print(f"[bold]Checking returned logs against kit[/] {escape(str(manifest.get('config')))}")
    _out.print(f"  manifest  {escape(str(manifest_file))}")
    _out.print(f"            kit id {manifest.get('kit_id')}, built {manifest.get('generated')}")
    _out.print(
        f"            {len(manifest.get('tests', []))} tests in {len(manifest.get('archives', []))} archives; "
        f"{escape(str(tool.get('compiler', '?')))}; reference model {escape(str(tool.get('reference_model', '?')))}"
    )
    _out.print(f"  kit dir   {escape(str(kit_dir)) if kit_dir else '(not given; objects are not re-hashed)'}")
    _out.print(f"  logs      {escape(str(logs_dir))} ({n_logs} log files)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for ``act-verify-logs``."""
    app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})

    @app.command()
    def run(
        manifest: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="Kit manifest.json")],
        logs: Annotated[Path, typer.Argument(exists=True, file_okay=False, help="Returned logs directory")],
        kit_dir: Annotated[
            Path | None,
            typer.Option("--kit-dir", file_okay=False, help="Kit directory, to re-verify file hashes"),
        ] = None,
        show: Annotated[int, typer.Option("--show", help="Max failing entries to list per check")] = 20,
        details: Annotated[bool, typer.Option("--details", help="List every test in every check")] = False,
    ) -> None:
        """Check returned certification logs against the kit manifest."""
        data = json.loads(manifest.read_text())
        _header(manifest, data, kit_dir, logs, len(log_files(logs)))

        _out.print("\n[bold]1/4  Kit integrity[/]: each file in the kit dir, re-hashed, against its digest in the kit")
        if kit_dir is None:
            _out.print("    [dim]skipped: pass --kit-dir to re-hash the shipped files[/]")
        else:
            checks = check_kit(manifest, kit_dir)
            _rows(
                [
                    (
                        c.ok,
                        [
                            c.path,
                            f"sha256 {_short(c.actual) if c.actual else '(missing)'}",
                            f"vs {_short(c.expected)} in {c.source}",
                        ],
                    )
                    for c in checks
                ],
                details,
                show,
            )
            bad = [c for c in checks if not c.ok]
            if bad:
                _out.print(f"[bold red]Kit integrity check FAILED: {len(bad)} of {len(checks)} files do not match.[/]")
                raise typer.Exit(2)
            n_arch = sum(c.source == "manifest archives[]" for c in checks)
            n_obj = sum(c.source == "manifest tests[]" for c in checks)
            has_stamp = any(c.source == "MANIFEST.sha256" for c in checks)
            _out.print(
                f"    [green]Kit integrity: all objects match the manifest[/] "
                f"({'manifest digest, ' if has_stamp else ''}{n_arch} archives, {n_obj} objects)."
            )

        report = verify(manifest, logs)

        _out.print("\n[bold]2/4  Results[/]: the RVCP-SUMMARY line of each log, one PASSED per test in the manifest")
        _rows(
            [
                (r.outcome == "PASSED", [r.name, r.log.name if r.log else "(no log)", r.outcome or "no result"])
                for r in report.rows
            ],
            details,
            show,
        )
        for label, items in (
            ("UNKNOWN (result for a test not in the kit)", report.unknown),
            ("DUPLICATED (more than one result)", report.duplicated),
        ):
            if items:
                _out.print(f"    [yellow]{label}: {len(items)}[/]")
                for i in items[:show]:
                    _out.print(f"      {escape(i)}")
        _out.print(
            f"    {len(report.passed)} of {len(report.rows)} passed; {len(report.failed)} failed, "
            f"{len(report.sigrun)} SIGRUN, {len(report.missing)} missing"
        )

        _out.print(
            "\n[bold]3/4  Signatures[/]: the RVCP-SIGNATURES digest each test printed, "
            "against signature_sha256 in the manifest"
        )
        _rows(
            [
                (
                    r.sig_log is not None and r.sig_log == r.sig_kit,
                    [
                        r.name,
                        f"log {_short(r.sig_log)}",
                        f"vs {_short(r.sig_kit)} in manifest",
                        f"({r.sig_values} values)" if r.sig_values is not None else "",
                    ],
                )
                for r in report.rows
                if r.sig_kit
            ],
            details,
            show,
        )
        _out.print(f"    {report.sig_verified} of {sum(1 for r in report.rows if r.sig_kit)} digests match")

        kit_id, kit_built = data.get("kit_id"), data.get("generated")
        _out.print("\n[bold]4/4  Kit stamp[/]: the RVCP-KIT line each test printed, against kit_id and generated")
        if kit_id:
            _out.print(f"    expected  id={kit_id} built={kit_built}")
            _rows(
                [
                    (
                        r.stamp_log == (kit_id, kit_built),
                        [
                            r.name,
                            f"id {_short(r.stamp_log[0])}" if r.stamp_log else "(no stamp)",
                            f"built {r.stamp_log[1]}" if r.stamp_log else "",
                        ],
                    )
                    for r in report.rows
                    if r.outcome
                ],
                details,
                show,
            )
            _out.print(f"    {report.kit_verified} of {sum(1 for r in report.rows if r.outcome)} stamps match")
        else:
            _out.print("    [dim]skipped: this kit has no kit_id[/]")

        _out.print(f"\n[bold]Result:[/] {report.summary()}")
        if report.ok:
            _out.print("[bold green]All certified tests accounted for and passing.[/]")
            _out.print("[dim]Note: this verifies bookkeeping, not that the logs are genuine.[/]")
        else:
            rprint("[bold red]Log set does not satisfy the kit.[/]", file=sys.stderr)
            raise typer.Exit(1)

    app()
