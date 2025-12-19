#!/usr/bin/env -S uv run
# ruff: noqa: ANN401
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pyyaml",
# ]
# ///

"""
Generate YAML files for normative rule mappings from CSV testplans.

Usage:
  norm_yaml_gen.py [--testplans PATH] [--json PATH] [--yaml PATH] [--output PATH]

Defaults:
    testplans: testplans/
    json:      coverpoints/norm/norm-rules.json
    yaml:      coverpoints/norm/yaml
    output:    coverpoints/norm/yaml/new

For each CSV file in the testplans directory, this script creates a YAML file
containing normative rule definitions. It maps instruction names from the CSV
to rules in the JSON file, where dots in instruction names are replaced with
underscores and "_op" is appended.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    """Load JSON from a file."""
    return json.loads(path.read_text(encoding='utf-8'))


def load_csv_with_coverpoints(csv_path: Path) -> dict[str, dict[str, str | list[str]]]:
    """
    Load instruction names and coverpoint data from a CSV testplan file.

    Returns a dict mapping instruction names to dicts with 'row' and 'coverpoints' keys.
    Excludes columns that:
    - Start with 'cmp'
    - Contain 'edges' unless they start with 'cr' OR no cr*edges coverpoint exists
    """
    data = {}
    with csv_path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        # Find the index of cp_asm_count column
        if reader.fieldnames is None:
            return data

        try:
            asm_count_idx = reader.fieldnames.index('cp_asm_count')
        except ValueError:
            # If cp_asm_count not found, use all columns after a certain point
            asm_count_idx = 0

        for row in reader:
            if 'Instruction' not in row or not row['Instruction']:
                continue

            # Strip whitespace from instruction name
            instr = row['Instruction'].strip()
            if not instr:
                continue

            # First pass: collect all candidate coverpoints and check for cr*edges
            candidates = []
            has_cr_edges = False

            for col_name in reader.fieldnames[asm_count_idx + 1:]:
                # Skip columns that start with 'cmp'
                if col_name.startswith('cmp'):
                    continue

                cell_value = row.get(col_name, '').strip()
                # Only consider columns that have a value (not blank)
                if not cell_value:
                    continue

                # Check if this is a cr*edges column
                if col_name.startswith('cr') and 'edges' in col_name:
                    has_cr_edges = True

                if cell_value == 'x':
                    candidates.append(col_name)
                else:
                    candidates.append(f'{col_name}_{cell_value}')

            # Second pass: filter based on whether cr*edges exists
            coverpoints = []
            for col_name in reader.fieldnames[asm_count_idx + 1:]:
                # Skip columns that start with 'cmp'
                if col_name.startswith('cmp'):
                    continue

                cell_value = row.get(col_name, '').strip()
                if not cell_value:
                    continue

                # If 'edges' is in the name and we have cr*edges, skip non-cr edges
                if 'edges' in col_name:
                    if has_cr_edges and not col_name.startswith('cr'):
                        continue

                if cell_value == 'x':
                    coverpoints.append(col_name)
                else:
                    coverpoints.append(f'{col_name}_{cell_value}')

            data[instr] = {'row': row, 'coverpoints': coverpoints}

    return data


def normalize_instruction_name(instruction: str) -> str:
    """
    Convert instruction name to rule name format.

    Dots are replaced with dashes and "_op" is appended.
    Example: "c.add" -> "c-add_op", "fadd.s" -> "fadd-s_op"
    """
    return instruction.replace('.', '-') + '_op'


def find_rule_in_json(rule_name: str, json_data: dict[str, Any]) -> dict[str, Any] | None:
    """
    Find a rule by name in the JSON data.

    Returns the rule dict if found, None otherwise.
    """
    for rule in json_data.get('normative_rules', []):
        if rule.get('name') == rule_name:
            return rule
    return None


def generate_yaml_content(csv_base_name: str, instr_data: dict[str, dict[str, str | list[str]]], json_data: dict[str, Any]) -> str:
    """
    Generate YAML content for the given instructions.

    For each instruction, if a corresponding rule exists in the JSON,
    create a YAML entry with the rule name and text comments from tags.
    The coverpoint is generated based on CSV columns.
    """
    yaml_lines = [
        '# Mapping of normative rules to coverpoints for a test suite',
        '',
        'normative_rule_definitions:',
    ]

    for instruction, data in instr_data.items():
        rule_name = normalize_instruction_name(instruction)
        rule = find_rule_in_json(rule_name, json_data)

        if rule:
            yaml_lines.append(f'  - name: {rule_name}')

            # Add comments from tags
            tags = rule.get('tags', [])
            for tag in tags:
                text = tag.get('text', '')
                if text:
                    # Format multi-line text as YAML comments
                    for line in text.split('\n'):
                        yaml_lines.append(f'    # {line}')

            # Generate coverpoint from CSV data
            coverpoints = data.get('coverpoints', [])
            if coverpoints:
                # Format: <file>_<instr>_cg/{points}
                # instr uses underscores instead of dashes
                instr_with_underscore = instruction.replace('.', '_')
                points_str = ', '.join(coverpoints)
                cp_str = f'{csv_base_name}_{instr_with_underscore}_cg/{{{points_str}}}'
                yaml_lines.append(f'    coverpoint: ["{cp_str}"]')
            else:
                yaml_lines.append('    coverpoint: [TODO]')

    return '\n'.join(yaml_lines) + '\n'


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate YAML files for normative rule mappings from CSV testplans.'
    )
    parser.add_argument(
        '--testplans',
        type=Path,
        default=Path('testplans'),
        help='Directory containing CSV testplan files (default: testplans/)',
    )
    parser.add_argument(
        '--json',
        type=Path,
        default=Path('coverpoints/norm/norm-rules.json'),
        help='Path to norm-rules.json file (default: coverpoints/norm/norm-rules.json)',
    )
    parser.add_argument(
        '--yaml',
        type=Path,
        default=Path('coverpoints/norm/yaml'),
        help='Directory to check for existing YAML files (default: coverpoints/norm/yaml)',
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('coverpoints/norm/yaml/new'),
        help='Output directory for new YAML files (default: coverpoints/norm/yaml/new)',
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.testplans.is_dir():
        print(f'Error: Testplans directory not found: {args.testplans}', file=sys.stderr)
        return 1

    if not args.json.is_file():
        print(f'Error: JSON file not found: {args.json}', file=sys.stderr)
        return 1

    # Load JSON data
    try:
        json_data = load_json(args.json)
    except Exception as e:
        print(f'Error loading JSON file: {e}', file=sys.stderr)
        return 1

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Get existing YAML files
    existing_yamls = set()
    if args.yaml.is_dir():
        existing_yamls = {f.stem for f in args.yaml.glob('*.yaml')}

    # Process each CSV file
    csv_files = sorted(args.testplans.glob('*.csv'))
    if not csv_files:
        print(f'Warning: No CSV files found in {args.testplans}', file=sys.stderr)
        return 0

    created_count = 0
    skipped_count = 0

    for csv_file in csv_files:
        base_name = csv_file.stem

        # Skip if YAML already exists
        if base_name in existing_yamls:
            print(f'Skipping {base_name}.yaml (already exists)')
            skipped_count += 1
            continue

        # Load instructions and coverpoints from CSV
        try:
            instr_data = load_csv_with_coverpoints(csv_file)
        except Exception as e:
            print(f'Error reading {csv_file}: {e}', file=sys.stderr)
            continue

        if not instr_data:
            print(f'Warning: No instructions found in {csv_file}', file=sys.stderr)
            continue

        # Generate YAML content
        yaml_content = generate_yaml_content(base_name, instr_data, json_data)

        # Write YAML file
        output_file = args.output / f'{base_name}.yaml'
        try:
            output_file.write_text(yaml_content, encoding='utf-8')
            print(f'Created {output_file}')
            created_count += 1
        except Exception as e:
            print(f'Error writing {output_file}: {e}', file=sys.stderr)

    print(f'\nSummary: Created {created_count} files, skipped {skipped_count} existing files')
    return 0


if __name__ == '__main__':
    sys.exit(main())
