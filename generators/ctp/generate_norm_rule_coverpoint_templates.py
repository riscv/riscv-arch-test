#!/usr/bin/env python3
"""
Generate normative rule to coverpoint mapping YAML files.

For each normative rule definition YAML file in riscv-isa-manual/normative_rule_defs,
create a corresponding output YAML file in coverpoints/norm/yaml/chapters that maps
each rule to an empty coverpoint list, with comments from norm-rules.json.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any


def load_norm_rules_json(json_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load norm-rules.json and create a name -> rule mapping (case-insensitive)."""
    with open(json_path) as f:
        data = json.load(f)

    rules_map = {}
    for rule in data.get("normative_rules", []):
        name = rule.get("name")
        if name:
            # Store with uppercase key for case-insensitive lookup
            rules_map[name.upper()] = rule

    return rules_map


def get_rule_description(rule: Dict[str, Any]) -> str:
    """Extract description from rule tags."""
    descriptions = []
    for tag in rule.get("tags", []):
        text = tag.get("text", "").strip()
        if text:
            descriptions.append(text)

    return " ".join(descriptions) if descriptions else ""


def process_rule_file(
    input_yaml: Path,
    output_dir: Path,
    rules_map: Dict[str, Dict[str, Any]]
) -> None:
    """Process one normative rule definition file and create output."""
    # Load input YAML
    with open(input_yaml) as f:
        input_data = yaml.safe_load(f)

    if not input_data:
        return

    # Extract normative rule definitions
    norm_rules = input_data.get("normative_rule_definitions", [])
    if not norm_rules:
        return

    # Build output structure
    output_rules = []
    for rule in norm_rules:
        # Handle both "name" (single) and "names" (array) syntax
        is_names_list = "names" in rule
        names = rule.get("name")
        if not names:
            names = rule.get("names", [])

        # Convert single name to list
        if isinstance(names, str):
            names = [names]
        elif not isinstance(names, list):
            continue

        # Get descriptions for all names in this group
        descriptions = []
        output_names = []
        for name in names:
            if not name:
                continue

            # Look up rule in JSON mapping (case-insensitive)
            json_rule = rules_map.get(name.upper(), {})
            description = get_rule_description(json_rule)
            if not description:
                description = f"TODO: Add description for {name}"
            descriptions.append(description)

            # Use the original case from JSON if available, otherwise use YAML case
            output_name = json_rule.get("name", name)
            output_names.append(output_name)

        # Create one output entry for this rule group
        if output_names:
            output_rule = {
                "names": output_names if is_names_list else output_names[0],
                "is_names_list": is_names_list,
                "coverpoint": []
            }
            # Use first description as the comment for the group
            comment = descriptions[0] if descriptions else ""
            output_rules.append({
                "rule": output_rule,
                "comment": comment
            })

    # Create output YAML with comments
    output_path = output_dir / input_yaml.name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write YAML with comments
    with open(output_path, 'w') as f:
        f.write("# Normative rule to coverpoint mappings\n")
        f.write("# Generated from riscv-isa-manual normative rule definitions\n\n")
        f.write("normative_rule_definitions:\n")

        for item in output_rules:
            rule = item["rule"]
            comment = item["comment"]

            # Write comment if available
            if comment:
                # Wrap long comments
                lines = []
                current_line = ""
                for word in comment.split():
                    if len(current_line) + len(word) + 1 > 80:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                    else:
                        if current_line:
                            current_line += " " + word
                        else:
                            current_line = word
                if current_line:
                    lines.append(current_line)

                for i, line in enumerate(lines):
                    if i == 0:
                        f.write(f"  # {line}\n")
                    else:
                        f.write(f"  # {line}\n")

            # Write rule - handle both name and names formats
            f.write("  - ")
            if rule["is_names_list"]:
                names = rule["names"]
                names_str = ", ".join(names)
                f.write(f"names: [{names_str}]\n")
            else:
                f.write(f"name: {rule['names']}\n")
            f.write(f"    coverpoint: [\"\"]\n")
            f.write("\n")


def main() -> None:
    # Set up paths
    script_dir = Path(__file__).parent
    riscv_arch_test_dh_dir = script_dir.parent.parent
    riscv_isa_manual_dir = riscv_arch_test_dh_dir.parent / "riscv-isa-manual"
    norm_rules_json = riscv_isa_manual_dir / "build" / "norm-rules.json"
    input_dir = riscv_isa_manual_dir / "normative_rule_defs"
    output_dir = riscv_arch_test_dh_dir / "coverpoints" / "norm" / "yaml" / "chapters"

    # Validate paths
    if not norm_rules_json.exists():
        print(f"Error: {norm_rules_json} not found")
        return

    if not input_dir.exists():
        print(f"Error: {input_dir} not found")
        return

    # Load the normative rules JSON
    print(f"Loading normative rules from {norm_rules_json}...")
    rules_map = load_norm_rules_json(norm_rules_json)
    print(f"Loaded {len(rules_map)} normative rules")

    # Process each YAML file
    output_dir.mkdir(parents=True, exist_ok=True)
    yaml_files = list(input_dir.glob("*.yaml"))

    print(f"Processing {len(yaml_files)} normative rule definition files...")
    for yaml_file in sorted(yaml_files):
        if yaml_file.name == "README.md":
            continue

        try:
            process_rule_file(yaml_file, output_dir, rules_map)
            print(f"  ✓ {yaml_file.name}")
        except Exception as e:
            print(f"  ✗ {yaml_file.name}: {e}")

    print(f"\nOutput files created in {output_dir}")


if __name__ == "__main__":
    main()
