#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 RISC-V International
#
# Run make_config.py on every configuration under config/ that has a run_cmd.txt, and compare
#   1. the generated UDB yaml with the configuration's yaml (extensions, and the parameters the
#      extractor measured),
#   2. the generated sail.json with the configuration's sail.json, and
#   3. the configuration's own yaml with its own sail.json (through udb_to_sail.py).
#
# Written by David Harris with assistance from Claude.
#
#   uv run tests-dev/priv/UDBFeatureExtractor/test/make_config_regression.py --build-dir work/make_config --jobs 16

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import sys
import traceback
from pathlib import Path
from typing import Any

import pyjson5

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import make_config
import udb_to_sail


def ext_names(lines: list[str]) -> tuple[set[str], set[str]]:
    """Extension names in yaml lines, split into reported and assumed ones."""
    reported, assumed = set(), set()
    for line in lines:
        m = re.search(r"name: (\w+)", line)
        if m:
            (assumed if "# assumed" in line and "requires it" in line else reported).add(m.group(1))
    return reported, assumed


def sail_diffs(
    conv: udb_to_sail.Converter,
    new: dict[str, Any],
    old: dict[str, Any],
    extra: dict[str, Any],
    assumed: set[str],
    untested: set[str],
) -> dict[str, list]:
    """Differences split by where the generated value came from."""
    out: dict[str, list] = {"udb": [], "measured": [], "assumed": [], "untested": [], "default": []}
    defaulted = set(conv.defaulted())
    for key, a, b in udb_to_sail.compare(conv, new, old):
        src = conv.sources.get(key, set())
        if key in extra:
            kind = "measured"
        elif key in defaulted:
            kind = "default"
        elif src & assumed:
            kind = "assumed"
        elif any(s.startswith("ext:") and s[4:] in untested and s[4:] not in conv.exts for s in src):
            kind = "untested"
        else:
            kind = "udb"
        out[kind].append((key, a, b))
    return out


def run_one(config_dir: Path, udb_yaml: Path, build: Path, timeout: int) -> dict[str, Any]:
    name = config_dir.name
    result: dict[str, Any] = {"name": name, "dir": str(config_dir.relative_to(make_config.REPO_ROOT))}
    old_yaml = make_config.load_yaml(udb_yaml.read_text())
    old_sail = pyjson5.loads((config_dir / "sail.json").read_text()) if (config_dir / "sail.json").exists() else None

    # 3. The configuration's yaml against its sail.json
    if old_sail is not None:
        try:
            _, cfg, conv, notes = udb_to_sail.convert_file(udb_yaml, config_dir, {})
            result["own_sail_diffs"] = udb_to_sail.compare(conv, cfg, old_sail)
            result["own_notes"] = notes + conv.unmodelled
        except Exception as e:  # noqa: BLE001
            result["own_error"] = f"{type(e).__name__}: {e}"

    try:
        r = make_config.make_config(config_dir, build / name, timeout)
    except FileNotFoundError as e:
        result["status"] = "skip"
        result["note"] = str(e)
        return result
    except Exception as e:  # noqa: BLE001
        result["status"] = "FAIL"
        result["note"] = f"{type(e).__name__}: {e}"
        result["trace"] = traceback.format_exc()
        return result
    result["status"] = "ok"
    result["xlen"] = r["xlen"]
    result["udb_errors"] = r["udb_errors"]
    result["sail_error"] = r["sail_error"]
    result["dropped"] = r["dropped"]
    result["assumed_params"] = sorted(r["assumed"])
    result["skipped_probes"] = r["skipped_probes"]
    result["incomplete"] = r["incomplete"]

    # 1. Extensions and measured parameters against the configuration's yaml
    gen = make_config.load_yaml(r["yaml"].read_text())
    text = r["yaml"].read_text()
    reported, assumed_exts = ext_names(re.findall(r"^  - \{.*$", text, re.MULTILINE))
    expected = {e["name"] if isinstance(e, dict) else str(e) for e in old_yaml["implemented_extensions"]}
    untested = make_config.untested_extensions(text)
    extra = reported - expected
    implied = {n for n in extra if n in make_config.IMPLIED and make_config.IMPLIED[n] <= expected}
    result["ext_missing"] = sorted(expected - reported - assumed_exts - untested)
    result["ext_extra"] = sorted(extra - implied)
    result["ext_assumed"] = sorted(assumed_exts)
    result["ext_untested_listed"] = sorted(expected & untested)
    old_params = old_yaml.get("params") or {}
    measured = {k: v for k, v in (gen.get("params") or {}).items() if k not in r["assumed"]}
    result["param_match"] = sorted(k for k, v in measured.items() if k in old_params and old_params[k] == v)
    result["param_mismatch"] = {
        k: (v, old_params[k]) for k, v in measured.items() if k in old_params and old_params[k] != v
    }
    result["param_not_in_yaml"] = sorted(k for k in measured if k not in old_params)
    result["param_assumed_differs"] = {
        k: (gen["params"][k], old_params[k])
        for k in r["assumed"]
        if k in old_params and old_params[k] != gen["params"][k]
    }

    # 2. Generated sail.json against the configuration's
    if old_sail is not None:
        _, cfg, conv, _ = udb_to_sail.convert_file(r["yaml"], config_dir, r["sail_extra"])
        result["sail_diffs"] = sail_diffs(conv, cfg, old_sail, r["sail_extra"], set(r["assumed"]), untested)
    return result


def fmt(v: object) -> str:
    if isinstance(v, int) and not isinstance(v, bool) and v > 9:
        return hex(v)
    s = json.dumps(v)
    return s if len(s) < 60 else s[:57] + "..."


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build-dir", type=Path, required=True)
    ap.add_argument("--jobs", "-j", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--configs", default="", help="comma-separated configuration names (default all)")
    args = ap.parse_args()

    build = args.build_dir.resolve()
    build.mkdir(parents=True, exist_ok=True)
    make_config.UDB_DATA_HOME = build / "udb-data"
    wanted = set(args.configs.split(",")) if args.configs else None
    configs = [(d, y) for d, y in make_config.find_configs() if wanted is None or d.name in wanted]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda c: run_one(c[0], c[1], build, args.timeout), configs))
    (build / "results.json").write_text(json.dumps(results, indent=1, default=str))

    for r in results:
        if r.get("status") != "ok":
            print(f"{r.get('status', 'FAIL'):4} {r['name']}  {r.get('note', '')}")
            continue
        print(f"---- {r['name']} (RV{r['xlen']})")
        if r["skipped_probes"]:
            print(f"  probes left out because they stopped the run: {', '.join(r['skipped_probes'])}")
        if r["incomplete"]:
            print(f"  the extractor did not finish: {r['incomplete']}")
        if r["udb_errors"]:
            print("  UDB rejects the generated yaml: " + " | ".join(e[:160] for e in r["udb_errors"]))
        if r["sail_error"]:
            print("  Sail rejects the generated sail.json: " + r["sail_error"].replace("\n", " | ")[:300])
        if r["ext_missing"] or r["ext_extra"]:
            print(f"  extensions: missing {' '.join(r['ext_missing']) or '-'}; extra {' '.join(r['ext_extra']) or '-'}")
        if r["param_mismatch"]:
            print(
                "  params measured != yaml: "
                + ", ".join(f"{k} {fmt(a)} vs {fmt(b)}" for k, (a, b) in sorted(r["param_mismatch"].items()))
            )
        print(
            f"  params: {len(r['param_match'])} match, {len(r['param_mismatch'])} differ, {len(r['assumed_params'])} assumed"
            f" ({len(r['param_assumed_differs'])} differ from the yaml), {len(r['dropped'])} dropped"
        )
        for kind, diffs in (r.get("sail_diffs") or {}).items():
            if diffs:
                print(f"  sail.json [{kind}]: " + ", ".join(f"{k} {fmt(a)} vs {fmt(b)}" for k, a, b in diffs))
        if r.get("own_sail_diffs"):
            print(
                "  own yaml vs own sail.json: "
                + ", ".join(f"{k} {fmt(a)} vs {fmt(b)}" for k, a, b in r["own_sail_diffs"])
            )
    ran = [r for r in results if r.get("status") == "ok"]
    print(
        f"{len(ran)} configurations run, {sum(r.get('status') == 'skip' for r in results)} skipped, "
        f"{sum(r.get('status') == 'FAIL' for r in results)} failed; "
        f"{sum(not r['udb_errors'] for r in ran)} generated yamls valid in UDB, "
        f"{sum(not r['sail_error'] for r in ran)} generated sail.json valid in Sail"
    )


if __name__ == "__main__":
    main()
