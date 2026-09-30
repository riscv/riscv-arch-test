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
# Provenance line the test prints on the pass path: which signature set it checked against.
_SIGDIGEST_RE = re.compile(r"RVCP-SIGNATURES: results verified against sha256=([0-9a-f]{64})")
# Kit identity stamped into the object by act-package, printed next to the digest.
_KIT_RE = re.compile(r"RVCP-KIT: id=(\S+) built=(\S+)")


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


def scan_logs(log_paths: list[Path]) -> tuple[dict[str, list[str]], dict[str, str], dict[str, tuple[str, str]]]:
    """Return ({test-file: [outcomes]}, {test-file: signature digest}, {test-file: (kit id, built)})."""
    found: dict[str, list[str]] = {}
    digests: dict[str, str] = {}
    stamps: dict[str, tuple[str, str]] = {}
    for p in log_paths:
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        hits = _SUMMARY_RE.findall(text)
        for outcome, test_file in hits:
            found.setdefault(test_file, []).append(outcome)
        # The provenance line has no test name, so tie it to the test this log reports.
        sig = _SIGDIGEST_RE.search(text)
        if sig and len(hits) == 1:
            digests[hits[0][1]] = sig.group(1)
        kit = _KIT_RE.search(text)
        if kit and len(hits) == 1:
            stamps[hits[0][1]] = (kit.group(1), kit.group(2))
    return found, digests, stamps


def verify(manifest_file: Path, logs_dir: Path) -> LogReport:
    """Check a returned log directory against a kit manifest."""
    manifest = json.loads(manifest_file.read_text())
    expected = _expected_test_files(manifest)

    log_files = sorted(p for p in logs_dir.rglob("*") if p.is_file() and p.suffix in (".log", ".txt"))
    found, digests, stamps = scan_logs(log_files)
    want_digest = {f"{Path(t['name']).name}.S": t.get("signature_sha256") for t in manifest.get("tests", [])}

    kit_id = manifest.get("kit_id")
    kit_built = manifest.get("generated")

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
        expect_d, got_d = want_digest.get(test_file), digests.get(test_file)
        if expect_d and got_d:
            if expect_d == got_d:
                report.sig_verified += 1
            else:
                report.sig_mismatch.append(f"{name} (log {got_d[:12]}… != kit {expect_d[:12]}…)")

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
            ("SIGNATURE MISMATCH (ran against different signatures)", report.sig_mismatch, "bold red"),
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
