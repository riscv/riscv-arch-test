#!/usr/bin/env python3
"""
Generate YAML file with empty coverpoints for rules found in mismatch report.

Usage:
  rule_coverpoint.py <yaml_filename>

Example:
  rule_coverpoint.py bfloat16.yaml

This script:
1. Takes a YAML filename (e.g., "bfloat16.yaml")
2. Prepends "normative_rule_defs/" to form the chapter name
3. Searches coverpoints/norm/mismatch_report.txt for that chapter
4. Extracts all rule names listed under that chapter
5. Generates a YAML file in coverpoints/norm/yaml/ with the same base name
6. Each rule gets an empty coverpoint list

The output format matches I.yaml structure:
  - name: rule_name
    coverpoint: []
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


def load_norm_rules_json(json_path: str = 'coverpoints/norm/norm-rules.json', cache_path: Path | str | None = None) -> dict[str, str]:
    """
    Load norm-rules.json and extract a mapping of rule name to tag text.
    
    Args:
        json_path: Path or URL to norm-rules.json
        cache_path: Optional cache file path for remote JSON
    
    Returns:
        Dict mapping rule name to tag display text
    """
    # Try to load from default location
    parsed = urlparse(json_path)
    
    if parsed.scheme in ('http', 'https'):
        try:
            with urllib.request.urlopen(json_path, timeout=20) as resp:
                jdata = json.loads(resp.read().decode('utf-8'))
                if cache_path:
                    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(cache_path).write_text(json.dumps(jdata), encoding='utf-8')
        except Exception as e:
            print(f"Warning: Failed to fetch JSON from {json_path}: {e}", file=sys.stderr)
            return {}
    else:
        try:
            jdata = json.loads(Path(json_path).read_text(encoding='utf-8'))
        except FileNotFoundError:
            print(f"Warning: JSON file not found: {json_path}", file=sys.stderr)
            return {}
    
    # Extract rule name -> tag text mapping from the JSON
    rule_texts = {}
    
    # Navigate the JSON structure to find rules
    def find_rules(obj, path=""):
        if isinstance(obj, dict):
            # Check if this looks like a normative rule entry
            if 'name' in obj and ('tags' in obj or 'tag' in obj):
                name = obj.get('name')
                tags = obj.get('tags') or obj.get('tag') or []
                tag_list = [tags] if isinstance(tags, dict) else (list(tags) if tags else [])
                
                # Collect tag display texts
                tag_texts = []
                for tag in tag_list:
                    if isinstance(tag, dict) and 'text' in tag:
                        text = tag['text']
                        if text:
                            tag_texts.append(str(text).strip())
                
                if name and tag_texts:
                    rule_texts[name] = ' | '.join(tag_texts)
            
            # Recursively search nested dicts
            for key, val in obj.items():
                find_rules(val, f"{path}/{key}")
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                find_rules(item, f"{path}[{idx}]")
    
    find_rules(jdata)
    return rule_texts


def resolve_json_path(json_path: str, script_dir: Path) -> str:
    """Resolve JSON path, checking multiple locations."""
    # If it's a URL, return as-is
    if urlparse(json_path).scheme in ('http', 'https'):
        return json_path
    
    # Check relative to current working directory
    p = Path(json_path)
    if p.exists():
        return json_path
    
    # Check relative to script directory
    alt = script_dir.parent.parent / json_path
    if alt.exists():
        return str(alt)
    
    # Return original and let it fail gracefully
    return json_path


def parse_mismatch_report(report_path: Path, chapter_name: str) -> list[str]:
    """
    Parse the mismatch report and extract rule names for the given chapter.
    
    Args:
        report_path: Path to mismatch_report.txt
        chapter_name: Chapter identifier (e.g., "normative_rule_defs/bfloat16.yaml")
    
    Returns:
        List of rule names found under that chapter
    """
    if not report_path.exists():
        raise FileNotFoundError(f"Mismatch report not found: {report_path}")
    
    text = report_path.read_text(encoding='utf-8')
    lines = text.splitlines()
    
    rules = []
    in_chapter = False
    chapter_marker = f"Chapter: {chapter_name}"
    
    for line in lines:
        if line.strip().startswith("Chapter:"):
            # Check if this is our target chapter
            in_chapter = line.strip() == chapter_marker
        elif in_chapter:
            # Rule names are indented with two spaces
            if line.startswith("  ") and not line.startswith("Chapter:"):
                rule_name = line.strip()
                if rule_name:
                    rules.append(rule_name)
            elif line and not line.startswith(" "):
                # End of current chapter section
                break
    
    return rules
    """
    Parse the mismatch report and extract rule names for the given chapter.
    
    Args:
        report_path: Path to mismatch_report.txt
        chapter_name: Chapter identifier (e.g., "normative_rule_defs/bfloat16.yaml")
    
    Returns:
        List of rule names found under that chapter
    """
    if not report_path.exists():
        raise FileNotFoundError(f"Mismatch report not found: {report_path}")
    
    text = report_path.read_text(encoding='utf-8')
    lines = text.splitlines()
    
    rules = []
    in_chapter = False
    chapter_marker = f"Chapter: {chapter_name}"
    
    for line in lines:
        if line.strip().startswith("Chapter:"):
            # Check if this is our target chapter
            in_chapter = line.strip() == chapter_marker
        elif in_chapter:
            # Rule names are indented with two spaces
            if line.startswith("  ") and not line.startswith("Chapter:"):
                rule_name = line.strip()
                if rule_name:
                    rules.append(rule_name)
            elif line and not line.startswith(" "):
                # End of current chapter section
                break
    
    return rules


def generate_yaml_file(rules: list[str], output_path: Path, rule_texts: dict[str, str] | None = None) -> None:
    """
    Generate a YAML file with empty coverpoint lists for the given rules.
    
    Args:
        rules: List of rule names
        output_path: Path where the YAML file will be written
        rule_texts: Optional dict mapping rule name to tag text from JSON
    """
    if rule_texts is None:
        rule_texts = {}
    
    lines = [
        "# Mapping of normative rules to coverpoints for a test suite",
        "",
        "normative_rule_definitions:",
    ]
    
    for rule in rules:
        lines.append(f"  - name: {rule}")
        lines.append("    coverpoint: []")
        # Add tag text as a comment if available
        if rule in rule_texts and rule_texts[rule]:
            comment_text = rule_texts[rule].replace('\n', ' ').strip()
            lines.append(f"      # {comment_text}")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Generate YAML file with empty coverpoints for rules from mismatch report'
    )
    parser.add_argument(
        'yaml_file',
        help='YAML filename (e.g., bfloat16.yaml) - will be prepended with normative_rule_defs/'
    )
    parser.add_argument(
        '--report',
        default='coverpoints/norm/mismatch_report.txt',
        help='Path to mismatch report (default: coverpoints/norm/mismatch_report.txt)'
    )
    parser.add_argument(
        '--out-dir',
        default='coverpoints/norm/yaml',
        help='Output directory for generated YAML (default: coverpoints/norm/yaml)'
    )
    parser.add_argument(
        '--json',
        default='https://risc-v-certification-steering-committee.github.io/riscv-isa-manual/snapshot/norm-rules/norm-rules.json',
        help='Path or URL to norm-rules.json (default: remote canonical URL)'
    )
    parser.add_argument(
        '--always-fetch',
        action='store_true',
        help='Always fetch JSON from remote URL'
    )
    
    args = parser.parse_args()
    
    # Resolve paths relative to script directory if they don't exist from CWD
    script_dir = Path(__file__).resolve().parent
    
    # Construct chapter name by prepending normative_rule_defs/
    yaml_filename = args.yaml_file
    if not yaml_filename.endswith('.yaml'):
        yaml_filename += '.yaml'
    
    chapter_name = f"normative_rule_defs/{yaml_filename}"
    
    # Find report file
    report_path = Path(args.report)
    if not report_path.exists():
        alt_report = script_dir.parent.parent / args.report
        if alt_report.exists():
            report_path = alt_report
        else:
            print(f"Error: Mismatch report not found: {args.report}", file=sys.stderr)
            sys.exit(1)
    
    # Find output directory
    out_dir = Path(args.out_dir)
    if not out_dir.exists():
        alt_out = script_dir.parent.parent / args.out_dir
        if alt_out.parent.exists():
            out_dir = alt_out
        else:
            out_dir = Path(args.out_dir)  # Use as-is and create it
    
    # Parse the mismatch report
    print(f"Searching for chapter: {chapter_name}")
    rules = parse_mismatch_report(report_path, chapter_name)
    
    if not rules:
        print(f"Warning: No rules found for chapter '{chapter_name}' in mismatch report", file=sys.stderr)
        print("Available chapters in the report:")
        # Show available chapters for debugging
        text = report_path.read_text(encoding='utf-8')
        for line in text.splitlines():
            if line.strip().startswith("Chapter:"):
                print(f"  {line.strip()}")
        sys.exit(1)
    
    # Generate output file
    base_name = Path(yaml_filename).stem
    output_path = out_dir / f"{base_name}.yaml"
    
    print(f"Found {len(rules)} rules")
    
    # Load JSON normative rules to get tag text for comments
    print("Loading normative rules JSON...")
    canonical_json_url = 'https://risc-v-certification-steering-committee.github.io/riscv-isa-manual/snapshot/norm-rules/norm-rules.json'
    
    if args.always_fetch:
        json_path = canonical_json_url
    else:
        json_path = resolve_json_path(args.json, script_dir)
    
    rule_texts = load_norm_rules_json(json_path)
    print(f"Loaded {len(rule_texts)} rule texts from JSON")
    
    print(f"Writing to: {output_path}")
    
    generate_yaml_file(rules, output_path, rule_texts)
    
    print("Done.")


if __name__ == "__main__":
    main()
