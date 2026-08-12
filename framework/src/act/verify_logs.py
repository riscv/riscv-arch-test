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
self-checking), and the objects still match the manifest hashes. A dropped test
is reported as loudly as a failure - it's the easy way to hide one.

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

# Annotated/typer imported at module scope: Typer resolves CLI annotations at runtime.

# The summary line run_tests.py emits, same regex it parses.
_SUMMARY_RE = re.compile(r'RVCP-SUMMARY: TEST (PASSED|FAILED|SIGRUN) - Test File "([^"]*)"')


@dataclass
class LogReport:
    """Outcome of checking one returned log set."""

    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    sigrun: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)  # certified but no result returned
    unknown: list[str] = field(default_factory=list)  # result returned for a non-kit test
    duplicated: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.failed or self.sigrun or self.missing or self.unknown or self.duplicated)

    def summary(self) -> str:
        parts = [f"{len(self.passed)} passed"]
        for label, items in (
            ("failed", self.failed),
            ("SIGRUN", self.sigrun),
            ("missing", self.missing),
            ("unknown", self.unknown),
            ("duplicated", self.duplicated),
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


def scan_logs(log_paths: list[Path]) -> dict[str, list[str]]:
    """Return {test-file basename: [outcomes]} found across the given files."""
    found: dict[str, list[str]] = {}
    for p in log_paths:
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        for outcome, test_file in _SUMMARY_RE.findall(text):
            found.setdefault(test_file, []).append(outcome)
    return found


def verify(manifest_file: Path, logs_dir: Path) -> LogReport:
    """Check a returned log directory against a kit manifest."""
    manifest = json.loads(manifest_file.read_text())
    expected = _expected_test_files(manifest)

    log_files = sorted(p for p in logs_dir.rglob("*") if p.is_file() and p.suffix in (".log", ".txt"))
    found = scan_logs(log_files)

    report = LogReport()
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
        {"PASSED": report.passed, "FAILED": report.failed, "SIGRUN": report.sigrun}[outcome].append(name)

    accounted = set(report.passed) | set(report.failed) | set(report.sigrun)
    accounted |= {d.split(" (")[0] for d in report.duplicated}
    report.missing = sorted(set(expected.values()) - accounted)
    return report


def verify_kit_integrity(manifest_file: Path, kit_dir: Path) -> list[str]:
    """Re-hash the kit's objects and report any that no longer match the manifest.

    Run before trusting a returned log set: results are only meaningful if they
    came from the objects we certified.
    """
    manifest = json.loads(manifest_file.read_text())
    problems: list[str] = []
    for t in manifest.get("tests", []):
        obj = kit_dir / t["object"]
        if not obj.exists():
            problems.append(f"{t['object']}: missing from the kit")
            continue
        digest = hashlib.sha256(obj.read_bytes()).hexdigest()
        if digest != t["sha256"]:
            problems.append(f"{t['object']}: SHA-256 mismatch (object was modified)")
    return problems


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
            typer.Option("--kit-dir", file_okay=False, help="Kit directory, to re-verify object hashes"),
        ] = None,
        show: Annotated[int, typer.Option("--show", help="Max entries to list per category")] = 20,
    ) -> None:
        """Check returned certification logs against the kit manifest."""
        if kit_dir is not None:
            problems = verify_kit_integrity(manifest, kit_dir)
            if problems:
                rprint("[bold red]Kit integrity check FAILED:[/]")
                for p in problems[:show]:
                    rprint(f"  {p}")
                raise typer.Exit(2)
            rprint("[green]Kit integrity: all objects match the manifest.[/]")

        report = verify(manifest, logs)
        for label, items, style in (
            ("FAILED", report.failed, "bold red"),
            ("SIGRUN (not self-checking)", report.sigrun, "bold red"),
            ("MISSING (certified, no result returned)", report.missing, "bold red"),
            ("UNKNOWN (result for a test not in the kit)", report.unknown, "yellow"),
            ("DUPLICATED (more than one result)", report.duplicated, "yellow"),
        ):
            if items:
                rprint(f"\n[{style}]{label}: {len(items)}[/]")
                for i in items[:show]:
                    rprint(f"  {i}")
                if len(items) > show:
                    rprint(f"  ... and {len(items) - show} more")

        rprint(f"\n[bold]Result:[/] {report.summary()}")
        if report.ok:
            rprint("[bold green]All certified tests accounted for and passing.[/]")
            rprint("[dim]Note: this verifies bookkeeping, not that the logs are genuine.[/]")
        else:
            rprint("[bold red]Log set does not satisfy the kit.[/]", file=sys.stderr)
            raise typer.Exit(1)

    app()
