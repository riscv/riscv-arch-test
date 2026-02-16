#!/usr/bin/env python3
##################################
# covergroupgen.py
#
# David_Harris@hmc.edu 15 August 2025
# SPDX-License-Identifier: Apache-2.0
#
# Generate functional covergroups for RISC-V instructions
##################################

import csv
import math
import re
from pathlib import Path
from typing import TextIO

##################################
# Functions
##################################

# readTestplans iterates over all of the CSV testplan files in the testplans directory
# It poupulates a dictionary of dictionaries with
# the top level key being the architecture (e.g. RV64I)
# the second level key being the instruction mnemonic (e.g. add)
# the value being a list of covergroups for that instruction


def read_testplans(testplans_dir: Path) -> tuple[dict[str, dict[tuple[str, str], list[str]]], dict[str, str]]:
    """
    Iterates over all of the CSV testplan files in the provided directory. It populates a dictionary of dictionaries with
    the top level key being the architecture/extension (e.g. RV64I), the second level key being a tuple of
    (instruction mnemonic, type) to allow duplicate instructions with different types, and the value being a list
    of coverpoints for that instruction.
    """
    testplans: dict[str, dict[tuple[str, str], list[str]]] = {}
    arch_sources: dict[str, str] = {}
    coverplan_dirs = [(testplans_dir, "unpriv")]
    for coverplan_dir, source in coverplan_dirs:
        if not coverplan_dir.exists():
            continue  # Skip missing directories
        for file in coverplan_dir.rglob("*.csv"):
            arch = file.stem
            with file.open() as csvfile:
                reader = csv.DictReader(csvfile)
                tp: dict[tuple[str, str], list[str]] = {}
                for row in reader:
                    if "Instruction" not in row:
                        raise ValueError(
                            f"Error reading testplan {file.name}.  Did you remember to shrink the .csv files after expanding?"
                        )
                    instr = row["Instruction"]
                    instr_type = row["Type"]
                    cps: list[str] = []
                    del row["Instruction"]
                    for key, value in row.items():
                        if isinstance(value, str) and value != "":
                            if key == "Type":
                                cps.append(f"sample_{value}")
                            else:
                                if (
                                    value != "x"
                                ):  # for special entries, append the entry name (e.g. cp_rd_edges becomes cp_rd_edges_lui)
                                    key = f"{key}_{value}"
                                cps.append(key)
                    tp[(instr, instr_type)] = cps
            testplans[arch] = tp
            arch_sources[arch] = source
            if arch == "I":  # duplicate I testplan for E
                testplans["E"] = tp
                arch_sources["E"] = source
            if arch == "Vx":
                for effew in ["8", "16", "32", "64"]:
                    testplans[f"Vx{effew}"] = tp
                    arch_sources[f"Vx{effew}"] = source
                del testplans["Vx"]
                del arch_sources["Vx"]
            if arch == "Vls":
                for effew in ["8", "16", "32", "64"]:
                    testplans[f"Vls{effew}"] = tp
                    arch_sources[f"Vls{effew}"] = source
                del testplans["Vls"]
                del arch_sources["Vls"]
            if arch == "Vf":
                for effew in ["16", "32", "64"]:  # SEW of 8 is not supported for vector floating point
                    testplans[f"Vf{effew}"] = tp
                    arch_sources[f"Vf{effew}"] = source
                del testplans["Vf"]
                del arch_sources["Vf"]
    return testplans, arch_sources


def read_covergroup_templates(template_dir: Path) -> dict[str, str]:
    """Read the covergroup templates from the templates directory."""
    covergroupTemplates: dict[str, str] = {}
    for file in template_dir.rglob("*.txt"):
        cg = file.stem
        covergroupTemplates[cg] = file.read_text()
    return covergroupTemplates


def customize_template(covergroup_templates: dict[str, str], name: str, arch: str, instr: str, effew: str = "") -> str:
    """Customize the covergroup template with the given parameters and pick from RV32/RV64 as necessary."""
    if name not in covergroup_templates:
        raise ValueError(f"No template found for '{name}'. Check if there are spaces before or after coverpoint name.")
    template = covergroup_templates[name]
    instr_nodot = instr.replace(".", "_")
    template = (
        template.replace("INSTRNODOT", instr_nodot)
        .replace("INSTR", instr)
        .replace("ARCHUPPER", arch.upper())
        .replace("ARCHCASE", arch)
        .replace("ARCH", arch.lower())
    )
    if effew != "":
        template = (
            template.replace("TWOEFFEW", str(2 * int(effew)))
            .replace("EFFEW", str(int(effew)))
            .replace("EFFVSEW", str(int(math.log2(int(effew))) - 3))
        )
    return template


def any_exclusion(rv: str, instrs: list[tuple[str, str]], tp: dict[tuple[str, str], list[str]]) -> bool:
    """Check if any instruction in this extension is not available in the specified RV32 or RV64."""
    for instr_key in instrs:
        cps = tp[instr_key]
        if rv not in cps:
            return True
    return False


def any_effew_exclusion(effew: str, instrs: list[tuple[str, str]], tp: dict[tuple[str, str], list[str]]) -> bool:
    for instr_key in instrs:
        cps = tp[instr_key]
        if effew not in cps:
            return True
    return False


SEW_DEPENDENT_CPS = [
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
]


def write_instrs(
    f: TextIO,
    finit: TextIO,
    k: list[tuple[str, str]],
    covergroupTemplates: dict[str, str],
    tp: dict[tuple[str, str], list[str]],
    arch: str,
    hasRV32: bool,
    hasRV64: bool,
) -> None:
    """Write the instructions if they match the RV32/RV64 criteria."""
    for instr_key in k:
        instr, _instr_type = instr_key
        cps = tp[instr_key]
        match32 = ("RV32" in cps) ^ (not hasRV32)
        match64 = ("RV64" in cps) ^ (not hasRV64)
        vectorwiden = (arch.startswith("Vx") or arch.startswith("Vls") or arch.startswith("Vf")) and (
            instr.startswith("vw") or instr.startswith("vfw") or (".w" in instr)
        )
        if match32 and match64:
            if vectorwiden:
                effew = get_effew(arch)
                f.write(customize_template(covergroupTemplates, "instruction_vector_widen", arch, instr, effew=effew))
                finit.write(customize_template(covergroupTemplates, "init_vector_widen", arch, instr, effew=effew))
            else:
                f.write(customize_template(covergroupTemplates, "instruction", arch, instr))
                finit.write(customize_template(covergroupTemplates, "init", arch, instr))
            for cp in cps:
                if not (
                    cp.startswith("sample_") or cp == "RV32" or cp == "RV64" or cp.startswith("EFFEW")
                ):  # skip these initial columns
                    if any(substring in cp for substring in SEW_DEPENDENT_CPS):
                        effew = get_effew(arch)
                        cp = cp + "_sew" + effew

                    if "sew_lte" in cp:
                        effew = get_effew(arch)
                        match = re.search(r"(\d+)$", cp)
                        if match:
                            num = int(match.group(1))
                            if int(effew) <= num:  # only_sew8 should only be included if sew = 8
                                cp = re.sub(r"_sew_lte_\d+", "", cp)
                                f.write(customize_template(covergroupTemplates, cp, arch, instr))
                    else:
                        f.write(customize_template(covergroupTemplates, cp, arch, instr))
            if vectorwiden:
                f.write(customize_template(covergroupTemplates, "endgroup_vector_widen", arch, instr))
            else:
                f.write(customize_template(covergroupTemplates, "endgroup", arch, instr))


def write_covergroup_sample_functions(
    f: TextIO,
    k: list[tuple[str, str]],
    covergroupTemplates: dict[str, str],
    tp: dict[tuple[str, str], list[str]],
    arch: str,
    hasRV32: bool,
    hasRV64: bool,
) -> None:
    for instr_key in k:
        instr, _instr_type = instr_key
        cps = tp[instr_key]
        match32 = ("RV32" in cps) ^ (not hasRV32)
        match64 = ("RV64" in cps) ^ (not hasRV64)
        if match32 and match64:
            if arch.startswith("Vx") or arch.startswith("Vls") or arch.startswith("Vf"):
                if instr.startswith("vw") or instr.startswith("vfw") or (".w" in instr):
                    effew = get_effew(arch)
                    f.write(
                        customize_template(
                            covergroupTemplates, "covergroup_sample_vector_widen", arch, instr, effew=effew
                        )
                    )
                else:
                    f.write(customize_template(covergroupTemplates, "covergroup_sample_vector", arch, instr))
            elif arch != "E":  # E currently breaks coverage
                f.write(customize_template(covergroupTemplates, "covergroup_sample", arch, instr))


def write_instruction_sample_function(
    f: TextIO,
    k: list[tuple[str, str]],
    covergroupTemplates: dict[str, str],
    tp: dict[tuple[str, str], list[str]],
    arch: str,
    hasRV32: bool,
    hasRV64: bool,
) -> None:
    for instr_key in k:
        instr, _instr_type = instr_key
        cps = tp[instr_key]
        match32 = ("RV32" in cps) ^ (not hasRV32)
        match64 = ("RV64" in cps) ^ (not hasRV64)
        if match32 and match64:
            for cp in cps:
                if cp in cps and cp.startswith("sample_"):
                    f.write(customize_template(covergroupTemplates, cp, arch, instr))


def get_effew(arch: str) -> str:
    match = re.search(r"(\d+)$", arch)
    if match:
        effew = match.group(1)
    elif arch in ["Zvfhmin", "Zvfbfmin", "Zvfbfwma"]:
        effew = "16"
    else:
        raise ValueError(f"Arch does not contain an expected integer: '{arch}'")
    return effew


def write_coverage_headers(
    test_plans: dict[str, dict[tuple[str, str], list[str]]],
    arch_sources: dict[str, str],
    covergroup_dir: Path,
    covergroup_templates: dict[str, str],
) -> None:
    coverage_dir = covergroup_dir / "coverage"
    coverage_dir.mkdir(parents=True, exist_ok=True)

    # Collect all keys
    keys = set(test_plans.keys())
    priv_path = covergroup_dir / "priv"
    if priv_path.exists():
        keys.update(f.stem.split("_")[0] for f in priv_path.iterdir() if f.name.endswith("_coverage.svh"))
    sorted_keys = sorted(list(keys))

    # Write RISCV_coverage_config.svh
    with (coverage_dir / "RISCV_coverage_config.svh").open("w") as f:
        f.write(customize_template(covergroup_templates, "config_header", "NA", "NA"))
        for arch in sorted_keys:
            f.write(f"`ifdef {arch.upper()}_COVERAGE\n")
            f.write(f'  `include "{arch}_coverage.svh"\n')
            f.write("`endif\n")

    # Write RISCV_coverage_base_init.svh
    with (coverage_dir / "RISCV_coverage_base_init.svh").open("w") as f:
        f.write(customize_template(covergroup_templates, "base_init_header", "NA", "NA"))
        for arch in sorted_keys:
            f.write(customize_template(covergroup_templates, "coverageinit", arch, ""))

    # Write RISCV_coverage_base_sample.svh
    with (coverage_dir / "RISCV_coverage_base_sample.svh").open("w") as f:
        f.write(customize_template(covergroup_templates, "base_sample_header", "NA", "NA"))
        for arch in sorted_keys:
            f.write(customize_template(covergroup_templates, "coveragesample", arch, ""))


# writeCovergroups iterates over the testplans and covergroup templates to generate the covergroups for
# all instructions in each testplan
def write_covergroups(
    test_plans: dict[str, dict[tuple[str, str], list[str]]],
    covergroup_templates: dict[str, str],
    arch_sources: dict[str, str],
    output_dir: Path,
) -> None:
    covergroup_dir = output_dir
    coverageHeaderDir = covergroup_dir / "coverage"
    coverageHeaderDir.mkdir(parents=True, exist_ok=True)

    with (coverageHeaderDir / "RISCV_instruction_sample.svh").open("w") as fsample:
        fsample.write(customize_template(covergroup_templates, "instruction_sample_header", "NA", "NA"))
        for arch, tp in test_plans.items():
            covergroupSubDir = arch_sources.get(arch, "unpriv")
            covergroup_out_dir = covergroup_dir / covergroupSubDir
            covergroup_out_dir.mkdir(parents=True, exist_ok=True)

            file = arch + "_coverage.svh"
            initfile = arch + "_coverage_init.svh"
            print("***** Writing " + file)

            vector = arch.startswith("Vx") or arch.startswith("Zv") or arch.startswith("Vls") or arch.startswith("Vf")

            with (covergroup_out_dir / file).open("w") as f:
                finit = (covergroup_out_dir / initfile).open("w")
                if vector:
                    effew = get_effew(arch)
                    f.write(customize_template(covergroup_templates, "header_vector", arch, "", effew=effew))
                else:
                    f.write(customize_template(covergroup_templates, "header", arch, ""))
                finit.write(customize_template(covergroup_templates, "initheader", arch, ""))

                k = list(tp.keys())
                k.sort()
                if vector:
                    k = [instr_key for instr_key in k if f"EFFEW{effew}" in tp[instr_key]]

                write_instrs(f, finit, k, covergroup_templates, tp, arch, True, True)
                if any_exclusion("RV64", k, tp):
                    f.write(customize_template(covergroup_templates, "RV32", arch, "NA1"))
                    finit.write(customize_template(covergroup_templates, "RV32", arch, "NA1"))
                    write_instrs(f, finit, k, covergroup_templates, tp, arch, True, False)
                    f.write(customize_template(covergroup_templates, "end", arch, "NA1"))
                    finit.write(customize_template(covergroup_templates, "end", arch, "NA1"))
                if any_exclusion("RV32", k, tp):
                    f.write(customize_template(covergroup_templates, "RV64", arch, "NA2"))
                    finit.write(customize_template(covergroup_templates, "RV64", arch, "NA2"))
                    write_instrs(f, finit, k, covergroup_templates, tp, arch, False, True)
                    f.write(customize_template(covergroup_templates, "end", arch, "NA2"))
                    finit.write(customize_template(covergroup_templates, "end", arch, "NA2"))

                # Covergroup sample functions: also separate out generic and ones specific to RV32/RV64 with `ifdefs`
                if vector:
                    f.write(
                        customize_template(
                            covergroup_templates, "covergroup_sample_header_vector", arch, "NA3", effew=effew
                        )
                    )
                else:
                    f.write(customize_template(covergroup_templates, "covergroup_sample_header", arch, "NA3"))
                write_covergroup_sample_functions(f, k, covergroup_templates, tp, arch, True, True)
                if any_exclusion("RV64", k, tp):
                    f.write(customize_template(covergroup_templates, "RV32", arch, "NA4"))
                    write_covergroup_sample_functions(f, k, covergroup_templates, tp, arch, True, False)
                    f.write(customize_template(covergroup_templates, "end", arch, "NA4"))
                if any_exclusion("RV32", k, tp):
                    f.write(customize_template(covergroup_templates, "RV64", arch, "NA5"))
                    write_covergroup_sample_functions(f, k, covergroup_templates, tp, arch, False, True)
                    f.write(customize_template(covergroup_templates, "end", arch, "NA5"))
                if vector:
                    f.write(customize_template(covergroup_templates, "covergroup_sample_end_vector", arch, "NA3"))
                else:
                    f.write(customize_template(covergroup_templates, "covergroup_sample_end", arch, "NA3"))

                # Instruction sample function: also separate out generic and ones specific to RV32/RV64 with `ifdefs`
                write_instruction_sample_function(fsample, k, covergroup_templates, tp, arch, True, True)
                if any_exclusion("RV64", k, tp):
                    fsample.write(customize_template(covergroup_templates, "RV32", arch, "NA4"))
                    write_instruction_sample_function(fsample, k, covergroup_templates, tp, arch, True, False)
                    fsample.write(customize_template(covergroup_templates, "end", arch, "NA4"))
                if any_exclusion("RV32", k, tp):
                    fsample.write(customize_template(covergroup_templates, "RV64", arch, "NA5"))
                    write_instruction_sample_function(fsample, k, covergroup_templates, tp, arch, False, True)
                    fsample.write(customize_template(covergroup_templates, "end", arch, "NA5"))

        fsample.write(customize_template(covergroup_templates, "instruction_sample_end", "NA", "NA"))

    write_coverage_headers(test_plans, arch_sources, covergroup_dir, covergroup_templates)


##################################
# Main Python Script
##################################


def main(testplan_dir: Path, output_dir: Path) -> None:
    test_plans, arch_sources = read_testplans(testplan_dir)
    covergroup_templates = read_covergroup_templates(Path(__file__).parent / "templates")
    write_covergroups(test_plans, covergroup_templates, arch_sources, output_dir)


if __name__ == "__main__":
    test_plan_dir = (Path(__file__).parent / "../../testplans").resolve()
    output_dir = (Path(__file__).parent / "../../coverpoints").resolve()
    main(test_plan_dir, output_dir)
