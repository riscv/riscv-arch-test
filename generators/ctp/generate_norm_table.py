#!/usr/bin/env python3
"""
Generate ASCIIDoc table from normative rules JSON and coverpoints YAML.

Usage:
  generate_norm_table.py [--json PATH] [--yaml PATH] [--out PATH]

Defaults:
    json: coverpoints/norm/norm-rules.json
    yaml: coverpoints/norm/yaml
    out:  ctp/src/norm/

The script writes an .adoc file containing a table with columns:
  - normative rule name
  - normative rule text
  - coverpoints

It also prints (and writes) a small report of names present in one file but not the other.
"""

import argparse
import json
import os
import glob
import sys
import re

try:
    import yaml
except Exception:
    yaml = None


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_yaml(path):
    """
    Try to load YAML normally; if the file contains non-YAML coverpoint expressions
    (braces, slashes, etc.) that break the parser, fall back to a tolerant text
    parser that extracts name/names and coverpoint: lines and returns a mapping
    structure compatible with the rest of the script.
    """
    if yaml is None:
        raise RuntimeError('PyYAML is required to read YAML files. Install with: pip install pyyaml')

    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    try:
        data = yaml.safe_load(text)
    except Exception:
        # Fallback parser: extract entries under normative_rule_definitions or top-level - entries
        return parse_coverpoints_fallback(text)

    return data


def parse_coverpoints_fallback(text):
    """Parse a relaxed subset of the YAML file and return a mapping
    where each key is a rule name and value is a dict with 'coverpoint'.
    This handles coverpoint values that include braces, slashes, or other
    characters that break the YAML parser.
    """
    lines = text.splitlines()
    entries = []
    groups = []
    in_block = False
    cur = []
    for ln in lines:
        stripped = ln.lstrip()
        # Detect list item start (e.g., "- name:" or "- names:")
        if stripped.startswith('- '):
            if in_block and cur:
                entries.append('\n'.join(cur))
                cur = []
            in_block = True
            cur.append(stripped[2:])
        else:
            if in_block:
                cur.append(stripped)

    if in_block and cur:
        entries.append('\n'.join(cur))

    for block in entries:
        # find name: or names: and coverpoint:
        name = None
        names = []
        cover = None

        for bline in block.splitlines():
            m_name = re.match(r"^name:\s*(.+)$", bline)
            m_names = re.match(r"^names:\s*(.+)$", bline)
            m_cover = re.match(r"^coverpoint:\s*(.+)$", bline)
            if m_name:
                val = m_name.group(1).strip()
                # strip quotes if present
                val = val.strip('\"\'')
                name = val
            elif m_names:
                val = m_names.group(1).strip()
                # Expect bracketed list like [a, b]
                if val.startswith('[') and val.endswith(']'):
                    inner = val[1:-1]
                    parts = [p.strip() for p in inner.split(',') if p.strip()]
                    names.extend(parts)
                else:
                    # fallback: comma split
                    parts = [p.strip() for p in val.split(',') if p.strip()]
                    names.extend(parts)
            elif m_cover:
                cover = m_cover.group(1).strip()

        all_names = []
        if name:
            all_names.append(name)
        if names:
            all_names.extend(names)

        if all_names:
            groups.append({'names': all_names, 'coverpoint': cover})

    return groups


def find_normative_rules(data):
    # Common pattern: top-level 'normative_rules' key
    if isinstance(data, dict) and 'normative_rules' in data:
        return data['normative_rules']

    # Otherwise, look for the first list of dicts containing 'name'
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict) and 'name' in v[0]:
                return v

    raise ValueError('Could not locate normative rules list in JSON')


def extract_rule_text(tags):
    # tags may be a list or a dict; we want the 'text' fields
    texts = []
    if tags is None:
        return ''
    if isinstance(tags, dict):
        # maybe tags contains text directly
        t = tags.get('text')
        if t:
            if isinstance(t, list):
                texts.extend([str(x).strip() for x in t if x is not None])
            else:
                texts.append(str(t).strip())
        return ' '.join(texts)

    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict):
                t = tag.get('text')
                if t:
                    if isinstance(t, list):
                        texts.extend([str(x).strip() for x in t if x is not None])
                    else:
                        texts.append(str(t).strip())
            else:
                # if tag is a string
                texts.append(str(tag).strip())

    return ' '.join([t for t in texts if t])


def build_coverpoint_groups(yaml_data):
    """Return a list of groups: each group is {'names': [name,...], 'coverpoint': <str>}.
    Accept multiple YAML shapes (list of dicts, dict mapping name->obj, nested 'coverpoints').
    """
    groups = []

    # If the fallback parser already returned groups (list), trust it
    if isinstance(yaml_data, list):
        for item in yaml_data:
            if not isinstance(item, dict):
                continue
            names = []
            if 'names' in item:
                n = item.get('names')
                if isinstance(n, list):
                    names.extend([str(x) for x in n if x])
                elif isinstance(n, str):
                    s = n.strip()
                    if s.startswith('[') and s.endswith(']'):
                        inner = s[1:-1]
                        parts = [p.strip() for p in inner.split(',') if p.strip()]
                        names.extend(parts)
                    else:
                        names.extend([p.strip() for p in s.split(',') if p.strip()])
            if 'name' in item:
                names.insert(0, str(item.get('name')))
            cover = item.get('coverpoint')
            if names:
                groups.append({'names': names, 'coverpoint': cover})
        return groups

    # If yaml_data is a dict mapping name -> {coverpoint: ...}
    if isinstance(yaml_data, dict):
        # Sometimes the YAML nests the list under a key like 'normative_rule_definitions'
        # or similar. Detect lists of dicts that look like groups and process them.
        for k, v in yaml_data.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                # Heuristic: element contains 'name' or 'names' or 'coverpoint'
                first = v[0]
                if any(key in first for key in ('name', 'names', 'coverpoint')):
                    for item in v:
                        if not isinstance(item, dict):
                            continue
                        names = []
                        if 'names' in item:
                            n = item.get('names')
                            if isinstance(n, list):
                                names.extend([str(x) for x in n if x])
                            elif isinstance(n, str):
                                s = n.strip()
                                if s.startswith('[') and s.endswith(']'):
                                    inner = s[1:-1]
                                    parts = [p.strip() for p in inner.split(',') if p.strip()]
                                    names.extend(parts)
                                else:
                                    names.extend([p.strip() for p in s.split(',') if p.strip()])
                        if 'name' in item:
                            names.insert(0, str(item.get('name')))
                        cover = item.get('coverpoint')
                        if names:
                            groups.append({'names': names, 'coverpoint': cover})
                    return groups

        # First, check for top-level mapping where each key is a name
        for k, v in yaml_data.items():
            if isinstance(v, dict) and 'coverpoint' in v:
                groups.append({'names': [k], 'coverpoint': v.get('coverpoint')})

        # Also handle nested 'coverpoints' key
        if 'coverpoints' in yaml_data and isinstance(yaml_data['coverpoints'], dict):
            for k, v in yaml_data['coverpoints'].items():
                if isinstance(v, dict) and 'coverpoint' in v:
                    groups.append({'names': [k], 'coverpoint': v.get('coverpoint')})

    return groups


def make_adoc_table(rows, outpath):
    # rows: list of (name, text, coverpoints)
    lines = []
    lines.append('[cols="1,4,3", options="header"]')
    lines.append('|===')
    lines.append('|Normative Rule |Rule Text |Coverpoints')
    lines.append('')
    for name, text, cp in rows:
        # sanitize pipes
        n = name.replace('|', r'\|')
        t = text.replace('|', r'\|')
        # Normalize coverpoint string and drop any leading '[' or trailing ']' if present
        c = (str(cp) if cp is not None else '').strip()
        if c.startswith('['):
            c = c[1:].strip()
        if c.endswith(']'):
            c = c[:-1].strip()
        # Collapse consecutive closing braces '}}' into a single '}' to remove excess
        c = re.sub(r"\}{2,}", "}", c)
        c = c.replace('|', r'\\|')
        lines.append(f'|{n} |{t} |{c}')
        lines.append('')

    lines.append('|===')

    os.makedirs(os.path.dirname(outpath) or '.', exist_ok=True)
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def ensure_dir(path):
    """Ensure 'path' exists as a directory. If a file exists at 'path', move it
    to path + '.bak' and create the directory. Returns the final directory path.
    """
    if os.path.exists(path):
        if os.path.isdir(path):
            return path
        # exists but not a directory: move aside
        backup = path + '.bak'
        try:
            os.rename(path, backup)
        except Exception:
            raise RuntimeError(f"Cannot move existing file {path} to {backup}")
        os.makedirs(path, exist_ok=True)
        return path
    else:
        os.makedirs(path, exist_ok=True)
        return path


def pick_cover_for_name(coverpoint, names, idx):
    """If `coverpoint` contains a brace-delimited list (e.g. "{A, B, C}..."),
    attempt to select the item corresponding to position `idx` in `names`.
    Otherwise return the original coverpoint.
    """
    if not coverpoint or not isinstance(coverpoint, str):
        return coverpoint

    # If there is a slash, keep the entire right-hand side and select the
    # corresponding element from the left-hand brace-list.
    s = coverpoint
    slash_pos = s.find('/')
    if slash_pos != -1:
        left = s[:slash_pos]
        right = s[slash_pos+1:]
        # Try to find a brace-delimited list on the left side first
        m_left = re.search(r"\{([^}]*)\}", left)
        if m_left:
            inner = m_left.group(1)
            parts = [p.strip() for p in inner.split(',') if p.strip()]
            if 0 <= idx < len(parts):
                # preserve the right-hand side exactly as it appears
                return parts[idx] + '/' + right
        else:
            # No brace group on left. Try splitting on commas (single or multiple names).
            parts = [p.strip() for p in left.split(',') if p.strip()]
            if parts:
                if 0 <= idx < len(parts):
                    return parts[idx] + '/' + right
                # If only one part and names indicates a single normative name, prefer that
                if len(parts) == 1:
                    return parts[0] + '/' + right
            # As a last resort, if the YAML names list contains a single name,
            # use it (this handles cases like mul_op where names==[mul_op]).
            if len(names) == 1 and idx == 0:
                return names[0] + '/' + right

    # Fallback: find the first {...} group anywhere and pick element
    m = re.search(r"\{([^}]*)\}", s)
    if not m:
        return coverpoint

    inner = m.group(1)
    parts = [p.strip() for p in inner.split(',') if p.strip()]
    if not parts:
        return coverpoint

    # If index is within parts, return that part. Otherwise, return original.
    if 0 <= idx < len(parts):
        return parts[idx]
    return coverpoint


def main():
    p = argparse.ArgumentParser(description='Generate ASCIIDoc table from normative rules JSON and coverpoints YAML')
    p.add_argument('--json', default='coverpoints/norm/norm-rules.json', help='Path to norm-rules.json')
    p.add_argument('--yaml', default='coverpoints/norm/yaml', help='Path to a YAML file or a directory containing YAML files (default directory: coverpoints/norm/yaml)')
    p.add_argument('--out', default='ctp/src/norm/', help='Output ASCIIDoc file or directory when --yaml is a directory (default dir: coverpoints/norm/adoc/)')
    p.add_argument('--report', default='coverpoints/norm/mismatch_report.txt', help='Report file or directory when --yaml is a directory')
    args = p.parse_args()

    # If paths are relative and not found from current CWD, try resolving
    # them relative to the script directory so running from repo root still works.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(args.json):
        alt = os.path.join(script_dir, args.json)
        if os.path.exists(alt):
            args.json = alt
        else:
            print(f'Error: JSON file not found: {args.json}', file=sys.stderr)
            sys.exit(2)

    if not os.path.exists(args.yaml):
        alt = os.path.join(script_dir, args.yaml)
        if os.path.exists(alt):
            args.yaml = alt
        else:
            print(f'Error: YAML file not found: {args.yaml}', file=sys.stderr)
            sys.exit(2)

    # Load JSON once
    jdata = load_json(args.json)
    rules_list = find_normative_rules(jdata)

    # Build a mapping of JSON rule name -> text for fast lookup
    json_text_map = {}
    json_names = set()
    json_def_map = {}
    for entry in rules_list:
        if not isinstance(entry, dict):
            continue
        name = entry.get('name')
        if not name:
            continue
        json_names.add(name)
        tags = entry.get('tags') or entry.get('tag') or []
        text = extract_rule_text(tags)
        json_text_map[name] = text
        # capture def_filename for later grouping in reports
        def_fn = entry.get('def_filename') or entry.get('def_file') or entry.get('definition_filename')
        json_def_map[name] = def_fn or 'unknown'

    # If args.yaml is a directory, process every .yaml/.yml file inside
    if os.path.isdir(args.yaml):
        yaml_files = sorted(glob.glob(os.path.join(args.yaml, '*.yaml')) + glob.glob(os.path.join(args.yaml, '*.yml')))
        if not yaml_files:
            print(f'No YAML files found in directory: {args.yaml}', file=sys.stderr)
            sys.exit(2)

        # Determine output directory for adoc files.
        # Treat an --out ending with a path separator as a directory. If it's an
        # existing directory, use it. Otherwise fall back to dirname or the yaml
        # directory.
        if os.path.isdir(args.out):
            out_dir = args.out
        elif args.out.endswith(os.sep) or args.out.endswith('/'):
            out_dir = args.out.rstrip(os.sep)
        else:
            out_dir = os.path.dirname(args.out) or args.yaml

        # Determine report directory
        if os.path.isdir(args.report):
            report_dir = args.report
        else:
            report_dir = os.path.dirname(args.report) or out_dir

        # Accumulate per-YAML missing-in-JSON lists, and track all YAML names seen
        per_yaml_missing = {}
        all_yaml_names = set()

        for yfile in yaml_files:
            ydata = load_yaml(yfile)
            groups = build_coverpoint_groups(ydata)

            # Build rows and mappings
            cover_map = {}
            yaml_names = set()
            rows = []
            for g in groups:
                names = g.get('names', [])
                cp = g.get('coverpoint')
                for idx, n in enumerate(names):
                    # If coverpoint contains multiple brace-delimited groups,
                    # pick the one corresponding to this name's index.
                    chosen_cp = pick_cover_for_name(g.get('coverpoint'), names, idx)
                    cover_map[n] = chosen_cp
                    yaml_names.add(n)
                    if idx == 0:
                        text = json_text_map.get(n, '')
                    else:
                        text = 'see above'
                    rows.append((n, text, chosen_cp))

            # record per-yaml missing-in-json
            missing_in_json = sorted(list(yaml_names - json_names))
            base = os.path.splitext(os.path.basename(yfile))[0]
            per_yaml_missing[base] = missing_in_json

            # accumulate all yaml names seen
            all_yaml_names.update(yaml_names)

            # Write adoc for this yaml
            out_dir = ensure_dir(out_dir)
            report_dir = ensure_dir(report_dir)
            outpath = os.path.join(out_dir, base + '.adoc')
            make_adoc_table(rows, outpath)

        # After processing all YAMLs, create a single combined mismatch report
        # missing_in_yaml = JSON names that did not appear in any YAML
        missing_in_yaml = sorted(list(json_names - all_yaml_names))

        report_lines = []
        report_lines.append('Mismatch report')
        report_lines.append('===============')
        report_lines.append('')
        report_lines.append(f'Total JSON rules: {len(json_names)}')
        report_lines.append(f'Total YAML coverpoints (unique names seen): {len(all_yaml_names)}')
        report_lines.append('')
        # Per-YAML sections
        for base in sorted(per_yaml_missing.keys()):
            report_lines.append(f'YAML file: {base}.yaml')
            report_lines.append('-' * (10 + len(base)))
            missing = per_yaml_missing[base]
            report_lines.append('Names present in YAML but missing from JSON:')
            if missing:
                report_lines.extend(['  ' + n for n in missing])
            else:
                report_lines.append('  (none)')
            report_lines.append('')

        # Now list JSON-only names organized by def_filename (chapter)
        report_lines.append('Names present in JSON but missing from any YAML (organized by def_filename):')
        if missing_in_yaml:
            # group by def_filename
            chapter_map = {}
            for name in missing_in_yaml:
                chapter = json_def_map.get(name, 'unknown') or 'unknown'
                chapter_map.setdefault(chapter, []).append(name)

            for chap in sorted(chapter_map.keys()):
                report_lines.append(f'Chapter: {chap}')
                for n in sorted(chapter_map[chap]):
                    report_lines.append('  ' + n)
                report_lines.append('')
        else:
            report_lines.append('  (none)')

        # Write the single report file. If args.report is a directory, write mismatch_report.txt inside it.
        if os.path.isdir(args.report) or args.report.endswith(os.sep):
            rpt_dir = ensure_dir(args.report.rstrip(os.sep))
            report_path = os.path.join(rpt_dir, 'mismatch_report.txt')
        else:
            parent = os.path.dirname(args.report) or '.'
            ensure_dir(parent)
            report_path = args.report

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        return

    # Single YAML file mode
    ydata = load_yaml(args.yaml)
    groups = build_coverpoint_groups(ydata)

    # Build a name->coverpoint map and the set of yaml names for mismatch reporting
    cover_map = {}
    yaml_names = set()
    rows = []
    for g in groups:
        names = g.get('names', [])
        cp = g.get('coverpoint')
        # populate cover_map and create one row per normative rule name
        for idx, n in enumerate(names):
            chosen_cp = pick_cover_for_name(cp, names, idx)
            cover_map[n] = chosen_cp
            yaml_names.add(n)
            # Only include the rule text for the first name in the group
            if idx == 0:
                text = json_text_map.get(n, '')
            else:
                text = 'see above'
            rows.append((n, text, chosen_cp))

    missing_in_json = sorted(list(yaml_names - json_names))
    missing_in_yaml = sorted(list(json_names - yaml_names))

    # Write adoc
    # If args.out looks like a directory (ends with / or is an existing dir),
    # ensure it exists and write into it using the yaml basename.
    if args.out.endswith(os.sep) or os.path.isdir(args.out):
        out_dir = ensure_dir(args.out.rstrip(os.sep))
        outpath = os.path.join(out_dir, os.path.splitext(os.path.basename(args.yaml))[0] + '.adoc')
    else:
        out_parent = os.path.dirname(args.out) or '.'
        ensure_dir(out_parent)
        outpath = args.out

    make_adoc_table(rows, outpath)

    # Write the mismatch report only to the report file (do not print to stdout)
    report_lines = []
    report_lines.append('Mismatch report')
    report_lines.append('===============')
    report_lines.append('')
    report_lines.append(f'Total JSON rules: {len(json_names)}')
    report_lines.append(f'Total YAML coverpoints: {len(yaml_names)}')
    report_lines.append('')
    report_lines.append('Names present in YAML but missing from JSON:')
    if missing_in_json:
        report_lines.extend(['  ' + n for n in missing_in_json])
    else:
        report_lines.append('  (none)')
    report_lines.append('')
    report_lines.append('Names present in JSON but missing from YAML:')
    if missing_in_yaml:
        report_lines.extend(['  ' + n for n in missing_in_yaml])
    else:
        report_lines.append('  (none)')

    report_text = '\n'.join(report_lines)
    with open(args.report, 'w', encoding='utf-8') as f:
        f.write(report_text)


if __name__ == '__main__':
    main()
