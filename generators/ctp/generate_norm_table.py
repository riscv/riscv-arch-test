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
import urllib.request
import urllib.error
import urllib.parse

try:  # pylint: disable=import-error
    import yaml
except Exception:  # pragma: no cover - optional dependency
    yaml = None


def load_json(path, cache_path=None):
    """Load JSON from a local file path or an HTTP/HTTPS URL.

    If `path` starts with 'http://' or 'https://', attempt to download it.
    If `cache_path` is provided, write the downloaded JSON to that path.
    Otherwise read it from the filesystem.
    """
    if isinstance(path, str) and (path.startswith('http://') or path.startswith('https://')):
        try:
            with urllib.request.urlopen(path, timeout=20) as resp:
                data = resp.read()
                text = data.decode('utf-8')
                # Optionally cache the downloaded JSON
                if cache_path:
                    try:
                        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                        with open(cache_path, 'w', encoding='utf-8') as cf:
                            cf.write(text)
                    except Exception:
                        # Don't fail the whole run if caching fails; just warn
                        print(f'Warning: failed to write cache to {cache_path}', file=sys.stderr)
                return json.loads(text)
        except urllib.error.URLError as e:
            raise RuntimeError(f'Failed to download JSON from {path}: {e}')
    # local file
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

    def flush_group():
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


def split_name_list(val):
    """Split a name or names expression into a list of names.
    Handles bracketed lists ([a, b]), comma-separated strings, and
    strips surrounding quotes and whitespace.
    """
    if not val:
        return []
    v = str(val).strip()
    v = v.strip('"\'')
    if v.startswith('[') and v.endswith(']'):
        inner = v[1:-1]
        parts = [p.strip() for p in inner.split(',') if p.strip()]
        return parts
    if ',' in v:
        return [p.strip() for p in v.split(',') if p.strip()]
    return [v]


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
                    for el in n:
                        names.extend(split_name_list(el))
                elif isinstance(n, str):
                    s = n.strip()
                    if s.startswith('[') and s.endswith(']'):
                        inner = s[1:-1]
                        parts = [p.strip() for p in inner.split(',') if p.strip()]
                        names.extend(parts)
                    else:
                        names.extend([p.strip() for p in s.split(',') if p.strip()])
            if 'name' in item:
                raw = item.get('name')
                parts = split_name_list(raw)
                # insert parts at the front preserving order
                for p in reversed(parts):
                    names.insert(0, p)
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
                                for el in n:
                                    names.extend(split_name_list(el))
                            elif isinstance(n, str):
                                s = n.strip()
                                if s.startswith('[') and s.endswith(']'):
                                    inner = s[1:-1]
                                    parts = [p.strip() for p in inner.split(',') if p.strip()]
                                    names.extend(parts)
                                else:
                                    names.extend([p.strip() for p in s.split(',') if p.strip()])
                        if 'name' in item:
                            raw = item.get('name')
                            parts = split_name_list(raw)
                            for p in reversed(parts):
                                names.insert(0, p)
                        cover = item.get('coverpoint')
                        if names:
                            groups.append({'names': names, 'coverpoint': cover})
                    return groups

        # First, check for top-level mapping where each key is a name
        for k, v in yaml_data.items():
            if isinstance(v, dict) and 'coverpoint' in v:
                groups.append({'names': split_name_list(k), 'coverpoint': v.get('coverpoint')})

        # Also handle nested 'coverpoints' key
        if 'coverpoints' in yaml_data and isinstance(yaml_data['coverpoints'], dict):
            for k, v in yaml_data['coverpoints'].items():
                if isinstance(v, dict) and 'coverpoint' in v:
                    groups.append({'names': split_name_list(k), 'coverpoint': v.get('coverpoint')})

    return groups


def make_adoc_table(rows, outpath, base=None):
    # rows: list of (name, text, coverpoints)
    lines = []
    # Optional anchor and title for the table per-extension
    if base:
        lines.append(f'[[t-{base}-normative_rules]]')
        lines.append(f'.{base} Normative Rules')
    lines.append('[cols="1,4,3", options="header"]')
    lines.append('|===')
    lines.append('|Normative Rule |Rule Text |Coverpoints')
    lines.append('')

    for name, text, cp in rows:
        # Replace any pipe in the name with the HTML entity so table parsing
        # cannot be broken by literal '|' characters.
        n = name.replace('|', '&#124;')

        # Rule Text: replace any '|' characters with the HTML entity so
        # Asciidoc table column parsing is not broken by literal vertical
        # bars inside cells. If the rule text contains newlines, emit an
        # 'a|' multi-paragraph table cell so paragraph breaks are
        # preserved and multiple links appear separated by blank lines.
        t = (text or '')
        # Always replace any literal '|' characters to the HTML
        # entity so the source .adoc table cell is not broken.
        if '|' in t:
            t = t.replace('|', '&#124;')

        # Normalize coverpoint value. If cp is a list (from YAML), join items
        # without quotes. If it's a scalar string, use it. Then remove any
        # surrounding list brackets and surrounding quotes so the ADOC cell
        # contains the bare coverpoint text.
        if isinstance(cp, list):
            # join list items with comma+space
            c = ', '.join([str(x) for x in cp])
        else:
            c = (str(cp) if cp is not None else '').strip()

        # If the value was written as a flow list string like "['x','y']",
        # strip enclosing brackets first.
        if c.startswith('[') and c.endswith(']'):
            c = c[1:-1].strip()

        # Remove surrounding single or double quotes if present
        if (c.startswith("'") and c.endswith("'")) or (c.startswith('"') and c.endswith('"')):
            c = c[1:-1]

        # Collapse consecutive closing braces '}}' into a single '}' to remove excess
        c = re.sub(r"\}{2,}", "}", c)
        # Replace any pipe characters in the coverpoint text as well.
        c = c.replace('|', '&#124;')

        # If the rule text contains newline(s) we previously emitted an
        # 'a|' multi-paragraph cell. That marker was visible in some
        # renderers. To avoid the visible 'a' while still preserving
        # paragraphs, we now treat embedded HTML paragraphs or anchor
        # content as safe (emit inline cell), and only fall back to the
        # Asciidoc 'a|' marker for raw plaintext that contains newlines.
        # Treat Asciidoc passthroughs and raw HTML paragraphs as safe
        # inline content so we don't emit the Asciidoc 'a|' multi-paragraph
        # table cell marker which was visible in some renderers. Detect
        # both raw '<p'/'<a href=' fragments and 'pass:[' passthroughs.
        if '\n' in t and not (t.strip().startswith('<p') or '<a href=' in t or 'pass:[' in t):
            # write a multi-paragraph cell using Asciidoc marker
            lines.append(f'|{n} |a|{t} |{c}')
        else:
            # inline cell — includes HTML paragraph/anchor strings we
            # generated for multi-link cases, or single-line text.
            lines.append(f'|{n} |{t} |{c}')

        lines.append('')

    lines.append('|===')
    lines.append('')

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


def main():
    p = argparse.ArgumentParser(description='Generate ASCIIDoc table from normative rules JSON and coverpoints YAML')
    # Default: download the canonical norm-rules.json from the ISA manual snapshot
    # canonical remote JSON used as default and as the fetch target when
    # --always-fetch is requested
    canonical_json_url = 'https://risc-v-certification-steering-committee.github.io/riscv-isa-manual/snapshot/norm-rules/norm-rules.json'
    p.add_argument('--json', default=canonical_json_url, help='Path or URL to norm-rules.json')
    p.add_argument('--yaml', default='coverpoints/norm/yaml', help='Path to a YAML file or a directory containing YAML files (default directory: coverpoints/norm/yaml)')
    p.add_argument('--out', default='ctp/src/norm/', help='Output directory for ASCIIDoc files (default: ctp/src/norm/)')
    p.add_argument('--report', default='coverpoints/norm/mismatch_report.txt', help='Report file or directory when --yaml is a directory')
    p.add_argument('--always-fetch', action='store_true', help='Always fetch the canonical remote JSON and update local cache even when --json is a local path')
    args = p.parse_args()

    # If paths are relative and not found from current CWD, try resolving
    # them relative to the script directory so running from repo root still works.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # If args.json is an HTTP(S) URL, we'll download it later; skip filesystem checks.
    if not (isinstance(args.json, str) and (args.json.startswith('http://') or args.json.startswith('https://'))):
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
    # Compute a cache path under the repository's coverpoints/norm directory.
    # script_dir is the script's directory; the repo root is four levels up.
    repo_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..', '..'))
    cache_dir = os.path.join(repo_root, 'coverpoints', 'norm')
    cache_path = os.path.join(cache_dir, 'norm-rules.json')

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
        # If args.json is a URL the loader will download it; otherwise load locally
        jdata = load_json(args.json, cache_path=cache_path)
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
        UNPRIV_BASE = 'https://risc-v-certification-steering-committee.github.io/riscv-isa-manual/snapshot/unprivileged/index.html'
        PRIV_BASE = 'https://risc-v-certification-steering-committee.github.io/riscv-isa-manual/snapshot/privileged/index.html'
        if isinstance(tags, dict):
            tags_iter = [tags]
        else:
            tags_iter = list(tags) if tags is not None else []
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
            frag = urllib.parse.quote(str(tag_name), safe='')
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
    if os.path.isdir(args.yaml):
        yaml_files = sorted(glob.glob(os.path.join(args.yaml, '*.yaml')) + glob.glob(os.path.join(args.yaml, '*.yml')))
        if not yaml_files:
            print(f'No YAML files found in directory: {args.yaml}', file=sys.stderr)
            sys.exit(2)

        # Always treat --out as a directory
        out_dir = args.out

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
            base = os.path.splitext(os.path.basename(yfile))[0]
            per_yaml_missing[base] = missing_in_json

            # accumulate all yaml names seen
            all_yaml_names.update(yaml_names)

            # Write adoc for this yaml
            out_dir = ensure_dir(out_dir)
            report_dir = ensure_dir(report_dir)
            outpath = os.path.join(out_dir, base + '_norm_rules.adoc')
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
                tlinks = json_links_map.get(n, [])
                if tlinks:
                    text = (text + '  ' + ' '.join(tlinks)).strip()
            else:
                text = 'see above'
            rows.append((n, text, chosen_cp))

    missing_in_json = sorted(list(yaml_names - json_names))
    missing_in_yaml = sorted(list(json_names - yaml_names))

    # Always treat --out as a directory
    out_dir = ensure_dir(args.out)
    base = os.path.splitext(os.path.basename(args.yaml))[0]
    outpath = os.path.join(out_dir, base + '_norm_rules.adoc')
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

    report_text = '\n'.join(report_lines)
    with open(args.report, 'w', encoding='utf-8') as f:
        f.write(report_text)


if __name__ == '__main__':
    main()
