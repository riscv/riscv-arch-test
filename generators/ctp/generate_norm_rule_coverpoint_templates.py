#!/usr/bin/env -S uv run
# SPDX-License-Identifier: Apache-2.0
#
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
Generate normative rule to coverpoint mapping template YAML files.

Each norm: tag in the ISA manual is one normative rule, named by the tag without the
norm: prefix. For each chapter of the manual, create a YAML file in
coverpoints/norm/yaml/chapters that maps each rule in that chapter to an empty
coverpoint list, with the rule's text from norm-rules.json as a comment.
"""

import json
import re
import textwrap
from pathlib import Path
from typing import Any


def load_rules_by_chapter(json_path: Path) -> dict[str, list[dict[str, Any]]]:
    """Load norm-rules.json and group the rules by chapter, keeping document order."""
    with json_path.open() as f:
        data = json.load(f)

    chapters: dict[str, list[dict[str, Any]]] = {}
    for rule in data.get("normative_rules", []):
        if rule.get("name"):
            chapters.setdefault(rule.get("chapter_name") or "unknown", []).append(rule)
    return chapters


def chapter_filename(chapter: str) -> str:
    """File name for a chapter title, e.g. 'Atomic Instructions' -> 'atomic-instructions.yaml'."""
    return re.sub(r"[^a-z0-9]+", "-", chapter.lower()).strip("-") + ".yaml"


def write_chapter(output_path: Path, chapter: str, rules: list[dict[str, Any]]) -> None:
    """Write one template file with an empty coverpoint list for each rule."""
    with output_path.open("w") as f:
        f.write("# Normative rule to coverpoint mappings\n")
        f.write(f"# Generated from the riscv-isa-manual normative rules of chapter: {chapter}\n\n")
        f.write("normative_rule_definitions:\n")
        for rule in rules:
            # YAML forbids non-printable characters even in comments.
            text = "".join(c if c.isprintable() else " " for c in str(rule.get("text", "")))
            text = " ".join(text.split()) or f"TODO: Add description for {rule['name']}"
            for line in textwrap.wrap(text, width=80, break_long_words=False, break_on_hyphens=False):
                f.write(f"  # {line}\n")
            f.write(f"  - name: {rule['name']}\n")
            f.write('    coverpoint: [""]\n')
            f.write("\n")


def main() -> None:
    # Set up paths
    script_dir = Path(__file__).parent
    riscv_arch_test_dh_dir = script_dir.parent.parent
    riscv_isa_manual_dir = riscv_arch_test_dh_dir.parent / "riscv-isa-manual"
    norm_rules_json = riscv_isa_manual_dir / "build" / "norm-rules.json"
    output_dir = riscv_arch_test_dh_dir / "coverpoints" / "norm" / "yaml" / "chapters"

    # Validate paths
    if not norm_rules_json.exists():
        print(f"Error: {norm_rules_json} not found")
        return

    # Load the normative rules JSON
    print(f"Loading normative rules from {norm_rules_json}...")
    chapters = load_rules_by_chapter(norm_rules_json)
    print(f"Loaded {sum(len(r) for r in chapters.values())} normative rules in {len(chapters)} chapters")

    output_dir.mkdir(parents=True, exist_ok=True)
    for chapter, rules in chapters.items():
        output_path = output_dir / chapter_filename(chapter)
        write_chapter(output_path, chapter, rules)
        print(f"  {output_path.name}: {len(rules)} rules")

    print(f"\nOutput files created in {output_dir}")


if __name__ == "__main__":
    main()
