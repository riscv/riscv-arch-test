#!/usr/bin/env python3
"""Generate a YAML mapping from a Google Sheet.

Reads a sheet (CSV export or via service account) and builds a YAML file where
for every normative rule name found in column I there is an entry:

- name: <rule_name>
  coverpoint: [<coverpoint1>, <coverpoint2>, ...]

Usage (public sheet or accessible by HTTP):
  python3 google_sheet_to_yaml.py \
    --sheet-url 'https://docs.google.com/spreadsheets/d/<id>/edit' \
    --gid 747120884 \
    --out out.yaml

If the sheet is not publicly accessible, provide a service account JSON and the
`gspread` package will be used to read the sheet (requires enabling the
Sheets API and creating a service account with access):

  python3 google_sheet_to_yaml.py --sheet-id <id> --gid 747120884 \
    --service-account /path/to/service.json --out out.yaml

Dependencies:
- requests (optional; used for unauthenticated CSV export)
- gspread and google-auth (optional; used with --service-account)
- pyyaml

The script extracts columns:
- Column A => coverpoint
- Column I => normative rule names (one or more per cell)

Names in column I can be a comma-separated list, pipe-separated, or bracketed
list (e.g. "[add_op, sub_op]"). Blank rows are ignored.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from collections import OrderedDict, defaultdict
from typing import Dict, List, Optional

try:
    import requests
except Exception:
    requests = None

try:
    import yaml
except Exception:
    yaml = None


def fetch_csv_via_export(sheet_id: str, gid: str) -> Optional[str]:
    """Fetch CSV export for a Google Sheet (works for public or accessible sheets).

    Returns CSV text or None if requests isn't available or fetch failed.
    """
    if requests is None:
        return None
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.text
    return None


def fetch_csv_via_gspread(sheet_id: str, gid: str, service_account: str) -> Optional[str]:
    """Fetch CSV via gspread using a service account JSON file.

    Returns CSV text or None if gspread isn't available or an error occurred.
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except Exception:
        return None

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ]
    creds = Credentials.from_service_account_file(service_account, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    # gspread worksheets use gid -> sheet id mapping; find the worksheet with matching gid
    ws = None
    for w in sh.worksheets():
        # gspread has internal id as _properties['sheetId']
        try:
            sid = str(w._properties.get('sheetId'))
        except Exception:
            sid = None
        if sid == str(gid):
            ws = w
            break
    if ws is None:
        # fallback: use first worksheet
        ws = sh.get_worksheet(0)

    # get_all_values returns list of rows; write CSV text
    rows = ws.get_all_values()
    output_lines = []
    for row in rows:
        # ensure proper CSV row using csv module
        output_lines.append(','.join('"' + c.replace('"', '""') + '"' for c in row))
    return '\n'.join(output_lines)


def parse_sheet_csv(csv_text: str) -> List[List[str]]:
    """Return a list of rows (each a list of columns) parsed from CSV text."""
    reader = csv.reader(csv_text.splitlines())
    return [row for row in reader]


def extract_names(cell: str) -> List[str]:
    """Given the contents of column I, return a list of normalized names.

    Accepts formats like:
      - "add_op"
      - "add_op, sub_op"
      - "[add_op, sub_op]"
      - "add_op | sub_op"
    """
    if cell is None:
        return []
    s = str(cell).strip()
    if not s:
        return []
    # strip surrounding brackets
    if s.startswith('[') and s.endswith(']'):
        s = s[1:-1].strip()
    # split on comma, pipe, semicolon
    parts = re.split(r'[,|;]+', s)
    names = [p.strip() for p in parts if p and p.strip()]
    return names


def build_name_to_coverpoints(rows: List[List[str]]) -> Dict[str, List[str]]:
    """Process CSV rows and return mapping name -> list of coverpoints.

    Column A -> index 0
    Column I -> index 8 (0-based)
    """
    mapping: Dict[str, List[str]] = defaultdict(list)
    for row in rows:
        # protect against short rows
        cover = row[0].strip() if len(row) > 0 else ''
        names_cell = row[8] if len(row) > 8 else ''
        names = extract_names(names_cell)
        if not names:
            continue
        # preserve insertion order and avoid duplicates per name
        for nm in names:
            if cover and cover not in mapping[nm]:
                mapping[nm].append(cover)
    return mapping


def write_yaml(name_to_cps: Dict[str, List[str]], out_path: str) -> None:
    """Write the mapping to YAML as a list of entries with 'name' and 'coverpoint' list."""
    if yaml is None:
        raise RuntimeError('PyYAML is required to write YAML output (pip install pyyaml)')
    entries = []
    for nm in sorted(name_to_cps.keys()):
        cps = name_to_cps.get(nm, [])
        entries.append({'name': nm, 'coverpoint': cps})
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump({'normative_rule_definitions': entries}, f, sort_keys=False, default_flow_style=False)


def sheet_id_from_url(url: str) -> Optional[str]:
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if m:
        return m.group(1)
    return None


def main():
    p = argparse.ArgumentParser(description='Generate a YAML mapping from a Google Sheet')
    p.add_argument('--sheet-url', help='Full sheet URL (will extract sheet id)')
    p.add_argument('--sheet-id', help='Google sheet id (if sheet-url not provided)')
    p.add_argument('--gid', required=True, help='GID of the worksheet (the sheet tab id)')
    p.add_argument('--service-account', help='Path to a service account JSON file for gspread auth')
    p.add_argument('--out', required=True, help='Output YAML file path')
    args = p.parse_args()

    sheet_id = None
    if args.sheet_id:
        sheet_id = args.sheet_id
    elif args.sheet_url:
        sheet_id = sheet_id_from_url(args.sheet_url)
    if not sheet_id:
        print('Error: could not determine sheet id. Provide --sheet-id or a valid --sheet-url', file=sys.stderr)
        sys.exit(2)

    csv_text = None
    # Try unauthenticated CSV export first (works if sheet is public)
    csv_text = fetch_csv_via_export(sheet_id, args.gid)
    if csv_text is None and args.service_account:
        csv_text = fetch_csv_via_gspread(sheet_id, args.gid, args.service_account)

    if csv_text is None:
        print('Failed to fetch sheet contents. Ensure the sheet is public or provide --service-account.', file=sys.stderr)
        sys.exit(3)

    rows = parse_sheet_csv(csv_text)
    name_to_cps = build_name_to_coverpoints(rows)

    write_yaml(name_to_cps, args.out)
    print(f'Wrote YAML with {len(name_to_cps)} rules to {args.out}')


if __name__ == '__main__':
    main()
