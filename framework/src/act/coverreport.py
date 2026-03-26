##################################
# coverreport.py
#
# jcarlin@hmc.edu 9 May 2025
# SPDX-License-Identifier: Apache-2.0
#
# Generate txt coverage reports from UCDB file
##################################

import re
import subprocess
import sys
from pathlib import Path

from act.config import CoverageSimulator

# Pattern used to detect Questa summary headers (for dedup)
_QUESTA_HEADER_LINE = "Covergroup                                             Metric       Goal       Bins    Status"
_TYPE_LINE_PATTERN = re.compile(r"^\s*TYPE\s+(.+?)\s*$")
_COVERGROUP_PREFIX = "/RISCV_coverage_pkg/RISCV_coverage__1/"

_TABLE_HEADERS = ["Covergroup", "Metric", "Goal", "Bins", "Status"]

# A single row in a coverage summary table
CoverageEntry = tuple[str, str, str, str, str]


# ── Formatting helpers ──────────────────────────────────────────────────────


def _ansi(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text


def _red(text: str) -> str:
    return _ansi("1;31", text)


def _green(text: str) -> str:
    return _ansi("1;32", text)


def _format_table(entries: list[CoverageEntry]) -> str:
    """Format coverage entries as a fixed-width column table with headers."""
    padding = 5
    widths = [max(len(h) + padding, max(len(e[i]) for e in entries) + padding) for i, h in enumerate(_TABLE_HEADERS)]
    header = "".join(f"{h:<{w}}" for h, w in zip(_TABLE_HEADERS, widths))
    rows = ["".join(f"{e[i]:<{w}}" for i, w in enumerate(widths)) for e in entries]
    return header + "\n" + "\n".join(rows) + "\n"


def _report_paths(prefix: Path) -> tuple[Path, Path, Path]:
    """Return (full_report, uncovered_report, summary) paths for a report prefix."""
    name = prefix.name
    parent = prefix.parent
    return (
        parent / f"{name}_report.txt",
        parent / f"{name}_uncovered.txt",
        parent / f"{name}_summary.txt",
    )


# ── Parsing helpers ─────────────────────────────────────────────────────────


def _parse_summary_file(path: Path) -> list[CoverageEntry]:
    """Parse a summary .txt file (header + whitespace-delimited rows) into entries."""
    entries: list[CoverageEntry] = []
    for line in path.read_text().splitlines()[1:]:  # skip header
        parts = line.split()
        if len(parts) >= 5:
            entries.append((parts[0], parts[1], parts[2], parts[3], " ".join(parts[4:])))
    return entries


# ── Public API ──────────────────────────────────────────────────────────────


def merge_summaries(input_files: list[Path], output_file: Path) -> None:
    """Merge multiple summary files into one with consistent formatting."""
    all_entries: list[CoverageEntry] = []
    for path in input_files:
        if not path.exists():
            print(f"Warning: File {path} does not exist, skipping.", file=sys.stderr)
            continue
        all_entries.extend(_parse_summary_file(path))

    if not all_entries:
        print("Error: Failed to merge coverage summaries. All input summary files are empty.", file=sys.stderr)
        sys.exit(1)

    output_file.write_text(_format_table(all_entries))


def print_coverage_summary(overall_summary: Path, config_name: str) -> None:
    """Print a human-readable coverage summary from an _overall_summary.txt file."""
    entries = _parse_summary_file(overall_summary)

    partial: list[CoverageEntry] = []
    total_pct = 0.0
    parsed = 0
    for entry in entries:
        try:
            pct = float(entry[1].rstrip("%"))
        except ValueError:
            continue
        parsed += 1
        total_pct += pct
        if pct < 100.0:
            partial.append(entry)

    avg = total_pct / parsed if parsed else 0.0

    if partial:
        print(_red(f" RVCP: {config_name} Coverage FAIL"))
        print(f"  {len(entries)} covergroups, average coverage {avg:.2f}%")
        print(f"  Partially covered covergroups: {len(partial)}")
        for name, metric, goal, bins, status in partial:
            print(f"    {name} {metric} {goal} {bins} {status}")
    else:
        print(_green(f" RVCP: {config_name} Coverage PASS"))
        print(f"  {len(entries)} covergroups all with 100% coverage")


def generate_report(
    coverage_db: Path,
    report_prefix: Path,
    simulator: CoverageSimulator = CoverageSimulator.QUESTA,
) -> None:
    """Generate coverage reports from a simulator coverage database."""
    report_prefix.parent.mkdir(parents=True, exist_ok=True)

    if simulator == CoverageSimulator.QUESTA:
        _generate_questa_report(coverage_db, report_prefix)
    elif simulator == CoverageSimulator.VCS:
        _generate_vcs_report(coverage_db, report_prefix)
    else:
        raise ValueError(f"Unknown simulator: {simulator}")


# ── Questa helpers ──────────────────────────────────────────────────────────


def _remove_questa_duplicates(path: Path) -> None:
    """Remove duplicate lines that appear after the second summary header in a Questa report."""
    seen: set[str] = set()
    header_count = 0
    output: list[str] = []

    for line in path.read_text().splitlines(keepends=True):
        stripped = line.strip()
        if stripped == _QUESTA_HEADER_LINE:
            header_count += 1
            if header_count == 2:
                continue
        if header_count == 2 and stripped in seen:
            continue
        output.append(line)
        if header_count < 2:
            seen.add(stripped)

    path.write_text("".join(output))


def _questa_report_to_summary(report_path: Path, summary_path: Path) -> None:
    """Extract covergroup-level entries from a detailed Questa report into a summary table."""
    lines = report_path.read_text().splitlines()
    entries: list[CoverageEntry] = []

    for idx, line in enumerate(lines):
        match = _TYPE_LINE_PATTERN.match(line)
        if not match:
            continue

        full_path = match.group(1).strip()
        if _COVERGROUP_PREFIX in full_path:
            name = full_path.split(_COVERGROUP_PREFIX, 1)[1].strip()
        else:
            name = full_path.split("/")[-1].strip()

        metrics_line = next((candidate.strip() for candidate in lines[idx + 1 :] if candidate.strip()), "")
        if not metrics_line:
            continue

        parts = metrics_line.split()
        if len(parts) < 4:
            raise ValueError(f"Unexpected metric line format: '{metrics_line}'")

        entries.append((name, parts[0], parts[1], parts[2], " ".join(parts[3:])))

    if not entries:
        raise ValueError("No coverage entries found in report.")

    summary_path.write_text(_format_table(entries))


def _generate_questa_report(ucdb: Path, report_prefix: Path) -> None:
    """Generate Questa coverage reports from a ucdb file."""
    full_report, uncovered_report, summary_report = _report_paths(report_prefix)

    vcover_cmd = ["vcover", "report", "-details", str(ucdb)]
    subprocess.run([*vcover_cmd, "-output", str(full_report)], check=True, capture_output=True)
    _remove_questa_duplicates(full_report)

    if "TOTAL COVERGROUP COVERAGE: 100.00%" not in full_report.read_text():
        subprocess.run(
            [*vcover_cmd, "-below", "100", "-output", str(uncovered_report)],
            check=True,
            capture_output=True,
        )
        _remove_questa_duplicates(uncovered_report)

    _questa_report_to_summary(full_report, summary_report)


# ── VCS helpers ─────────────────────────────────────────────────────────────


def _parse_vcs_groups(groups_file: Path) -> list[CoverageEntry]:
    """Parse urg groups.txt into coverage entries."""
    entries: list[CoverageEntry] = []
    for line in groups_file.read_text(errors="ignore").splitlines():
        parts = line.split()
        if len(parts) < 8:
            continue
        try:
            score = float(parts[0])
            goal = float(parts[2])
        except ValueError:
            continue

        covergroup = parts[-1].split("::")[-1]
        metric = f"{score:.2f}%"
        goal_str = f"{goal:.0f}"
        status = "Covered" if score >= goal else ("ZERO" if score == 0.0 else "Uncovered")
        entries.append((covergroup, metric, goal_str, "-", status))

    if not entries:
        raise ValueError(f"No covergroup entries found in {groups_file}")
    return entries


def _collect_uncovered_sections(grpinfo_file: Path, uncovered_groups: set[str]) -> str:
    """Extract detailed sections for uncovered groups from urg grpinfo.txt."""
    content = grpinfo_file.read_text(errors="ignore")
    starts = list(re.finditer(r"(?m)^Group\s*:\s+", content))
    sections: list[str] = []
    for idx, match in enumerate(starts):
        start = match.start()
        end = starts[idx + 1].start() if idx + 1 < len(starts) else len(content)
        section = content[start:end]
        header_line = section.splitlines()[0] if section.splitlines() else ""
        full_name = header_line.split("Group :", 1)[1].strip() if "Group :" in header_line else ""
        if full_name.split("::")[-1] in uncovered_groups:
            sections.append(section.rstrip())
    return "\n\n".join(sections)


def _write_vcs_reports(report_prefix: Path, urg_report_dir: Path) -> None:
    """Create report, uncovered, and summary files from urg text outputs."""
    full_report, uncovered_report, summary_report = _report_paths(report_prefix)

    groups_file = urg_report_dir / "groups.txt"
    grpinfo_file = urg_report_dir / "grpinfo.txt"
    if not groups_file.exists() or not grpinfo_file.exists():
        raise FileNotFoundError(f"URG output missing required files in {urg_report_dir}")

    entries = _parse_vcs_groups(groups_file)
    table = _format_table(entries)
    grpinfo_text = grpinfo_file.read_text(errors="ignore")

    summary_report.write_text(table)
    full_report.write_text(
        f"Coverage Report by instance with details\n\n{table}\n"
        f"Detailed group information (from urg grpinfo.txt)\n{'=' * 89}\n{grpinfo_text}"
    )

    uncovered = [e for e in entries if e[4] != "Covered"]
    if uncovered:
        uncovered_table = _format_table(uncovered)
        uncovered_groups = {e[0] for e in uncovered}
        sections = _collect_uncovered_sections(grpinfo_file, uncovered_groups)
        uncovered_report.write_text(
            f"Coverage Report by instance with details\n\n{uncovered_table}\n"
            f"Detailed uncovered group information\n{'=' * 89}\n" + (sections or "No uncovered group details found.")
        )
    elif uncovered_report.exists():
        uncovered_report.unlink()


def _generate_vcs_report(vdb: Path, report_prefix: Path) -> None:
    """Generate VCS coverage reports from a vdb database."""
    urg_report_dir = vdb.parent / f"{report_prefix.name}_urg"
    subprocess.run(
        ["urg", "-full64", "-dir", str(vdb), "-report", str(urg_report_dir), "-format", "text"],
        check=True,
        capture_output=True,
        text=True,
    )
    _write_vcs_reports(report_prefix, urg_report_dir)
