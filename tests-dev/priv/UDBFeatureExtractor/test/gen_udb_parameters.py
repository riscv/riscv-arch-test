#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 RISC-V International
#
# Generate udb_parameters.h, the list of every UDB parameter with the condition under which it
# applies to a hart, from the udb gem the framework pins (framework/src/act/data/Gemfile) or from a
# riscv-unified-db checkout:
#
#   uv run tests-dev/priv/UDBFeatureExtractor/test/gen_udb_parameters.py > udb_parameters.h
#   uv run tests-dev/priv/UDBFeatureExtractor/test/gen_udb_parameters.py /path/to/riscv-unified-db > udb_parameters.h
#
# The extractor prints, commented out, every parameter that applies to the hart but that it could
# not determine, so the reader of the output knows what is left to fill in by hand.

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import make_config

# Extensions the extractor knows by a name other than have("X")
SPECIAL = {
    "Sm": "true",
    "Zicsr": "true",
    "S": "has_s",
    "H": "has_h",
    "U": "has_u",
    "Zvl32b": "vlen != 0",
    # the translation modes are not in the extension tables; any_atp says whether satp accepts one
    "Sv32": "any_atp",
    "Sv39": "any_atp",
    "Sv48": "any_atp",
    "Sv57": "any_atp",
}


# Conditions on another parameter, as C expressions over variables print_parameters() sets before
# it lists the undetermined parameters; any other parameter condition is taken as true
PARAM_EQUAL_TRUE = {
    "TDATA3_IMPLEMENTED": "tdata3_impl",
    "MCONTEXT_IMPLEMENTED": "mcontext_impl",
    "SCONTEXT_IMPLEMENTED": "scontext_impl",
    "MCOUNTINHIBIT_IMPLEMENTED": "inhibit",
    "MARCHID_IMPLEMENTED": "marchid_impl",
    "MIMPID_IMPLEMENTED": "mimpid_impl",
    "MISALIGNED_LDST": "lw_ok",
}
PARAM_INCLUDES_TRUE = {
    "SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS": "trig_mcontrol6",
    "SDTRIG_ICOUNT_SUPPORTED_TRIGGERS": "trig_icount",
    "SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS": "trig_itrigger",
    "SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS": "trig_etrigger",
}


def param_gate(p: dict) -> str:
    if "allOf" in p or "anyOf" in p:
        op = " && " if "allOf" in p else " || "
        parts = [param_gate(q) for q in p.get("allOf", p.get("anyOf", []))]
        if "anyOf" in p and not all(parts):
            return ""  # an unmodelled alternative may hold
        parts = [q for q in parts if q]
        return op.join(f"({q})" for q in parts)
    name = p.get("name")
    if name == "NUM_PMP_ENTRIES" and p.get("greaterThan") == 0:
        return "num_pmp > 0"
    if name == "HPM_COUNTER_EN" and p.get("equal") is True and "index" in p:
        return f"(hpm >> {p['index']}) & 1"
    if p.get("equal") is True and name in PARAM_EQUAL_TRUE:
        return PARAM_EQUAL_TRUE[name]
    if p.get("includes") is True and name in PARAM_INCLUDES_TRUE:
        return PARAM_INCLUDES_TRUE[name]
    if name in ("SXLEN", "VSXLEN") and p.get("includes") in (32, 64):
        return f"__riscv_xlen == {p['includes']}"  # a mode's XLEN other than MXLEN is not modelled
    return ""


def gate(node: object) -> str:
    """The C condition for a definedBy node: extensions become have() tests, allOf/anyOf combine them."""
    if isinstance(node, dict):
        if "extension" in node:
            return gate(node["extension"])
        if "allOf" in node:
            parts = [gate(n) for n in node["allOf"]]
            parts = [p for p in parts if p]
            return " && ".join(f"({p})" for p in parts) if parts else ""
        if "anyOf" in node:
            parts = [gate(n) for n in node["anyOf"]]
            parts = [p for p in parts if p]
            return " || ".join(f"({p})" for p in parts) if parts else ""
        if "noneOf" in node:
            parts = [gate(n) for n in node["noneOf"]]
            parts = [p for p in parts if p]
            return " && ".join(f"!({p})" for p in parts) if parts else ""
        if "param" in node:
            return param_gate(node["param"])
        if "name" in node:
            return SPECIAL.get(node["name"], f'have("{node["name"]}")')
    if isinstance(node, list):
        parts = [gate(n) for n in node]
        parts = [p for p in parts if p]
        return " && ".join(f"({p})" for p in parts) if parts else ""
    return ""


def main() -> None:
    # the udb gem's .data directory holds the same spec/ tree as a checkout
    udb = Path(sys.argv[1]) if len(sys.argv) > 1 else make_config.udb_param_dir().parents[3]
    if (udb / ".git").exists():
        rev = (
            "riscv-unified-db "
            + subprocess.run(
                ["git", "-C", str(udb), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=False
            ).stdout.strip()
        )
    else:
        rev = udb.parent.name  # udb-<version>
    rows = []
    for f in sorted((udb / "spec/std/isa/param").glob("*.yaml")):
        doc = make_config.load_yaml(f.read_text())
        if not isinstance(doc, dict) or doc.get("kind") != "parameter" or doc.get("name") != f.stem:
            continue
        g = gate(doc.get("definedBy", {})) or "true"
        rows.append((doc["name"], g))
    print("// SPDX-License-Identifier: Apache-2.0")
    print("// Copyright (c) 2026 RISC-V International")
    print("//")
    print("// udb_parameters.h: every UDB parameter and the condition under which it applies to the hart.")
    print(f"// Generated by test/gen_udb_parameters.py from {rev}; do not edit by hand.")
    print("//")
    print("// UDB_PARAMETERS(P) expands P(name, applies) for each parameter, where applies is a C")
    print("// expression over have(), has_s, has_h, has_u, vlen, num_pmp, any_atp and the parameter values")
    print("// print_parameters() records (hpm, inhibit, lw_ok, *_impl, trig_*).")
    print()
    print("#define UDB_PARAMETERS(P) \\")
    for name, g in rows:
        print(f"    P({name}, {g}) \\")
    print("    /* end */")


if __name__ == "__main__":
    main()
