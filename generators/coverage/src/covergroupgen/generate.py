##################################
# generate.py
#
# David_Harris@hmc.edu 15 August 2025
# SPDX-License-Identifier: Apache-2.0
#
# Generate functional covergroups for RISC-V instructions
##################################

from __future__ import annotations

import csv
import importlib.resources
import math
import re
from difflib import get_close_matches
from pathlib import Path

from rich.progress import track

# Coverpoints whose template name depends on the SEW (element width).
SEW_DEPENDENT_CPS = {
    "cp_vs2_edges_f",
    "cp_vs1_edges_f",
    "cp_custom_shift_wv",
    "cp_custom_shift_wx",
    "cp_custom_shift_vv",
    "cp_custom_shift_vx",
    "cp_custom_shift_vi",
    "cp_custom_vindex",
    "cr_vs2_vs1_edges_f",
    "cp_fs1_edges_v",
    "cr_vs2_fs1_edges",
    "cr_vl_lmul",
}

# Vector extension prefixes used to identify vector architectures.
VECTOR_PREFIXES = ("Vx", "Zv", "Vls", "Vf")

# Subset of vector prefixes that support widening instructions.
VECTOR_WIDEN_PREFIXES = ("Vx", "Vls", "Vf")


##################################
# Reading testplans and templates
##################################


def read_testplans(testplan_dir: Path) -> dict[str, dict[tuple[str, str], list[str]]]:
    """Read all CSV testplan files and return a dict mapping extension name to testplan.

    Each CSV file produces one testplan entry keyed by the file's stem (e.g. "I", "Zba").
    Some extensions are expanded:
      - "I" is duplicated as "E"
      - Vector extensions (Vx, Vls, Zvkb) are expanded to per-SEW variants (Vx8, Vx16, ...)
      - Floating-point vector extensions (Vf) are expanded to SEW 16/32/64
    """
    testplans: dict[str, dict[tuple[str, str], list[str]]] = {}

    for csv_path in testplan_dir.glob("*.csv"):
        arch = csv_path.stem

        # Parse the CSV into a dict of (instruction, type) -> coverpoints
        tp: dict[tuple[str, str], list[str]] = {}
        with csv_path.open() as csvfile:
            for row in csv.DictReader(csvfile):
                if "Instruction" not in row:
                    raise ValueError(
                        f"Error reading testplan {csv_path.name}. "
                        "Did you remember to shrink the .csv files after expanding?"
                    )
                instr = row["Instruction"]
                instr_type = row["Type"]

                # Build list of coverpoints from the remaining columns
                cps: list[str] = []
                del row["Instruction"]
                for key, value in row.items():
                    if not isinstance(value, str) or value == "":
                        continue
                    if key == "Type":
                        cps.append(f"sample_{value}")
                    else:
                        # For special entries, append the value as a suffix
                        # e.g. cp_rd_edges with value "lui" becomes cp_rd_edges_lui
                        if value != "x":
                            key = f"{key}_{value}"
                        cps.append(key)

                tp[(instr, instr_type)] = cps

        testplans[arch] = tp

        # Duplicate I testplan for E
        if arch == "I":
            testplans["E"] = tp

        # Expand vector extensions into per-SEW variants, replacing the base entry
        sew_variants: list[str] | None = None
        if any(prefix in arch for prefix in ("Vx", "Vls", "Zvbb", "Zvkb")):
            sew_variants = ["8", "16", "32", "64"]
        elif "Vf" in arch:
            sew_variants = ["16", "32", "64"]  # SEW of 8 is not supported for vector floating point
        if sew_variants is not None:
            for sew in sew_variants:
                testplans[f"{arch}{sew}"] = tp
            del testplans[arch]

    return testplans


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

    Placeholders replaced: INSTRNODOT, INSTR, ARCHUPPER, ARCHCASE, ARCH,
    and (if effew is set) TWOEFFEW, EFFEW, EFFVSEW.
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

    result = (
        templates[name]
        .replace("INSTRNODOT", instr.replace(".", "_"))
        .replace("INSTR", instr)
        .replace("ARCHUPPER", arch.upper())
        .replace("ARCHCASE", arch)
        .replace("ARCH", arch.lower())
    )
    if effew:
        result = (
            result.replace("TWOEFFEW", str(2 * int(effew)))
            .replace("EFFEW", str(int(effew)))
            .replace("EFFVSEW", str(int(math.log2(int(effew))) - 3))
        )
    return result


def _get_effew(arch: str) -> str:
    """Extract the effective element width (SEW) from an architecture name.

    Examples: "Vx32" -> "32", "Zvfhmin" -> "16"
    """
    match = re.search(r"(\d+)$", arch)
    if match:
        return match.group(1)
    if arch in ("Zvfhmin", "Zvfbfmin", "Zvfbfwma"):
        return "16"
    raise ValueError(f"Arch does not contain an expected integer: '{arch}'")


def _is_vector(arch: str) -> bool:
    return arch.startswith(VECTOR_PREFIXES)


def _is_vector_widen(arch: str, instr: str) -> bool:
    """Check if this is a vector widening instruction."""
    return arch.startswith(VECTOR_WIDEN_PREFIXES) and (instr.startswith(("vw", "vfw")) or ".w" in instr)


def _get_sorted_instr_keys(tp: dict[tuple[str, str], list[str]], arch: str) -> list[tuple[str, str]]:
    """Get sorted instruction keys, filtering by EFFEW for vector architectures.

    Also excludes instructions where nf × EMUL > 8 at this extension's SEW
    (they can never legally execute).  Per-coverpoint LMUL requirements
    (from ``_CP_MIN_LMUL``) are checked so that instructions are kept only
    when at least one non-standard coverpoint is coverable.
    """
    keys = sorted(tp.keys())
    if _is_vector(arch):
        effew = _get_effew(arch)
        keys = [k for k in keys if f"EFFEW{effew}" in tp[k]]
        sew = int(effew)
        # Base filter at LMUL=1
        keys = [k for k in keys if _nf_emul_legal(k[0], sew)]
        # Per-coverpoint LMUL filter: standard coverpoints (cp_asm_count,
        # std_vec) are always present but depend on a test being generated.
        # Only non-standard coverpoints drive test generation, so at least
        # one must be coverable at its template's required LMUL.
        _STANDARD_CPS = {"cp_asm_count", "std_vec"}
        filtered: list[tuple[str, str]] = []
        for k in keys:
            cps = [cp for cp in tp[k] if not cp.startswith(("sample_", "EFFEW")) and cp not in {"RV32", "RV64"}]
            non_standard = [cp for cp in cps if cp not in _STANDARD_CPS]
            if not non_standard:
                # No custom coverpoints — keep (standard-only covergroup)
                filtered.append(k)
            elif any(_nf_emul_legal(k[0], sew, _cp_required_lmul(cp, k[0])) for cp in non_standard):
                filtered.append(k)
        keys = filtered
    return keys


def _nf_emul_legal(instr: str, sew: int, lmul: int = 1) -> bool:
    """Return False if *instr* has nf × EMUL > 8 at *sew* and *lmul*.

    EMUL = EEW × LMUL / SEW.  The check is nf × EMUL ≤ 8.

    Handles indexed (vloxsegNeiM), unit-stride (vlsegNeM / vlsegNeMff),
    strided (vlssegNeM / vsssegNeM), and non-segmented unit-stride
    (vleNff / vleN / vseN) patterns.
    """
    # Indexed segmented: v[ls][ou]xsegNeiM.v
    m = re.match(r"v[ls][ou]xseg(\d+)ei(\d+)\.", instr)
    if m:
        nf, eew = int(m.group(1)), int(m.group(2))
        # For indexed: data EMUL = LMUL, index EMUL = EEW*LMUL/SEW
        # NF applies to data group only; index EMUL must be ≤ 8 independently
        data_emul = lmul
        index_emul = eew * lmul / sew
        return nf * data_emul <= 8 and index_emul <= 8

    # Unit-stride segmented (incl. fault-first): v[ls]segNeM[ff].v
    m = re.match(r"v[ls]seg(\d+)e(\d+)(?:ff)?\.", instr)
    if m:
        nf, eew = int(m.group(1)), int(m.group(2))
        return nf * (eew * lmul / sew) <= 8

    # Strided segmented: v[ls]ssegNeM.v
    m = re.match(r"v[ls]sseg(\d+)e(\d+)\.", instr)
    if m:
        nf, eew = int(m.group(1)), int(m.group(2))
        return nf * (eew * lmul / sew) <= 8

    # Non-segmented unit-stride (incl. fault-first): v[ls]eN[ff].v
    m = re.match(r"v[ls]e(\d+)(?:ff)?\.", instr)
    if m:
        eew = int(m.group(1))
        return (eew * lmul / sew) <= 8

    return True


# Minimum LMUL required by specific coverpoint templates.
# Used to filter out covergroups where the template's cross bins
# cannot be covered due to EMUL constraints.
_CP_MIN_LMUL: dict[str, int] = {
    "cp_custom_ffLS_update_vl": 2,
}


def _cp_required_lmul(cp: str, instr: str) -> int:
    """Return the LMUL required by *cp* for *instr*.

    For most coverpoints, this is the static value from ``_CP_MIN_LMUL``.
    For ``cp_custom_indexed_emul_data_only``, the required LMUL depends on
    the instruction's NF: NF=2→LMUL=4, NF=4→LMUL=2, NF=8→LMUL=1.
    """
    if cp == "cp_custom_indexed_emul_data_only":
        m = re.search(r"seg(\d+)", instr)
        if m:
            nf = int(m.group(1))
            return {2: 4, 4: 2, 8: 1}.get(nf, 1)
        return 1
    return _CP_MIN_LMUL.get(cp, 1)


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


##################################
# Content generation
##################################


def _gen_instrs(
    instr_keys: list[tuple[str, str]],
    templates: dict[str, str],
    tp: dict[tuple[str, str], list[str]],
    arch: str,
    has_rv32: bool,
    has_rv64: bool,
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

        vectorwiden = _is_vector_widen(arch, instr)

        # Instruction header
        if vectorwiden:
            effew = _get_effew(arch)
            covergroup_lines.append(customize_template(templates, "instruction_vector_widen", arch, instr, effew=effew))
            init_lines.append(customize_template(templates, "init_vector_widen", arch, instr, effew=effew))
        else:
            covergroup_lines.append(customize_template(templates, "instruction", arch, instr))
            init_lines.append(customize_template(templates, "init", arch, instr))

        # Coverpoint entries (skip metadata columns: sample_*, RV32, RV64, EFFEW*)
        # VCS requires coverpoints to be declared before they are referenced by cross coverpoints.
        # Some templates embed cross definitions (for example, *_frm templates), so prioritize
        # cp_frm_* declarations first, then regular coverpoints, then explicit cross templates.
        frm_coverpoints = {"cp_frm_2", "cp_frm_3", "cp_frm_4"}
        ordered_cps = sorted(cps, key=lambda cp: (0 if cp in frm_coverpoints else 2 if cp.startswith("cr_") else 1, cp))
        sew = int(_get_effew(arch)) if _is_vector(arch) else 0
        for cp in ordered_cps:
            if cp.startswith(("sample_", "EFFEW")) or cp in {"RV32", "RV64"}:
                continue

            # Skip coverpoints whose LMUL requirement makes this instr illegal
            req_lmul = _cp_required_lmul(cp, instr)
            if sew and req_lmul > 1 and not _nf_emul_legal(instr, sew, req_lmul):
                continue

            # Append SEW suffix for SEW-dependent coverpoints
            if any(sew_cp in cp for sew_cp in SEW_DEPENDENT_CPS):
                cp = cp + "_sew" + _get_effew(arch)

            # Handle conditional SEW inclusion
            if "sew_lte" in cp:
                effew = _get_effew(arch)
                match = re.search(r"(\d+)$", cp)
                if match:
                    max_sew = int(match.group(1))
                    if int(effew) <= max_sew:
                        cp = re.sub(r"_sew_lte_\d+", "", cp)
                        covergroup_lines.append(customize_template(templates, cp, arch, instr))
            else:
                covergroup_lines.append(customize_template(templates, cp, arch, instr))

        # Instruction footer
        if vectorwiden:
            covergroup_lines.append(customize_template(templates, "endgroup_vector_widen", arch, instr))
        else:
            covergroup_lines.append(customize_template(templates, "endgroup", arch, instr))

    return "".join(covergroup_lines), "".join(init_lines)


def _gen_covergroup_samples(
    instr_keys: list[tuple[str, str]],
    templates: dict[str, str],
    tp: dict[tuple[str, str], list[str]],
    arch: str,
    has_rv32: bool,
    has_rv64: bool,
) -> str:
    """Generate covergroup sample function calls for matching instructions."""
    lines: list[str] = []
    for instr, _instr_type in instr_keys:
        cps = tp[(instr, _instr_type)]
        if not _matches_xlen(cps, has_rv32, has_rv64):
            continue

        if arch.startswith(VECTOR_WIDEN_PREFIXES):
            if _is_vector_widen(arch, instr):
                effew = _get_effew(arch)
                lines.append(customize_template(templates, "covergroup_sample_vector_widen", arch, instr, effew=effew))
            else:
                lines.append(customize_template(templates, "covergroup_sample_vector", arch, instr))
        elif arch != "E":  # E currently breaks coverage
            lines.append(customize_template(templates, "covergroup_sample", arch, instr))

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


def _get_sibling_sew_macros(arch: str, all_archs: list[str]) -> list[str]:
    """Return COVER_* macro names for sibling SEW variants of this arch.

    E.g. for "Vf64" with siblings ["Vf16", "Vf32", "Vf64"],
    returns ["COVER_VF16", "COVER_VF32", "COVER_VFCUSTOM16", "COVER_VFCUSTOM32"] (excluding self).
    """
    match = re.search(r"^(.*?)(\d+)$", arch)
    if not match:
        return []
    base = match.group(1)
    siblings = [a for a in all_archs if a != arch and a.startswith(base) and re.match(rf"^{re.escape(base)}\d+$", a)]
    macros = [f"COVER_{a.upper()}" for a in siblings]
    # Also undef the VFCUSTOM* aliases generated by header_vector.sv
    sibling_sews = []
    for a in siblings:
        m = re.search(r"(\d+)$", a)
        if m is None:
            raise ValueError(f"Expected trailing digits in sibling name: {a!r}")
        sibling_sews.append(m.group(1))
    macros.extend(f"COVER_VFCUSTOM{s}" for s in sibling_sews)
    return macros


def write_covergroups(
    test_plans: dict[str, dict[tuple[str, str], list[str]]],
    templates: dict[str, str],
    output_dir: Path,
) -> None:
    """Generate and write per-extension _coverage.svh and _coverage_init.svh files."""
    unpriv_dir = output_dir / "unpriv"
    unpriv_dir.mkdir(parents=True, exist_ok=True)

    all_archs = list(test_plans.keys())

    for arch, tp in track(test_plans.items(), description="[cyan]Generating covergroups...", total=len(test_plans)):
        vector = _is_vector(arch)
        effew = _get_effew(arch) if vector else ""
        instr_keys = _get_sorted_instr_keys(tp, arch)

        lines: list[str] = []
        init_lines: list[str] = []

        # Undef sibling SEW macros so only this arch's macro is active
        # (prevents conflicts when multiple SEW coverage files are compiled together)
        if vector:
            for macro in _get_sibling_sew_macros(arch, all_archs):
                lines.append(f"`ifdef {macro}\n  `undef {macro}\n`endif\n")

        # Header
        header_tmpl = "header_vector" if vector else "header"
        lines.append(customize_template(templates, header_tmpl, arch, effew=effew))
        init_lines.append(customize_template(templates, "initheader", arch))

        # Covergroup definitions with XLEN ifdefs
        # Common instructions (both RV32 and RV64)
        instr_content, init_content = _gen_instrs(instr_keys, templates, tp, arch, True, True)
        lines.append(instr_content)
        init_lines.append(init_content)

        # RV32-only instructions
        if _any_xlen_exclusion("RV64", instr_keys, tp):
            guard = customize_template(templates, "RV32", arch)
            end = customize_template(templates, "end", arch)
            instr_content, init_content = _gen_instrs(instr_keys, templates, tp, arch, True, False)
            lines.extend([guard, instr_content, end])
            init_lines.extend([guard, init_content, end])

        # RV64-only instructions
        if _any_xlen_exclusion("RV32", instr_keys, tp):
            guard = customize_template(templates, "RV64", arch)
            end = customize_template(templates, "end", arch)
            instr_content, init_content = _gen_instrs(instr_keys, templates, tp, arch, False, True)
            lines.extend([guard, instr_content, end])
            init_lines.extend([guard, init_content, end])

        # Covergroup sample functions with XLEN ifdefs
        sample_header = "covergroup_sample_header_vector" if vector else "covergroup_sample_header"
        lines.append(customize_template(templates, sample_header, arch, effew=effew))
        lines.append(_gen_covergroup_samples(instr_keys, templates, tp, arch, True, True))
        if _any_xlen_exclusion("RV64", instr_keys, tp):
            lines.append(customize_template(templates, "RV32", arch))
            lines.append(_gen_covergroup_samples(instr_keys, templates, tp, arch, True, False))
            lines.append(customize_template(templates, "end", arch))
        if _any_xlen_exclusion("RV32", instr_keys, tp):
            lines.append(customize_template(templates, "RV64", arch))
            lines.append(_gen_covergroup_samples(instr_keys, templates, tp, arch, False, True))
            lines.append(customize_template(templates, "end", arch))
        sample_end = "covergroup_sample_end_vector" if vector else "covergroup_sample_end"
        lines.append(customize_template(templates, sample_end, arch))

        # Write both files
        (unpriv_dir / f"{arch}_coverage.svh").write_text("".join(lines))
        (unpriv_dir / f"{arch}_coverage_init.svh").write_text("".join(init_lines))


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
    (coverage_dir / "RISCV_coverage_config.svh").write_text("".join(lines))

    # RISCV_coverage_base_init.svh — init calls for each extension
    lines = [customize_template(templates, "base_init_header")]
    for arch in sorted_keys:
        lines.append(customize_template(templates, "coverageinit", arch))
    (coverage_dir / "RISCV_coverage_base_init.svh").write_text("".join(lines))

    # RISCV_coverage_base_sample.svh — sample calls for each extension
    lines = [customize_template(templates, "base_sample_header")]
    for arch in sorted_keys:
        lines.append(customize_template(templates, "coveragesample", arch))
    (coverage_dir / "RISCV_coverage_base_sample.svh").write_text("".join(lines))


def write_instruction_sample_file(
    test_plans: dict[str, dict[tuple[str, str], list[str]]],
    templates: dict[str, str],
    output_dir: Path,
) -> None:
    """Generate and write RISCV_instruction_sample.svh with a complete instruction decode case statement.

    This file must always contain ALL instructions regardless of extension filtering,
    because the case statement is used for runtime instruction decoding.
    """
    coverage_dir = output_dir / "coverage"
    coverage_dir.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [customize_template(templates, "instruction_sample_header")]
    for arch, tp in test_plans.items():
        if arch == "E":
            continue  # E is a duplicate of I; skip to avoid duplicate case entries
        instr_keys = _get_sorted_instr_keys(tp, arch)

        lines.append(_gen_instruction_samples(instr_keys, templates, tp, arch, True, True))
        if _any_xlen_exclusion("RV64", instr_keys, tp):
            lines.append(customize_template(templates, "RV32", arch))
            lines.append(_gen_instruction_samples(instr_keys, templates, tp, arch, True, False))
            lines.append(customize_template(templates, "end", arch))
        if _any_xlen_exclusion("RV32", instr_keys, tp):
            lines.append(customize_template(templates, "RV64", arch))
            lines.append(_gen_instruction_samples(instr_keys, templates, tp, arch, False, True))
            lines.append(customize_template(templates, "end", arch))

    lines.append(customize_template(templates, "instruction_sample_end"))
    (coverage_dir / "RISCV_instruction_sample.svh").write_text("".join(lines))


def write_priv_covergroups(
    testplan_dir: Path,
    templates: dict[str, str],
    output_dir: Path,
    extensions: str = "all",
    exclude: str = "",
) -> None:
    """Generate per-instruction priv coverage files from testplans/priv/*.csv.

    Reads CSVs from testplan_dir / "priv" and generates _coverage.svh
    and _coverage_init.svh files in output_dir / "priv".
    Skips extensions that already have handwritten coverage files.
    """
    priv_plan_dir = testplan_dir / "priv"
    if not priv_plan_dir.exists():
        return

    priv_output_dir = output_dir / "priv"
    priv_output_dir.mkdir(parents=True, exist_ok=True)

    # Read priv testplans (no SEW expansion needed)
    priv_plans: dict[str, dict[tuple[str, str], list[str]]] = {}
    for csv_path in priv_plan_dir.glob("*.csv"):
        arch = csv_path.stem
        tp: dict[tuple[str, str], list[str]] = {}
        with csv_path.open() as csvfile:
            for row in csv.DictReader(csvfile):
                if "Instruction" not in row:
                    raise ValueError(
                        f"Error reading testplan {csv_path.name}. "
                        "Did you remember to shrink the .csv files after expanding?"
                    )
                instr = row["Instruction"]
                instr_type = row["Type"]
                cps: list[str] = []
                del row["Instruction"]
                for key, value in row.items():
                    if not isinstance(value, str) or value == "":
                        continue
                    if key == "Type":
                        cps.append(f"sample_{value}")
                    else:
                        if value != "x":
                            key = f"{key}_{value}"
                        cps.append(key)
                tp[(instr, instr_type)] = cps
        priv_plans[arch] = tp

    # Apply extension filtering
    if extensions != "all" or exclude != "":
        priv_plans = _filter_testplans(priv_plans, extensions, exclude)

    # Skip extensions that already have handwritten coverage files
    existing_priv = {f.stem.split("_")[0] for f in priv_output_dir.iterdir() if f.name.endswith("_coverage.svh")}

    for arch, tp in track(
        priv_plans.items(), description="[cyan]Generating priv covergroups...", total=len(priv_plans)
    ):
        if arch in existing_priv:
            continue

        instr_keys = sorted(tp.keys())
        lines: list[str] = []
        init_lines: list[str] = []

        # Header
        lines.append(customize_template(templates, "header", arch))
        init_lines.append(customize_template(templates, "initheader", arch))

        # Per-instruction covergroups
        instr_content, init_content = _gen_instrs(instr_keys, templates, tp, arch, True, True)
        lines.append(instr_content)
        init_lines.append(init_content)

        # RV32-only instructions
        if _any_xlen_exclusion("RV64", instr_keys, tp):
            guard = customize_template(templates, "RV32", arch)
            end = customize_template(templates, "end", arch)
            instr_content, init_content = _gen_instrs(instr_keys, templates, tp, arch, True, False)
            lines.extend([guard, instr_content, end])
            init_lines.extend([guard, init_content, end])

        # RV64-only instructions
        if _any_xlen_exclusion("RV32", instr_keys, tp):
            guard = customize_template(templates, "RV64", arch)
            end = customize_template(templates, "end", arch)
            instr_content, init_content = _gen_instrs(instr_keys, templates, tp, arch, False, True)
            lines.extend([guard, instr_content, end])
            init_lines.extend([guard, init_content, end])

        # Sample function
        lines.append(customize_template(templates, "covergroup_sample_header", arch))
        lines.append(_gen_covergroup_samples(instr_keys, templates, tp, arch, True, True))
        if _any_xlen_exclusion("RV64", instr_keys, tp):
            lines.append(customize_template(templates, "RV32", arch))
            lines.append(_gen_covergroup_samples(instr_keys, templates, tp, arch, True, False))
            lines.append(customize_template(templates, "end", arch))
        if _any_xlen_exclusion("RV32", instr_keys, tp):
            lines.append(customize_template(templates, "RV64", arch))
            lines.append(_gen_covergroup_samples(instr_keys, templates, tp, arch, False, True))
            lines.append(customize_template(templates, "end", arch))
        lines.append(customize_template(templates, "covergroup_sample_end", arch))

        # Write files
        (priv_output_dir / f"{arch}_coverage.svh").write_text("".join(lines))
        (priv_output_dir / f"{arch}_coverage_init.svh").write_text("".join(init_lines))


##################################
# Entry point
##################################


def generate_covergroups(testplan_dir: Path, output_dir: Path, extensions: str = "all", exclude: str = "") -> None:
    """Main entry point: read testplans, generate all coverage files."""
    all_test_plans = read_testplans(testplan_dir)
    if extensions != "all" or exclude != "":
        test_plans = _filter_testplans(all_test_plans, extensions, exclude)
    else:
        test_plans = all_test_plans

    templates = read_covergroup_templates()
    write_covergroups(test_plans, templates, output_dir)
    write_priv_covergroups(testplan_dir, templates, output_dir, extensions, exclude)
    write_coverage_headers(test_plans, output_dir, templates)
    write_instruction_sample_file(all_test_plans, templates, output_dir)
