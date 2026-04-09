#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Build prompts for Claude CLI invocations to write custom coverpoint scripts."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
CUSTOM_DIR = REPO_ROOT / "generators" / "testgen" / "scripts" / "custom"
TEMPLATES_DIR = REPO_ROOT / "generators" / "coverage" / "templates" / "vector"


def find_coverage_template(coverpoint_name: str) -> str | None:
    """Find the coverage template file for a coverpoint, if it exists.

    Coverage templates may be named exactly after the coverpoint or may
    contain the coverpoint as a cross/coverpoint inside a broader template.
    """
    from testplan_manager import EXPLICIT_COLUMN_MAP

    # Direct match: cp_custom_foo.sv
    direct = TEMPLATES_DIR / f"{coverpoint_name}.sv"
    if direct.exists():
        return str(direct)

    # Check explicit column mapping (covers cases like cp_custom_vfp_state)
    if coverpoint_name in EXPLICIT_COLUMN_MAP:
        mapped = TEMPLATES_DIR / f"{EXPLICIT_COLUMN_MAP[coverpoint_name]}.sv"
        if mapped.exists():
            return str(mapped)

    # Check if the coverpoint is defined inside another template
    # e.g. cp_custom_vfp_flags_set is inside cp_custom_vfp_flags.sv
    # Try progressively shorter prefixes
    parts = coverpoint_name.split("_")
    for end in range(len(parts) - 1, 2, -1):  # at least "cp_custom_X"
        candidate = TEMPLATES_DIR / ("_".join(parts[:end]) + ".sv")
        if candidate.exists():
            return str(candidate)

    return None


def build(
    coverpoint_name: str,
    instructions: list[str],
    goal: str = "",
    feature_description: str = "",
    expectation: str = "",
    bins: str = "",
    notes: str = "",
    template_path: str | None = None,
    iteration: int = 0,
    previous_coverage: str = "",
    category: str = "Vf",
) -> str:
    """Build the prompt string for a Claude CLI invocation.

    Args:
        coverpoint_name: The coverpoint name (e.g. cp_custom_vfp_flags_set)
        instructions: List of instruction mnemonics this coverpoint applies to
        goal: Goal from definitions CSV
        feature_description: Feature description from definitions CSV
        expectation: Expected behavior from definitions CSV
        bins: Number/description of bins from definitions CSV
        notes: Additional notes from definitions CSV
        template_path: Path to coverage template .sv file, if found
        iteration: Iteration number (0 = first attempt)
        previous_coverage: Coverage feedback from previous iteration

    Returns:
        Prompt string for claude CLI
    """
    guide_path = CUSTOM_DIR / "CLAUDE-custom-testgen.md"
    knowledge_path = CUSTOM_DIR / "claude-scripts" / "knowledge.md"
    script_path = CUSTOM_DIR / f"{coverpoint_name}.py"

    sections = []

    # Header
    sections.append(f"# Task: Write a custom coverpoint test generation script for `{coverpoint_name}`\n")

    # Essential reading
    sections.append("## Step 1: Read reference files\n")
    sections.append(f"Read `{guide_path}` for the API reference on how to write custom test generation scripts.")
    sections.append(f"Read `{knowledge_path}` for accumulated tips from previous coverpoint runs.\n")

    # Coverpoint specification
    sections.append("## Step 2: Understand the coverpoint\n")
    sections.append(f"**Coverpoint name:** `{coverpoint_name}`")
    if goal:
        sections.append(f"**Goal:** {goal}")
    if feature_description:
        sections.append(f"**Feature description:** {feature_description}")
    if expectation:
        sections.append(f"**Expectation:** {expectation}")
    if bins:
        sections.append(f"**Number of bins:** {bins}")
    if notes:
        sections.append(f"**Notes:** {notes}")
    sections.append(f"\n**Instructions this coverpoint applies to:** {', '.join(instructions)}\n")

    # Coverage template
    if template_path:
        sections.append("## Step 3: Read the coverage template\n")
        sections.append(f"Read `{template_path}` to see the exact SystemVerilog bins that need to be covered. ")
        sections.append("Each bin in the template must be hit by your generated tests. Pay close attention to ")
        sections.append("cross coverage definitions - they require specific combinations of coverpoints to be hit simultaneously.\n")

    # Script writing instructions
    sections.append(f"## Step {'4' if template_path else '3'}: Write the script\n")
    sections.append(f"Write a Python script at `{script_path}` that:")
    sections.append(f"- Uses the `@register(\"{coverpoint_name}\")` decorator from `coverpoint_registry`")
    sections.append("- Exports a `make(test, sew)` function (test = instruction mnemonic, sew = element width)")
    sections.append("- Generates test cases that cover ALL bins in the coverage template")
    sections.append("- Follows the patterns in CLAUDE-custom-testgen.md")
    sections.append("- Imports helpers from `vector_testgen_common`\n")

    # Build and test instructions
    step_num = 5 if template_path else 4
    sections.append(f"## Step {step_num}: Build and check coverage\n")
    sections.append("Run the following commands to build and check coverage:")
    sections.append("```bash")
    sections.append(f"cd {REPO_ROOT}")
    sections.append("make clean && make vector-tests && make coverage")
    sections.append("```\n")
    sections.append("Then check the uncovered reports for your coverpoint:")
    sections.append("```bash")
    cat_config = {
        "Vf": {"prefix": "VfCustom", "effews": ["16", "32", "64"]},
        "Vls": {"prefix": "VlsCustom", "effews": ["8", "16", "32", "64"]},
    }
    cfg = cat_config.get(category, cat_config["Vf"])
    for xlen in ["rv32", "rv64"]:
        for effew in cfg["effews"]:
            report = REPO_ROOT / "work" / f"sail-{xlen}-max" / "reports" / f"{cfg['prefix']}{effew}_uncovered.txt"
            sections.append(f"grep -A 5 '{coverpoint_name}' {report}")
    sections.append("```\n")

    # Iteration feedback
    if iteration > 0 and previous_coverage:
        sections.append(f"## ITERATION {iteration}: Previous coverage results\n")
        sections.append("Your previous script did not achieve full coverage. Here are the results:\n")
        sections.append(previous_coverage)
        sections.append("\nPlease update the script to cover the remaining uncovered bins.\n")

    # Iteration limit
    step_num += 1
    sections.append(f"## Step {step_num}: Iterate if needed\n")
    sections.append("If coverage is not 100%, update the script and re-run `make clean && make vector-tests && make coverage`.")
    sections.append("You may iterate up to 3 times. Focus on the uncovered bins shown in the report.\n")

    # Knowledge update
    step_num += 1
    sections.append(f"## Step {step_num}: Update knowledge base\n")
    sections.append(f"After finishing (whether successful or not), append any useful learnings to `{knowledge_path}`.")
    sections.append("Include:")
    sections.append(f"- What worked for `{coverpoint_name}`")
    sections.append("- Any pitfalls you encountered")
    sections.append("- API quirks or corrections")
    sections.append("- Patterns that could help future coverpoints\n")

    return "\n".join(sections)


if __name__ == "__main__":
    # Demo: build a prompt for a test coverpoint
    prompt = build(
        coverpoint_name="cp_custom_vfp_flags_set",
        instructions=["vfadd.vv", "vfadd.vf", "vfsub.vv"],
        goal="Confirm that vector fp exceptions set the fp exception flags",
        feature_description="Reference fflags_vduon for target test cases",
        expectation="Flags properly set",
        bins="10",
        template_path=str(TEMPLATES_DIR / "cp_custom_vfp_flags.sv"),
    )
    print(prompt)
