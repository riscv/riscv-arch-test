#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 RISC-V International
#
# Self-test for the UDB feature extractor.
#
# Adapted by David Harris from the original by Jayant Malvi (riscv-arch-test #1655),
# with assistance from Claude.
#
# Builds the extractor for RV32 and RV64, runs it on the Sail max configurations with groups of
# extensions switched off through --config-override, and checks that every extension the
# extractor reports, or fails to report, agrees with the configuration.  Only unprivileged,
# ratified, trap-detectable extensions that the Sail configuration names are checked; the rest of
# the output is listed as unchecked.

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# name -> Sail override (a partial configuration merged over the base one)
CASES = {
    "max": {},
    "no-M": {"extensions": {"M": {"supported": False}}},
    "no-M-Zmmul": {"extensions": {"M": {"supported": False}, "Zmmul": {"supported": False}}},
    # H requires I, and the Sh* extensions require H
    "E": {"base": {"E": True}, "extensions": {k: {"supported": False} for k in
          ["H", "Sha", "Shcounterenw", "Shgatpa", "Shtvala", "Shvsatpa", "Shvstvala", "Shvstvecd"]}},
    "no-A": {"extensions": {k: {"supported": False} for k in
             ["A", "Zaamo", "Zalrsc", "Zacas", "Zabha", "Zawrs", "Zicfiss"]}},
    "no-B": {"extensions": {k: {"supported": False} for k in
             ["B", "Zba", "Zbb", "Zbs", "Zbc", "Zbkb", "Zbkc", "Zbkx", "Zknd", "Zkne", "Zknh", "Zksed", "Zksh", "Zkr"]}},
    "no-C": {"extensions": {k: {"supported": False} for k in ["Zca", "Zcb", "Zcd", "Zcf", "Zcmop"]}},
    # Zifencei is not switched off: Sail 0.14 decodes fence.i whatever the configuration says
    "no-Zi": {"extensions": {k: {"supported": False} for k in
              ["Zicbom", "Zicboz", "Zicond", "Zimop", "Zicntr", "Zihpm", "Zicfiss", "Zicfilp"]}},
    "no-V": {"extensions": {"V": {"support_level": "Disabled"},
                            **{k: {"supported": False} for k in
                               ["Zvbb", "Zvbc", "Zvkb", "Zvkg", "Zvkned", "Zvknha", "Zvknhb", "Zvksed", "Zvksh",
                                "Zvfh", "Zvfhmin", "Zvfbfmin", "Zvfbfwma", "Zvabd", "Zvkt"]}}},
    "no-FP": {"extensions": {"V": {"support_level": "Disabled"},
                             **{k: {"supported": False} for k in
                                ["F", "D", "Zfh", "Zfhmin", "Zfa", "Zfbfmin", "Zcd", "Zcf",
                                 "Zvbb", "Zvbc", "Zvkb", "Zvkg", "Zvkned", "Zvknha", "Zvknhb", "Zvksed", "Zvksh",
                                 "Zvfh", "Zvfhmin", "Zvfbfmin", "Zvfbfwma", "Zvabd", "Zvkt"]}}},
    "Zfinx": {"base": {"mstatus": {"fs_legal_states": "ExtContext_Off"}},
              "extensions": {"V": {"support_level": "Disabled"},
                             **{k: {"supported": False} for k in
                                ["F", "D", "Zfh", "Zfhmin", "Zfa", "Zfbfmin", "Zcd", "Zcf",
                                 "Zvbb", "Zvbc", "Zvkb", "Zvkg", "Zvkned", "Zvknha", "Zvknhb", "Zvksed", "Zvksh",
                                 "Zvfh", "Zvfhmin", "Zvfbfmin", "Zvfbfwma", "Zvabd", "Zvkt"]},
                             **{k: {"supported": True} for k in ["Zfinx", "Zhinx", "Zhinxmin"]},
                             # Zdinx without D fails an assertion in Sail 0.14 (flen stays 32)
                             "Zdinx": {"supported": False}}},
}

# Extensions the extractor derives from vector support rather than a same-named Sail key
VECTOR_DERIVED = ["V", "Zve32x", "Zve32f", "Zve64x", "Zve64f", "Zve64d"]

# Sail keys the extractor cannot be expected to report: privileged extensions (S, H, U, Sm*, Ss*,
# Sh*, Sv*), the unprivileged extensions that no instruction can detect by trapping (listed in
# NOT_DETECTABLE_EXTENSIONS in extensions.h), and extensions that are not yet ratified
NOT_CHECKED = {"Zihintpause", "Zihintntl", "Zicbop", "Zicclsm", "Ztso", "Zkt", "Zvkt", "Zic64b", "Ziccif",
               "Ziccamoa", "Ziccamoc", "Ziccrse", "Za64rs", "Za128rs", "Zama16b",
               "Zibi", "Zvabd"}


def checked(name):
    return name not in NOT_CHECKED and not re.match(r"^(S|H$|U$)", name)


def load_config(path):
    text = re.sub(r"^\s*//.*$", "", Path(path).read_text(), flags=re.M)
    return json.loads(text)


def merge(base, override):
    out = dict(base)
    for k, v in override.items():
        out[k] = merge(base.get(k, {}), v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def expected_extensions(config, reported):
    """Return {name: expected} for every reported or configured extension the config can decide."""
    exp = {}
    ext = config["extensions"]
    for name, entry in ext.items():
        if isinstance(entry, dict) and "supported" in entry and checked(name):
            exp[name] = bool(entry["supported"])
    exp["E"] = bool(config["base"]["E"])
    exp["I"] = not exp["E"]
    exp["Zicsr"] = True
    v = ext.get("V", {})
    level = v.get("support_level")
    if level == "Disabled":
        for name in VECTOR_DERIVED:
            exp[name] = False
    elif level == "Full":
        vlen = 1 << v.get("vlen_exp", 7)
        for name in VECTOR_DERIVED:
            exp[name] = True
        exp["V"] = vlen >= 128
        for n in [32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]:
            exp[f"Zvl{n}b"] = n <= vlen
    # Umbrella names the extractor derives; Sail names them too, so check them when it does
    return exp


def run(cmd, log):
    with open(log, "w") as f:
        return subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", required=True)
    p.add_argument("--sim", default="sail_riscv_sim")
    p.add_argument("--build-dir", required=True)
    p.add_argument("--xlen", default="32,64")
    p.add_argument("--cases", default=",".join(CASES))
    args = p.parse_args()

    root = Path(args.repo_root)
    build = Path(args.build_dir)
    makefile = root / "tests-dev/priv/UDBFeatureExtractor/Makefile"
    failures = 0
    for xlen in [int(x) for x in args.xlen.split(",")]:
        config_dir = root / f"config/sail/sail-rv{xlen}-max"
        base = load_config(config_dir / "sail.json")
        elf = build / f"feature_extractor{xlen}.elf"
        if subprocess.run(["make", "-f", str(makefile), "elf", f"XLEN={xlen}", f"CONFIG_DIR={config_dir}",
                           f"BUILD_DIR={build}"]).returncode:
            print(f"FAIL: build for XLEN={xlen}")
            failures += 1
            continue
        for case in args.cases.split(","):
            override = CASES[case]
            work = build / f"test-{xlen}-{case}"
            work.mkdir(parents=True, exist_ok=True)
            override_file = work / "override.json"
            override_file.write_text(json.dumps(override, indent=2))
            out = work / "extracted_config.yaml"
            log = work / "sail.log"
            cmd = [args.sim, "--config", str(config_dir / "sail.json"), "--config-override", str(override_file),
                   "--terminal-log", str(out), str(elf)]
            rc = run(cmd, log)
            text = out.read_text() if out.exists() else ""
            reported = set(re.findall(r"name: (\w+),", text))
            warnings = [l for l in text.splitlines() if l.startswith("# warning") or l.startswith("# FATAL")]
            if rc or not reported:
                print(f"FAIL rv{xlen} {case}: sail exit {rc}, {len(reported)} extensions reported; see {log}")
                failures += 1
                continue
            exp = expected_extensions(merge(base, override), reported)
            wrong = {n: e for n, e in exp.items() if e != (n in reported)}
            unchecked = sorted(reported - set(exp))
            status = "ok  " if not wrong and not warnings else "FAIL"
            if wrong or warnings:
                failures += 1
            mismatches = ", ".join(f"{n} (expected {'on' if e else 'off'})" for n, e in sorted(wrong.items())) or "none"
            extra = "  unchecked: " + " ".join(unchecked) if unchecked else ""
            print(f"{status} rv{xlen} {case:11} reported {len(reported):3}  mismatches: {mismatches}{extra}")
            for w in warnings:
                print("     ", w)
    print("all tests passed" if not failures else f"{failures} failure(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
