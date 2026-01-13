#!/usr/bin/env python3
"""
Generate a CSV spreadsheet of UDB parameters from YAML files.

Creates a CSV with columns:
- name: Parameter name (YAML filename without extension)
- definedBy: Comma-separated list of specs that define this parameter
- description: Parameter description
"""

import yaml
import csv
from pathlib import Path
import sys
import argparse

def extract_name_from_defined_by(entry):
    """Extract the 'name' field from a definedBy entry."""
    if isinstance(entry, dict):
        # Check for extension.name
        if 'extension' in entry and isinstance(entry['extension'], dict):
            # Check for anyOf within extension
            if 'anyOf' in entry['extension'] and isinstance(entry['extension']['anyOf'], list) and entry['extension']['anyOf']:
                # Take the first entry from anyOf
                first = entry['extension']['anyOf'][0]
                if isinstance(first, dict) and 'name' in first:
                    return first['name']
            # Check for allOf within extension
            if 'allOf' in entry['extension'] and isinstance(entry['extension']['allOf'], list) and entry['extension']['allOf']:
                # Take the first entry from allOf
                first = entry['extension']['allOf'][0]
                if isinstance(first, dict) and 'name' in first:
                    return first['name']
            # Normal extension name
            return entry['extension'].get('name', '')
        # Check for param.name
        if 'param' in entry and isinstance(entry['param'], dict):
            return entry['param'].get('name', '')
        # Check for allOf (take first entry)
        if 'allOf' in entry and isinstance(entry['allOf'], list) and entry['allOf']:
            return extract_name_from_defined_by(entry['allOf'][0])
    return ""

def main():
    parser = argparse.ArgumentParser(description="Generate CSV of RISC-V UDB parameters")
    parser.add_argument("--yaml-dir", type=Path,
                       default=Path.home() / "riscv-unified-db" / "spec" / "std" / "isa" / "param",
                       help="Directory containing YAML parameter files")
    parser.add_argument("--output", type=Path,
                       default= Path(".") / "udb_parameters.csv",
                       help="Output CSV file path")

    args = parser.parse_args()

    yaml_dir = args.yaml_dir
    output_csv = args.output

    if not yaml_dir.exists():
        print(f"Error: Directory not found: {yaml_dir}", file=sys.stderr)
        sys.exit(1)

    # Collect data
    rows = []
    skipped_files = []

    for yaml_file in sorted(yaml_dir.glob("*.yaml")):
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)

            if not data:
                skipped_files.append(yaml_file.stem)
                continue

            # Get the parameter name (filename without extension)
            param_name = yaml_file.stem

            # Get description
            description = data.get('description', '')

            # Get definedBy entries - could be a list or single string
            defined_by = data.get('definedBy', [])
            if isinstance(defined_by, list):
                defined_by_str = ", ".join(str(item) for item in defined_by)
                # Extract name from first entry
                if defined_by and isinstance(defined_by[0], dict):
                    ext = extract_name_from_defined_by(defined_by[0])
                else:
                    ext = ""
            else:
                defined_by_str = str(defined_by) if defined_by else ""
                # Extract name from single entry
                if isinstance(defined_by, dict):
                    ext = extract_name_from_defined_by(defined_by)
                else:
                    ext = ""

            # Skip Xmock entries
            if ext != "Xmock":
                rows.append({
                    'name': param_name,
                    'ext': ext,
                    'definedBy': defined_by_str,
                    'description': description
                })
        except Exception as e:
            print(f"Error processing {yaml_file.name}: {e}", file=sys.stderr)

    # Sort by ext column
    rows.sort(key=lambda x: x['ext'])

    # Write to CSV
    try:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'ext', 'definedBy', 'description'])
            writer.writeheader()
            writer.writerows(rows)

        print(f"CSV file created: {output_csv}")
        print(f"Total parameters: {len(rows)}")
        if skipped_files:
            print(f"Skipped {len(skipped_files)} empty/null files: {', '.join(skipped_files)}")
    except Exception as e:
        print(f"Error writing CSV: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
