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
import re
import sys
import urllib.request
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import yaml


def load_json(path: Path | str, cache_path: Path | str | None = None) -> Any:
    """Load JSON from a local file path or an HTTP/HTTPS URL."""
    path_str = str(path)
    parsed = urlparse(path_str)
    if parsed.scheme in ('http', 'https'):
        try:
            with urllib.request.urlopen(path_str, timeout=20) as resp:
                text = resp.read().decode('utf-8')
                if cache_path:
                    cache = Path(cache_path)
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    cache.write_text(text, encoding='utf-8')
                return json.loads(text)
        except Exception as e:
            raise RuntimeError(f'Failed to download JSON from {path}: {e}') from e
    # Load from local file
    text = Path(path).read_text(encoding='utf-8')
    # Save to cache if cache_path is provided
    if cache_path:
        cache = Path(cache_path)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(text, encoding='utf-8')
    return json.loads(text)


def load_yaml(path: Path | str) -> Any:
    """Load YAML with fallback parsing if standard parsing fails."""
    text = Path(path).read_text(encoding='utf-8')
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        return parse_coverpoints_fallback(text)


def parse_coverpoints_fallback(text: str) -> list[dict[str, Any]]:
    """Parse a relaxed subset of the YAML file and return a list of
    groups where each group is a dict: {'names': [name,...], 'coverpoint': <str>}.

    This tolerant parser scans the file for occurrences of 'name:',
    'names:' and 'coverpoint:' lines and builds groups from contiguous
    entries. It's intended as a fallback when PyYAML fails to parse the
    file due to non-YAML expressions present in coverpoint values.
    """
    lines = text.splitlines()
    groups = []

    name = None
    names = []
    cover = None

    def flush_group() -> None:
        nonlocal name, names, cover
        all_names = []
        if name:
            all_names.extend(split_name_list(name))
        for n in names:
            all_names.extend(split_name_list(n))
        if all_names:
            groups.append({'names': all_names, 'coverpoint': cover})
        name = None
        names = []
        cover = None

    for line in lines:
        bline = line.strip()
        if not bline:
            # blank line separates entries
            if name or names or cover:
                flush_group()
            continue

        m_name = re.match(r"^name:\s*(.+)$", bline)
        m_names = re.match(r"^names:\s*(.+)$", bline)
        m_cover = re.match(r"^coverpoint:\s*(.+)$", bline)

        if m_name:
            val = m_name.group(1).strip()
            val = val.strip('"\'')
            # finalize any previous group
            if name or names or cover:
                flush_group()
            name = val
        elif m_names:
            val = m_names.group(1).strip()
            # Expect bracketed list like [a, b] or comma list
            if val.startswith('[') and val.endswith(']'):
                inner = val[1:-1]
                parts = [p.strip() for p in inner.split(',') if p.strip()]
                names.extend(parts)
            else:
                parts = [p.strip() for p in val.split(',') if p.strip()]
                names.extend(parts)
        elif m_cover:
            cover = m_cover.group(1).strip().strip('"\'')
        else:
            # Try to catch list-style '- name: value' entries
            m_dash_name = re.match(r"^-+\s*name:\s*(.+)$", bline)
            if m_dash_name:
                val = m_dash_name.group(1).strip().strip('"\'')
                if name or names or cover:
                    flush_group()
                name = val
            # otherwise ignore unrecognized lines

    # flush any trailing group
    if name or names or cover:
        flush_group()

    return groups


def find_normative_rules(data: Any) -> list[dict[str, Any]]:
    """Extract normative rules list from JSON data."""
    if isinstance(data, dict):
        if 'normative_rules' in data:
            return data['normative_rules']
        # Search for first list of dicts with 'name' key
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict) and 'name' in v[0]:
                return v
    elif isinstance(data, list):
        return data
    raise ValueError('Could not locate normative rules list in JSON')


def extract_rule_text(tags: Any) -> str:
    """Extract text from tags structure (dict, list, or mixed)."""
    if not tags:
        return ''

    texts = []
    items = [tags] if isinstance(tags, dict) else tags if isinstance(tags, list) else []

    for item in items:
        if isinstance(item, dict):
            text = item.get('text')
            if isinstance(text, list):
                texts.extend(str(x).strip() for x in text if x)
            elif text:
                texts.append(str(text).strip())
        elif item:
            texts.append(str(item).strip())

    return ' '.join(texts)


def split_name_list(val: Any) -> list[str]:
    """Split name(s) into a list, handling various formats."""
    if not val:
        return []
    s = str(val).strip().strip('"\'')
    # Remove list brackets if present
    if s.startswith('[') and s.endswith(']'):
        s = s[1:-1]
    return [p.strip() for p in s.split(',') if p.strip()] if ',' in s else [s]


def extract_names_from_item(item: dict[str, Any]) -> list[str]:
    """Extract and normalize names from a YAML item."""
    names = []
    # Process 'names' field (can be list or string)
    if 'names' in item:
        n = item['names']
        names.extend(split_name_list(el) if isinstance(n, list) else split_name_list(n) for el in ([n] if not isinstance(n, list) else n))
        names = [name for sublist in names for name in sublist]  # Flatten
    # Process 'name' field (prepend to preserve order)
    if 'name' in item:
        names = split_name_list(item['name']) + names
    return names


def process_items_to_groups(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert list of items to groups with names and coverpoints."""
    groups = []
    for item in items:
        if not isinstance(item, dict):
            continue
        names = extract_names_from_item(item)
        if names:
            groups.append({'names': names, 'coverpoint': item.get('coverpoint')})
    return groups


def build_coverpoint_groups(yaml_data: Any) -> list[dict[str, Any]]:
    """Extract groups from YAML data in various formats."""
    if isinstance(yaml_data, list):
        return process_items_to_groups(yaml_data)

    if not isinstance(yaml_data, dict):
        return []

    # Check for nested list under a key
    for v in yaml_data.values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and any(key in v[0] for key in ('name', 'names', 'coverpoint')):
            return process_items_to_groups(v)

    # Top-level mapping: key -> {coverpoint: ...}
    groups = []
    for k, v in yaml_data.items():
        if isinstance(v, dict) and 'coverpoint' in v:
            groups.append({'names': split_name_list(k), 'coverpoint': v['coverpoint']})

    # Also check nested 'coverpoints' key
    if 'coverpoints' in yaml_data:
        cp_data = yaml_data['coverpoints']
        if isinstance(cp_data, dict):
            for k, v in cp_data.items():
                if isinstance(v, dict) and 'coverpoint' in v:
                    groups.append({'names': split_name_list(k), 'coverpoint': v['coverpoint']})

    return groups


def normalize_coverpoint(cp: Any) -> str:
    """Normalize coverpoint value for AsciiDoc output."""
    c = ', '.join(str(x) for x in cp) if isinstance(cp, list) else str(cp).strip() if cp else ''

    # Strip brackets and quotes
    c = c.strip('[]"\'')
    # Clean up braces and pipes
    c = re.sub(r'}+', '}', c).replace('|', '&#124;')
    return c


def make_adoc_table(rows: list[tuple[str, str, Any]], outpath: Path, base: str | None = None) -> None:
    """Generate AsciiDoc table from rows."""
    lines = []
    # Add auto-generation header comment with absolute paths
    argv_abs = [str(Path(arg).resolve()) if Path(arg).exists() else arg for arg in sys.argv]
    command_line = ' '.join(argv_abs)
    gen_date = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    lines.extend([
        '// WARNING: This file was automatically generated.',
        '// Do not modify by hand.',
        '// Generation command: ' + command_line,
        '// Generation date: ' + gen_date,
        ''
    ])
    if base:
        lines.extend([f'[[t-{base}-normative-rules]]', f'.{base} Normative Rules'])

    lines.extend([
        '[cols="1,4,3", options="header"]',
        '|===',
        '|Normative Rule |Rule Text |Coverpoints',
        ''
    ])

    for name, text, cp in rows:
        n = name.replace('|', '&#124;')
        t = (text or '').replace('|', '&#124;')
        c = normalize_coverpoint(cp)

        # Use multi-paragraph cell only for plain text with newlines
        if '\n' in t and not (t.strip().startswith('<p') or '<a href=' in t or 'pass:[' in t):
            lines.append(f'|{n} |a|{t} |{c}')
        else:
            lines.append(f'|{n} |{t} |{c}')
        lines.append('')

    lines.extend(['|===', ''])
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text('\n'.join(lines), encoding='utf-8')


def pick_cover_for_name(coverpoint: Any, names: list[str], idx: int) -> Any:
    """If `coverpoint` contains a brace-delimited list (e.g. "{A, B, C}..."),
    attempt to select the item corresponding to position `idx` in `names`.
    Otherwise return the original coverpoint.
    """
    if not coverpoint:
        return coverpoint

    # Accept a single-element list containing the string (common when YAML
    # coverpoint is written as a flow list). If coverpoint is a list with
    # multiple elements, leave it unchanged.
    if isinstance(coverpoint, list):
        if len(coverpoint) == 1 and isinstance(coverpoint[0], str):
            s = coverpoint[0]
        else:
            return coverpoint
    elif isinstance(coverpoint, str):
        s = coverpoint
    else:
        return coverpoint

    # If there is a slash, keep the entire right-hand side and select the
    # corresponding element from the left-hand brace-list.
    slash_pos = s.find('/')
    if slash_pos != -1:
        left = s[:slash_pos]
        right = s[slash_pos+1:]
        # Try to find a brace-delimited list on the left side first
        m_left = re.search(r"\{([^}]*)\}", left)
        if m_left:
            # If the YAML group contains a single normative name, preserve
            # the entire brace-delimited list (don't pick a single element).
            if len(names) == 1:
                return left + '/' + right
            inner = m_left.group(1)
            parts = [p.strip() for p in inner.split(',') if p.strip()]
            if 0 <= idx < len(parts):
                # preserve the right-hand side exactly as it appears
                return parts[idx] + '/' + right
        else:
            # No brace group on left. Try splitting on commas (single or multiple names).
            parts = [p.strip() for p in left.split(',') if p.strip()]
            if parts:
                # If the YAML group contains a single normative name, preserve
                # the entire left-hand listing instead of selecting an element.
                if len(names) == 1:
                    return left + '/' + right
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


def truncate_rule_text(text: str) -> str:
    """Return rule text without truncation."""
    return text


def main() -> None:
    p = argparse.ArgumentParser(description='Generate ASCIIDoc table from normative rules JSON and coverpoints YAML')
    # Default: download the canonical norm-rules.json from the ISA manual snapshot
    # canonical remote JSON used as default and as the fetch target when
    # --always-fetch is requested
    canonical_json_url = 'https://riscv.github.io/riscv-isa-manual/snapshot/norm-rules/norm-rules.json'
    p.add_argument('--json', default=canonical_json_url, help='Path or URL to norm-rules.json')
    p.add_argument('--yaml', default='coverpoints/norm/yaml', help='Path to a YAML file or a directory containing YAML files (default directory: coverpoints/norm/yaml)')
    p.add_argument('--out', default='ctp/src/norm/', help='Output directory for ASCIIDoc files (default: ctp/src/norm/)')
    p.add_argument('--report', default='coverpoints/norm/mismatch_report.txt', help='Report file or directory when --yaml is a directory')
    p.add_argument('--always-fetch', action='store_true', help='Always fetch the canonical remote JSON and update local cache even when --json is a local path')
    args = p.parse_args()

    # If paths are relative and not found from current CWD, try resolving
    # them relative to the script directory so running from repo root still works.
    script_dir = Path(__file__).resolve().parent

    # Parse args as Paths
    json_path = args.json  # Keep as string if URL
    yaml_path = Path(args.yaml)
    out_path = Path(args.out)
    report_path = Path(args.report)

    # If args.json is an HTTP(S) URL, we'll download it later; skip filesystem checks.
    if urlparse(args.json).scheme not in ('http', 'https'):
        json_path_obj = Path(args.json)
        if not json_path_obj.exists():
            alt = script_dir / args.json
            if alt.exists():
                json_path = alt
            else:
                print(f'Error: JSON file not found: {args.json}', file=sys.stderr)
                sys.exit(2)
        else:
            json_path = json_path_obj

    if not yaml_path.exists():
        alt = script_dir / args.yaml
        if alt.exists():
            yaml_path = alt
        else:
            print(f'Error: YAML file not found: {args.yaml}', file=sys.stderr)
            sys.exit(2)

    # Compute a cache path under the repository's coverpoints/norm directory.
    repo_root = script_dir.parent.parent
    cache_path = repo_root / 'coverpoints' / 'norm' / 'norm-rules.json'

    # Load JSON. Default behavior: if args.json is a URL it will be downloaded
    # and cached. If args.json is a local path the local file will be read.
    # If --always-fetch is set, force a download from the canonical remote
    # URL and update the cache; this ensures the run uses the remote copy.
    if args.always_fetch:
        try:
            jdata = load_json(canonical_json_url, cache_path=cache_path)
        except Exception as e:
            print(f'Error: failed to fetch canonical JSON ({canonical_json_url}): {e}', file=sys.stderr)
            sys.exit(2)
    else:
        jdata = load_json(json_path, cache_path=cache_path)
    print(f'Loaded normative rules JSON from: {json_path} to {cache_path}')
    rules_list = find_normative_rules(jdata)

    # Build a mapping of JSON rule name -> text for fast lookup
    json_text_map = {}
    json_links_map = {}
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
    # Build ASCIIDoc linked text for tags associated with this rule.
    # The link should apply to the tagged text (tag['text']) and the
    # tag 'name' (e.g. 'norm:...') should not be printed.
        linked_text_parts = []
        UNPRIV_BASE = 'https://riscv.github.io/riscv-isa-manual/snapshot/unprivileged/index.html'
        PRIV_BASE = 'https://riscv.github.io/riscv-isa-manual/snapshot/privileged/index.html'
        tags_iter = [tags] if isinstance(tags, dict) else list(tags) if tags is not None else []
        for tg in tags_iter:
            if not isinstance(tg, dict):
                continue
            tag_name = tg.get('name')
            tag_fn = tg.get('tag_filename', '') or ''
            tag_text = tg.get('text') or ''
            if not tag_name:
                continue
            # choose privileged or unprivileged base URL based on filename
            # do a case-insensitive check and test for 'unprivileged' first
            tag_fn_l = (tag_fn or '').lower()
            if 'unprivileged' in tag_fn_l:
                base = UNPRIV_BASE
            elif 'privileged' in tag_fn_l:
                base = PRIV_BASE
            else:
                base = UNPRIV_BASE
            # assemble URL with fragment pointing to the tag name
            # Percent-encode the fragment to produce a safe URL fragment.
            # Use urllib.parse.quote with an empty 'safe' to encode reserved
            # characters (e.g., ':') so the fragment is valid when embedded in
            # a link target.
            frag = quote(str(tag_name), safe='')
            url = f"{base}#{frag}"
            # Prepare display text: collapse whitespace and remove surrounding newlines
            disp = ' '.join(str(tag_text).split())
            # Replace any vertical bar '|' with the HTML entity '&#124;'
            # instead of truncating. This preserves more of the text while
            # preventing Asciidoc table column parsing from being broken by
            # literal '|' characters appearing inside quoted link or cell
            # text.
            if '|' in disp:
                disp = disp.replace('|', '&#124;')
            # ASCIIDoc inline link: link:url["display text"]
            # Use quoted display text to allow commas in the text (otherwise
            # Asciidoctor will treat commas as attribute separators). Also
            # escape double-quotes, backslashes and closing brackets inside
            # the display text.
            if disp:
                esc = disp.replace('\\', '\\\\').replace('"', '\\"').replace(']', '\\]')
                # encode comma as HTML entity so Asciidoctor won't treat it
                # as an attribute separator and we can emit an unquoted
                # link:URL[display text] form (no visible quotes).
                if ',' in esc:
                    esc = esc.replace(',', '&#44;')
                # final safety: replace any remaining '|' with '&#124;'
                if '|' in esc:
                    esc = esc.replace('|', '&#124;')
                # Store as a tuple so we can render multi-link cases as HTML
                # paragraphs (anchors) later to avoid relying on the Asciidoc
                # 'a|' multi-paragraph cell marker which was showing up as a
                # visible 'a' in some renderers.
                linked_text_parts.append((url, esc))
            else:
                # fallback to linking the tag name (without printing 'norm:')
                # but per request do not print the tag name; so skip if no display text
                pass

        # If we created linked parts, use them as the rule text; when there
        # are multiple linked parts, join them with a blank line so they
        # render as separate paragraphs. The presence of newlines will
        # cause the adoc table generator to emit an 'a|' (asciidoc) cell
        # so the paragraphs are preserved.
        if linked_text_parts:
            # If there's only a single linked part, keep the original
            # Asciidoc link: macro so existing consumers that prefer it
            # keep working. If there are multiple link parts, convert
            # them into HTML paragraphs with anchor tags. This avoids
            # emitting the Asciidoc 'a|' multi-paragraph marker which
            # some renderers were showing as a visible 'a'.
            if len(linked_text_parts) == 1:
                url, esc = linked_text_parts[0]
                # We've encoded commas to '&#44;' and escaped ']' already,
                # so emit the simple inline link form without surrounding
                # quotes to avoid visible quotation marks in the ADOC.
                joined = f'link:{url}[{esc}]'
            else:
                # For multiple links, emit simple inline Asciidoc link macros
                # separated by single spaces (no HTML/passthrough and no
                # blank lines between parts). This collapses any paragraph
                # separation into single-space separated links so the table
                # cell remains a single-line cell and avoids emitting 'a|'.
                parts = []
                for url, esc in linked_text_parts:
                    # commas are encoded and brackets escaped above; emit
                    # the plain inline link macro to avoid visible quotes.
                    parts.append(f'link:{url}[{esc}]')
                joined = ' '.join(parts)

            json_text_map[name] = joined
            json_links_map[name] = []
        else:
            # Extract rule text and collapse any internal newlines/whitespace
            # into single spaces so we never emit multi-paragraph cells
            # (which previously required the 'a|' marker).
            raw_text = extract_rule_text(tags) or ''
            text = ' '.join(str(raw_text).split())
            # Replace any literal '|' characters with the HTML entity
            # to avoid breaking Asciidoc table parsing.
            if '|' in text:
                text = text.replace('|', '&#124;')
            json_text_map[name] = text
            json_links_map[name] = []
        # capture def_filename for later grouping in reports
        def_fn = entry.get('def_filename') or entry.get('def_file') or entry.get('definition_filename')
        json_def_map[name] = def_fn or 'unknown'

    # If args.yaml is a directory, process every .yaml/.yml file inside
    if yaml_path.is_dir():
        yaml_files = sorted(list(yaml_path.glob('*.yaml')) + list(yaml_path.glob('*.yml')))
        if not yaml_files:
            print(f'No YAML files found in directory: {yaml_path}', file=sys.stderr)
            sys.exit(2)

        # Always treat --out as a directory
        out_dir = out_path

        # Determine report directory
        report_dir = report_path if report_path.is_dir() else report_path.parent

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
                        text = truncate_rule_text(json_text_map.get(n, ''))
                        # append tag links (if any) to the rule text
                        tlinks = json_links_map.get(n, [])
                        if tlinks:
                            # separate text and links with two spaces so ADOC treats it as appended content
                            text = (text + '  ' + ' '.join(tlinks)).strip()
                    else:
                        text = 'see above'
                    rows.append((n, text, chosen_cp))

            # record per-yaml missing-in-json
            missing_in_json = sorted(list(yaml_names - json_names))
            base = yfile.stem
            per_yaml_missing[base] = missing_in_json

            # accumulate all yaml names seen
            all_yaml_names.update(yaml_names)

            # Write adoc for this yaml
            out_dir.mkdir(parents=True, exist_ok=True)
            report_dir.mkdir(parents=True, exist_ok=True)
            outpath = out_dir / f'{base}_norm_rules.adoc'
            make_adoc_table(rows, outpath, base=base)

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
        # Per-YAML sections: only include files that have missing names
        for base in sorted(per_yaml_missing.keys()):
            missing = per_yaml_missing[base]
            if not missing:
                # omit files with no missing names from the report
                continue
            report_lines.append(f'YAML file: {base}.yaml')
            report_lines.append('-' * (10 + len(base)))
            report_lines.append('Names present in YAML but missing from JSON:')
            report_lines.extend(['  ' + n for n in missing])
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
        if report_path.is_dir() or str(report_path).endswith(os.sep):
            rpt_dir = report_path
            rpt_dir.mkdir(parents=True, exist_ok=True)
            final_report_path = rpt_dir / 'mismatch_report.txt'
        else:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            final_report_path = report_path

        final_report_path.write_text('\n'.join(report_lines), encoding='utf-8')

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
                text = truncate_rule_text(json_text_map.get(n, ''))
                tlinks = json_links_map.get(n, [])
                if tlinks:
                    text = (text + '  ' + ' '.join(tlinks)).strip()
            else:
                text = 'see above'
            rows.append((n, text, chosen_cp))

    missing_in_json = sorted(list(yaml_names - json_names))
    missing_in_yaml = sorted(list(json_names - yaml_names))

    # Always treat --out as a directory
    out_dir = out_path
    out_dir.mkdir(parents=True, exist_ok=True)
    base = yaml_path.stem
    outpath = out_dir / f'{base}_norm_rules.adoc'
    make_adoc_table(rows, outpath, base=base)

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

    report_path.write_text('\n'.join(report_lines), encoding='utf-8')


if __name__ == '__main__':
    main()
