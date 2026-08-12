##################################
# dut_environment.py
#
# SPDX-License-Identifier: Apache-2.0
#
# Generate dut_environment.h from the `dut_environment` block of a UDB config.
##################################

"""Turn the config's dut_environment block into a C header.

These are DUT-specific values (device addresses, interrupt timing) the test body
bakes into certified code, as opposed to the DUT code behind the RVMODEL_* macros.
They come from the config, not the customer's private rvmodel_macros.h, because
the reference model needs the same addresses to produce a matching signature - so
they were never really private.

UDB accepts an unknown top-level block but udb-gen won't emit it, so we do it here.
"""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

# Integer-valued entries: emitted as #define <name> <value>.
# Anything not listed here is rejected, so a typo in a config fails loudly
# instead of silently leaving a constant undefined.
_INT_KEYS: tuple[str, ...] = (
    "RVMODEL_ACCESS_FAULT_ADDRESS",
    "RVMODEL_MTIME_ADDRESS",
    "RVMODEL_MTIMECMP_ADDRESS",
    "RVMODEL_INTERRUPT_LATENCY",
    "RVMODEL_TIMER_INT_SOON_DELAY",
    "RVMODEL_MAX_CYCLES_PER_TIMER_TICK",
)

# Boolean flags: emitted as a bare #define when true, omitted when false.
_FLAG_KEYS: tuple[str, ...] = ("STANDARD_SM_SUPPORTED",)

_GUARD = "_ACT_DUT_ENVIRONMENT_H"


def read_dut_environment(udb_config_file: Path) -> dict[str, object]:
    """Return the ``dut_environment`` block, or {} when the config has none."""
    yaml = YAML(typ="safe", pure=True)
    config = yaml.load(udb_config_file.read_text())
    block = (config or {}).get("dut_environment") or {}
    if not isinstance(block, dict):
        raise TypeError(f"dut_environment must be a mapping in {udb_config_file}, got {type(block).__name__}")
    unknown = sorted(set(block) - set(_INT_KEYS) - set(_FLAG_KEYS))
    if unknown:
        known = ", ".join((*_INT_KEYS, *_FLAG_KEYS))
        raise ValueError(f"Unknown dut_environment key(s) in {udb_config_file}: {unknown}. Known keys: {known}")
    return block


def _int_lines(name: str, value: object) -> list[str]:
    """Emit one integer constant plus an agreement check. Kit builds have no
    rvmodel_macros.h so the config wins; normal builds keep the DUT header but
    #error if it disagrees, catching a reference model built for a different map."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"dut_environment.{name} must be an integer, got {value!r}")
    cfg_name = f"ACT_CFG_{name}"
    return [
        f"#define {cfg_name} {value:#x}",
        f"#ifdef {name}",
        f"  #if ({name}) != ({cfg_name})",
        f'    #error "{name} in rvmodel_macros.h disagrees with dut_environment in the UDB config"',
        "  #endif",
        "#else",
        f"  #define {name} {cfg_name}",
        "#endif",
        "",
    ]


def generate_dut_environment_header(udb_config_file: Path, output_file: Path) -> None:
    """Write dut_environment.h for one config."""
    block = read_dut_environment(udb_config_file)

    lines = [
        "// Auto-generated from the UDB config's dut_environment block by act (do not edit)",
        "// SPDX-License-Identifier: Apache-2.0",
        "",
        f"#ifndef {_GUARD}",
        f"#define {_GUARD}",
        "",
    ]

    if not block:
        lines += [
            "// This config has no dut_environment block, so every constant still comes",
            "// from the DUT's rvmodel_macros.h. Certification-kit builds require the",
            "// block; normal builds are unaffected.",
            "",
        ]

    for name in _INT_KEYS:
        if name in block:
            lines += _int_lines(name, block[name])

    for name in _FLAG_KEYS:
        if block.get(name):
            lines += [f"#ifndef {name}", f"  #define {name}", "#endif", ""]

    lines += [f"#endif // {_GUARD}", ""]
    output_file.write_text("\n".join(lines))
