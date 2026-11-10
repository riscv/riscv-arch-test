##################################
# generate.py
#
# David_Harris@hmc.edu 15 August 2025
# SPDX-License-Identifier: Apache-2.0
#
# Generate functional covergroups for RISC-V instructions
##################################

import csv
import importlib.resources
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path
from types import ModuleType

from rich import print as rprint
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)


def _progress(description: str) -> Progress:
    """Construct the standard project progress display."""
    return Progress(
        SpinnerColumn(),
        TextColumn(f"[cyan]{description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TextColumn("elapsed:"),
        TimeElapsedColumn(),
        transient=True,
    )


def _load_testgen_script(filename: str) -> ModuleType:
    """Load a module from ``generators/testgen/scripts/`` by file path.

    That directory is not a Python package, so its helpers (the single source
    of truth for several vector rules) must be imported by path. These modules
    are large, so they are loaded once into module-level globals rather than
    per use.
    """
    import importlib.util

    repo_root = Path(__file__).resolve().parents[4]
    mod_path = repo_root / "generators" / "testgen" / "scripts" / filename
    if not mod_path.exists():
        raise FileNotFoundError(f"Required testgen script not found: {mod_path}")
    spec = importlib.util.spec_from_file_location(mod_path.stem, mod_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create import spec for {mod_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Loaded once at import; both are large testgen modules consulted per instruction.
_VECTOR_TESTGEN_COMMON = _load_testgen_script("vector_testgen_common.py")


# Vector extension prefixes used to identify vector architectures.
VECTOR_PREFIXES = ("Zv", "V", "ExceptionsV", "ExceptionsZv", "SsstrictV", "SsstrictZv")

# Priv tests that are driven by csvs (only for Vector Priv)
PRIV_TESTPLAN_PREFIXES = ("Exceptions", "Ssstrict")

# Map instruction Type code → (has_vd_reg_group, has_vs1_reg_group, has_vs2_reg_group).
# Used to suppress per-operand off_group / overlap crosses for instructions whose
# encoding hardcodes an operand field (e.g. vid.v has no vs1/vs2 registers — those
# bits are part of the opcode, so unaligned-vs1 / unaligned-vs2 bins can never fire).
# vd is recorded as "present" for stores (the vs3 data register lives in the rd field
# and still has an EMUL-aligned register group constraint).
_TYPE_OPERANDS: dict[str, tuple[bool, bool, bool]] = {
    "VVVM": (True, True, True),
    "VVV": (True, True, True),
    "VVVMR": (True, True, True),
    "VVIM": (True, False, True),
    "VVI": (True, False, True),
    "VVXM": (True, False, True),
    "VVX": (True, False, True),
    "VVFM": (True, False, True),
    "VVM": (True, False, True),
    "VV": (True, False, True),
    "VVR": (True, True, False),
    "VFVM": (True, False, True),
    "VI": (True, False, False),
    "VM": (True, False, False),
    "VF": (True, False, False),
    "FV": (False, False, True),
    "XV": (False, False, True),
    "XVM": (False, False, True),
    "VX": (True, False, False),
    "VXM": (True, False, False),
    "VXVM": (True, False, True),
    "VXXM": (True, False, False),
    "VSX": (True, False, False),
    "VSXM": (True, False, False),
    "VSXVM": (True, False, True),
    "VSXXM": (True, False, False),
    # Vector integer types from Vx.csv
    "WVV": (True, True, True),
    "WVX": (True, False, True),
    "WVV_ACC": (True, True, True),
    "WVX_ACC": (True, False, True),
    "WWV": (True, True, True),
    "WWX": (True, False, True),
    "VWV": (True, True, True),
    "VWX": (True, False, True),
    "VWI": (True, False, True),
    "VVV_ACC": (True, True, True),
    "VVX_ACC": (True, False, True),
    "VVV_SAT": (True, True, True),
    "VVX_SAT": (True, False, True),
    "VVI_SAT": (True, False, True),
    "VVSR": (True, True, True),
    "WVWSR": (True, True, True),
    "MVV": (True, True, True),
    "MVX": (True, False, True),
    "MVI": (True, False, True),
    "MVVM": (True, True, True),
    "MVXM": (True, False, True),
    "MVIM": (True, False, True),
    "MMM": (True, True, True),
    "MM": (True, False, True),
    "VVVP": (True, True, True),
    "VVXP": (True, False, True),
    "VVIP": (True, False, True),
    "VEXT": (True, False, True),
    "VMVR": (True, False, True),
    "VCOMPRESS": (True, True, True),
    "VID": (True, False, False),
}


def _operand_presence(instr_type: str) -> tuple[bool, bool, bool]:
    """Return (has_vd, has_vs1, has_vs2) register-group presence for a given Type.

    Unknown types default to (True, True, True) so we don't accidentally drop bins
    for new types that are added without updating this table.
    """
    return _TYPE_OPERANDS.get(instr_type, (True, True, True))


def _max_legal_lmul_for_instruction(instr: str) -> int:
    """Return the largest legal LMUL for ``instr`` (≤ 8).

    Mirrors the rules in ``priv/_ssstrictv_helpers.max_legal_lmul``:

    * Segment LS instructions require ``NF * EMUL ≤ 8`` so EMUL ≤ 8/NF.
    * Widening / narrowing ops have an operand with EEW = 2*SEW so EMUL = 2*LMUL,
      capping LMUL at 4.
    * Otherwise LMUL ≤ 8.
    """
    _c = _VECTOR_TESTGEN_COMMON
    nf = _c.getInstructionSegments(instr)
    if nf and nf > 1:
        cap = 8 // nf
        for m in (8, 4, 2, 1):
            if m <= cap:
                return m
        return 1
    if instr in _c.vd_widen_ins or instr in _c.vs2_widen_ins:
        return 4
    return 8


_LMUL_CROSS_RE = re.compile(r"cp_ssstrictv_lmul(\d+)_(vd|vs1|vs2)_off_group")


def _filter_per_operand_crosses(rendered: str, has_vd: bool, has_vs1: bool, has_vs2: bool, max_lmul: int) -> str:
    """Drop cross lines tied to operands the instruction's Type does not encode.

    The ``cp_ssstrictv_lmulgt1_off_group`` template emits one cross per (lmul,
    operand) pair. Two reasons we may drop a cross:

    * Operand absent in the Type encoding (e.g. ``vid.v`` has no vs1/vs2).
    * The (LMUL, instruction) combination is illegal — e.g. widening ops cap at
      LMUL=4 because vd has EEW=2*SEW, and segment LS caps at LMUL=8/NF.
    """
    if has_vd and has_vs1 and has_vs2 and max_lmul >= 8:
        return rendered
    out_lines: list[str] = []
    for line in rendered.splitlines(keepends=True):
        stripped = line.lstrip()
        m = _LMUL_CROSS_RE.search(stripped)
        if m and stripped.startswith("cp_ssstrictv_lmul"):
            lmul = int(m.group(1))
            role = m.group(2)
            if role == "vd" and not has_vd:
                continue
            if role == "vs1" and not has_vs1:
                continue
            if role == "vs2" and not has_vs2:
                continue
            if lmul > max_lmul:
                continue
        out_lines.append(line)
    return "".join(out_lines)


def _write_if_changed(path: Path, content: str) -> None:
    """Write content only if it differs from the existing file, to avoid unnecessary rebuilds."""
    if path.exists() and path.read_text() == content:
        return
    path.write_text(content)


##################################
# Reading testplans and templates
##################################

Testplan = dict[tuple[str, str], list[str]]


def _parse_testplan_groups(csv_path: Path) -> dict[tuple[str, ...], Testplan]:
    """Parse a testplan CSV into (instruction, type) -> coverpoints, grouped by ExtraExtensions entry.

    The () group holds the rows that need only the suite's own extensions.
    """
    groups: dict[tuple[str, ...], Testplan] = defaultdict(dict)
    with csv_path.open() as csvfile:
        for row in csv.DictReader(csvfile):
            if "Instruction" not in row:
                raise ValueError(
                    f"Error reading testplan {csv_path.name}. "
                    "Did you remember to shrink the .csv files after expanding?"
                )
            instr = row["Instruction"]
            instr_type = row.get("Type", "")
            extra_extensions = tuple(ext.strip() for ext in row.pop("ExtraExtensions", "").split(":") if ext.strip())

            cps: list[str] = []
            del row["Instruction"]
            for key, value in row.items():
                if not isinstance(value, str) or value == "":
                    continue
                if key == "Type":
                    # TODO: Expand the list of aliased types to avoid duplicate sample function templates
                    sample_type = value.removesuffix("_RD_NX0")
                    cps.append(f"sample_{sample_type}")
                else:
                    # For special entries, append the value as a suffix
                    # e.g. cp_rd_edges with value "lui" becomes cp_rd_edges_lui
                    if value != "x":
                        key = f"{key}_{value}"
                    cps.append(key)

            groups[extra_extensions][(instr, instr_type)] = cps
    return groups


def read_testplans(testplan_dir: Path) -> tuple[dict[str, Testplan], dict[str, dict[tuple[str, ...], Testplan]]]:
    """Read all CSV testplan files.

    Returns (testplans, extra_testplans). testplans maps each extension name to the rows that need only
    that extension; extra_testplans maps an extension name to its rows with a ExtraExtensions entry,
    keyed by that entry. Each CSV file produces one testplan entry keyed by the file's stem (e.g. "I", "Zba").
    Some extensions are expanded:
      - "I" is duplicated as "E"
    """
    testplans: dict[str, Testplan] = {}
    extra_testplans: dict[str, dict[tuple[str, ...], Testplan]] = {}

    for csv_path in testplan_dir.glob("**/*.csv"):
        arch = csv_path.stem
        if arch == "instruction_formats":
            continue

        groups = _parse_testplan_groups(csv_path)
        tp = groups.pop((), {})
        testplans[arch] = tp
        if groups:
            extra_testplans[arch] = groups

        # Duplicate I testplan for E
        if arch == "I":
            testplans["E"] = tp

    return testplans, extra_testplans


def _filter_testplans(
    test_plans: dict[str, dict[tuple[str, str], list[str]]],
    extensions: str,
    exclude: str,
) -> dict[str, dict[tuple[str, str], list[str]]]:
    """Filter testplans by comma-separated include/exclude extension lists.

    Matches against post-expansion keys (e.g. Vx8, not Vx).
    """
    include_set: set[str] | None = None
    if extensions != "all":
        include_set = {ext.strip() for ext in extensions.split(",") if ext.strip()}
    exclude_set: set[str] = set()
    if exclude:
        exclude_set = {ext.strip() for ext in exclude.split(",") if ext.strip()}

    return {
        arch: tp
        for arch, tp in test_plans.items()
        if (include_set is None or arch in include_set) and arch not in exclude_set
    }


def read_covergroup_templates(package: str = "covergroupgen.templates") -> dict[str, str]:
    """Recursively read all .sv covergroup templates from the given package and its sub-packages."""
    templates: dict[str, str] = {}
    for item in importlib.resources.files(package).iterdir():
        if item.is_file() and item.name.endswith(".sv"):
            templates[item.name.removesuffix(".sv")] = item.read_text()
        elif item.is_dir() and not item.name.startswith("__"):
            templates.update(read_covergroup_templates(f"{package}.{item.name}"))
    return templates


##################################
# Template helpers
##################################


def customize_template(templates: dict[str, str], name: str, arch: str = "", instr: str = "", effew: str = "") -> str:
    """Look up a template by name and substitute placeholders.

    Placeholders replaced: @INSTRNODOT@, @INSTR@, @ARCHPREFIXUPPER@, @ARCHPREFIX@,
    @ARCHUPPER@, @ARCHCASE@, @ARCH@, and (if effew is set) @TWOEFFEW@, @EFFEW@, @EFFVSEW@.
    ARCHPREFIX is the arch with any trailing digits stripped (e.g. "Vx16" -> "Vx").
    """
    if name not in templates:
        available = list(templates.keys())
        similar = get_close_matches(name, available, n=5, cutoff=0.4)
        msg = f"No template found for '{name}'. "
        if similar:
            msg += f"Similar templates: {', '.join(similar)}. "
        templates_dir = importlib.resources.files("covergroupgen.templates")
        msg += f"To add support, create a new .sv template in '{templates_dir}'."
        raise ValueError(msg)

    arch_prefix = re.sub(r"\d+$", "", arch)
    result = (
        templates[name]
        .replace("@INSTRNODOT@", instr.replace(".", "_"))
        .replace("@INSTR@", instr)
        .replace("@ARCHPREFIXUPPER@", arch_prefix.upper())
        .replace("@ARCHPREFIX@", arch_prefix)
        .replace("@ARCHUPPER@", arch.upper())
        .replace("@ARCHCASE@", arch)
        .replace("@ARCH@", arch.lower())
    )
    if effew:
        result = (
            result.replace("@TWOEFFEW@", str(2 * int(effew)))
            .replace("@EFFEW@", str(int(effew)))
            .replace("@EFFVSEW@", str(int(math.log2(int(effew))) - 3))
        )
    return result


def _is_vector(arch: str) -> bool:
    return arch.startswith(VECTOR_PREFIXES)


def _is_priv(arch: str) -> bool:
    """Priv testplans whose covergroups need vector helpers but no SEW expansion."""
    return arch.startswith(PRIV_TESTPLAN_PREFIXES)


def _matches_xlen(cps: list[str], has_rv32: bool, has_rv64: bool) -> bool:
    """Check if an instruction's coverpoints match the requested XLEN filter.

    An instruction matches when its RV32/RV64 markers agree with the filter.
    Instructions without an RV32 or RV64 marker match any XLEN.
    """
    return ("RV32" in cps) == has_rv32 and ("RV64" in cps) == has_rv64


def _any_xlen_exclusion(
    rv_marker: str, instr_keys: list[tuple[str, str]], tp: dict[tuple[str, str], list[str]]
) -> bool:
    """Check if any instruction lacks the given RV marker (meaning it's XLEN-specific)."""
    return any(rv_marker not in tp[key] for key in instr_keys)


def _ffLS_feasible(instr: str, sew: int) -> bool:
    """Check if cp_custom_ffLS (which requires LMUL=2) is feasible for this instruction at the given SEW.

    Returns False when EMUL * nf > 8 with LMUL=2, meaning the configuration is impossible.
    """
    # Extract EEW from instruction name (e.g., vle32ff.v → 32, vlseg3e64ff.v → 64)
    eew_m = re.search(r"e(\d+)ff", instr)
    if not eew_m:
        return True
    eew = int(eew_m.group(1))
    # Extract nf (number of fields) from segmented instructions
    nf_m = re.search(r"seg(\d+)", instr)
    nf = int(nf_m.group(1)) if nf_m else 1
    lmul = 2
    emul = eew * lmul // sew
    return emul * nf <= 8


##################################
# Content generation
##################################


def _resolve_coverpoint(cp: str, instr: str, sew: int | None, templates: dict[str, str]) -> str | None:
    """Resolve a raw testplan coverpoint to its final template name, or None to skip it.

    Applies, in order: metadata-column skips, the SsstrictV skip table, the
    cp_custom_ffLS feasibility gate, and the SEW-conditional suffix rules
    (_sew_ge{N}, the SEW-dependent suffix, _eew_eq_sew, _sew_lte_{N}).
    """
    # Skip metadata columns (sample_*, RV32/RV64, EFFEW*, cp_ibm).
    if cp.startswith(("sample_", "EFFEW", "cp_ibm")) or cp in {"RV32", "RV64"}:
        return None

    if sew is None:
        return cp

    tested_sews, cleaned_cp = _extract_sews(cp)
    if sew not in tested_sews:
        return None

    # Strip the SEW suffix
    cp = cleaned_cp

    # cp_custom_ffLS requires LMUL=2; Use a fallback when this isn't possible
    if cp == "cp_custom_ffLS" and not _ffLS_feasible(instr, sew):
        cp = "cp_custom_ffLS_lmul_lt2"

        eew_m = re.search(r"e(\d+)ff", instr)
        eew = int(eew_m.group(1)) if eew_m else 0
        if eew >= 32:
            cp += f"_eew{eew}"

    # Append SEW suffix for SEW-dependent coverpoints.
    if cp not in templates:
        retry_cp = f"{cp}_sew{sew}"
        if retry_cp in templates:
            cp = retry_cp
        # Otherwise let the error be handled in customize template where a better error message
        # will be generated

    return cp


def _get_test_sews(cps: list[str]) -> list[int]:
    available_sews: set[int] = set()
    for cp in cps:
        if cp.startswith(("sample_", "RV32", "RV64")):
            continue
        extracted_sews, _ = _extract_sews(cp)
        if not extracted_sews:
            raise ValueError(f"Could not parse vector SEWs to test in coverpoint: {cp}")
        available_sews |= extracted_sews

    return list(available_sews)


def _extract_sews(cp: str) -> tuple[set[int], str]:
    parts = cp.split("_")

    available_sews = set()
    i = len(parts)
    for cp_part in parts[::-1]:
        if not cp_part.isnumeric() or cp_part == "0":
            break
        available_sews.add(int(cp_part))
        i -= 1

    return available_sews, "_".join(parts[:i])


def _gen_instrs(
    instr_keys: list[tuple[str, str]],
    templates: dict[str, str],
    tp: dict[tuple[str, str], list[str]],
    arch: str,
    has_rv32: bool,
    has_rv64: bool,
    name: str,
) -> tuple[str, str]:
    """Generate covergroup definitions and init content for matching instructions.

    Returns (covergroup_content, init_content).
    """
    covergroup_lines: list[str] = []
    init_lines: list[str] = []

    for instr, _instr_type in instr_keys:
        cps = tp[(instr, _instr_type)]
        if not _matches_xlen(cps, has_rv32, has_rv64):
            continue

        is_vector = _is_vector(arch)
        sews = [None] if not is_vector else _get_test_sews(cps)

        for sew in sews:
            # Instruction header
            if is_vector:
                covergroup_lines.append(
                    customize_template(templates, "instruction_vector", name, instr, effew=str(sew))
                )
                init_lines.append(customize_template(templates, "init_vector", name, instr, effew=str(sew)))
            else:
                covergroup_lines.append(customize_template(templates, "instruction", name, instr))
                init_lines.append(customize_template(templates, "init", name, instr))

            # SsstrictV templates reference a small set of helpers (vtype_lmul_*,
            # std_trap_vec, mask_enabled, vd_v0, vd/vs1/vs2_all_reg_unaligned_lmul_*,
            # vstart_zero, vl_nonzero, vtype_prev_vill_*, vtype_all_lmulge1).
            # We include a SsstrictV-scoped header rather than the full standard
            # vector header so the SsstrictV covergroups don't pick up dozens of
            # unrelated 32-bin sweeps (vd_all_reg, vs1_all_reg, etc.) that aren't in
            # SsstrictV's testplan and would inflate the corpus past the linker's
            # ±1MiB JAL range. Other priv vector arches (ExceptionsVx/Vls/Vf)
            # intentionally use a small, focused set of coverpoints (cp_vill /
            # cp_vstart / cp_vstart_gt_vl) and must not pull in either header.
            if arch.startswith(("SsstrictV", "SsstrictZv")):
                covergroup_lines.append('    `include "general/RISCV_coverage_ssstrictv_helpers.svh"\n')

            # Coverpoint entries (skip metadata columns: sample_*, RV32, RV64, EFFEW*)
            # VCS requires coverpoints to be declared before cross references.
            early_cps = ("cp_frm_2", "cp_frm_3", "cp_frm_4", "std_vec")
            ordered_cps = sorted(
                cps, key=lambda cp: (0 if cp.startswith(early_cps) else 2 if cp.startswith("cr_") else 1, cp)
            )
            # Per-operand cross filtering depends only on the instruction, so resolve
            # its operand presence and max LMUL once rather than per coverpoint.
            has_vd, has_vs1, has_vs2 = _operand_presence(_instr_type)
            max_lmul = _max_legal_lmul_for_instruction(instr)
            for cp in ordered_cps:
                resolved = _resolve_coverpoint(cp, instr, sew, templates)
                if resolved is None:
                    continue
                rendered = customize_template(templates, resolved, arch, instr) + "\n"
                covergroup_lines.append(_filter_per_operand_crosses(rendered, has_vd, has_vs1, has_vs2, max_lmul))

            # Instruction footer
            covergroup_lines.append(customize_template(templates, "endgroup", name, instr))

    return "".join(covergroup_lines), "".join(init_lines)


def _guard(extension: tuple[str, ...], content: str) -> str:
    """Wrap content in `ifdef <EXT>_SUPPORTED for each extension of an ExtraExtensions entry."""
    for ext in reversed(extension):
        content = f"`ifdef {ext.upper()}_SUPPORTED\n{content}`endif\n"
    return content


def _extra_name(arch: str, extension: tuple[str, ...]) -> str:
    """Name prefix for an ExtraExtensions group: the suite followed by its extensions, e.g. ZfaZfhD for Zfh:D."""
    return arch + "".join(extension)


def _gen_sample_arm(templates: dict[str, str], instr: str, calls: list[str]) -> str:
    """Generate the sample function's case arm for instr around the given sample calls."""
    return (
        customize_template(templates, "covergroup_case_begin", instr=instr)
        + "".join(calls)
        + customize_template(templates, "covergroup_case_end")
    )


def _gen_covergroup_samples(
    instr_keys: list[tuple[str, str]],
    templates: dict[str, str],
    tp: dict[tuple[str, str], list[str]],
    arch: str,
    has_rv32: bool,
    has_rv64: bool,
    extras: dict[tuple[str, ...], Testplan],
    effew: str = "",
) -> str:
    """Generate covergroup sample function calls for matching instructions and ExtraExtensions rows."""
    lines: list[str] = []
    template = "covergroup_case_sample" if not _is_vector(arch) else "covergroup_sample_vector"
    for key in sorted(set(instr_keys).union(*extras.values())):
        instr = key[0]
        extra_rows = [extension for extension, group in sorted(extras.items()) if key in group]
        cps = tp[key] if key in tp else extras[extra_rows[0]][key]
        if not _matches_xlen(cps, has_rv32, has_rv64):
            continue

        if extra_rows:
            base_calls = [customize_template(templates, template, arch, instr, effew=effew)] if key in tp else []
            extra_calls = {
                ext: customize_template(templates, template, _extra_name(arch, ext), instr, effew=effew)
                for ext in extra_rows
            }
            if not base_calls and len(extra_calls) == 1:
                ((ext, call),) = extra_calls.items()
                lines.append(_guard(ext, _gen_sample_arm(templates, instr, [call])))
            else:
                guarded_calls = [_guard(ext, call) for ext, call in extra_calls.items()]
                lines.append(_gen_sample_arm(templates, instr, base_calls + guarded_calls))
            continue

        call = customize_template(templates, template, arch, instr, effew=effew)
        lines.append(_gen_sample_arm(templates, instr, [call]))

    return "".join(lines)


def _gen_instruction_samples(
    instr_keys: list[tuple[str, str]],
    templates: dict[str, str],
    tp: dict[tuple[str, str], list[str]],
    arch: str,
    has_rv32: bool,
    has_rv64: bool,
) -> str:
    """Generate instruction sample case entries (the decode switch body)."""
    lines: list[str] = []
    for instr, _instr_type in instr_keys:
        cps = tp[(instr, _instr_type)]
        if not _matches_xlen(cps, has_rv32, has_rv64):
            continue
        lines.extend(customize_template(templates, cp, arch, instr) for cp in cps if cp.startswith("sample_"))
    return "".join(lines)


##################################
# File writers
##################################


def _write_extension_files(
    arch: str,
    tp: dict[tuple[str, str], list[str]],
    templates: dict[str, str],
    output_dir: Path,
    *,
    vector: bool,
    extras: dict[tuple[str, ...], Testplan],
) -> None:
    """Write the _coverage.svh / _coverage_init.svh pair for one extension.

    When *vector* is True the vector-flavored header/sample templates are used,
    an EFFEW substitution is made available in the header, and the instruction
    key list is filtered to the matching SEW. *extras* holds the testplan's
    ExtraExtensions rows by extension; their covergroups follow the base
    covergroups inside `ifdef <EXT>_SUPPORTED guards.
    """
    instr_keys = sorted(tp.keys())

    header_tmpl = "header"
    sample_header_tmpl = "covergroup_sample_header_vector" if vector else "covergroup_sample_header"
    sample_end_tmpl = "covergroup_sample_end_vector" if vector else "covergroup_sample_end"

    lines: list[str] = [customize_template(templates, header_tmpl, arch)]
    init_lines: list[str] = [customize_template(templates, "initheader", arch)]

    # Covergroup definitions: common instructions, then RV32-only, then RV64-only;
    # then the same for each group of ExtraExtensions rows inside its extension guards
    for extension, group in [((), tp), *sorted(extras.items())]:
        group_keys = instr_keys if not extension else sorted(group.keys())
        name = _extra_name(arch, extension)
        instr_content, init_content = _gen_instrs(group_keys, templates, group, arch, True, True, name)
        group_lines, group_init_lines = [instr_content], [init_content]

        for rv32, rv64, exclude_marker in ((True, False, "RV64"), (False, True, "RV32")):
            if _any_xlen_exclusion(exclude_marker, group_keys, group):
                guard = customize_template(templates, "RV32" if rv32 else "RV64", arch)
                end = customize_template(templates, "end", arch)
                instr_content, init_content = _gen_instrs(group_keys, templates, group, arch, rv32, rv64, name)
                group_lines.extend([guard, instr_content, end])
                group_init_lines.extend([guard, init_content, end])
        lines.append(_guard(extension, "".join(group_lines)))
        init_lines.append(_guard(extension, "".join(group_init_lines)))

    # Covergroup sample functions with the same XLEN ifdef structure
    all_rows = {key: cps for group in [tp, *extras.values()] for key, cps in group.items()}
    all_keys = sorted(set(instr_keys).union(*extras.values()))

    lines.append(customize_template(templates, sample_header_tmpl, arch))
    if vector:
        all_sews = [8, 16, 32, 64]
        for sew in all_sews:
            relevant_instrs = [instr for instr, cps in all_rows.items() if sew in _get_test_sews(cps)]
            relevant_extras = {
                extensions: {instr: cps for instr, cps in group.items() if sew in _get_test_sews(cps)}
                for extensions, group in extras.items()
            }

            lines.append(customize_template(templates, "covergroup_case_header_vector", arch, effew=str(sew)))
            lines.append(
                _gen_covergroup_samples(
                    relevant_instrs, templates, tp, arch, True, True, extras=relevant_extras, effew=str(sew)
                )
            )
            for rv32, rv64, exclude_marker in ((True, False, "RV64"), (False, True, "RV32")):
                if _any_xlen_exclusion(exclude_marker, all_keys, all_rows):
                    lines.append(customize_template(templates, "RV32" if rv32 else "RV64", arch))
                    lines.append(
                        _gen_covergroup_samples(
                            relevant_instrs, templates, tp, arch, rv32, rv64, extras=relevant_extras, effew=str(sew)
                        )
                    )
                    lines.append(customize_template(templates, "end", arch))
            lines.append(customize_template(templates, "covergroup_case_end_vector", arch))
        lines.append(customize_template(templates, sample_end_tmpl, arch))
    else:
        lines.append(_gen_covergroup_samples(instr_keys, templates, tp, arch, True, True, extras=extras))
        for rv32, rv64, exclude_marker in ((True, False, "RV64"), (False, True, "RV32")):
            if _any_xlen_exclusion(exclude_marker, all_keys, all_rows):
                lines.append(customize_template(templates, "RV32" if rv32 else "RV64", arch))
                lines.append(_gen_covergroup_samples(instr_keys, templates, tp, arch, rv32, rv64, extras=extras))
                lines.append(customize_template(templates, "end", arch))
        lines.append(customize_template(templates, sample_end_tmpl, arch))

    _write_if_changed(output_dir / f"{arch}_coverage.svh", "".join(lines))
    _write_if_changed(output_dir / f"{arch}_coverage_init.svh", "".join(init_lines))


@dataclass
class _CovergroupJob:
    """One per-extension covergroup file pair to write."""

    arch: str
    tp: dict[tuple[str, str], list[str]]
    output_dir: Path
    vector: bool
    extras: dict[tuple[str, ...], Testplan]


def _plan_coverage_jobs(
    test_plans: dict[str, dict[tuple[str, str], list[str]]],
    output_dir: Path,
    extra_testplans: dict[str, dict[tuple[str, ...], Testplan]],
) -> list[_CovergroupJob]:
    """Collect the unpriv per-extension covergroup jobs (writes go in output_dir/unpriv)."""
    unpriv_dir = output_dir / "unpriv"
    unpriv_dir.mkdir(parents=True, exist_ok=True)
    priv_dir = output_dir / "priv"
    priv_dir.mkdir(parents=True, exist_ok=True)
    return [
        _CovergroupJob(
            arch, tp, (priv_dir if _is_priv(arch) else unpriv_dir), _is_vector(arch), extra_testplans.get(arch, {})
        )
        for arch, tp in test_plans.items()
    ]


def write_coverage_headers(
    test_plans: dict[str, dict[tuple[str, str], list[str]]],
    output_dir: Path,
    templates: dict[str, str],
) -> None:
    """Generate and write the shared coverage header files in the coverage/ subdirectory."""
    coverage_dir = output_dir / "coverage"
    coverage_dir.mkdir(parents=True, exist_ok=True)

    # Collect extension names from both unpriv testplans and existing priv covergroups
    keys = set(test_plans.keys())
    priv_path = output_dir / "priv"
    if priv_path.exists():
        keys.update(f.stem.split("_")[0] for f in priv_path.iterdir() if f.name.endswith("_coverage.svh"))
    sorted_keys = sorted(keys)

    # RISCV_coverage_config.svh — ifdef includes for each extension
    lines: list[str] = [customize_template(templates, "config_header")]
    for arch in sorted_keys:
        lines.append(f"`ifdef {arch.upper()}_COVERAGE\n")
        lines.append(f'  `include "{arch}_coverage.svh"\n')
        lines.append("`endif\n")
    _write_if_changed(coverage_dir / "RISCV_coverage_config.svh", "".join(lines))

    # RISCV_coverage_base_init.svh — init calls for each extension
    lines = [customize_template(templates, "base_init_header")]
    for arch in sorted_keys:
        lines.append(customize_template(templates, "coverageinit", arch))
    _write_if_changed(coverage_dir / "RISCV_coverage_base_init.svh", "".join(lines))

    # RISCV_coverage_base_sample.svh — sample calls for each extension
    lines = [customize_template(templates, "base_sample_header")]
    for arch in sorted_keys:
        lines.append(customize_template(templates, "coveragesample", arch))
    _write_if_changed(coverage_dir / "RISCV_coverage_base_sample.svh", "".join(lines))


def _merge_instruction_testplans(
    test_plans: dict[str, dict[tuple[str, str], list[str]]],
    instruction_formats: dict[tuple[str, str], list[str]],
    extra_testplans: dict[str, dict[tuple[str, ...], Testplan]],
) -> dict[tuple[str, str], list[str]]:
    """Merge testplan and extra instruction formats into a single mapping with unique instruction entries."""
    merged = dict(instruction_formats)
    for arch in sorted(test_plans.keys()):
        if arch == "E":
            continue  # E is a duplicate of I
        tp = test_plans[arch]
        for key in sorted(tp.keys()):
            if key not in merged:
                merged[key] = tp[key]
            elif "RV32" not in merged[key] and "RV32" in tp[key]:
                merged[key].append("RV32")
            elif "RV64" not in merged[key] and "RV64" in tp[key]:
                merged[key].append("RV64")
    # Instructions that appear only in ExtraExtensions rows
    for arch in sorted(extra_testplans):
        for _, group in sorted(extra_testplans[arch].items()):
            for key in sorted(group):
                if key not in merged:
                    merged[key] = group[key]
                elif "RV32" not in merged[key] and "RV32" in group[key]:
                    merged[key].append("RV32")
                elif "RV64" not in merged[key] and "RV64" in group[key]:
                    merged[key].append("RV64")
    return merged


def write_instruction_sample_file(
    test_plans: dict[str, dict[tuple[str, str], list[str]]],
    instruction_formats: dict[tuple[str, str], list[str]],
    templates: dict[str, str],
    output_dir: Path,
    extra_testplans: dict[str, dict[tuple[str, ...], Testplan]],
) -> None:
    """Generate and write RISCV_instruction_sample.svh with a complete instruction decode case statement.

    This file must always contain ALL instructions regardless of extension filtering,
    because the case statement is used for runtime instruction decoding.
    """
    coverage_dir = output_dir / "coverage"
    coverage_dir.mkdir(parents=True, exist_ok=True)

    merged_tp = _merge_instruction_testplans(test_plans, instruction_formats, extra_testplans)
    instr_keys = sorted(merged_tp.keys())

    lines: list[str] = [customize_template(templates, "instruction_sample_header")]
    lines.append(_gen_instruction_samples(instr_keys, templates, merged_tp, "", True, True))
    if _any_xlen_exclusion("RV64", instr_keys, merged_tp):
        lines.append(customize_template(templates, "RV32"))
        lines.append(_gen_instruction_samples(instr_keys, templates, merged_tp, "", True, False))
        lines.append(customize_template(templates, "end"))
    if _any_xlen_exclusion("RV32", instr_keys, merged_tp):
        lines.append(customize_template(templates, "RV64"))
        lines.append(_gen_instruction_samples(instr_keys, templates, merged_tp, "", False, True))
        lines.append(customize_template(templates, "end"))

    lines.append(customize_template(templates, "instruction_sample_end"))
    _write_if_changed(coverage_dir / "RISCV_instruction_sample.svh", "".join(lines))


##################################
# Entry point
##################################


def generate_covergroups(testplan_dir: Path, output_dir: Path, extensions: str = "all", exclude: str = "") -> None:
    """Main entry point: read testplans, generate all coverage files."""
    all_test_plans, extra_testplans = read_testplans(testplan_dir)
    if extensions != "all" or exclude != "":
        test_plans = _filter_testplans(all_test_plans, extensions, exclude)
    else:
        test_plans = all_test_plans

    templates = read_covergroup_templates()
    instruction_formats = _parse_testplan_groups(testplan_dir / "coverage" / "instruction_formats.csv")[()]

    jobs = _plan_coverage_jobs(test_plans, output_dir, extra_testplans)
    with _progress("Generating covergroups...") as progress:
        task_id = progress.add_task("covergroups", total=len(jobs))
        for job in jobs:
            _write_extension_files(job.arch, job.tp, templates, job.output_dir, vector=job.vector, extras=job.extras)
            progress.advance(task_id)

    write_coverage_headers(all_test_plans, output_dir, templates)
    write_instruction_sample_file(all_test_plans, instruction_formats, templates, output_dir, extra_testplans)
    rprint(f"[bold green]✓ Generated covergroups for {len(test_plans)} extension(s)[/]")
